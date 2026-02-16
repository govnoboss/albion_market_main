"""
GBot Release Manager — Dev Tool
PyQt6 UI for building, packaging, and publishing GitHub Releases.
Run: python tools/release_manager.py
"""

import sys
import os
import json
import subprocess
import requests
import re
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QGroupBox,
    QProgressBar, QMessageBox, QFormLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from src.core.version import CURRENT_VERSION, GITHUB_REPO, APP_NAME

# Paths
VERSION_FILE = PROJECT_ROOT / "src" / "core" / "version.py"
BUILD_SCRIPT = PROJECT_ROOT / "build.bat"
PACKAGE_SCRIPT = PROJECT_ROOT / "package.bat"
TOKEN_FILE = PROJECT_ROOT / "config" / "release_token.json"
ZIP_FILE = PROJECT_ROOT / "dist" / f"{APP_NAME}.zip"


def load_token() -> str:
    """Load GitHub token from config file."""
    try:
        if TOKEN_FILE.exists():
            data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
            return data.get("token", "")
    except Exception:
        pass
    return ""


def save_token(token: str):
    """Save GitHub token to config file."""
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps({"token": token}), encoding="utf-8")


def update_version_file(new_version: str):
    """Update CURRENT_VERSION in version.py."""
    content = VERSION_FILE.read_text(encoding="utf-8")
    content = re.sub(
        r'CURRENT_VERSION\s*=\s*"[^"]*"',
        f'CURRENT_VERSION = "{new_version}"',
        content
    )
    VERSION_FILE.write_text(content, encoding="utf-8")


class ProcessWorker(QThread):
    """Runs a subprocess and emits output line by line."""
    output = pyqtSignal(str)
    finished_ok = pyqtSignal()
    finished_error = pyqtSignal(str)

    def __init__(self, command: str, cwd: str):
        super().__init__()
        self.command = command
        self.cwd = cwd

    def run(self):
        try:
            process = subprocess.Popen(
                self.command,
                cwd=self.cwd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            for line in process.stdout:
                self.output.emit(line.rstrip())
            process.wait()
            if process.returncode == 0:
                self.finished_ok.emit()
            else:
                self.finished_error.emit(f"Exit code: {process.returncode}")
        except Exception as e:
            self.finished_error.emit(str(e))


class ReleaseWorker(QThread):
    """Creates GitHub Release and uploads zip asset."""
    output = pyqtSignal(str)
    progress = pyqtSignal(int)
    finished_ok = pyqtSignal(str)  # release URL
    finished_error = pyqtSignal(str)

    def __init__(self, token: str, version: str, changelog: str, zip_path: Path):
        super().__init__()
        self.token = token
        self.version = version
        self.changelog = changelog
        self.zip_path = zip_path

    def run(self):
        try:
            headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json"
            }

            tag = f"v{self.version}"

            # 1. Create Release
            self.output.emit(f"Creating release {tag}...")
            release_data = {
                "tag_name": tag,
                "name": f"{APP_NAME} v{self.version}",
                "body": self.changelog,
                "draft": False,
                "prerelease": False
            }
            resp = requests.post(
                f"https://api.github.com/repos/{GITHUB_REPO}/releases",
                headers=headers,
                json=release_data,
                timeout=30
            )

            if resp.status_code == 422:
                # Release/tag already exists
                self.finished_error.emit(f"Release {tag} already exists on GitHub!")
                return

            resp.raise_for_status()
            release = resp.json()
            upload_url = release["upload_url"].replace("{?name,label}", "")
            self.output.emit(f"✅ Release created: {release['html_url']}")
            self.progress.emit(30)

            # 2. Upload zip asset
            if not self.zip_path.exists():
                self.finished_error.emit(f"ZIP file not found: {self.zip_path}")
                return

            file_size = self.zip_path.stat().st_size
            self.output.emit(f"Uploading {self.zip_path.name} ({file_size / 1024 / 1024:.1f} MB)...")

            upload_headers = {
                "Authorization": f"token {self.token}",
                "Content-Type": "application/zip"
            }

            with open(self.zip_path, "rb") as f:
                resp = requests.post(
                    f"{upload_url}?name={self.zip_path.name}",
                    headers=upload_headers,
                    data=f,
                    timeout=600
                )

            resp.raise_for_status()
            self.output.emit(f"✅ Asset uploaded: {self.zip_path.name}")
            self.progress.emit(100)

            self.finished_ok.emit(release["html_url"])

        except requests.exceptions.HTTPError as e:
            error_body = ""
            if e.response is not None:
                try:
                    error_body = e.response.json().get("message", "")
                except Exception:
                    error_body = e.response.text[:200]
            self.finished_error.emit(f"GitHub API Error: {e} — {error_body}")
        except Exception as e:
            self.finished_error.emit(str(e))


# ─── Styles ──────────────────────────────────────────────

STYLE = """
QMainWindow {
    background-color: #0d1117;
}
QWidget {
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 13px;
    color: #f0f6fc;
}
QGroupBox {
    border: 1px solid #30363d;
    border-radius: 8px;
    margin-top: 15px;
    padding-top: 15px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 5px;
    color: #f0f6fc;
}
QLineEdit, QTextEdit {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 12px;
    color: #f0f6fc;
    selection-background-color: #1f6feb;
}
QLineEdit:focus, QTextEdit:focus {
    border-color: #1f6feb;
}
QPushButton {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 10px 20px;
    color: #f0f6fc;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #30363d;
    border-color: #8b949e;
}
QPushButton:disabled {
    background-color: #161b22;
    color: #484f58;
    border-color: #21262d;
}
QPushButton#primary {
    background-color: #238636;
    border-color: #238636;
    font-weight: 700;
    font-size: 14px;
    padding: 12px 24px;
}
QPushButton#primary:hover {
    background-color: #2ea043;
}
QPushButton#primary:disabled {
    background-color: #21262d;
    border-color: #30363d;
    color: #484f58;
}
QTextEdit#log {
    background-color: #010409;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 10px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    color: #8b949e;
}
QProgressBar {
    border: 1px solid #30363d;
    border-radius: 6px;
    background-color: #0d1117;
    text-align: center;
    color: #f0f6fc;
}
QProgressBar::chunk {
    background-color: #238636;
    border-radius: 5px;
}
"""


class ReleaseManagerWindow(QMainWindow):
    """Developer tool for building, packaging, and publishing releases."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"GBot Release Manager")
        self.resize(700, 700)
        self.setStyleSheet(STYLE)
        self._workers = []  # Keep references
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("🚀 GBot Release Manager")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #f0f6fc;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # --- Release Info Group ---
        info_group = QGroupBox("Параметры релиза")
        info_layout = QFormLayout(info_group)
        info_layout.setSpacing(10)

        self.version_input = QLineEdit(CURRENT_VERSION)
        self.version_input.setPlaceholderText("1.0.0")
        info_layout.addRow("Версия:", self.version_input)

        self.token_input = QLineEdit(load_token())
        self.token_input.setPlaceholderText("ghp_xxxxxxxxxxxxxxxxxxxx")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        info_layout.addRow("GitHub Token:", self.token_input)

        self.changelog_input = QTextEdit()
        self.changelog_input.setPlaceholderText("Описание изменений в этой версии...")
        self.changelog_input.setMaximumHeight(100)
        info_layout.addRow("Changelog:", self.changelog_input)

        layout.addWidget(info_group)

        # --- Action Buttons ---
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_build = QPushButton("📦 Build")
        self.btn_build.setToolTip("Запускает build.bat (Nuitka)")
        self.btn_build.clicked.connect(self._run_build)
        btn_layout.addWidget(self.btn_build)

        self.btn_package = QPushButton("🗜 Package")
        self.btn_package.setToolTip("Запускает package.bat (ZIP)")
        self.btn_package.clicked.connect(self._run_package)
        btn_layout.addWidget(self.btn_package)

        self.btn_release = QPushButton("🚀 Release")
        self.btn_release.setToolTip("Публикует на GitHub Releases")
        self.btn_release.clicked.connect(self._run_release)
        btn_layout.addWidget(self.btn_release)

        layout.addLayout(btn_layout)

        # Full pipeline button
        self.btn_full = QPushButton("🔄 Build + Package + Release")
        self.btn_full.setObjectName("primary")
        self.btn_full.clicked.connect(self._run_full_pipeline)
        layout.addWidget(self.btn_full)

        # --- Progress ---
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(20)
        layout.addWidget(self.progress)

        # --- Log ---
        self.log = QTextEdit()
        self.log.setObjectName("log")
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

    def _log(self, text: str, color: str = "#8b949e"):
        self.log.append(f'<span style="color:{color}">{text}</span>')
        # Auto-scroll
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def _set_buttons_enabled(self, enabled: bool):
        self.btn_build.setEnabled(enabled)
        self.btn_package.setEnabled(enabled)
        self.btn_release.setEnabled(enabled)
        self.btn_full.setEnabled(enabled)

    def _validate_version(self) -> str | None:
        version = self.version_input.text().strip()
        if not re.match(r'^\d+\.\d+\.\d+$', version):
            QMessageBox.warning(self, "Ошибка", "Версия должна быть в формате X.Y.Z")
            return None
        return version

    def _validate_token(self) -> str | None:
        token = self.token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "Ошибка", "Введите GitHub Personal Access Token")
            return None
        save_token(token)
        return token

    # ─── Build ───

    def _run_build(self):
        version = self._validate_version()
        if not version:
            return

        # Update version.py
        update_version_file(version)
        self._log(f"✅ version.py → {version}", "#3fb950")

        self._set_buttons_enabled(False)
        self.progress.setValue(0)
        self._log("📦 Запуск build.bat...", "#58a6ff")

        worker = ProcessWorker(str(BUILD_SCRIPT), str(PROJECT_ROOT))
        worker.output.connect(lambda line: self._log(line))
        worker.finished_ok.connect(self._on_build_ok)
        worker.finished_error.connect(self._on_step_error)
        self._workers.append(worker)
        worker.start()

    def _on_build_ok(self):
        self.progress.setValue(33)
        self._log("✅ Build завершён!", "#3fb950")
        self._set_buttons_enabled(True)

        # If running pipeline, continue to package
        if self._pipeline_mode:
            self._run_package()

    # ─── Package ───

    def _run_package(self):
        self._set_buttons_enabled(False)
        self._log("🗜 Запуск package.bat...", "#58a6ff")

        worker = ProcessWorker(str(PACKAGE_SCRIPT), str(PROJECT_ROOT))
        worker.output.connect(lambda line: self._log(line))
        worker.finished_ok.connect(self._on_package_ok)
        worker.finished_error.connect(self._on_step_error)
        self._workers.append(worker)
        worker.start()

    def _on_package_ok(self):
        self.progress.setValue(66)
        self._log("✅ Package завершён!", "#3fb950")
        self._set_buttons_enabled(True)

        # If running pipeline, continue to release
        if self._pipeline_mode:
            self._run_release()

    # ─── Release ───

    def _run_release(self):
        version = self._validate_version()
        if not version:
            return
        token = self._validate_token()
        if not token:
            return

        if not ZIP_FILE.exists():
            QMessageBox.warning(
                self, "Ошибка",
                f"ZIP файл не найден:\n{ZIP_FILE}\n\nСначала выполните Build + Package."
            )
            return

        self._set_buttons_enabled(False)
        changelog = self.changelog_input.toPlainText().strip() or "No changelog provided"

        worker = ReleaseWorker(token, version, changelog, ZIP_FILE)
        worker.output.connect(lambda line: self._log(line, "#58a6ff"))
        worker.progress.connect(self.progress.setValue)
        worker.finished_ok.connect(self._on_release_ok)
        worker.finished_error.connect(self._on_step_error)
        self._workers.append(worker)
        worker.start()

    def _on_release_ok(self, url: str):
        self.progress.setValue(100)
        self._pipeline_mode = False
        self._log(f"🎉 Release опубликован: {url}", "#3fb950")
        self._log("═" * 50, "#30363d")
        self._set_buttons_enabled(True)

        QMessageBox.information(
            self, "Успех!",
            f"Release v{self.version_input.text()} опубликован!\n\n{url}"
        )

    # ─── Full Pipeline ───

    def _run_full_pipeline(self):
        """Build → Package → Release — all in one."""
        version = self._validate_version()
        if not version:
            return
        token = self._validate_token()
        if not token:
            return

        self._pipeline_mode = True
        self._run_build()

    # ─── Error handling ───

    _pipeline_mode = False

    def _on_step_error(self, error: str):
        self._pipeline_mode = False
        self._log(f"❌ Ошибка: {error}", "#f85149")
        self._set_buttons_enabled(True)
        self.progress.setValue(0)

    def closeEvent(self, event):
        """Сохраняем токен при выходе."""
        token = self.token_input.text().strip()
        if token:
            save_token(token)
        event.accept()


def main():
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = ReleaseManagerWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

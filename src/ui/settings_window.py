"""
Окно глобальных настроек — координаты и параметры.
Доступно из Лаунчера.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTabWidget
)
from PyQt6.QtCore import Qt

from .styles import MAIN_STYLE, COLORS
from .coordinates_tab import CoordinatesTab
from .settings_panel import SettingsPanel


class SettingsWindow(QMainWindow):
    """Окно настроек: Координаты + Настройки"""

    def __init__(self, launcher=None):
        super().__init__()
        self.launcher = launcher
        self.setWindowTitle("GBot - Настройки")
        self.resize(750, 600)
        self.setStyleSheet(MAIN_STYLE)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # === Заголовок ===
        header = QHBoxLayout()
        header.setSpacing(10)

        title = QLabel("⚙️ Настройки")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #f0f6fc;")
        header.addWidget(title)
        header.addStretch()

        if self.launcher:
            back_btn = QPushButton("← Меню")
            back_btn.setFixedSize(100, 32)
            back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            back_btn.setStyleSheet("""
                QPushButton { background: #21262d; color: #8b949e; border: 1px solid #30363d; border-radius: 6px; font-size: 13px; }
                QPushButton:hover { background: #30363d; color: #f0f6fc; }
            """)
            back_btn.clicked.connect(self._on_back)
            header.addWidget(back_btn)

        layout.addLayout(header)

        # === Вкладки ===
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; }
            QTabBar::tab {
                background: #161b22;
                color: #8b949e;
                padding: 10px 15px;
                border: 1px solid #30363d;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: #0d1117;
                color: #f0f6fc;
                border-bottom-color: #0d1117;
            }
            QTabBar::tab:hover { color: #f0f6fc; }
        """)

        # Вкладка 1: Координаты
        self.coords_tab = CoordinatesTab()
        self.tabs.addTab(self.coords_tab, "📍 Координаты")

        # Вкладка 2: Настройки
        self.settings_tab = SettingsPanel()
        self.tabs.addTab(self.settings_tab, "⚙️ Настройки")

        layout.addWidget(self.tabs, stretch=1)

    def _on_back(self):
        if self.launcher:
            self.launcher.show()
            self.hide()

    def closeEvent(self, event):
        if self.launcher:
            self.launcher.show()
        event.accept()

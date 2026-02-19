"""
GBot Auto-Updater
Проверка, скачивание и установка обновлений через GitHub Releases.
"""

import os
import sys
import json
import shutil
import zipfile
import tempfile
import subprocess
import requests
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from .version import CURRENT_VERSION, GITHUB_REPO, APP_NAME
from ..utils.logger import get_logger
from ..utils.paths import get_app_root

logger = get_logger()

# GitHub API
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
UPDATE_TEMP_DIR = Path(tempfile.gettempdir()) / "gbot_update"


def _parse_version(version_str: str) -> tuple:
    """
    Парсит строку версии 'v1.2.3' или '1.2.3' в кортеж (1, 2, 3).
    """
    v = version_str.strip().lstrip("v")
    try:
        parts = v.split(".")
        return tuple(int(p) for p in parts)
    except (ValueError, AttributeError):
        return (0, 0, 0)


def check_for_update() -> dict | None:
    """
    Проверяет наличие новой версии на GitHub Releases.
    
    Returns:
        dict с ключами {version, download_url, size, changelog} или None
    """
    try:
        logger.debug("[UPDATE] Проверка обновлений...")
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": f"{APP_NAME}/{CURRENT_VERSION}"
        }
        
        response = requests.get(GITHUB_API_URL, headers=headers, timeout=10)
        
        if response.status_code == 404:
            logger.debug("[UPDATE] Релизов пока нет")
            return None
        
        response.raise_for_status()
        data = response.json()
        
        latest_tag = data.get("tag_name", "")
        latest_version = _parse_version(latest_tag)
        current_version = _parse_version(CURRENT_VERSION)
        
        if latest_version <= current_version:
            logger.debug(f"[UPDATE] Версия актуальна ({CURRENT_VERSION})")
            return None
        
        # Ищем .zip asset
        download_url = None
        asset_size = 0
        for asset in data.get("assets", []):
            if asset["name"].lower().endswith(".zip"):
                download_url = asset["browser_download_url"]
                asset_size = asset.get("size", 0)
                break
        
        if not download_url:
            logger.warning("[UPDATE] ZIP-файл не найден в релизе")
            return None
        
        version_clean = latest_tag.lstrip("v")
        changelog = data.get("body", "Нет описания")
        
        logger.info(f"[UPDATE] Доступна новая версия: {version_clean}")
        
        return {
            "version": version_clean,
            "tag": latest_tag,
            "download_url": download_url,
            "size": asset_size,
            "changelog": changelog
        }
        
    except requests.exceptions.ConnectionError:
        logger.debug("[UPDATE] Нет подключения к интернету")
        return None
    except requests.exceptions.Timeout:
        logger.debug("[UPDATE] Таймаут при проверке обновлений")
        return None
    except Exception as e:
        logger.warning(f"[UPDATE] Ошибка проверки: {e}")
        return None


def download_update(url: str, progress_callback=None) -> Path | None:
    """
    Скачивает ZIP-файл обновления во временную папку.
    
    Args:
        url: URL для скачивания .zip
        progress_callback: Функция (downloaded_bytes, total_bytes)
    
    Returns:
        Path к скачанному файлу или None при ошибке
    """
    try:
        # Очищаем предыдущие файлы обновления
        if UPDATE_TEMP_DIR.exists():
            shutil.rmtree(UPDATE_TEMP_DIR, ignore_errors=True)
        UPDATE_TEMP_DIR.mkdir(parents=True, exist_ok=True)
        
        zip_path = UPDATE_TEMP_DIR / f"{APP_NAME}.zip"
        
        logger.debug("[UPDATE] Скачивание обновления...")
        
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        
        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0
        
        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size > 0:
                        progress_callback(downloaded, total_size)
        
        logger.debug(f"[UPDATE] Скачано: {downloaded / 1024 / 1024:.1f} MB")
        return zip_path
        
    except Exception as e:
        logger.error(f"[UPDATE] Ошибка скачивания: {e}")
        # Очистка при ошибке
        if UPDATE_TEMP_DIR.exists():
            shutil.rmtree(UPDATE_TEMP_DIR, ignore_errors=True)
        return None


def install_update(zip_path: Path) -> bool:
    """
    Распаковывает обновление и запускает скрипт замены файлов.
    Эта функция завершает текущий процесс!
    
    Args:
        zip_path: Путь к скачанному .zip
    
    Returns:
        True если скрипт запущен (приложение завершится), False при ошибке
    """
    try:
        extract_dir = UPDATE_TEMP_DIR / "extracted"
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        extract_dir.mkdir(parents=True)
        
        # Распаковка
        logger.info("[UPDATE] Распаковка обновления...")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)
        
        # Определяем папку с файлами (может быть вложенная GBot/)
        contents = list(extract_dir.iterdir())
        if len(contents) == 1 and contents[0].is_dir():
            # Архив содержит одну папку — используем её содержимое
            source_dir = contents[0]
        else:
            source_dir = extract_dir
        
        # Определяем путь приложения
        app_dir = get_app_root()
        
        # Генерируем update.bat
        bat_path = app_dir / "update.bat"
        bat_content = _generate_update_script(
            source_dir=str(source_dir),
            target_dir=str(app_dir),
            exe_name=f"{APP_NAME}.exe",
            temp_dir=str(UPDATE_TEMP_DIR)
        )
        
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
        
        logger.info("[UPDATE] Запуск обновления, приложение перезапустится...")
        
        # Запускаем bat без отображения консоли
        subprocess.Popen(
            ["cmd.exe", "/c", str(bat_path)],
            creationflags=subprocess.CREATE_NO_WINDOW,
            close_fds=True
        )
        
        # Завершаем приложение
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"[UPDATE] Ошибка установки: {e}")
        return False


def _generate_update_script(source_dir: str, target_dir: str, exe_name: str, temp_dir: str) -> str:
    """
    Генерирует содержимое update.bat для замены файлов.
    Скрипт:
    1. Ждёт завершения GBot.exe
    2. Копирует новые файлы (кроме config/, data/, logs/)
    3. Очищает временные файлы
    4. Перезапускает приложение
    5. Самоудаляется
    """
    return f"""@echo off
chcp 65001 >nul
echo ══════════════════════════════════════════
echo   GBot — Установка обновления
echo ══════════════════════════════════════════

echo Ожидание завершения GBot...
timeout /t 3 /nobreak >nul

:: Принудительно завершить если ещё работает
taskkill /IM {exe_name} /F >nul 2>&1
timeout /t 2 /nobreak >nul

echo Копирование новых файлов...

:: Копируем всё, КРОМЕ config, data, logs
:: /E — все подпапки, /XD — исключить директории
robocopy "{source_dir}" "{target_dir}" /E /XD config data logs /NFL /NDL /NJH /NJS /R:3 /W:2

if errorlevel 8 (
    echo ❌ Ошибка при копировании файлов!
    echo    Старая версия должна быть работоспособна.
    pause
    goto :cleanup
)

echo ✅ Файлы обновлены!

:cleanup
echo Очистка временных файлов...
rd /s /q "{temp_dir}" >nul 2>&1

echo Запуск GBot...
start "" "{target_dir}\\{exe_name}"

echo Обновление завершено!
timeout /t 2 /nobreak >nul

:: Самоудаление
(goto) 2>nul & del "%~f0"
"""


class UpdateCheckWorker(QThread):
    """
    Фоновый поток для проверки обновлений.
    Не блокирует UI.
    """
    update_available = pyqtSignal(dict)   # Сигнал: найдено обновление
    no_update = pyqtSignal()               # Сигнал: обновлений нет
    check_error = pyqtSignal(str)          # Сигнал: ошибка
    
    def run(self):
        try:
            result = check_for_update()
            if result:
                self.update_available.emit(result)
            else:
                self.no_update.emit()
        except Exception as e:
            self.check_error.emit(str(e))


class UpdateDownloadWorker(QThread):
    """
    Фоновый поток для скачивания и установки обновления.
    """
    progress = pyqtSignal(int, int)         # (downloaded, total)
    download_complete = pyqtSignal(object)   # Path к zip
    download_error = pyqtSignal(str)         # Ошибка
    
    def __init__(self, download_url: str):
        super().__init__()
        self.download_url = download_url
    
    def run(self):
        try:
            def on_progress(downloaded, total):
                self.progress.emit(downloaded, total)
            
            zip_path = download_update(self.download_url, on_progress)
            
            if zip_path:
                self.download_complete.emit(zip_path)
            else:
                self.download_error.emit("Не удалось скачать обновление")
                
        except Exception as e:
            self.download_error.emit(str(e))

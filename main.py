"""
Albion Market Bot v3.0 - Entry Point

Точка входа приложения.
"""

import sys
import logging
from pathlib import Path

# Настройка логирования
LOG_FILE = Path(__file__).parent / "logs" / "app.log"
LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Главная функция запуска."""
    logger.info("Starting Albion Market Bot v3.0")
    
    try:
        # Проверка PyQt6
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
    except ImportError:
        print("ERROR: PyQt6 не установлен!")
        print("Установите: pip install PyQt6")
        sys.exit(1)
    
    # Проверка окружения
    from config import validate_environment, TESSERACT_PATH
    
    errors = validate_environment()
    if errors:
        for error in errors:
            logger.warning(f"Environment issue: {error}")
    
    if TESSERACT_PATH:
        logger.info(f"Tesseract found: {TESSERACT_PATH}")
    else:
        logger.warning("Tesseract not found!")
    
    # Запуск GUI
    from gui.main_window import run_app
    
    exit_code = run_app()
    
    logger.info(f"Application closed with code: {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

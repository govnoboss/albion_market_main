"""
Albion Market Scanner & Buyer
Точка входа приложения
"""

import sys
import os

# Fix for QFont point size error on HighDPI displays
os.environ["QT_FONT_DPI"] = "96"

# Добавляем корневую папку проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from src.ui.launcher import LauncherWindow

def run_app():
    """Запуск приложения"""
    app = QApplication(sys.argv)
    
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Запускаем Лаунчер
    # Он сам решит, показать себя или окно входа
    _ = LauncherWindow()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    run_app()

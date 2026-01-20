"""
Albion Market Scanner & Buyer
Точка входа приложения
"""

import sys
import os

# Добавляем корневую папку проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui.main_window import run_app


if __name__ == "__main__":
    run_app()

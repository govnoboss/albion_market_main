"""
 Scanner & Buyer
Точка входа приложения
"""

import sys
import os

# Fix for QFont point size error on HighDPI displays
os.environ["QT_FONT_DPI"] = "96"

# Добавляем корневую папку проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QFont
    from src.ui.launcher import LauncherWindow
except Exception as e:
    import traceback
    sys.stderr.write(f"CRASH during imports: {e}\n")
    sys.stderr.write(traceback.format_exc())
    sys.stderr.flush()
    input("Press Enter to exit (Import Error)...")
    sys.exit(1)

def run_app():
    """Запуск приложения"""
    try:
        app = QApplication(sys.argv)
    except Exception as e:
        sys.stderr.write(f"CRASH: QApplication init failed: {e}\n")
        sys.stderr.flush()
        raise e
    
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    try:
        # Запускаем Лаунчер
        # Он сам решит, показать себя или окно входа
        _ = LauncherWindow()
    except Exception as e:
        sys.stderr.write(f"CRASH: LauncherWindow init failed: {e}\n")
        sys.stderr.flush()
        raise e
    
    sys.exit(app.exec())

if __name__ == "__main__":
    try:
        run_app()
    except Exception as e:
        import traceback
        sys.stderr.write(traceback.format_exc())
        sys.stderr.write(f"CRASH: {e}\n")
        sys.stderr.flush()
        input("Press Enter to exit...")

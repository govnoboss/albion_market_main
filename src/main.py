"""
 Scanner & Buyer
Точка входа приложения
"""

import sys
import os
import ctypes

# Fix for QFont point size error on HighDPI displays
os.environ["QT_FONT_DPI"] = "96"

# Set AppUserModelID for Windows Taskbar Icon
try:
    myappid = 'govnoboss.albionmarket.scanner.v1' # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass

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
    
    # --- Set Application Icon ---
    from PyQt6.QtGui import QIcon
    icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    # ---------------------------

    try:
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

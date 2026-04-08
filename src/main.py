"""
 Scanner & Buyer
Точка входа приложения
"""

import time
_t0 = time.perf_counter()  # Самый ранний момент

import sys
import os
import ctypes
def critical_error_handler(exc_type, exc_value, exc_traceback):
    """Перехватчик всех необработанных исключений"""
    # Не логируем прерывание клавиатурой (Ctrl+C)
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    
    # Формируем имя файла с датой
    log_filename = f"crash_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(log_filename, "w", encoding="utf-8") as f:
        f.write("=== GBOT CRASH REPORT ===\n")
        f.write(f"Time: {datetime.now()}\n")
        f.write(f"Version: 1.2.0\n") # Можешь брать из своего version.py
        f.write("-" * 30 + "\n")
        f.write(error_msg)

    # Если PyQt6 уже загружен, можно попробовать показать красивое окно
    try:
        from PyQt6.QtWidgets import QMessageBox, QApplication
        if QApplication.instance():
            QMessageBox.critical(None, "Критическая ошибка", 
                               f"Программа завершила работу из-за ошибки.\nОтчет создан: {log_filename}")
    except:
        pass

# Устанавливаем глобальный перехватчик
sys.excepthook = critical_error_handler
# Очищаем системные переменные, чтобы избежать конфликта с другими Qt-программами на ПК пользователя
os.environ.pop("QT_PLUGIN_PATH", None)
os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)

if getattr(sys, 'frozen', False) or hasattr(sys, '__compiled__'):
    app_dir = os.path.dirname(sys.executable)

    # Nuitka может класть Qt-плагины в разные места — ищем первый существующий
    _candidate_plugin_dirs = [
        os.path.join(app_dir, "PyQt6", "Qt6", "plugins"),
        os.path.join(app_dir, "qt6_plugins"),
        os.path.join(app_dir, "PyQt6", "plugins"),
        os.path.join(app_dir, "plugins"),
    ]
    for _p in _candidate_plugin_dirs:
        if os.path.isdir(_p) and os.path.isdir(os.path.join(_p, "platforms")):
            os.environ["QT_PLUGIN_PATH"] = _p
            # Дублируем на уровне конкретной платформы — наиболее надёжный вариант
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(_p, "platforms")
            break

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

# --- Startup Profiler ---
from src.utils.startup_profiler import get_startup_profiler
profiler = get_startup_profiler()
profiler._t0 = _t0  # Устанавливаем самый ранний момент
profiler.start("total")
profiler.mark("python_ready")

# --- PyQt6 Imports ---
profiler.start("pyqt_imports")
try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QFont
    profiler.end("pyqt_imports")
except Exception as e:
    profiler.end("pyqt_imports")
    import traceback
    sys.stderr.write(f"CRASH during imports: {e}\n")
    sys.stderr.write(traceback.format_exc())
    sys.stderr.flush()
    input("Press Enter to exit (Import Error)...")
    sys.exit(1)

# --- Launcher Import ---
profiler.start("import_launcher")
try:
    from src.ui.launcher import LauncherWindow
    profiler.end("import_launcher")
except Exception as e:
    profiler.end("import_launcher")
    import traceback
    sys.stderr.write(f"CRASH during imports: {e}\n")
    sys.stderr.write(traceback.format_exc())
    sys.stderr.flush()
    input("Press Enter to exit (Import Error)...")
    sys.exit(1)

def run_app():
    """Запуск приложения"""
    profiler.start("qapp_init")
    try:
        app = QApplication(sys.argv)
    except Exception as e:
        profiler.end("qapp_init")
        _exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) or hasattr(sys, '__compiled__') else 'dev mode'
        sys.stderr.write(f"CRASH: QApplication init failed: {e}\n")
        sys.stderr.write(f"  App dir:                    {_exe_dir}\n")
        sys.stderr.write(f"  QT_PLUGIN_PATH:             {os.environ.get('QT_PLUGIN_PATH', 'NOT SET')}\n")
        sys.stderr.write(f"  QT_QPA_PLATFORM_PLUGIN_PATH:{os.environ.get('QT_QPA_PLATFORM_PLUGIN_PATH', 'NOT SET')}\n")
        sys.stderr.flush()
        raise e
    profiler.end("qapp_init")
    
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # --- Initialize Localization ---
    from src.utils.config import get_config
    from src.utils.localization import set_language
    lang = get_config().get_setting("language", "en")
    set_language(lang)
    # ------------------------------
    
    # --- Set Application Icon ---
    from PyQt6.QtGui import QIcon
    icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    # ---------------------------

    profiler.start("launcher_init")
    try:
        launcher = LauncherWindow()
    except Exception as e:
        profiler.end("launcher_init")
        sys.stderr.write(f"CRASH: LauncherWindow init failed: {e}\n")
        sys.stderr.flush()
        raise e
    profiler.end("launcher_init")
    
    # --- Финальный отчёт ---
    profiler.end("total")
    profiler.report()
    
    # Prevent app from quitting when Launcher closes before Dashboard is ready
    app.setQuitOnLastWindowClosed(False)
    
    exit_code = app.exec()
    sys.exit(exit_code)

if __name__ == "__main__":
    try:
        run_app()
    except Exception as e:
        import traceback
        sys.stderr.write(traceback.format_exc())
        sys.stderr.write(f"CRASH: {e}\n")
        sys.stderr.flush()
        input("Press Enter to exit...")

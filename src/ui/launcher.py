from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QApplication, QMessageBox,
    QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QFont, QIcon, QDesktopServices

from .styles import MAIN_STYLE, COLORS
from ..utils.logger import get_logger
from ..utils.startup_profiler import get_startup_profiler

logger = get_logger()
from .splash_screen import SplashScreen
from ..core.license import license_manager
from ..core.version import CURRENT_VERSION
from ..core.updater import UpdateCheckWorker, UpdateDownloadWorker, install_update


class LauncherWindow(QMainWindow):
    """
    Точка входа UI: проверка лицензии → SplashScreen → Dashboard.
    """
    
    def __init__(self):
        super().__init__()
        _profiler = get_startup_profiler()
        
        # --- Splash Screen ---
        _profiler.start("splash_init")
        self.splash = SplashScreen()
        self.splash.show()
        self.splash.set_progress(10)
        self.splash.set_status("Проверка лицензии...")
        QApplication.processEvents()
        _profiler.end("splash_init")
        
        # --- License Check ---
        self.login_window = None
        self.license_expires = None

        _profiler.start("license_check")
        if not self._check_license_silent():
            _profiler.end("license_check")
            # Show Login Window instead of Dashboard
            self.splash.close()
            from .login_window import LoginWindow
            self.login_window = LoginWindow(on_success_callback=self._show_dashboard)
            self.login_window.show()
            return
        _profiler.end("license_check")

        self._show_dashboard()
        
        # Only show launcher if dashboard didn't open
        if not hasattr(self, 'dashboard') or not self.dashboard.isVisible():
            self.show()
            self._force_foreground()

    def _force_foreground(self):
        """Принудительно вывести окно на передний план (Windows workaround)"""
        flags = self.windowFlags()
        self.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
        self.show()
        
        def _remove_top_hint():
            self.setWindowFlags(flags)
            self.show()
            self.activateWindow()
        
        QTimer.singleShot(500, _remove_top_hint)

    def _check_license_silent(self):
        """Silently checks if we have a stored valid key"""
        res = license_manager.validate_key()
        if res.get('success'):
            license_manager.mark_checked()
            self.license_expires = res.get('expires')
        return res.get('success', False)

    def _show_dashboard(self):
        """Вызывается после успешного входа или валидации"""
        _profiler = get_startup_profiler()
        
        if hasattr(self, 'splash') and self.splash.isVisible():
            self.splash.set_status("Запуск Dashboard...")
            self.splash.set_progress(20)
            QApplication.processEvents()
        
        _profiler.start("import_dashboard")
        from .dashboard import MainDashboard
        _profiler.end("import_dashboard")
        
        _profiler.start("dashboard_init")
        self.dashboard = MainDashboard(
            splash=getattr(self, 'splash', None),
            license_expires=self.license_expires
        )
        _profiler.end("dashboard_init")
        self.dashboard.show()
        
        self.close()

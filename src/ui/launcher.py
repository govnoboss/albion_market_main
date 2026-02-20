from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QApplication, QMessageBox,
    QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QFont, QIcon, QDesktopServices
import sys
import webbrowser

# --- CONTACT LINKS ---
LINK_TELEGRAM = "https://t.me/nobrainchel" 
LINK_DISCORD = "https://discordapp.com/users/dendidima228" 

from .styles import MAIN_STYLE, COLORS
from ..utils.logger import get_logger

logger = get_logger()
from .splash_screen import SplashScreen
from ..core.license import license_manager
from ..core.version import CURRENT_VERSION
from ..core.updater import UpdateCheckWorker, UpdateDownloadWorker, install_update

class LauncherWindow(QMainWindow):
    """
    Главное меню (Launcher) для выбора режима работы:
    1. SCANNER (Сбор данных)
    2. BUYER (Автоматическая закупка)
    """
    
    def __init__(self):
        super().__init__()
        # --- Splash Screen ---
        self.splash = SplashScreen()
        self.splash.show()
        self.splash.set_progress(10)
        self.splash.set_status("Проверка лицензии...")
        QApplication.processEvents()
        
        # --- License Check ---
        self.login_window = None
        self.shutdown_timer = None
        self.shutdown_seconds = 60

        if not self._check_license_silent():
            # Show Login Window instead of Launcher
            self.splash.close()
            from .login_window import LoginWindow
            self.login_window = LoginWindow(on_success_callback=self._show_launcher)
            self.login_window.show()
            return

        self._init_launcher_ui()
        self._setup_daily_license_check()
        self.splash.close()
        
        # Only show launcher if we didn't already transition to Dashboard
        if not hasattr(self, 'dashboard') or not self.dashboard.isVisible():
            self.show()
            self._force_foreground()

    def _force_foreground(self):
        """Принудительно вывести окно на передний план (Windows workaround)"""
        # Windows блокирует фоновым приложениям захват фокуса.
        # Временно ставим WindowStaysOnTopHint, потом убираем.
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
        res = license_manager.validate_key() # Load from file
        if res.get('success'):
            license_manager.mark_checked()
            # STORE Expiry Date
            self.license_expires = res.get('expires')
        return res.get('success', False)
    
    def _setup_daily_license_check(self):
        """Setup timer for daily license validation"""
        # Check every 10 minutes if we need to validate today
        self.license_check_timer = QTimer(self)
        self.license_check_timer.timeout.connect(self._daily_license_check)
        self.license_check_timer.start(10 * 60 * 1000)  # 10 minutes
    
    def _daily_license_check(self):
        """Perform daily license check"""
        if not license_manager.should_check_today():
            return  # Already checked today
        
        res = license_manager.validate_key()
        if res.get('success'):
            license_manager.mark_checked()
        else:
            self._start_graceful_shutdown(res.get('message', 'License expired'))
    
    def _start_graceful_shutdown(self, reason: str):
        """Start 1-minute graceful shutdown with warning"""
        self.shutdown_seconds = 60
        
        # Create warning dialog
        self.shutdown_dialog = QMessageBox(self)
        self.shutdown_dialog.setIcon(QMessageBox.Icon.Warning)
        self.shutdown_dialog.setWindowTitle("Лицензия недействительна")
        self.shutdown_dialog.setText(f"Причина: {reason}\n\nПриложение закроется через 60 секунд.\nСохраните свою работу.")
        self.shutdown_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        self.shutdown_dialog.button(QMessageBox.StandardButton.Ok).setText("Понятно")
        self.shutdown_dialog.show()
        
        # Start countdown timer
        self.shutdown_timer = QTimer(self)
        self.shutdown_timer.timeout.connect(self._shutdown_tick)
        self.shutdown_timer.start(1000)  # Every second
    
    def _shutdown_tick(self):
        """Update shutdown countdown"""
        self.shutdown_seconds -= 1
        
        if self.shutdown_seconds <= 0:
            self.shutdown_timer.stop()
            QApplication.quit()
        elif self.shutdown_dialog and self.shutdown_dialog.isVisible():
            self.shutdown_dialog.setText(
                f"Приложение закроется через {self.shutdown_seconds} секунд.\n"
                f"Сохраните свою работу."
            )

    def _show_launcher(self):
        """Вызывается после успешного входа или валидации"""
        if hasattr(self, 'splash') and self.splash.isVisible():
            self.splash.set_status("Запуск Dashboard...")
            self.splash.set_progress(90)
            QApplication.processEvents()
            self.splash.close()
            
        from .dashboard import MainDashboard
        self.dashboard = MainDashboard()
        self.dashboard.show()
        
        self.close() 

    def _init_launcher_ui(self):
        """Переход к Dashboard"""
        self._show_launcher()

    def _preload_windows(self):
        """Устарело, окна теперь встроенные виджеты"""
        pass

    def _check_for_updates(self):
        """Фоновая проверка обновлений (теперь в Dashboard или тут)"""
        pass

    def _update_license_display(self):
        """Updates the license label text and color"""
        if not hasattr(self, 'license_expires'):
            self.license_lbl.setText("Ситус лицензии: Неизвестно")
            self.license_lbl.setStyleSheet("color: #8b949e; font-size: 12px;")
            return

        try:
            from datetime import datetime
            # Parse expiry (Format: 2026-03-01 12:00:00 or similar from server)
            # Server sends: str(license_obj.expires_at) which is typically ISO-like 'YYYY-MM-DD HH:MM:SS.ms'
            expires_str = self.license_expires.split('.')[0] # Remove potential microseconds
            expires_at = datetime.fromisoformat(expires_str)
            now = datetime.now()
            
            delta = expires_at - now
            days_left = delta.days
            
            # Format display
            date_display = expires_at.strftime("%d.%m.%Y")
            
            if days_left < 0:
                text = f"ЛИЦЕНЗИЯ ИСТЕКЛА ({date_display})"
                color = "#da3633" # Red
            elif days_left < 3:
                text = f"Лицензия активна до: {date_display} (Осталось: {days_left} дн.) ⚠️"
                color = "#d29922" # Yellow/Orange
            else:
                text = f"Лицензия активна до: {date_display} (Осталось: {days_left} дн.)"
                color = "#3fb950" # Green
                
            self.license_lbl.setText(text)
            self.license_lbl.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold;")
            
        except Exception as e:
            logger.error(f"Error parsing date: {e}")
            self.license_lbl.setText(f"Лицензия активна: {self.license_expires}")
            self.license_lbl.setStyleSheet("color: #3fb950; font-size: 12px;")


    def _create_mode_button(self, title, desc, color):
        btn = QPushButton()
        btn.setMinimumHeight(100)
        btn.setSizePolicy(
            btn.sizePolicy().horizontalPolicy().Expanding,
            btn.sizePolicy().verticalPolicy().Expanding
        )
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #161b22;
                border: 2px solid {COLORS['border']};
                border-radius: 12px;
                text-align: center;
                padding: 20px;
            }}
            QPushButton:hover {{
                border-color: {color};
                background-color: #21262d;
            }}
        """)
        
        # Компонуем текст внутри кнопки (вертикально)
        btn_layout = QVBoxLayout(btn)
        
        lbl_title = QLabel(title)
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {color}; border: none; background: transparent;")
        
        lbl_desc = QLabel(desc)
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_desc.setStyleSheet("font-size: 12px; color: #8b949e; border: none; background: transparent;")
        
        btn_layout.addWidget(lbl_title)
        btn_layout.addWidget(lbl_desc)
        
        return btn
    
    def _preload_windows(self):
        """Предзагрузка окон для быстрого переключения"""
        if not hasattr(self, 'splash') or not self.splash:
            return

        self.splash.set_status("Загрузка Сканера...")
        self.splash.set_progress(30)
        QApplication.processEvents()
        
        # Ленивые импорты (тяжёлые модули)
        try:
            from .main_window import MainWindow as ScannerWindow
            self.scanner_window = ScannerWindow(launcher=self)
        except Exception as e:
            sys.stderr.write(f"ERROR initializing ScannerWindow: {e}\n"); sys.stderr.flush()
            import traceback
            traceback.print_exc()
            raise e
        
        self.splash.set_status("Загрузка Закупщика...")
        self.splash.set_progress(60)
        QApplication.processEvents()
            
        from .buyer_window import BuyerWindow
        self.buyer_window = BuyerWindow(launcher=self)
        
        self.splash.set_status("Загрузка Настроек...")
        self.splash.set_progress(75)
        QApplication.processEvents()
        
        from .settings_window import SettingsWindow
        self.settings_window = SettingsWindow(launcher=self)
        
        self.splash.set_status("Загрузка Финансов...")
        self.splash.set_progress(85)
        QApplication.processEvents()
        
        from .finance_window import FinanceWindow
        self.finance_window = FinanceWindow(launcher=self)
        
        self.splash.set_progress(95)
        self.splash.set_status("Подготовка...")
        QApplication.processEvents()

        # Small delay for visual consistency
        import time
        time.sleep(0.5)
        
        self.splash.set_progress(100)
        self.splash.set_status("Готово!")
        QApplication.processEvents()
        
        self.splash.close()

    def _launch_scanner(self):
        self.scanner_window.show()
        self.hide()

    def _launch_buyer(self):
        self.buyer_window.show()
        self.hide()

    def _launch_settings(self):
        self.settings_window.show()
        self.hide()

    def _launch_finance(self):
        if hasattr(self, 'finance_window') and self.finance_window:
            self.finance_window.show()
            self.hide()

    # ── Auto-Update ──────────────────────────────────────

    def _check_for_updates(self):
        """Запускает фоновую проверку обновлений"""
        self._update_info = None
        self._update_worker = UpdateCheckWorker()
        self._update_worker.update_available.connect(self._on_update_available)
        self._update_worker.no_update.connect(lambda: None)  # Тихо
        self._update_worker.check_error.connect(lambda e: None)  # Тихо
        self._update_worker.start()

    def _on_update_available(self, info: dict):
        """Вызывается когда найдена новая версия"""
        self._update_info = info
        # Подчеркиваем текст, чтобы показать интерактивность
        self.update_lbl.setText(f"<u>Доступна версия {info['version']}</u>")
        
        # Список изменений в подсказку текста
        changelog = info.get('changelog', 'Нет описания изменений')
        # Делаем текст подсказки чисто белым
        tooltip_text = f"<div style='color: #ffffff;'><b>Что нового в v{info['version']}:</b><br><br>{changelog.replace('\n', '<br>')}</div>"
        
        self.update_lbl.setToolTip(tooltip_text)
        self.update_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_update.setToolTip("") # Убеждаемся, что на кнопке нет дубликата
        
        self.update_frame.show()

    def _start_update_download(self):
        """Начинает скачивание обновления"""
        if not self._update_info:
            return

        self.btn_update.setEnabled(False)
        self.btn_update.setText("Скачивание...")
        self.update_progress.setValue(0)
        self.update_progress.show()

        self._download_worker = UpdateDownloadWorker(self._update_info["download_url"])
        self._download_worker.progress.connect(self._on_download_progress)
        self._download_worker.download_complete.connect(self._on_download_complete)
        self._download_worker.download_error.connect(self._on_download_error)
        self._download_worker.start()

    def _on_download_progress(self, downloaded: int, total: int):
        """Обновление прогресс-бара скачивания"""
        if total > 0:
            percent = int(downloaded * 100 / total)
            self.update_progress.setValue(percent)
            mb_done = downloaded / 1024 / 1024
            mb_total = total / 1024 / 1024
            self.update_lbl.setText(f"Скачивание: {mb_done:.1f} / {mb_total:.1f} MB")

    def _on_download_complete(self, zip_path):
        """Скачивание завершено — устанавливаем"""
        self.update_lbl.setText("Установка обновления...")
        self.update_progress.setValue(100)
        QApplication.processEvents()

        # install_update() завершит приложение (sys.exit)
        install_update(zip_path)

    def _on_download_error(self, error: str):
        """Ошибка скачивания"""
        self.btn_update.setEnabled(True)
        self.btn_update.setText("🔄 Повторить")
        self.update_progress.hide()
        self.update_lbl.setText(f"Ошибка: {error}")
        self.update_lbl.setStyleSheet("color: #f85149; font-size: 13px; border: none;")

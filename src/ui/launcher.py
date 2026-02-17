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
        self.show()

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
        """Called when login is successful"""
        # Show splash screen during preloading
        if not self.splash.isVisible():
            self.splash.show()
        
        self.splash.set_progress(10)
        self.splash.set_status("Активация лицензии...")
        QApplication.processEvents()

        # Force re-check to get fresh expiry data
        self._check_license_silent()
        
        self.splash.set_progress(20)
        self.splash.set_status("Загрузка интерфейса...")
        QApplication.processEvents()

        self._init_launcher_ui()
        
        # SplashScreen is closed at the end of _preload_windows (called inside _init_launcher_ui)
        self.show()

    def _init_launcher_ui(self):
        self.setWindowTitle("GBot Launcher")
        self.resize(600, 530)
        self.setStyleSheet(MAIN_STYLE)
        
        # Центрирование окна (если возможно)
        # self.setGeometry(100, 100, 600, 400)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 30, 40, 30)
        
        # Заголовок
        title_lbl = QLabel("GBOT Albion")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet("font-size: 28px; font-weight: bold; color: #f0f6fc;")
        layout.addWidget(title_lbl)
        
        subtitle_lbl = QLabel("Выберите режим работы")
        subtitle_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_lbl.setStyleSheet("font-size: 14px; color: #8b949e;")
        layout.addWidget(subtitle_lbl)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)
        
        # SCANNNER
        self.btn_scanner = self._create_mode_button(
            "🔍 СКАНЕР", 
            "Сбор цен и анализ рынка", 
            "#1f6feb"
        )
        self.btn_scanner.clicked.connect(self._launch_scanner)
        btn_layout.addWidget(self.btn_scanner)
        
        # BUYER
        self.btn_buyer = self._create_mode_button(
            "🛒 ЗАКУПЩИК", 
            "Автоматическая покупка\nпо выгодным ценам", 
            "#238636"
        )
        self.btn_buyer.clicked.connect(self._launch_buyer)
        btn_layout.addWidget(self.btn_buyer)
        
        layout.addLayout(btn_layout)

        # Кнопка Настройки (по центру, под режимами)
        self.btn_settings = QPushButton()
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.setStyleSheet(f"""
            QPushButton {{
                background-color: #161b22;
                border: 2px solid {COLORS['border']};
                border-radius: 10px;
                padding: 12px 20px;
            }}
            QPushButton:hover {{
                border-color: #8b949e;
                background-color: #21262d;
            }}
        """)
        settings_btn_layout = QHBoxLayout(self.btn_settings)
        settings_icon = QLabel("⚙️ НАСТРОЙКИ")
        settings_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        settings_icon.setStyleSheet("font-size: 15px; font-weight: bold; color: #8b949e; border: none; background: transparent;")
        settings_btn_layout.addWidget(settings_icon)
        self.btn_settings.clicked.connect(self._launch_settings)
        layout.addWidget(self.btn_settings)

        layout.addStretch()

        # --- Update Banner (скрыт по умолчанию) ---
        self.update_frame = QFrame()
        self.update_frame.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border: 1px solid #1f6feb;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        update_inner = QVBoxLayout(self.update_frame)
        update_inner.setSpacing(8)
        update_inner.setContentsMargins(12, 8, 12, 8)

        # Первая строка: текст + кнопка
        update_top = QHBoxLayout()
        self.update_lbl = QLabel("")
        self.update_lbl.setStyleSheet("color: #58a6ff; font-size: 13px; border: none;")
        update_top.addWidget(self.update_lbl)
        update_top.addStretch()

        self.btn_update = QPushButton("🔄 Обновить")
        self.btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_update.setStyleSheet("""
            QPushButton {
                background-color: #1f6feb;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                color: #ffffff;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #388bfd;
            }
            QPushButton:disabled {
                background-color: #21262d;
                color: #484f58;
            }
        """)
        self.btn_update.clicked.connect(self._start_update_download)
        update_top.addWidget(self.btn_update)
        update_inner.addLayout(update_top)

        # Прогресс-бар (скрыт до скачивания)
        self.update_progress = QProgressBar()
        self.update_progress.setRange(0, 100)
        self.update_progress.setValue(0)
        self.update_progress.setFixedHeight(6)
        self.update_progress.setTextVisible(False)
        self.update_progress.setStyleSheet("""
            QProgressBar {
                background-color: #21262d;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #1f6feb;
                border-radius: 3px;
            }
        """)
        self.update_progress.hide()
        update_inner.addWidget(self.update_progress)

        self.update_frame.hide()  # Скрыт до обнаружения обновления
        layout.addWidget(self.update_frame)

        # --- License Info Footer ---
        footer_layout = QVBoxLayout()
        footer_layout.setSpacing(5)

        self.license_lbl = QLabel()
        self.license_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_license_display()
        footer_layout.addWidget(self.license_lbl)

        version_lbl = QLabel(f"v{CURRENT_VERSION}")
        version_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_lbl.setStyleSheet("color: #30363d; font-size: 11px;")
        footer_layout.addWidget(version_lbl)

        layout.addLayout(footer_layout)

        # --- Contacts (Footer) ---
        contacts_layout = QHBoxLayout()
        contacts_layout.setSpacing(15)
        contacts_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Telegram
        btn_tg = QPushButton("Telegram")
        btn_tg.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_tg.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #24A1DE;
                border: 1px solid #24A1DE;
                border-radius: 15px;
                padding: 5px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #24A1DE;
                color: white;
            }
        """)
        btn_tg.clicked.connect(lambda: webbrowser.open(LINK_TELEGRAM))
        contacts_layout.addWidget(btn_tg)

        # Discord
        btn_ds = QPushButton("Discord")
        btn_ds.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ds.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #5865F2;
                border: 1px solid #5865F2;
                border-radius: 15px;
                padding: 5px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5865F2;
                color: white;
            }
        """)
        btn_ds.clicked.connect(lambda: webbrowser.open(LINK_DISCORD))
        contacts_layout.addWidget(btn_ds)

        layout.addLayout(contacts_layout)


        # Предзагрузка окон для быстрого переключения
        self._preload_windows()

        # Фоновая проверка обновлений
        self._check_for_updates()

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
            print(f"Error parsing date: {e}")
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
        sys.stderr.write("DEBUG: Importing ScannerWindow...\n"); sys.stderr.flush()
        try:
            from .main_window import MainWindow as ScannerWindow
            sys.stderr.write("DEBUG: ScannerWindow imported. Initializing...\n"); sys.stderr.flush()
            self.scanner_window = ScannerWindow(launcher=self)
            sys.stderr.write("DEBUG: ScannerWindow initialized.\n"); sys.stderr.flush()
        except Exception as e:
            sys.stderr.write(f"ERROR initializing ScannerWindow: {e}\n"); sys.stderr.flush()
            import traceback
            traceback.print_exc()
            raise e
        
        self.splash.set_status("Загрузка Закупщика...")
        self.splash.set_progress(60)
        QApplication.processEvents()
            
        sys.stderr.write("DEBUG: Importing BuyerWindow...\n"); sys.stderr.flush()
        from .buyer_window import BuyerWindow
        self.buyer_window = BuyerWindow(launcher=self)
        sys.stderr.write("DEBUG: BuyerWindow initialized.\n"); sys.stderr.flush()
        
        self.splash.set_status("Загрузка Настроек...")
        self.splash.set_progress(75)
        QApplication.processEvents()
        
        from .settings_window import SettingsWindow
        self.settings_window = SettingsWindow(launcher=self)
        
        self.splash.set_progress(90)
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
        self.update_lbl.setText(f"Доступна версия {info['version']}")
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

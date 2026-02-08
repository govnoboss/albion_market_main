from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFrame, QApplication, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon


from .styles import MAIN_STYLE, COLORS
from .splash_screen import SplashScreen
from ..core.license import license_manager

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
        self._init_launcher_ui()
        self.show()

    def _init_launcher_ui(self):
        self.setWindowTitle("GBot - Launcher")
        self.setWindowTitle("GBot Launcher")
        self.resize(600, 400)
        self.setStyleSheet(MAIN_STYLE)
        
        # Центрирование окна (если возможно)
        # self.setGeometry(100, 100, 600, 400)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(30)
        layout.setContentsMargins(40, 40, 40, 40)
        
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
        layout.addStretch()
        
        # Footer
        footer = QLabel("v2.0 • 2026")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #30363d;")
        layout.addWidget(footer)
        
        # Предзагрузка окон для быстрого переключения
        self._preload_windows()

    def _create_mode_button(self, title, desc, color):
        btn = QPushButton()
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
        # Статус в splash (проверяем, что splash существует и не закрыт)
        if hasattr(self, 'splash') and self.splash and self.splash.isVisible():
            self.splash.set_progress(0)
            self.splash.set_status("Загрузка Сканера...")
            self.splash.set_progress(25)
        
        # Ленивые импорты (тяжёлые модули)
        from .main_window import MainWindow as ScannerWindow
        self.scanner_window = ScannerWindow(launcher=self)
        
        if hasattr(self, 'splash') and self.splash and self.splash.isVisible():
            self.splash.set_progress(50)
            self.splash.set_status("Загрузка Закупщика...")
            self.splash.set_progress(75)
            
        from .buyer_window import BuyerWindow
        self.buyer_window = BuyerWindow(launcher=self)
        
        if hasattr(self, 'splash') and self.splash and self.splash.isVisible():
            self.splash.set_progress(100)
            self.splash.set_status("Готово!")

    def _launch_scanner(self):
        self.scanner_window.show()
        self.hide()
        
    def _launch_buyer(self):
        self.buyer_window.show()
        self.hide()


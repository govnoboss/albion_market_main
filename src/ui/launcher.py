from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFrame, QApplication
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
        self.splash.set_status("Проверка лицензии...")
        QApplication.processEvents()
        
        # --- License Check ---
        self.login_window = None

        if not self._check_license_silent():
            # Show Login Window instead of Launcher
            self.splash.close()
            from .login_window import LoginWindow
            self.login_window = LoginWindow(on_success_callback=self._show_launcher)
            self.login_window.show()
            return

        self._init_launcher_ui()
        self.splash.close()
        self.show()

    def _check_license_silent(self):
        """Silently checks if we have a stored valid key"""
        res = license_manager.validate_key() # Load from file
        return res.get('success', False)

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
        # Статус в splash
        self.splash.set_status("Загрузка Сканера...")
        
        # Ленивые импорты (тяжёлые модули)
        from .main_window import MainWindow as ScannerWindow
        self.scanner_window = ScannerWindow(launcher=self)
        
        self.splash.set_status("Загрузка Закупщика...")
        from .buyer_window import BuyerWindow
        self.buyer_window = BuyerWindow(launcher=self)

    def _launch_scanner(self):
        self.scanner_window.show()
        self.hide()
        
    def _launch_buyer(self):
        self.buyer_window.show()
        self.hide()


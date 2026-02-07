"""
Окно загрузки (Splash Screen) для GBot
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class SplashScreen(QWidget):
    """Окно загрузки приложения"""
    
    def __init__(self):
        super().__init__()
        self._setup_window()
        self._setup_ui()
        
    def _setup_window(self):
        """Настройка окна"""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(300, 150)
        self.setStyleSheet("background-color: #0d1117;")
        
        # Центрируем на экране
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        
    def _setup_ui(self):
        """Создание интерфейса"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Заголовок
        title = QLabel("GBot")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #58a6ff;")
        layout.addWidget(title)
        
        # Статус
        self.status_label = QLabel("Загрузка...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 12px; color: #8b949e;")
        layout.addWidget(self.status_label)
        
        # Прогресс-бар
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)  # Режим 0-100%
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: #21262d;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #58a6ff;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress)
        
        layout.addStretch()
    
    def set_status(self, text: str):
        """Обновить статус загрузки"""
        self.status_label.setText(text)
        # Принудительно перерисовываем
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
    
    def set_progress(self, value: int):
        """Установить прогресс (0-100)"""
        self.progress.setValue(value)
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

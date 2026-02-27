from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import QFont
from .styles import COLORS
from ..utils.logger import get_logger
from ..utils.localization import get_text

class LogViewer(QTextEdit):
    """Виджет для отображения логов с поддержкой цветов"""
    
    def __init__(self, parent=None, placeholder=""):
        super().__init__(parent)
        self.setObjectName("logViewer")
        self.setReadOnly(True)
        self.setMinimumHeight(100)
        self.setPlaceholderText(placeholder)
        self.setFont(QFont("Consolas", 10))
        
        # Дефолтные цвета уровней
        self.color_map = {
            "debug": COLORS.get("text_dark", "#6e7681"),
            "info": COLORS.get("text", "#ffffff"),
            "warning": COLORS.get("warning", "#d29922"),
            "success": COLORS.get("accent", "#00ff9d"),
            "error": COLORS.get("danger", "#ff4a4a"),
            "critical": COLORS.get("danger", "#ff4a4a"),
        }

    def connect_logger(self):
        """Подключить автоматический прием логов от глобального логгера"""
        get_logger().connect_ui(self.add_log)

    def add_log(self, message: str, level: str):
        """Callback для логгера"""
        self.append_styled(message, level)

    def append_styled(self, message: str, level: str = "info"):
        """Добавить стилизованный текст вручную"""
        level_lower = level.lower()
        color = self.color_map.get(level_lower, self.color_map["info"])
        
        # Форматирование (HTML)
        html = f'<span style="color: {color};">{message}</span>'
        self.append(html)
        
        # Авто-скролл вниз
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel

class LogPanel(QFrame):
    """Общая панель логов с заголовком и рамкой"""
    
    def __init__(self, parent=None, title=None, placeholder=None):
        if title is None: title = get_text("ui_logs_panel_title", "📋 ЛОГ СОБЫТИЙ")
        if placeholder is None: placeholder = get_text("ui_logs_waiting", "Ожидание логов...")
        super().__init__(parent)
        
        # Стиль рамки
        self.setStyleSheet(f"""
            QFrame {{ 
                background-color: {COLORS['bg_card']}; 
                border: 1px solid {COLORS['border']}; 
                border-radius: 12px; 
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(5)
        
        # Заголовок
        self.header = QLabel(title)
        self.header.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLORS['text_dark']}; text-transform: uppercase; letter-spacing: 1px; border: none; background: transparent; padding-top: 5px;")
        layout.addWidget(self.header)
        
        # Сам лог
        self.viewer = LogViewer(placeholder=placeholder)
        # Убираем внутреннюю рамку QTextEdit, так как она есть у QFrame
        self.viewer.setStyleSheet("QTextEdit { border: none; background: transparent; }")
        layout.addWidget(self.viewer)
        
    def add_log(self, message: str, level: str):
        self.viewer.add_log(message, level)
        
    def append_styled(self, message: str, level: str = "info"):
        self.viewer.append_styled(message, level)
        
    def connect_logger(self):
        self.viewer.connect_logger()
        
    def clear(self):
        self.viewer.clear()

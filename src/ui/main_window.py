"""
Главное окно приложения Albion Market Scanner & Buyer
"""

import sys
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QLabel, QTabWidget, QTextEdit, QSplitter,
    QFrame, QCheckBox
)
from PyQt6.QtGui import QFont, QIcon

from .styles import MAIN_STYLE, COLORS
from .coordinate_panel import CoordinatePanel
from .coordinate_panel import CoordinatePanel
from .control_panel import ControlPanel
from .settings_panel import SettingsPanel
from ..utils.logger import get_logger
from ..utils.config import get_config


class LogViewer(QTextEdit):
    """Виджет для отображения логов"""
    
    def __init__(self):
        super().__init__()
        self.setObjectName("logViewer")
        self.setReadOnly(True)
        self.setMinimumHeight(150)
        
        # Подключаем логгер
        logger = get_logger()
        logger.connect_ui(self.add_log)
    
    def add_log(self, message: str, level: str):
        """Добавить сообщение в лог"""
        color_map = {
            "debug": COLORS["text_secondary"],
            "info": COLORS["text_primary"],
            "warning": COLORS["warning"],
            "error": COLORS["error"],
        }
        color = color_map.get(level, COLORS["text_primary"])
        
        # Форматируем с цветом
        html = f'<span style="color: {color};">{message}</span>'
        self.append(html)
        
        # Прокручиваем вниз
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


class MainWindow(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        self._setup_window()
        self._setup_ui()
        
        # Приветственное сообщение
        logger = get_logger()
        logger.info("Albion Market Scanner & Buyer запущен")
        logger.info("Настройте координаты перед запуском бота")
    
    def _setup_window(self):
        """Настройка окна"""
        self.setWindowTitle("Albion Market Scanner & Buyer")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # Применяем стили
        self.setStyleSheet(MAIN_STYLE)
    
    def _setup_ui(self):
        """Создание UI"""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # === Заголовок ===
        header_layout = QHBoxLayout()
        
        title = QLabel("🎮 Albion Market Scanner & Buyer")
        title.setObjectName("title")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Переключатель "Поверх всех окон"
        self.always_on_top_checkbox = QCheckBox("📌 Поверх всех окон")
        self.always_on_top_checkbox.setStyleSheet("""
            QCheckBox {
                color: #8b949e;
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox:checked {
                color: #3fb950;
            }
        """)
        self.always_on_top_checkbox.toggled.connect(self._toggle_always_on_top)
        header_layout.addWidget(self.always_on_top_checkbox)
        
        header_layout.addSpacing(15)
        
        version_label = QLabel("v1.0.0")
        version_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        header_layout.addWidget(version_label)
        
        main_layout.addLayout(header_layout)
        
        # === Основной контент со сплиттером ===
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Левая панель - Координаты
        left_panel = QFrame()
        left_panel.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.coordinate_panel = CoordinatePanel()
        left_layout.addWidget(self.coordinate_panel)
        
        splitter.addWidget(left_panel)
        
        # Правая панель - Табы
        right_panel = QFrame()
        right_panel.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)  # Немного отступа для табов
        
        self.tabs = QTabWidget()
        
        # Вкладка Управления
        self.control_panel = ControlPanel()
        self.tabs.addTab(self.control_panel, "🕹 Управление")
        
        # Вкладка Настроек
        self.settings_panel = SettingsPanel()
        self.tabs.addTab(self.settings_panel, "⚙️ Настройки")
        
        right_layout.addWidget(self.tabs)
        
        splitter.addWidget(right_panel)
        
        # Пропорции сплиттера
        splitter.setSizes([500, 700])
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        
        main_layout.addWidget(splitter, stretch=1)
        
        # === Панель логов ===
        log_frame = QFrame()
        log_frame.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
        """)
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(15, 10, 15, 10)
        log_layout.setSpacing(8)
        
        log_header = QLabel("📋 Журнал событий")
        log_header.setStyleSheet("font-size: 14px; font-weight: 600; color: #f0f6fc;")
        log_layout.addWidget(log_header)
        
        self.log_viewer = LogViewer()
        log_layout.addWidget(self.log_viewer)
        
        main_layout.addWidget(log_frame)
    
    def _toggle_always_on_top(self, checked: bool):
        """Переключить режим 'поверх всех окон'"""
        if checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
            get_logger().info("Режим 'Поверх всех окон' включен")
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
            get_logger().info("Режим 'Поверх всех окон' выключен")
        
        # Нужно показать окно заново после изменения флагов
        self.show()
    
    def closeEvent(self, event):
        """Обработчик закрытия окна"""
        get_logger().info("Приложение закрыто")
        event.accept()


def run_app():
    """Запуск приложения"""
    app = QApplication(sys.argv)
    
    # Настройка шрифта
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Создание и показ окна
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

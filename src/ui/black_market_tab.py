
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QGroupBox, QFormLayout, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from .styles import COLORS

class BlackMarketTab(QWidget):
    """
    Вкладка управления сканированием Черного Рынка.
    """
    start_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(15)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self._setup_ui()
        
    def _setup_ui(self):
        # 1. Заголовок
        header = QLabel("🕷️ Black Market Scanner")
        header.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['accent']};")
        self.layout.addWidget(header)
        
        # 2. Панель управления (Start/Stop)
        control_group = QGroupBox("Управление")
        control_layout = QHBoxLayout(control_group)
        
        self.btn_start = QPushButton("▶ Запуск сканера")
        self.btn_start.setMinimumHeight(40)
        self.btn_start.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                font-weight: bold;
                border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: #2ea043; }}
        """)
        self.btn_start.clicked.connect(self.start_clicked.emit)
        
        self.btn_stop = QPushButton("⛔ Стоп")
        self.btn_stop.setMinimumHeight(40)
        self.btn_stop.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['error']};
                color: white;
                font-weight: bold;
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: #bd2c00; }}
        """)
        self.btn_stop.clicked.connect(self.stop_clicked.emit)
        self.btn_stop.setEnabled(False)
        
        control_layout.addWidget(self.btn_start)
        control_layout.addWidget(self.btn_stop)
        
        self.layout.addWidget(control_group)
        
        # 3. Настройки маршрута (Заглушка)
        route_group = QGroupBox("Настройки маршрута")
        route_layout = QFormLayout(route_group)
        
        self.spin_loops = QSpinBox()
        self.spin_loops.setRange(1, 9999)
        self.spin_loops.setValue(10)
        route_layout.addRow("Количество кругов:", self.spin_loops)
        
        self.layout.addWidget(route_group)
        
        # 4. Статус
        self.status_label = QLabel("Статус: Ожидание")
        self.status_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 14px;")
        self.layout.addWidget(self.status_label)
        
        self.layout.addStretch()

    def set_running_state(self, is_running: bool):
        """Обновить состояние кнопок"""
        self.btn_start.setEnabled(not is_running)
        self.btn_start.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success'] if not is_running else '#21262d'};
                color: {'white' if not is_running else '#484f58'};
                font-weight: bold;
                border-radius: 4px;
            }}
        """)
        
        self.btn_stop.setEnabled(is_running)

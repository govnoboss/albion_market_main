"""
Панель управления ботом (урезанная)
Только Старт/Стоп и Статус
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGroupBox, QProgressBar
)

from ..utils.logger import get_logger


class ControlPanel(QWidget):
    """Панель управления ботом"""
    
    start_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._is_running = False
        self._is_paused = False
        self._setup_ui()
    
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)
        
        # === Статус ===
        status_group = QGroupBox("📊 Статус")
        status_layout = QVBoxLayout(status_group)
        
        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("Состояние:"))
        self.status_label = QLabel("Ожидание")
        self.status_label.setObjectName("statusReady")
        self.status_label.setStyleSheet("color: #8b949e; font-weight: 600;")
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        status_layout.addLayout(status_row)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Ожидание...")
        status_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(status_group)
        
        # === Управление ===
        controls_group = QGroupBox("🎮 Управление")
        controls_layout = QVBoxLayout(controls_group)
        
        self.start_btn = QPushButton("▶ Старт")
        self.start_btn.setObjectName("primary")
        self.start_btn.setMinimumHeight(45)
        self.start_btn.clicked.connect(self.start_clicked.emit)
        controls_layout.addWidget(self.start_btn)
        
        self.pause_btn = QPushButton("⏸ Пауза")
        self.pause_btn.setMinimumHeight(45)
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.pause_clicked.emit)
        controls_layout.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton("⏹ Стоп")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setMinimumHeight(45)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_clicked.emit)
        controls_layout.addWidget(self.stop_btn)
        
        main_layout.addWidget(controls_group)
        main_layout.addStretch()

    def set_running_state(self, is_running: bool):
        """Установить состояние работы (вызывается из MainWindow)"""
        self._is_running = is_running
        self._is_paused = False # Сброс паузы при смене состояния
        self._update_ui_state()
        
    def set_paused_state(self, is_paused: bool):
        """Установить состояние паузы"""
        self._is_paused = is_paused
        self._update_ui_state()

    def _update_ui_state(self):
        """Обновить UI на основе внутреннего состояния"""
        self.start_btn.setEnabled(not self._is_running)
        self.pause_btn.setEnabled(self._is_running)
        self.stop_btn.setEnabled(self._is_running)
        
        if not self._is_running:
            self.status_label.setText("Остановлен")
            self.status_label.setStyleSheet("color: #8b949e; font-weight: 600;")
            self.pause_btn.setText("⏸ Пауза")
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Ожидание...")
        elif self._is_paused:
            self.status_label.setText("На паузе")
            self.status_label.setStyleSheet("color: #d29922; font-weight: 600;")
            self.pause_btn.setText("▶ Продолжить")
        else:
            self.status_label.setText("Работает")
            self.status_label.setStyleSheet("color: #3fb950; font-weight: 600;")
            self.pause_btn.setText("⏸ Пауза")
    
    def update_progress(self, current: int, total: int, item_name: str = ""):
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)
            self.progress_bar.setFormat(f"{item_name} ({current}/{total})")
        else:
             self.progress_bar.setValue(0)
             self.progress_bar.setFormat(item_name if item_name else "Ожидание...")

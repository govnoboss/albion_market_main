"""
Панель управления ботом (урезанная)
Только Старт/Стоп и Статус
"""

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGroupBox, QProgressBar, QMessageBox,
    QSpinBox, QStyle, QGridLayout
)
import os
import pyautogui

from ..utils.config import get_config
from ..utils.logger import get_logger
from .styles import COLORS


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
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)
        
        # === Статус ===
        status_group = QGroupBox("📊 Статус")
        status_layout = QVBoxLayout(status_group)
        
        status_row = QHBoxLayout()
        status_lbl = QLabel("Состояние:")
        status_lbl.setStyleSheet(f"color: {COLORS['text_dark']}; font-weight: 700; font-size: 11px; text-transform: uppercase;")
        status_row.addWidget(status_lbl)
        
        self.status_label = QLabel("Ожидание")
        self.status_label.setObjectName("statusReady")
        self.status_label.setStyleSheet(f"color: {COLORS['text_dark']}; font-weight: 700; font-size: 11px; text-transform: uppercase;")
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
        controls_group = QGroupBox("🎮 Управление")
        controls_layout = QVBoxLayout(controls_group)
        
        # Row: Start Index & Resume
        resume_layout = QHBoxLayout()
        
        self.start_index_spin = QSpinBox()
        self.start_index_spin.setRange(1, 9999)
        self.start_index_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)  # Убираем +/-
        self.start_index_spin.setToolTip("Номер предмета, с которого начать")
        self.start_index_spin.setFixedWidth(60)
        self.start_index_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        resume_layout.addWidget(QLabel("Старт с:"))
        resume_layout.addWidget(self.start_index_spin)
        
        self.resume_btn = QPushButton("Продолжить")
        self.resume_btn.setToolTip("Продолжить с последнего сохраненного места")
        self.resume_btn.clicked.connect(self._on_resume_clicked)
        self.resume_btn.setVisible(False) # Скрыта по умолчанию
        resume_layout.addWidget(self.resume_btn)
        
        resume_layout.addStretch()
        controls_layout.addLayout(resume_layout)

        # Check for last index at startup
        self.refresh_resume_button()
        
        
        self.start_btn = QPushButton("▶ ЗАПУСТИТЬ")
        self.start_btn.setObjectName("primary")
        self.start_btn.setMinimumHeight(50)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self.start_clicked.emit)
        controls_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("🛑 ОСТАНОВИТЬ (F5)")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setMinimumHeight(50)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setVisible(False)
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

    def refresh_resume_button(self):
        """Обновить кнопку 'Продолжить' на основе сохраненного прогресса"""
        try:
            last_index = get_config().get_setting("last_scan_index", 0)
            if last_index > 0:
                resume_item = last_index + 1
                self.resume_btn.setText(f"Продолжить ({resume_item})")
                self.resume_btn.setVisible(True)
                self.resume_btn.setStyleSheet(f"background-color: {COLORS['accent']}; color: white; font-weight: bold; border-radius: 6px; padding: 5px;")
            else:
                self.resume_btn.setVisible(False)
        except:
            self.resume_btn.setVisible(False)

    def _update_ui_state(self):
        """Обновить UI на основе внутреннего состояния"""
        # Toggle visibility instead of enabling/disabling
        self.start_btn.setVisible(not self._is_running)
        self.stop_btn.setVisible(self._is_running)
        
        if not self._is_running:
            self.status_label.setText("Ожидание")
            self.status_label.setStyleSheet(f"color: {COLORS['text_dark']}; font-weight: 700; font-size: 11px; text-transform: uppercase;")
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Ожидание...")
        elif self._is_paused:
            self.status_label.setText("На паузе")
            self.status_label.setStyleSheet(f"color: {COLORS['warning']}; font-weight: 700; font-size: 11px; text-transform: uppercase;")
        else:
            self.status_label.setText("В работе")
            self.status_label.setStyleSheet(f"color: {COLORS['accent']}; font-weight: 700; font-size: 11px; text-transform: uppercase;")
    
    def update_progress(self, current: int, total: int, item_name: str = ""):
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)
            self.progress_bar.setFormat(f"{item_name} ({current}/{total})")
        else:
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat(item_name if item_name else "Ожидание...")


            self.progress_bar.setFormat(item_name if item_name else "Ожидание...")

    def _on_resume_clicked(self):
        """Обработчик кнопки Продолжить"""
        try:
            last_index = get_config().get_setting("last_scan_index", 0)
            # Устанавливаем в спинбокс (UI 1-based, internal 0-based. 
            # Если мы остановились на 10 (index 9), next is 11 (index 10).
            # last_scan_index сохраняет индекс ПОСЛЕДНЕГО обработанного.
            # Значит следующий = last_index + 1.
            # Spinbox is 1-based index (№ предмета) -> (last_index + 1) + 1?
            # Нет: items[0] -> Spin=1. 
            # Processed index 0 (Item 1). Next is Index 1 (Item 2).
            # Last index = 0. Next Spin = 2.
            # Next Spin = last_index + 2?
            
            # Продолжаем с ТОГО ЖЕ предмета (last_index + 1 для UI 1-based)
            resume_item_number = last_index + 1
            self.start_index_spin.setValue(resume_item_number)
            
            # Auto-start
            self.start_clicked.emit()
            
        except Exception as e:
            get_logger().error(f"Error resuming: {e}")

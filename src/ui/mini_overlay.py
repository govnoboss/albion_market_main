"""
Мини-оверлей для мониторинга и управления ботом поверх игры
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint
from PyQt6.QtGui import QColor, QPalette
from .styles import MINI_OVERLAY_STYLE

class MiniOverlay(QWidget):
    """
    Компактное окно поверх всех окон.
    Отображает статус, прогресс и кнопки управления.
    """
    
    # Сигналы для управления из главного окна
    start_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    restore_clicked = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._is_dragging = False
        self._drag_pos = QPoint()
        
        self._setup_window()
        self._setup_ui()
        
        if not self.load_settings():
            self._initial_positioning()
        
    def _setup_window(self):
        """Настройка окна"""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(320, 95) # Compact height (removed logs)
        
    def _initial_positioning(self):
        """Установка начальной позиции (вверху по центру)"""
        try:
            from PyQt6.QtWidgets import QApplication
            screen = QApplication.primaryScreen().geometry()
            x = (screen.width() - self.width()) // 2
            y = 10 # Отступ от верхнего края
            self.move(x, y)
        except:
            pass

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._is_dragging:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._is_dragging = False
        self.save_settings()

    def save_settings(self):
        """Сохранить позицию окна"""
        from PyQt6.QtCore import QSettings
        settings = QSettings("GBot", "MiniOverlay")
        settings.setValue("pos", self.pos())

    def load_settings(self) -> bool:
        """Загрузить позицию окна"""
        from PyQt6.QtCore import QSettings
        settings = QSettings("GBot", "MiniOverlay")
        pos = settings.value("pos")
        if pos:
            self.move(pos)
            return True
        return False

    def _setup_ui(self):
        """Создание интерфейса"""
        # Основной контейнер с фоном и рамкой
        self.container = QFrame(self)
        self.container.setGeometry(0, 0, 320, 95)
        self.container.setStyleSheet(MINI_OVERLAY_STYLE["container_ready"])
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(10, 5, 10, 5) # Compact margins
        layout.setSpacing(2) # Minimal spacing
        
        # --- Верхняя строка: Статус и Кнопка возврата ---
        top_layout = QHBoxLayout()
        
        self.status_label = QLabel("🚀 Ready")
        self.status_label.setStyleSheet(MINI_OVERLAY_STYLE["status_ready"])
        top_layout.addWidget(self.status_label)
        
        top_layout.addStretch()
        
        self.restore_btn = QPushButton("↙")
        self.restore_btn.setToolTip("Развернуть")
        self.restore_btn.setFixedSize(20, 20)
        self.restore_btn.setStyleSheet(MINI_OVERLAY_STYLE["restore_btn"])
        self.restore_btn.clicked.connect(self.restore_clicked.emit)
        top_layout.addWidget(self.restore_btn)
        
        layout.addLayout(top_layout)
        
        # --- Строка прогресса ---
        self.progress_label = QLabel("Ожидание запуска...")
        self.progress_label.setStyleSheet("color: #f0f6fc; font-size: 11px; border: none; background: transparent;")
        layout.addWidget(self.progress_label)
        
        # --- Кнопки управления ---
        btn_layout = QHBoxLayout()
        
        # Кнопка Старт (видна когда бот не работает)
        self.start_btn = QPushButton("▶ Старт (F5)")
        self.start_btn.setFixedHeight(30)
        self.start_btn.setStyleSheet(MINI_OVERLAY_STYLE["start_btn"])
        self.start_btn.clicked.connect(self.start_clicked.emit)
        btn_layout.addWidget(self.start_btn)
        
        # Кнопки Пауза и Стоп (видны когда бот работает)
        self.pause_btn = QPushButton("❚❚ Пауза (F6)")
        self.pause_btn.setFixedHeight(30)
        self.pause_btn.setStyleSheet(MINI_OVERLAY_STYLE["pause_btn"])
        self.pause_btn.clicked.connect(self.pause_clicked.emit)
        self.pause_btn.hide()  # Скрыта по умолчанию
        btn_layout.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton("■ Стоп (F5)")
        self.stop_btn.setFixedHeight(30)
        self.stop_btn.setStyleSheet(MINI_OVERLAY_STYLE["stop_btn"])
        self.stop_btn.clicked.connect(self.stop_clicked.emit)
        self.stop_btn.hide()  # Скрыта по умолчанию
        btn_layout.addWidget(self.stop_btn)
        
        layout.addLayout(btn_layout)

    def update_status(self, is_running: bool, is_paused: bool):
        """Обновление статуса и стиля кнопок"""
        if not is_running:
            self.status_label.setText("🚀 Ready")
            self.status_label.setStyleSheet(MINI_OVERLAY_STYLE["status_ready"])
            self.container.setStyleSheet(MINI_OVERLAY_STYLE["container_ready"])
            # Показываем кнопку Старт, скрываем Пауза/Стоп
            self.start_btn.show()
            self.pause_btn.hide()
            self.stop_btn.hide()
            
        elif is_paused:
            self.status_label.setText("⏸ Paused")
            self.status_label.setStyleSheet(MINI_OVERLAY_STYLE["status_paused"])
            self.container.setStyleSheet(MINI_OVERLAY_STYLE["container_paused"])
            # Скрываем Старт, показываем Пауза/Стоп
            self.start_btn.hide()
            self.pause_btn.show()
            self.stop_btn.show()
            self.pause_btn.setText("▶ Продолжить (F6)")
            self.pause_btn.setStyleSheet(MINI_OVERLAY_STYLE["resume_btn"])
            
        else:
            self.status_label.setText("⚡ Running")
            self.status_label.setStyleSheet(MINI_OVERLAY_STYLE["status_running"])
            self.container.setStyleSheet(MINI_OVERLAY_STYLE["container_running"])
            # Скрываем Старт, показываем Пауза/Стоп
            self.start_btn.hide()
            self.pause_btn.show()
            self.stop_btn.show()
            self.pause_btn.setText("❚❚ Пауза (F6)")
            self.pause_btn.setStyleSheet(MINI_OVERLAY_STYLE["pause_btn"])

    def update_progress(self, current: int, total: int, item_name: str):
        """Обновление прогресса"""
        if total > 0:
            self.progress_label.setText(f"[{current}/{total}] {item_name}")
        else:
            self.progress_label.setText(item_name) # Например "Завершено"



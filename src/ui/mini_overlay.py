"""
Мини-оверлей для мониторинга и управления ботом поверх игры
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QPalette

class MiniOverlay(QWidget):
    """
    Компактное окно поверх всех окон.
    Отображает статус, прогресс и кнопки управления.
    """
    
    # Сигналы для управления из главного окна
    pause_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    restore_clicked = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._setup_window()
        self._setup_ui()
        
    def _setup_window(self):
        """Настройка окна"""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(320, 130)
        
    def _setup_ui(self):
        """Создание интерфейса"""
        # Основной контейнер с фоном и рамкой
        self.container = QFrame(self)
        self.container.setGeometry(0, 0, 320, 130)
        self.container.setStyleSheet("""
            QFrame {
                background-color: rgba(22, 27, 34, 230);
                border: 1px solid #30363d;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(5)
        
        # --- Верхняя строка: Статус и Кнопка возврата ---
        top_layout = QHBoxLayout()
        
        self.status_label = QLabel("🚀 Ready")
        self.status_label.setStyleSheet("color: #8b949e; font-weight: bold; border: none; background: transparent;")
        top_layout.addWidget(self.status_label)
        
        top_layout.addStretch()
        
        self.restore_btn = QPushButton("↙")
        self.restore_btn.setToolTip("Развернуть")
        self.restore_btn.setFixedSize(24, 24)
        self.restore_btn.setStyleSheet("""
            QPushButton { 
                background-color: transparent; 
                color: #8b949e; 
                border: none; 
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover { color: #58a6ff; }
        """)
        self.restore_btn.clicked.connect(self.restore_clicked.emit)
        top_layout.addWidget(self.restore_btn)
        
        layout.addLayout(top_layout)
        
        # --- Строка прогресса ---
        self.progress_label = QLabel("Ожидание запуска...")
        self.progress_label.setStyleSheet("color: #f0f6fc; font-size: 13px; border: none; background: transparent;")
        layout.addWidget(self.progress_label)
        
        # --- Строка лога (последнее сообщение) ---
        self.log_label = QLabel("")
        self.log_label.setStyleSheet("color: #8b949e; font-size: 11px; font-style: italic; border: none; background: transparent;")
        self.log_label.setFixedHeight(15)
        self.log_label.setWordWrap(False) # Обрезаем длинный текст
        layout.addWidget(self.log_label)
        
        # --- Кнопки управления ---
        btn_layout = QHBoxLayout()
        
        self.pause_btn = QPushButton("❚❚ Пауза")
        self.pause_btn.setFixedHeight(30)
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #d29922;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #ac7c18; }
        """)
        self.pause_btn.clicked.connect(self.pause_clicked.emit)
        btn_layout.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton("■ Стоп")
        self.stop_btn.setFixedHeight(30)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f85149;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #bd3832; }
        """)
        self.stop_btn.clicked.connect(self.stop_clicked.emit)
        btn_layout.addWidget(self.stop_btn)
        
        layout.addLayout(btn_layout)

    def update_status(self, is_running: bool, is_paused: bool):
        """Обновление статуса и стиля кнопок"""
        if not is_running:
            self.status_label.setText("🛑 Stopped")
            self.status_label.setStyleSheet("color: #f85149; font-weight: bold; border: none; background: transparent;")
            self.container.setStyleSheet("""
                QFrame {
                    background-color: rgba(22, 27, 34, 230);
                    border: 1px solid #f85149;
                    border-radius: 8px;
                }
            """)
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            self.pause_btn.setText("❚❚ Пауза")
            
        elif is_paused:
            self.status_label.setText("⏸ Paused")
            self.status_label.setStyleSheet("color: #d29922; font-weight: bold; border: none; background: transparent;")
            self.container.setStyleSheet("""
                QFrame {
                    background-color: rgba(22, 27, 34, 230);
                    border: 1px solid #d29922;
                    border-radius: 8px;
                }
            """)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            self.pause_btn.setText("▶ Продолжить")
            self.pause_btn.setStyleSheet("""
                QPushButton {
                    background-color: #238636;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #2ea043; }
            """)
            
        else:
            self.status_label.setText("⚡ Running")
            self.status_label.setStyleSheet("color: #3fb950; font-weight: bold; border: none; background: transparent;")
            self.container.setStyleSheet("""
                QFrame {
                    background-color: rgba(22, 27, 34, 230);
                    border: 1px solid #3fb950;
                    border-radius: 8px;
                }
            """)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            self.pause_btn.setText("❚❚ Пауза")
            self.pause_btn.setStyleSheet("""
                QPushButton {
                    background-color: #d29922;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #ac7c18; }
            """)

    def update_progress(self, current: int, total: int, item_name: str):
        """Обновление прогресса"""
        if total > 0:
            self.progress_label.setText(f"[{current}/{total}] {item_name}")
        else:
            self.progress_label.setText(item_name) # Например "Завершено"

    def set_last_log(self, message: str):
        """Обновление последней строки лога"""
        # Убираем HTML теги если есть, для простоты просто показываем текст
        # Можно почистить теги regex-ом, но для скорости пока так
        clean_msg = message
        if ">" in message and "<" in message:
             # Basic stripping of span tags
             import re
             clean_msg = re.sub('<[^<]+?>', '', message)
             
        self.log_label.setText(clean_msg)

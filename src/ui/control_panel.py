"""
Панель управления ботом
Start/Stop/Pause и список предметов для покупки
"""

from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea, QListWidget,
    QListWidgetItem, QLineEdit, QSpinBox, QGroupBox,
    QProgressBar, QSizePolicy
)

from ..utils.config import get_config
from ..utils.logger import get_logger


class ItemCard(QFrame):
    """Карточка предмета для покупки"""
    
    removed = pyqtSignal(int)  # index
    
    def __init__(self, index: int, name: str, max_price: int, quantity: int, enabled: bool = True):
        super().__init__()
        self.index = index
        self.item_name = name
        self.max_price = max_price
        self.quantity = quantity
        self.enabled = enabled
        
        self._setup_ui()
    
    def _setup_ui(self):
        self.setObjectName("card")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        
        # Статус
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(f"color: {'#3fb950' if self.enabled else '#484f58'}; font-size: 10px;")
        layout.addWidget(self.status_dot)
        
        # Название
        name_label = QLabel(self.item_name)
        name_label.setStyleSheet("font-size: 14px; font-weight: 500;")
        name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(name_label, stretch=1)
        
        # Макс. цена
        price_label = QLabel(f"≤ {self.max_price:,} серебра")
        price_label.setStyleSheet("color: #d29922; font-size: 12px;")
        layout.addWidget(price_label)
        
        # Количество
        qty_label = QLabel(f"x{self.quantity}")
        qty_label.setStyleSheet("color: #8b949e; font-size: 12px; min-width: 40px;")
        layout.addWidget(qty_label)
        
        # Кнопка удаления
        remove_btn = QPushButton("✕")
        remove_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #8b949e;
                padding: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                color: #f85149;
            }
        """)
        remove_btn.clicked.connect(lambda: self.removed.emit(self.index))
        layout.addWidget(remove_btn)


class ControlPanel(QWidget):
    """Панель управления ботом"""
    
    # Сигналы управления ботом
    start_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._is_running = False
        self._is_paused = False
        self._setup_ui()
        self._load_items()
    
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)
        
        # === Секция статуса ===
        status_group = QGroupBox("📊 Статус")
        status_layout = QVBoxLayout(status_group)
        
        # Статус бота
        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("Состояние:"))
        self.status_label = QLabel("Остановлен")
        self.status_label.setObjectName("statusReady")
        self.status_label.setStyleSheet("color: #8b949e; font-weight: 600;")
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        status_layout.addLayout(status_row)
        
        # Прогресс
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Ожидание...")
        status_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(status_group)
        
        # === Секция кнопок управления ===
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)
        
        self.start_btn = QPushButton("▶ Старт")
        self.start_btn.setObjectName("primary")
        self.start_btn.setMinimumHeight(45)
        self.start_btn.clicked.connect(self._on_start_clicked)
        controls_layout.addWidget(self.start_btn)
        
        self.pause_btn = QPushButton("⏸ Пауза")
        self.pause_btn.setMinimumHeight(45)
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        controls_layout.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton("⏹ Стоп")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setMinimumHeight(45)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        controls_layout.addWidget(self.stop_btn)
        
        main_layout.addLayout(controls_layout)
        
        # === Секция добавления предмета ===
        add_group = QGroupBox("➕ Добавить предмет")
        add_layout = QVBoxLayout(add_group)
        
        # Название предмета
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Название:"))
        self.item_name_input = QLineEdit()
        self.item_name_input.setPlaceholderText("Введите название предмета...")
        name_row.addWidget(self.item_name_input, stretch=1)
        add_layout.addLayout(name_row)
        
        # Макс цена и количество
        params_row = QHBoxLayout()
        
        params_row.addWidget(QLabel("Макс. цена:"))
        self.max_price_input = QSpinBox()
        self.max_price_input.setRange(0, 999999999)
        self.max_price_input.setValue(0)
        self.max_price_input.setSuffix(" серебра")
        params_row.addWidget(self.max_price_input)
        
        params_row.addSpacing(20)
        
        params_row.addWidget(QLabel("Количество:"))
        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(1, 9999)
        self.quantity_input.setValue(1)
        params_row.addWidget(self.quantity_input)
        
        params_row.addStretch()
        
        add_btn = QPushButton("Добавить")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self._add_item)
        params_row.addWidget(add_btn)
        
        add_layout.addLayout(params_row)
        main_layout.addWidget(add_group)
        
        # === Список предметов ===
        items_group = QGroupBox("📋 Список предметов для покупки")
        items_layout = QVBoxLayout(items_group)
        
        # Скролл для списка
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setMinimumHeight(200)
        
        self.items_container = QWidget()
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(8)
        self.items_layout.addStretch()
        
        scroll.setWidget(self.items_container)
        items_layout.addWidget(scroll)
        
        # Кнопка очистки
        clear_btn = QPushButton("🗑 Очистить список")
        clear_btn.clicked.connect(self._clear_items)
        items_layout.addWidget(clear_btn)
        
        main_layout.addWidget(items_group, stretch=1)
    
    def _load_items(self):
        """Загрузить сохраненные предметы"""
        config = get_config()
        items = config.get_items()
        
        for i, item in enumerate(items):
            self._add_item_card(
                i, 
                item.get("name", ""),
                item.get("max_price", 0),
                item.get("quantity", 1),
                item.get("enabled", True)
            )
    
    def _add_item(self):
        """Добавить новый предмет"""
        name = self.item_name_input.text().strip()
        if not name:
            get_logger().warning("Введите название предмета")
            return
        
        max_price = self.max_price_input.value()
        quantity = self.quantity_input.value()
        
        # Сохраняем в конфиг
        config = get_config()
        config.add_item(name, max_price, quantity)
        
        # Добавляем карточку
        items = config.get_items()
        index = len(items) - 1
        self._add_item_card(index, name, max_price, quantity)
        
        # Очищаем поля
        self.item_name_input.clear()
        self.max_price_input.setValue(0)
        self.quantity_input.setValue(1)
        
        get_logger().info(f"Предмет добавлен: {name}")
    
    def _add_item_card(self, index: int, name: str, max_price: int, quantity: int, enabled: bool = True):
        """Добавить карточку предмета в UI"""
        card = ItemCard(index, name, max_price, quantity, enabled)
        card.removed.connect(self._remove_item)
        
        # Вставляем перед stretch
        self.items_layout.insertWidget(self.items_layout.count() - 1, card)
    
    def _remove_item(self, index: int):
        """Удалить предмет"""
        config = get_config()
        items = config.get_items()
        
        if 0 <= index < len(items):
            name = items[index].get("name", "")
            config.remove_item(index)
            get_logger().info(f"Предмет удален: {name}")
            
            # Перезагружаем список
            self._reload_items()
    
    def _clear_items(self):
        """Очистить все предметы"""
        config = get_config()
        config.clear_items()
        self._reload_items()
        get_logger().info("Список предметов очищен")
    
    def _reload_items(self):
        """Перезагрузить список предметов"""
        # Удаляем все карточки
        while self.items_layout.count() > 1:
            item = self.items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Загружаем заново
        self._load_items()
    
    def _on_start_clicked(self):
        """Обработчик кнопки Старт"""
        self._is_running = True
        self._is_paused = False
        self._update_buttons()
        self.status_label.setText("Работает")
        self.status_label.setStyleSheet("color: #3fb950; font-weight: 600;")
        self.start_requested.emit()
        get_logger().action("Бот запущен")
    
    def _on_pause_clicked(self):
        """Обработчик кнопки Пауза"""
        self._is_paused = not self._is_paused
        self._update_buttons()
        
        if self._is_paused:
            self.status_label.setText("На паузе")
            self.status_label.setStyleSheet("color: #d29922; font-weight: 600;")
            self.pause_btn.setText("▶ Продолжить")
            get_logger().warning("Бот приостановлен")
        else:
            self.status_label.setText("Работает")
            self.status_label.setStyleSheet("color: #3fb950; font-weight: 600;")
            self.pause_btn.setText("⏸ Пауза")
            get_logger().action("Бот возобновлен")
        
        self.pause_requested.emit()
    
    def _on_stop_clicked(self):
        """Обработчик кнопки Стоп"""
        self._is_running = False
        self._is_paused = False
        self._update_buttons()
        self.status_label.setText("Остановлен")
        self.status_label.setStyleSheet("color: #8b949e; font-weight: 600;")
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Ожидание...")
        self.stop_requested.emit()
        get_logger().info("Бот остановлен")
    
    def _update_buttons(self):
        """Обновить состояние кнопок"""
        self.start_btn.setEnabled(not self._is_running)
        self.pause_btn.setEnabled(self._is_running)
        self.stop_btn.setEnabled(self._is_running)
    
    def update_progress(self, current: int, total: int, item_name: str = ""):
        """Обновить прогресс"""
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)
            self.progress_bar.setFormat(f"{item_name} ({current}/{total})")

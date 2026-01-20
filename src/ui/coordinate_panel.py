"""
Панель настройки координат
Карточки с кнопками захвата для каждой координаты
"""

from typing import Dict, Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea, QGridLayout,
    QGroupBox
)
from PyQt6.QtGui import QFont

from ..core.coordinate_capture import get_capture_manager
from ..utils.config import get_config
from ..utils.logger import get_logger


# Определение координат для захвата (базовые)
COORDINATE_DEFINITIONS = {
    # Основные координаты
    "basic": {
        "search_input": {
            "name": "🔍 Поле поиска",
            "description": "Клик для активации поиска"
        },
        "search_clear": {
            "name": "❌ Очистка поиска", 
            "description": "Кнопка очистки поля поиска"
        },
        "buy_button": {
            "name": "💰 Кнопка Купить",
            "description": "Основная кнопка покупки"
        },
    },
    # Меню и взаимодействие
    "interaction": {
        "item_expand": {
            "name": "Раскрыть окно предмета",
            "description": "Кнопка стрелки для раскрытия лота"
        },
        "tier_dropdown": {
            "name": "Дропдаун Тиров",
            "description": "Выпадающий список выбора тира"
        },
        "enchant_dropdown": {
            "name": "Дропдаун Энчантов",
            "description": "Выпадающий список выбора зачарования"
        },
        "quality_dropdown": {
            "name": "Дропдаун Качеств",
            "description": "Выпадающий список выбора качества"
        },
        "menu_close": {
            "name": "Закрыть меню",
            "description": "Крестик или кнопка закрытия окна"
        },
    },
}


class CoordinateCard(QFrame):
    """Карточка для одной координаты"""
    
    capture_requested = pyqtSignal(str, str)  # key, display_name
    
    def __init__(self, key: str, name: str, description: str):
        super().__init__()
        self.key = key
        self.coord_name = name
        self.description = description
        
        self._setup_ui()
        self._load_saved_coordinate()
    
    def _setup_ui(self):
        self.setObjectName("card")
        self.setMinimumHeight(80)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(15)
        
        # Левая часть: информация
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        # Название
        self.name_label = QLabel(self.coord_name)
        self.name_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #f0f6fc;")
        self.name_label.setWordWrap(True)
        info_layout.addWidget(self.name_label)
        
        # Описание
        desc_label = QLabel(self.description)
        desc_label.setStyleSheet("font-size: 12px; color: #8b949e;")
        desc_label.setWordWrap(True)
        info_layout.addWidget(desc_label)
        
        layout.addLayout(info_layout, stretch=1)
        
        # Центр: отображение координат
        self.coord_label = QLabel("Не задано")
        self.coord_label.setStyleSheet("""
            font-size: 13px;
            color: #8b949e;
            font-family: 'Consolas', monospace;
            padding: 5px 10px;
            background-color: #0d1117;
            border-radius: 4px;
            min-width: 100px;
        """)
        self.coord_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.coord_label)
        
        # Правая часть: кнопка захвата
        self.capture_btn = QPushButton("Захватить")
        self.capture_btn.setObjectName("capture")
        self.capture_btn.setMinimumWidth(100)
        self.capture_btn.clicked.connect(self._on_capture_clicked)
        layout.addWidget(self.capture_btn)
        
        # Кнопка очистки
        self.clear_btn = QPushButton("✕")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 6px 10px;
                color: #8b949e;
                min-width: 30px;
                max-width: 30px;
            }
            QPushButton:hover {
                background-color: #da3633;
                border-color: #da3633;
                color: #f0f6fc;
            }
        """)
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        self.clear_btn.setVisible(False)
        layout.addWidget(self.clear_btn)

        # Set minimum width to prevent squashing
        self.setMinimumWidth(450)
    
    def _load_saved_coordinate(self):
        """Загрузить сохраненную координату"""
        config = get_config()
        coord = config.get_coordinate(self.key)
        if coord:
            self.set_coordinate(coord[0], coord[1])
    
    def _on_capture_clicked(self):
        """Обработчик клика на кнопку захвата"""
        self.capture_requested.emit(self.key, self.coord_name)
    
    def _on_clear_clicked(self):
        """Очистить координату"""
        config = get_config()
        config.clear_coordinate(self.key)
        
        self.coord_label.setText("Не задано")
        self.coord_label.setStyleSheet("""
            font-size: 13px;
            color: #8b949e;
            font-family: 'Consolas', monospace;
            padding: 5px 10px;
            background-color: #0d1117;
            border-radius: 4px;
            min-width: 100px;
        """)
        self.clear_btn.setVisible(False)
        
        get_logger().info(f"Координата '{self.coord_name}' очищена")
    
    def set_coordinate(self, x: int, y: int):
        """Установить координату"""
        self.coord_label.setText(f"X: {x}, Y: {y}")
        self.coord_label.setStyleSheet("""
            font-size: 13px;
            color: #3fb950;
            font-family: 'Consolas', monospace;
            padding: 5px 10px;
            background-color: #0d1117;
            border-radius: 4px;
            min-width: 100px;
        """)
        self.clear_btn.setVisible(True)
    
    def set_capturing(self, is_capturing: bool):
        """Установить состояние захвата"""
        self.capture_btn.setEnabled(not is_capturing)
        if is_capturing:
            self.capture_btn.setText("...")
        else:
            self.capture_btn.setText("Захватить")


class CoordinatePanel(QWidget):
    """Панель настройки всех координат"""
    
    def __init__(self):
        super().__init__()
        self._cards: Dict[str, CoordinateCard] = {}
        self._setup_ui()
        self._connect_capture_manager()
    
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Скролл область
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        # Контент
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(20)
        
        # Заголовок
        header = QLabel("⚙️ Настройка координат")
        header.setObjectName("sectionHeader")
        content_layout.addWidget(header)
        
        # Информация
        info = QLabel("Нажмите 'Захватить' и кликните в нужном месте экрана игры")
        info.setStyleSheet("color: #8b949e; font-size: 13px; margin-bottom: 10px;")
        content_layout.addWidget(info)
        
        # Группы координат
        group_names = {
            "basic": "⚙️ Основные координаты",
        }
        
        for group_key, coords in COORDINATE_DEFINITIONS.items():
            group_box = QGroupBox(group_names.get(group_key, group_key))
            group_layout = QVBoxLayout(group_box)
            group_layout.setSpacing(10)
            
            for coord_key, coord_info in coords.items():
                card = CoordinateCard(
                    key=coord_key,
                    name=coord_info["name"],
                    description=coord_info["description"]
                )
                card.capture_requested.connect(self._start_capture)
                group_layout.addWidget(card)
                self._cards[coord_key] = card
            
            content_layout.addWidget(group_box)
        
        # Spacer
        content_layout.addStretch()
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
    
    def _connect_capture_manager(self):
        """Подключить сигналы менеджера захвата"""
        capture = get_capture_manager()
        capture.coordinate_captured.connect(self._on_coordinate_captured)
        capture.capture_cancelled.connect(self._on_capture_cancelled)
        capture.capture_started.connect(self._on_capture_started)
    
    def _start_capture(self, key: str, display_name: str):
        """Начать захват координаты"""
        capture = get_capture_manager()
        capture.start_capture(key, display_name)
    
    def _on_capture_started(self, key: str):
        """Обработчик начала захвата"""
        if key in self._cards:
            self._cards[key].set_capturing(True)
        get_logger().info(f"Захват координаты начат...")
    
    def _on_coordinate_captured(self, key: str, x: int, y: int):
        """Обработчик успешного захвата"""
        # Сохраняем координату
        config = get_config()
        config.set_coordinate(key, x, y)
        
        # Обновляем карточку
        if key in self._cards:
            self._cards[key].set_coordinate(x, y)
            self._cards[key].set_capturing(False)
        
        get_logger().success(f"Координата захвачена: X={x}, Y={y}")
    
    def _on_capture_cancelled(self, key: str):
        """Обработчик отмены захвата"""
        if key in self._cards:
            self._cards[key].set_capturing(False)
        get_logger().warning("Захват отменен")
    
    def get_missing_coordinates(self) -> list:
        """Получить список незаданных обязательных координат"""
        required = ["search_input", "search_clear", "buy_button"]
        config = get_config()
        missing = []
        
        for key in required:
            if config.get_coordinate(key) is None:
                if key in self._cards:
                    missing.append(self._cards[key].coord_name)
        
        return missing

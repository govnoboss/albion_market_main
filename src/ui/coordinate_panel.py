"""
Панель настройки координат
Карточки с кнопками захвата для каждой координаты
"""

from typing import Dict, Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea, QGridLayout,
    QGroupBox, QComboBox, QMessageBox, QInputDialog
)
from PyQt6.QtGui import QFont

from ..core.coordinate_capture import get_capture_manager
from ..utils.config import get_config
from ..utils.logger import get_logger


# Определение координат для захвата
COORDINATE_DEFINITIONS = {
    "basic": {
        "search_input": {
            "name": "🔍 Поле поиска",
            "description": "Клик для активации поиска",
            "type": "point"
        },
        "search_clear": {
            "name": "❌ Очистка поиска", 
            "description": "Кнопка очистки поля поиска",
            "type": "point"
        },
        "buy_button": {
            "name": "💰 Кнопка Купить",
            "description": "Основная кнопка покупки",
            "type": "point"
        },
    },
    "interaction": {
        "item_expand": {
            "name": "Раскрыть окно предмета",
            "description": "Кнопка стрелки для раскрытия лота",
            "type": "point"
        },
        "tier_dropdown": {
            "name": "Дропдаун Тиров",
            "description": "Выпадающий список выбора тира",
            "type": "point"
        },
        "enchant_dropdown": {
            "name": "Дропдаун Энчантов",
            "description": "Выпадающий список выбора зачарования",
            "type": "point"
        },
        "quality_dropdown": {
            "name": "Дропдаун Качеств",
            "description": "Выпадающий список выбора качества",
            "type": "point"
        },
        "menu_close": {
            "name": "Закрыть меню",
            "description": "Крестик или кнопка закрытия окна",
            "type": "point"
        },
    },
    "validation": {
        "market_menu_check": {
            "name": "🏪 Область Меню (OCR)",
            "description": "Заголовок окна рынка (для проверки открытия)",
            "type": "area"
        },
        "item_icon_check": {
            "name": "🖼️ Иконка Предмета",
            "description": "Область иконки текущего предмета (на будущее)",
            "type": "area"
        },
        "inventory_check_area": {
            "name": "🎒 Текст 'Рюкзак'",
            "description": "Заголовок окна инвентаря для авто-закрытия (OCR)",
            "type": "area"
        },
        "bank_check_area": {
            "name": "🏦 Текст 'Банк'",
            "description": "Заголовок окна банка для подтверждения открытия (OCR)",
            "type": "area"
        },
        "bank_tabs_point": {
            "name": "📑 Вкладки банка",
            "description": "Клик по основной вкладке банка (где сундуки)",
            "type": "point"
        },
        "bank_sets_tab_point": {
            "name": "👘 Вкладка Сеты",
            "description": "Клик по вкладке 'Комплекты' (Loadouts)",
            "type": "point"
        },
        "bank_select_set_point": {
            "name": "🔽 Выбрать комплект (Меню)",
            "description": "Клик по выпадающему списку комплектов (открыть список)",
            "type": "point"
        },
        "bank_first_set_point": {
            "name": "1️⃣ Первый сет в списке",
            "description": "Клик по ПЕРВОЙ строке в открытом списке комплектов",
            "type": "point"
        },
        "bank_equip_point": {
            "name": "⚔️ Экипировать",
            "description": "Кнопка 'Экипировать' в меню комплекта",
            "type": "point"
        },
        "bank_move_all_point": {
            "name": "📦 Переместить все",
            "description": "Кнопка перемещения всех вещей",
            "type": "point"
        },
        "bank_to_inventory_point": {
            "name": "⬇️ В инвентарь",
            "description": "Кнопка 'Взять' или перенос в сумку",
            "type": "point"
        },
        "bank_from_inventory_point": {
            "name": "⬆️ Из инвентаря",
            "description": "Кнопка 'Положить' или перенос в банк",
            "type": "point"
        }
    },
    "buyer": {
        "create_buy_order": {
            "name": "➕ Вкладка 'Создать Заказ'",
            "description": "Вкладка в окне рынка для создания ордера",
            "type": "point"
        },
        "quantity_input": {
            "name": "🔢 Ввод количества",
            "description": "Поле для ввода количества товара",
            "type": "point"
        },
        "price_input": {
            "name": "💰 Ввод цены",
            "description": "Поле для ввода цены за единицу",
            "type": "point"
        },
        "buyer_total_price": {
            "name": "💵 Итоговая сумма (OCR)",
            "description": "Область с общей стоимостью заказа (Total: ...)",
            "type": "area"
        }
    }
}


class CoordinateCard(QFrame):
    """Карточка для одной координаты"""
    
    capture_requested = pyqtSignal(str, str, str)  # key, display_name, mode
    
    def __init__(self, key: str, name: str, description: str, capture_mode: str = "point"):
        super().__init__()
        self.key = key
        self.coord_name = name
        self.description = description
        self.capture_mode = capture_mode
        
        self._setup_ui()
        self._load_saved_coordinate()
    
    def _setup_ui(self):
        self.setObjectName("card")
        self.setMinimumHeight(80)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(15)
        
        # Левая часть
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        name_label = QLabel(self.coord_name)
        name_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #f0f6fc;")
        name_label.setWordWrap(True)
        info_layout.addWidget(name_label)
        
        desc_label = QLabel(self.description)
        desc_label.setStyleSheet("font-size: 12px; color: #8b949e;")
        desc_label.setWordWrap(True)
        info_layout.addWidget(desc_label)
        
        layout.addLayout(info_layout, stretch=1)
        
        # Центр
        self.coord_label = QLabel("Не задано")
        self._set_label_style(False)
        self.coord_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.coord_label)
        
        # Правая часть
        self.capture_btn = QPushButton("Выбрать" if self.capture_mode == "area" else "Захватить")
        self.capture_btn.setObjectName("capture")
        self.capture_btn.setMinimumWidth(100)
        self.capture_btn.clicked.connect(self._on_capture_clicked)
        layout.addWidget(self.capture_btn)
        
        # Очистка
        self.clear_btn = QPushButton("✕")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent; border: 1px solid #30363d;
                border-radius: 4px; padding: 6px 10px; color: #8b949e;
                min-width: 30px; max-width: 30px;
            }
            QPushButton:hover {
                background-color: #da3633; border-color: #da3633; color: #f0f6fc;
            }
        """)
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        self.clear_btn.setVisible(False)
        layout.addWidget(self.clear_btn)

        self.setMinimumWidth(450)
    
    def _set_label_style(self, success: bool):
        color = "#3fb950" if success else "#8b949e"
        self.coord_label.setStyleSheet(f"""
            font-size: 13px; color: {color}; font-family: 'Consolas', monospace;
            padding: 5px 10px; background-color: #0d1117; border-radius: 4px; min-width: 100px;
        """)

    def _load_saved_coordinate(self):
        config = get_config()
        if self.capture_mode == "point":
            coord = config.get_coordinate(self.key)
            if coord: self.set_point(coord[0], coord[1])
        else:
            area = config.get_coordinate_area(self.key)
            if area: self.set_area(area['x'], area['y'], area['w'], area['h'])
    
    def _on_capture_clicked(self):
        self.capture_requested.emit(self.key, self.coord_name, self.capture_mode)
    
    def _on_clear_clicked(self):
        config = get_config()
        config.clear_coordinate(self.key)
        self.coord_label.setText("Не задано")
        self._set_label_style(False)
        self.clear_btn.setVisible(False)
        get_logger().info(f"Координата '{self.coord_name}' очищена")
    
    def set_point(self, x: int, y: int):
        self.coord_label.setText(f"X: {x}, Y: {y}")
        self._set_label_style(True)
        self.clear_btn.setVisible(True)

    def set_area(self, x: int, y: int, w: int, h: int):
        self.coord_label.setText(f"Area: {w}x{h}")
        self.coord_label.setToolTip(f"X:{x}, Y:{y}, W:{w}, H:{h}")
        self._set_label_style(True)
        self.clear_btn.setVisible(True)
    
    def set_capturing(self, is_capturing: bool):
        self.capture_btn.setEnabled(not is_capturing)
        self.capture_btn.setText("..." if is_capturing else ("Выбрать" if self.capture_mode == "area" else "Захватить"))


class CoordinatePanel(QWidget):
    """Панель настройки всех координат"""
    
    def __init__(self):
        super().__init__()
        self._cards: Dict[str, CoordinateCard] = {}
        self._setup_ui()
        self._refresh_profiles() # Load profiles on init
        self._connect_capture_manager()
    
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(20)
        
        header = QLabel("⚙️ Настройка координат")
        header.setObjectName("sectionHeader")
        content_layout.addWidget(header)
        
        info = QLabel("Настройте точки кликов и области проверок")
        info.setStyleSheet("color: #8b949e; font-size: 13px; margin-bottom: 10px;")
        content_layout.addWidget(info)
        
        self._setup_profiles_ui(content_layout) # Add profiles section

        group_names = {
            "basic": "⚙️ Основные координаты",
            "interaction": "🖱️ Взаимодействие с меню",
            "validation": "🛡️ Проверки (Валидация)"
        }
        
        # Сортировка групп для порядка отображения
        for group_key in ["basic", "interaction", "validation"]:
            if group_key not in COORDINATE_DEFINITIONS: continue
            
            coords = COORDINATE_DEFINITIONS[group_key]
            group_box = QGroupBox(group_names.get(group_key, group_key))
            group_layout = QVBoxLayout(group_box)
            group_layout.setSpacing(10)
            
            for coord_key, coord_info in coords.items():
                card = CoordinateCard(
                    key=coord_key,
                    name=coord_info["name"],
                    description=coord_info["description"],
                    capture_mode=coord_info.get("type", "point")
                )
                card.capture_requested.connect(self._start_capture)
                group_layout.addWidget(card)
                self._cards[coord_key] = card
            
            content_layout.addWidget(group_box)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
    
    def _connect_capture_manager(self):
        capture = get_capture_manager()
        capture.coordinate_captured.connect(self._on_coordinate_captured)
        capture.area_captured.connect(self._on_area_captured)
        capture.capture_cancelled.connect(self._on_capture_cancelled)
        capture.capture_started.connect(self._on_capture_started)
    
    def _start_capture(self, key: str, display_name: str, mode: str):
        capture = get_capture_manager()
        capture.start_capture(key, display_name, mode)
    
    def _on_capture_started(self, key: str, mode: str):
        if key in self._cards:
            self._cards[key].set_capturing(True)
        get_logger().info(f"Захват '{key}' начат (mode={mode})")
    
    def _on_coordinate_captured(self, key: str, x: int, y: int):
        get_config().set_coordinate(key, x, y)
        if key in self._cards:
            self._cards[key].set_point(x, y)
            self._cards[key].set_capturing(False)
        get_logger().success(f"Точка '{key}' сохранена: {x}, {y}")

    def _on_area_captured(self, key: str, x: int, y: int, w: int, h: int):
        get_config().set_coordinate_area(key, x, y, w, h)
        if key in self._cards:
            self._cards[key].set_area(x, y, w, h)
            self._cards[key].set_capturing(False)
        get_logger().success(f"Область '{key}' сохранена: {w}x{h}")
    
    def _on_capture_cancelled(self, key: str):
        if key in self._cards:
            self._cards[key].set_capturing(False)
        get_logger().warning("Захват отменен")
    
    
    def get_missing_coordinates(self) -> list:
        required = ["search_input", "search_clear", "buy_button"]
        config = get_config()
        missing = []
        for key in required:
            if config.get_coordinate(key) is None:
                if key in self._cards:
                    missing.append(self._cards[key].coord_name)
        return missing

    def _setup_profiles_ui(self, parent_layout):
        """Создание секции управления профилями"""
        group = QGroupBox("📁 Профили координат")
        group_layout = QVBoxLayout(group)
        
        # Row with controls
        controls_layout = QHBoxLayout()
        
        self.profiles_combo = QComboBox()
        self.profiles_combo.setPlaceholderText("Выберите профиль...")
        self.profiles_combo.setMinimumWidth(150)
        
        load_btn = QPushButton("Загрузить")
        load_btn.clicked.connect(self._on_load_profile)
        
        save_btn = QPushButton("Сохранить...")
        save_btn.clicked.connect(self._on_save_profile)
        
        del_btn = QPushButton("Удалить")
        del_btn.setStyleSheet("""
            QPushButton { background-color: #4a3b3b; }
            QPushButton:hover { background-color: #bd3b3b; }
        """)
        del_btn.clicked.connect(self._on_delete_profile)
        
        controls_layout.addWidget(self.profiles_combo, stretch=1)
        controls_layout.addWidget(load_btn)
        controls_layout.addWidget(save_btn)
        controls_layout.addWidget(del_btn)
        
        group_layout.addLayout(controls_layout)
        parent_layout.addWidget(group)

    def _refresh_profiles(self):
        """Обновить список профилей в ComboBox"""
        current = self.profiles_combo.currentText()
        self.profiles_combo.clear()
        
        profiles = get_config().get_profiles_list()
        self.profiles_combo.addItems(profiles)
        
        # Restore selection if possible
        index = self.profiles_combo.findText(current)
        if index >= 0:
            self.profiles_combo.setCurrentIndex(index)

    def _on_save_profile(self):
        name, ok = QInputDialog.getText(self, "Сохранить профиль", "Введите название профиля:")
        if ok and name:
            if get_config().save_profile(name):
                QMessageBox.information(self, "Успех", f"Профиль '{name}' сохранен!")
                self._refresh_profiles()
                # Select the new profile
                self.profiles_combo.setCurrentText(name)
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось сохранить профиль.\nПроверьте имя и права доступа.")

    def _on_load_profile(self):
        name = self.profiles_combo.currentText()
        if not name:
            return
            
        reply = QMessageBox.question(
            self, "Подтверждение", 
            f"Загрузить профиль '{name}'?\nТекущие координаты будут перезаписаны!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if get_config().load_profile(name):
                QMessageBox.information(self, "Успех", f"Профиль '{name}' загружен!")
                self._refresh_coordinates_ui()
            else:
                QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить профиль '{name}'.")

    def _on_delete_profile(self):
        name = self.profiles_combo.currentText()
        if not name:
            return
            
        reply = QMessageBox.question(
            self, "Подтверждение", 
            f"Удалить профиль '{name}' навсегда?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if get_config().delete_profile(name):
                QMessageBox.information(self, "Успех", f"Профиль '{name}' удален.")
                self._refresh_profiles()
            else:
                QMessageBox.warning(self, "Ошибка", f"Не удалось удалить профиль '{name}'.")

    def _refresh_coordinates_ui(self):
        """Обновить все карточки текущими значениями из конфига"""
        # This is a bit duplicative of logic inside cards, but we need to force refresh
        # Ideally, cards should listen to a config change signal. 
        # For now, we will iterate and explicitly reload.
        for card in self._cards.values():
            card._load_saved_coordinate() 
            # Note: accessing protected member for pragmatic reasons, 
            # should expose public reload method in CoordinateCard ideally.


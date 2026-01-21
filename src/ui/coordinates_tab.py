"""
Вкладка управления координатами
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QScrollArea, QFrame, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSlot

from ..utils.config import get_config
from ..core.coordinate_capture import get_capture_manager

class CoordinatesTab(QWidget):
    def __init__(self):
        super().__init__()
        self.config = get_config()
        self.capture = get_capture_manager()
        
        self._setup_ui()
        self._connect_signals()
        self._refresh_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Управление координатами")
        header.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)
        
        instruction = QLabel(
            "Для точечных координат: нажмите 'Задать', затем кликните в нужном месте.\n"
            "Для областей (OCR): нажмите 'Задать', затем выделите область с зажатой мышью."
        )
        instruction.setStyleSheet("color: #888; margin-bottom: 10px;")
        layout.addWidget(instruction)
        
        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setSpacing(15)
        
        # Define categories
        self.categories = {
            "Поиск и Покупка": [
                ("search_input", "Поле поиска", "point"),
                ("search_clear", "Очистка поиска", "point"),
                ("buy_button", "Кнопка Купить", "point"),
                ("item_expand", "Раскрыть лот", "point"),
                ("create_buy_order", "Вкладка Заказ", "point"),
                ("menu_close", "Закрыть меню", "point"),
            ],
            "Фильтры": [
                ("tier_dropdown", "Меню Тира", "point"),
                ("enchant_dropdown", "Меню Чары", "point"),
                ("quality_dropdown", "Меню Качества", "point"),
            ],
            "OCR (Распознавание / Валидация)": [
                ("quality_text_region", "Текст Качества", "area"),
                ("market_menu_check", "Заголовок Рынка (Меню)", "area"),
                ("item_icon_check", "Иконка Предмета", "area"),
                ("best_price_area", "Цена (Топ лот)", "area"),
            ]
        }
        
        self.coord_widgets = {}  # key -> value_label
        
        for category, items in self.categories.items():
            group = QGroupBox(category)
            group_layout = QVBoxLayout(group)
            
            for key, name, mode in items:
                row = self._create_coord_row(key, name, mode)
                group_layout.addLayout(row)
                
            self.content_layout.addWidget(group)
            
        self.content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _create_coord_row(self, key, name, mode):
        layout = QHBoxLayout()
        
        name_lbl = QLabel(name)
        name_lbl.setMinimumWidth(120)
        
        val_lbl = QLabel("Не задано")
        val_lbl.setStyleSheet("color: #666;")
        self.coord_widgets[key] = val_lbl
        
        set_btn = QPushButton("Задать")
        set_btn.setFixedWidth(70)
        set_btn.clicked.connect(lambda checked, k=key, n=name, m=mode: self._start_capture(k, n, m))
        
        layout.addWidget(name_lbl)
        layout.addWidget(val_lbl, stretch=1)
        layout.addWidget(set_btn)
        
        if mode == 'area':
            # Выбор названия кнопки теста
            if key == "market_menu_check":
                test_label = "Test Check"
            elif key == "best_price_area":
                test_label = "Test Price"
            else:
                test_label = "Test OCR"
                
            test_btn = QPushButton(test_label)
            test_btn.setFixedWidth(80)
            test_btn.setStyleSheet("""
                QPushButton { background-color: #238636; }
                QPushButton:hover { background-color: #2ea043; }
            """)
            test_btn.clicked.connect(lambda checked, k=key: self._test_area(k))
            layout.addWidget(test_btn)
        
        clear_btn = QPushButton("Сброс")
        clear_btn.setFixedWidth(60)
        # Style for clear button
        clear_btn.setStyleSheet("""
            QPushButton { background-color: #4a3b3b; }
            QPushButton:hover { background-color: #bd3b3b; }
        """)
        clear_btn.clicked.connect(lambda checked, k=key: self._clear_coord(k))
        
        layout.addWidget(clear_btn)
        
        return layout

    def _connect_signals(self):
        self.capture.coordinate_captured.connect(self._on_captured)
        self.capture.area_captured.connect(self._on_area_captured)

    def _start_capture(self, key, name, mode):
        # Disable all buttons temporarily could be added here
        self.capture.start_capture(key, name, mode)

    @pyqtSlot(str, int, int)
    def _on_captured(self, key, x, y):
        self.config.set_coordinate(key, x, y)
        self._refresh_values()

    @pyqtSlot(str, int, int, int, int)
    def _on_area_captured(self, key, x, y, w, h):
        self.config.set_coordinate_area(key, x, y, w, h)
        self._refresh_values()
        
        # Если это зона валидации -> сохраняем эталонное изображение
        validation_keys = ["market_menu_check", "item_icon_check"]
        if key in validation_keys:
            try:
                import os
                from PIL import ImageGrab
                
                # Создаем папку resources если нет
                resources_dir = os.path.join(os.getcwd(), "resources")
                os.makedirs(resources_dir, exist_ok=True)
                
                # Захват и сохранение
                bbox = (x, y, x + w, y + h)
                img = ImageGrab.grab(bbox=bbox)
                save_path = os.path.join(resources_dir, f"ref_{key}.png")
                img.save(save_path)
                
                # Логируем
                from ..utils.logger import get_logger
                get_logger().success(f"📸 Эталон изображения сохранен: {save_path}")
                
            except Exception as e:
                from ..utils.logger import get_logger
                get_logger().error(f"Ошибка сохранения эталона: {e}")

    def _clear_coord(self, key):
        self.config.clear_coordinate(key)
        self._refresh_values()

    def _test_area(self, key):
        """Тест OCR или Валидатора для заданной области"""
        area = self.config.get_coordinate_area(key)
        if not area:
            QMessageBox.warning(self, "Ошибка", f"Область '{key}' не задана!")
            return
            
        # 1. Спец. проверка для Меню Рынка (Валидатор)
        if key == "market_menu_check":
            from ..core.validator import ScreenValidator
            is_open, msg = ScreenValidator.check_market_open(area)
            
            if is_open:
                QMessageBox.information(self, "✅ Проверка успешна", 
                    f"Результат: OPEN\n\nПодробности: {msg}")
            else:
                QMessageBox.warning(self, "❌ Проверка провалена", 
                    f"Результат: CLOSED\n\nПодробности: {msg}")
            return
            
        # 2. Спец. проверка для Цены (Parser)
        if key == "best_price_area":
            from ..utils.ocr import read_price_at
            
            price = read_price_at(area)
            if price is not None:
                QMessageBox.information(self, "✅ Цена распознана", 
                    f"Результат: {price}\n(Тип: {type(price)})")
            else:
                QMessageBox.warning(self, "⚠️ Не удалось распознать", 
                    "Результат: None\n\nПроверьте, что в зоне только цифры.")
            return

        # 3. Обычный OCR тест (для остальных)
        from ..utils.ocr import read_screen_text
        
        try:
            text = read_screen_text(area['x'], area['y'], area['w'], area['h'])
            QMessageBox.information(
                self, 
                "Результат OCR", 
                f"Распознанный текст:\n\n'{text}'\n\n(Длина: {len(text)})"
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка OCR", str(e))

    def _refresh_values(self):
        coords = self.config.get_all_coordinates()
        for key, label in self.coord_widgets.items():
            if key in coords:
                data = coords[key]
                if data.get('type') == 'area':
                    text = f"X: {data['x']}, Y: {data['y']} [W: {data['w']}, H: {data['h']}]"
                else:
                    text = f"X: {data['x']}, Y: {data['y']}"
                label.setText(text)
                label.setStyleSheet("color: #0f0;") # Green for set
            else:
                label.setText("Не задано")
                label.setStyleSheet("color: #888;")

    def _refresh_values(self):
        coords = self.config.get_all_coordinates()
        for key, label in self.coord_widgets.items():
            if key in coords:
                data = coords[key]
                if data.get('type') == 'area':
                    text = f"X: {data['x']}, Y: {data['y']} [W: {data['w']}, H: {data['h']}]"
                else:
                    text = f"X: {data['x']}, Y: {data['y']}"
                label.setText(text)
                label.setStyleSheet("color: #0f0;") # Green for set
            else:
                label.setText("Не задано")
                label.setStyleSheet("color: #888;")

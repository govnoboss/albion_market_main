"""
Вкладка управления координатами
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QScrollArea, QFrame, QGroupBox, QMessageBox, QComboBox, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer

from ..utils.config import get_config
from ..utils.logger import get_logger
from ..utils.localization import get_text
from ..core.coordinate_capture import get_capture_manager
from ..utils.paths import get_app_root

class CoordinatesTab(QWidget):
    def __init__(self):
        super().__init__()
        self.config = get_config()
        self.logger = get_logger()
        self.capture = get_capture_manager()
        
        self._setup_ui()
        self._refresh_profiles() # Load profiles
        self._connect_signals()
        self._refresh_values()

    def showEvent(self, event):
        """Обновить значения при каждом показе вкладки"""
        super().showEvent(event)
        self._refresh_values()
        self._refresh_profiles()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel(get_text("coord_header", "Управление координатами"))
        header.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 2px;")
        layout.addWidget(header)
        
        instruction = QLabel(get_text("coord_instruction", "Для точечных координат: нажмите 'Задать', наведите курсор и нажмите F1..."))
        instruction.setStyleSheet("color: #888; margin-bottom: 2px;")
        instruction.setWordWrap(True)
        layout.addWidget(instruction)
 
        # Wizard Button
        wizard_btn = QPushButton(get_text("coord_wizard_btn", "🪄 Запустить Мастер настройки"))
        wizard_btn.setStyleSheet("""
            QPushButton {
                background-color: #fca326; 
                color: #0d1117;
                font-weight: bold;
                padding: 8px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #e69d00; }
        """)
        wizard_btn.clicked.connect(self._start_wizard)
        layout.addWidget(wizard_btn)

        self._check_first_run()

        self._setup_profiles_ui(layout) # Add profiles UI
        
        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setSpacing(10)
        
        # Define categories
        self.categories = {
            get_text("coord_cat_main", "Основное меню рынка"): [
                ("search_input", get_text("coord_item_search_input", "Поле поиска"), "point"),
                ("search_clear", get_text("coord_item_search_clear", "Очистка поиска"), "point"),
                ("buy_button", get_text("coord_item_buy_btn", "Купить предмет"), "point"),
                ("item_sort", get_text("coord_item_sort", "Сортировка предмета"), "point"),
                # OCR
                ("market_name_area", get_text("coord_market_name_ocr", "Название Рынка (OCR)"), "area"),
                
                # Выпадающие списки
                ("tier_dropdown", get_text("coord_tier_dropdown", "Выпадающий список Тиров"), "point"),
                ("enchant_dropdown", get_text("coord_enchant_dropdown", "Выпадающий список Чары"), "point"),
                ("quality_dropdown", get_text("coord_quality_dropdown", "Выпадающий список Качества"), "point"),
                
                ("item_name_area", get_text("coord_item_name_ocr", "Название предмета (OCR)"), "area"),
                
                ("best_price_area", get_text("coord_best_price_ocr", "Цена за 1шт предмета (OCR)"), "area"), 
            ],
            get_text("coord_cat_item_menu", "Окно меню предмета"): [
                # Основные кнопки
                ("item_expand", get_text("coord_item_expand", "Раскрыть цену предмета"), "point"),
                # Элементы ордера
                ("buyer_amount_input", get_text("coord_amount_input", "Кнопка Количество (Ввод)"), "point"),
                ("buyer_create_order_confirm", get_text("coord_create_order_confirm", "Кнопка Заказать (confirm)"), "point"),
                ("menu_close", get_text("coord_menu_close", "Крестик закрытия меню предмета"), "point"),
 
                # OCR зоны
                ("item_menu_check", get_text("coord_item_menu_check", "Надпись 'Заказы на продажу' (Check)"), "area"),
                ("buyer_top_lot_qty", get_text("coord_top_lot_qty", "Кол-во в топ лоте (OCR)"), "area"),
                ("buyer_total_price", get_text("coord_total_price", "Итоговая стоимость (OCR)"), "area"),
            ],
            get_text("coord_cat_bm", "Black Market"): [
                ("bm_sell_tab", get_text("coord_bm_sell_tab", "Вкладка 'Продать'"), "point"),
                ("bm_settings_btn", get_text("coord_bm_settings", "Кнопка Настройки"), "point"),
                ("bm_logout_btn", get_text("coord_bm_logout", "Кнопка Выйти"), "point"),
                ("bm_login_btn", get_text("coord_bm_login", "▶Кнопка Войти"), "point"),
                ("bm_char1_area", get_text("coord_bm_char1", "Аватарка Персонаж 1"), "area"),
                ("bm_char2_area", get_text("coord_bm_char2", "Аватарка Персонаж 2"), "area"),
                # New Coordinates
                ("bm_tier_dropdown", get_text("coord_bm_tier", "BM: Список Тиров"), "point"),
                ("bm_enchant_dropdown", get_text("coord_bm_enchant", "BM: Список Чары"), "point"),
                ("bm_price_area", get_text("coord_bm_price_ocr", "BM: Цена топ лота (OCR)"), "area"),
            ],
        }
        
        self.coord_widgets = {}  # key -> value_label
        
        for category, items in self.categories.items():
            group = QGroupBox() # Без заголовка, делаем свой
            group_layout = QVBoxLayout(group)
            
            # --- Заголовок Раздела ---
            header_layout = QHBoxLayout()
            cat_label = QLabel(category)
            cat_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #58a6ff;")
            
            # Кнопка помощи раздела
            help_btn = QPushButton("?")
            help_btn.setFixedSize(32, 32)
            help_btn.setCursor(Qt.CursorShape.WhatsThisCursor)
            help_btn.setToolTip(f"Показать справку для раздела '{category}'")
            help_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #58a6ff;
                    border: none;
                    border-radius: 16px;
                    font-size: 18px;
                    font-weight: bold;
                    padding: 0;
                    margin: 0;
                    text-align: center;
                }
                QPushButton:hover {
                    color: #79c0ff;
                    background-color: rgba(88, 166, 255, 0.1);
                }
            """)
            # Передаем category как key для поиска картинки
            help_btn.clicked.connect(lambda checked, c=category: self._show_help_image(c, c)) # key=category name
            
            header_layout.addWidget(cat_label)
            header_layout.addWidget(help_btn)
            header_layout.addStretch()
            
            group_layout.addLayout(header_layout)
            
            # Разделитель
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setFrameShadow(QFrame.Shadow.Sunken)
            line.setStyleSheet("background-color: #30363d; margin-bottom: 2px;")
            group_layout.addWidget(line)
            
            # --- Элементы (с нумерацией) ---
            for i, (key, name, mode) in enumerate(items, 1):
                row = self._create_coord_row(key, name, mode, i)
                group_layout.addLayout(row)
                
            self.content_layout.addWidget(group)
            
        self.content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _create_coord_row(self, key, name, mode, index):
        layout = QHBoxLayout()
        
        # Нумерация: "1. Название"
        numbered_name = f"{index}. {name}"
        name_lbl = QLabel(numbered_name)
        name_lbl.setMinimumWidth(150)
        
        val_lbl = QLabel(get_text("coord_not_set", "Не задано"))
        val_lbl.setStyleSheet("color: #666;")
        self.coord_widgets[key] = val_lbl
        
        set_btn = QPushButton(get_text("coord_btn_set", "Задать"))
        set_btn.setFixedWidth(80)
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
            test_btn.setFixedWidth(90)
            test_btn.setStyleSheet("""
                QPushButton { background-color: #238636; }
                QPushButton:hover { background-color: #2ea043; }
            """)
            test_btn.clicked.connect(lambda checked, k=key: self._test_area(k))
            layout.addWidget(test_btn)
        
        clear_btn = QPushButton(get_text("coord_btn_reset", "Сброс"))
        clear_btn.setFixedWidth(70)
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

    def _show_help_image(self, key, name):
        """Показать картинку-подсказку для координаты"""
        import os
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QMessageBox
        from PyQt6.QtGui import QPixmap
        
        # Путь к картинке подсказки
        help_dir = get_app_root() / "resources" / "help"
        help_dir.mkdir(parents=True, exist_ok=True)
        image_path = help_dir / f"{key}.png"
        
        # Если картинки нет — предлагаем создать
        if not os.path.exists(image_path):
            reply = QMessageBox.question(
                self, get_text("coord_help_img_not_found", "Картинка не найдена"),
                get_text("coord_help_img_missing", "Картинка-подсказка для '{name}' отсутствует...").format(name=name),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self._start_help_capture(key, name)
            return

        # Создаем диалог (сохраняем в self, чтобы не удалился сборщиком мусора)
        if hasattr(self, '_help_dialog') and self._help_dialog:
            self._help_dialog.close()
            
        self._help_dialog = QDialog(self)
        self._help_dialog.setWindowTitle(f"📖 {name}")
        # Ресайзабельное окно поверх остальных
        self._help_dialog.setWindowFlags(
            Qt.WindowType.Window | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        from .styles import HELP_DIALOG_STYLE
        self._help_dialog.setStyleSheet(HELP_DIALOG_STYLE)
        
        layout = QVBoxLayout(self._help_dialog)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Картинка масштабируется вместе с окном
        img_label = QLabel()
        pixmap = QPixmap(str(image_path))
        img_label.setPixmap(pixmap)
        img_label.setScaledContents(True)  # Картинка растягивается за лейблом
        img_label.setMinimumSize(1, 1)     # Разрешаем сжимать меньше исходного размера
        layout.addWidget(img_label)
        
        # Начальный размер — подогнать под картинку, но не больше 1000x700
        w = min(pixmap.width() + 10, 1000)
        h = min(pixmap.height() + 30, 700)
        self._help_dialog.resize(w, h)
        self._help_dialog.show()

    def _start_help_capture(self, key, name):
        """Запуск захвата области для справки"""
        from .overlay import AreaSelectionOverlay
        
        # Сохраняем контекст
        self._help_capture_key = key
        self._help_capture_name = name
        
        self._help_overlay = AreaSelectionOverlay()
        self._help_overlay.area_selected.connect(self._on_help_captured)
        self._help_overlay.show()
        
    def _on_help_captured(self, x, y, w, h):
        """Обработка захваченной области справки"""
        import os
        from PIL import ImageGrab
        
        key = getattr(self, '_help_capture_key', None)
        name = getattr(self, '_help_capture_name', None)
        
        if not key:
            return
            
        try:
            # Скриншот
            bbox = (x, y, x + w, y + h)
            img = ImageGrab.grab(bbox=bbox)
            
            # Путь
            help_dir = get_app_root() / "resources" / "help"
            help_dir.mkdir(parents=True, exist_ok=True)
            save_path = help_dir / f"{key}.png"
            
            img.save(save_path)
            
            # Показываем результат с небольшой задержкой, чтобы оверлей успел закрыться
            QTimer.singleShot(100, lambda: self._show_help_image(key, name))
            
        except Exception as e:
            QMessageBox.critical(self, get_text("coord_msg_error", "Ошибка"), f"{get_text('coord_profile_save_err', 'Не удалось сохранить скриншот')}:\n{e}")
        
        finally:
            if self._help_overlay:
                self._help_overlay.close()
            self._help_overlay = None # Cleanup

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
        validation_keys = ["market_menu_check", "item_name_area", "ui_avatar_check", "bm_char1_area", "bm_char2_area"]
        if key in validation_keys:
            try:
                import os
                from PIL import ImageGrab
                
                # Создаем папку resources если нет
                resources_dir = get_app_root() / "resources"
                resources_dir.mkdir(parents=True, exist_ok=True)
                
                # Захват и сохранение
                bbox = (x, y, x + w, y + h)
                img = ImageGrab.grab(bbox=bbox)
                save_path = resources_dir / f"ref_{key}.png"
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
            QMessageBox.warning(self, get_text("coord_msg_error", "Ошибка"), f"{get_text('coord_msg_error', 'Область')} '{key}' {get_text('coord_not_set', 'не задана')}!")
            return
            
        # 1. Спец. проверка для Меню Рынка (Валидатор)
        if key == "market_menu_check":
            from ..core.validator import ScreenValidator
            is_open, msg = ScreenValidator.check_market_open(area)
            
            if is_open:
                QMessageBox.information(self, get_text("coord_ocr_test_success", "✅ Проверка успешна"), 
                    f"Результат: OPEN\n\nПодробности: {msg}")
            else:
                QMessageBox.warning(self, get_text("coord_ocr_test_fail", "❌ Проверка провалена"), 
                    f"Результат: CLOSED\n\nПодробности: {msg}")
            return
            
        # 2. Спец. проверка для Цены (Parser)
        if key == "best_price_area":
            from ..utils.ocr import read_price_at
            
            price = read_price_at(area)
            if price is not None:
                QMessageBox.information(self, get_text("coord_ocr_test_success", "✅ Цена распознана"), 
                    f"Результат: {price}\n(Тип: {type(price)})")
            else:
                QMessageBox.warning(self, get_text("coord_ocr_test_fail", "⚠️ Не удалось распознать"), 
                    get_text("coord_msg_error", "Проверьте, что в зоне только цифры."))
            return

        # 2.4 TEMPLATE MATCH TEST (BM Char)
        if key in ["bm_char1_area", "bm_char2_area"]:
            import os
            from ..utils.image_utils import find_image_on_screen
            
            ref_path = get_app_root() / "resources" / f"ref_{key}.png"
            if not os.path.exists(ref_path):
                 QMessageBox.warning(self, get_text("coord_msg_error", "Ошибка"), f"{get_text('coord_help_img_not_found', 'Нет эталона')}: {ref_path}\n{get_text('coord_instruction', 'Сначала задайте область')}!")
                 return
                 
            # Search
            found = find_image_on_screen(ref_path, confidence=0.85)
            
            if found:
                 QMessageBox.information(self, get_text("coord_ocr_test_success", "✅ Template Match"), 
                     f"Изображение НАЙДЕНО!\n\nКоординаты центра: {found}\n(Поиск по всему экрану)")
            else:
                 QMessageBox.warning(self, get_text("coord_ocr_test_fail", "❌ Template Match"), 
                     "Изображение НЕ НАЙДЕНО на экране.\n\nПроверьте, что оно видимо и не перекрыто.")
            return

        # 2.5. Спец. проверка для Проверки UI (Avatar Pixel Match - Fixed Area)
        if key in ["ui_avatar_check"]:
            import os
            import numpy as np
            from PIL import Image, ImageGrab, ImageChops
            
            ref_path = get_app_root() / "resources" / f"ref_{key}.png"
            if not os.path.exists(ref_path):
                QMessageBox.warning(self, get_text("coord_msg_error", "Ошибка"), f"{get_text('coord_help_img_not_found', 'Нет эталона')}: {ref_path}\n{get_text('coord_instruction', 'Сначала задайте область')}!")
                return
                
            # Захват текущего
            bbox = (area['x'], area['y'], area['x'] + area['w'], area['y'] + area['h'])
            current_img = ImageGrab.grab(bbox=bbox)
            ref_img = Image.open(ref_path).convert('RGB')
            current_img = current_img.resize(ref_img.size) # На всякий случай
            
            # Сравнение (Standardized)
            from ..utils.image_utils import find_image_on_screens
            mean_diff = find_image_on_screens(ref_img, current_img)
            
            # Разница для генерации debug изображения (визуализации)
            if ref_img.size != current_img.size:
                current_img_resized = current_img.resize(ref_img.size)
                diff = ImageChops.difference(ref_img, current_img_resized)
            else:
                 diff = ImageChops.difference(ref_img, current_img)
            
            # Чем меньше mean_diff, тем больше похожесть
            # E.g. 0 = копия. > 50 = сильно отличается.
            
            is_match = mean_diff < 15.0 # Порог
            
            # --- DEBUG SAVE ---
            resources_dir = get_app_root() / "resources"
            debug_curr_path = resources_dir / f"debug_current_{key}.png"
            debug_diff_path = resources_dir / f"debug_diff_{key}.png"
            
            try:
                current_img.save(debug_curr_path)
                diff.save(debug_diff_path)
            except Exception as e:
                get_logger().error(f"Debug save error: {e}")

            status = "👁️ Аватар на месте (UI Visible)" if is_match else "🕶️ Аватар скрыт (UI Hidden) или изменен"
            
            msg = (
                f"Статус: {status}\n"
                f"Различие (Mean Diff): {mean_diff:.2f}\n"
                f"(Порог < 15.0 -> Match)\n\n"
                f"Дебаг файлы сохранены в resources/:\n"
                f"- debug_current_{key}.png (То что видим сейчас)\n"
                f"- debug_diff_{key}.png (Разница с эталоном)"
            )
            
            QMessageBox.information(self, "Pixel Check", msg)
            return

        # 2.6. Спец. проверка для текста (Travel Mode -> RUS, Market Name -> ENG)
        if key == "travel_mode_text":
            from ..utils.ocr import read_screen_text
            text = read_screen_text(area['x'], area['y'], area['w'], area['h'], lang='rus')
            QMessageBox.information(self, f"{get_text('coord_ocr_result', 'OCR Result')} (RUS)", 
                f"Результат: '{text}'\n\n(Russian OCR)")
            return

            QMessageBox.information(self, f"{get_text('coord_ocr_result', 'OCR Result')} (ENG)", 
                f"Результат: '{text}'\n\n(English OCR)")
            return

        if key in ["inventory_check_area", "bank_check_area"]:
            from ..utils.ocr import read_screen_text
            # Используем rus+eng, так как Рюкзак=Rus, Bank=Eng (возможно)
            text = read_screen_text(area['x'], area['y'], area['w'], area['h'], lang='rus+eng')
            QMessageBox.information(self, f"{get_text('coord_ocr_result', 'OCR Result')} ({key})", 
                f"Результат: '{text}'")
            return

        # 3. Обычный OCR тест (для остальных)
            from ..utils.ocr import read_screen_text
            text = read_screen_text(area['x'], area['y'], area['w'], area['h'], lang='eng')
            QMessageBox.information(self, f"{get_text('coord_ocr_result', 'OCR Result')} (ENG)", 
                f"Результат: '{text}'\n\n(English OCR)")
            return

        # 3. Обычный OCR тест (для остальных)
        from ..utils.ocr import read_screen_text
        
        try:
            text = read_screen_text(area['x'], area['y'], area['w'], area['h'])
            QMessageBox.information(
                self, 
                get_text("coord_ocr_result", "Результат OCR"), 
                f"Распознанный текст:\n\n'{text}'\n\n(Длина: {len(text)})"
            )
        except Exception as e:
            QMessageBox.critical(self, f"{get_text('coord_msg_error', 'Ошибка')} OCR", str(e))

    def _setup_profiles_ui(self, parent_layout):
        """Создание секции управления профилями"""
        group = QGroupBox(get_text("coord_profiles_group", "📁 Профили координат"))
        group_layout = QVBoxLayout(group)
        
        # Row with controls
        controls_layout = QHBoxLayout()
        
        self.profiles_combo = QComboBox()
        self.profiles_combo.setPlaceholderText(get_text("coord_profile_placeholder", "Выберите профиль..."))
        self.profiles_combo.setMinimumWidth(150)
        self.profiles_combo.setStyleSheet("""
            QComboBox {
                background-color: #161b22;
                color: #f0f6fc;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 5px 10px;
            }
            QComboBox:hover {
                border-color: #58a6ff;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #161b22;
                color: #f0f6fc;
                border: 1px solid #30363d;
                selection-background-color: #30363d;
            }
        """)
        
        load_btn = QPushButton(get_text("coord_btn_load", "Загрузить"))
        load_btn.clicked.connect(self._on_load_profile)
        
        save_btn = QPushButton(get_text("coord_btn_save", "Сохранить..."))
        save_btn.clicked.connect(self._on_save_profile)
        
        del_btn = QPushButton(get_text("coord_btn_delete", "Удалить"))
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
        
        profiles = self.config.get_profiles_list()
        self.profiles_combo.addItems(profiles)
        
        # Restore selection if possible
        index = self.profiles_combo.findText(current)
        if index >= 0:
            self.profiles_combo.setCurrentIndex(index)

    def _on_save_profile(self):
        dialog = QInputDialog(self)
        dialog.setWindowTitle(get_text("coord_btn_save", "Сохранить профиль"))
        dialog.setLabelText(get_text("coord_profiles_group", "Введите название профиля:"))
        dialog.setStyleSheet(self._get_dialog_style())
        
        if dialog.exec():
            name = dialog.textValue()
            if name:
                if self.config.save_profile(name):
                    self._show_message(get_text("coord_msg_success", "Успех"), get_text("coord_profile_saved", "Профиль '{name}' сохранен!").format(name=name))
                    self._refresh_profiles()
                    self.profiles_combo.setCurrentText(name)
                else:
                    self._show_message(get_text("coord_msg_error", "Ошибка"), get_text("coord_profile_save_err", "Не удалось сохранить профиль.\nПроверьте имя и права доступа."), is_warning=True)

    def _on_load_profile(self):
        name = self.profiles_combo.currentText()
        if not name:
            return
            
        if self._show_question(get_text("coord_msg_confirm", "Подтверждение"), get_text("coord_profile_load_confirm", "Загрузить профиль '{name}'?\nТекущие координаты будут перезаписаны!").format(name=name)):
            if self.config.load_profile(name):
                self._show_message(get_text("coord_msg_success", "Успех"), get_text("coord_profile_loaded", "Профиль '{name}' загружен!").format(name=name))
                self._refresh_values()
            else:
                self._show_message(get_text("coord_msg_error", "Ошибка"), get_text("coord_profile_load_err", "Не удалось загрузить профиль '{name}'.").format(name=name), is_warning=True)

    def _on_delete_profile(self):
        name = self.profiles_combo.currentText()
        if not name:
            return
            
        if self._show_question(get_text("coord_msg_confirm", "Подтверждение"), get_text("coord_profile_delete_confirm", "Удалить профиль '{name}' навсегда?").format(name=name)):
            if self.config.delete_profile(name):
                self._show_message(get_text("coord_msg_success", "Успех"), get_text("coord_profile_deleted", "Профиль '{name}' удален.").format(name=name))
                self._refresh_profiles()
            else:
                self._show_message(get_text("coord_msg_error", "Ошибка"), get_text("coord_profile_delete_err", "Не удалось удалить профиль '{name}'.").format(name=name), is_warning=True)

    def _get_dialog_style(self):
        """Темная тема для диалогов"""
        from .styles import COLORS
        return f"""
            QInputDialog, QMessageBox {{
                background-color: {COLORS['bg']};
                color: {COLORS['text']};
            }}
            QLabel {{
                color: {COLORS['text']};
            }}
            QLineEdit, QSpinBox {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 5px;
            }}
            QPushButton {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 5px 15px;
                min-width: 60px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['item_bg']};
            }}
        """

    def _show_message(self, title, text, is_warning=False):
        """Показать сообщение с темной темой"""
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setIcon(QMessageBox.Icon.Warning if is_warning else QMessageBox.Icon.Information)
        msg.setStyleSheet(self._get_dialog_style())
        msg.exec()

    def _show_question(self, title, text):
        """Показать диалог подтверждения с темной темой"""
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setStyleSheet(self._get_dialog_style())
        return msg.exec() == QMessageBox.StandardButton.Yes

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
                label.setStyleSheet("color: #888;")

    def _check_first_run(self):
        """Проверка на первый запуск (пустой конфиг)"""
        # Если координат нет - предлагаем запустить мастер
        if not self.config.get_all_coordinates():
             QTimer.singleShot(500, self._start_wizard)

    def _start_wizard(self):
        from .wizard_overlay import WizardOverlay
        
        # Если мастер уже запущен - не запускаем копию
        if hasattr(self, 'wizard') and self.wizard:
            self.wizard.close()
            
        # Скрываем главное окно
        if self.window():
            self.window().hide()
            
        self.wizard = WizardOverlay(self.categories)
        self.wizard.wizard_finished.connect(self._on_wizard_finished)
        self.wizard.showFullScreen()
        
    def _on_wizard_finished(self, success=False):
        self._refresh_values()
        
        # Восстанавливаем главное окно
        main_win = self.window()
        if main_win:
            self.logger.info(f"Restoring main window: {main_win}")
            main_win.show() # Force show
            main_win.showNormal()
            main_win.raise_()
            main_win.activateWindow()
        else:
            self.logger.warning("Could not restore main window: self.window() is None")
            
        if success:
            QMessageBox.information(self, "Мастер настройки", "✅ Настройка координат завершена!")
        
        self.wizard = None

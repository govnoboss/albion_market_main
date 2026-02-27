"""
Панель настроек приложения
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QSpinBox, QDoubleSpinBox, QGroupBox, QFormLayout, QCheckBox,
    QScrollArea, QComboBox, QMessageBox
)
from ..utils.config import get_config
from ..utils.logger import get_logger
from .calibration_overlay import CalibrationOverlay
from .styles import PANEL_STYLE
from ..utils.localization import get_text

class SettingsPanel(QScrollArea):
    """Панель глобальных настроек"""
    
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Оверлей калибровки
        self.overlay = CalibrationOverlay()
        
        # Убираем рамки
        self.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.content_widget = QWidget()
        self.content_widget.setObjectName("settingsContent") # Для CSS если нужно
        self.setWidget(self.content_widget)
        
        self._setup_ui()
        self._load_settings()
    
    def showEvent(self, event):
        """Обновить настройки при каждом показе вкладки"""
        super().showEvent(event)
        self._load_settings()
    
    def _setup_ui(self):
        main_layout = QHBoxLayout(self.content_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(25)
        
        # Left and Right Columns
        left_col = QVBoxLayout()
        left_col.setSpacing(20)
        right_col = QVBoxLayout()
        right_col.setSpacing(20)
        
        main_layout.addLayout(left_col, stretch=1)
        main_layout.addLayout(right_col, stretch=1)
        
        # Helper to style GroupBoxes
        def style_groupbox(gb, title):
            gb.setTitle(title.upper())
            gb.setStyleSheet("QGroupBox { background-color: #121916; border: 1px solid #1e2923; border-radius: 12px; margin-top: 25px; padding-top: 20px; font-weight: 800; color: #10b981; letter-spacing: 1px; font-size: 13px; } QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 5px; }")
        
        # =======================================================
        # LEFT COLUMN
        # =======================================================
        
        # === Фильтры сканирования ===
        filters_group = QGroupBox()
        style_groupbox(filters_group, get_text("settings_filters", "🔍 Фильтры предметов"))
        filters_layout = QVBoxLayout(filters_group)
        filters_layout.setContentsMargins(15, 15, 15, 15)
        filters_layout.setSpacing(15)
        
        # Grid для колонок фильтров
        grid_filters = QHBoxLayout()
        
        # Тиры
        tiers_layout = QVBoxLayout()
        tiers_layout.addWidget(QLabel(get_text("settings_tiers", "Тиры:")))
        self.tier_checks = {}
        for tier in range(4, 9):
            chk = QCheckBox(f"Tier {tier}")
            chk.setChecked(True)
            chk.stateChanged.connect(self._on_filters_changed)
            self.tier_checks[tier] = chk
            tiers_layout.addWidget(chk)
        tiers_layout.addStretch()
        grid_filters.addLayout(tiers_layout)
        
        # Зачарования
        enchants_layout = QVBoxLayout()
        enchants_layout.addWidget(QLabel(get_text("settings_enchants", "Зачарования:")))
        self.enchant_checks = {}
        for enchant in range(5):
            chk = QCheckBox(f".{enchant}")
            chk.setChecked(True)
            chk.stateChanged.connect(self._on_filters_changed)
            self.enchant_checks[enchant] = chk
            enchants_layout.addWidget(chk)
        enchants_layout.addStretch()
        grid_filters.addLayout(enchants_layout)
        
        # Качество
        qualities_layout = QVBoxLayout()
        qualities_layout.addWidget(QLabel(get_text("settings_qualities", "Качество:")))
        self.quality_checks = {}
        quality_names = {
            1: get_text("settings_quality_1", "Обычное"), 
            2: get_text("settings_quality_2", "Хорошее"), 
            3: get_text("settings_quality_3", "Выдающееся"),
            4: get_text("settings_quality_4", "Отличное"), 
            5: get_text("settings_quality_5", "Шедевр")
        }
        for q_id, q_name in quality_names.items():
            chk = QCheckBox(q_name)
            chk.setChecked(True)
            chk.stateChanged.connect(self._on_filters_changed)
            self.quality_checks[q_id] = chk
            qualities_layout.addWidget(chk)
        qualities_layout.addStretch()
        grid_filters.addLayout(qualities_layout)
        
        filters_layout.addLayout(grid_filters)
        left_col.addWidget(filters_group)
        
        # === Настройки мыши ===
        mouse_group = QGroupBox()
        style_groupbox(mouse_group, get_text("settings_mouse", "🐭 Настройки мыши"))
        mouse_layout = QFormLayout(mouse_group)
        mouse_layout.setContentsMargins(15, 15, 15, 15)
        mouse_layout.setSpacing(12)

        self.mouse_speed_spin = QSpinBox()
        self.mouse_speed_spin.setRange(500, 5000)
        self.mouse_speed_spin.setSingleStep(100)
        self.mouse_speed_spin.setSuffix(" px/sec")
        self.mouse_speed_spin.valueChanged.connect(self._on_mouse_speed_changed)
        mouse_layout.addRow(QLabel(get_text("settings_mouse_speed", "Скорость:")), self.mouse_speed_spin)

        self.mouse_mindur_spin = QDoubleSpinBox()
        self.mouse_mindur_spin.setRange(0.01, 1.0)
        self.mouse_mindur_spin.setSingleStep(0.01)
        self.mouse_mindur_spin.setSuffix(" сек")
        self.mouse_mindur_spin.valueChanged.connect(self._on_mouse_mindur_changed)
        mouse_layout.addRow(QLabel(get_text("settings_mouse_mindur", "Мин. время:")), self.mouse_mindur_spin)

        self.mouse_curve_spin = QDoubleSpinBox()
        self.mouse_curve_spin.setRange(0.0, 1.0)
        self.mouse_curve_spin.setSingleStep(0.05)
        self.mouse_curve_spin.valueChanged.connect(self._on_mouse_curve_changed)
        mouse_layout.addRow(QLabel(get_text("settings_mouse_curvature", "Кривизна:")), self.mouse_curve_spin)

        self.mouse_jitter_spin = QSpinBox()
        self.mouse_jitter_spin.setRange(0, 50)
        self.mouse_jitter_spin.setSuffix(" px")
        self.mouse_jitter_spin.valueChanged.connect(self._on_mouse_jitter_changed)
        mouse_layout.addRow(QLabel(get_text("settings_mouse_jitter", "Разброс:")), self.mouse_jitter_spin)

        left_col.addWidget(mouse_group)
        
        # === Черный рынок ===
        bm_group = QGroupBox()
        style_groupbox(bm_group, get_text("settings_bm", "🖤 Черный рынок"))
        bm_layout = QVBoxLayout(bm_group)
        bm_layout.setContentsMargins(15, 15, 15, 15)
        
        self.char_switch_check = QCheckBox(get_text("settings_char_switch", "Использовать смену персонажа (после 48 пред.)"))
        self.char_switch_check.stateChanged.connect(self._on_char_switch_changed)
        bm_layout.addWidget(self.char_switch_check)
        left_col.addWidget(bm_group)
        
        left_col.addStretch()


        # =======================================================
        # RIGHT COLUMN
        # =======================================================
        
        # === Языки ===
        langs_group = QGroupBox()
        style_groupbox(langs_group, get_text("settings_language", "🌐 Локализация"))
        langs_layout = QFormLayout(langs_group)
        langs_layout.setContentsMargins(15, 15, 15, 15)
        langs_layout.setSpacing(12)
        
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("English", "en")
        self.lang_combo.addItem("Русский", "ru")
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        langs_layout.addRow(QLabel(get_text("settings_lang_label", "Интерфейс бота:")), self.lang_combo)
        
        self.game_lang_combo = QComboBox()
        self.game_lang_combo.addItem("English", "en")
        self.game_lang_combo.addItem("Русский", "ru")
        self.game_lang_combo.currentIndexChanged.connect(self._on_game_language_changed)
        langs_layout.addRow(QLabel(get_text("settings_game_lang_label", "Язык клиента игры:")), self.game_lang_combo)
        
        right_col.addWidget(langs_group)

        # === Таймауты сканирования ===
        timeouts_group = QGroupBox()
        style_groupbox(timeouts_group, get_text("settings_timeouts", "⏳ Время ожидания"))
        timeouts_layout = QFormLayout(timeouts_group)
        timeouts_layout.setContentsMargins(15, 15, 15, 15)

        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.5, 60.0)
        self.timeout_spin.setSuffix(" сек")
        self.timeout_spin.setSingleStep(0.5)
        self.timeout_spin.valueChanged.connect(self._on_timeout_changed)
        timeouts_layout.addRow(QLabel(get_text("settings_wait_update", "Обновление цены:")), self.timeout_spin)
        right_col.addWidget(timeouts_group)

        # === Калибровка меню ===
        dropdown_group = QGroupBox()
        style_groupbox(dropdown_group, get_text("settings_calibration", "📏 Размеры выпадающих меню"))
        dropdown_layout = QFormLayout(dropdown_group)
        dropdown_layout.setContentsMargins(15, 15, 15, 15)
        dropdown_layout.setSpacing(12)
        
        info_label = QLabel(get_text("settings_calibration_info", "Для попадания мышью в Тиры (тещируется через Координаты)"))
        info_label.setStyleSheet("color: #64748b; font-size: 11px;")
        info_label.setWordWrap(True)
        dropdown_layout.addRow(info_label)
        
        self.row_height_spin = QSpinBox()
        self.row_height_spin.setRange(10, 100)
        self.row_height_spin.setSuffix(" px")
        self.row_height_spin.valueChanged.connect(self._on_row_height_changed)
        dropdown_layout.addRow(QLabel(get_text("settings_row_height", "Высота пункта меню:")), self.row_height_spin)
        
        self.offset_spin = QSpinBox()
        self.offset_spin.setRange(0, 200)
        self.offset_spin.setSuffix(" px")
        self.offset_spin.valueChanged.connect(self._on_offset_changed)
        dropdown_layout.addRow(QLabel(get_text("settings_offset", "Смещение списка вниз:")), self.offset_spin)
        
        right_col.addWidget(dropdown_group)
        
        # === Отладка OCR ===
        debug_group = QGroupBox()
        style_groupbox(debug_group, get_text("settings_ocr_debug", "🔬 Отладка модулей"))
        debug_layout = QVBoxLayout(debug_group)
        debug_layout.setContentsMargins(15, 15, 15, 15)
        
        self.ocr_debug_check = QCheckBox(get_text("settings_save_ocr", "Сохранять скриншоты OCR на диск (data/debug_ocr)"))
        self.ocr_debug_check.stateChanged.connect(self._on_ocr_debug_changed)
        debug_layout.addWidget(self.ocr_debug_check)
        
        right_col.addWidget(debug_group)

        right_col.addStretch()
    
    def _load_settings(self):
        """Загрузить настройки из конфига"""
        config = get_config()
        

        
        # Timeouts
        self.timeout_spin.setValue(config.get_setting("price_update_timeout", 5.0))
        
        # Dropdowns (block signals to prevent calibration overlay on startup)
        self.row_height_spin.blockSignals(True)
        self.offset_spin.blockSignals(True)
        self.row_height_spin.setValue(config.get_dropdown_setting("row_height", 28))
        self.offset_spin.setValue(config.get_dropdown_setting("list_start_offset", 30))
        self.row_height_spin.blockSignals(False)
        self.offset_spin.blockSignals(False)
        
        # Filters
        filters = config.get_scan_filters()
        
        # Block signals to prevent auto-save during loading
        self.blockSignals(True)
        
        for tier, chk in self.tier_checks.items():
            chk.setChecked(tier in filters.get("tiers", []))
            
        for enchant, chk in self.enchant_checks.items():
            chk.setChecked(enchant in filters.get("enchants", []))
            
        for q_id, chk in self.quality_checks.items():
            chk.setChecked(q_id in filters.get("qualities", []))

        # Mouse
        mouse_cfg = config.get_mouse_settings()
        self.mouse_speed_spin.setValue(int(mouse_cfg.get("speed_pps", 1800.0)))
        self.mouse_mindur_spin.setValue(mouse_cfg.get("min_duration", 0.08))
        self.mouse_curve_spin.setValue(mouse_cfg.get("curvature", 0.1))
        self.mouse_jitter_spin.setValue(int(mouse_cfg.get("jitter", 5)))

        # Character Switch
        self.char_switch_check.setChecked(config.get_setting("use_character_switch", True))

        # OCR Debug (block signals to avoid save during load)
        self.ocr_debug_check.blockSignals(True)
        self.ocr_debug_check.setChecked(config.get_setting("ocr_debug_mode", False))
        self.ocr_debug_check.blockSignals(False)

        # Language
        self.lang_combo.blockSignals(True)
        current_lang = config.get_setting("language", "en")
        idx = self.lang_combo.findData(current_lang)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.blockSignals(False)

        # Game Language
        self.game_lang_combo.blockSignals(True)
        current_game_lang = config.get_setting("game_language", "ru")
        game_idx = self.game_lang_combo.findData(current_game_lang)
        if game_idx >= 0:
            self.game_lang_combo.setCurrentIndex(game_idx)
        self.game_lang_combo.blockSignals(False)
            
        self.blockSignals(False)
        


    def _on_timeout_changed(self, value):
        get_config().set_setting("price_update_timeout", value)
        
    def _on_row_height_changed(self, value):
        get_config().set_dropdown_setting("row_height", value)
        self._show_calibration_points()
        
    def _on_offset_changed(self, value):
        get_config().set_dropdown_setting("list_start_offset", value)
        self._show_calibration_points()

    def _show_calibration_points(self):
        """Показать точки калибровки для текущего Tier Dropdown"""
        # Берем настройки из UI (так как они еще могут быть не сохранены или просто для live preview)
        row_height = self.row_height_spin.value()
        offset = self.offset_spin.value()
        
        # Получаем координату "tier_dropdown" через конфиг
        config = get_config()
        anchor = config.get_coordinate("tier_dropdown")
        
        if not anchor:
            return
            
        x, y = anchor
        points = []
        
        # Генерируем точки для 9 элементов (8 тиров + пункт "Все")
        for i in range(9):
            # Формула: anchor_y + offset + (index * row_height)
            py = y + offset + (i * row_height)
            points.append((x, py))
            
        self.overlay.show_points(points)
 
    def _on_filters_changed(self):
        """Сохранить фильтры при изменении чекбоксов"""
        if self.signalsBlocked():
            return
            
        selected_tiers = [t for t, chk in self.tier_checks.items() if chk.isChecked()]
        selected_enchants = [e for e, chk in self.enchant_checks.items() if chk.isChecked()]
        selected_qualities = [q for q, chk in self.quality_checks.items() if chk.isChecked()]
        
        config = get_config()
        config.set_scan_filter("tiers", selected_tiers)
        config.set_scan_filter("enchants", selected_enchants)
        config.set_scan_filter("qualities", selected_qualities)



    def _on_mouse_speed_changed(self, value):
        get_config().set_mouse_setting("speed_pps", float(value))

    def _on_mouse_mindur_changed(self, value):
        get_config().set_mouse_setting("min_duration", value)

    def _on_mouse_curve_changed(self, value):
        get_config().set_mouse_setting("curvature", value)

    def _on_mouse_jitter_changed(self, value):
        get_config().set_mouse_setting("jitter", int(value))

    def _on_char_switch_changed(self, state):
        get_config().set_setting("use_character_switch", state == Qt.CheckState.Checked.value)

    def _on_ocr_debug_changed(self, state):
        get_config().set_setting("ocr_debug_mode", state == Qt.CheckState.Checked.value)

    def _on_language_changed(self, index):
        lang_code = self.lang_combo.itemData(index)
        config = get_config()
        old_lang = config.get_setting("language", "en")
        
        if lang_code != old_lang:
            config.set_setting("language", lang_code)
            
            QMessageBox.information(
                self,
                "Language Changed",
                "Language preference saved. Please restart the application to apply changes fully.\n\n"
                "Язык сохранен. Пожалуйста, перезапустите приложение для полного применения изменений."
            )

    def _on_game_language_changed(self, index):
        lang_code = self.game_lang_combo.itemData(index)
        config = get_config()
        old_lang = config.get_setting("game_language", "ru")
        
        if lang_code != old_lang:
            config.set_setting("game_language", lang_code)
            self._translate_items_database(lang_code)
            self._translate_tier_exceptions(lang_code)
            self._translate_wholesale_targets(lang_code)
            
            get_logger().info(f"Game language changed: {old_lang} -> {lang_code}")
            
            QMessageBox.information(
                self,
                get_text("settings_game_language", "🎮 Язык игры"),
                get_text("settings_game_lang_restart", "Язык игры изменен. База предметов и исключения автоматически переведены.")
            )

    def _translate_items_database(self, to_lang: str):
        """Автоматически перевести все предметы в базе"""
        from ..utils.items_db import translate_items_list, get_default_items
        config = get_config()
        
        current_items = config.get_known_items()
        if not current_items:
            # Если база пуста — загружаем дефолт для нового языка
            config.set_known_items(get_default_items())
            return
        
        translated = translate_items_list(current_items, to_lang)
        config.set_known_items(translated)
        get_logger().info(f"Items database translated to '{to_lang}': {len(translated)} items")

    def _translate_tier_exceptions(self, to_lang: str):
        """Автоматически перевести исключения тиров и добавить дефолтные для нового языка"""
        from ..utils.items_db import translate_item
        from ..utils.default_exceptions import get_default_exceptions
        config = get_config()
        
        current_exc = config.get_tier_exceptions()
        new_exc = {}
        
        # Получаем дефолтные исключения для целевого языка (config.game_language уже изменен)
        default_exc = get_default_exceptions()
        
        for tier_key, items in current_exc.items():
            translated = [translate_item(item, to_lang) for item in items]
            
            # Добавляем дефолтные предметы для этого тира в целевом языке
            if tier_key in default_exc:
                translated.extend(default_exc[tier_key])
                
            # Убираем дубликаты сохраняя порядок
            dedup_translated = []
            for item in translated:
                if item not in dedup_translated:
                    dedup_translated.append(item)
                    
            new_exc[tier_key] = dedup_translated
        
        config.set_tier_exceptions(new_exc)
        get_logger().info(f"Tier exceptions translated and merged with defaults for '{to_lang}'")

    def _translate_wholesale_targets(self, to_lang: str):
        """Автоматически перевести ключи wholesale targets"""
        from ..utils.items_db import translate_item
        config = get_config()
        
        targets = config.get_wholesale_targets()
        if not targets:
            return
        
        new_targets = {}
        for item_name, variants in targets.items():
            translated_name = translate_item(item_name, to_lang)
            new_targets[translated_name] = variants
        
        config._config["wholesale_targets"] = new_targets
        config.save()
        get_logger().info(f"Wholesale targets translated to '{to_lang}': {len(new_targets)} items")

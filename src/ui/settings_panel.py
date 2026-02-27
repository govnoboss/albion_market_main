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
        
        # Убираем рамки и ставим фон
        self.setStyleSheet(PANEL_STYLE)
        
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
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)
        
        
        # === Таймауты сканирования ===
        timeouts_group = QGroupBox(get_text("settings_timeouts", "⏳ Таймауты сканирования"))
        timeouts_layout = QFormLayout(timeouts_group)
        timeouts_layout.setSpacing(15)

        # Timeout
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.5, 60.0)
        self.timeout_spin.setSuffix(" сек")
        self.timeout_spin.setSingleStep(0.5)
        self.timeout_spin.valueChanged.connect(self._on_timeout_changed)
        
        timeout_lbl = QLabel(get_text("settings_wait_update", "Ожидание обновления цены:"))
        timeout_lbl.setToolTip(get_text("settings_wait_update_tip", "Сколько секунд мы ждем перед тем как пропустить предмет, цена которого не обновилась."))
        timeouts_layout.addRow(timeout_lbl, self.timeout_spin)

        layout.addWidget(timeouts_group)


        # === Калибровка меню ===
        dropdown_group = QGroupBox(get_text("settings_calibration", "📏 Калибровка выпадающих меню"))
        dropdown_layout = QFormLayout(dropdown_group)
        dropdown_layout.setSpacing(15)
        
        # Описание
        info_label = QLabel(get_text("settings_calibration_info", "Настройка параметров для точного попадания по пунктам меню (Тир, Зачарование и т.д.)"))
        info_label.setStyleSheet("color: #8b949e; font-size: 12px; margin-bottom: 10px;")
        info_label.setWordWrap(True)
        dropdown_layout.addRow(info_label)
        
        # Высота строки
        self.row_height_spin = QSpinBox()
        self.row_height_spin.setRange(10, 100)
        self.row_height_spin.setSuffix(" px")
        self.row_height_spin.valueChanged.connect(self._on_row_height_changed)
        
        row_height_lbl = QLabel(get_text("settings_row_height", "Высота строки:"))
        row_height_lbl.setToolTip(get_text("settings_row_height_tip", "Точки которые помогают откалибровать клики по Тирам."))
        dropdown_layout.addRow(row_height_lbl, self.row_height_spin)
        
        # Смещение первого элемента
        self.offset_spin = QSpinBox()
        self.offset_spin.setRange(0, 200)
        self.offset_spin.setSuffix(" px")
        self.offset_spin.valueChanged.connect(self._on_offset_changed)
        
        offset_lbl = QLabel(get_text("settings_offset", "Смещение списка:"))
        offset_lbl.setToolTip(get_text("settings_offset_tip", "Точки которые помогают откалибровать клики по Тирам."))
        dropdown_layout.addRow(offset_lbl, self.offset_spin)
        
        layout.addWidget(dropdown_group)
        
        # === Настройки мыши ===
        mouse_group = QGroupBox(get_text("settings_mouse", "🐭 Настройки мыши"))
        mouse_layout = QFormLayout(mouse_group)
        mouse_layout.setSpacing(10)

        

        # Speed
        self.mouse_speed_spin = QSpinBox()
        self.mouse_speed_spin.setRange(500, 5000)
        self.mouse_speed_spin.setSingleStep(100)
        self.mouse_speed_spin.setSuffix(" px/sec")
        self.mouse_speed_spin.valueChanged.connect(self._on_mouse_speed_changed)
        
        speed_lbl = QLabel(get_text("settings_mouse_speed", "Скорость:"))
        speed_lbl.setToolTip(get_text("settings_mouse_speed_tip", "с какой скоростью двигается мышь."))
        mouse_layout.addRow(speed_lbl, self.mouse_speed_spin)

        # Min Duration
        self.mouse_mindur_spin = QDoubleSpinBox()
        self.mouse_mindur_spin.setRange(0.01, 1.0)
        self.mouse_mindur_spin.setSingleStep(0.01)
        self.mouse_mindur_spin.setSuffix(" сек")
        self.mouse_mindur_spin.valueChanged.connect(self._on_mouse_mindur_changed)
        
        mindur_lbl = QLabel(get_text("settings_mouse_mindur", "Мин. время:"))
        mindur_lbl.setToolTip(get_text("settings_mouse_mindur_tip", "Минимальное время за которое бот доводит мышь на координату."))
        mouse_layout.addRow(mindur_lbl, self.mouse_mindur_spin)

        # Curvature
        self.mouse_curve_spin = QDoubleSpinBox()
        self.mouse_curve_spin.setRange(0.0, 1.0)
        self.mouse_curve_spin.setSingleStep(0.05)
        self.mouse_curve_spin.valueChanged.connect(self._on_mouse_curve_changed)
        
        curve_lbl = QLabel(get_text("settings_mouse_curvature", "Кривизна:"))
        curve_lbl.setToolTip(get_text("settings_mouse_curvature_tip", "Насколько сильно бот будет двигать мышь по кривой."))
        mouse_layout.addRow(curve_lbl, self.mouse_curve_spin)

        # Jitter
        self.mouse_jitter_spin = QSpinBox()
        self.mouse_jitter_spin.setRange(0, 50)
        self.mouse_jitter_spin.setSuffix(" px")
        self.mouse_jitter_spin.valueChanged.connect(self._on_mouse_jitter_changed)
        
        jitter_lbl = QLabel(get_text("settings_mouse_jitter", "Разброс:"))
        jitter_lbl.setToolTip(get_text("settings_mouse_jitter_tip", "Радиус вокруг указанной координаты, куда бот будет случайно кликать."))
        mouse_layout.addRow(jitter_lbl, self.mouse_jitter_spin)

        layout.addWidget(mouse_group)

        # === Черный рынок ===
        bm_group = QGroupBox(get_text("settings_bm", "🖤 Черный рынок"))
        bm_layout = QVBoxLayout(bm_group)
        bm_layout.setSpacing(10)
        
        self.char_switch_check = QCheckBox(get_text("settings_char_switch", "Использовать смену персонажа (после 48 пред.)"))
        self.char_switch_check.setToolTip(get_text("settings_char_switch_tip", "Если включено, бот попытается переключиться на второго персонажа при достижении лимита ЧР."))
        self.char_switch_check.stateChanged.connect(self._on_char_switch_changed)
        bm_layout.addWidget(self.char_switch_check)
        
        layout.addWidget(bm_group)

        # === Отладка OCR ===
        debug_group = QGroupBox(get_text("settings_ocr_debug", "🔬 Отладка OCR"))
        debug_layout = QVBoxLayout(debug_group)
        debug_layout.setSpacing(10)
        
        self.ocr_debug_check = QCheckBox(get_text("settings_save_ocr", "Сохранять скриншоты OCR при сканировании цен"))
        self.ocr_debug_check.setToolTip(get_text("settings_save_ocr_tip", "При включении все изображения, которые видит OCR (цены, количество), сохраняются в папку data/debug_ocr/"))
        self.ocr_debug_check.stateChanged.connect(self._on_ocr_debug_changed)
        debug_layout.addWidget(self.ocr_debug_check)
        
        layout.addWidget(debug_group)
        # === Фильтры сканирования ===
        filters_group = QGroupBox(get_text("settings_filters", "🔍 Фильтры предметов"))
        filters_group.setToolTip(get_text("settings_filters_tip", "Выбор предметов для сканирования и закупки."))
        filters_layout = QVBoxLayout(filters_group)
        filters_layout.setSpacing(15)
        
        # Grid для колонок
        grid_layout = QHBoxLayout()
        grid_layout.setSpacing(20)  # Добавляем отступы между колонками
        
        # Тиры
        tiers_layout = QVBoxLayout()
        tiers_layout.setSpacing(10) # Отступы между чекбоксами
        tiers_layout.addWidget(QLabel(get_text("settings_tiers", "Тиры:")))
        self.tier_checks = {}
        for tier in range(4, 9):
            chk = QCheckBox(f"Tier {tier}")
            chk.setChecked(True)
            chk.stateChanged.connect(self._on_filters_changed)
            self.tier_checks[tier] = chk
            tiers_layout.addWidget(chk)
        tiers_layout.addStretch()
        grid_layout.addLayout(tiers_layout)
        
        # Зачарования
        enchants_layout = QVBoxLayout()
        enchants_layout.setSpacing(10)
        enchants_layout.addWidget(QLabel(get_text("settings_enchants", "Зачарования:")))
        self.enchant_checks = {}
        for enchant in range(5):
            chk = QCheckBox(f".{enchant}")
            chk.setChecked(True)
            chk.stateChanged.connect(self._on_filters_changed)
            self.enchant_checks[enchant] = chk
            enchants_layout.addWidget(chk)
        enchants_layout.addStretch()
        grid_layout.addLayout(enchants_layout)
        
        # Качество
        qualities_layout = QVBoxLayout()
        qualities_layout.setSpacing(10)
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
        grid_layout.addLayout(qualities_layout)
        
        filters_layout.addLayout(grid_layout)
        layout.addWidget(filters_group)

        # === Язык ===
        lang_group = QGroupBox(get_text("settings_language", "🌐 Язык"))
        lang_layout = QFormLayout(lang_group)
        
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("English", "en")
        self.lang_combo.addItem("Русский", "ru")
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        
        lang_lbl = QLabel(get_text("settings_lang_label", "Выберите язык:"))
        lang_layout.addRow(lang_lbl, self.lang_combo)
        
        layout.addWidget(lang_group)

        
        layout.addStretch()
    
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
            
            # Предлагаем перезапуск или уведомляем, что изменения вступят в силу после перезапуска
            # Хотя мы можем сменить язык "на лету" для LocalizationManager, 
            # но большинство виджетов уже созданы с конкретным текстом.
            QMessageBox.information(
                self,
                "Language Changed",
                "Language preference saved. Please restart the application to apply changes fully.\n\n"
                "Язык сохранен. Пожалуйста, перезапустите приложение для полного применения изменений."
            )

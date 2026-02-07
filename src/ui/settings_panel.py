"""
Панель настроек приложения
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QSpinBox, QDoubleSpinBox, QGroupBox, QFormLayout, QCheckBox,
    QScrollArea
)
from ..utils.config import get_config
from ..utils.config import get_config
from ..utils.logger import get_logger
from .calibration_overlay import CalibrationOverlay

class SettingsPanel(QScrollArea):
    """Панель глобальных настроек"""
    
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Оверлей калибровки
        self.overlay = CalibrationOverlay()
        
        # Убираем рамки и ставим фон
        self.setStyleSheet("""
            QScrollArea { border: none; background-color: #0d1117; }
            QWidget { background-color: #0d1117; color: #f0f6fc; }
            QGroupBox { background-color: transparent; }
            QLabel { background-color: transparent; }
            QCheckBox { background-color: transparent; }
        """)
        
        self.content_widget = QWidget()
        self.content_widget.setObjectName("settingsContent") # Для CSS если нужно
        self.setWidget(self.content_widget)
        
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)
        
        
        # === Таймауты сканирования ===
        timeouts_group = QGroupBox("⏳ Таймауты сканирования")
        timeouts_layout = QFormLayout(timeouts_group)
        timeouts_layout.setSpacing(15)

        # Timeout
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.5, 60.0)
        self.timeout_spin.setSuffix(" сек")
        self.timeout_spin.setSingleStep(0.5)
        self.timeout_spin.valueChanged.connect(self._on_timeout_changed)
        timeouts_layout.addRow("Ожидание обновления цены:", self.timeout_spin)

        layout.addWidget(timeouts_group)
        
        # === Калибровка меню ===
        dropdown_group = QGroupBox("📏 Калибровка выпадающих меню")
        dropdown_layout = QFormLayout(dropdown_group)
        dropdown_layout.setSpacing(15)
        
        # Описание
        info_label = QLabel("Настройка параметров для точного попадания по пунктам меню (Тир, Зачарование и т.д.)")
        info_label.setStyleSheet("color: #8b949e; font-size: 12px; margin-bottom: 10px;")
        info_label.setWordWrap(True)
        dropdown_layout.addRow(info_label)
        
        # Высота строки
        self.row_height_spin = QSpinBox()
        self.row_height_spin.setRange(10, 100)
        self.row_height_spin.setSuffix(" px")
        self.row_height_spin.valueChanged.connect(self._on_row_height_changed)
        dropdown_layout.addRow("Высота строки:", self.row_height_spin)
        
        # Смещение первого элемента
        self.offset_spin = QSpinBox()
        self.offset_spin.setRange(0, 200)
        self.offset_spin.setSuffix(" px")
        self.offset_spin.valueChanged.connect(self._on_offset_changed)
        dropdown_layout.addRow("Смещение списка:", self.offset_spin)
        
        layout.addWidget(dropdown_group)
        
        # === Фильтры сканирования ===
        filters_group = QGroupBox("🔍 Фильтры сканирования")
        filters_layout = QVBoxLayout(filters_group)
        filters_layout.setSpacing(15)
        
        # Grid для колонок
        grid_layout = QHBoxLayout()
        grid_layout.setSpacing(20)  # Добавляем отступы между колонками
        
        # Тиры
        tiers_layout = QVBoxLayout()
        tiers_layout.setSpacing(10) # Отступы между чекбоксами
        tiers_layout.addWidget(QLabel("Тиры:"))
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
        enchants_layout.addWidget(QLabel("Зачарования:"))
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
        qualities_layout.addWidget(QLabel("Качество:"))
        self.quality_checks = {}
        quality_names = {
            1: "Обычное", 2: "Хорошее", 3: "Выдающееся",
            4: "Отличное", 5: "Шедевр"
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
        
        # Генерируем точки для 8 элементов (как пример)
        for i in range(8):
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

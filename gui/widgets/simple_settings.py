"""
Albion Market Bot v3.0 - Simplified Settings Panel

Упрощённая панель настроек: только 3 OCR-региона.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QSpinBox, QDoubleSpinBox, QPushButton, 
    QGroupBox, QCheckBox, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.simple_config import (
    SimplifiedSettings, OCRRegion, 
    load_simplified_settings, save_simplified_settings,
    REGIONS_DESCRIPTION
)


class RegionCapture(QWidget):
    """Виджет для настройки OCR-региона с кнопкой захвата."""
    
    valueChanged = pyqtSignal()
    
    def __init__(self, name: str, description: str, parent=None):
        super().__init__(parent)
        self.name = name
        self._overlay = None  # Для хранения ссылки на overlay
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Описание
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #a6adc8; font-size: 9pt;")
        layout.addWidget(desc_label)
        
        # Поля ввода
        inputs_layout = QHBoxLayout()
        
        self.left = QSpinBox()
        self.left.setRange(0, 9999)
        self.left.setPrefix("L: ")
        self.left.valueChanged.connect(self.valueChanged.emit)
        inputs_layout.addWidget(self.left)
        
        self.top = QSpinBox()
        self.top.setRange(0, 9999)
        self.top.setPrefix("T: ")
        self.top.valueChanged.connect(self.valueChanged.emit)
        inputs_layout.addWidget(self.top)
        
        self.width = QSpinBox()
        self.width.setRange(1, 999)
        self.width.setPrefix("W: ")
        self.width.valueChanged.connect(self.valueChanged.emit)
        inputs_layout.addWidget(self.width)
        
        self.height = QSpinBox()
        self.height.setRange(1, 999)
        self.height.setPrefix("H: ")
        self.height.valueChanged.connect(self.valueChanged.emit)
        inputs_layout.addWidget(self.height)
        
        self.capture_btn = QPushButton("📍 Захватить")
        self.capture_btn.setFixedWidth(100)
        self.capture_btn.clicked.connect(self._start_capture)
        inputs_layout.addWidget(self.capture_btn)
        
        layout.addLayout(inputs_layout)
    
    def _start_capture(self):
        """Запуск overlay для захвата области."""
        from gui.widgets.region_capture import RegionCaptureOverlay
        
        # Скрываем главное окно чтобы не мешало
        main_window = self.window()
        if main_window:
            main_window.hide()
        
        self._overlay = RegionCaptureOverlay()
        self._overlay.region_captured.connect(self._on_region_captured)
        self._overlay.capture_cancelled.connect(self._on_capture_cancelled)
        self._overlay.start_capture()
    
    def _on_region_captured(self, left: int, top: int, width: int, height: int):
        """Обработка захваченной области."""
        self.left.setValue(left)
        self.top.setValue(top)
        self.width.setValue(width)
        self.height.setValue(height)
        self.valueChanged.emit()
        
        # Показываем главное окно обратно
        main_window = self.window()
        if main_window:
            main_window.show()
    
    def _on_capture_cancelled(self):
        """Обработка отмены захвата."""
        main_window = self.window()
        if main_window:
            main_window.show()

    
    def get_region(self) -> OCRRegion:
        return OCRRegion(
            left=self.left.value(),
            top=self.top.value(),
            width=self.width.value(),
            height=self.height.value()
        )
    
    def set_region(self, region: OCRRegion):
        self.left.setValue(region.left)
        self.top.setValue(region.top)
        self.width.setValue(region.width)
        self.height.setValue(region.height)


class SimplifiedSettingsPanel(QWidget):
    """
    Упрощённая панель настроек.
    
    Содержит только 3 OCR-региона вместо 10+ координат.
    Кнопки находятся автоматически через Template Matching.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = load_simplified_settings()
        self._setup_ui()
        self._load_values()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Информационный блок
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #313244;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        
        info_title = QLabel("✨ Упрощённая настройка")
        info_title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #a6e3a1;")
        info_layout.addWidget(info_title)
        
        info_text = QLabel(
            "Нужно настроить только 3 области OCR.\n"
            "Все кнопки находятся автоматически!"
        )
        info_text.setStyleSheet("color: #cdd6f4;")
        info_layout.addWidget(info_text)
        
        layout.addWidget(info_frame)
        
        # OCR Регионы
        regions_group = QGroupBox("📐 Области OCR (нужно настроить)")
        regions_layout = QVBoxLayout(regions_group)
        
        self.price_region = RegionCapture(
            "price", 
            REGIONS_DESCRIPTION["price_region"]
        )
        regions_layout.addWidget(self.price_region)
        
        self.quantity_region = RegionCapture(
            "quantity",
            REGIONS_DESCRIPTION["quantity_region"]
        )
        regions_layout.addWidget(self.quantity_region)
        
        self.item_name_region = RegionCapture(
            "item_name",
            REGIONS_DESCRIPTION["item_name_region"]
        )
        regions_layout.addWidget(self.item_name_region)
        
        layout.addWidget(regions_group)
        
        # Настройки закупки
        buy_group = QGroupBox("💰 Параметры закупки")
        buy_layout = QGridLayout(buy_group)
        
        buy_layout.addWidget(QLabel("Бюджет:"), 0, 0)
        self.budget_input = QSpinBox()
        self.budget_input.setRange(0, 2_000_000_000)
        self.budget_input.setSingleStep(1_000_000)
        self.budget_input.setSuffix(" серебра")
        buy_layout.addWidget(self.budget_input, 0, 1)
        
        buy_layout.addWidget(QLabel("Задержка:"), 1, 0)
        self.delay_input = QDoubleSpinBox()
        self.delay_input.setRange(0.0, 10.0)
        self.delay_input.setSingleStep(0.1)
        self.delay_input.setSuffix(" сек")
        buy_layout.addWidget(self.delay_input, 1, 1)
        
        buy_layout.addWidget(QLabel("Начальная строка:"), 2, 0)
        self.start_row_input = QSpinBox()
        self.start_row_input.setRange(1, 10000)
        buy_layout.addWidget(self.start_row_input, 2, 1)
        
        self.tier6_checkbox = QCheckBox("Только 6 тир (мастер)")
        buy_layout.addWidget(self.tier6_checkbox, 3, 0, 1, 2)
        
        layout.addWidget(buy_group)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 Сохранить")
        self.save_btn.clicked.connect(self._save_settings)
        buttons_layout.addWidget(self.save_btn)
        
        self.test_btn = QPushButton("🔍 Тест Template Matching")
        self.test_btn.clicked.connect(self._test_template_matching)
        buttons_layout.addWidget(self.test_btn)
        
        layout.addLayout(buttons_layout)
        layout.addStretch()
    
    def _load_values(self):
        """Загрузка значений."""
        self.price_region.set_region(self.settings.price_region)
        self.quantity_region.set_region(self.settings.quantity_region)
        self.item_name_region.set_region(self.settings.item_name_region)
        
        self.budget_input.setValue(self.settings.budget)
        self.delay_input.setValue(self.settings.delay)
        self.start_row_input.setValue(self.settings.start_row)
        self.tier6_checkbox.setChecked(self.settings.tier6_only)
    
    def _save_settings(self):
        """Сохранение настроек."""
        self.settings.price_region = self.price_region.get_region()
        self.settings.quantity_region = self.quantity_region.get_region()
        self.settings.item_name_region = self.item_name_region.get_region()
        
        self.settings.budget = self.budget_input.value()
        self.settings.delay = self.delay_input.value()
        self.settings.start_row = self.start_row_input.value()
        self.settings.tier6_only = self.tier6_checkbox.isChecked()
        
        save_simplified_settings(self.settings)
        QMessageBox.information(self, "Успех", "Настройки сохранены!")
    
    def _test_template_matching(self):
        """Тестирование поиска кнопок."""
        from core.template_matcher import get_template_matcher
        
        matcher = get_template_matcher()
        results = []
        
        templates = ['buy_button', 'ok_button', 'clear_button', 'search_button']
        
        for name in templates:
            result = matcher.find_on_screen(name)
            status = "✅" if result.found else "❌"
            conf = f"{result.confidence:.0%}" if result.confidence > 0 else "N/A"
            results.append(f"{status} {name}: {conf}")
        
        QMessageBox.information(
            self, 
            "Результат тестирования",
            "Поиск шаблонов на экране:\n\n" + "\n".join(results) +
            "\n\nОткройте окно рынка в игре для корректного теста."
        )

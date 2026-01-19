"""
Albion Market Bot v3.0 - Settings Panel Widget

Панели настроек и координат.
"""

from typing import Dict, Callable

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QSpinBox, QDoubleSpinBox,
    QPushButton, QGroupBox, QScrollArea, QCheckBox,
    QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from config import AppSettings, Coordinates, Region, save_settings


class CoordinateInput(QWidget):
    """Виджет для ввода координат (X, Y)."""
    
    valueChanged = pyqtSignal()
    
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.label = QLabel(label)
        self.label.setMinimumWidth(150)
        layout.addWidget(self.label)
        
        self.x_input = QSpinBox()
        self.x_input.setRange(0, 9999)
        self.x_input.setPrefix("X: ")
        self.x_input.valueChanged.connect(self.valueChanged.emit)
        layout.addWidget(self.x_input)
        
        self.y_input = QSpinBox()
        self.y_input.setRange(0, 9999)
        self.y_input.setPrefix("Y: ")
        self.y_input.valueChanged.connect(self.valueChanged.emit)
        layout.addWidget(self.y_input)
        
        self.capture_btn = QPushButton("Захватить")
        self.capture_btn.setFixedWidth(100)
        layout.addWidget(self.capture_btn)
    
    def get_values(self) -> tuple[int, int]:
        return (self.x_input.value(), self.y_input.value())
    
    def set_values(self, x: int, y: int):
        self.x_input.setValue(x)
        self.y_input.setValue(y)


class RegionInput(QWidget):
    """Виджет для ввода региона (L, T, W, H)."""
    
    valueChanged = pyqtSignal()
    
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.label = QLabel(label)
        layout.addWidget(self.label)
        
        inputs_layout = QHBoxLayout()
        
        self.left_input = QSpinBox()
        self.left_input.setRange(0, 9999)
        self.left_input.setPrefix("L: ")
        self.left_input.valueChanged.connect(self.valueChanged.emit)
        inputs_layout.addWidget(self.left_input)
        
        self.top_input = QSpinBox()
        self.top_input.setRange(0, 9999)
        self.top_input.setPrefix("T: ")
        self.top_input.valueChanged.connect(self.valueChanged.emit)
        inputs_layout.addWidget(self.top_input)
        
        self.width_input = QSpinBox()
        self.width_input.setRange(1, 999)
        self.width_input.setPrefix("W: ")
        self.width_input.valueChanged.connect(self.valueChanged.emit)
        inputs_layout.addWidget(self.width_input)
        
        self.height_input = QSpinBox()
        self.height_input.setRange(1, 999)
        self.height_input.setPrefix("H: ")
        self.height_input.valueChanged.connect(self.valueChanged.emit)
        inputs_layout.addWidget(self.height_input)
        
        self.capture_btn = QPushButton("Захватить область")
        inputs_layout.addWidget(self.capture_btn)
        
        layout.addLayout(inputs_layout)
    
    def get_region(self) -> Region:
        return Region(
            left=self.left_input.value(),
            top=self.top_input.value(),
            width=self.width_input.value(),
            height=self.height_input.value()
        )
    
    def set_region(self, region: Region):
        self.left_input.setValue(region.left)
        self.top_input.setValue(region.top)
        self.width_input.setValue(region.width)
        self.height_input.setValue(region.height)


class CoordinatesPanel(QWidget):
    """Панель настройки координат."""
    
    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._setup_ui()
        self._load_values()
    
    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(16)
        
        # Навигация
        nav_group = QGroupBox("Навигация")
        nav_layout = QVBoxLayout(nav_group)
        
        self.search_coord = CoordinateInput("Search (Строка поиска)")
        nav_layout.addWidget(self.search_coord)
        
        self.clear_coord = CoordinateInput("Clear (Очистка)")
        nav_layout.addWidget(self.clear_coord)
        
        layout.addWidget(nav_group)
        
        # Покупка
        buy_group = QGroupBox("Покупка/Продажа")
        buy_layout = QVBoxLayout(buy_group)
        
        self.buy_coord = CoordinateInput("Buy/Sell (Кнопка)")
        buy_layout.addWidget(self.buy_coord)
        
        self.confirm_coord = CoordinateInput("Confirm (Подтверждение)")
        buy_layout.addWidget(self.confirm_coord)
        
        self.quantity_coord = CoordinateInput("Quantity (Количество)")
        buy_layout.addWidget(self.quantity_coord)
        
        self.close_coord = CoordinateInput("Close (Крестик)")
        buy_layout.addWidget(self.close_coord)
        
        layout.addWidget(buy_group)
        
        # Ордера
        order_group = QGroupBox("Ордера")
        order_layout = QVBoxLayout(order_group)
        
        self.buy_order_coord = CoordinateInput("Buy Order")
        order_layout.addWidget(self.buy_order_coord)
        
        self.price_per_unit_coord = CoordinateInput("Price per Unit")
        order_layout.addWidget(self.price_per_unit_coord)
        
        self.minus_coord = CoordinateInput("Minus (Кнопка минус)")
        order_layout.addWidget(self.minus_coord)
        
        self.quality_coord = CoordinateInput("Quality")
        order_layout.addWidget(self.quality_coord)
        
        layout.addWidget(order_group)
        
        # OCR Регионы
        ocr_group = QGroupBox("OCR Регионы")
        ocr_layout = QVBoxLayout(ocr_group)
        
        self.price_region = RegionInput("Цена покупки")
        ocr_layout.addWidget(self.price_region)
        
        self.quantity_region = RegionInput("Количество")
        ocr_layout.addWidget(self.quantity_region)
        
        self.item_name_region = RegionInput("Название предмета")
        ocr_layout.addWidget(self.item_name_region)
        
        self.sell_price_region = RegionInput("Цена продажи")
        ocr_layout.addWidget(self.sell_price_region)
        
        layout.addWidget(ocr_group)
        
        layout.addStretch()
        
        scroll.setWidget(content)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
    
    def _load_values(self):
        """Загрузка значений из настроек."""
        c = self.settings.coordinates
        self.search_coord.set_values(c.search_x, c.search_y)
        self.clear_coord.set_values(c.clear_x, c.clear_y)
        self.buy_coord.set_values(c.buy_x, c.buy_y)
        self.confirm_coord.set_values(c.confirm_x, c.confirm_y)
        self.quantity_coord.set_values(c.quantity_x, c.quantity_y)
        self.close_coord.set_values(c.close_x, c.close_y)
        self.buy_order_coord.set_values(c.buy_order_x, c.buy_order_y)
        self.price_per_unit_coord.set_values(c.price_per_unit_x, c.price_per_unit_y)
        self.minus_coord.set_values(c.minus_x, c.minus_y)
        self.quality_coord.set_values(c.quality_x, c.quality_y)
        
        r = self.settings.regions
        self.price_region.set_region(r.price)
        self.quantity_region.set_region(r.quantity)
        self.item_name_region.set_region(r.item_name)
        self.sell_price_region.set_region(r.sell_price)
    
    def save_values(self):
        """Сохранение значений в настройки."""
        c = self.settings.coordinates
        
        x, y = self.search_coord.get_values()
        c.search_x, c.search_y = x, y
        
        x, y = self.clear_coord.get_values()
        c.clear_x, c.clear_y = x, y
        
        x, y = self.buy_coord.get_values()
        c.buy_x, c.buy_y = x, y
        
        x, y = self.confirm_coord.get_values()
        c.confirm_x, c.confirm_y = x, y
        
        x, y = self.quantity_coord.get_values()
        c.quantity_x, c.quantity_y = x, y
        
        x, y = self.close_coord.get_values()
        c.close_x, c.close_y = x, y
        
        x, y = self.buy_order_coord.get_values()
        c.buy_order_x, c.buy_order_y = x, y
        
        x, y = self.price_per_unit_coord.get_values()
        c.price_per_unit_x, c.price_per_unit_y = x, y
        
        x, y = self.minus_coord.get_values()
        c.minus_x, c.minus_y = x, y
        
        x, y = self.quality_coord.get_values()
        c.quality_x, c.quality_y = x, y
        
        r = self.settings.regions
        r.price = self.price_region.get_region()
        r.quantity = self.quantity_region.get_region()
        r.item_name = self.item_name_region.get_region()
        r.sell_price = self.sell_price_region.get_region()


class SettingsPanel(QWidget):
    """Панель общих настроек."""
    
    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._setup_ui()
        self._load_values()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Настройки закупки
        buy_group = QGroupBox("Параметры закупки")
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
        
        buy_layout.addWidget(QLabel("Стоимость перевозки:"), 3, 0)
        self.transport_cost_input = QSpinBox()
        self.transport_cost_input.setRange(0, 10000)
        self.transport_cost_input.setSuffix(" за кг")
        buy_layout.addWidget(self.transport_cost_input, 3, 1)
        
        self.tier6_checkbox = QCheckBox("Только 6 тир (мастер)")
        buy_layout.addWidget(self.tier6_checkbox, 4, 0, 1, 2)
        
        layout.addWidget(buy_group)
        
        # Статистика
        stats_group = QGroupBox("Статистика")
        stats_layout = QGridLayout(stats_group)
        
        stats_layout.addWidget(QLabel("Потрачено за всё время:"), 0, 0)
        self.cumulative_spent_input = QSpinBox()
        self.cumulative_spent_input.setRange(0, 2_000_000_000)
        self.cumulative_spent_input.setSuffix(" серебра")
        self.cumulative_spent_input.setReadOnly(True)
        stats_layout.addWidget(self.cumulative_spent_input, 0, 1)
        
        self.reset_stats_btn = QPushButton("Сбросить статистику")
        self.reset_stats_btn.clicked.connect(self._reset_stats)
        stats_layout.addWidget(self.reset_stats_btn, 1, 0, 1, 2)
        
        layout.addWidget(stats_group)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 Сохранить настройки")
        self.save_btn.clicked.connect(self._save_settings)
        buttons_layout.addWidget(self.save_btn)
        
        self.reset_btn = QPushButton("Сбросить по умолчанию")
        self.reset_btn.clicked.connect(self._reset_to_defaults)
        buttons_layout.addWidget(self.reset_btn)
        
        layout.addLayout(buttons_layout)
        layout.addStretch()
    
    def _load_values(self):
        """Загрузка значений из настроек."""
        b = self.settings.buy
        self.budget_input.setValue(b.budget)
        self.delay_input.setValue(b.delay)
        self.start_row_input.setValue(b.start_row)
        self.transport_cost_input.setValue(b.transport_cost_per_kg)
        self.tier6_checkbox.setChecked(b.tier6_only)
        
        self.cumulative_spent_input.setValue(self.settings.cumulative_spent)
    
    def _save_settings(self):
        """Сохранение настроек."""
        b = self.settings.buy
        b.budget = self.budget_input.value()
        b.delay = self.delay_input.value()
        b.start_row = self.start_row_input.value()
        b.transport_cost_per_kg = self.transport_cost_input.value()
        b.tier6_only = self.tier6_checkbox.isChecked()
        
        save_settings(self.settings)
        QMessageBox.information(self, "Успех", "Настройки сохранены!")
    
    def _reset_stats(self):
        """Сброс статистики."""
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Сбросить накопленную статистику?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.settings.cumulative_spent = 0
            self.cumulative_spent_input.setValue(0)
            save_settings(self.settings)
    
    def _reset_to_defaults(self):
        """Сброс к значениям по умолчанию."""
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Сбросить все настройки к значениям по умолчанию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.settings.buy = BuySettings()
            self._load_values()
            save_settings(self.settings)


# Import needed for reset
from config import BuySettings

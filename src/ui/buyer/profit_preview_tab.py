"""
Вкладка предпросмотра профитов (Profit Preview Tab)
Показывает отсортированный список предметов с профитами из сканера.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QHeaderView, QComboBox, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush

from ...utils.price_storage import price_storage
from ...utils.config import get_config
from ..styles import COLORS


class ProfitPreviewTab(QWidget):
    """
    Вкладка отображения профитов из сканера.
    Позволяет увидеть как будут отсортированы предметы в умном режиме.
    """
    
    def __init__(self):
        super().__init__()
        self.config = get_config()
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # --- Header ---
        header_layout = QHBoxLayout()
        
        title = QLabel("📊 Профиты из сканера")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #e6edf3;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Выбор города
        city_lbl = QLabel("Город:")
        city_lbl.setStyleSheet("color: #8b949e;")
        header_layout.addWidget(city_lbl)
        
        self.city_combo = QComboBox()
        self.city_combo.setMinimumWidth(150)
        self.city_combo.currentTextChanged.connect(self._on_city_changed)
        header_layout.addWidget(self.city_combo)
        
        # Выбор сортировки
        sort_lbl = QLabel("Сортировка:")
        sort_lbl.setStyleSheet("color: #8b949e;")
        header_layout.addWidget(sort_lbl)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("💰 По серебру", "silver")
        self.sort_combo.addItem("📊 По % профита", "percent")
        self.sort_combo.currentIndexChanged.connect(self._refresh_table)
        header_layout.addWidget(self.sort_combo)
        
        # Кнопка обновления
        refresh_btn = QPushButton("🔄 Обновить")
        refresh_btn.clicked.connect(self.refresh_data)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # --- Разделитель ---
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {COLORS['border']};")
        layout.addWidget(line)
        
        # --- Таблица ---
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Предмет", "Тир", "Энч", "Цена рынка", "Профит (s)", "Профит (%)"
        ])
        
        # Настройка колонок
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 6):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #0d1117;
                color: #e6edf3;
                gridline-color: #30363d;
                border: 1px solid #30363d;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #1f6feb;
            }
            QHeaderView::section {
                background-color: #161b22;
                color: #8b949e;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #30363d;
            }
        """)
        
        layout.addWidget(self.table)
        
        # --- Статус ---
        self.status_label = QLabel("Нет данных. Нажмите 'Обновить'.")
        self.status_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        layout.addWidget(self.status_label)
        
    def showEvent(self, event):
        """При открытии вкладки обновляем данные"""
        super().showEvent(event)
        self._update_city_list()
        self.refresh_data()
        
    def _update_city_list(self):
        """Обновить список городов из price_storage"""
        self.city_combo.blockSignals(True)
        self.city_combo.clear()
        
        cities = price_storage.get_cities()
        # Убираем Black Market - это цель, а не источник
        cities = [c for c in cities if c != "Black Market"]
        
        for city in cities:
            self.city_combo.addItem(city)
            
        self.city_combo.blockSignals(False)
        
    def _on_city_changed(self, city):
        """При смене города обновляем таблицу"""
        self._refresh_table()
        
    def refresh_data(self):
        """Полное обновление данных"""
        self._update_city_list()
        self._refresh_table()
        
    def _refresh_table(self):
        """Обновить таблицу профитов"""
        self.table.setRowCount(0)
        
        city = self.city_combo.currentText()
        if not city:
            self.status_label.setText("Выберите город")
            return
            
        # Получаем данные
        items = self._get_profitable_items(city)
        
        if not items:
            self.status_label.setText(f"Нет данных для города: {city}")
            return
            
        # Сортировка
        sort_mode = self.sort_combo.currentData()
        if sort_mode == "percent":
            items.sort(key=lambda x: x[5], reverse=True)  # profit_percent
        else:
            items.sort(key=lambda x: x[3], reverse=True)  # profit
            
        # Заполняем таблицу
        self.table.setRowCount(len(items))
        
        for row, (name, tier, enchant, profit, market_price, profit_pct) in enumerate(items):
            # Предмет
            item_name = QTableWidgetItem(name)
            self.table.setItem(row, 0, item_name)
            
            # Тир
            tier_item = QTableWidgetItem(f"T{tier}")
            tier_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, tier_item)
            
            # Энчант
            ench_item = QTableWidgetItem(f".{enchant}")
            ench_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, ench_item)
            
            # Цена рынка
            price_item = QTableWidgetItem(f"{int(market_price):,}")
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 3, price_item)
            
            # Профит (серебро)
            profit_item = QTableWidgetItem(f"+{int(profit):,}")
            profit_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            # Цвет в зависимости от профита
            if profit > 5000:
                profit_item.setForeground(QBrush(QColor("#3fb950")))  # Зеленый
            elif profit > 2000:
                profit_item.setForeground(QBrush(QColor("#d29922")))  # Желтый
            else:
                profit_item.setForeground(QBrush(QColor("#8b949e")))  # Серый
            self.table.setItem(row, 4, profit_item)
            
            # Профит (%)
            pct_item = QTableWidgetItem(f"{profit_pct:.1f}%")
            pct_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            # Цвет в зависимости от процента
            if profit_pct > 30:
                pct_item.setForeground(QBrush(QColor("#3fb950")))
            elif profit_pct > 15:
                pct_item.setForeground(QBrush(QColor("#d29922")))
            else:
                pct_item.setForeground(QBrush(QColor("#8b949e")))
            self.table.setItem(row, 5, pct_item)
            
        self.status_label.setText(f"Найдено {len(items)} выгодных предметов для {city}")
        
    def _get_profitable_items(self, city: str) -> list:
        """
        Получить список профитных предметов.
        Returns: [(name, tier, enchant, profit, market_price, profit_percent), ...]
        """
        items = []
        city_prices = price_storage.get_city_prices(city)
        bm_prices = price_storage.get_city_prices("Black Market")
        
        if not city_prices or not bm_prices:
            return []
            
        for item_name, variants in city_prices.items():
            if item_name not in bm_prices:
                continue
                
            bm_variants = bm_prices[item_name]
            
            for key, data in variants.items():
                market_price = data.get("price", 0)
                if market_price <= 0:
                    continue
                    
                if key not in bm_variants:
                    continue
                    
                bm_price = bm_variants[key].get("price", 0)
                if bm_price <= 0:
                    continue
                    
                try:
                    t_str, e_str = key.replace("T", "").split(".")
                    tier = int(t_str)
                    enchant = int(e_str)
                    
                    # Profit Calc (Tax 6.5%)
                    net_bm = bm_price * 0.935
                    profit = net_bm - market_price
                    profit_percent = ((net_bm - market_price) / market_price) * 100
                    
                    # Фильтр: профит > 500
                    if profit > 500:
                        items.append((item_name, tier, enchant, profit, market_price, profit_percent))
                        
                except Exception:
                    continue
                    
        return items

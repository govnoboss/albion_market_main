"""
Вкладка для расчета профита (Black Market - Source City)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableWidget, QTableWidgetItem, QHeaderView, 
    QComboBox, QPushButton
)
from PyQt6.QtCore import Qt
from ..utils.price_storage import get_price_storage

class NumericTableWidgetItem(QTableWidgetItem):
    """Item for proper numeric sorting"""
    def __lt__(self, other):
        try:
            # Удаляем запятые и проценты для сортировки
            val1 = float(self.text().replace(',', '').replace('%', ''))
            val2 = float(other.text().replace(',', '').replace('%', ''))
            return val1 < val2
        except ValueError:
            return super().__lt__(other)

class ProfitsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.storage = get_price_storage()
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # === Controls ===
        controls_layout = QHBoxLayout()
        
        lbl = QLabel("🏙️ Город закупки:")
        lbl.setStyleSheet("font-weight: bold; color: #8b949e;")
        controls_layout.addWidget(lbl)
        
        self.city_combo = QComboBox()
        self.city_combo.setMinimumWidth(150)
        # Темная тема для ComboBox
        self.city_combo.setStyleSheet("""
            QComboBox {
                background-color: #161b22;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 5px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #8b949e;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #161b22;
                color: #c9d1d9;
                selection-background-color: #1f6feb;
                border: 1px solid #30363d;
            }
        """)
        self.city_combo.currentIndexChanged.connect(self._calculate_profits)
        controls_layout.addWidget(self.city_combo)
        
        refresh_btn = QPushButton("🔄 Обновить")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #30363d;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_data)
        controls_layout.addWidget(refresh_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # === Table ===
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Предмет", "Тир.Чары", 
            "Цена BM", "Цена Города", 
            "Профит", "%", "Обновлено"
        ])
        
        # Включаем сортировку
        self.table.setSortingEnabled(True)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Tier
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # BM
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # City
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents) # Profit
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents) # %
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents) # Time
        
        layout.addWidget(self.table)
        
        # Initial Load
        self.refresh_data()
        
    def refresh_data(self):
        """Reload data and repopulate combo"""
        self.storage.reload()
        all_cities = self.storage.get_cities()
        
        # Filter: exclude BM itself from 'Source' list
        # Using both English and Russian variants just in case
        sources = [c for c in all_cities if c not in ["Black Market", "Черный рынок"]]
        sources.sort()
        
        current_source = self.city_combo.currentText()
        self.city_combo.blockSignals(True)
        self.city_combo.clear()
        self.city_combo.addItems(sources)
        
        # Restore selection if possible
        if current_source in sources:
            self.city_combo.setCurrentText(current_source)
            
        self.city_combo.blockSignals(False)
        self._calculate_profits()
        
    def _calculate_profits(self):
        """Calculate and display profits"""
        # Отключаем сортировку на время обновления
        self.table.setSortingEnabled(False)
        
        source_city = self.city_combo.currentText()
        if not source_city:
            self.table.setRowCount(0)
            self.table.setSortingEnabled(True)
            return

        # 1. Get BM Data
        bm_data = self.storage.get_city_prices("Black Market")
        if not bm_data:
            # Fallback for russian name
            bm_data = self.storage.get_city_prices("Черный рынок")
            
        if not bm_data:
            self.table.setRowCount(0)
            self.table.setSortingEnabled(True)
            return

        # 2. Get Source Data
        source_data = self.storage.get_city_prices(source_city)
        if not source_data:
            self.table.setRowCount(0)
            self.table.setSortingEnabled(True)
            return
            
        rows = []
        
        # 3. Iterate BM items and match with Source
        for item_name, variants in bm_data.items():
            if item_name not in source_data:
                continue
                
            source_variants = source_data[item_name]
            
            for variant_key, bm_info in variants.items():
                if variant_key not in source_variants:
                    continue
                    
                # Match Found!
                bm_price = bm_info['price']
                
                source_info = source_variants[variant_key]
                source_price = source_info['price']
                
                if source_price <= 0: continue
                
                # Taxes: 4.5% Sell Tax + 2.0% Setup Fee = 6.5%
                tax_rate = 0.065
                revenue_after_tax = bm_price * (1 - tax_rate)
                
                profit = int(revenue_after_tax - source_price)
                percent = (profit / source_price) * 100 if source_price > 0 else 0
                
                rows.append({
                    "name": item_name,
                    "variant": variant_key,
                    "bm_price": bm_price,
                    "source_price": source_price,
                    "profit": profit,
                    "percent": percent,
                    "updated": bm_info['updated'].split('T')[1][:8]
                })
        
        # 4. Sort by Profit (Desc) DEFAULT
        rows.sort(key=lambda x: x['profit'], reverse=True)
        
        # 5. Populate Table
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(row['name']))
            self.table.setItem(r, 1, QTableWidgetItem(row['variant']))
            
            # Format Prices (NumericItem)
            self.table.setItem(r, 2, NumericTableWidgetItem(f"{row['bm_price']:,}"))
            self.table.setItem(r, 3, NumericTableWidgetItem(f"{row['source_price']:,}"))
            
            # Profit Color
            profit_item = NumericTableWidgetItem(f"{row['profit']:,}")
            if row['profit'] > 0:
                profit_item.setForeground(Qt.GlobalColor.green)
            else:
                profit_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(r, 4, profit_item)
            
            # Percent
            pct_item = NumericTableWidgetItem(f"{row['percent']:.1f}%")
            if row['percent'] > 0:
                pct_item.setForeground(Qt.GlobalColor.green)
            else:
                pct_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(r, 5, pct_item)
            
            self.table.setItem(r, 6, QTableWidgetItem(row['updated']))
            
        # Включаем сортировку обратно
        self.table.setSortingEnabled(True)

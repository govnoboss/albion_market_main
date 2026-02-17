"""
Вкладка для расчета профита (Black Market - Source City)
"""

import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableWidget, QTableWidgetItem, QHeaderView, 
    QComboBox, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from ..utils.price_storage import get_price_storage

class ProfitLoader(QThread):
    """Фоновый поток для расчета профитов"""
    data_ready = pyqtSignal(list)
    finished_loading = pyqtSignal()
    
    def __init__(self, storage, buy_city, sell_city):
        super().__init__()
        self.storage = storage
        self.buy_city = buy_city
        self.sell_city = sell_city
        
    def run(self):
        # 1. IO: Обновляем цены
        self.storage.reload()
        
        # 2. Получаем данные
        buy_data = self.storage.get_city_prices(self.buy_city)
        sell_data = self.storage.get_city_prices(self.sell_city)
        
        rows = []
        
        if buy_data and sell_data:
            # 3. CPU: Расчет
            for item_name, variants in sell_data.items():
                if item_name not in buy_data:
                    continue
                    
                buy_variants = buy_data[item_name]
                
                for variant_key, sell_info in variants.items():
                    if variant_key not in buy_variants:
                        continue
                        
                    sell_price = sell_info['price']
                    buy_info = buy_variants[variant_key]
                    buy_price = buy_info['price']
                    
                    # Пропускаем вариации с нулевой ценой (невалидные данные)
                    if sell_price <= 0 or buy_price <= 0: 
                        continue
                    
                    # Taxes: 6.5% everywhere (as per USER feedback)
                    tax_rate = 0.065
                    revenue_after_tax = sell_price * (1 - tax_rate)
                    
                    profit = int(revenue_after_tax - buy_price)
                    percent = (profit / buy_price) * 100 if buy_price > 0 else 0
                    
                    # Edge Case: OCR errors
                    if percent > 1000:
                        continue
                    
                    rows.append({
                        "name": item_name,
                        "variant": variant_key,
                        "sell_price": sell_price,
                        "buy_price": buy_price,
                        "profit": profit,
                        "percent": percent,
                        "updated": sell_info['updated'].split('T')[1][:8]
                    })
            
            # 4. CPU: Начальная сортировка
            rows.sort(key=lambda x: x['profit'], reverse=True)
            
        self.data_ready.emit(rows)
        self.finished_loading.emit()

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
        self.loader = None
        self._is_updating = False # Флаг для предотвращения рекурсии при programmatic change
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # === Controls ===
        controls_layout = QHBoxLayout()
        
        lbl_buy = QLabel("🏙️ Купить в:")
        lbl_buy.setStyleSheet("font-weight: bold; color: #8b949e;")
        controls_layout.addWidget(lbl_buy)
        
        self.buy_city_combo = QComboBox()
        self.buy_city_combo.setMinimumWidth(130)
        self._style_combo(self.buy_city_combo)
        self.buy_city_combo.currentIndexChanged.connect(self.refresh_data)
        controls_layout.addWidget(self.buy_city_combo)

        lbl_sell = QLabel(" ➡️ Продать в:")
        lbl_sell.setStyleSheet("font-weight: bold; color: #8b949e;")
        controls_layout.addWidget(lbl_sell)
        
        self.sell_city_combo = QComboBox()
        self.sell_city_combo.setMinimumWidth(130)
        self._style_combo(self.sell_city_combo)
        self.sell_city_combo.currentIndexChanged.connect(self.refresh_data)
        controls_layout.addWidget(self.sell_city_combo)
        
        self.refresh_btn = QPushButton("🔄 Обновить")
        self.refresh_btn.setStyleSheet("""
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
            QPushButton:disabled {
                background-color: #161b22;
                color: #484f58;
            }
        """)
        self.refresh_btn.clicked.connect(self.refresh_data)
        controls_layout.addWidget(self.refresh_btn)
        
        self.clean_btn = QPushButton("🗑️ Очистить старые")
        self.clean_btn.setToolTip("Удалить записи предыдущих сканирований (оставить только текущие)")
        self.clean_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #f85149;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #30363d;
                background-color: #b31d28;
                color: #ffffff;
            }
        """)
        self.clean_btn.clicked.connect(self.request_clean_history)
        controls_layout.addWidget(self.clean_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # === Table ===
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Предмет", "Тир.Чары", 
            "Цена Продажи", "Цена Покупки", 
            "Профит", "%", "Обновлено"
        ])
        
        # Включаем сортировку
        self.table.setSortingEnabled(True)
        # Подключаем сигнал изменения ячейки
        self.table.itemChanged.connect(self.on_item_changed)
        
        # Стилизация таблицы и редактора
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #0d1117;
                color: #c9d1d9;
                gridline-color: #30363d;
                selection-background-color: #1f6feb;
                selection-color: #ffffff;
            }
            QTableWidget QLineEdit {
                background-color: #161b22;
                color: #ffffff;
                border: 1px solid #1f6feb;
                border-radius: 2px;
                padding: 1px;
            }
        """)

        # Начальная настройка заголовков (без ResizeToContents для скорости инициализации)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        
        layout.addWidget(self.table)
        
        # Initial Load Cities
        self._load_cities()
        
    def _style_combo(self, combo):
        """Apply dark theme to combo boxes"""
        combo.setStyleSheet("""
            QComboBox {
                background-color: #161b22;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 5px;
            }
            QComboBox::drop-down { border: none; }
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

    def _load_cities(self):
        """Initial city loading and refresh"""
        self.storage.reload()
        all_cities = self.storage.get_cities()
        all_cities.sort()
        
        # Запоминаем текущий выбор
        cur_buy = self.buy_city_combo.currentText()
        cur_sell = self.sell_city_combo.currentText()
        
        self.buy_city_combo.blockSignals(True)
        self.sell_city_combo.blockSignals(True)
        
        self.buy_city_combo.clear()
        self.sell_city_combo.clear()
        
        self.buy_city_combo.addItems(all_cities)
        self.sell_city_combo.addItems(all_cities)
        
        # Восстанавливаем выбор или ставим дефолты
        if cur_buy and cur_buy in all_cities:
            self.buy_city_combo.setCurrentText(cur_buy)
        elif "Martlock" in all_cities:
            idx = all_cities.index("Martlock")
            self.buy_city_combo.setCurrentIndex(idx)
        
        if cur_sell and cur_sell in all_cities:
            self.sell_city_combo.setCurrentText(cur_sell)
        elif "Black Market" in all_cities:
            idx = all_cities.index("Black Market")
            self.sell_city_combo.setCurrentIndex(idx)
        elif "Черный рынок" in all_cities:
            idx = all_cities.index("Черный рынок")
            self.sell_city_combo.setCurrentIndex(idx)
            
        self.buy_city_combo.blockSignals(False)
        self.sell_city_combo.blockSignals(False)
        
        if all_cities and not cur_buy: # Только при первом запуске
            self.refresh_data()
        
    def refresh_data(self):
        """Start data reload in background"""
        # Сначала обновляем список городов (вдруг просканировали новый)
        self._load_cities()
        
        buy_city = self.buy_city_combo.currentText()
        sell_city = self.sell_city_combo.currentText()
        if not buy_city or not sell_city:
            return
        
        if buy_city == sell_city:
            # Maybe show warning? But user might want to see prices in one city.
            pass

        # UI State: Loading
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("⏳ Загрузка...")
        self.buy_city_combo.setEnabled(False)
        self.sell_city_combo.setEnabled(False)
        
        # Start Thread
        self.loader = ProfitLoader(self.storage, buy_city, sell_city)
        self.loader.data_ready.connect(self.on_data_ready)
        self.loader.finished_loading.connect(self.on_loading_finished)
        self.loader.start()
        
    def on_loading_finished(self):
        """Cleanup after thread"""
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("🔄 Обновить")
        self.buy_city_combo.setEnabled(True)
        self.sell_city_combo.setEnabled(True)
        
    def on_data_ready(self, rows):
        """Populate table with optimized batch updates"""
        self._is_updating = True # Блокируем обработку изменений
        try:
            # 1. Disable Updates
            self.table.setSortingEnabled(False)
            self.table.setUpdatesEnabled(False)
            
            # 2. Clear & Populate
            self.table.setRowCount(len(rows))
            
            for r, row in enumerate(rows):
                self.table.setItem(r, 0, QTableWidgetItem(row['name']))
                self.table.setItem(r, 1, QTableWidgetItem(row['variant']))
                
                # Format Prices (Editable)
                sell_item = NumericTableWidgetItem(f"{row['sell_price']:,}")
                # Разрешаем редактирование
                sell_item.setFlags(sell_item.flags() | Qt.ItemFlag.ItemIsEditable) 
                self.table.setItem(r, 2, sell_item)
                
                buy_item = NumericTableWidgetItem(f"{row['buy_price']:,}")
                buy_item.setFlags(buy_item.flags() | Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r, 3, buy_item)
                
                # Profit Color
                profit_item = NumericTableWidgetItem(f"{row['profit']:,}")
                # Profit не редактируем
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
            
            # 3. Optimize Column Widths (Once!)
            self.table.resizeColumnsToContents()
            header = self.table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch) # Name Stretches
            
            # 4. Restore Updates
            self.table.setUpdatesEnabled(True)
            self.table.setSortingEnabled(True)
        finally:
            self._is_updating = False

    def request_clean_history(self):
        """Handle history cleanup request"""
        reply = QMessageBox.question(
            self, 
            'Подтверждение очистки', 
            "Вы уверены, что хотите удалить записи прошлых сессий?\n\nБудут удалены все цены, кроме полученных в последнем сеансе сканирования.\nЭто действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            count = self.storage.clean_history(gap_minutes=30)
            if count > 0:
                QMessageBox.information(self, "Очистка завершена", f"Удалено старых записей: {count}")
                self.refresh_data()
            else:
                QMessageBox.information(self, "Очистка", "Нет старых записей для удаления.")

    def on_item_changed(self, item):
        """Handle price editing in real-time"""
        if self._is_updating:
            return
            
        col = item.column()
        # Только колонки цены (2 - BM, 3 - Source)
        if col not in [2, 3]:
            return
            
        row = item.row()
        table = self.table
        
        # Получаем данные
        try:
            raw_text = item.text().replace(',', '').replace('%', '').strip()
            new_price = int(float(raw_text)) # Поддерживаем float ввод, конвертируем в int
        except ValueError:
            # Revert logic could go here, but complex with QTableWidget signals.
            return

        # Идентификация предмета
        try:
            item_name = table.item(row, 0).text()
            variant_raw = table.item(row, 1).text() # "T4.0"
            # Парсим тир/энчант для save_price
            # variant format: T4.0 -> tier=4, enchant=0
            match = re.match(r"T(\d+)\.(\d+)", variant_raw)
            if not match:
                return
            tier = int(match.group(1))
            enchant = int(match.group(2))
            
            # Определяем город
            target_city = self.sell_city_combo.currentText() if col == 2 else self.buy_city_combo.currentText()
            variant_key = f"T{tier}.{enchant}"
            
            # 1. Если цена 0 — удаляем запись из БД и строку из таблицы
            if new_price <= 0:
                self.storage.delete_price(target_city, item_name, variant_key)
                self._is_updating = True
                try:
                    self.table.removeRow(row)
                finally:
                    self._is_updating = False
                return
            
            # 2. Сохраняем новую цену
            # Качество считаем 1 (Normal), т.к. таблица агрегирует
            self.storage.save_price(target_city, item_name, tier, enchant, 1, new_price)
            
            # 3. Мгновенный пересчет профита для этой строки
            # Считываем актуальные данные из ячеек (учитывая что другую цену могли не менять)
            sell_text = table.item(row, 2).text().replace(',', '')
            buy_text = table.item(row, 3).text().replace(',', '')
            
            # Если одну из цен удалили/сломали, берем 0
            try: sell_p = int(float(sell_text))
            except: sell_p = 0
            
            try: buy_p = int(float(buy_text))
            except: buy_p = 0
            
            # Формула
            tax_rate = 0.065 # Fixed 6.5% everywhere
            revenue = sell_p * (1 - tax_rate)
            profit = int(revenue - buy_p)
            percent = (profit / buy_p) * 100 if buy_p > 0 else 0
            
            # 4. Обновляем UI (Profit & %)
            self._is_updating = True # Блокируем сигналы, т.к. меняем ячейки
            try:
                # Обновляем форматирование текущей ячейки (вернуть запятые)
                item.setText(f"{new_price:,}")
                
                # Обновляем Profit
                profit_item = table.item(row, 4)
                profit_item.setText(f"{profit:,}")
                if profit > 0:
                    profit_item.setForeground(Qt.GlobalColor.green)
                else:
                    profit_item.setForeground(Qt.GlobalColor.red)
                    
                # Обновляем Percent
                percent_item = table.item(row, 5)
                percent_item.setText(f"{percent:.1f}%")
                if percent > 0:
                    percent_item.setForeground(Qt.GlobalColor.green)
                else:
                    percent_item.setForeground(Qt.GlobalColor.red)
                    
            finally:
                self._is_updating = False
                
        except Exception as e:
            print(f"Edit error: {e}")

"""
Вкладка для расчета профита (Black Market - Source City)
"""

import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableWidget, QTableWidgetItem, QHeaderView, 
    QComboBox, QPushButton, QMessageBox, QAbstractItemView, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from ..utils.price_storage import get_price_storage
from ..utils.logger import get_logger
from ..utils.localization import get_text
from .styles import MAIN_STYLE

logger = get_logger()

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
        rows = []
        try:
            # 1. IO: Обновляем цены
            self.storage.reload()
            
            # 2. Получаем данные
            buy_data = self.storage.get_city_prices(self.buy_city)
            sell_data = self.storage.get_city_prices(self.sell_city)
            
            if buy_data and sell_data:
                # 3. CPU: Расчет
                for item_name, variants in sell_data.items():
                    if item_name not in buy_data:
                        continue
                        
                    buy_variants = buy_data[item_name]
                    
                    for variant_key, sell_info in variants.items():
                        if variant_key not in buy_variants:
                            continue
                            
                        sell_price = sell_info.get('price', 0)
                        buy_info = buy_variants[variant_key]
                        buy_price = buy_info.get('price', 0)
                        
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
                        
                        updated_raw = sell_info.get('updated', '')
                        updated_str = updated_raw.split('T')[1][:8] if 'T' in updated_raw else updated_raw[:8]
                        
                        rows.append({
                            "name": item_name,
                            "variant": variant_key,
                            "sell_price": sell_price,
                            "buy_price": buy_price,
                            "profit": profit,
                            "percent": percent,
                            "updated": updated_str
                        })
                
                # 4. CPU: Начальная сортировка
                rows.sort(key=lambda x: x['profit'], reverse=True)
        except Exception:
            rows = []
            
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
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # === Header ===
        header = QHBoxLayout()
        title = QLabel(get_text("finance_title", "📈 Анализ профита"))
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)
        
        # === Controls Group ===
        ctrl_group = QGroupBox(get_text("finance_controls_group", "Параметры фильтрации"))
        controls_layout = QHBoxLayout(ctrl_group)
        controls_layout.setSpacing(15)
        
        lbl_buy = QLabel(get_text("finance_header", "Купить в:"))
        controls_layout.addWidget(lbl_buy)
        
        self.buy_city_combo = QComboBox()
        self.buy_city_combo.setMinimumWidth(150)
        self.buy_city_combo.currentIndexChanged.connect(self.refresh_data)
        controls_layout.addWidget(self.buy_city_combo)
 
        lbl_sell = QLabel(get_text("finance_arrow", " ➡️ Продать в:"))
        controls_layout.addWidget(lbl_sell)
        
        self.sell_city_combo = QComboBox()
        self.sell_city_combo.setMinimumWidth(150)
        self.sell_city_combo.currentIndexChanged.connect(self.refresh_data)
        controls_layout.addWidget(self.sell_city_combo)
        
        # Actions
        controls_layout.addStretch()
        
        self.refresh_btn = QPushButton(get_text("finance_refresh", "🔄 ОБНОВИТЬ"))
        self.refresh_btn.setObjectName("primary")
        self.refresh_btn.setMinimumHeight(35)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh_data)
        controls_layout.addWidget(self.refresh_btn)
        
        self.delete_btn = QPushButton(get_text("finance_delete", "🗑️ УДАЛИТЬ"))
        self.delete_btn.setObjectName("danger")
        self.delete_btn.setMinimumHeight(35)
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.delete_selected_record)
        controls_layout.addWidget(self.delete_btn)
        
        self.clean_btn = QPushButton(get_text("finance_clean", "🧹 ОЧИСТИТЬ СТАРЫЕ"))
        self.clean_btn.setObjectName("danger")
        self.clean_btn.setMinimumHeight(35)
        self.clean_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clean_btn.setToolTip(get_text("finance_clean_tip", "Удалить записи предыдущих сканирований (оставить только текущие)"))
        self.clean_btn.clicked.connect(self.request_clean_history)
        controls_layout.addWidget(self.clean_btn)
        
        layout.addWidget(ctrl_group)
        
        # === Table ===
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            get_text("finance_col_item", "Предмет"), 
            get_text("finance_col_variant", "Тир.Чары"), 
            get_text("finance_col_sell", "Цена Продажи"), 
            get_text("finance_col_buy", "Цена Покупки"), 
            get_text("finance_col_profit", "Профит"), 
            get_text("finance_col_percent", "%"), 
            get_text("finance_col_updated", "Обновлено")
        ])
        
        # Включаем сортировку
        self.table.setSortingEnabled(True)
        # Подключаем сигналы
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.itemSelectionChanged.connect(self.update_delete_button_state)
        
        # Настройка поведения выделения
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)

        # Начальная настройка заголовков (без ResizeToContents для скорости инициализации)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        
        layout.addWidget(self.table)
        
        # Initial Load Cities
        self._load_cities()
        
    def _load_cities(self):
        """Initial city loading and refresh"""
        try:
            self.storage.reload()
            all_cities = self.storage.get_cities()
            all_cities.sort()
        except Exception:
            all_cities = []
        
        # Запоминаем текущий выбор
        cur_buy = self.buy_city_combo.currentText()
        cur_sell = self.sell_city_combo.currentText()
        
        self.buy_city_combo.blockSignals(True)
        self.sell_city_combo.blockSignals(True)
        
        self.buy_city_combo.clear()
        self.sell_city_combo.clear()
        
        if not all_cities:
            self.buy_city_combo.blockSignals(False)
            self.sell_city_combo.blockSignals(False)
            return
        
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
        
        if not cur_buy: # Только при первом запуске
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
        self.refresh_btn.setText(get_text("finance_loading", "⏳ Загрузка..."))
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
        self.refresh_btn.setText(get_text("finance_refresh", "🔄 Обновить"))
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
                # Columns: 0:Name, 1:Variant, 2:Sell, 3:Buy, 4:Profit, 5:%, 6:Updated
                
                # Non-editable items
                name_item = QTableWidgetItem(row['name'])
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r, 0, name_item)
                
                variant_item = QTableWidgetItem(row['variant'])
                variant_item.setFlags(variant_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r, 1, variant_item)
                
                # Format Prices (Editable)
                sell_item = NumericTableWidgetItem(f"{row['sell_price']:,}")
                sell_item.setFlags(sell_item.flags() | Qt.ItemFlag.ItemIsEditable) 
                self.table.setItem(r, 2, sell_item)
                
                buy_item = NumericTableWidgetItem(f"{row['buy_price']:,}")
                buy_item.setFlags(buy_item.flags() | Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r, 3, buy_item)
                
                # Profit Color (Non-editable)
                profit_item = NumericTableWidgetItem(f"{row['profit']:,}")
                profit_item.setFlags(profit_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if row['profit'] > 0:
                    profit_item.setForeground(Qt.GlobalColor.green)
                else:
                    profit_item.setForeground(Qt.GlobalColor.red)
                self.table.setItem(r, 4, profit_item)
                
                # Percent (Non-editable)
                pct_item = NumericTableWidgetItem(f"{row['percent']:.1f}%")
                pct_item.setFlags(pct_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if row['percent'] > 0:
                    pct_item.setForeground(Qt.GlobalColor.green)
                else:
                    pct_item.setForeground(Qt.GlobalColor.red)
                self.table.setItem(r, 5, pct_item)
                
                updated_item = QTableWidgetItem(row['updated'])
                updated_item.setFlags(updated_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r, 6, updated_item)
            
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
            get_text("finance_clean_confirm_title", "Подтверждение очистки"), 
            get_text("finance_clean_confirm_msg", "Вы уверены, что хотите удалить записи прошлых сессий?\n\nБудут удалены все цены, кроме полученных в последнем сеансе сканирования.\nЭто действие нельзя отменить."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            count = self.storage.clean_history(gap_minutes=30)
            if count > 0:
                QMessageBox.information(self, get_text("finance_clean_done_title", "Очистка завершена"), get_text("finance_clean_done_msg", "Удалено старых записей: {count}").format(count=count))
                self.refresh_data()
            else:
                QMessageBox.information(self, get_text("finance_clean", "Очистка"), get_text("finance_clean_no_records", "Нет старых записей для удаления."))

    def update_delete_button_state(self):
        """Toggle delete button based on selection"""
        self.delete_btn.setEnabled(len(self.table.selectionModel().selectedRows()) > 0)

    def delete_selected_record(self):
        """Delete selected row from DB and UI"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return
            
        row_idx = selected_rows[0].row()
        item_name = self.table.item(row_idx, 0).text()
        variant_key = self.table.item(row_idx, 1).text()
        
        confirm = QMessageBox.question(
            self, 
            get_text("finance_delete_confirm_title", "Удаление записи"), 
            get_text("finance_delete_confirm_msg", "Вы уверены, что хотите удалить запись:\n\n{item} ({variant})?\n\nБудут удалены цены для ОБОИХ городов в этой строке.").format(item=item_name, variant=variant_key),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            buy_city = self.buy_city_combo.currentText()
            sell_city = self.sell_city_combo.currentText()
            
            # Удаляем из обоих городов
            self.storage.delete_price(buy_city, item_name, variant_key)
            self.storage.delete_price(sell_city, item_name, variant_key)
            
            self._is_updating = True
            try:
                self.table.removeRow(row_idx)
            finally:
                self._is_updating = False

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
            logger.error(f"Edit error: {e}")

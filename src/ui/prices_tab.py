"""
Вкладка просмотра цен по городам
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QTableWidget, 
    QTableWidgetItem, QHeaderView, QLabel, QPushButton, QHBoxLayout,
    QLineEdit, QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt, QTimer

from ..utils.price_storage import get_price_storage


class PricesTab(QWidget):
    def __init__(self):
        super().__init__()
        self.storage = get_price_storage()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Заголовок и кнопки
        top_layout = QHBoxLayout()
        header = QLabel("💰 Цены по городам")
        header.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 5px;")
        top_layout.addWidget(header)
        
        top_layout.addStretch()
        
        # Поиск
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск предмета...")
        self.search_input.setFixedWidth(200)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #161b22;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 5px;
            }
        """)
        self.search_input.textChanged.connect(self.filter_table)
        top_layout.addWidget(self.search_input)
        
        # Кнопка удаления
        self.delete_btn = QPushButton("🗑️ Удалить запись")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #b33e3e; /* Red hover */
                color: white;
                border-color: #b33e3e;
            }
            QPushButton:disabled {
                background-color: #161b22;
                color: #484f58;
                border-color: #30363d;
            }
        """)
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.delete_selected_record)
        self.delete_btn.clicked.connect(self.delete_selected_record)
        top_layout.addWidget(self.delete_btn)
        
        # Кнопка очистки старых
        clean_old_btn = QPushButton("🧹 Очистить старые")
        clean_old_btn.setToolTip("Удалить цены, которым больше X часов")
        clean_old_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #f85149;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #b31d28;
                color: #ffffff;
            }
        """)
        clean_old_btn.clicked.connect(self.clean_old_records)
        top_layout.addWidget(clean_old_btn)
        
        refresh_btn = QPushButton("Обновить")
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
        top_layout.addWidget(refresh_btn)
        
        layout.addLayout(top_layout)
        
        # Вкладки городов
        self.city_tabs = QTabWidget()
        self.city_tabs.currentChanged.connect(self.on_tab_changed)
        layout.addWidget(self.city_tabs)
        
        # Инициализация (первая загрузка)
        self.refresh_data()

    def refresh_data(self):
        """Обновить данные во всех вкладках"""
        self.storage.reload()
        cities = self.storage.get_cities()
        
        # Сохраняем текущий активный таб
        current_tab_idx = self.city_tabs.currentIndex()
        current_tab_text = self.city_tabs.tabText(current_tab_idx) if current_tab_idx >= 0 else None
        
        self.city_tabs.clear()
        
        if not cities:
            self.city_tabs.addTab(QLabel("Нет данных. Запустите бота для сканирования."), "Пусто")
            self.delete_btn.setEnabled(False)
            return
            
        cities.sort()
        for city in cities:
            tab = self._create_city_table(city)
            self.city_tabs.addTab(tab, city)
            
        # Восстанавливаем вкладку
        if current_tab_text:
            for i in range(self.city_tabs.count()):
                if self.city_tabs.tabText(i) == current_tab_text:
                    self.city_tabs.setCurrentIndex(i)
                    break
        
        # Восстанавливаем фильтр
        self.filter_table(self.search_input.text())
        self.update_delete_button_state()

    def _create_city_table(self, city):
        """Создать таблицу для конкретного города"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 5, 0, 0)
        
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Предмет", "Вариант", "Цена", "Обновлено"])
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Настройка заголовков
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch) # Предмет
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Вариант
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Цена
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # Время
        
        # Заполняем данными
        items_data = self.storage.get_city_prices(city)
        
        row_count = 0
        for item_name, variants in items_data.items():
            row_count += len(variants)
            
        table.setRowCount(row_count)
        
        current_row = 0
        # Сортируем предметы по имени
        for item_name in sorted(items_data.keys()):
            variants = items_data[item_name]
            # Сортируем варианты (по ключу T4.0 и т.д.)
            for variant_key in sorted(variants.keys()):
                data = variants[variant_key]
                price = data['price']
                updated = data['updated'].split('T')[1][:8] # Только время HH:MM:SS
                
                # Item Name
                table.setItem(current_row, 0, QTableWidgetItem(item_name))
                
                # Variant
                table.setItem(current_row, 1, QTableWidgetItem(variant_key))
                
                # Price (с форматированием)
                price_item = QTableWidgetItem(f"{price:,}")
                price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(current_row, 2, price_item)
                
                # Time
                table.setItem(current_row, 3, QTableWidgetItem(updated))
                
                current_row += 1
        
        table.itemSelectionChanged.connect(self.update_delete_button_state)
        layout.addWidget(table)
        return widget

    def on_tab_changed(self):
        """При смене вкладки обновляем кнопку и фильтр"""
        self.filter_table(self.search_input.text())
        self.update_delete_button_state()

    def get_current_table(self) -> QTableWidget:
        """Получить таблицу из текущей вкладки"""
        current_widget = self.city_tabs.currentWidget()
        if not current_widget:
            return None
        # Ищем QTableWidget внутри widget (он там один)
        return current_widget.findChild(QTableWidget)

    def filter_table(self, text):
        """Фильтрация таблицы по тексту"""
        table = self.get_current_table()
        if not table:
            return
            
        text = text.lower()
        for i in range(table.rowCount()):
            item_name = table.item(i, 0).text().lower()
            if text in item_name:
                table.setRowHidden(i, False)
            else:
                table.setRowHidden(i, True)

    def update_delete_button_state(self):
        """Активация кнопки удаления при выборе строки"""
        table = self.get_current_table()
        if not table:
            self.delete_btn.setEnabled(False)
            return
            
        self.delete_btn.setEnabled(len(table.selectedItems()) > 0)

    def delete_selected_record(self):
        """Удаление выбранной записи"""
        table = self.get_current_table()
        if not table:
            return
            
        selected_rows = table.selectionModel().selectedRows()
        if not selected_rows:
            return
            
        row_idx = selected_rows[0].row()
        
        item_name = table.item(row_idx, 0).text()
        variant = table.item(row_idx, 1).text()
        city = self.city_tabs.tabText(self.city_tabs.currentIndex())
        
        confirm = QMessageBox.question(
            self, 
            "Удаление записи", 
            f"Вы уверены, что хотите удалить запись:\n\n{item_name} ({variant}) из {city}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            self.storage.delete_price(city, item_name, variant)
            self.refresh_data() # Перезагружаем UI
            
    def clean_old_records(self):
        """Удаление записей старше N часов"""
        hours, ok = QInputDialog.getInt(
            self, 
            "Очистка старых цен", 
            "Удалить цены старше (часов):", 
            value=3, 
            min=1, 
            max=168
        )
        
        if ok:
            count = self.storage.remove_older_than(hours)
            if count > 0:
                QMessageBox.information(self, "Очистка завершена", f"Удалено устаревших записей: {count}")
                self.refresh_data()
            else:
                QMessageBox.information(self, "Очистка", f"Нет записей старше {hours} ч.")

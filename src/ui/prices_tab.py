"""
Вкладка просмотра цен по городам
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QTableWidget, 
    QTableWidgetItem, QHeaderView, QLabel, QPushButton, QHBoxLayout,
    QLineEdit, QMessageBox, QInputDialog,QGroupBox
)
from PyQt6.QtCore import Qt, QTimer

from ..utils.price_storage import get_price_storage
from ..utils.localization import get_text
from .styles import MAIN_STYLE


class PricesTab(QWidget):
    def __init__(self):
        super().__init__()
        self.storage = get_price_storage()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # === Header ===
        header = QHBoxLayout()
        title = QLabel(get_text("prices_header", "💰 База цен"))
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)
        
        # === Controls Group ===
        ctrl_group = QGroupBox(get_text("prices_controls_group", "Управление базой данных"))
        controls_layout = QHBoxLayout(ctrl_group)
        controls_layout.setSpacing(15)
        
        # Поиск
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(get_text("prices_search_placeholder", "🔍 Поиск предмета..."))
        self.search_input.setMinimumWidth(250)
        self.search_input.textChanged.connect(self.filter_table)
        controls_layout.addWidget(self.search_input)
        
        controls_layout.addStretch()
        
        refresh_btn = QPushButton(get_text("prices_btn_refresh", "🔄 ОБНОВИТЬ"))
        refresh_btn.setObjectName("primary")
        refresh_btn.setMinimumHeight(35)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh_data)
        controls_layout.addWidget(refresh_btn)
        
        self.delete_btn = QPushButton(get_text("prices_btn_delete", "🗑️ УДАЛИТЬ ЗАПИСЬ"))
        self.delete_btn.setObjectName("danger")
        self.delete_btn.setMinimumHeight(35)
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.delete_selected_record)
        controls_layout.addWidget(self.delete_btn)
        
        clean_old_btn = QPushButton(get_text("prices_btn_clean", "🧹 ОЧИСТИТЬ СТАРЫЕ"))
        clean_old_btn.setObjectName("danger")
        clean_old_btn.setMinimumHeight(35)
        clean_old_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clean_old_btn.setToolTip(get_text("prices_btn_clean_tip", "Удалить цены, которым больше X часов"))
        clean_old_btn.clicked.connect(self.clean_old_records)
        controls_layout.addWidget(clean_old_btn)
        
        layout.addWidget(ctrl_group)
        
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
            self.city_tabs.addTab(QLabel(get_text("prices_empty_msg", "Нет данных. Запустите бота для сканирования.")), get_text("prices_empty_tab", "Пусто"))
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
        table.setHorizontalHeaderLabels([
            get_text("prices_col_item", "Предмет"), 
            get_text("prices_col_variant", "Вариант"), 
            get_text("prices_col_price", "Цена"), 
            get_text("prices_col_updated", "Обновлено")
        ])
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        
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
            get_text("finance_delete_confirm_title", "Удаление записи"), 
            get_text("prices_delete_confirm_msg", "Вы уверены, что хотите удалить запись:\n\n{item} ({variant}) из {city}?").format(item=item_name, variant=variant, city=city),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            self.storage.delete_price(city, item_name, variant)
            self.refresh_data() # Перезагружаем UI
            
    def clean_old_records(self):
        """Удаление записей старше N часов"""
        dialog = QInputDialog(self)
        dialog.setWindowTitle(get_text("prices_clean_dialog_title", "Очистка старых цен"))
        dialog.setLabelText(get_text("prices_clean_dialog_label", "Удалить цены старше (часов):"))
        dialog.setIntValue(3)
        dialog.setIntRange(1, 168)
        
        if dialog.exec():
            hours = dialog.intValue()
            count = self.storage.remove_older_than(hours)
            
            # Создаем кастомный QMessageBox с темной темой
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Information)
            
            if count > 0:
                msg.setWindowTitle(get_text("finance_clean_done_title", "Очистка завершена"))
                msg.setText(get_text("prices_clean_done_msg", "Удалено устаревших записей: {count}").format(count=count))
                self.refresh_data()
            else:
                msg.setWindowTitle(get_text("finance_clean", "Очистка"))
                msg.setText(get_text("prices_clean_none_msg", "Нет записей старше {hours} ч.").format(hours=hours))
            
            msg.exec()

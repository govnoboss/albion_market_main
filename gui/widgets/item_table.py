"""
Albion Market Bot v3.0 - Item Table Widget

Таблица предметов с поиском и фильтрацией.
"""

from typing import Optional, List, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QTableView, QLabel, QPushButton, QHeaderView,
    QAbstractItemView, QCheckBox
)
from PyQt6.QtCore import Qt, QSortFilterProxyModel, QAbstractTableModel, QModelIndex
from PyQt6.QtGui import QColor

import pandas as pd

from core.data_manager import get_data_manager


class ItemsTableModel(QAbstractTableModel):
    """Модель данных для таблицы предметов."""
    
    COLUMNS = ['name', 'value', 'store', 'profit', 'present', 'weightforitem']
    COLUMN_HEADERS = {
        'name': 'Название',
        'value': 'Цена продажи',
        'store': 'Количество',
        'profit': 'Прибыль',
        'present': 'Присутствие',
        'weightforitem': 'Вес'
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: pd.DataFrame = pd.DataFrame()
        self.load_data()
    
    def load_data(self, tier6_only: bool = False):
        """Загрузка данных из файла."""
        try:
            manager = get_data_manager()
            self._data = manager.load_items(tier6_only=tier6_only)
            
            # Оставляем только нужные колонки
            available_cols = [c for c in self.COLUMNS if c in self._data.columns]
            self._data = self._data[available_cols]
            
        except Exception as e:
            self._data = pd.DataFrame(columns=self.COLUMNS)
            print(f"Error loading items: {e}")
        
        self.layoutChanged.emit()
    
    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._data)
    
    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._data.columns)
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        
        row = index.row()
        col = index.column()
        col_name = self._data.columns[col]
        value = self._data.iloc[row, col]
        
        if role == Qt.ItemDataRole.DisplayRole:
            if col_name in ['value', 'profit']:
                try:
                    return f"{int(value):,}"
                except (ValueError, TypeError):
                    return str(value)
            elif col_name == 'present':
                try:
                    return f"{float(value):.1%}"
                except (ValueError, TypeError):
                    return str(value)
            elif col_name == 'weightforitem':
                try:
                    return f"{float(value):.2f} кг"
                except (ValueError, TypeError):
                    return str(value)
            return str(value)
        
        elif role == Qt.ItemDataRole.BackgroundRole:
            # Цветовая индикация по прибыльности
            if 'profit' in self._data.columns:
                try:
                    profit = float(self._data.iloc[row]['profit'])
                    if profit > 50000:
                        return QColor(166, 227, 161, 50)  # Зелёный
                    elif profit > 20000:
                        return QColor(250, 179, 135, 50)  # Оранжевый
                    elif profit < 0:
                        return QColor(243, 139, 168, 50)  # Красный
                except (ValueError, TypeError):
                    pass
            return None
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col_name in ['value', 'store', 'profit', 'present', 'weightforitem']:
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        
        return None
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            col_name = self._data.columns[section]
            return self.COLUMN_HEADERS.get(col_name, col_name)
        return None
    
    def get_item_at_row(self, row: int) -> Optional[pd.Series]:
        """Получение данных предмета по номеру строки."""
        if 0 <= row < len(self._data):
            return self._data.iloc[row]
        return None


class ItemTableWidget(QWidget):
    """Виджет таблицы предметов с поиском."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Панель поиска
        search_layout = QHBoxLayout()
        
        search_label = QLabel("🔍")
        search_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по названию...")
        self.search_input.textChanged.connect(self._on_search)
        self.search_input.setClearButtonEnabled(True)
        search_layout.addWidget(self.search_input)
        
        self.tier6_checkbox = QCheckBox("Только 6 тир")
        self.tier6_checkbox.stateChanged.connect(self._on_tier6_changed)
        search_layout.addWidget(self.tier6_checkbox)
        
        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.clicked.connect(self._refresh_data)
        search_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(search_layout)
        
        # Таблица
        self.model = ItemsTableModel()
        
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(0)  # Фильтр по имени
        
        self.table = QTableView()
        self.table.setModel(self.proxy_model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(3, Qt.SortOrder.DescendingOrder)  # По прибыли
        
        # Настройка заголовков
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, self.model.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.table)
        
        # Статистика
        self.stats_label = QLabel()
        self._update_stats()
        layout.addWidget(self.stats_label)
    
    def _on_search(self, text: str):
        """Обработка поискового запроса."""
        self.proxy_model.setFilterWildcard(f"*{text}*")
        self._update_stats()
    
    def _on_tier6_changed(self, state: int):
        """Фильтр по 6 тиру."""
        self.model.load_data(tier6_only=state == Qt.CheckState.Checked.value)
        self._update_stats()
    
    def _refresh_data(self):
        """Обновление данных."""
        self.model.load_data(tier6_only=self.tier6_checkbox.isChecked())
        self._update_stats()
    
    def _update_stats(self):
        """Обновление статистики."""
        total = self.model.rowCount()
        visible = self.proxy_model.rowCount()
        self.stats_label.setText(f"Показано: {visible} из {total} предметов")
    
    def get_selected_item(self) -> Optional[pd.Series]:
        """Получение выбранного предмета."""
        indexes = self.table.selectionModel().selectedRows()
        if indexes:
            source_row = self.proxy_model.mapToSource(indexes[0]).row()
            return self.model.get_item_at_row(source_row)
        return None

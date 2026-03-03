from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget, QHBoxLayout
from PyQt6.QtCore import Qt
from ...utils.localization import get_text

class SummaryBox(QFrame):
    """Блок сводки со стилизованными строками элементов"""
    def __init__(self, title, items, color="#f59e0b", parent=None):
        super().__init__(parent)
        self.setObjectName("summaryBox")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header Container
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 20, 20, 10)
        
        title_lbl = QLabel(title)
        title_lbl.setObjectName("summaryTitle")
        header_layout.addWidget(title_lbl)
        layout.addWidget(header_widget)
        
        # Content Container
        self.content_widget = QWidget()
        self.layout_content = QVBoxLayout(self.content_widget)
        self.layout_content.setContentsMargins(20, 0, 20, 20)
        self.layout_content.setSpacing(0) # Spacing handled by row margins
        
        layout.addWidget(self.content_widget)
        
        self.update_items(items)
            
    def update_items(self, items):
        """Динамическое обновление списка элементов.
        
        items: список dict {name, qty, profit} или строк (для фолбэка).
        """
        # Очистка
        while self.layout_content.count():
            child = self.layout_content.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        qty_label = get_text("home_hot_item_qty_label", "Количество")
        qty_suffix = get_text("home_hot_item_qty", "шт")
        
        # Наполнение
        for entry in items:
            # Поддержка структурированных данных (dict) и простых строк
            if isinstance(entry, dict):
                name = entry.get("name", "")
                qty = str(entry.get("qty", ""))
                profit_part = entry.get("profit", "")
            else:
                name, qty, profit_part = str(entry), "", ""

            row = QFrame()
            row.setObjectName("hotItemRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 10, 12, 10)
            
            info_v_layout = QVBoxLayout()
            info_v_layout.setSpacing(2)
            
            name_lbl = QLabel(name)
            name_lbl.setObjectName("hotItemName")
            info_v_layout.addWidget(name_lbl)
            
            if qty:
                stats_lbl = QLabel(f"{qty_label}: {qty} {qty_suffix}")
                stats_lbl.setObjectName("hotItemStats")
                info_v_layout.addWidget(stats_lbl)
            
            row_layout.addLayout(info_v_layout)
            row_layout.addStretch()
            
            if profit_part:
                profit_lbl = QLabel(profit_part)
                profit_lbl.setObjectName("hotItemProfit")
                row_layout.addWidget(profit_lbl)
            
            self.layout_content.addWidget(row)
        
        # Add stretch at the end
        self.layout_content.addStretch()

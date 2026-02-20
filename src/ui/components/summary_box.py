from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

class SummaryBox(QFrame):
    """Блок сводки со статус-линией слева"""
    def __init__(self, title, items, color="#f59e0b", parent=None):
        super().__init__(parent)
        self.setObjectName("summaryBox")
        self.setStyleSheet(f"border-top: 2px solid {color};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(5)
        
        title_lbl = QLabel(title)
        title_lbl.setObjectName("summaryTitle")
        layout.addWidget(title_lbl)
        
        for text in items:
            item_lbl = QLabel(text)
            item_lbl.setStyleSheet("font-size: 11px; color: #94a3b8;")
            item_lbl.setWordWrap(True)
            layout.addWidget(item_lbl)

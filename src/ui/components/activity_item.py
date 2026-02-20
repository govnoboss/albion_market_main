from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt

class ActivityItem(QFrame):
    """Элемент ленты активности (Market Pulse)"""
    def __init__(self, time, text, dot_color="#10b981", parent=None):
        super().__init__(parent)
        self.setObjectName("activityItem")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(12)
        
        # Dot
        dot = QFrame()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background-color: {dot_color}; border-radius: 4px;")
        layout.addWidget(dot)
        
        # Text Layout
        content = QVBoxLayout()
        content.setSpacing(2)
        
        self.lbl_text = QLabel(text)
        self.lbl_text.setObjectName("activityText")
        self.lbl_text.setWordWrap(True)
        
        self.lbl_time = QLabel(time)
        self.lbl_time.setObjectName("activityTime")
        
        content.addWidget(self.lbl_text)
        content.addWidget(self.lbl_time)
        
        layout.addLayout(content)
        layout.addStretch()

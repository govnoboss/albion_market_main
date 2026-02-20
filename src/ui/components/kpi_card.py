from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt

class KPICard(QFrame):
    """Карточка с ключевым показателем (KPI)"""
    def __init__(self, title, value, subtext="", icon="📈", parent=None):
        super().__init__(parent)
        self.setObjectName("kpiCard")
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Icon Section
        icon_container = QFrame()
        icon_container.setObjectName("iconContainer")
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_icon = QLabel(icon)
        self.lbl_icon.setObjectName("kpiIcon")
        icon_layout.addWidget(self.lbl_icon)
        main_layout.addWidget(icon_container)
        
        # Text Section
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("kpiTitle")
        
        self.lbl_value = QLabel(value)
        self.lbl_value.setObjectName("kpiValue")
        
        text_layout.addWidget(self.lbl_title)
        text_layout.addWidget(self.lbl_value)
        
        if subtext:
            self.lbl_subtext = QLabel(subtext)
            self.lbl_subtext.setObjectName("kpiSubtext")
            text_layout.addWidget(self.lbl_subtext)
        
        main_layout.addLayout(text_layout)
        main_layout.addStretch()
            
    def update_value(self, value, subtext=None):
        self.lbl_value.setText(value)
        if subtext and hasattr(self, 'lbl_subtext'):
            self.lbl_subtext.setText(subtext)

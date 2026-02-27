from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt

class KPICard(QFrame):
    """Карточка с ключевым показателем (KPI)"""
    def __init__(self, title, value, subtext="", icon="📈", parent=None):
        super().__init__(parent)
        self.setObjectName("kpiCard")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)
        
        # Header: Icon + Title
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        icon_container = QFrame()
        icon_container.setObjectName("iconContainer")
        icon_inner_layout = QVBoxLayout(icon_container)
        icon_inner_layout.setContentsMargins(0, 0, 0, 0)
        icon_inner_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_icon = QLabel(icon)
        self.lbl_icon.setObjectName("kpiIcon")
        icon_inner_layout.addWidget(self.lbl_icon)
        header_layout.addWidget(icon_container)
        
        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("kpiTitle")
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # Value Section
        self.lbl_value = QLabel(value)
        self.lbl_value.setObjectName("kpiValue")
        self.lbl_value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        main_layout.addWidget(self.lbl_value)
        
        # Subtext Section
        if subtext:
            self.lbl_subtext = QLabel(subtext)
            self.lbl_subtext.setObjectName("kpiSubtext")
            main_layout.addWidget(self.lbl_subtext)
        else:
            # Placeholder for consistent layout
            self.lbl_subtext = QLabel("")
            self.lbl_subtext.setObjectName("kpiSubtext")
            main_layout.addWidget(self.lbl_subtext)
            
        main_layout.addStretch()
            
    def update_value(self, value, subtext=None):
        self.lbl_value.setText(value)
        if subtext and hasattr(self, 'lbl_subtext'):
            self.lbl_subtext.setText(subtext)

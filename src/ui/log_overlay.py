"""
Semi-transparent, draggable, and resizable log overlay.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QTextEdit, QSizeGrip
)
from PyQt6.QtCore import Qt, QPoint, QSize
from PyQt6.QtGui import QColor, QFont

class LogOverlay(QWidget):
    """
    Overlay window to display logs in real-time.
    Features:
    - Semi-transparent background
    - Draggable
    - Resizable
    - Always on top
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_window()
        self._setup_ui()
        
        # State for dragging
        self._is_dragging = False
        self._drag_pos = QPoint()

    def _setup_window(self):
        """Window configuration"""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(400, 200) # Default size
        self.load_settings()
        
    def _setup_ui(self):
        """UI initialization"""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Main Frame (with semi-transparent background)
        self.frame = QFrame()
        self.frame.setStyleSheet("""
            QFrame {
                background-color: rgba(13, 17, 23, 180); 
                border: 1px solid #30363d;
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.frame)
        
        # Frame Layout
        frame_layout = QVBoxLayout(self.frame)
        frame_layout.setContentsMargins(5, 5, 5, 5)
        frame_layout.setSpacing(5)
        
        # --- Header (Draggable Area) ---
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(5, 0, 5, 0)
        
        self.title_label = QLabel("📋 Logs")
        self.title_label.setStyleSheet("""
            color: #8b949e; 
            font-weight: bold; 
            font-size: 12px;
            background: transparent;
            border: none;
        """)
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        # Close Button
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setToolTip("Hide Overlay")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8b949e;
                border: none;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover { color: #f0f6fc; }
        """)
        self.close_btn.clicked.connect(self.hide)
        header_layout.addWidget(self.close_btn)
        
        frame_layout.addLayout(header_layout)
        
        # --- Log Viewer ---
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                border: none;
                color: #f0f6fc;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }
        """)
        self.log_viewer.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        frame_layout.addWidget(self.log_viewer)
        
        # --- Footer (Resize Grip) ---
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addStretch()
        
        # Size Grip
        self.size_grip = QSizeGrip(self.frame)
        self.size_grip.setStyleSheet("""
            QSizeGrip {
                background: transparent;
                width: 15px;
                height: 15px;
            }
        """)
        footer_layout.addWidget(self.size_grip, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        
        frame_layout.addLayout(footer_layout)

    def add_log(self, message: str, level: str = "info"):
        """Add a log message"""
        # Simple colorizing based on level
        color = "#f0f6fc" # Default info
        if level == "error": color = "#f85149"
        elif level == "warning": color = "#d29922"
        elif level == "debug": color = "#8b949e"
        elif level == "success": color = "#3fb950"

        # Strip existing HTML tags if needed, or wrap in span
        # Note: Logger often sends raw text or simple HTML
        
        html = f'<span style="color: {color};">{message}</span>'
        self.log_viewer.append(html)
        
        # Auto-scroll
        scrollbar = self.log_viewer.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_logs(self):
        self.log_viewer.clear()

    # --- Dragging Logic ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if click is in the top header area (approx height 30)
            if event.position().y() < 30:
                self._is_dragging = True
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        if self._is_dragging:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._is_dragging = False
    # --- Persistence ---
    def save_settings(self):
        """Save window geometry"""
        from PyQt6.QtCore import QSettings
        settings = QSettings("GBot", "LogOverlay")
        settings.setValue("geometry", self.saveGeometry())

    def load_settings(self):
        """Load window geometry"""
        from PyQt6.QtCore import QSettings
        settings = QSettings("GBot", "LogOverlay")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)
        
    def hideEvent(self, event):
        self.save_settings()
        super().hideEvent(event)

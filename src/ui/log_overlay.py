"""
Semi-transparent, draggable, and resizable log overlay.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QTextEdit
)
from PyQt6.QtCore import Qt, QPoint, QSize, QRect
from PyQt6.QtGui import QColor, QFont, QCursor
from .styles import LOG_OVERLAY_STYLE

# Resize edge flags
_EDGE_NONE = 0
_EDGE_LEFT = 1
_EDGE_RIGHT = 2
_EDGE_TOP = 4
_EDGE_BOTTOM = 8
_EDGE_MARGIN = 8  # px threshold for edge detection

class LogOverlay(QWidget):
    """
    Overlay window to display logs in real-time.
    Features:
    - Semi-transparent background
    - Draggable
    - Resizable from any edge/corner
    - Always on top
    """
    
    MIN_WIDTH = 200
    MIN_HEIGHT = 100
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_window()
        self._setup_ui()
        
        # State for dragging
        self._is_dragging = False
        self._drag_pos = QPoint()
        
        # State for resizing
        self._resize_edge = _EDGE_NONE
        self._resize_start_pos = QPoint()
        self._resize_start_geo = QRect()
        
        self.setMouseTracking(True)

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
        self.frame.setStyleSheet(LOG_OVERLAY_STYLE["frame"])
        layout.addWidget(self.frame)
        
        # Frame Layout
        frame_layout = QVBoxLayout(self.frame)
        frame_layout.setContentsMargins(5, 5, 5, 5)
        frame_layout.setSpacing(5)
        
        # --- Header (Draggable Area) ---
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(5, 0, 5, 0)
        
        self.title_label = QLabel("📋 Logs")
        self.title_label.setStyleSheet(LOG_OVERLAY_STYLE["title"])
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        # Close Button
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setToolTip("Hide Overlay")
        self.close_btn.setStyleSheet(LOG_OVERLAY_STYLE["close_btn"])
        self.close_btn.clicked.connect(self.hide)
        header_layout.addWidget(self.close_btn)
        
        frame_layout.addLayout(header_layout)
        
        # --- Log Viewer ---
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setStyleSheet(LOG_OVERLAY_STYLE["viewer"])
        self.log_viewer.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        frame_layout.addWidget(self.log_viewer)

    def add_log(self, message: str, level: str = "info"):
        """Add a log message"""
        # Simple colorizing based on level
        color = "#f0f6fc" # Default info
        if level == "error": color = "#f85149"
        elif level == "warning": color = "#d29922"
        elif level == "debug": color = "#8b949e"
        elif level == "success": color = "#3fb950"

        html = f'<span style="color: {color};">{message}</span>'
        self.log_viewer.append(html)
        
        # Auto-scroll
        scrollbar = self.log_viewer.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_logs(self):
        self.log_viewer.clear()

    # --- Edge detection ---
    def _detect_edge(self, pos) -> int:
        """Detect which edge(s) the mouse is near"""
        edge = _EDGE_NONE
        rect = self.rect()
        
        if pos.x() <= _EDGE_MARGIN:
            edge |= _EDGE_LEFT
        elif pos.x() >= rect.width() - _EDGE_MARGIN:
            edge |= _EDGE_RIGHT
            
        if pos.y() <= _EDGE_MARGIN:
            edge |= _EDGE_TOP
        elif pos.y() >= rect.height() - _EDGE_MARGIN:
            edge |= _EDGE_BOTTOM
            
        return edge
    
    def _update_cursor(self, edge):
        """Set cursor shape based on detected edge"""
        if edge == _EDGE_LEFT or edge == _EDGE_RIGHT:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif edge == _EDGE_TOP or edge == _EDGE_BOTTOM:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif edge == (_EDGE_TOP | _EDGE_LEFT) or edge == (_EDGE_BOTTOM | _EDGE_RIGHT):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif edge == (_EDGE_TOP | _EDGE_RIGHT) or edge == (_EDGE_BOTTOM | _EDGE_LEFT):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    # --- Mouse events ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            edge = self._detect_edge(pos)
            
            if edge != _EDGE_NONE:
                # Start resizing
                self._resize_edge = edge
                self._resize_start_pos = event.globalPosition().toPoint()
                self._resize_start_geo = self.geometry()
                event.accept()
            elif pos.y() < 30:
                # Drag from header
                self._is_dragging = True
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        if self._resize_edge != _EDGE_NONE:
            # Resizing
            delta = event.globalPosition().toPoint() - self._resize_start_pos
            geo = QRect(self._resize_start_geo)
            
            if self._resize_edge & _EDGE_LEFT:
                new_left = geo.left() + delta.x()
                new_width = geo.width() - delta.x()
                if new_width >= self.MIN_WIDTH:
                    geo.setLeft(new_left)
                    
            if self._resize_edge & _EDGE_RIGHT:
                new_width = geo.width() + delta.x()
                if new_width >= self.MIN_WIDTH:
                    geo.setWidth(new_width)
                    
            if self._resize_edge & _EDGE_TOP:
                new_top = geo.top() + delta.y()
                new_height = geo.height() - delta.y()
                if new_height >= self.MIN_HEIGHT:
                    geo.setTop(new_top)
                    
            if self._resize_edge & _EDGE_BOTTOM:
                new_height = geo.height() + delta.y()
                if new_height >= self.MIN_HEIGHT:
                    geo.setHeight(new_height)
            
            self.setGeometry(geo)
            event.accept()
            
        elif self._is_dragging:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            # Update cursor shape on hover
            edge = self._detect_edge(event.position().toPoint())
            self._update_cursor(edge)

    def mouseReleaseEvent(self, event):
        self._is_dragging = False
        self._resize_edge = _EDGE_NONE

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


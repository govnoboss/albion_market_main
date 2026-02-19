from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QPen

class DimOverlay(QWidget):
    """
    Transparent overlay for "Cinema Scope" dimming effect.
    This window is transparent for mouse events (clicks pass through),
    but paints the semi-transparent black borders.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput # For clicks to pass through
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        
        self.dim_enabled = True
        self.dim_right_enabled = True
        
    def set_dim_state(self, enabled: bool, right_enabled: bool):
        self.dim_enabled = enabled
        self.dim_right_enabled = right_enabled
        self.update()

    def paintEvent(self, event):
        if not self.dim_enabled:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # Dimming parameters (25% width, 15% height)
        side_width = int(w * 0.25)
        top_height = int(h * 0.15)
        
        # Color
        dim_color = QColor(0, 0, 0, 180)
        
        painter.setBrush(dim_color)
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Top
        painter.drawRect(0, 0, w, top_height)
        # Bottom
        painter.drawRect(0, h - top_height, w, top_height)
        # Left
        painter.drawRect(0, top_height, side_width, h - 2 * top_height)
        
        # Right
        if self.dim_right_enabled:
            painter.drawRect(w - side_width, top_height, side_width, h - 2 * top_height)
            
        # Border lines (Decorative)
        pen = QPen(QColor("#58a6ff"))
        pen.setWidth(2)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # Top Line
        painter.drawLine(side_width, top_height, w - side_width, top_height)
        # Bottom Line
        painter.drawLine(side_width, h - top_height, w - side_width, h - top_height)
        # Left Line
        painter.drawLine(side_width, top_height, side_width, h - top_height)
        # Right Line
        if self.dim_right_enabled:
            painter.drawLine(w - side_width, top_height, w - side_width, h - top_height)

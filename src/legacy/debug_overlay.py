from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QFont

class DebugOverlay(QWidget):
    """
    Оверлей для визуального дебага поверх игры.
    Пропускает клики (TransparentForMouseEvents).
    """
    def __init__(self):
        super().__init__()
        # Fullscreen, Frameless, Top, Click-Through
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput # Key feature!
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        
        # State
        self.status_text = ""
        self.shapes = [] # list of (type, args, color)
        
        # Auto-clear shapes after some time? Or manual?
        # Manual is better for "current state".
        
    def set_status(self, text: str):
        self.status_text = text
        self.update()
        
    def add_circle(self, x, y, radius, color="red"):
        self.shapes.append(("circle", (x, y, radius), color))
        self.update()
        
    def add_line(self, x1, y1, x2, y2, color="yellow"):
        self.shapes.append(("line", (x1, y1, x2, y2), color))
        self.update()
        
    def clear_shapes(self):
        self.shapes = []
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Draw Shapes
        for shape_type, args, color_name in self.shapes:
            color = QColor(color_name)
            pen = QPen(color, 3)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            if shape_type == "circle":
                x, y, r = args
                painter.drawEllipse(x - r, y - r, r * 2, r * 2)
            elif shape_type == "line":
                x1, y1, x2, y2 = args
                painter.drawLine(x1, y1, x2, y2)
                
        # 2. Draw Status Text (Top Center)
        if self.status_text:
            text_rect = self.rect()
            text_rect.setHeight(100) # Top area
            
            # Background for text
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 150))
            painter.drawRect(0, 0, self.width(), 60)
            
            # Text
            painter.setPen(QColor("white"))
            font = QFont("Arial", 20, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.status_text)

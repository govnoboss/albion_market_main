from PyQt6.QtWidgets import QWidget, QSizeGrip, QVBoxLayout
from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QMouseEvent

class ResizablePanel(QWidget):
    """
    A container that can be moved (dragged) and resized.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.SubWindow) # Allows it to be a child widget but movable? 
        # Actually for a panel inside an overlay, we just want standard widget behavior but with mouse handling.
        # But if it's inside a full screen transparent overlay, it needs to handle events.
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # State
        self.m_mouse_down = False
        self.m_old_pos = None
        
        # Layout for content
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Resize Grip (Bottom Right)
        self.grip_size = 20
        self.grip = QSizeGrip(self)
        self.grip.resize(self.grip_size, self.grip_size)
        
    def addWidget(self, widget):
        self.layout.addWidget(widget)

    def resizeEvent(self, event):
        rect = self.rect()
        self.grip.move(rect.right() - self.grip_size, rect.bottom() - self.grip_size)
        super().resizeEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.m_mouse_down = True
            self.m_old_pos = event.globalPosition().toPoint()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.m_mouse_down = False
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.m_mouse_down:
            delta = event.globalPosition().toPoint() - self.m_old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.m_old_pos = event.globalPosition().toPoint()
            event.accept()
        else:
            super().mouseMoveEvent(event)

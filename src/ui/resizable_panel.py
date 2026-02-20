from PyQt6.QtWidgets import QWidget, QSizeGrip, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt, QPoint, QRect, QEvent
from PyQt6.QtGui import QMouseEvent, QCursor

class ResizablePanel(QWidget):
    """
    A container that can be moved (dragged) and resized by edges.
    """
    MARGIN = 15 # Increased margin for easier detection
    MIN_WIDTH = 200
    MIN_HEIGHT = 150

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True) # Important for cursor switching
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # State
        self.m_is_resizing = False
        self.m_is_moving = False
        self.m_old_pos = None
        self.m_resize_edge = Qt.Edge(0)
        
        # Layout for content
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # No more manual QSizeGrip needed as we implement edge resizing
        
    def addWidget(self, widget):
        self.layout.addWidget(widget)
        # To handle mouse movement/cursor over children, we need tracking and event filter
        widget.setMouseTracking(True)
        widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseMove:
            # When hovering over children, update cursor based on position relative to THIS panel
            pos = self.mapFromGlobal(QCursor.pos())
            if not (Qt.MouseButton.LeftButton & QApplication.mouseButtons()):
                edge = self._get_resize_edge(pos)
                self._update_cursor(edge)
        return super().eventFilter(obj, event)

    def _get_resize_edge(self, pos: QPoint):
        """Determine which edge/corner is under the mouse."""
        edge = Qt.Edge(0)
        if pos.x() <= self.MARGIN:
            edge |= Qt.Edge.LeftEdge
        elif pos.x() >= self.width() - self.MARGIN:
            edge |= Qt.Edge.RightEdge
            
        if pos.y() <= self.MARGIN:
            edge |= Qt.Edge.TopEdge
        elif pos.y() >= self.height() - self.MARGIN:
            edge |= Qt.Edge.BottomEdge
            
        return edge

    def _update_cursor(self, edge: Qt.Edge):
        if edge == (Qt.Edge.LeftEdge | Qt.Edge.TopEdge) or edge == (Qt.Edge.RightEdge | Qt.Edge.BottomEdge):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif edge == (Qt.Edge.RightEdge | Qt.Edge.TopEdge) or edge == (Qt.Edge.LeftEdge | Qt.Edge.BottomEdge):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif edge & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif edge & (Qt.Edge.TopEdge | Qt.Edge.BottomEdge):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._get_resize_edge(event.position().toPoint())
            if edge:
                self.m_is_resizing = True
                self.m_resize_edge = edge
            else:
                self.m_is_moving = True
            
            self.m_old_pos = event.globalPosition().toPoint()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.m_is_resizing = False
        self.m_is_moving = False
        self.m_resize_edge = Qt.Edge(0)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position().toPoint()
        
        # Cursor update for hover
        if not event.buttons() & Qt.MouseButton.LeftButton:
            edge = self._get_resize_edge(pos)
            self._update_cursor(edge)
            super().mouseMoveEvent(event)
            return

        # Moving or Resizing
        if self.m_is_moving:
            delta = event.globalPosition().toPoint() - self.m_old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.m_old_pos = event.globalPosition().toPoint()
            event.accept()
        elif self.m_is_resizing:
            delta = event.globalPosition().toPoint() - self.m_old_pos
            rect = self.geometry()
            
            if self.m_resize_edge & Qt.Edge.LeftEdge:
                new_width = rect.width() - delta.x()
                if new_width >= self.MIN_WIDTH:
                    rect.setLeft(rect.left() + delta.x())
            elif self.m_resize_edge & Qt.Edge.RightEdge:
                new_width = rect.width() + delta.x()
                if new_width >= self.MIN_WIDTH:
                    rect.setRight(rect.right() + delta.x())
                    
            if self.m_resize_edge & Qt.Edge.TopEdge:
                new_height = rect.height() - delta.y()
                if new_height >= self.MIN_HEIGHT:
                    rect.setTop(rect.top() + delta.y())
            elif self.m_resize_edge & Qt.Edge.BottomEdge:
                new_height = rect.height() + delta.y()
                if new_height >= self.MIN_HEIGHT:
                    rect.setBottom(rect.bottom() + delta.y())
            
            self.setGeometry(rect)
            self.m_old_pos = event.globalPosition().toPoint()
            event.accept()

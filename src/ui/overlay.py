from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRect, pyqtSignal, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QRegion

class AreaSelectionOverlay(QWidget):
    """
    Полупрозрачный оверлей для выделения области экрана.
    """
    area_selected = pyqtSignal(int, int, int, int) # x, y, w, h
    cancelled = pyqtSignal()

    def __init__(self):
        super().__init__()
        # Настройка окна: без рамки, поверх всех, прозрачный фон, на весь экран
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool 
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.grabKeyboard() # Ensure we catch ESC
        
        self.start_pos: QPoint | None = None
        self.current_pos: QPoint | None = None
        self.selection_rect: QRect | None = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        full_rect = self.rect()
        
        # Фон (затемнение)
        painter.setBrush(QColor(0, 0, 0, 80)) # Черный, 80 alpha
        painter.setPen(Qt.PenStyle.NoPen)
        
        if not self.selection_rect:
            painter.drawRect(full_rect)
        else:
            # Рисуем "дырку"
            region = QRegion(full_rect)
            region -= QRegion(self.selection_rect)
            
            # Рисуем затемнение только в region (вокруг выделения)
            painter.setClipRegion(region)
            painter.drawRect(full_rect)
            painter.setClipping(False) # Сброс
            
            # 2. Рисуем рамку выделения
            pen = QPen(QColor(255, 69, 0), 2) # Оранжево-красный
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush) # Прозрачный центр рамки
            painter.drawRect(self.selection_rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.globalPosition().toPoint()
            self.current_pos = self.start_pos
            self.update_rect()

    def mouseMoveEvent(self, event):
        if self.start_pos:
            self.current_pos = event.globalPosition().toPoint()
            self.update_rect()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.start_pos:
            self.current_pos = event.globalPosition().toPoint()
            self.update_rect()
            
            # Финализация
            if self.selection_rect and self.selection_rect.isValid() and \
               self.selection_rect.width() > 0 and self.selection_rect.height() > 0:
                
                self.area_selected.emit(
                    self.selection_rect.x(),
                    self.selection_rect.y(),
                    self.selection_rect.width(),
                    self.selection_rect.height()
                )
            else:
                self.cancelled.emit()
            
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self.close()

    def update_rect(self):
        if not self.start_pos or not self.current_pos:
            return
            
        x = min(self.start_pos.x(), self.current_pos.x())
        y = min(self.start_pos.y(), self.current_pos.y())
        w = abs(self.current_pos.x() - self.start_pos.x())
        h = abs(self.current_pos.y() - self.start_pos.y())
        
        self.selection_rect = QRect(x, y, w, h)

# Для QRegion нужен импорт
from PyQt6.QtGui import QRegion

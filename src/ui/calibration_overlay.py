from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush

class CalibrationOverlay(QWidget):
    """
    Прозрачный оверлей для отображения точек калибровки.
    Появляется при настройке, исчезает автоматически.
    """
    def __init__(self):
        super().__init__()
        # Настройка окна: без рамки, поверх всех, прозрачный фон, клики проходят сквозь
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        
        self.points: list[tuple[int, int]] = []
        
        # Таймер для автоскрытия
        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)
        self.HIDE_DELAY = 3000  # 3 секунды
        
    def show_points(self, points: list[tuple[int, int]]):
        """
        Показать точки на экране.
        
        Args:
            points: Список координат [(x, y), ...]
        """
        self.points = points
        self.show()
        self.update() # Перерисовка
        
        # Сброс таймера
        self.hide_timer.stop()
        self.hide_timer.start(self.HIDE_DELAY)
        
    def paintEvent(self, event):
        if not self.points:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Настройка кисти для точек
        painter.setBrush(QBrush(QColor(255, 0, 0, 200))) # Красный, слегка прозрачный
        painter.setPen(Qt.PenStyle.NoPen)
        
        radius = 4
        for x, y in self.points:
            painter.drawEllipse(QPoint(x, y), radius, radius)
            
        # Опционально: можно нарисовать линии, чтобы видеть структуру списка
        if len(self.points) > 1:
            pen = QPen(QColor(255, 255, 0, 150), 1)
            painter.setPen(pen)
            for i in range(len(self.points) - 1):
                p1 = QPoint(*self.points[i])
                p2 = QPoint(*self.points[i+1])
                painter.drawLine(p1, p2)

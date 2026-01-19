"""
Albion Market Bot v3.0 - Region Capture Overlay

Прозрачный overlay для визуального захвата областей экрана.
"""

import sys
from typing import Optional, Tuple, Callable

from PyQt6.QtWidgets import QWidget, QApplication, QLabel
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QScreen, QGuiApplication


class RegionCaptureOverlay(QWidget):
    """
    Полноэкранный прозрачный overlay для захвата области.
    
    Использование:
        overlay = RegionCaptureOverlay()
        overlay.region_captured.connect(on_region_selected)
        overlay.start_capture()
    """
    
    # Сигнал: (left, top, width, height)
    region_captured = pyqtSignal(int, int, int, int)
    capture_cancelled = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._start_pos: Optional[QPoint] = None
        self._current_pos: Optional[QPoint] = None
        self._is_selecting = False
        
        self._setup_window()
    
    def _setup_window(self):
        """Настройка окна overlay."""
        # Полноэкранный, прозрачный, всегда поверх
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        # Захватываем весь экран
        screen = QGuiApplication.primaryScreen()
        if screen:
            geometry = screen.geometry()
            self.setGeometry(geometry)
        
        self.setCursor(Qt.CursorShape.CrossCursor)
    
    def start_capture(self):
        """Начать захват области."""
        self._start_pos = None
        self._current_pos = None
        self._is_selecting = False
        self.showFullScreen()
        self.activateWindow()
    
    def paintEvent(self, event):
        """Отрисовка overlay."""
        painter = QPainter(self)
        
        # Полупрозрачный тёмный фон
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        
        # Если выделяем область
        if self._start_pos and self._current_pos:
            rect = self._get_selection_rect()
            
            # Прозрачная область выделения
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            
            # Рамка выделения
            pen = QPen(QColor(137, 180, 250), 2)  # Голубой цвет
            painter.setPen(pen)
            painter.drawRect(rect)
            
            # Размеры
            size_text = f"{rect.width()} × {rect.height()}"
            painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            painter.setPen(QColor(255, 255, 255))
            
            # Фон для текста
            text_rect = painter.fontMetrics().boundingRect(size_text)
            text_x = rect.center().x() - text_rect.width() // 2
            text_y = rect.bottom() + 25
            
            bg_rect = QRect(text_x - 8, text_y - text_rect.height() - 4, 
                           text_rect.width() + 16, text_rect.height() + 8)
            painter.fillRect(bg_rect, QColor(30, 30, 46, 200))
            painter.drawText(text_x, text_y, size_text)
        
        # Инструкции
        painter.setFont(QFont("Segoe UI", 14))
        painter.setPen(QColor(255, 255, 255))
        
        instructions = "🖱️ Выделите область мышью  •  ESC — отмена"
        text_rect = painter.fontMetrics().boundingRect(instructions)
        x = (self.width() - text_rect.width()) // 2
        
        # Фон для инструкций
        bg_rect = QRect(x - 16, 20, text_rect.width() + 32, text_rect.height() + 16)
        painter.fillRect(bg_rect, QColor(30, 30, 46, 220))
        painter.drawText(x, 45, instructions)
    
    def mousePressEvent(self, event):
        """Начало выделения."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_pos = event.pos()
            self._current_pos = event.pos()
            self._is_selecting = True
            self.update()
    
    def mouseMoveEvent(self, event):
        """Обновление выделения."""
        if self._is_selecting:
            self._current_pos = event.pos()
            self.update()
    
    def mouseReleaseEvent(self, event):
        """Завершение выделения."""
        if event.button() == Qt.MouseButton.LeftButton and self._is_selecting:
            self._current_pos = event.pos()
            self._is_selecting = False
            
            rect = self._get_selection_rect()
            
            # Минимальный размер
            if rect.width() > 5 and rect.height() > 5:
                self.region_captured.emit(
                    rect.x(), rect.y(), 
                    rect.width(), rect.height()
                )
            
            self.close()
    
    def keyPressEvent(self, event):
        """Отмена по ESC."""
        if event.key() == Qt.Key.Key_Escape:
            self.capture_cancelled.emit()
            self.close()
    
    def _get_selection_rect(self) -> QRect:
        """Получить прямоугольник выделения."""
        if not self._start_pos or not self._current_pos:
            return QRect()
        
        x1, y1 = self._start_pos.x(), self._start_pos.y()
        x2, y2 = self._current_pos.x(), self._current_pos.y()
        
        left = min(x1, x2)
        top = min(y1, y2)
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        
        return QRect(left, top, width, height)


class PointCaptureOverlay(QWidget):
    """
    Overlay для захвата точки (одного клика).
    """
    
    point_captured = pyqtSignal(int, int)
    capture_cancelled = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._mouse_pos: Optional[QPoint] = None
        self._setup_window()
    
    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        screen = QGuiApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())
        
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)
    
    def start_capture(self):
        self.showFullScreen()
        self.activateWindow()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        
        # Полупрозрачный фон
        painter.fillRect(self.rect(), QColor(0, 0, 0, 80))
        
        # Перекрестие в позиции мыши
        if self._mouse_pos:
            pen = QPen(QColor(166, 227, 161), 2)  # Зелёный
            painter.setPen(pen)
            
            x, y = self._mouse_pos.x(), self._mouse_pos.y()
            
            # Горизонтальная линия
            painter.drawLine(0, y, self.width(), y)
            # Вертикальная линия
            painter.drawLine(x, 0, x, self.height())
            
            # Координаты
            coord_text = f"({x}, {y})"
            painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            painter.setPen(QColor(255, 255, 255))
            
            text_x = x + 15
            text_y = y - 15
            
            # Фон
            text_rect = painter.fontMetrics().boundingRect(coord_text)
            bg_rect = QRect(text_x - 4, text_y - text_rect.height(), 
                           text_rect.width() + 8, text_rect.height() + 4)
            painter.fillRect(bg_rect, QColor(30, 30, 46, 220))
            painter.drawText(text_x, text_y, coord_text)
        
        # Инструкции
        painter.setFont(QFont("Segoe UI", 14))
        painter.setPen(QColor(255, 255, 255))
        
        instructions = "🖱️ Кликните для выбора точки  •  ESC — отмена"
        text_rect = painter.fontMetrics().boundingRect(instructions)
        x = (self.width() - text_rect.width()) // 2
        
        bg_rect = QRect(x - 16, 20, text_rect.width() + 32, text_rect.height() + 16)
        painter.fillRect(bg_rect, QColor(30, 30, 46, 220))
        painter.drawText(x, 45, instructions)
    
    def mouseMoveEvent(self, event):
        self._mouse_pos = event.pos()
        self.update()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            self.point_captured.emit(pos.x(), pos.y())
            self.close()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.capture_cancelled.emit()
            self.close()


def capture_region(callback: Callable[[int, int, int, int], None]):
    """
    Быстрая функция для захвата области.
    
    Args:
        callback: Функция (left, top, width, height)
    """
    overlay = RegionCaptureOverlay()
    overlay.region_captured.connect(callback)
    overlay.start_capture()
    return overlay


def capture_point(callback: Callable[[int, int], None]):
    """
    Быстрая функция для захвата точки.
    
    Args:
        callback: Функция (x, y)
    """
    overlay = PointCaptureOverlay()
    overlay.point_captured.connect(callback)
    overlay.start_capture()
    return overlay

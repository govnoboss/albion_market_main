"""
Модуль захвата координат по клику мыши
Использует pynput для глобального прослушивания (без оверлея)
"""

from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from pynput import mouse, keyboard


class CoordinateCapture(QObject):
    """Менеджер захвата координат с глобальным прослушиванием мыши"""
    
    # Сигналы (автоматически потокобезопасны в Qt)
    coordinate_captured = pyqtSignal(str, int, int)  # key, x, y
    area_captured = pyqtSignal(str, int, int, int, int)  # key, x, y, w, h
    capture_cancelled = pyqtSignal(str)  # key
    capture_started = pyqtSignal(str, str)  # key, mode
    
    # Внутренние сигналы для межпоточного взаимодействия
    _internal_captured = pyqtSignal(str, int, int)
    _internal_area_captured = pyqtSignal(str, int, int, int, int)
    _internal_cancelled = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self._capture_mode: str = 'point'  # 'point' or 'area'
        self._start_pos: Optional[tuple[int, int]] = None
        self._overlay = None # Ссылка на виджет оверлея
        
        self._mouse_listener: Optional[mouse.Listener] = None
        self._keyboard_listener: Optional[keyboard.Listener] = None
        self._is_capturing = False
        
        # Подключаем внутренние сигналы к обработчикам
        self._internal_captured.connect(self._handle_captured, Qt.ConnectionType.QueuedConnection)
        self._internal_area_captured.connect(self._handle_area_captured, Qt.ConnectionType.QueuedConnection)
        self._internal_cancelled.connect(self._handle_cancelled, Qt.ConnectionType.QueuedConnection)
    
    @property
    def is_capturing(self) -> bool:
        return self._is_capturing
    
    def start_capture(self, key: str, display_name: str, mode: str = 'point') -> None:
        """Начать захват (point - клик, area - выделение области)"""
        if self._is_capturing:
            return
        
        self._is_capturing = True
        self._current_key = key
        self._current_name = display_name
        self._capture_mode = mode
        self._start_pos = None
        self._overlay = None
        
        # Сигнал о начале захвата
        self.capture_started.emit(key, mode)
        
        if mode == 'area':
            # Запуск визуального оверлея
            # Импорт здесь, чтобы избежать циклических зависимостей, если они возникнут
            # Но лучше вынести в начало, если не циклится. Пробуем локально для надежности.
            from ..ui.overlay import AreaSelectionOverlay
            
            self._overlay = AreaSelectionOverlay()
            self._overlay.area_selected.connect(self._handle_overlay_success)
            self._overlay.cancelled.connect(self._handle_overlay_cancelled)
            self._overlay.show()
            
        else:
            # Запуск слушателей pynput (для точки)
            self._mouse_listener = mouse.Listener(on_click=self._on_click)
            self._mouse_listener.start()
            
            self._keyboard_listener = keyboard.Listener(on_press=self._on_key_press)
            self._keyboard_listener.start()
            
    def _handle_overlay_success(self, x, y, w, h):
        """Успешный выбор области через оверлей"""
        key = self._current_key
        self._cleanup() # Закроет оверлей (он сам закрывается, но очистим ссылки)
        if key:
            self.area_captured.emit(key, x, y, w, h)

    def _handle_overlay_cancelled(self):
        """Отмена выбора области"""
        key = self._current_key
        self._cleanup()
        if key:
            self.capture_cancelled.emit(key)
    
    def _on_key_press(self, key) -> bool:
        """Обработчик нажатия клавиш (вызывается из потока pynput)"""
        try:
            if key == keyboard.Key.esc:
                current_key = self._current_key
                if current_key:
                    # Эмитим сигнал для главного потока
                    self._internal_cancelled.emit(current_key)
                return False  # Останавливаем listener
        except:
            pass
        return True
    
    def _on_click(self, x, y, button, pressed) -> bool:
        """Обработчик клика мыши (вызывается из потока pynput)"""
        if button != mouse.Button.left:
            return True

        current_key = self._current_key
        if not current_key:
            return False

        if self._capture_mode == 'point':
            # Режим точки: реагируем на нажатие (или отпускание, как удобнее, обычно нажатие быстрее)
            if pressed:
                self._internal_captured.emit(current_key, int(x), int(y))
                return False
                
        elif self._capture_mode == 'area':
            # Режим области: Drag & Drop
            if pressed:
                # Начало выделения
                self._start_pos = (int(x), int(y))
                return True # Продолжаем слушать, ждем отпускания
            else:
                # Конец выделения
                if self._start_pos:
                    start_x, start_y = self._start_pos
                    end_x, end_y = int(x), int(y)
                    
                    # Нормализация координат (на случай выделения справа-налево)
                    x_final = min(start_x, end_x)
                    y_final = min(start_y, end_y)
                    w = abs(end_x - start_x)
                    h = abs(end_y - start_y)
                    
                    self._internal_area_captured.emit(current_key, x_final, y_final, w, h)
                    return False

        return True  # Продолжаем слушать
    
    def _handle_captured(self, key: str, x: int, y: int) -> None:
        """Обработчик захвата точки"""
        self._cleanup()
        self.coordinate_captured.emit(key, x, y)

    def _handle_area_captured(self, key: str, x: int, y: int, w: int, h: int) -> None:
        """Обработчик захвата области"""
        self._cleanup()
        self.area_captured.emit(key, x, y, w, h)
    
    def _handle_cancelled(self, key: str) -> None:
        """Обработчик отмены (вызывается в главном потоке через сигнал)"""
        self._cleanup()
        self.capture_cancelled.emit(key)
    
    def cancel_capture(self) -> None:
        """Отменить текущий захват"""
        if not self._is_capturing:
            return
        
        key = self._current_key
        self._cleanup()
        
        if key:
            self.capture_cancelled.emit(key)
    
    def _cleanup(self) -> None:
        """Очистить состояние"""
        self._is_capturing = False
        self._current_key = None
        self._current_name = None
        self._start_pos = None
        
        if self._overlay:
            try:
                self._overlay.close()
            except:
                pass
            self._overlay = None
        
        if self._mouse_listener:
            try:
                self._mouse_listener.stop()
            except:
                pass
            self._mouse_listener = None
        
        if self._keyboard_listener:
            try:
                self._keyboard_listener.stop()
            except:
                pass
            self._keyboard_listener = None


# Глобальный экземпляр
_capture_manager: Optional[CoordinateCapture] = None


def get_capture_manager() -> CoordinateCapture:
    """Получить глобальный экземпляр CoordinateCapture"""
    global _capture_manager
    if _capture_manager is None:
        _capture_manager = CoordinateCapture()
    return _capture_manager

# Глобальный экземпляр
_capture_manager: Optional[CoordinateCapture] = None


def get_capture_manager() -> CoordinateCapture:
    """Получить глобальный экземпляр CoordinateCapture"""
    global _capture_manager
    if _capture_manager is None:
        _capture_manager = CoordinateCapture()
    return _capture_manager

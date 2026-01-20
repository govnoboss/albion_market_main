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
    capture_cancelled = pyqtSignal(str)  # key
    capture_started = pyqtSignal(str)  # key
    
    # Внутренние сигналы для межпоточного взаимодействия
    _internal_captured = pyqtSignal(str, int, int)
    _internal_cancelled = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self._current_key: Optional[str] = None
        self._current_name: Optional[str] = None
        self._mouse_listener: Optional[mouse.Listener] = None
        self._keyboard_listener: Optional[keyboard.Listener] = None
        self._is_capturing = False
        
        # Подключаем внутренние сигналы к обработчикам
        self._internal_captured.connect(self._handle_captured, Qt.ConnectionType.QueuedConnection)
        self._internal_cancelled.connect(self._handle_cancelled, Qt.ConnectionType.QueuedConnection)
    
    @property
    def is_capturing(self) -> bool:
        return self._is_capturing
    
    def start_capture(self, key: str, display_name: str) -> None:
        """Начать захват координаты (просто ждём следующий клик)"""
        if self._is_capturing:
            return
        
        self._is_capturing = True
        self._current_key = key
        self._current_name = display_name
        
        # Сигнал о начале захвата
        self.capture_started.emit(key)
        
        # Запускаем слушатель мыши
        self._mouse_listener = mouse.Listener(on_click=self._on_click)
        self._mouse_listener.start()
        
        # Запускаем слушатель клавиатуры для ESC
        self._keyboard_listener = keyboard.Listener(on_press=self._on_key_press)
        self._keyboard_listener.start()
    
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
        # Захватываем только при нажатии левой кнопки
        if pressed and button == mouse.Button.left:
            current_key = self._current_key
            if current_key:
                # Эмитим сигнал для главного потока
                self._internal_captured.emit(current_key, int(x), int(y))
            return False  # Останавливаем listener
        
        return True  # Продолжаем слушать
    
    def _handle_captured(self, key: str, x: int, y: int) -> None:
        """Обработчик захвата (вызывается в главном потоке через сигнал)"""
        self._cleanup()
        self.coordinate_captured.emit(key, x, y)
    
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

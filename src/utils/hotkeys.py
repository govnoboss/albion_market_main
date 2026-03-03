"""
Глобальные хоткеи через Windows RegisterHotKey API.
Не использует глобальный хук (WH_KEYBOARD_LL), поэтому не блокирует
хоткеи других приложений (OBS, Discord и т.д.).
"""

import ctypes
import ctypes.wintypes
from PyQt6.QtCore import QAbstractNativeEventFilter, QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

from .logger import get_logger

logger = get_logger()

# Windows API
WM_HOTKEY = 0x0312
MOD_NOREPEAT = 0x4000
user32 = ctypes.windll.user32

# Virtual Key Codes
VK_MAP = {
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
    "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
    "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
}


class _NativeMsg(ctypes.Structure):
    """Структура Windows MSG для парсинга нативных событий."""
    _fields_ = [
        ("hwnd", ctypes.wintypes.HWND),
        ("message", ctypes.wintypes.UINT),
        ("wParam", ctypes.wintypes.WPARAM),
        ("lParam", ctypes.wintypes.LPARAM),
        ("time", ctypes.wintypes.DWORD),
        ("pt", ctypes.wintypes.POINT),
    ]


class _HotkeyFilter(QAbstractNativeEventFilter):
    """Фильтр нативных событий Windows для перехвата WM_HOTKEY."""

    def __init__(self, manager):
        super().__init__()
        self._manager = manager

    def nativeEventFilter(self, eventType, message):
        try:
            if eventType == b"windows_generic_MSG":
                msg = _NativeMsg.from_address(int(message))
                if msg.message == WM_HOTKEY:
                    hotkey_id = msg.wParam
                    self._manager._on_hotkey_triggered(hotkey_id)
        except Exception:
            pass
        return False, 0


class HotkeyManager(QObject):
    """
    Менеджер глобальных хоткеев через Windows RegisterHotKey.
    
    Использование:
        manager = HotkeyManager()
        manager.register("F5", callback_fn)
        manager.register("F6", callback_fn)
        ...
        manager.unregister_all()  # при закрытии
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hotkeys = {}       # id -> (key_name, callback)
        self._next_id = 1
        self._filter = _HotkeyFilter(self)
        
        app = QApplication.instance()
        if app:
            app.installNativeEventFilter(self._filter)
    
    def register(self, key: str, callback) -> bool:
        """
        Зарегистрировать глобальный хоткей.
        
        Args:
            key: Имя клавиши ("F5", "F6", etc.)
            callback: Функция без аргументов
            
        Returns:
            True если хоткей зарегистрирован
        """
        key_upper = key.upper()
        vk = VK_MAP.get(key_upper)
        if vk is None:
            logger.error(f"Hotkey: неизвестная клавиша '{key}'")
            return False
        
        hid = self._next_id
        self._next_id += 1
        
        # RegisterHotKey(NULL, id, modifiers, vk)
        # NULL = текущий поток, MOD_NOREPEAT = без повторов при удержании
        result = user32.RegisterHotKey(None, hid, MOD_NOREPEAT, vk)
        if result:
            self._hotkeys[hid] = (key_upper, callback)
            logger.debug(f"Hotkey {key_upper} зарегистрирован (id={hid})")
            return True
        else:
            logger.warning(f"Hotkey {key_upper} не удалось зарегистрировать (занят другим приложением?)")
            return False
    
    def unregister(self, key: str):
        """Снять регистрацию конкретного хоткея."""
        key_upper = key.upper()
        to_remove = []
        for hid, (name, _) in self._hotkeys.items():
            if name == key_upper:
                user32.UnregisterHotKey(None, hid)
                to_remove.append(hid)
                logger.debug(f"Hotkey {key_upper} снят (id={hid})")
        for hid in to_remove:
            del self._hotkeys[hid]
    
    def unregister_all(self):
        """Снять все зарегистрированные хоткеи."""
        for hid in list(self._hotkeys.keys()):
            user32.UnregisterHotKey(None, hid)
        self._hotkeys.clear()
        logger.debug("Все хоткеи сняты")
    
    def _on_hotkey_triggered(self, hotkey_id):
        """Вызывается из нативного фильтра при нажатии хоткея."""
        entry = self._hotkeys.get(hotkey_id)
        if entry:
            _, callback = entry
            try:
                callback()
            except Exception as e:
                logger.error(f"Ошибка в обработчике хоткея: {e}")

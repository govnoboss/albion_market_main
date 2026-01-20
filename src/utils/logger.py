"""
Система логирования для Albion Market Scanner
"""

import logging
from datetime import datetime
from typing import Callable, Optional
from PyQt6.QtCore import QObject, pyqtSignal


class LogHandler(logging.Handler):
    """Обработчик логов для отправки в UI"""
    
    def __init__(self, callback: Callable[[str, str], None]):
        super().__init__()
        self.callback = callback
        self.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', 
                                            datefmt='%H:%M:%S'))
    
    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        level = record.levelname.lower()
        self.callback(msg, level)


class LogEmitter(QObject):
    """Эмиттер сигналов для логов (thread-safe)"""
    log_signal = pyqtSignal(str, str)  # message, level


class Logger:
    """Кастомный логгер с поддержкой UI"""
    
    def __init__(self, name: str = "AlbionMarket"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Консольный хендлер
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', 
                            datefmt='%H:%M:%S')
        )
        self.logger.addHandler(console_handler)
        
        # Эмиттер для UI
        self.emitter = LogEmitter()
        self._ui_handler: Optional[LogHandler] = None
    
    def connect_ui(self, callback: Callable[[str, str], None]) -> None:
        """Подключить UI callback для получения логов"""
        if self._ui_handler:
            self.logger.removeHandler(self._ui_handler)
        
        self._ui_handler = LogHandler(callback)
        self._ui_handler.setLevel(logging.INFO)
        self.logger.addHandler(self._ui_handler)
    
    def debug(self, msg: str) -> None:
        self.logger.debug(msg)
    
    def info(self, msg: str) -> None:
        self.logger.info(msg)
    
    def warning(self, msg: str) -> None:
        self.logger.warning(msg)
    
    def error(self, msg: str) -> None:
        self.logger.error(msg)
    
    def success(self, msg: str) -> None:
        """Кастомный уровень для успешных операций"""
        self.logger.info(f"✓ {msg}")
    
    def action(self, msg: str) -> None:
        """Кастомный уровень для действий бота"""
        self.logger.info(f"⚡ {msg}")


# Глобальный экземпляр логгера
_logger: Optional[Logger] = None


def get_logger() -> Logger:
    """Получить глобальный экземпляр логгера"""
    global _logger
    if _logger is None:
        _logger = Logger()
    return _logger

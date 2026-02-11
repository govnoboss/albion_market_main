import logging
import os
from datetime import datetime
from typing import Callable, Optional
from logging.handlers import RotatingFileHandler
from PyQt6.QtCore import QObject, pyqtSignal


class LogHandler(logging.Handler):
    """Обработчик логов для отправки в UI через сигналы"""
    
    def __init__(self, emitter: 'LogEmitter'):
        super().__init__()
        self.emitter = emitter
        self.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', 
                                            datefmt='%H:%M:%S'))
    
    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        level = record.levelname.lower()
        # Отправляем сигнал (Thread-Safe)
        self.emitter.log_signal.emit(msg, level)


class LogEmitter(QObject):
    """Эмиттер сигналов для логов (thread-safe)"""
    log_signal = pyqtSignal(str, str)  # message, level


class Logger:
    """Кастомный логгер с поддержкой UI"""
    
    def __init__(self, name: str = "AlbionMarket"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # 1. Консольный хендлер
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', 
                            datefmt='%H:%M:%S')
        )
        self.logger.addHandler(console_handler)

        # 2. Файловый хендлер (Rotating)
        # Создаем папку logs если её нет
        log_dir = "logs"
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except Exception:
                pass # Если не удалось создать (например, нет прав)

        try:
            log_file = os.path.join(log_dir, "debug.log")
            file_handler = RotatingFileHandler(
                log_file, 
                maxBytes=5*1024*1024,  # 5 MB
                backupCount=3,
                encoding="utf-8"
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
            )
            self.logger.addHandler(file_handler)
        except Exception as e:
            print(f"FAILED TO INIT FILE LOGGER: {e}")
        
        # Эмиттер для UI
        self.emitter = LogEmitter()
        self._ui_handler: Optional[LogHandler] = None
    
    def connect_ui(self, callback: Callable[[str, str], None]) -> None:
        """
        Подключить UI callback для получения логов.
        Callback будет вызываться в потоке UI (через слот).
        """
        # 1. Создаем хендлер, если нет
        if not self._ui_handler:
            self._ui_handler = LogHandler(self.emitter)
            self._ui_handler.setLevel(logging.INFO)
            self.logger.addHandler(self._ui_handler)
            
        # 2. Подключаем сигнал к callback (слоту)
        # Обратите внимание: Qt автоматически определит QueuedConnection,
        # если сигнал идет из другого потока.
        self.emitter.log_signal.connect(callback)
    
    def debug(self, msg: str) -> None:
        self.logger.debug(msg)
    
    def info(self, msg: str) -> None:
        self.logger.info(msg)
    
    def warning(self, msg: str) -> None:
        self.logger.warning(msg)
    
    def error(self, msg: str) -> None:
        self.logger.error(msg)
        
    def critical(self, msg: str) -> None:
        self.logger.critical(msg)
    
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

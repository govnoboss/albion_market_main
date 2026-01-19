"""
Albion Market Bot v3.0 - Scan Worker v2

Фоновый поток для сканирования цен с Tier/Enchant/Quality.
"""

import logging
from typing import List
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from core.scanner_engine import ScannerEngineV2, ScannerConfig, ScanResult

logger = logging.getLogger(__name__)


class ScanWorker(QThread):
    """
    QThread для фонового сканирования цен v2.
    
    Использует ScannerEngineV2 с поддержкой Tier/Enchant/Quality.
    """
    
    # Сигналы
    progress = pyqtSignal(int, int, str)  # (current, total, description)
    status = pyqtSignal(str)               # message
    result = pyqtSignal(object)            # ScanResult
    finished_scan = pyqtSignal(bool, str, str)  # (success, message, filepath)
    error = pyqtSignal(str)
    
    def __init__(self, config: ScannerConfig = None, items: List[str] = None, parent=None):
        super().__init__(parent)
        self.config = config or ScannerConfig()
        self.items = items
        self.engine: ScannerEngineV2 = None
    
    def stop(self):
        if self.engine:
            self.engine.stop()
    
    def pause(self):
        if self.engine:
            self.engine.pause()
    
    def resume(self):
        if self.engine:
            self.engine.resume()
    
    def run(self):
        try:
            self.engine = ScannerEngineV2(self.config)
            
            # Подключение callbacks
            self.engine.on_progress = lambda c, t, d: self.progress.emit(c, t, d)
            self.engine.on_status = lambda m: self.status.emit(m)
            self.engine.on_result = lambda r: self.result.emit(r)
            
            # Запуск сканирования
            results = self.engine.run_full_scan(self.items)
            
            # Сохранение результатов
            if results:
                filepath = self.engine.save_results()
                
                success_count = sum(1 for r in results if r.success)
                message = f"Сканирование завершено: {success_count}/{len(results)} записей"
                
                self.finished_scan.emit(True, message, str(filepath))
            else:
                self.finished_scan.emit(False, "Нет результатов", "")
                
        except Exception as e:
            error_msg = f"Ошибка сканирования: {e}"
            logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)
            self.finished_scan.emit(False, error_msg, "")

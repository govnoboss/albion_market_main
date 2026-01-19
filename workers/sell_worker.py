"""
Albion Market Bot v3.0 - Sell Worker

Фоновый поток для процесса продажи.
"""

import time
import logging
from datetime import datetime
from typing import List, Dict, Any

from PyQt6.QtCore import QThread, pyqtSignal

from core.ocr_engine import get_ocr_engine
from core.automation import get_automation_controller
from core.data_manager import get_data_manager
from config import AppSettings

logger = logging.getLogger(__name__)


class SellWorker(QThread):
    """Рабочий поток для продажи предметов."""
    
    # Сигналы
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    item_sold = pyqtSignal(str, int, int)  # (name, quantity, price)
    error = pyqtSignal(str)
    finished_with_result = pyqtSignal(bool, str)
    
    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self.settings = settings
        
        self._running = True
        self._paused = False
        
        self.total_income = 0
        self.total_cost = 0
        self.sold_items: List[Dict[str, Any]] = []
        self.log_entries: List[str] = []
    
    def stop(self):
        self._running = False
    
    def pause(self):
        self._paused = True
    
    def resume(self):
        self._paused = False
    
    def _log(self, message: str):
        entry = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        self.log_entries.append(entry)
        logger.info(message)
        self.status.emit(message)
    
    def _wait_if_paused(self):
        while self._paused and self._running:
            time.sleep(0.1)
    
    def run(self):
        """Основной цикл продажи."""
        try:
            self._log("=== Начало сессии продаж ===")
            
            manager = get_data_manager()
            ocr = get_ocr_engine()
            auto = get_automation_controller()
            
            coords = self.settings.coordinates
            regions = self.settings.regions
            
            # Получаем WAPP для расчёта прибыли
            item_costs = manager.get_item_costs()
            
            failure_counter = 0
            max_failures = 5
            
            while failure_counter < max_failures and self._running:
                self._wait_if_paused()
                
                # Клик на кнопку продажи
                self._log("Сканирование предмета для продажи...")
                auto.move_and_click(coords.buy_x, coords.buy_y, scatter=5)
                time.sleep(0.5)
                
                # OCR имени
                scanned_name = ocr.scan_text(regions.item_name.to_tuple())
                
                if not scanned_name:
                    failure_counter += 1
                    self._log(f"Не удалось распознать имя (попытка {failure_counter})")
                    continue
                
                self._log(f"Предмет: {scanned_name}")
                
                # Поиск WAPP
                wapp = 0.0
                match = item_costs[item_costs['item_name'].str.lower() == scanned_name.lower()]
                if not match.empty:
                    wapp = match.iloc[0]['wapp']
                
                if wapp == 0:
                    self._log(f"Нет данных о себестоимости для {scanned_name}")
                    failure_counter += 1
                    continue
                
                # Клик минус для корректировки
                auto.move_and_click(coords.minus_x, coords.minus_y, scatter=5)
                time.sleep(0.2)
                
                # OCR цены продажи
                sale_price = ocr.scan_digits(regions.sell_price.to_tuple())
                item_price = ocr.scan_digits(regions.sell_item_price.to_tuple())
                
                if sale_price > 0 and item_price > 1:
                    # Расчёт
                    tax = 0.105
                    quantity = int(round(sale_price / ((item_price - 1) * (1 - tax))))
                    profit_per_item = (item_price - 1) * (1 - tax) - wapp
                    cost_for_stack = quantity * wapp
                    
                    # Подтверждение
                    auto.move_and_click(coords.confirm_x, coords.confirm_y, scatter=5)
                    
                    self.total_income += sale_price
                    self.total_cost += cost_for_stack
                    
                    self.sold_items.append({
                        'name': scanned_name,
                        'quantity': quantity,
                        'sale_price_total': sale_price,
                        'profit_per_item': profit_per_item,
                        'cost_for_stack': cost_for_stack
                    })
                    
                    self.item_sold.emit(scanned_name, quantity, sale_price)
                    self._log(f"Продано: {scanned_name} x{quantity} за {sale_price}")
                    
                    failure_counter = 0
                else:
                    failure_counter += 1
                    self._log(f"Не удалось распознать цену (попытка {failure_counter})")
                
                time.sleep(0.5)
            
            # Отчёт
            final_profit = self.total_income - self.total_cost
            self._log(f"=== Сессия завершена. Прибыль: {final_profit:,.0f} ===")
            
            manager.save_sell_report(
                self.sold_items,
                self.total_income,
                self.total_cost,
                self.log_entries
            )
            
            self.finished_with_result.emit(
                True,
                f"Продажа завершена! Прибыль: {final_profit:,.0f}"
            )
            
        except Exception as e:
            error_msg = f"Ошибка продажи: {e}"
            logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)
            self.finished_with_result.emit(False, error_msg)

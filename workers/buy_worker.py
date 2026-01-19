"""
Albion Market Bot v3.0 - Buy Worker

Фоновый поток для процесса закупки.
"""

import time
import logging
from datetime import datetime
from typing import Optional, List

from PyQt6.QtCore import QThread, pyqtSignal
import pandas as pd

from core.ocr_engine import get_ocr_engine
from core.automation import get_automation_controller
from core.price_calculator import calculate_limit_price, is_profitable, calculate_batch_cost
from core.data_manager import get_data_manager
from config import AppSettings

logger = logging.getLogger(__name__)


class BuyWorker(QThread):
    """Рабочий поток для закупки предметов."""
    
    # Сигналы
    progress = pyqtSignal(int)  # Прогресс (0-100)
    status = pyqtSignal(str)  # Статус
    item_info = pyqtSignal(dict)  # Информация о текущем предмете
    item_bought = pyqtSignal(str, int, int)  # (name, quantity, price)
    error = pyqtSignal(str)  # Ошибка
    finished_with_result = pyqtSignal(bool, str)  # (success, message)
    
    def __init__(
        self, 
        settings: AppSettings,
        mode: str = "manual",  # "manual" или "order"
        parent=None
    ):
        super().__init__(parent)
        self.settings = settings
        self.mode = mode
        
        # Управление состоянием
        self._running = True
        self._paused = False
        self._skip_current = False
        
        # Статистика
        self.total_spent = 0
        self.items_bought = 0
        self.log_entries: List[str] = []
    
    def stop(self):
        """Остановка процесса."""
        self._running = False
    
    def pause(self):
        """Пауза."""
        self._paused = True
    
    def resume(self):
        """Возобновление."""
        self._paused = False
    
    def skip_item(self):
        """Пропуск текущего предмета."""
        self._skip_current = True
    
    def _log(self, message: str):
        """Добавление записи в лог."""
        entry = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        self.log_entries.append(entry)
        logger.info(message)
        self.status.emit(message)
    
    def _wait_if_paused(self):
        """Ожидание снятия паузы."""
        while self._paused and self._running:
            time.sleep(0.1)
    
    def run(self):
        """Основной цикл закупки."""
        try:
            self._log(f"=== Начало сессии ({self.mode}) ===")
            
            # Инициализация
            manager = get_data_manager()
            ocr = get_ocr_engine()
            auto = get_automation_controller()
            
            # Загрузка данных
            df = manager.load_items(
                sort_by='profit',
                ascending=False,
                tier6_only=self.settings.buy.tier6_only
            )
            
            total_items = len(df)
            if total_items == 0:
                self.finished_with_result.emit(False, "Таблица предметов пуста")
                return
            
            coords = self.settings.coordinates
            regions = self.settings.regions
            budget = self.settings.buy.budget
            delay = self.settings.buy.delay
            start_row = self.settings.buy.start_row - 1
            
            # Основной цикл
            for index, row in df.iloc[start_row:].iterrows():
                self._wait_if_paused()
                
                if not self._running:
                    self._log("Остановлено пользователем")
                    break
                
                if self._skip_current:
                    self._log(f"Пропущен: {row['name']}")
                    self._skip_current = False
                    continue
                
                # Прогресс
                progress_pct = int((index - start_row + 1) / (total_items - start_row) * 100)
                self.progress.emit(progress_pct)
                
                # Обработка предмета
                name = str(row['name']).strip()
                
                try:
                    value = int(row['value'])
                    store = int(row['store'])
                    present = float(row.get('present', 1.0))
                    weight = float(row.get('weightforitem', 0))
                except (ValueError, TypeError) as e:
                    self._log(f"Ошибка данных для {name}: {e}")
                    continue
                
                if value <= 0 or store <= 0:
                    continue
                
                # Расчёт лимита
                limit_price = calculate_limit_price(
                    value, present, weight,
                    self.settings.buy.transport_cost_per_kg
                )
                
                if limit_price <= 0:
                    self._log(f"Невыгоден: {name} (лимит={limit_price})")
                    continue
                
                # Информация о предмете
                self.item_info.emit({
                    'name': name,
                    'value': value,
                    'store': store,
                    'limit_price': limit_price,
                    'bought': 0,
                    'total_spent': self.total_spent,
                    'budget': budget
                })
                
                self._log(f"Обработка: {name} (лимит: {limit_price})")
                
                # Очистка и поиск
                auto.move_and_click(coords.clear_x, coords.clear_y)
                auto.random_delay(0.1, 0.2)
                
                auto.move_and_click(coords.search_x, coords.search_y)
                auto.random_delay(0.1, 0.2)
                
                auto.type_text(name)
                auto.random_delay(0.5, 1.0)
                
                # Цикл покупки
                bought = 0
                failed_attempts = 0
                max_attempts = 5
                
                while bought < store and self._running and failed_attempts < max_attempts:
                    self._wait_if_paused()
                    
                    if self._skip_current:
                        break
                    
                    # OCR цены
                    ocr_price = ocr.scan_digits(regions.price.to_tuple())
                    
                    if ocr_price == 0:
                        failed_attempts += 1
                        self._log(f"OCR вернул 0 (попытка {failed_attempts})")
                        time.sleep(delay)
                        continue
                    
                    # Проверка выгодности
                    if not is_profitable(ocr_price, limit_price):
                        self._log(f"Цена {ocr_price} > лимит {limit_price}")
                        break
                    
                    # Проверка бюджета
                    if self.total_spent + ocr_price > budget:
                        self._log("Бюджет исчерпан")
                        self._running = False
                        break
                    
                    # Покупка
                    auto.move_and_click(coords.buy_x, coords.buy_y)
                    auto.random_delay(0.3, 0.5)
                    
                    # Подтверждение
                    auto.move_and_click(coords.confirm_x, coords.confirm_y)
                    auto.random_delay(0.2, 0.4)
                    
                    bought += 1
                    self.total_spent += ocr_price
                    self.items_bought += 1
                    
                    # Лог покупки
                    manager.log_purchase(name, 1, ocr_price, self.mode)
                    self.item_bought.emit(name, 1, ocr_price)
                    
                    self._log(f"Куплено: {name} за {ocr_price} ({bought}/{store})")
                    
                    failed_attempts = 0
                    time.sleep(delay)
                
                self._skip_current = False
            
            # Завершение
            self._log(f"=== Сессия завершена. Потрачено: {self.total_spent} ===")
            manager.save_session_log(self.log_entries, self.mode)
            
            self.finished_with_result.emit(
                True, 
                f"Завершено! Потрачено: {self.total_spent:,}, куплено предметов: {self.items_bought}"
            )
            
        except Exception as e:
            error_msg = f"Критическая ошибка: {e}"
            logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)
            self.finished_with_result.emit(False, error_msg)

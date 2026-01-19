"""
Albion Market Bot v3.0 - Smart Buy Worker

Фоновый поток для закупки с использованием Template Matching.
"""

import time
import logging
from datetime import datetime
from typing import Optional, List

from PyQt6.QtCore import QThread, pyqtSignal
import pandas as pd

from core.ocr_engine import get_ocr_engine
from core.smart_automation import get_smart_automation
from core.price_calculator import calculate_limit_price, is_profitable
from core.data_manager import get_data_manager
from core.simple_config import load_simplified_settings

logger = logging.getLogger(__name__)


class SmartBuyWorker(QThread):
    """
    Рабочий поток для закупки с Template Matching.
    
    Использует автоматический поиск кнопок вместо фиксированных координат.
    """
    
    # Сигналы
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    item_info = pyqtSignal(dict)
    item_bought = pyqtSignal(str, int, int)
    error = pyqtSignal(str)
    finished_with_result = pyqtSignal(bool, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Загружаем упрощённые настройки
        self.settings = load_simplified_settings()
        
        # Состояние
        self._running = True
        self._paused = False
        self._skip_current = False
        
        # Статистика
        self.total_spent = 0
        self.items_bought = 0
        self.log_entries: List[str] = []
    
    def stop(self):
        self._running = False
    
    def pause(self):
        self._paused = True
    
    def resume(self):
        self._paused = False
    
    def skip_item(self):
        self._skip_current = True
    
    def _log(self, message: str):
        entry = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        self.log_entries.append(entry)
        logger.info(message)
        self.status.emit(message)
    
    def _wait_if_paused(self):
        while self._paused and self._running:
            time.sleep(0.1)
    
    def run(self):
        """Основной цикл закупки."""
        try:
            self._log("=== Начало сессии (Smart Buy) ===")
            
            # Инициализация
            manager = get_data_manager()
            ocr = get_ocr_engine()
            smart = get_smart_automation()
            
            # Загрузка данных
            df = manager.load_items(
                sort_by='profit',
                ascending=False,
                tier6_only=self.settings.tier6_only
            )
            
            total_items = len(df)
            if total_items == 0:
                self.finished_with_result.emit(False, "Таблица предметов пуста")
                return
            
            budget = self.settings.budget
            delay = self.settings.delay
            start_row = self.settings.start_row - 1
            
            # Проверяем наличие OCR регионов
            if not self.settings.price_region.is_valid():
                self.finished_with_result.emit(False, "Не настроена область OCR для цены!")
                return
            
            self._log(f"Загружено {total_items} предметов, бюджет: {budget:,}")
            
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
                current_idx = index - start_row + 1
                progress_pct = min(99, int(current_idx / (total_items - start_row) * 100))
                self.progress.emit(progress_pct)
                
                # Данные предмета
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
                    self.settings.transport_cost_per_kg
                )
                
                if limit_price <= 0:
                    continue
                
                # Информация о предмете
                self.item_info.emit({
                    'name': name,
                    'value': value,
                    'store': store,
                    'limit_price': limit_price,
                    'total_spent': self.total_spent,
                    'budget': budget
                })
                
                self._log(f"🔍 {name} (лимит: {limit_price:,})")
                
                # 1. Очистка поиска (через template matching)
                if not smart.click_button('clear_button', timeout=2.0):
                    self._log("⚠️ Не найдена кнопка очистки")
                time.sleep(delay)
                
                # 2. Ввод в поиск
                if not smart.type_in_search(name, self.settings.search_coords):
                    self._log("⚠️ Не удалось ввести в поиск")
                    continue
                
                time.sleep(0.5 + delay)
                
                # 3. Цикл покупки
                bought = 0
                failed_attempts = 0
                max_attempts = 3
                
                while bought < store and self._running and failed_attempts < max_attempts:
                    self._wait_if_paused()
                    
                    if self._skip_current:
                        break
                    
                    # Клик "Купить" в списке
                    if not smart.click_buy_in_list(row_index=0):
                        failed_attempts += 1
                        self._log(f"⚠️ Кнопка 'Купить' не найдена (попытка {failed_attempts})")
                        time.sleep(delay)
                        continue
                    
                    time.sleep(0.3 + delay)
                    
                    # OCR цены
                    ocr_price = ocr.scan_digits(self.settings.price_region.to_tuple())
                    
                    if ocr_price == 0:
                        # Попробуем подтвердить если уже открыто окно
                        smart.click_confirm(timeout=1.0)
                        failed_attempts += 1
                        time.sleep(delay)
                        continue
                    
                    # Проверка выгодности
                    if not is_profitable(ocr_price, limit_price):
                        self._log(f"❌ Цена {ocr_price:,} > лимит {limit_price:,}")
                        # Закрываем окно
                        smart.handle_popups()
                        break
                    
                    # Проверка бюджета
                    if self.total_spent + ocr_price > budget:
                        self._log("💰 Бюджет исчерпан")
                        self._running = False
                        break
                    
                    # Подтверждение покупки
                    if smart.click_confirm(timeout=2.0):
                        # Ждём popup "Да"
                        time.sleep(0.3)
                        smart.click_button('yes_button', timeout=2.0)
                        
                        bought += 1
                        self.total_spent += ocr_price
                        self.items_bought += 1
                        
                        manager.log_purchase(name, 1, ocr_price, "smart")
                        self.item_bought.emit(name, 1, ocr_price)
                        
                        self._log(f"✅ Куплено за {ocr_price:,} ({bought}/{store})")
                        failed_attempts = 0
                    else:
                        failed_attempts += 1
                    
                    time.sleep(delay)
                
                self._skip_current = False
            
            # Завершение
            self._log(f"=== Сессия завершена. Потрачено: {self.total_spent:,} ===")
            manager.save_session_log(self.log_entries, "smart")
            
            self.finished_with_result.emit(
                True,
                f"✅ Завершено! Потрачено: {self.total_spent:,}, куплено: {self.items_bought}"
            )
            
        except Exception as e:
            error_msg = f"Критическая ошибка: {e}"
            logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)
            self.finished_with_result.emit(False, error_msg)

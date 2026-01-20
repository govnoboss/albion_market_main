"""
Core Scanning Logic Engine
"""

import time
import threading
import pyautogui
from typing import Optional

from ..utils.config import get_config
from ..utils.logger import get_logger
from .interaction import DropdownSelector

class ScannerEngine:
    """Движок сканирования рынка"""
    
    def __init__(self, stop_event: threading.Event):
        self.stop_event = stop_event
        self.config = get_config()
        self.logger = get_logger()
        self.interaction = DropdownSelector()
        
    def should_stop(self) -> bool:
        """Проверка запроса на остановку"""
        return self.stop_event.is_set()
        
    def _sleep(self, multiplier: float = 1.0):
        """Пауза с учетом настройки задержки"""
        base_delay = self.config.get_setting("click_delay", 100) / 1000.0
        time.sleep(base_delay * multiplier)

    def _click(self, x: int, y: int):
        """Безопасный клик"""
        if self.should_stop(): return
        pyautogui.click(x, y)
        self._sleep()

    def run(self):
        """Основной цикл сканирования"""
        items = self.config.get_items()
        
        if not items:
            self.logger.warning("Список предметов пуст! Добавьте предметы.")
            return

        self.logger.info(f"Начинаю сканирование {len(items)} предметов...")
        
        for item in items:
            if self.should_stop(): break
            
            item_name = item.get("name")
            if not item.get("enabled", True):
                continue
                
            self.logger.info(f">>> Обработка предмета: {item_name}")
            self._process_item(item_name)
            
            # Пауза между предметами (Scan Interval)
            if not self.should_stop():
                interval = self.config.get_setting("scan_interval", 500) / 1000.0
                time.sleep(interval)
                
        self.logger.info("Цикл сканирования завершен.")

    def _process_item(self, name: str):
        """Логика обработки одного предмета"""
        
        # 1. Reset Search
        self._reset_search()
        if self.should_stop(): return
        
        # 2. Search Item
        self._search_item(name)
        if self.should_stop(): return
        
        # 3. Open Buy Menu (Раскрыть лот -> Купить?)
        coord = self.config.get_coordinate("buy_button")
        if not coord:
            self.logger.error("Координата 'Кнопка Купить' не задана!")
            return
        self._click(*coord)
        self._sleep(1.5) # Ждем открытия окна покупки
        
        # 4. Setup Initial State (T4, En0, Q1)
        # Как просил пользователь: сбрасываем в дефолт перед сканированием
        self.logger.info("Установка начального состояния (T4, .0, Normal)...")
        self._set_dropdown_state(4, 0, 1)
        if self.should_stop(): return
        
        # 5. Iterate Variations
        self._iterate_variations(name)
        
        # 6. Close Menu (после обработки всех вариантов, чтобы не мешало след. предмету)
        coord = self.config.get_coordinate("menu_close")
        if coord:
            self._click(*coord)
        
    def _reset_search(self):
        """Сброс поиска"""
        coord = self.config.get_coordinate("search_clear")
        if coord:
            self._click(*coord)
            self._sleep(0.5)

    def _search_item(self, name: str):
        """Ввод имени предмета"""
        coord = self.config.get_coordinate("search_input")
        if not coord:
            self.logger.error("Координата 'Поле поиска' не задана!")
            return
            
        self._click(*coord)
        
        if self.should_stop(): return
        pyautogui.write(name, interval=0.05)
        pyautogui.press('enter')
        self._sleep(1.5) # Ждем результатов

    def _iterate_variations(self, item_name: str):
        """Перебор вариаций (Tier, Enchant, Quality)"""
        
        filters = self.config.get_scan_filters()
        
        tiers = filters.get("tiers", [])
        enchants = filters.get("enchants", [])
        qualities = filters.get("qualities", [])
        
        # Идем вложенными циклами
        for tier in tiers:
            if self.should_stop(): return
            
            # Выбор Тира
            self._select_dropdown("tier_dropdown", self.interaction.get_tier_click_point(tier))
            
            for enchant in enchants:
                if self.should_stop(): return
                
                # Выбор Зачарования
                self._select_dropdown("enchant_dropdown", self.interaction.get_enchant_click_point(enchant))
                
                for quality in qualities:
                    if self.should_stop(): return
                    
                    # Выбор Качества
                    self._select_dropdown("quality_dropdown", self.interaction.get_quality_click_point(quality))
                    
                    # Распознавание цены
                    self._recognize_price_stub(item_name, tier, enchant, quality)

    def _set_dropdown_state(self, t: int, e: int, q: int):
        """Установка конкретных значений дропдаунов"""
        if self.should_stop(): return
        
        # Tier
        self._select_dropdown("tier_dropdown", self.interaction.get_tier_click_point(t))
        # Enchant
        self._select_dropdown("enchant_dropdown", self.interaction.get_enchant_click_point(e))
        # Quality
        self._select_dropdown("quality_dropdown", self.interaction.get_quality_click_point(q))

    def _select_dropdown(self, anchor_key: str, click_point: Optional[tuple]):
        """Общий метод выбора из дропдауна"""
        if not click_point: return
        
        # Открываем дропдаун
        anchor = self.config.get_coordinate(anchor_key)
        if anchor: 
            self._click(*anchor)
            self._sleep(0.5)
            # Выбираем пункт
            self._click(*click_point)
            self._sleep(0.5)

    def _recognize_price_stub(self, name: str, t: int, e: int, q: int):
        """Заглушка распознавания цены"""
        if self.should_stop(): return
        self.logger.info(f"🛒 Scanning: {name} | T{t}.{e} | Q{q} -> Price: ???")

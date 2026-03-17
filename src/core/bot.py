"""
Логика бота (Scanner Mode)
Перебор предметов из базы для сбора цен.
"""

import time
import random
import os
import threading
import pyautogui
from PyQt6.QtCore import pyqtSignal

from .base_bot import BaseBot
from .interaction import DropdownSelector
from .network_listener import NetworkListener

class MarketBot(BaseBot):
    """Режим сканирования цен (Scanner Mode)"""
    
    # Сигнал для управления видимостью оверлея (True=Show, False=Hide)
    overlay_status = pyqtSignal(bool) 
    
    def __init__(self):
        super().__init__()
        self.dropdowns = DropdownSelector()
        self.start_index = 0 # Индекс, с которого начинать (0-based)
        self._first_item_processed = False
        
        # Текущее состояние фильтров
        self._current_tier = None
        self._current_enchant = None
        self._current_quality = None
        self._last_detected_quality = None
        
        # Статистика восстановления
        self._recovery_attempts = 0
        self._safe_menu_snapshot = None
        
        # Отчет о подозрительных ценах (Collision Report)
        self._suspicious_reports = []
        
        # Network Listener
        self.network_listener = NetworkListener()
        self.network_listener.market_data_received.connect(self._on_network_data)
        self._last_network_data = None
        self._network_event = threading.Event()
        
        # Текущий обрабатываемый предмет
        self._current_item_name = ""

    def _on_network_data(self, data):
        """Коллбек при получении сетевых данных"""
        self._last_network_data = data
        self._network_event.set()
        
    def run(self):
        """Основной цикл сканирования"""
        self._is_running = True
        self._stop_requested = False
        self._is_paused = False
        self._first_item_processed = False
        
        self.logger.info("⏳ Задержка старта 1 сек...")
        time.sleep(1.0)
        
        # Запуск сетевого слушателя
        self.network_listener.start()
        
        self._detect_current_city()
        
        items = self.config.get_known_items()
        total_items = len(items)
        
        if total_items == 0:
            self.logger.warning("База предметов пуста!")
            self._is_running = False
            self.finished.emit()
            return
            
        self.logger.info(f"Запуск сканирования {total_items} предметов...")
        
        # ONE-TIME SELL TAB CLICK (Before Loop)
        if self._is_black_market:
            self._click_bm_sell_tab()
        
        i = 0
        while i < total_items:
            if self._stop_requested: break
            
            item_name = items[i]
            self._current_item_name = item_name
            
            while self._is_paused:
                if self._stop_requested: break
                time.sleep(0.1)
                
            # --- START INDEX LOGIC ---
            if i < self.start_index:
                # Тихо пропускаем, пока не дойдем до нужного
                i += 1
                continue
            
            self.progress_updated.emit(i + 1, total_items, item_name)
            self.logger.info(f"[{i+1}/{total_items}] Обработка: {item_name}")
            
            # --- SPLIT LOGIC (Black Market Switch) ---
            if self._is_black_market and i == 48:
                 use_switch = self.config.get_setting("use_character_switch", True)
                 if use_switch:
                     self.logger.info("🌗 Достигнут предел (Item 48). Смена персонажа...")
                     if self._perform_character_switch(target_char_index=2):
                         self.logger.info("✅ Смена выполнена. Продолжаем...")
                         self._detect_current_city()
                         # Restore Sell Tab after switch
                         self._click_bm_sell_tab()
                     else:
                         self.logger.error("❌ Смена персонажа не удалась.")
                         self._stop_requested = True
                         break
                 else:
                     self.logger.info("🌗 Достигнут предел (Item 48). Смена персонажа отключена. Остановка.")
                     self._stop_requested = True
                     break
                     
            try:
                # Сбрасываем флаг перед обработкой предмета
                self._recovery_performed_during_item = False
                
                self._process_item(item_name)
                
                if self._recovery_performed_during_item:
                    self.logger.warning(f"🔄 Повторная обработка {item_name} (был вылет)")
                    # НЕ инкрементируем i, чтобы пройти предмет заново
                    continue

                self._first_item_processed = True
                
                # Сохраняем прогресс (чтобы можно было продолжить)
                self.config.set_setting("last_scan_index", i)
                
            except Exception as e:
                self.logger.error(f"Ошибка при обработке '{item_name}': {e}")
            
            i += 1
                
        self.logger.info("Цикл сканирования завершен")
        self._is_running = False
        self.network_listener.stop()
        self.finished.emit()

    def _process_item(self, name: str):
        """
        Логика обработки одного предмета.
        """
        if self._stop_requested: return
        
        # 0. Safety Check
        market_found = False
        for attempt in range(10):
            if self._stop_requested: return
            self._check_pause()
            if self._check_market_is_open():
                market_found = True
                break
            time.sleep(1.0)
            
        if not market_found:
             self.logger.warning(f"Рынок не открыт! Пропуск {name}")
             return

        # 1. Clear Search
        search_clear = self.config.get_coordinate("search_clear")
        if search_clear:
            self._human_move_to(*search_clear)
            self._human_click()
            time.sleep(0.3)
        
        # 2. Input Name
        search_input = self.config.get_coordinate("search_input")
        if search_input:
            self._human_move_to(*search_input)
            self._human_click()
            self._human_type(name)
            pyautogui.press('enter')
            time.sleep(1.0)
            
        # 3. Wait for search result (Network)
        # Ждем первый пакет данных после ввода имени предмета
        self._wait_for_network_update(timeout=3.0)
        
        # 4. Filter and capture variations
        if self._is_black_market:
            self._process_item_black_market(name)
        else:
            self._process_item_normal_market(name)

    def _process_item_normal_market(self, name: str):
        """Быстрый скан для обычного рынка (без клика по предмету)"""
        self._reset_filters()
        self._scan_variations()

    def _process_item_black_market(self, name: str):
        """Полный скан для ЧР (с заходом в меню покупки)"""
        buy_btn = self.config.get_coordinate("buy_button")
        if not buy_btn: return
        
        self._human_move_to(*buy_btn)
        self._human_click()
        time.sleep(0.8) # Даем время окну открыться
        
        self._reset_filters()
        self._scan_variations()
        
        # Close menu
        close_btn = self.config.get_coordinate("menu_close")
        if close_btn:
            self._human_move_to(*close_btn)
            self._human_click()
            time.sleep(0.5)

    def _reset_filters(self):
        """Сброс фильтров в базовое состояние"""
        filters = self.config.get_scan_filters()
        target_tier = min(filters.get("tiers", [4]))
        target_enchant = min(filters.get("enchants", [0]))
        target_quality = min(filters.get("qualities", [1]))
            
        self.logger.info(f"Сброс фильтров в T{target_tier}.{target_enchant} Q{target_quality}")
        
        self._current_tier = None
        self._current_enchant = None
        self._current_quality = None
        
        self._select_enchant(target_enchant)
        self._select_tier(target_tier)
        if self._is_black_market:
             self._select_quality(target_quality, force=True)

    def _scan_variations(self):
        """Перебор вариантов согласно фильтрам."""
        filters = self.config.get_scan_filters()
        max_tier = max(filters.get("tiers", [8]))
        enchants = filters.get("enchants", [0, 1, 2, 3, 4])
        
        last_price = 0
            
        for tier in range(4, max_tier + 1):
             if self._stop_requested: return
             if filters.get("tiers") and tier not in filters["tiers"]: continue
             if self.config.is_tier_exception(tier, self._current_item_name): continue
                 
             self._select_tier(tier)
             
             for enchant in enchants:
                  if self._stop_requested: return
                  key = f"T{tier}.{enchant}"
                  
                  self._select_enchant(enchant)
                  if self._is_black_market:
                      self._select_quality(1)
                  
                  # Ждем данные из сети
                  base_timeout = self.config.get_setting("price_update_timeout", 5.0)
                  timeout_val = 2.0 if last_price == 0 else base_timeout
                  price = self._wait_for_network_update(timeout=timeout_val)
                  
                  if price > 0:
                      self.logger.info(f"💰 [Network] {self._current_item_name} {key}: {price}")
                      from ..utils.price_storage import price_storage
                      price_storage.save_price(
                          self._current_city, self._current_item_name,
                          tier, enchant, 1, price
                      )
                      last_price = price
                  else:
                      if not self._check_market_is_open():
                          return 
                  time.sleep(random.uniform(0.1, 0.2))

    def _select_tier(self, tier: int):
        if self._current_tier == tier: return
        self.logger.debug(f"Выбор тира {tier}...")
        
        if self._is_black_market:
            dropdown_pos = self.config.get_coordinate("bm_tier_dropdown")
            if dropdown_pos:
                self._human_move_to(*dropdown_pos)
                self._human_click()
                time.sleep(0.3)
                bm_index = self._calculate_bm_tier_index(tier, enchant=self._current_enchant or 0)
                coord = self.dropdowns.get_dropdown_click_point("bm_tier_dropdown", bm_index)
                if coord:
                    self._human_move_to(*coord)
                    self._human_click()
                    self._current_tier = tier
                    time.sleep(0.3)
            return

        coord = self.dropdowns.get_tier_click_point(tier)
        if coord:
            self.dropdowns.open_tier_menu(self)
            self._human_move_to(*coord)
            self._human_click()
            self._current_tier = tier
            time.sleep(0.2)

    def _calculate_bm_tier_index(self, tier: int, enchant: int = 0) -> int:
        # Для ЧР при enchant > 0 список начинается с T4
        min_tier = 4
        if enchant == 0:
            if self.config.is_tier_exception(1, self._current_item_name): min_tier = 1
            elif self.config.is_tier_exception(2, self._current_item_name): min_tier = 2
            elif self.config.is_tier_exception(3, self._current_item_name): min_tier = 3
        return tier - min_tier

    def _select_enchant(self, enchant: int):
        if self._current_enchant == enchant: return
        self.logger.debug(f"Выбор зачарования {enchant}...")
        
        if self._is_black_market:
            dropdown_pos = self.config.get_coordinate("bm_enchant_dropdown")
            if dropdown_pos:
                self._human_move_to(*dropdown_pos)
                self._human_click()
                time.sleep(0.3)
                coord = self.dropdowns.get_dropdown_click_point("bm_enchant_dropdown", enchant)
                if coord:
                    self._human_move_to(*coord)
                    self._human_click()
                    self._current_enchant = enchant
                    time.sleep(0.3)
            return

        coord = self.dropdowns.get_enchant_click_point(enchant)
        if coord:
            self.dropdowns.open_enchant_menu(self)
            self._human_move_to(*coord)
            self._human_click()
            self._current_enchant = enchant
            time.sleep(0.2)

    def _select_quality(self, quality: int, force: bool = False):
        """Выбор качества предмета (используется для ЧР и T7+)"""
        if not force and self._current_quality == quality: return True
        
        anchor = self.config.get_coordinate("quality_dropdown")
        if not anchor: return False

        # Активный выбор без OCR-проверки
        self._human_move_to(*anchor)
        self._human_click()
        time.sleep(0.3)
        
        point = self.dropdowns.get_quality_click_point(quality)
        if point:
             self._human_move_to(*point)
             self._human_click()
             self._current_quality = quality
             time.sleep(0.3)
             return True
             
        return False

    def _perform_character_switch(self, target_char_index: int) -> bool:
        """Смена персонажа"""
        self.logger.info("🔄 Смена персонажа...")
        self.overlay_status.emit(False)
        
        settings_btn = self.config.get_coordinate("bm_settings_btn")
        logout_btn = self.config.get_coordinate("bm_logout_btn")
        if not settings_btn or not logout_btn: return False
             
        self._human_move_to(*settings_btn)
        self._human_click()
        time.sleep(1.0)
        self._human_move_to(*logout_btn)
        self._human_click()
        time.sleep(11.0)
        
        char_area = self.config.get_coordinate_area("bm_char2_area")
        if not char_area: return False
        
        char_icon_click = (char_area['x'] + char_area['w']//2, char_area['y'] + char_area['h']//2)
        self._human_move_to(*char_icon_click)
        self._human_click()
        time.sleep(1.0)
        
        login_btn = self.config.get_coordinate("bm_login_btn")
        if login_btn:
            self._human_move_to(*login_btn)
            self._human_click()
            time.sleep(5.0)
            return self._wait_for_market_reopen()
        return False

    def _wait_for_market_reopen(self) -> bool:
        from .market_opener import MarketOpener
        opener = MarketOpener(self.logger, self.config)
        return opener.open_market()

    def _wait_for_network_update(self, timeout: float = 5.0) -> int:
        """Ожидает получения данных из сети"""
        self._network_event.clear()
        self._last_network_data = None
        if not self._network_event.wait(timeout): return 0
        data = self._last_network_data
        if not data or data.get("type") != "search_results": return 0
        lots = data.get("data", [])
        if not lots: return 0
        prices = [lot.get("UnitPriceSilver") for lot in lots if lot.get("UnitPriceSilver")]
        return int(min(prices)) if prices else 0

    def _click_bm_sell_tab(self):
        """Переход на вкладку Продать на ЧР"""
        tab = self.config.get_coordinate("bm_sell_tab")
        if tab:
            self._human_move_to(*tab)
            self._human_click()
            time.sleep(0.5)

    def _wait_for_price_update(self, old_price: int, timeout: float = 5.0) -> int:
        return self._wait_for_network_update(timeout)

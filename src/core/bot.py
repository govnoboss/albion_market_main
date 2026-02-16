"""
Логика бота (Scanner Mode)
Перебор предметов из базы для сбора цен.
"""

import time
import random
import pyautogui
from .base_bot import BaseBot
from .interaction import DropdownSelector

from PyQt6.QtCore import pyqtSignal

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
        
    def run(self):
        """Основной цикл сканирования"""
        self._is_running = True
        self._stop_requested = False
        self._is_paused = False
        self._first_item_processed = False
        
        self.logger.info("⏳ Задержка старта 1 сек...")
        time.sleep(1.0)
        
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
        
        for i, item_name in enumerate(items):
            if self._stop_requested: break
            
            while self._is_paused:
                if self._stop_requested: break
                time.sleep(0.1)
                
            # --- START INDEX LOGIC ---
            if i < self.start_index:
                # Тихо пропускаем, пока не дойдем до нужного
                continue
            
            self.progress_updated.emit(i + 1, total_items, item_name)
            self.logger.info(f"[{i+1}/{total_items}] Обработка: {item_name}")
            
            # --- SPLIT LOGIC (Black Market Switch) ---
            if self._is_black_market and i == 48:
                 self.logger.info("🌗 Достигнут предел (Item 48). Смена персонажа...")
                 if self._perform_character_switch(target_char_index=2):
                     self.logger.info("✅ Смена выполнена. Продолжаем...")
                     self._detect_current_city()
                     # Restore Sell Tab after switch
                     self._click_bm_sell_tab()
                 else:
                     self._stop_requested = True
                     break
                     
            try:
                self._process_item(item_name)
                self._first_item_processed = True
                
                # Сохраняем прогресс (чтобы можно было продолжить)
                # Сохраняем ИМЕННО ЭТОТ индекс как последний успешно обработанный
                self.config.set_setting("last_scan_index", i)
                
            except Exception as e:
                self.logger.error(f"Ошибка при обработке '{item_name}': {e}")
                
        self.logger.info("Цикл сканирования завершен")
        self._print_statistics()
        self._is_running = False
        self.finished.emit()

    def _process_item(self, name: str):
        """
        Логика обработки одного предмета.
        Разделяется на два флоу:
        1. Normal Market (Быстрый скан без открытия окна покупка)
        2. Black Market (Полный скан с вкладками и качеством)
        """
        if self._stop_requested: return
        
        # 0. Safety Check (Shared)
        market_found = False
        for attempt in range(10):
            if self._stop_requested: return
            self._check_pause()
            if self._check_market_is_open():
                market_found = True
                break
            else:
                self.logger.warning(f"⏳ Окно рынка не найдено... ({attempt+1}/10)")
                time.sleep(1.0)
                
        if not market_found:
            self.logger.error("🛑 Окно рынка не обнаружено!")
            self._stop_requested = True
            return

        self.logger.info(f"--- Начало обработки: {name} ---")
        
        self._consecutive_excellent_streak = 0
        self._current_item_name = name
        self._recovery_attempts = 0
        self._safe_menu_snapshot = None
        
        if self._is_black_market:
            self._process_item_black_market(name)
        else:
            self._process_item_normal_market(name)
            
        self.logger.info(f"--- Завершено: {name} ---")

    def _process_item_normal_market(self, name: str):
        """
        Новая логика для ОБЫЧНОГО рынка.
        Sequence:
        1. Clear/Search -> Enter
        2. Verify Name (Immediately)
        3. Reset Filters (No Quality)
        4. Scan Loop (No Quality)
        5. Finish (No Close)
        """
        # 1. Clear Search
        search_clear_coord = self.config.get_coordinate("search_clear")
        if search_clear_coord:
            self._human_move_to(*search_clear_coord)
            self._human_click()

        # 1.1 Reset Filters (BEFORE Search)
        # Сбрасываем фильтры на минимум (T4.0), чтобы при вводе имени предмет точно нашелся
        self._reset_filters()
            
        # 2. Search Input
        search_coord = self.config.get_coordinate("search_input")
        if not search_coord:
            self.logger.error("Нет координат поиска!")
            return
        
        self._human_move_to(*search_coord)
        self._human_click()
        
        self._human_type(name)
        pyautogui.press('enter')
        self.logger.debug("Нажат Enter. Ждем обновления списка...")
        time.sleep(1.0) # Даем время прогрузиться списку
        
        # 3. Varify Name (Immediately)
        # 3. Varify Name (Immediately)
        # allow_recovery_clicks -> use_buy_button=False (Разрешаем Sort, запрещаем Buy)
        if not self._verify_item_name_with_retry(name, max_retries=2, use_buy_button=False):
            self.logger.warning(f"⚠️ Предмет '{name}' не найден или имя не совпало!")
            return

        # 4. Filters already reset at step 1.1
        # self._reset_filters()
        
        # 5. Scan Loop (Item already selected implicitly by search result?)
        # Пользователь: "Все клики по энчантам и тирам происходят сразу после сканирования имени"
        self._scan_variations(initial_last_price=0)
        
        # 6. No Close Loop (User Request)
        # Просто переходим к следующему

    def _click_bm_sell_tab(self):
        """Клик по вкладке 'Продать' на Черном Рынке"""
        if not self._is_black_market: return
        
        sell_tab = self.config.get_coordinate("bm_sell_tab")
        if sell_tab:
            self.logger.info(f"👉 Clicking 'bm_sell_tab' (One-time) {sell_tab}")
            self._human_move_to(*sell_tab)
            self._human_click()
            time.sleep(random.uniform(0.3, 0.5))

    def _process_item_black_market(self, name: str):
        """
        Старая логика для ЧЕРНОГО рынка.
        (Без изменений, скопировано из старого _process_item)
        """
        if self._stop_requested: return

        # 1. Clear Search
        search_clear_coord = self.config.get_coordinate("search_clear")
        if search_clear_coord:
            self._human_move_to(*search_clear_coord)
            self._human_click()
            
        # 1.1 BM Sell Tab
        sell_tab = self.config.get_coordinate("bm_sell_tab")
        if sell_tab:
            self._human_move_to(*sell_tab)
            self._human_click()
            time.sleep(random.uniform(0.2, 0.4))
                
        # 2. Search Input
        search_coord = self.config.get_coordinate("search_input")
        if not search_coord: return
        
        self._human_move_to(*search_coord)
        self._human_click()
        
        self._human_type(name)
        pyautogui.press('enter')
        self.logger.debug("Нажат Enter...")
        
        # 4. Verify Name (Before Clicking Buy)
        # Мы проверяем найденный результат в списке, чтобы убедиться, что это тот предмет
        if not self._verify_item_name_with_retry(name, max_retries=2, use_buy_button=False):
            return
        
        # 4.1 Click Buy Button
        buy_coord = self.config.get_coordinate("buy_button")
        
        if buy_coord:
            time.sleep(0.5)
            self._human_move_to(*buy_coord)
            self._human_click()
            time.sleep(random.uniform(0.5, 0.8))
            
        # 4.1 Verify Name (IMMEDIATELY AFTER CLICK) - REMOVED (Moved up)
        # if not self._verify_item_name_with_retry(name):
        #    return
            
        # 5. Expand (First run)
        need_expand = True
        from ..utils.ocr import read_price_at
        area = self.config.get_coordinate_area("best_price_area")
        if area:
            p = read_price_at(area)
            if p and p > 0: need_expand = False
        
        if need_expand and not self._first_item_processed:
            expand_coord = self.config.get_coordinate("item_expand")
            if expand_coord:
                self._human_move_to(*expand_coord)
                self._human_click()
                time.sleep(0.5)

        # 5.1 BM Check logic (Should be redundants this IS BM function, bu at kept for legacy structure)
        # if not self._is_black_market: ... (Removed as we are in BM func)

        # 5.1 BM Check logic (Should be redundants this IS BM function, bu at kept for legacy structure)
        # if not self._is_black_market: ... (Removed as we are in BM func)
                
        self._capture_item_menu_state()
        
        # 6. Reset Filters
        self._reset_filters()
        self._scan_variations(initial_last_price=0)
        
        # 8. Close
        close_coord = self.config.get_coordinate("menu_close")
        if close_coord:
            self._human_move_to(*close_coord)
            self._human_click()
            time.sleep(0.3)

    def _capture_item_menu_state(self):
        """
        Захват текущего состояния валидационной области меню предмета.
        Используется для проверки 'Safe State' (чтобы убедиться, что меню не закрылось).
        """
        area = self.config.get_coordinate_area("item_menu_check")
        if not area:
            self._safe_menu_snapshot = None
            return

        from PIL import ImageGrab
        bbox = (area['x'], area['y'], area['x'] + area['w'], area['y'] + area['h'])
        self._safe_menu_snapshot = ImageGrab.grab(bbox=bbox)

    def _check_safe_state(self):
        """
        Проверка безопасности: гарантирует, что мы всё еще в меню предмета.
        Если проверка не проходит -> пытается восстановить состояние (Auto-Recovery).
        """
        if self._stop_requested: return
        if self._is_paused: return
        
        start_time = time.time()
        area = self.config.get_coordinate_area("item_menu_check")
        if not area:
            return
            
        # --- ПРОВЕРКА СОСТОЯНИЯ ---
        is_modified = False
        msg = ""

        # 1. Динамическая проверка (по снимку)
        if self._safe_menu_snapshot:
            from PIL import ImageGrab
            from ..utils.image_utils import find_image_on_screens
            
            bbox = (area['x'], area['y'], area['x'] + area['w'], area['y'] + area['h'])
            current_img = ImageGrab.grab(bbox=bbox)
            
            if self._safe_menu_snapshot.size != current_img.size:
                 current_img = current_img.resize(self._safe_menu_snapshot.size)

            rms = find_image_on_screens(self._safe_menu_snapshot, current_img)
            threshold = 30.0
            
            if rms > threshold:
                 is_modified = True
                 msg = f"RMS: {rms:.2f}"
        else:
            # 2. Статическая проверка (Fallback)
            from .validator import ScreenValidator
            is_modified_static, msg_static = ScreenValidator.check_item_menu(area)
            if not is_modified_static:
                 is_modified = True
                 msg = msg_static

        self._record_time("Валидация: Меню", (time.time() - start_time) * 1000)

        # Если все ОК -> выходим
        if not is_modified:
            return

        # --- AUTO-RECOVERY LOGIC ---
        self.logger.warning(f"⚠️ Меню предмета потеряно ({msg})! Попытка восстановления...")
        
        # 1. Проверяем счетчик попыток
        if self._recovery_attempts >= 3:
            self.logger.warning("⏸️ ПАУЗА: Превышено число попыток восстановления (3)!")
            self._is_paused = True
            return

        self._recovery_attempts += 1
        
        # 2. Проверяем, открыт ли рынок (Main Market)
        market_open = False
        wait_start = time.time()
        while time.time() - wait_start < 60.0:
            if self._stop_requested: return
            if self._check_market_is_open():
                market_open = True
                break
            self.logger.info("⏳ Ожидание открытия рынка... (Проверка каждую 1 сек)")
            time.sleep(1.0)
            
        if not market_open:
            self.logger.warning("⏸️ ПАУЗА: Рынок закрыт более 60 сек!")
            self._is_paused = True
            return
            
        # 3. Рынок открыт -> Пробуем открыть предмет заново
        buy_coord = self.config.get_coordinate("buy_button")
        if not buy_coord:
             self.logger.error("Нет координат кнопки Купить - восстановление невозможно")
             self._is_paused = True
             return
             
        self.logger.info("🔄 Восстановление: Нажимаю 'Купить'...")
        self._human_move_to(*buy_coord)
        self._human_click()
        time.sleep(1.0) # Ждем анимации
        
        # 4. Проверяем имя предмета (критично!)
        if not self._verify_item_name_with_retry(self._current_item_name, max_retries=1):
             self.logger.warning("⚠️ Имя предмета не совпало даже после 'Купить'. Запускаю ПОЛНЫЙ СБРОС ПОИСКА...")
             
             # --- FULL SEARCH RESET ---
             # 4.1. Очистка поиска
             search_clear = self.config.get_coordinate("search_clear")
             if search_clear:
                 self._human_move_to(*search_clear)
                 self._human_click()
                 time.sleep(0.3)
                 
             # 4.2. Клик в поле поиска
             search_input = self.config.get_coordinate("search_input")
             if search_input:
                 self._human_move_to(*search_input)
                 self._human_click()
                 
                 # 4.3. Ввод имени
                 self.logger.info(f"🔄 Повторный ввод имени: {self._current_item_name}")
                 self._human_type(self._current_item_name)
                 pyautogui.press('enter')
                 time.sleep(1.5) # Ждем прогрузки
             
             # 4.4. Ждем кнопку купить (обновление)
             self._wait_for_search_result(timeout=2.0)
             
             # 4.5. Клик Купить (Снова)
             self._human_move_to(*buy_coord)
             self._human_click()
             time.sleep(1.0)
             
             # 4.6. Финальная проверка
             if not self._verify_item_name_with_retry(self._current_item_name, max_retries=1):
                 self.logger.warning(f"⏸️ ПАУЗА: Восстановление не удалось - предмет не тот даже после сброса поиска!")
                 self._is_paused = True
                 return
             
        # 5. УСПЕХ -> Восстанавливаем состояние
        self.logger.info("✅ Предмет восстановлен! Возвращаю фильтры...")
        
        # Переключаем на "Заказ"
        if not self._is_black_market:
            order_tab = self.config.get_coordinate("create_buy_order")
            if order_tab:
                self._human_move_to(*order_tab)
                self._human_click()
                time.sleep(0.5)

        # Восстанавливаем Tier / Enchant
        if self._current_tier:
            # Сброс кэша чтобы метод реально кликнул
            saved_tier = self._current_tier
            self._current_tier = None 
            self._select_tier(saved_tier)
            
        if self._current_enchant is not None:
             saved_enchant = self._current_enchant
             self._current_enchant = None
             self._select_enchant(saved_enchant)
             
        # 6. Обновляем Snapshot
        self._capture_item_menu_state()
        self.logger.info("📸 Новый snapshot захвачен. Продолжаем работу.")

    def _is_item_menu_open(self) -> bool:
        """Проверка, что открыто меню конкретного предмета"""
        area = self.config.get_coordinate_area("item_menu_check")
        if not area: return False
        
        from .validator import ScreenValidator
        is_open, _ = ScreenValidator.check_item_menu(area)
        return is_open

    def _check_market_safe_state(self):
        
        if self._stop_requested: return
        if self._is_paused: return
        
        # 1. Сначала проверяем, открыт ли Сам Рынок (Заголовок)
        if self._check_market_is_open():
            return

        # 2. Если нет (заголовок не виден), проверяем, открыто ли Меню Предмета
        if self._is_item_menu_open():
            return

        # 3. Ничего не открыто -> Пауза
        self.logger.warning("⏸️ Рынок закрыт (и меню предмета не найдено)! Пауза.")
        self._is_paused = True

    def _reset_filters(self):
        """Сброс фильтров в базовое состояние (динамическое)"""
        filters = self.config.get_scan_filters()
        
        # 1. Tier
        tiers = filters.get("tiers", [])
        if not tiers: 
            target_tier = 4
        else:
            target_tier = min(tiers)
            
        # 2. Enchant
        enchants = filters.get("enchants", [])
        if not enchants:
            target_enchant = 0
        else:
            target_enchant = min(enchants)
            
        # 3. Quality
        qualities = filters.get("qualities", [])
        if not qualities:
            target_quality = 1
        else:
            target_quality = min(qualities)
            
        self.logger.info(f"Сброс фильтров в T{target_tier}.{target_enchant} Q{target_quality}")
        
        self._current_tier = None
        self._current_enchant = None
        self._current_quality = None
        self._last_detected_quality = None
        
        # Важно: Сначала Enchant, потом Tier, потом Quality
        self._select_enchant(target_enchant)
        self._select_tier(target_tier)
        
        # Quality: Кликаем только на ЧР или если режим не "Быстрый Скан" (для надежности)
        # Если мы на Normal Market (is_black_market=False), то пользователь просил УБРАТЬ клик качества
        if self._is_black_market:
             self._select_quality(target_quality, force=True)

    def _scan_variations(self, initial_last_price: int = 0):
        """Перебор вариантов согласно фильтрам сканирования."""
        if self._stop_requested: return
        
        filters = self.config.get_scan_filters()
        
        scanned_variants = set()
        last_price = initial_last_price

        # Локальный трекер цен для обнаружения коллизий: { "TX.Y": price }
        detected_prices = {}
        
        # Текущий энчант на экране (после reset_filters = 0)
        current_screen_enchant = 0
        
        # Determine Max Tier
        max_tier = 8
        if filters.get("tiers"):
            max_tier = max(filters["tiers"])
            
        enchants = filters.get("enchants", [0, 1, 2, 3, 4])
            
        # Iterate Tiers
        for tier in range(4, max_tier + 1):
             if self._stop_requested: return
             
             if filters.get("tiers") and tier not in filters["tiers"]:
                 continue
                 
             # Check Exceptions
             if self.config.is_tier_exception(tier, self._current_item_name):
                 self.logger.info(f"⏭️ Пропуск Tier {tier} (Исключение)")
                 continue
                 
             tier_changed = (self._current_tier != tier)
             self._select_tier(tier)
             
             # === OPPORTUNISTIC CAPTURE ===
             # Если Tier изменился и текущий энчант на экране входит в фильтры
             if tier_changed and current_screen_enchant in enchants:
                 # TODO: Add opportunistic logic here
                 key = f"T{tier}.{current_screen_enchant}"
                 
                 if key not in scanned_variants:
                     self.logger.info(f"📸 Opportunistic: {key}")
                     
                     # Wait for price
                     base_timeout = self.config.get_setting("price_update_timeout", 5.0)
                     timeout_val = (base_timeout + 1.0) if last_price == 0 else base_timeout
                     price = self._wait_for_price_update(last_price, timeout=timeout_val)
                     
                     if price > 0:
                         self.logger.info(f"💰 {self._current_item_name} {key}: {price}")
                         from ..utils.price_storage import price_storage
                         price_storage.save_price(
                             self._current_city, self._current_item_name,
                             tier, current_screen_enchant, 1, price
                         )
                         last_price = price
                     
                     scanned_variants.add(key)
             
             # Iterate Enchants
             for enchant in enchants:
                 if self._stop_requested: return
                 
                 # Если уже отсканировано (opportunistic) -> пропускаем
                 key = f"T{tier}.{enchant}"
                 if key in scanned_variants: continue

                 self._select_enchant(enchant)
                 current_screen_enchant = enchant # Обновляем состояние
                 
                 # Quality Click: ТОЛЬКО ДЛЯ ЧР (или если старый режим)
                 if self._is_black_market:
                     self._select_quality(1)
                 
                 # READ PRICE
                 base_timeout = self.config.get_setting("price_update_timeout", 5.0)
                 timeout_val = 2.0 if last_price == 0 else base_timeout
                 price = self._wait_for_price_update(last_price, timeout=timeout_val)
                 
                 # Save
                 if price > 0:
                     self.logger.info(f"💰 {self._current_item_name} {key}: {price}")
                     from ..utils.price_storage import price_storage
                     price_storage.save_price(
                         self._current_city,
                         self._current_item_name,
                         tier,
                         enchant,
                         1, # Quality
                         price
                     )
                     last_price = price
                     
                     # --- TRACKING ---
                     detected_prices[key] = price
                     
                     # --- STUCK PRICE CHECK (T4.0) - REMOVED (Replaced by Collision Check) ---

                     
                 scanned_variants.add(key)
                 
        # === POST-SCAN ANALYSIS (Collision Check) ===
        self._verify_price_collisions(detected_prices)
                 
    # === Helper Selectors ===
    
    def _calculate_bm_tier_index(self, tier: int) -> int:
        """
        Рассчитывает индекс клика в выпадающем списке тиров для Черного Рынка.
        Логика:
        1. "Обычные" предметы начинаются с T4 (min_tier=4).
        2. "Исключения" (в списках tier_exceptions) могут начинаться с T1, T2, T3.
        """
        min_tier = 4 # Default for standard items (T4-T8)
        
        # Проверяем наличие в списках исключений (снизу вверх)
        # Если предмет есть в Tier_1 -> min_tier = 1
        # Если нет, проверяем Tier_2 -> min_tier = 2
        # И так далее.
        
        if self.config.is_tier_exception(1, self._current_item_name):
            min_tier = 1
        elif self.config.is_tier_exception(2, self._current_item_name):
            min_tier = 2
        elif self.config.is_tier_exception(3, self._current_item_name):
            min_tier = 3
            
        # DEBUG LOG
        # self.logger.info(f"DEBUG: BM Tier Calc: Item='{self._current_item_name}' TargetT={tier} MinTier={min_tier}")
        
        return tier - min_tier

    def _select_tier(self, tier: int):
        if self._current_tier == tier: return
        
        # Передаем только tier, так как метод в interaction.py не принимает другие аргументы
        if self._is_black_market:
            # BM override: use separate coordinate for dropdown open
            dropdown_pos = self.config.get_coordinate("bm_tier_dropdown")
            if dropdown_pos:
                self.logger.info(f"👉 Clicking 'bm_tier_dropdown' {dropdown_pos}")
                self._human_move_to(*dropdown_pos)
                self._human_click()
                time.sleep(random.uniform(0.2, 0.3))
                pass
            else:
                 self.logger.warning("No BM Tier Dropdown coordinate!")

            
            # Use the calculated point for the ITEM
            # Dynamic calculation based on item properties
            bm_index = self._calculate_bm_tier_index(tier)
            
            # Additional check: If index < 0, fallback to standard T4-based logic?
            # Or trust the config.
            if bm_index < 0:
                self.logger.warning(f"⚠️ BM Tier Index < 0 ({bm_index}) for T{tier}. Config might be wrong.")
                return

            coord = self.dropdowns.get_dropdown_click_point("bm_tier_dropdown", bm_index)
            if coord:
                self.logger.info(f"👉 Clicking 'BM Dropdown Item T{tier}' (Idx {bm_index}) {coord}")
                self._human_move_to(*coord)
                self._human_click()
                self._current_tier = tier
                self._current_quality = None
                time.sleep(random.uniform(0.1, 0.2))
            return

        # Standard Market
        coord = self.dropdowns.get_tier_click_point(tier)
        if coord:
            self.dropdowns.open_tier_menu(self)
            self._human_move_to(*coord)
            self._human_click()
            self._current_tier = tier
            self._current_quality = None # Сброс подтвержденного качества (игра может поменять выбор)
            time.sleep(random.uniform(0.1, 0.2))

    def _select_enchant(self, enchant: int):
        if self._current_enchant == enchant: return
        
        if self._is_black_market:
             # BM override
            dropdown_pos = self.config.get_coordinate("bm_enchant_dropdown")
            if dropdown_pos:
                self.logger.info(f"👉 Clicking 'bm_enchant_dropdown' {dropdown_pos}")
                self._human_move_to(*dropdown_pos)
                self._human_click()
                time.sleep(random.uniform(0.2, 0.3))
                
                # Click item
                # Logic from DropdownSelector.get_enchant_click_point: index = enchant + 1 (Skip "All")
                # For BM: If no "All", index = enchant
                coord = self.dropdowns.get_dropdown_click_point("bm_enchant_dropdown", enchant)
                
                if coord:
                    self.logger.info(f"👉 Clicking 'BM Dropdown Item E{enchant}' {coord}")
                    self._human_move_to(*coord)
                    self._human_click()
                    self._current_enchant = enchant
                    self._current_quality = None
                    time.sleep(random.uniform(0.1, 0.2))
            return
            
        # Standard Market
        coord = self.dropdowns.get_enchant_click_point(enchant)
        if coord:
            self.dropdowns.open_enchant_menu(self)
            self._human_move_to(*coord)
            self._human_click()
            self._current_enchant = enchant
            self._current_quality = None # Сброс подтвержденного качества
            time.sleep(random.uniform(0.1, 0.2))

    def _select_quality(self, quality: int, force: bool = False) -> bool:
        """
        Выбрать качество с проверкой OCR и эвристикой.
        
        Args:
            quality: Целевое качество (1-5)
            force: Если True, пропустить оптимизации и всегда кликать по дропдауну
        """
        # === BLACK MARKET OPTIMIZATION ===
        # На Черном Рынке качество ВСЕГДА "Normal" (1), проверка не нужна
        if self._is_black_market:
            self._current_quality = 1
            return True
        
        # === NORMAL MARKET OPTIMIZATION ===
        # Проверка качества нужна только для T7/T8 с зачарованиями (enchant > 0)
        # Для T4-T6 и T7/T8.0 качество можно оставить по умолчанию
        # НО: при force=True (сброс фильтров) всегда кликаем
        if not force:
            current_tier = self._current_tier or 4
            current_enchant = self._current_enchant or 0
            needs_quality_check = (current_tier >= 7 and current_enchant > 0)
            
            if not needs_quality_check:
                self._current_quality = quality
                return True
        
        # Если состояние уже верное (и мы в нем уверены)
        if self._current_quality == quality:
            self._consecutive_excellent_streak = 0 # Сброс стрика
            return True
            
        anchor = self.config.get_coordinate("quality_dropdown")
        if not anchor: return False

        # Маппинг качеств (Rus + Eng)
        quality_map = {
            1: ["Обычное", "Normal"],
            2: ["Хорошее", "Good"],
            3: ["Выдающееся", "Outstanding"],
            4: ["Отличное", "Excellent"],
            5: ["Шедевр", "Masterpiece"]
        }
        expected_names = quality_map.get(quality, [])
        
        # Обратный маппинг: текст -> число
        reverse_quality_map = {
            "Обычное": 1, "Normal": 1,
            "Хорошее": 2, "Good": 2,
            "Выдающееся": 3, "Outstanding": 3,
            "Отличное": 4, "Excellent": 4,
            "Шедевр": 5, "Masterpiece": 5
        }
        
        # Получаем допустимые качества из фильтров
        allowed_qualities = self.config.get_scan_filters().get('qualities', [])

        from ..utils.ocr import read_screen_text, is_ocr_available, fuzzy_match_quality
        
        # --- 0. ПАССИВНАЯ ПРОВЕРКА (ЭВРИСТИКА) ---
        if is_ocr_available():
            area = self.config.get_coordinate_area("quality_text_region")
            if area:
                try:
                    passive_text = read_screen_text(area['x'], area['y'], area['w'], area['h'])
                    self.logger.info(f"DEBUG: OCR Quality Text='{passive_text}' Expected={expected_names}")
                    
                    # 1. Совпадение (Уже стоит то, что нужно)
                    if fuzzy_match_quality(passive_text, expected_names):
                        self.logger.info(f"Пассивная проверка OK: '{passive_text}'")
                        self._current_quality = quality
                        self._last_detected_quality = passive_text
                        return True
                    
                    # 2. Проверка: качество допустимо (в списке фильтров)?
                    detected_quality_id = None
                    for name, qid in reverse_quality_map.items():
                        if fuzzy_match_quality(passive_text, [name]):
                            detected_quality_id = qid
                            break
                    
                    if detected_quality_id is not None and detected_quality_id in allowed_qualities:
                        # Качество допустимо -> не меняем
                        self.logger.info(f"Качество '{passive_text}' допустимо (Q{detected_quality_id}). Принимаем.")
                        self._current_quality = detected_quality_id
                        self._last_detected_quality = passive_text
                        return True
                    
                    # 3. Качество не допустимо -> Анализ
                    self.logger.debug(f"Пассивная проверка: '{passive_text}' != {expected_names}")
                    
                    # Проверяем: качество ИЗМЕНИЛОСЬ САМО (игра форсирует) или осталось тем же (унаследовано)?
                    quality_changed_by_game = (
                        self._last_detected_quality is not None and
                        passive_text != self._last_detected_quality
                    )
                    
                    # Запоминаем текущее для следующей проверки
                    self._last_detected_quality = passive_text
                    
                    if quality_changed_by_game:
                        # Качество изменилось само -> игра форсирует -> пропускаем
                        self.logger.warning(f"Игра форсирует '{passive_text}'. Пропускаем.")
                        return False
                    else:
                        # Качество не изменилось (унаследовано) -> пробуем переключить
                        self.logger.info(f"Качество '{passive_text}' унаследовано. Пробуем переключить.")

                except Exception as e:
                    self.logger.warning(f"Ошибка OCR: {e}")
            else:
                self.logger.warning("DEBUG: 'quality_text_region' not found in config.")
        else:
            self.logger.warning("DEBUG: OCR unavailable.")

        # --- АКТИВНЫЙ ВЫБОР (КЛИК) ---
        for attempt in range(2):
            if self._stop_requested: return False
            
            self.logger.debug(f"Выбор качества: {quality} (Попытка {attempt+1})")
            
            self._human_move_to(*anchor)
            self._human_click()
            time.sleep(random.uniform(0.3, 0.4))
            
            point = self.dropdowns.get_quality_click_point(quality)
            if point:
                 self._human_move_to(*point)
                 self._human_click()
                 time.sleep(random.uniform(0.5, 0.7))
            
            # Проверка результата
            if is_ocr_available() and area:
                text = read_screen_text(area['x'], area['y'], area['w'], area['h'])
                if fuzzy_match_quality(text, expected_names):
                    self._current_quality = quality
                    self.logger.info(f"Качество выбрано успешно: {text}")
                    self._consecutive_excellent_streak = 0 # Победа, сброс
                    return True
                else:
                     self.logger.warning(f"Не удалось выбрать (OCR: {text})")
                     self._current_quality = None
                     time.sleep(0.5)
            else:
                 self._current_quality = quality
                 return True # OCR недоступен, верим
        
        self.logger.error(f"Не удалось выбрать качество {quality} после попыток")
        return False
            
    def _perform_character_switch(self, target_char_index: int) -> bool:
        """
        Логика смены персонажа (Scanner Specific)
        Sequence: Settings -> Logout -> Wait 11s -> Select 2nd Char -> Login -> Wait 1s -> Open Market Loop
        """
        self.logger.info("🔄 Запуск процедуры смены персонажа...")
        
        # HIDE OVERLAY
        self.overlay_status.emit(False)
        
        # 1. Logout Sequence
        settings_btn = self.config.get_coordinate("bm_settings_btn")
        if not settings_btn:
             self.logger.error("Нет координат 'bm_settings_btn'!")
             self.overlay_status.emit(True) # Restore
             return False
             
        logout_btn = self.config.get_coordinate("bm_logout_btn")
        if not logout_btn:
             self.logger.error("Нет координат 'bm_logout_btn'!")
             self.overlay_status.emit(True) # Restore
             return False
             
        # Click Settings
        self._human_move_to(*settings_btn)
        self._human_click()
        time.sleep(1.0)
        
        # Click Logout
        self._human_move_to(*logout_btn)
        self._human_click()
        self.logger.info("⏳ Ожидание выхода из игры (11 сек)...")
        time.sleep(11.0)
        
        # 2. Select Character
        # Note: target_char_index arg is unused, we strictly use 'bm_char2_area' config per user request
        char_area = self.config.get_coordinate_area("bm_char2_area")
        if not char_area:
             self.logger.error("Нет координат 'bm_char2_area' (Area)!")
             self.overlay_status.emit(True)
             return False
        
        # Calculate center for clicking
        char_icon_click = (char_area['x'] + char_area['w']//2, char_area['y'] + char_area['h']//2)
        
        # --- Visual Check Loop (Template Match) ---
        self.logger.info("Поиск Аватара 2-го персонажа (Template Finding)...")
        
        from ..utils.paths import get_app_root
        from ..utils.image_utils import find_image_on_screen
        
        ref_path = get_app_root() / "resources" / "ref_bm_char2_area.png"
        if not os.path.exists(ref_path):
            self.logger.error(f"❌ Нет эталона: {ref_path}. Невозможно найти персонажа!")
            if not self.config.get_coordinate("bm_char2_area"): 
                 return False
            self.logger.warning("Пробуем кликнуть по старой координате (Fallback)...")
            char_icon_click = self.config.get_coordinate("bm_char2_area")
        else:
            # Loop check
            found_point = None
            
            for attempt in range(15): # 15 seconds wait max
                if self._stop_requested: return False
                
                # Ищем по всему экрану (region=None)
                # confidence=0.85 (нужен opencv, иначе fallback на tochnoe)
                found_point = find_image_on_screen(ref_path, confidence=0.85)
                
                if found_point:
                    self.logger.info(f"✅ Аватар найден в {found_point}!")
                    break
                    
                time.sleep(1.0)
                
            if not found_point:
                self.logger.error("❌ Аватар 2-го персонажа не найден на экране (Таймаут)!")
                self.overlay_status.emit(True)
                return False
                
            char_icon_click = found_point

        # Клик по иконке персонажа
        self.logger.info("Выбор 2-го персонажа...")
        self._human_move_to(*char_icon_click)
        self._human_click()
        time.sleep(1.0)
        
        # 3. Login
        login_btn = self.config.get_coordinate("bm_login_btn")
        if not login_btn:
             self.logger.error("Нет координат 'bm_login_btn'!")
             return False
             
        self.logger.info("Вход в игру...")
        self._human_move_to(*login_btn)
        self._human_click()
        
        self.logger.info("⏳ Быстрое ожидание прогрузки (1 сек)...")
        time.sleep(1.0)
        
        # 4. Re-open Market Loop
        return self._wait_for_market_reopen()

    def _wait_for_market_reopen(self) -> bool:
        """
        Цикл открытия рынка: Кликаем NPC раз в секунду, пока рынок не откроется.
        """
        npc_coord = self.config.get_coordinate("bm_open_market_btn")
        if not npc_coord:
             self.logger.error("Нет координат 'bm_open_market_btn'!")
             return False
             
        self.logger.info("🔄 Ожидание открытия рынка (Клик по NPC)...")
        
        max_attempts = 60 # 60 секунд попыток (можно увеличить)
        
        for i in range(max_attempts):
            if self._stop_requested: return False
            self._check_pause()
            
            # 1. Проверка: Уже открыт?
            if self._check_market_is_open():
                self.logger.info("✅ Рынок успешно открыт!")
                time.sleep(1.0) # Даем прогрузиться интерфейсу
                return True
                
            # 2. Клик по NPC
            self._human_move_to(*npc_coord)
            self._human_click()
            
            # 3. Ждем секунду
            time.sleep(1.0)
            
        self.logger.error("❌ Не удалось открыть рынок за 60 секунд!")
        return False
        
    def _wait_for_search_result(self, timeout: float = 15.0, initial_pixels=None):
         # Helper moved from BaseBot but heavily used here? 
         # Wait, I put it as instance method in BaseBot? No, I likely didn't include it in BaseBot 
         # because it uses `initial_pixels` logic specific to search UI.
         # So I keep it here.
        from PIL import ImageGrab
        import time
        
        buy_coord = self.config.get_coordinate("buy_button")
        if not buy_coord:
            time.sleep(0.5)
            return
        
        x, y = buy_coord
        check_area = (x - 30, y - 10, x + 30, y + 10)
        
        if initial_pixels is None:
             initial_screenshot = ImageGrab.grab(bbox=check_area)
             initial_pixels = list(initial_screenshot.getdata())
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._stop_requested: return
            self._check_pause()
            time.sleep(0.1)
            current_screenshot = ImageGrab.grab(bbox=check_area)
            if list(current_screenshot.getdata()) != initial_pixels:
                return
        self.logger.debug("Таймаут поиска")

    def _wait_for_price_update(self, old_price: int, timeout: float = 3.0) -> int:
        """
        Ждет, пока цена визуально изменится по сравнению с old_price.
        Если цена исчезает (None) -> продолжаем ждать (загрузка).
        Если цена равна старой -> продолжаем ждать (лаг).
        Если тайм-аут -> возвращаем 0.
        """
        start_time = time.time()
        
        # Select Area Key based on Mode
        area_key = "best_price_area"
        if self._is_black_market:
            area_key = "bm_price_area"
            
        area = self.config.get_coordinate_area(area_key)
        
        # Fallback for safe transition
        if not area and self._is_black_market:
             area = self.config.get_coordinate_area("best_price_area")
             
        if not area:
            self.logger.error(f"Не задана область цены '{area_key}'!")
            return 0
            
        from ..utils.ocr import read_price_at

        empty_read_count = 0
        max_empty_reads = 5
        
        while time.time() - start_time < timeout:
            if self._stop_requested: return 0
            self._check_pause()
            
            # Считываем цену
            try:
                price = read_price_at(area)
            except Exception:
                price = None
            
            # 1. Если цена None (не распозналась или пусто) -> Ждем
            if price is None:
                empty_read_count += 1
                if empty_read_count >= max_empty_reads:
                    self.logger.debug(f"⚠️ Цена не обнаружена после {max_empty_reads} попыток. Считаем, что лота нет.")
                    return 0
                    
                time.sleep(0.1)
                continue
            
            # Сброс счетчика, если что-то распознали
            empty_read_count = 0
                
            # 2. Если цена новая -> УСПЕХ
            if price != old_price and price > 0:
                # self.logger.debug(f"✅ Цена обновилась: {old_price} -> {price}")
                return price
                
            # 3. Если цена совпадает со старой
            if price == old_price:
                time.sleep(0.1)
                continue
            
        # 4. Таймаут
        # self.logger.warning(f"⏰ Таймаут ожидания цены! (Old: {old_price}). Возвращаем 0.")
        return 0

    def _print_statistics(self):
        """Вывод статистики времени в логи"""
        if not self._action_timings:
            self.logger.info("Нет статистики действий.")
            return
            
        self.logger.info("📊 СТАТИСТИКА ВРЕМЕНИ:")
        self.logger.info("─" * 60)
        self.logger.info(f"{'Действие':<25} {'Всего':<12} {'Кол-во':<8} {'Среднее':<10}")
        self.logger.info("─" * 60)
        
        # Сортируем по общему времени (убывание)
        sorted_actions = sorted(
            self._action_timings.items(),
            key=lambda x: x[1]["total_ms"],
            reverse=True
        )
        
        total_time = 0.0
        for action, stats in sorted_actions:
            total_ms = stats["total_ms"]
            count = stats["count"]
            avg_ms = total_ms / count if count > 0 else 0
            total_time += total_ms
            
            # Форматирование
            if total_ms >= 1000:
                total_str = f"{total_ms/1000:.2f} сек"
            else:
                total_str = f"{total_ms:.0f} мс"
                
            if avg_ms >= 1000:
                avg_str = f"{avg_ms/1000:.2f} сек"
            else:
                avg_str = f"{avg_ms:.0f} мс"
                
            self.logger.info(f"{action:<25} {total_str:<12} {count:<8} {avg_str:<10}")
        
        self.logger.info("─" * 60)
        self.logger.info(f"{'ИТОГО':<25} {total_time/1000:.2f} сек")
        self.logger.info("─" * 60)
        
        if self._suspicious_reports:
             self.logger.warning("\n⚠️ ОТЧЕТ О ПОДОЗРИТЕЛЬНЫХ ПРЕДМЕТАХ (COLLISIONS):")
             self.logger.warning("Возможно, цены не обновились корректно для:")
             for item, variants, price in self._suspicious_reports:
                 self.logger.warning(f"  • {item}: {variants} (Цена: {price})")
        
        self.logger.info("Сканирование завершено.")

    def _verify_price_collisions(self, prices_map: dict):
        """
        Проверка на коллизии цен (одинаковая цена у разных тиров/энчантов).
        Если обнаружено -> Re-scan.
        """
        # 1. Invert map: price -> [variants]
        price_groups = {}
        for variant, price in prices_map.items():
            if price <= 0: continue
            if price not in price_groups:
                price_groups[price] = []
            price_groups[price].append(variant)
            
        # 2. Find collisions
        collisions = {p: v for p, v in price_groups.items() if len(v) > 1}
        
        if not collisions:
            return

        self.logger.warning(f"⚠️ Обнаружены коллизии цен для '{self._current_item_name}':")
        
        # 3. Process collisions
        for price, variants in collisions.items():
            self.logger.warning(f"  💰 Цена {price} у вариантов: {variants}. Запуск перепроверки...")
            
            # Re-scan loop
            confirmed_variants = []
            
            for variant_key in variants:
                if self._stop_requested: return
                
                # Parse Key "T{tier}.{enchant}"
                try:
                    t_str, e_str = variant_key.replace("T", "").split(".")
                    tier = int(t_str)
                    enchant = int(e_str)
                except ValueError:
                    continue
                    
                self.logger.info(f"🔄 Re-verifying {variant_key}...")
                
                # Select
                self._select_tier(tier)
                self._select_enchant(enchant)
                self._select_quality(1)
                
                # Wait & Read
                # Force wait full timeout to be sure
                time.sleep(0.5) 
                base_timeout = self.config.get_setting("price_update_timeout", 5.0)
                # Передаем last_price=0, чтобы не "схватить" старую цену моментально, 
                # а честно подождать если она такая же (но мы надеемся что изменится)
                # Хотя стоп, если она РЕАЛЬНО такая же, мы будем ждать 5 сек зря?
                # Нет, мы хотим убедиться. Лучше подождать.
                
                new_price = self._wait_for_price_update(0, timeout=base_timeout)
                
                if new_price > 0:
                     # Update storage if changed (or confirmed)
                     # (price_storage handles updates)
                     from ..utils.price_storage import price_storage
                     price_storage.save_price(
                         self._current_city, self._current_item_name,
                         tier, enchant, 1, new_price
                     )
                     
                     if new_price != price:
                         self.logger.info(f"✅ Цена исправлена: {variant_key} {price} -> {new_price}")
                     else:
                         self.logger.info(f"ℹ️ Цена подтверждена: {variant_key} {new_price}")
                         confirmed_variants.append(variant_key)
                else:
                     self.logger.warning(f"❌ Не удалось получить цену при перепроверке {variant_key}")
            
            # 4. Final Report Check
            # Если после перепроверки у нас все еще есть группа с одинаковой ценой > 1
            if len(confirmed_variants) > 1:
                self._suspicious_reports.append((self._current_item_name, confirmed_variants, price))


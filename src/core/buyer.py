"""
Логика закупки (Buyer Mode)
Автоматическая покупка предметов на основе конфигурации и цен.
"""

import time
import random
import pyautogui
from .base_bot import BaseBot
from .interaction import DropdownSelector
from ..utils.price_storage import price_storage

class BuyerBot(BaseBot):
    """
    Режим покупателя (Buyer Mode)
    Поддерживает режимы:
    1. wholesale (Опт): Работает по списку из конфига.
    2. smart (Умный): Работает по таблице профитов с батчами.
    """
    
    def __init__(self):
        super().__init__()
        self.dropdowns = DropdownSelector()
        self._items_to_buy = [] # Список задач [(name, tier, enchant, limit)]
        self.simulation_mode = True # По умолчанию True для безопасности
        self.manual_confirm_mode = False # Debug F1/F2 mode
        self.simulation_mode = True # По умолчанию True для безопасности
        self.manual_confirm_mode = False # Debug F1/F2 mode
        self.mode = "wholesale" # wholesale | smart
        self._is_menu_open = False # State tracking for optimization
        self._current_tier_value = None # State for tier skip optimization
        
        # Current Item State (Context for specific tier logic)
        self._current_item_name = None
        self._current_enchant = 0
        
    def run(self):
        """Основной цикл закупки"""
        self._is_running = True
        self._stop_requested = False
        self._is_paused = False
        
        self.logger.info(f"💰 ЗАПУСК РЕЖИМА: ОПТ (Orders) 💰")
        self.logger.info("⏳ Задержка старта 1 сек...")
        time.sleep(1.0)
        
        self._detect_current_city()
        
        self._detect_current_city()
        
        if self.mode == "smart":
            self._run_smart_buyer()
        else:
            self._run_wholesale()
            
        self.logger.info("🏁 Закупка завершена.")
        self._is_running = False
        self.finished.emit()

    def _run_wholesale(self):
        """Логика ОПТОВОЙ закупки (по лимитам из конфига)"""
        # 1. Собираем список
        self._build_purchase_list()
        
        total_tasks = len(self._items_to_buy)
        if total_tasks == 0:
            self.logger.warning("Нет активных задач на закупку! (Проверьте лимиты в 'План закупки')")
            return
            
        self.logger.info(f"Найдено {total_tasks} позиций для проверки.")
        if self.simulation_mode:
            self.logger.warning("💊 РЕЖИМ СИМУЛЯЦИИ: Деньги не будут потрачены.")
            
        # 2. Группируем
        tasks_by_item = {}
        for name, tier, enchant, limit in self._items_to_buy:
             if name not in tasks_by_item: tasks_by_item[name] = []
             tasks_by_item[name].append((tier, enchant, limit))
             
        processed_count = 0
        
        for item_name, variants in tasks_by_item.items():
            if self._stop_requested: break
            self._check_pause()
            
            self.logger.info(f"🔎 Проверка предмета: {item_name} ({len(variants)} вариаций)")
            
            try:
                if not self._search_item_and_open(item_name):
                    self.logger.warning(f"❌ Не удалось открыть предмет: {item_name}")
                    continue
                
                # ПЕРЕД циклом вариаций переходим на вкладку "Заказ" ОДИН РАЗ
                if not self._is_black_market:
                     buy_order_tab = self.config.get_coordinate("create_buy_order") 
                     if buy_order_tab:
                        self.logger.info("📑 Переход на вкладку 'Создать заказ'")
                        self._human_move_to(*buy_order_tab)
                        self._human_click()
                        time.sleep(0.5)

                for tier, enchant, limit in variants:
                    if self._stop_requested: break
                    processed_count += 1
                    self.progress_updated.emit(processed_count, total_tasks, f"{item_name} T{tier}.{enchant}")
                    
                    self._process_variant_wholesale(item_name, tier, enchant, limit)
                    
                self._close_menu()
                
            except Exception as e:
                self.logger.error(f"Ошибка при обработке {item_name}: {e}")
                self._close_menu()

    def _run_smart_buyer(self):
        """
        Логика УМНОГО закупщика (Smart Batch).
        - Берет самые выгодные предметы из сканирования.
        - Если предмета нет в конфиге -> покупает по 10 шт (DEFAULT_BATCH).
        - Если есть в конфиге -> уважает лимит конфига.
        """
        DEFAULT_BATCH = 10
        
        # 1. Получаем список выгодных (sorted by profit)
        items_to_check = self._get_profitable_items_sorted()
        total_items = len(items_to_check)
        
        if total_items == 0:
            self.logger.warning("Нет подходящих предметов! (Сначала запустите Сканер или цены ЧР отсутствуют)")
            return

        self.logger.info(f"🧠 SMART: Найдено {total_items} выгодных предметов.")
        
        # 2. Итерация
        processed_count = 0
        
        # Чтобы не покупать миллион раз одно и то же, запоминаем что купили?
        # Пока просто идем по списку.
        
        for i, (item_name, tier, enchant, profit_est, market_price) in enumerate(items_to_check):
            if self._stop_requested: break
            self._check_pause()
            
            processed_count += 1 
            self.progress_updated.emit(processed_count, total_items, f"{item_name} (+{int(profit_est)} s.)")
            
            # 3. Определяем лимит (Batch)
            # Пробуем найти лимит в конфиге
            config_limit = 0
            try:
                # get_wholesale_limit returns (min_price, max_price, limit) -> Wait, method signature?
                # config.get_wholesale_limit(item, t, e) -> returns (min_profit, max_quantity, step_qty?) 
                # Let's check config.py... actually get_wholesale_limit usually returns profit percent.
                # Let's check existing usage: "_, _, min_profit_percent = self.config.get_wholesale_limit..."
                
                # We need separate check for configured LIMIT in 'wholesale_targets'
                targets = self.config.get_wholesale_targets()
                variant_key = f"T{tier}.{enchant}"
                
                if item_name in targets and variant_key in targets[item_name]:
                    data = targets[item_name][variant_key]
                    if data.get("enabled", False):
                        config_limit = data.get("limit", 0)
            except: pass
            
            final_limit = config_limit if config_limit > 0 else DEFAULT_BATCH
            
            self.logger.info(f"🧠 Smart Item: {item_name} T{tier}.{enchant} | Profit: {int(profit_est)} | Limit: {final_limit} {'(Config)' if config_limit > 0 else '(Default)'}")
            
            # 4. Выполняем закупку (Reusing Wholesale Logic)
            try:
                # Открываем предмет
                if not self._search_item_and_open(item_name):
                    continue
                
                # Переход на вкладку Заказа
                if not self._is_black_market:
                     buy_order_tab = self.config.get_coordinate("create_buy_order") 
                     if buy_order_tab:
                         # self._human_move_to... wait, wholesale logic does this ONCE per item group.
                         # Here we do it per item. OK.
                        self._human_move_to(*buy_order_tab)
                        self._human_click()
                        time.sleep(0.5)

                # Запускаем процессор вариации
                self._process_variant_wholesale(item_name, tier, enchant, final_limit)
                
                self._close_menu()
                
            except Exception as e:
                self.logger.error(f"Error smart loop: {e}")
                self._close_menu()
                
    def _get_profitable_items_sorted(self):
        """
        Возвращает список [(name, tier, enchant, profit, market_price), ...]
        отсортированный по profit (desc).
        """
        if not self._current_city:
            self.logger.warning("Город не определен, сортировка невозможна.")
            return []
            
        items = [] 
        city_prices = price_storage.get_city_prices(self._current_city)
        bm_prices = price_storage.get_city_prices("Black Market")
        
        if not city_prices or not bm_prices: return []
            
        for item_name, variants in city_prices.items():
            if item_name not in bm_prices: continue
            
            bm_variants = bm_prices[item_name]
            
            for key, data in variants.items():
                market_price = data.get("price", 0)
                if market_price <= 0: continue
                
                # Ищем пару на ЧР
                if key not in bm_variants: continue
                bm_price = bm_variants[key].get("price", 0)
                if bm_price <= 0: continue
                
                try:
                    t_str, e_str = key.replace("T", "").split(".")
                    tier = int(t_str)
                    enchant = int(e_str)
                    
                    # Profit Calc (Tax 6.5%)
                    # Profit = (BM * 0.935) - Market
                    net_bm = bm_price * 0.935
                    profit = net_bm - market_price
                    
                    # Basic filters
                    if profit > 500: # Min safe profit hardcoded
                        items.append((item_name, tier, enchant, profit, market_price))
                        
                except Exception: continue
                    
        # Sort DESC
        items.sort(key=lambda x: x[3], reverse=True)
        return items



    def _process_variant_wholesale(self, item_name, tier, enchant, limit):
        """
        Обработка одной вариации товара (ОПТ).
        Цикл покупки пока лимит не исчерпан.
        """
        remaining_limit = limit
        consecutive_errors = 0
        
        # Получаем цену ЧР (Она статична для сессии)
        bm_price = price_storage.get_item_price("Black Market", item_name, tier, enchant, 1)
        if not bm_price:
            self.logger.warning(f"⏩ Пропуск {item_name} T{tier}.{enchant}: Нет цены ЧР")
            return

        # Основной цикл покупки (пока нужен товар)
        while remaining_limit > 0:
            if self._stop_requested: break
            self._check_pause()
            
            if consecutive_errors >= 3:
                self.logger.error("🛑 Слишком много ошибок подряд. Пропуск вариации.")
                break

            self.logger.info(f"📦 Обработка: T{tier}.{enchant} | Осталось купить: {remaining_limit}")
            
            # 0. Открываем меню (если закрыто)
            if not self._is_menu_open:
                buy_btn = self.config.get_coordinate("buy_button")
                if buy_btn:
                    self._human_move_to(*buy_btn)
                    self._human_click()
                    self._is_menu_open = True
                    self._current_tier_value = None # Reset tier state on new menu
                    self._current_enchant = 0 # Reset enchant state on new menu
                    time.sleep(1.0) # Wait for animation
                else:
                    self.logger.error("❌ Нет координаты кнопки Купить!")
                    break
            
            # 1. Установка параметров (Tier -> Enchant)
            self._current_item_name = item_name
            # self._current_enchant SHOULD track actual screen state, do not overwrite with target here!
            
            if self._current_tier_value != tier:
                self._select_tier(tier) 
                self._current_tier_value = tier
            
            self._select_enchant(enchant)
            self._select_quality(1) # Всегда Normal
            
            # 2. Анализ цены (OCR)
            from ..utils.ocr import read_price_at
            
            price_area = self.config.get_coordinate_area("buyer_top_lot_price")
            if not price_area:
                 price_area = self.config.get_coordinate_area("best_price_area")
            
            if not price_area:
                self.logger.error("❌ Не задана зона чтения цены (buyer_top_lot_price)")
                break
                
            current_price = read_price_at(price_area)
            
            if current_price is None:
                self.logger.warning(f"⚠️ Ошибка чтения цены (None).")
                consecutive_errors += 1
                self._close_menu()
                time.sleep(1)
                continue
                
            # If price is 0, we assume market is empty or OCR failed but it's SAFE to place a BUY order at Target.
            if current_price == 0:
                 self.logger.info("⚠️ Цена 0 (Пусто/Ошибка). Пробуем выставить ордер (Safe).")
            
            # 3. Расчет цены покупки (Target)
            # Formula: (BM * 0.935) / (1.025 * (1 + Margin))
            bm_price = price_storage.get_item_price("Black Market", item_name, tier, enchant, 1)
            
            if bm_price <= 0:
                self.logger.warning(f"⚠️ Нет цены ЧР для {item_name} T{tier}.{enchant}. Пропуск.")
                self._close_menu()
                break # Нет смысла продолжать, если нет цены
            
            # Get Min Profit % from config
            _, _, min_profit_percent = self.config.get_wholesale_limit(item_name, tier, enchant)
            
            # Factors
            sell_tax_factor = 0.935      # 6.5% tax (4% Premium + 2.5% Setup)
            buy_tax_factor = 1.025       # 2.5% Setup fee
            margin_factor = 1 + (min_profit_percent / 100.0)
            
            # Target Price Calculation
            target_price = int((bm_price * sell_tax_factor) / (buy_tax_factor * margin_factor))
            if target_price < 1: target_price = 1
            
            self.logger.info(f"📊 Анализ: BM={bm_price} | MinProfit={min_profit_percent}%")
            self.logger.info(f"🎯 Target Calculation: ({bm_price} * 0.935) / (1.025 * {margin_factor:.2f}) = {target_price}")
            self.logger.info(f"💰 Current Price: {current_price} | Target: {target_price}")
            
            # Проверям, выгодна ли текущая цена ВООБЩЕ
            
            if current_price > 0 and current_price > target_price:
                self.logger.info(f"📉 Цена рынка ({current_price}) выше целевой ({target_price}). Пропуск.")
                # Не закрываем меню, чтобы следующая вариация могла продолжить
                break
            
            # 4. Количество (Batching)
            BATCH_SIZE = 10
            buy_qty = min(remaining_limit, BATCH_SIZE)
            self.logger.info(f"🛒 Микро-ордер: {buy_qty} шт. (Target: {target_price})")
            
            # 5. Ввод количества
            self._input_quantity(buy_qty)
            
            # 6. Ввод цены
            price_coord = self.config.get_coordinate("price_input")
            if price_coord:
                self._human_move_to(*price_coord)
                self._human_click()
                self._human_type(str(target_price), clear=True)
                time.sleep(0.3)
            else:
                 self.logger.error("❌ Не задана координата 'price_input'!")
                 self._close_menu()
                 return 0
            
            # 7. Верификация (Simplified for speed)
            # Мы доверяем вводу pynput. Можно добавить проверку Total, если критично.
            
            # 8. Покупка
            if self.simulation_mode:
                 self.logger.warning("💊 SIMULATION: Fake buy click.")
                 success = True
            else:
                 success = self._click_confirm_order()
                 
            if success:
                self.logger.info(f"✅ Ордер размещен: {buy_qty} шт. @ {target_price}")
                remaining_limit -= buy_qty
                consecutive_errors = 0
                
                # Меню закрывается само при успешной покупке
                self._is_menu_open = False
                time.sleep(1.5) # Wait for backend/refresh
            else:
                self.logger.error("❌ Не удалось нажать кнопку заказа")
                consecutive_errors += 1
                self._close_menu() # Ensure closed
                time.sleep(1)

            # Если купили все что было в лоте, цикл повторится и проверит следующую цену
            # Если лимит исчерпан, цикл завершится.




    def _build_purchase_list(self):
        targets = self.config.get_wholesale_targets()
        self._items_to_buy = []
        for item_name, variants in targets.items():
            for key, data in variants.items():
                try:
                    limit = data.get("limit", 0)
                    enabled = data.get("enabled", False)
                    if limit > 0 and enabled:
                        t, e = map(int, key.replace("T", "").split("."))
                        
                        self._items_to_buy.append((item_name, t, e, limit))
                except:
                    continue
        self._items_to_buy.sort(key=lambda x: (x[0], x[1], x[2]))

    def _search_item_and_open(self, name: str) -> bool:
        # 1. Сброс
        search_clear = self.config.get_coordinate("search_clear")
        if search_clear:
            self._human_move_to(*search_clear)
            self._human_click()
            
        # 2. Ввод
        search_input = self.config.get_coordinate("search_input")
        if not search_input: return False
        
        self._human_move_to(*search_input)
        self._human_click()
        self._human_type(name)
        pyautogui.press('enter')
        time.sleep(1.0)
        
        # 3. Купить (открыть меню)
        buy_btn = self.config.get_coordinate("buy_button")
        if not buy_btn: return False
        self._human_move_to(*buy_btn)
        self._human_click()
        time.sleep(1.0)
        
        # 4. Раскрыть (Smart Expand)
        need_expand = True
        from ..utils.ocr import read_price_at
        area = self.config.get_coordinate_area("best_price_area")
        if area:
            p = read_price_at(area)
            if p and p > 0: need_expand = False
        
        if need_expand:
            expand_coord = self.config.get_coordinate("item_expand")
            if expand_coord:
                self._human_move_to(*expand_coord)
                self._human_click()
                time.sleep(0.5)
        
        # 5. Проверка имени
        if not self._verify_item_name_with_retry(name):
             return False
             
        return True
        
    def _close_menu(self):
        close_btn = self.config.get_coordinate("menu_close")
        if close_btn:
             self._human_move_to(*close_btn)
             self._human_click()
             self._is_menu_open = False
             self._current_tier_value = None
             time.sleep(0.5)




    def _select_tier(self, tier):
        coord = self.dropdowns.get_tier_click_point(
            tier, 
            item_name=self._current_item_name,
            current_enchant=self._current_enchant
        )
        if coord:
            self.dropdowns.open_tier_menu(self)
            self._human_move_to(*coord)
            self._human_click()
            time.sleep(0.1)

    def _select_enchant(self, enchant):
        coord = self.dropdowns.get_enchant_click_point(enchant)
        if coord:
            self.dropdowns.open_enchant_menu(self)
            self._human_move_to(*coord)
            self._human_click()
            time.sleep(0.1)
            # Update internal state if needed
            self._current_enchant = enchant

    def _select_quality(self, quality):
        """
        Выбор качества с проверкой OCR.
        Если уже стоит нужное -> пропускаем клик.
        """
        # 0. Имя качества для логов/проверки
        quality_map = {
            1: ["Обычное", "Normal"],
            2: ["Хорошее", "Good"],
            3: ["Выдающееся", "Outstanding"],
            4: ["Отличное", "Excellent"],
            5: ["Шедевр", "Masterpiece"]
        }
        expected_names = quality_map.get(quality, [])

        # 1. Проверяем текущее состояние через OCR
        from ..utils.ocr import read_screen_text, is_ocr_available, fuzzy_match_quality
        
        if is_ocr_available():
            area = self.config.get_coordinate_area("quality_text_region")
            if area:
                try:
                    passive_text = read_screen_text(area['x'], area['y'], area['w'], area['h'])
                    # self.logger.debug(f"OCR Quality Check: '{passive_text}' vs {expected_names}")
                    
                    if fuzzy_match_quality(passive_text, expected_names):
                        # self.logger.info(f"✅ Качество '{passive_text}' уже выбрано. Skip click.")
                        return 
                        
                except Exception as e:
                    pass # Fallback to click

        # 2. Если не совпало или нет OCR -> Кликаем как раньше
        coord = self.dropdowns.get_quality_click_point(quality)
        if coord:
            self.dropdowns.open_quality_menu(self)
            self._human_move_to(*coord)
            self._human_click()
            time.sleep(0.1)

    def _input_quantity(self, qty: int):
        """Ввод количества в поле (buyer_amount_input)"""
        amount_input_coord = self.config.get_coordinate("buyer_amount_input")
        if amount_input_coord:
             self._human_move_to(*amount_input_coord)
             self._human_click()
             self._human_dbl_click()
             self._human_type(str(qty))
             
             # Клик левее для обновления (как в ТЗ)
             # x - 60, y
             self._human_move_to(amount_input_coord[0] - 60, amount_input_coord[1])
             self._human_click()
             time.sleep(0.5)

    def _click_confirm_order(self) -> bool:
        """Нажатие кнопки Создать заказ с проверкой Симуляции и Подтверждения"""
        confirm_btn = self.config.get_coordinate("buyer_create_order_confirm")
        if not confirm_btn: return False
        
        # --- MANUAL CONFIRM ---
        if self.manual_confirm_mode:
            self.logger.critical("👉 Нажмите F1 для ПОКУПКИ")
            self.logger.critical("👉 Нажмите F2 для ПРОПУСКА")
            
            import keyboard
            confirmed = False
            while True:
                if self._stop_requested: return False
                if keyboard.is_pressed('F1'):
                    confirmed = True
                    time.sleep(0.5)
                    break
                if keyboard.is_pressed('F2'):
                    self.logger.warning("🚫 Пропуск пользователем.")
                    time.sleep(0.5)
                    return False
                time.sleep(0.1)
            
            if not confirmed: return False
            
        # --- SIMULATION CHECK ---
        if self.simulation_mode:
            self.logger.info("💊 [SIMULATION] Клик 'Создать заказ' пропущен.")
            return True # Возвращаем True как будто купили
            
        # REAL CLICK
        self._human_move_to(*confirm_btn)
        self._human_click()
        return True

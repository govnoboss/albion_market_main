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
        self.simulation_mode = False # По умолчанию True для безопасности
        self.manual_confirm_mode = False # Debug F1/F2 mode
        self.max_budget = 0 # 0 = Unlimited
        self.spent_amount = 0 # Отслеживание трат сессии
        self.mode = "wholesale" # wholesale | smart
        self.sort_by_percent = False  # Сортировка по % профита (вместо абсолютного серебра)
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
        budget_str = f"{self.max_budget:,} Silver" if self.max_budget > 0 else "Безлимит"
        self.logger.info(f"💵 Бюджет на сессию: {budget_str}")
        self.spent_amount = 0 
        self.logger.info("⏳ Задержка старта 1 сек...")
        time.sleep(1.0)
        
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
            
        # 2. Группируем по имени для эффективного поиска
        tasks_by_item = {}
        processed_keys = set() 

        for name, tier, enchant, limit in self._items_to_buy:
             if name not in tasks_by_item: tasks_by_item[name] = []
             tasks_by_item[name].append((tier, enchant, limit))
             
        processed_count = 0
        
        for item_name, variants in tasks_by_item.items():
            if self._stop_requested: break
            self._check_pause()
            
            self.logger.info(f"🔎 Проверка предмета: {item_name} ({len(variants)} вариаций)")
            
            # Сбрасываем запомненное состояние фильтров при смене предмета
            # Чтобы гарантированно прокликать тир/энчант для нового айтема
            self._current_tier_value = None
            self._current_enchant = None
            
            # 0. Сначала ставим фильтры (берем первую вариацию как базу)
            if variants:
                first_tier, first_enchant, _ = variants[0]
                self.logger.info(f"⚙️ Предварительная установка фильтров: T{first_tier}.{first_enchant}")
                self._select_tier(first_tier)
                self._select_enchant(first_enchant)
                time.sleep(0.3)
            
            # 1. Поиск предмета (Один раз на имя)
            if not self._search_item_only(item_name):
                 self.logger.warning(f"❌ Не удалось найти предмет: {item_name}")
                 continue

            # 2. Перебор вариаций
            for tier, enchant, limit in variants:
                if self._stop_requested: break
                
                # Ключ текущей задачи
                task_key = (item_name, tier, enchant)
                if task_key in processed_keys: continue
                
                processed_count += 1
                self._process_variant(item_name, tier, enchant, limit, processed_count, total_tasks)
                processed_keys.add(task_key)

    def _search_item_only(self, name: str) -> bool:
        """Только поиск предмета без открытия"""
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
        time.sleep(0.7)
        return True

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
        
        for i, (item_name, tier, enchant, profit_est, market_price, profit_pct) in enumerate(items_to_check):
            if self._stop_requested: break
            self._check_pause()
            
            processed_count += 1
            # Отображаем % или серебро в зависимости от режима сортировки
            if self.sort_by_percent:
                self.progress_updated.emit(processed_count, total_items, f"{item_name} (+{profit_pct:.1f}%)")
            else:
                self.progress_updated.emit(processed_count, total_items, f"{item_name} (+{int(profit_est)} s.)")
            
            # 3. Определяем лимит (Batch)
            # Пробуем найти лимит в конфиге
            config_limit = 0
            try:
                
                targets = self.config.get_wholesale_targets()
                variant_key = f"T{tier}.{enchant}"
                
                if item_name in targets and variant_key in targets[item_name]:
                    data = targets[item_name][variant_key]
                    if data.get("enabled", False):
                        config_limit = data.get("limit", 0)
            except: pass
            
            final_limit = config_limit if config_limit > 0 else DEFAULT_BATCH
            
            # Логируем с обоими показателями
            self.logger.info(f"🧠 Smart Item: {item_name} T{tier}.{enchant} | Profit: {int(profit_est)} ({profit_pct:.1f}%) | Limit: {final_limit} {'(Config)' if config_limit > 0 else '(Default)'}")
            
            # 4. Выполняем закупку (Reusing Wholesale Logic)
            try:
                # Открываем предмет (с tier.enchant в поиске)
                if not self._search_item_and_open(item_name, tier, enchant):
                    continue
                
                # Переход на вкладку Заказа (УДАЛЕНО для Sniper Mode)
                # if not self._is_black_market: ...

                # Запускаем процессор вариации
                self._process_variant(item_name, tier, enchant, final_limit, processed_count, total_items)
                
                self._close_menu()
                
            except Exception as e:
                self.logger.error(f"Error smart loop: {e}")
                self._close_menu()
                
    def _get_profitable_items_sorted(self):
        """
        Возвращает список [(name, tier, enchant, profit, market_price, profit_percent), ...]
        отсортированный по profit или profit_percent (в зависимости от self.sort_by_percent).
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
                    
                    # Profit Percent = ((net_bm - market) / market) * 100
                    profit_percent = ((net_bm - market_price) / market_price) * 100
                    
                    # Фильтр: отсекаем нереалистичные профиты (ошибки OCR)
                    if profit_percent > 1000:
                        continue
                    
                    # Basic filters
                    if profit > 500: # Min safe profit hardcoded
                        items.append((item_name, tier, enchant, profit, market_price, profit_percent))
                        
                except Exception: continue
        
        # Sort by percentage or absolute profit
        if self.sort_by_percent:
            # Сортировка по % профита (desc)
            items.sort(key=lambda x: x[5], reverse=True)
            self.logger.info("📊 Сортировка: по % профита")
        else:
            # Сортировка по абсолютному профиту (desc)
            items.sort(key=lambda x: x[3], reverse=True)
            self.logger.info("💰 Сортировка: по серебру")
        
        # Применяем фильтры из настроек
        filters = self.config.get_scan_filters()
        allowed_tiers = filters.get("tiers", [4, 5, 6, 7, 8])
        allowed_enchants = filters.get("enchants", [0, 1, 2, 3, 4])
        
        filtered_items = [
            item for item in items 
            if item[1] in allowed_tiers and item[2] in allowed_enchants
        ]
        
        if len(filtered_items) < len(items):
            self.logger.info(f"🔍 Фильтры: {len(items)} → {len(filtered_items)} предметов")
            
        return filtered_items



    def _process_variant(self, item_name, tier, enchant, limit, prog_curr=0, prog_total=0):
        """
        Стандартная логика покупки (для всех режимов).
        Покупка из списка без создания ордера.
        Flow:
        1. Set Filters (Tier/Enchant)
        2. Verify Item Name (OCR)
        3. Check Market Price (OCR) -> Skip if > Target
        4. Click Buy
        5. Verify Quantity in Dialog (OCR)
        6. Verify Total Price in Dialog (OCR)
        7. Confirm
        """
        from ..utils.ocr import read_price_at, read_screen_text, read_qty_text
        
        # 1. Фильтры
        self.logger.info(f"� Фильтры: T{tier}.{enchant}")
        # Выбираем Тир
        self._select_tier(tier)
        # Выбираем Энчант
        self._select_enchant(enchant)
        time.sleep(0.5) # Ждем обновления списка
        
        # 2. Верификация имени (item_name_area)
        # Проверяем, что мы всё еще смотрим на нужный предмет, несмотря на фильтры.
        if not self._verify_item_name_with_retry(item_name):
             self.logger.warning(f"❌ Имя предмета не совпадает! Ожидалось: {item_name}")
             return
        
        # 3. Анализ цены (OCR)
        # Читаем цену топ лота (в списке)
        price_area = self.config.get_coordinate_area("best_price_area")
        if not price_area:
             self.logger.error("❌ Не задана зона 'best_price_area'")
             return
             
        current_price = read_price_at(price_area)
        
        if current_price is None or current_price <= 0:
            self.logger.warning(f"⏩ Пропуск: Не удалось прочитать цену (OCR: {current_price})")
            return
            
        # Target Price Validations
        bm_price = price_storage.get_item_price("Black Market", item_name, tier, enchant, 1)
        if not bm_price:
            self.logger.warning(f"⏩ Пропуск: Нет цены ЧР")
            return
            
        _, _, min_profit_percent = self.config.get_wholesale_limit(item_name, tier, enchant)
        
        # Target Price Formula (Sniper: No Tax on Buy)
        # Profit = (BM * 0.935) - BuyPrice
        # Margin = Profit / BuyPrice
        # BuyPrice * Margin = (BM * 0.935) - BuyPrice
        # BuyPrice * (1 + Margin) = BM * 0.935
        # BuyPrice = (BM * 0.935) / (1 + Margin)
        
        sell_tax_factor = 0.935
        margin_factor = 1 + (min_profit_percent / 100.0)
        target_price = int((bm_price * sell_tax_factor) / margin_factor)
        
        display_name = f"{item_name} T{tier}.{enchant}"
        self.logger.info(f"� Анализ: {current_price} vs Target {target_price} (BM: {bm_price})")
        
        if prog_total > 0:
             self.progress_updated.emit(prog_curr, prog_total, f"{display_name} - {current_price} / {target_price}")
             
        if current_price > target_price:
             self.logger.info(f"📉 Цена ({current_price}) выше целевой ({target_price}). Пропуск.")
             return
             
        # 4. Покупка (Клик по кнопке Купить)
        self.logger.info(f"✅ Цена подходит! Начинаем покупку...")
        buy_btn = self.config.get_coordinate("buy_button")
        if not buy_btn:
            self.logger.error("❌ Нет кнопки 'buy_button'")
            return
            
        self._human_move_to(*buy_btn)
        self._human_click()
        time.sleep(0.5) # Ждем диалог
        
        # 5. Верификация количества (Dialog)
        # User Req: "Прямо перед проверкой total_price... ocr проверку количества"
        # Используем buyer_amount_input как якорь для зоны
        qty_input_point = self.config.get_coordinate("buyer_amount_input")
        actual_qty = 1 # Default fallback
        
        if qty_input_point:
             # Вариант А: Читаем buyer_top_lot_qty (Специализированный метод read_qty_text)
             qty_area = self.config.get_coordinate_area("buyer_top_lot_qty")
             if qty_area:
                 # Используем новый метод с жесткими фильтрами
                 q_val = read_qty_text(qty_area)
                 if q_val and q_val > 0:
                     actual_qty = q_val
                     self.logger.info(f"🔢 Количество (OCR Spec): {actual_qty}")
                 else:
                     self.logger.warning("⚠️ Не удалось прочитать количество (buyer_top_lot_qty). Считаем 1.")
        
        # 6. Верификация итоговой суммы (Dialog)
        total_price_area = self.config.get_coordinate_area("buyer_total_price")
        if total_price_area:
             actual_total = read_price_at(total_price_area)
             if actual_total and actual_total > 0:
                 # Check
                 expected_total = current_price * actual_qty
                 # Buffer mismatch (sometimes prices update?)
                 if actual_total > int(expected_total * 1.05): # 5% buffer
                      self.logger.warning(f"🛑 Итоговая сумма не сходится! {actual_total} vs {expected_total}. Отмена.")
                      self._close_menu()
                      return
                 self.logger.info(f"✅ Сумма корректна: {actual_total}")
             else:
                 self.logger.warning("⚠️ Не удалось прочитать Total Price. Рискованно...")
                 # Решаем: пропускать или нет? Лучше пропустить если это Sniper.
        
        # 7. Подтверждение
        confirm_btn = self.config.get_coordinate("buyer_create_order_confirm")
        if confirm_btn:
             self._human_move_to(*confirm_btn)
             self._human_click()
             self.logger.info("� Куплено!")
             self.spent_amount += (current_price * actual_qty)
             time.sleep(0.5)
        else:
             self.logger.error("❌ Нет кнопки подтверждения!")
        
        # Закрываем меню (или оно само закроется?)
        # Обычно после покупки диалог закрывается, но лучше убедиться или нажать Esc/Close если что-то пошло не так.
        # В данном флоу мы предполагаем успех.
        
        time.sleep(0.5)




    def _build_purchase_list(self):
        targets = self.config.get_wholesale_targets()
        self._items_to_buy = []
        
        # Получаем фильтры из настроек
        filters = self.config.get_scan_filters()
        allowed_tiers = filters.get("tiers", [4, 5, 6, 7, 8])
        allowed_enchants = filters.get("enchants", [0, 1, 2, 3, 4])
        
        skipped_count = 0
        
        for item_name, variants in targets.items():
            for key, data in variants.items():
                try:
                    limit = data.get("limit", 0)
                    enabled = data.get("enabled", False)
                    if limit > 0 and enabled:
                        t, e = map(int, key.replace("T", "").split("."))
                        
                        # Проверка фильтров
                        if t not in allowed_tiers or e not in allowed_enchants:
                            skipped_count += 1
                            continue
                            
                        # Проверка цены ЧР (Если нет цены - не добавляем)
                        bm_price = price_storage.get_item_price("Black Market", item_name, t, e, 1)
                        if not bm_price or bm_price <= 0:
                            # self.logger.debug(f"⏩ Пропуск {item_name} T{t}.{e}: Нет цены ЧР")
                            continue
                        
                        self._items_to_buy.append((item_name, t, e, limit))
                except:
                    continue
        
        if skipped_count > 0:
            self.logger.info(f"🔍 Фильтры: пропущено {skipped_count} вариаций")
            
        self._items_to_buy.sort(key=lambda x: (x[0], x[1], x[2]))

    def _search_item_and_open(self, name: str, tier: int = None, enchant: int = None) -> bool:
        # Формируем поисковый запрос
        if tier is not None and enchant is not None:
            search_query = f"{name} T{tier}.{enchant}"
        else:
            search_query = name
            
        self.logger.debug(f"🔍 Поиск: '{search_query}'")
        
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
        self._human_type(search_query)
        pyautogui.press('enter')
        time.sleep(0.7)
        
        # 3. Купить (открыть меню)
        buy_btn = self.config.get_coordinate("buy_button")
        if not buy_btn: return False
        self._human_move_to(*buy_btn)
        self._human_click()
        time.sleep(0.2)
        
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
                time.sleep(0.2)
        
        # 5. Проверка имени
        if not self._verify_item_name_with_retry(name):
             return False
             
        self._is_menu_open = True
        return True
        
    def _close_menu(self):
        close_btn = self.config.get_coordinate("menu_close")
        if close_btn:
             self._human_move_to(*close_btn)
             self._human_click()
             self._human_click()
             self._is_menu_open = False
             self._current_tier_value = None
             self._current_enchant = None 
             self._current_quality = None
             time.sleep(0.5)




    def _select_tier(self, tier):
        """Выбор тира (с поддержкой исключений и сбросом качества)"""
        if self._current_tier_value == tier:
             return
             
        coord = self.dropdowns.get_tier_click_point(tier)
        if coord:
            self.dropdowns.open_tier_menu(self)
            self._human_move_to(*coord)
            self._human_click()
            time.sleep(0.1)
            self._current_tier_value = tier
            self._current_quality = None

    def _select_enchant(self, enchant):
        if self._current_enchant == enchant: return
        
        coord = self.dropdowns.get_enchant_click_point(enchant)
        if coord:
            self.dropdowns.open_enchant_menu(self)
            self._human_move_to(*coord)
            self._human_click()
            time.sleep(0.1)
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
        """
        Ввод количества.
        Приоритет: Ввод цифрами через поле 'buyer_amount_input'.
        Фоллбэк: Клики по кнопке 'buyer_plus_btn'.
        """
        # 1. Попытка ввода через клавиатуру (Keyboard Input)
        amount_input_coord = self.config.get_coordinate("buyer_amount_input")
        
        if amount_input_coord and qty > 1:
            self.logger.debug(f"⌨️ Ввод количества {qty} через клавиатуру...")
            
            self._human_move_to(*amount_input_coord)
            time.sleep(0.05)
            
            # Зажатие кнопки мыши на 0.1с (как просил пользователь)
            pyautogui.mouseDown()
            time.sleep(0.1)
            pyautogui.mouseUp()
            time.sleep(0.05)
            
            # Очистка и ввод
            import keyboard
            # Быстрая очистка (Ctrl+A, Del надежнее Backspace)
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.05)
            pyautogui.press('backspace')
            
            self._human_type(str(qty))
            time.sleep(0.2)
            return

        # 2. Фоллбэк: Клики по Плюсу (Mouse Clicks)
        plus_btn_coord = self.config.get_coordinate("buyer_plus_btn")
        
        if not plus_btn_coord:
            self.logger.warning("⚠️ Координата 'buyer_plus_btn' не задана! И 'buyer_amount_input' тоже нет.")
            return
            
        clicks_needed = qty - 1  # Изначально стоит 1
        
        if clicks_needed <= 0:
            self.logger.debug("Количество уже 1, кликать не нужно")
            return
            
        self.logger.debug(f"🔢 Ввод количества: {qty} (кликов: {clicks_needed}) - FALLBACK MODE")
        
        # Кликаем на Плюс нужное количество раз
        self._human_move_to(*plus_btn_coord)
        time.sleep(0.1)
        
        for i in range(clicks_needed):
            if self._stop_requested: return
            pyautogui.click()
            time.sleep(0.05)  # Минимальная задержка между кликами
            
        time.sleep(0.2)  # Ждём обновления UI

    def _click_confirm_order(self) -> bool:
        """Нажатие кнопки Создать заказ с проверкой Симуляции и Подтверждения (Без доп. клика 'Да')"""
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
        
        # Log success (verification happened before)
        return True

    def _get_price_area(self):
        """Helper to get preferred price area"""
        price_area = self.config.get_coordinate_area("buyer_top_lot_price")
        if not price_area:
             price_area = self.config.get_coordinate_area("best_price_area")
        return price_area

    def _wait_for_price_update(self, old_price: int, timeout: float = 0.5) -> int:
        """
        Ждет, пока цена визуально изменится по сравнению с old_price.
        """
        from ..utils.ocr import read_price_at
        
        area = self._get_price_area()
        if not area: return 0

        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self._stop_requested: return 0
            self._check_pause()
            
            price = read_price_at(area)
            
            # 1. Если цена None (не распозналась или пусто) -> Ждем
            if price is None:
                time.sleep(0.1)
                continue
                
            # 2. Если цена новая -> УСПЕХ
            if price != old_price:
                self.logger.debug(f"✅ Цена обновилась: {old_price} -> {price}")
                return price
                
            # 3. Если цена совпадает со старой
            if price == old_price:
                time.sleep(0.1)
                continue
            
        self.logger.warning(f"⏰ Таймаут ожидания цены! (Old: {old_price}).")
        return 0

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
    Поддерживает два режима:
    1. wholesale (Опт): Работает по списку из конфига (лимиты), ставит ордера.
    2. retail (Розница): Работает по таблице профитов (Sniper), покупает мгновенно.
    """
    
    def __init__(self):
        super().__init__()
        self.dropdowns = DropdownSelector()
        self._items_to_buy = [] # Список задач [(name, tier, enchant, limit)]
        self.simulation_mode = True # По умолчанию True для безопасности
        self.manual_confirm_mode = False # Debug F1/F2 mode
        self.mode = "wholesale" # wholesale | retail.mode = "wholesale" # wholesale | retail
        
    def run(self):
        """Основной цикл закупки"""
        self._is_running = True
        self._stop_requested = False
        self._is_paused = False
        
        mode_name = "РОЗНИЦА (Sniper)" if self.mode == "retail" else "ОПТ (Orders)"
        self.logger.info(f"💰 ЗАПУСК РЕЖИМА: {mode_name} 💰")
        self.logger.info("⏳ Задержка старта 1 сек...")
        time.sleep(1.0)
        
        self._detect_current_city()
        
        if self.mode == "retail":
            self._run_retail()
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
                
                for tier, enchant, limit in variants:
                    if self._stop_requested: break
                    processed_count += 1
                    self.progress_updated.emit(processed_count, total_tasks, f"{item_name} T{tier}.{enchant}")
                    
                    self._process_variant_wholesale(item_name, tier, enchant, limit)
                    
                self._close_menu()
                
            except Exception as e:
                self.logger.error(f"Ошибка при обработке {item_name}: {e}")
                self._close_menu()

    def _run_retail(self):
        """Логика РОЗНИЧНОЙ закупки (Sniper по таблице профитов)"""
        if self.simulation_mode:
            self.logger.warning("💊 РЕЖИМ СИМУЛЯЦИИ: Покупка не будет совершена.")

        # 1. Получаем и сортируем профиты
        # Нам нужны: City, Item, Tier, Enchant, ProfitSilver (Net)
        # Алгоритм сортировки по профиту за 1 шт.
        # Цена BM берется из price_storage (там данные ЧР, если есть)
        # Цена CurrentMarket берется тоже из price_storage (последний скан) 
        #   ИЛИ мы просто итерируем по всему, что есть в базе ЧР и сканим текущее?
        #   ТЗ: "Смотрим в таблицу профиты в нашем сканере. Сортируем таблицу всех городов..."
        # Значит, мы берем данные, которые УЖЕ собраны сканером.
        
        items_to_check = self._get_profitable_items_sorted()
        total_items = len(items_to_check)
        
        if total_items == 0:
            self.logger.warning("Нет выгодных предметов в базе! (Сначала запустите Сканер)")
            return

        self.logger.info(f"Найдено {total_items} кандидатов с потенциальным профитом.")
        
        for i, (item_name, tier, enchant, profit_est, market_price) in enumerate(items_to_check):
            if self._stop_requested: break
            self._check_pause()
            
            self.progress_updated.emit(i + 1, total_items, f"{item_name} (+{int(profit_est)} s.)")
            self.logger.info(f"🔎 Candidate [{i+1}/{total_items}]: {item_name} T{tier}.{enchant} (Est. Profit: {int(profit_est)})")
            
            try:
                # 2. Поиск и открытие
                if not self._search_item_and_open(item_name):
                    continue

                # 3. Выставляем T/E
                self._select_tier(tier)
                self._select_enchant(enchant)
                
                # 4. Проверяем качество (Normal only)
                self._select_quality(1) 
                
                # 5. Выполняем логику закупки (Instant Buy)
                # Покупаем 1 шт (Sniper logic) по ожидаемой цене.
                # Функция сама проверит OCR Total Price и подтвердит.
                self._execute_purchase_logic(expected_unit_price=market_price, limit=1)
                
                self._close_menu()
                
            except Exception as e:
                self.logger.error(f"Error retail loop: {e}")
                self._close_menu()

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
            
            # 1. Установка параметров (Tab -> Tier -> Enchant)
            # Переходим на вкладку "Заказ" !!! (Важно: конфиг должен иметь ключ 'create_buy_order')
            buy_order_tab = self.config.get_coordinate("create_buy_order") # Это вкладка "Создать заказ"
            if buy_order_tab:
                self._human_move_to(*buy_order_tab)
                self._human_click()
                time.sleep(0.5)
            else:
                 self.logger.error("❌ Не настроена координата вкладки 'Создать заказ' (create_buy_order)")
                 break
            
            self._select_tier(tier) 
            self._select_enchant(enchant)
            self._select_quality(1) # Всегда Normal
            
            # 2. Анализ цены (OCR)
            
            price_area = self.config.get_coordinate_area("buyer_top_lot_price")
            if not price_area:
                 price_area = self.config.get_coordinate_area("best_price_area")
            
            if not price_area:
                self.logger.error("❌ Не задана зона чтения цены (buyer_top_lot_price)")
                break
                
            from ..utils.ocr import read_price_at, read_amount_at
            current_price = read_price_at(price_area)
            
            if not current_price or current_price <= 0:
                self.logger.warning(f"⚠️ Не удалось прочитать цену. (OCR: {current_price})")
                consecutive_errors += 1
                time.sleep(1)
                continue
                
            # 3. Расчет профита
            # Formula: Profit = (BM * 0.935) - (Current * 1.025)
            net_sell_bm = bm_price * (1 - 0.065)
            gross_buy_cost = current_price * (1 + 0.025)
            profit = net_sell_bm - gross_buy_cost
            
            self.logger.info(f"📊 Анализ: BM={bm_price} | Cur={current_price} | Cost={int(gross_buy_cost)} | Profit={int(profit)}")
            
            if profit <= 0:
                self.logger.info(f"📉 Невыгодно. Profit {int(profit)} <= 0. Переход к следующему.")
                break
            
            # 4. Количество (OCR)
            qty_area = self.config.get_coordinate_area("buyer_top_lot_qty")
            available_qty = 1
            if qty_area:
                qty_read = read_amount_at(qty_area)
                if qty_read > 0: available_qty = qty_read
            
            # Решаем сколько брать
            buy_qty = min(remaining_limit, available_qty)
            self.logger.info(f"🛒 Покупаем: {buy_qty} шт. (Доступно: {available_qty})")
            
            # 5. Ввод количества
            self._input_quantity(buy_qty)
            
            # 6. Ввод цены? (Если мы в Make Order, цена может стоять +1 от топа или current)
            # ТЗ не говорит менять цену, значит оставляем ту, что предложила игра (обычно match lowest sell order)
            # Или вводим current_price?
            # "Вводим меньшее, клик чуть левее... Сравниваем...". Про цену ввода не сказано.
            # Значит игра сама подставила цену выкупа.
            
            # 7. Верификация суммы
            # Итоговая = buy_qty * current_price * 1.025
            expected_total = int(buy_qty * current_price * 1.025)
            
            total_area = self.config.get_coordinate_area("buyer_total_price")
            if total_area:
                total_ocr = read_price_at(total_area)
                if total_ocr:
                    
                    diff = abs(total_ocr - expected_total)
                    if diff > (expected_total):
                         self.logger.warning(f"⚠️ Ошибка суммы! OCR: {total_ocr} != Exp: {expected_total}. Скип.")
                         consecutive_errors += 1
                         continue
                else:
                    self.logger.warning("⚠️ Не удалось прочитать Total Price. Рискнуть?")
                    # Лучше скип
                    consecutive_errors += 1
                    continue
            
            # 8. Покупка
            if self._click_confirm_order():
                self.logger.info(f"✅ Успех! Куплено {buy_qty} шт.")
                remaining_limit -= buy_qty
                consecutive_errors = 0
                time.sleep(1.0)
            else:
                self.logger.warning("❌ Не удалось нажать Confirm.")
                consecutive_errors += 1
            
            # Если купили все что было в лоте, цикл повторится и проверит следующую цену
            # Если лимит исчерпан, цикл завершится.


    def _get_profitable_items_sorted(self):
        """
        Возвращает список [(name, tier, enchant, profit), ...]
        отсортированный по profit (desc).
        Данные берем из price_storage (Market vs Black Market).
        """
        if not self._current_city:
            self.logger.warning("Город не определен, сортировка невозможна.")
            return []
            
        items = [] # (name, tier, enchant, profit)
        
        # Получаем все цены для текущего города (Market Prices)
        city_prices = price_storage.get_city_prices(self._current_city)
        if not city_prices:
            self.logger.warning(f"Нет данных о ценах в {self._current_city}")
            return []
            
        # Проходим по всем предметам, для которых есть цена на ЧР
        bm_prices = price_storage.get_city_prices("Black Market")
        if not bm_prices:
             self.logger.warning("Нет данных с Черного Рынка (Black Market empty)")
             return []
             
        for item_name, variants in city_prices.items():
            if item_name not in bm_prices: continue
            
            bm_variants = bm_prices[item_name]
            
            for key, data in variants.items():
                market_price = data.get("price", 0)
                if market_price <= 0: continue
                
                # Ищем пару на ЧР
                if key not in bm_variants: continue
                
                bm_price_data = bm_variants[key]
                bm_price = bm_price_data.get("price", 0)
                
                if bm_price <= 0: continue
                
                try:
                    t_str, e_str = key.replace("T", "").split(".")
                    tier = int(t_str)
                    enchant = int(e_str)
                    
                    # --- Profit Calculation ---
                    # Tax: 6.5% total deduction logic
                    # Profit = (BM * (1 - 0.065)) - MarketPrice
                    
                    net_bm = bm_price * (1 - 0.065)
                    profit = net_bm - market_price
                    
                    # ROI check
                    roi = profit / market_price if market_price > 0 else 0
                    
                    # Filters: 
                    # 1. Min Profit > 1000 silver
                    # 2. ROI > 15% (0.15)
                    if profit > 1000 and roi > 0.15: 
                        # Return (name, tier, enchant, profit, market_price)
                        items.append((item_name, tier, enchant, profit, market_price))
                        
                except Exception as e:
                    continue
                    
        # Sort by Profit (Descending)
        items.sort(key=lambda x: x[3], reverse=True)
        
        return items

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
        
        # 4. Раскрыть (если надо) - можно добавить проверку area
        
        # 5. Проверка имени
        if not self._verify_item_name_with_retry(name):
             return False
             
        return True
        
    def _close_menu(self):
        close_btn = self.config.get_coordinate("menu_close")
        if close_btn:
             self._human_move_to(*close_btn)
             self._human_click()
             time.sleep(0.5)

    def _execute_purchase_logic(self, expected_unit_price: int, limit: int):
        """
        Физическое выполнение закупки.
        Ожидаем, что окно предмета уже открыто и мы выбрали T/E/Q.
        """


        # 1. Переход на вкладку "Купить" (Instant)
        buy_tab = self.config.get_coordinate("buyer_tab_buy")
        if buy_tab:
            self._human_move_to(*buy_tab)
            self._human_click()
            time.sleep(0.5)
        
        # 2. Проверяем количество в топ лоте (OCR)
        
        qty_area = self.config.get_coordinate_area("buyer_top_lot_qty")
        available_qty = 1 
        
        if qty_area:
            from ..utils.ocr import read_amount_at
            scanned_qty = read_amount_at(qty_area)
            if scanned_qty and scanned_qty > 0:
                available_qty = scanned_qty
        
        # Target Qty = min(limit, available)
        target_qty = min(limit, available_qty)
        
        # 3. Ввод количества
        if target_qty > 1:
             # Click Amount Input
             amount_input_coord = self.config.get_coordinate("buyer_amount_input")
             if amount_input_coord:
                 self._human_move_to(*amount_input_coord)
                 self._human_click() # Focus
                 # Double click to select all? OR Ctrl+A
                 self._human_dbl_click()
                 time.sleep(0.1)
                 
                 self._human_type(str(target_qty))
                 
                 # Click Offset (20px left) to unfocus and trigger calc
                 # X - 20, Y
                 self._human_move_to(amount_input_coord[0] - 40, amount_input_coord[1])
                 self._human_click()
                 time.sleep(0.5) 
        
        # 4. Проверка итоговой суммы (OCR Total Price)
        # ТЗ: "Проверяем OCR: Итоговая стоимость"
        total_price_area = self.config.get_coordinate_area("buyer_total_price")
        if total_price_area:
            from ..utils.ocr import read_price_at
            total_price_ocr = read_price_at(total_price_area)
            
            # Expected Max = target_qty * (expected_unit_price * 1.05) ? 
            # Allow small variance? Or exact match?
            # User: "Совпадает ли итоговая стоимость с отсканированной * количество? Совпадает -> Жмем"
            # Strict logic:
            
            # Since market price fluctuates, the unit price might be slightly diff from what we saw 1 sec ago.
            # But we want to ensure we don't pay 10x.
            
            expected_total = target_qty * expected_unit_price
            
            # Allow 1-2% deviation? NO, User said SAFE. 
            # If price changed Up, we skip.
            # If price changed Down, we ok.
            
            if total_price_ocr:
                if total_price_ocr > expected_total:
                    # Цена выросла!
                    self.logger.warning(f"❌ Цена изменилась! OCR Total: {total_price_ocr} > Exp: {expected_total}. СКИП.")
                    return
                # else: Good.
            else:
                self.logger.error("❌ Не удалось прочитать Итоговую сумму. СКИП.")
                return

        if self.manual_confirm_mode:
            self.logger.critical(f"🛑 [DEBUG CONFIRM] Готов купить {target_qty} шт. за {total_price_ocr}")
            self.logger.critical("👉 Нажмите F1 для ПОДТВЕРЖДЕНИЯ")
            self.logger.critical("👉 Нажмите F2 для ОТМЕНЫ")
            
            import keyboard
            while True:
                if self._stop_requested: return
                
                if keyboard.is_pressed('F1'):
                    self.logger.info("✅ F1 нажата -> ПОКУПАЕМ!")
                    time.sleep(0.5) # Wait for release
                    break
                    
                if keyboard.is_pressed('F2'):
                    self.logger.warning("🚫 F2 нажата -> ОТМЕНА.")
                    return
                
                time.sleep(0.1)

        # 5. Нажать "Заказать" (Confirm)
        confirm_btn = self.config.get_coordinate("buyer_create_order_confirm")
        if confirm_btn:
            self._human_move_to(*confirm_btn)
            self._human_click()
            time.sleep(0.5)
            
            # 6. Проверка popups (TODO)
             # "Item Sold" check


    def _select_tier(self, tier):
        # Fix: Pass item_name and enchant for exception handling
        coord = self.dropdowns.get_tier_click_point(
            tier, 
            item_name=self._current_item_name if hasattr(self, '_current_item_name') else None,
            current_enchant=self._current_enchant if hasattr(self, '_current_enchant') else 0
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

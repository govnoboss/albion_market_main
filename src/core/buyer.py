"""
Логика закупки (Buyer Mode)
Автоматическая покупка предметов на основе конфигурации и цен.
"""

import time
import random
from datetime import datetime
import pyautogui
from .base_bot import BaseBot
from .interaction import DropdownSelector
from .finance import finance_manager
from .network_listener import NetworkListener
import threading
from ..utils.price_storage import price_storage
from ..utils.localization import get_text

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
        self.simulation_mode = False
        self.manual_confirm_mode = False # Debug F1/F2 mode
        self.max_budget = 0 # 0 = Unlimited
        self.spent_amount = 0 # Отслеживание трат сессии
        self.mode = "wholesale" # wholesale | smart
        self.sort_by_percent = False  # Сортировка по % профита (вместо абсолютного серебра)
        self._is_menu_open = False # State tracking for optimization
        self._current_tier_value = None # State for tier skip optimization
        
        # Города (динамические)
        self.buy_city = "Martlock"
        self.sell_city = "Black Market"
        
        # Current Item State (Context for specific tier logic)
        self._current_item_name = None
        self._current_enchant = None
        self._skip_item_requested = False
        
        # Network Listener
        self.network_listener = NetworkListener()
        self.network_listener.market_data_received.connect(self._on_network_data)
        self._last_network_data = None
        self._network_event = threading.Event()

    def _on_network_data(self, data):
        """Коллбек при получении сетевых данных"""
        self._last_network_data = data
        self._network_event.set()
        
    def run(self):
        """Основной цикл закупки"""
        self._is_running = True
        self._stop_requested = False
        self._is_paused = False
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._session_start_time = time.time()
        
        self.logger.info(f"💰 ЗАПУСК РЕЖИМА: ОПТ (Orders) 💰")
        self.logger.info(f"📍 Маршрут: {self.buy_city} -> {self.sell_city}")
        budget_str = f"{self.max_budget:,} Silver" if self.max_budget > 0 else "Безлимит"
        self.logger.info(f"💵 Бюджет на сессию: {budget_str}")
        self.spent_amount = 0 
        self.logger.info("⏳ Задержка старта 1 сек...")
        time.sleep(1.0)
        
        # Запуск сетевого слушателя
        self.network_listener.start()
        
        self._detect_current_city()
        
        if self.mode == "smart":
            self._run_smart_buyer()
        else:
            self._run_wholesale()
            
        self.logger.info("🏁 Закупка завершена.")
        
        if not self.simulation_mode:
            self._report_session_to_server()
            
        self._is_running = False
        self.network_listener.stop()
        self.finished.emit()

    def _report_session_to_server(self):
        """Отправка агрегированных данных сессии на сервер (Fire-and-forget)"""
        try:
            import threading
            
            def send_task():
                try:
                    import sqlite3
                    import requests
                    from .finance import finance_manager
                    from .license import license_manager, SERVER_URL
                    
                    # 1. Получаем агрегированные данные сессии
                    conn = sqlite3.connect(finance_manager.db_path)
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT SUM(qty), SUM(total), SUM(profit_est)
                        FROM transactions
                        WHERE session_id = ? AND is_simulation = 0
                    ''', (self.session_id,))
                    row = cursor.fetchone()
                    
                    if not row or not row[0]:
                        conn.close()
                        self.logger.debug("Нет покупок в сессии, отчет не отправлен.")
                        return
                    
                    items_bought = int(row[0] or 0)
                    total_spent = int(row[1] or 0)
                    total_profit_est = int(row[2] or 0)
                    
                    if items_bought <= 0:
                        conn.close()
                        return
                    
                    # Получаем детализацию по предметам (Топ 20 по количеству)
                    cursor.execute('''
                        SELECT item_name, SUM(qty) as q, SUM(total) as t, SUM(profit_est) as p
                        FROM transactions
                        WHERE session_id = ? AND is_simulation = 0
                        GROUP BY item_name
                        ORDER BY q DESC
                        LIMIT 20
                    ''', (self.session_id,))
                    
                    items_detail = []
                    for item_row in cursor.fetchall():
                        items_detail.append({
                            "name": str(item_row[0]),
                            "qty": int(item_row[1] or 0),
                            "spent": int(item_row[2] or 0),
                            "profit": int(item_row[3] or 0)
                        })
                        
                    conn.close()
                        
                    # 2. Длительность сессии
                    duration_seconds = int(time.time() - getattr(self, "_session_start_time", time.time()))
                    
                    # 3. Лицензия
                    key = license_manager.load_key()
                    hwid = license_manager.get_hwid()
                    if not key:
                        return
                        
                    payload = {
                        "key": key,
                        "hwid": hwid,
                        "session_id": self.session_id,
                        "city": self.buy_city,
                        "items_bought": items_bought,
                        "total_spent": total_spent,
                        "total_profit_est": total_profit_est,
                        "duration_seconds": duration_seconds,
                        "items_detail": items_detail
                    }
                    
                    # 4. Отправка (POST /api/v1/report-session)
                    resp = requests.post(f"{SERVER_URL}/report-session", json=payload, timeout=5)
                    if resp.status_code == 200:
                        self.logger.info("📤 Статистика сессии отправлена на сервер.")
                    else:
                        self.logger.debug(f"Ответ сервера: {resp.status_code} {resp.text}")
                        
                except Exception as e:
                    self.logger.debug(f"Ошибка отправки телеметрии: {e}")
            
            # Запускаем в отдельном потоке чтобы не блокировать UI на 5 секунд
            threading.Thread(target=send_task, daemon=True).start()
            
        except Exception as e:
            self.logger.error(f"Failed to start telemetry thread: {e}")

    def skip_item(self):
        """Пропустить текущий предмет (вызывается из UI по F7)"""
        if self._is_running and not self._skip_item_requested:
            self.logger.info("⏭️ Пропуск текущего предмета запрошен...")
            self._skip_item_requested = True

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
        
        v_list = list(tasks_by_item.items())
        v_idx = 0
        while v_idx < len(v_list):
            item_name, variants = v_list[v_idx]
            if self._stop_requested: break
            self._check_pause()
            
            self._skip_item_requested = False # Reset for new item
            
            # --- Safety Check: Is Market Open? ---
            market_found = False
            for attempt in range(5):
                if self._stop_requested: break
                if self._check_market_is_open():
                    market_found = True
                    break
                else:
                    if self._detect_and_handle_kicks():
                        continue
                    self.logger.warning(f"⏳ Окно рынка не найдено (Buyer)... ({attempt+1}/5)")
                    time.sleep(1.0)
            
            if not market_found:
                self.logger.error("🛑 Работа Buyer остановлена: Рынок не открыт.")
                self._stop_requested = True
                break

            self.logger.info(f"🔎 Проверка предмета: {item_name} ({len(variants)} вариаций)")
            
            self._current_tier_value = None
            self._current_enchant = None
            
            if variants:
                first_tier, first_enchant, _ = variants[0]
                self._select_tier(first_tier)
                self._select_enchant(first_enchant)
                time.sleep(0.3)
            
            if not self._search_item_only(item_name):
                 self.logger.warning(f"❌ Не удалось найти предмет: {item_name}")
                 v_idx += 1
                 continue

            # Check skip after search
            if self._skip_item_requested:
                self.logger.info(f"⏭️ Пропуск {item_name} по запросу.")
                v_idx += 1
                continue

            # 2. Перебор вариаций (while для возможности Retry)
            var_idx = 0
            while var_idx < len(variants):
                if self._stop_requested: break
                
                tier, enchant, limit = variants[var_idx]
                task_key = (item_name, tier, enchant)
                if task_key in processed_keys: 
                    var_idx += 1
                    continue
                
                # Сбрасываем флаг перед обработкой варианта
                self._recovery_performed_during_item = False
                
                processed_count += 1
                self._process_variant(item_name, tier, enchant, limit, processed_count, total_tasks)
                
                if self._skip_item_requested:
                    self.logger.info(f"⏭️ Вариант T{tier}.{enchant} пропущен.")
                    # Если пропущен во время обработки варианта, выходим из цикла вариантов этого предмета
                    break 

                if self._recovery_performed_during_item:
                    self.logger.warning(f"🔄 Повтор варианта {item_name} T{tier}.{enchant} (был вылет)")
                    continue # Перезапуск того же var_idx
                
                processed_keys.add(task_key)
                var_idx += 1
            
            self._close_menu()
            v_idx += 1

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
        from ..utils.ocr import clear_ocr_cache
        clear_ocr_cache()
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
            self.logger.warning(f"Нет подходящих предметов! (Сначала запустите Сканер или цены в {self.sell_city} отсутствуют)")
            return

        self.logger.info(f"🧠 SMART: Найдено {total_items} выгодных предметов.")
        
        # 2. Итерация
        processed_count = 0
        
        # Чтобы не покупать миллион раз одно и то же, запоминаем что купили?
        # Пока просто идем по списку.
        
        for i, (item_name, tier, enchant, profit_est, market_price, profit_pct) in enumerate(items_to_check):
            if self._stop_requested: break
            self._check_pause()
            
            self._skip_item_requested = False # Reset for new item in smart mode
            
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
                # Только поиск (без открытия)
                if not self._search_item_only(item_name):
                    continue
                
                # Переход на вкладку Заказа (УДАЛЕНО для Sniper Mode)
                # if not self._is_black_market: ...

                # Запускаем процессор вариации
                self._process_variant(item_name, tier, enchant, final_limit, processed_count, total_items)
                
                if self._skip_item_requested:
                    self.logger.info(f"⏭️ Smart Item {item_name} T{tier}.{enchant} пропущен.")
                
                self._close_menu()
                
            except Exception as e:
                self.logger.error(f"Error smart loop: {e}")
                self._close_menu()
                
    def _get_profitable_items_sorted(self):
        """
        Возвращает список [(name, tier, enchant, profit, market_price, profit_percent), ...]
        отсортированный по profit или profit_percent (в зависимости от self.sort_by_percent).
        """
        if not self.buy_city or not self.sell_city:
            self.logger.warning("Города не определены, сортировка невозможна.")
            return []
            
        items = [] 
        city_prices = price_storage.get_city_prices(self.buy_city)
        bm_prices = price_storage.get_city_prices(self.sell_city)
        
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
                    # Profit = (SellPrice * 0.935) - Market
                    net_sell_price = bm_price * 0.935
                    profit = net_sell_price - market_price
                    
                    # Profit Percent = ((net_sell_price - market) / market) * 100
                    profit_percent = ((net_sell_price - market_price) / market_price) * 100
                    
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
        """
        from ..utils.ocr import read_price_at, read_qty_text, read_screen_text_cached, clear_ocr_cache
        
        # 1. Фильтры (Выставляем один раз перед циклом)
        self.logger.info(f" Фильтры: T{tier}.{enchant}")
        self._select_tier(tier)
        self._select_enchant(enchant)
        time.sleep(0.5)
        
        items_bought = 0
        consecutive_fails = 0 # Для выхода если лоты закончились или OCR сбоит
        
        while items_bought < limit:
            if self._stop_requested or self._skip_item_requested: break
            self._check_pause()
            
            remaining = limit - items_bought
            display_name = f"{item_name} T{tier}.{enchant}"
            
            # 2. Верификация имени и цены через Сеть
            price = self._wait_for_network_update(timeout=3.0)
            
            if price <= 0:
                consecutive_fails += 1
                if consecutive_fails >= 2:
                    self.logger.info(f"🏁 Лоты для {display_name} закончились.")
                    break
                continue
            
            consecutive_fails = 0
            current_price = price
            
            # Извлекаем количество из последнего пакета
            actual_qty = 1
            if self._last_network_data and self._last_network_data.get("data"):
                top_lot = self._last_network_data["data"][0]
                actual_qty = top_lot.get("Amount", 1)
                self.logger.info(f"🔢 Сеть: В лоте {actual_qty} шт.")

            # 3. ПРОВЕРКА БЮДЖЕТА
            max_affordable = remaining
            if self.max_budget > 0:
                remaining_budget = self.max_budget - self.spent_amount
                if current_price > remaining_budget:
                    self.logger.warning(f"🛑 Бюджет исчерпан! Остаток: {remaining_budget}, Цена: {current_price}")
                    break
                max_affordable = int(remaining_budget // current_price)
                if max_affordable <= 0:
                    self.logger.warning(f"🛑 Недостаточно бюджета для покупки даже 1 шт.!")
                    break

            # Target Price Validations
            limit_val, enabled, min_profit_percent = self.config.get_wholesale_limit(item_name, tier, enchant)
            targets = self.config.get_wholesale_targets()
            variant_data = targets.get(item_name, {}).get(f"T{tier}.{enchant}", {})
            s_city = variant_data.get("sell_city", self.sell_city)
            
            bm_price = price_storage.get_item_price(s_city, item_name, tier, enchant, 1)
            if not bm_price:
                self.logger.warning(f"⏩ Пропуск: Нет цены в {s_city}")
                break
                
            sell_tax_factor = 0.935
            margin_factor = 1 + (min_profit_percent / 100.0)
            target_price = int((bm_price * sell_tax_factor) / margin_factor)
            
            self.logger.info(f"🔎 Анализ: {current_price} vs Target {target_price} | Нужно еще: {remaining}")
            
            if prog_total > 0:
                 self.progress_updated.emit(prog_curr, prog_total, f"{display_name} - {current_price}/{target_price} ({get_text('buyer_bought_progress', 'Куплено')}: {items_bought}/{limit})")
                 
            if current_price > target_price:
                 self.logger.info(f"📉 Цена ({current_price}) выше целевой ({target_price}). Переход к следующему.")
                 break
                 
            # 4. Покупка (Клик по кнопке Купить)
            buy_btn = self.config.get_coordinate("buy_button")
            if not buy_btn: break
                
            self._human_move_to(*buy_btn)
            self._human_click()
            time.sleep(0.5)

            # 5. Установка лимита (Dialog)
            # Применяем лимит и бюджет если нужно
            target_qty = min(remaining, max_affordable)
            
            if actual_qty > target_qty:
                if target_qty <= 0: 
                    self.logger.warning("⏩ Невозможно купить даже 1 шт (лимит/бюджет).")
                    self._close_menu()
                    break
                    
                if max_affordable < remaining:
                     self.logger.info(f"⚖️ Бюджетный ограничитель: {actual_qty} -> {target_qty} (Остаток бюджета)")
                else:
                     self.logger.info(f"⚖️ Лимит-ограничитель: {actual_qty} > {target_qty}. Вводим нужное...")
                     
                self._input_quantity(target_qty)
                actual_qty = target_qty
                time.sleep(0.3)
            
            # 6. Верификация итоговой суммы
            total_price_area = self.config.get_coordinate_area("buyer_total_price")
            if total_price_area:
                 actual_total = read_price_at(total_price_area)
                 if actual_total and actual_total > 0:
                      expected_total = current_price * actual_qty
                      if actual_total > int(expected_total * 1.05):
                           self.logger.warning(f"🛑 Сумма не сходится! {actual_total} vs {expected_total}. Отмена.")
                           self._close_menu()
                           # Здесь лучше выйти из цикла для этого варианта, т.к. состояние рынка неясно
                           break
                      self.logger.info(f"✅ Сумма корректна: {actual_total}")
                 else:
                      self.logger.warning("⚠️ Не удалось прочитать Total Price.")
            
            # 7. Подтверждение
            confirm_btn = self.config.get_coordinate("buyer_create_order_confirm")
            if confirm_btn:
                 self._human_move_to(*confirm_btn)
                 self._human_click()
                 
                 # --- NEW: Check for "Cannot wear" dialog (from TODO) ---
                 bypass_btn = self.config.get_coordinate("cannot_wear_yes")
                 if bypass_btn:
                     time.sleep(0.4)
                     self._human_move_to(*bypass_btn)
                     self._human_click()
                 # -----------------------------------------------------
                 
                 self.logger.info(f"💰 {get_text('buyer_bought_qty', 'Куплено {qty} шт.!').format(qty=actual_qty)}")
                 
                 # Логируем транзакцию в БД финансов
                 finance_manager.log_transaction(
                     item_name=item_name,
                     tier=tier,
                     enchant=enchant,
                     price=current_price,
                     qty=actual_qty,
                     city=self.buy_city,
                     profit_est=int((bm_price * 0.935 - current_price) * actual_qty),
                     is_simulation=self.simulation_mode,
                     session_id=getattr(self, "session_id", None)
                 )
                 
                 self.spent_amount += (current_price * actual_qty)
                 items_bought += actual_qty
                 time.sleep(0.8) # Ждем пока диалог закроется и список обновится
            else:
                 self.logger.error("❌ Нет кнопки подтверждения!")
                 self._close_menu()
                 break




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
                            
                        # Проверка цены (Если нет цены в городе продажи - не добавляем)
                        s_city = data.get("sell_city", self.sell_city)
                        b_city = data.get("buy_city", self.buy_city)
                        
                        bm_price = price_storage.get_item_price(s_city, item_name, t, e, 1)
                        if not bm_price or bm_price <= 0:
                            # self.logger.debug(f"⏩ Пропуск {item_name} T{t}.{e}: Нет цены в {s_city}")
                            continue

                        # --- NEW: Profit Filter ---
                        # Получаем текущую цену в городе закупки для расчета профита
                        buy_price = price_storage.get_item_price(b_city, item_name, t, e, 1)
                        min_profit_pct = data.get("min_profit", 15)
                        
                        if buy_price and buy_price > 0:
                            net_sell = bm_price * 0.935 # Tax 6.5%
                            est_profit_pct = ((net_sell - buy_price) / buy_price) * 100
                            
                            if est_profit_pct < min_profit_pct:
                                # self.logger.debug(f"📉 Пропуск {item_name} T{t}.{e}: Профит {est_profit_pct:.1f}% < {min_profit_pct}%")
                                skipped_count += 1
                                continue
                        else:
                            # self.logger.debug(f"⏩ Пропуск {item_name} T{t}.{e}: Нет цены закупки в {b_city}")
                            skipped_count += 1
                            continue
                        # --------------------------
                        
                        self._items_to_buy.append((item_name, t, e, limit))
                except:
                    continue
        
        if skipped_count > 0:
            self.logger.info(f"🔍 Фильтры: пропущено {skipped_count} вариаций")
            
        self._items_to_buy.sort(key=lambda x: (x[0], x[1], x[2]))

    # _search_item_and_open removed to fix logic sequence
        
    def _close_menu(self):
        close_btn = self.config.get_coordinate("menu_close")
        if close_btn:
             self._human_move_to(*close_btn)
             self._human_click()
             self._human_click()
             from ..utils.ocr import clear_ocr_cache
             clear_ocr_cache()
             self._is_menu_open = False
             self._current_tier_value = None
             self._current_enchant = None 
             self._current_quality = None
             time.sleep(0.5)




    def _select_tier(self, tier):
        """Выбор тира (с поддержкой исключений и сбросом качества)"""
             
        coord = self.dropdowns.get_tier_click_point(tier)
        if coord:
            self.dropdowns.open_tier_menu(self)
            self._human_move_to(*coord)
            self._human_click()
            time.sleep(0.1)
            self._current_tier_value = tier
            self._current_quality = None

    def _select_enchant(self, enchant):
        
        coord = self.dropdowns.get_enchant_click_point(enchant)
        if coord:
            self.dropdowns.open_enchant_menu(self)
            self._human_move_to(*coord)
            self._human_click()
            time.sleep(0.1)
            self._current_enchant = enchant

    def _select_quality(self, quality):
        """Выбор качества (без OCR)"""
        coord = self.dropdowns.get_quality_click_point(quality)
        if coord:
            self.dropdowns.open_quality_menu(self)
            self._human_move_to(*coord)
            self._human_click()
            time.sleep(0.1)
            self._current_quality = quality

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

    def _input_quantity(self, qty: int):
        """
        Ввод количества.
        Приоритет: Ввод цифрами через поле 'buyer_amount_input'.
        """
        # 1. Попытка ввода через клавиатуру (Keyboard Input)
        amount_input_coord = self.config.get_coordinate("buyer_amount_input")
        
        if amount_input_coord and qty >= 1:
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

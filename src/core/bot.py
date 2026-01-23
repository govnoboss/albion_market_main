"""
Логика бота
Простой перебор предметов из базы с реалистичным поведением
"""

import time
import random
import math
import pyautogui
# from pynput.keyboard import Controller, Key  # Можно использовать для ввода, если pyautogui подведет
from PyQt6.QtCore import QThread, pyqtSignal

from ..utils.config import get_config
from ..utils.logger import get_logger
from .interaction import DropdownSelector

class MarketBot(QThread):
    """Рабочий поток бота"""
    
    # Сигналы для UI
    progress_updated = pyqtSignal(int, int, str)  # current, total, item_name
    finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._is_running = False
        self._is_paused = False
        self._stop_requested = False
        self.config = get_config()
        self.logger = get_logger()
        # self.keyboard = Controller()
        self.dropdowns = DropdownSelector()
        self._first_item_processed = False  # Флаг для первого предмета
        
        # Текущее состояние фильтров (для оптимизации кликов)
        self._current_tier = None
        self._current_enchant = None
        self._current_quality = None
        self._last_detected_quality = None  # Для отслеживания форсирования качества
        
    def run(self):
        """Основной цикл (Запускается в отдельном потоке)"""
        self._is_running = True
        self._stop_requested = False
        self._is_paused = False
        self._first_item_processed = False # Сбрасываем флаг при новом запуске
        
        # Сброс состояния фильтров
        self._current_tier = None
        self._current_enchant = None
        self._current_quality = None
        self._last_detected_quality = None
        self._current_city = "Unknown"  # Текущий город
        self._safe_menu_snapshot = None # Сброс снимка меню
        self._action_timings = {} # Статистика времени действий
        self._recovery_attempts = 0 # Счетчик попыток восстановления меню
        
        # Задержка перед стартом (по просьбе пользователя)
        self.logger.info("⏳ Задержка старта 1 сек...")
        time.sleep(1.0)
        
        # Определение текущего города через OCR
        self._detect_current_city()
        
        items = self.config.get_known_items()
        total_items = len(items)
        
        if total_items == 0:
            self.logger.warning("База предметов пуста! Добавьте предметы во вкладке 'База'.")
            self._is_running = False
            self.finished.emit()
            return
            
        self.logger.info(f"Запуск перебора {total_items} предметов...")
        
        for i, item_name in enumerate(items):
            # Проверка остановки
            if self._stop_requested:
                break
                
            # Проверка паузы
            while self._is_paused:
                if self._stop_requested: break
                time.sleep(0.1)
            
            # Обновление прогресса
            self.progress_updated.emit(i + 1, total_items, item_name)
            self.logger.info(f"[{i+1}/{total_items}] Обработка: {item_name}")
            
            # --- Действия ---
            try:
                self._process_item(item_name)
                self._first_item_processed = True # Отмечаем, что хотя бы один предмет прошел
            except Exception as e:
                self.logger.error(f"Ошибка при обработке '{item_name}': {e}")
            
            # Пауза между предметами убрана - переходим сразу
            
        self.logger.info("Цикл завершен")
        self._print_statistics() # Выводим статистику времени
        self._is_running = False
        self.finished.emit()
        
    def _record_time(self, action_name: str, duration_ms: float):
        """Записать время действия в статистику"""
        if action_name not in self._action_timings:
            self._action_timings[action_name] = {"total_ms": 0.0, "count": 0}
        self._action_timings[action_name]["total_ms"] += duration_ms
        self._action_timings[action_name]["count"] += 1

    def _print_statistics(self):
        """Вывод статистики времени в логи"""
        if not self._action_timings:
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
        
    def stop(self):
        """Остановить бота"""
        self._stop_requested = True
        
    def pause(self):
        """Поставить на паузу / Снять с паузы"""
        self._is_paused = not self._is_paused
        status = "паузе" if self._is_paused else "работе"
        self.logger.info(f"Бот на {status}")

    def _check_pause(self):
        """Блокирует выполнение, пока бот на паузу"""
        if not self._is_paused:
            return
            
        self.logger.info("⏸️ Работа приостановлена (Пауза)...")
        while self._is_paused:
            if self._stop_requested: 
                break
            time.sleep(0.1)
        self.logger.info("▶️ Работа возобновлена")

    # === Реалистичные действия ===

    def _human_move_to(self, x: int, y: int):
        """Реалистичное движение мыши к координатам с небольшим разбросом"""
        if self._stop_requested: return
        self._check_pause()
        
        start_time = time.time()
        
        start_x, start_y = pyautogui.position()
        
        # Добавляем случайный разброс -5..+5 пикселей (имитация дрожания руки)
        offset_x = random.randint(-5, 5)
        offset_y = random.randint(-5, 5)
        target_x = x + offset_x
        target_y = y + offset_y
        
        # Случайная длительность движения (ускоренно)
        min_duration = 0.03
        max_duration = 0.08
        duration = random.uniform(min_duration, max_duration)
        
        # Используем tweening function для плавного разгона и торможения
        pyautogui.moveTo(target_x, target_y, duration=duration, tween=pyautogui.easeInOutQuad)
        
        self._record_time("Мышь: Движение", (time.time() - start_time) * 1000)

    def _human_click(self):
        """Быстрый клик"""
        if self._stop_requested: return
        self._check_pause()
        start_time = time.time()
        pyautogui.click()
        self._record_time("Мышь: Клик", (time.time() - start_time) * 1000)

    def _human_type(self, text: str):
        """Имитация ввода текста через pynput (более надежная эмуляция клавиатуры)"""
        if self._stop_requested: return
        self._check_pause()
        
        start_time = time.time()
        from pynput.keyboard import Controller
        keyboard = Controller()
        
        # Ввод текста посимвольно для большей совместимости с играми
        for char in text:
            if self._stop_requested: return
            keyboard.type(char)
            # Случайная задержка (ускорено)
            time.sleep(random.uniform(0.01, 0.03))
        
        self._record_time("Ввод текста", (time.time() - start_time) * 1000)

    def _check_market_is_open(self) -> bool:
        """Проверка, что окно рынка открыто (Pixel Match or OCR)"""
        start_time = time.time()
        area = self.config.get_coordinate_area("market_menu_check")
        
        from .validator import ScreenValidator
        is_open, msg = ScreenValidator.check_market_open(area)
        
        self._record_time("Валидация: Рынок", (time.time() - start_time) * 1000)
        
        if is_open:
            self.logger.debug(f"Market Validation PASS: {msg}")
            return True
        else:
            self.logger.warning(f"Market Validation FAIL: {msg}")
            return False
            
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
            from ..utils.image_utils import compare_images_rms
            
            bbox = (area['x'], area['y'], area['x'] + area['w'], area['y'] + area['h'])
            current_img = ImageGrab.grab(bbox=bbox)
            
            if self._safe_menu_snapshot.size != current_img.size:
                 current_img = current_img.resize(self._safe_menu_snapshot.size)

            rms = compare_images_rms(self._safe_menu_snapshot, current_img)
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

    def _check_market_safe_state(self):
        """
        Safety Guard: Проверка, что окно РЫНКА (Main) открыто.
        Используется перед поиском, очисткой и кнопкой купить.
        """
        if self._stop_requested: return
        if self._is_paused: return
        
        # Используем существующий метод проверки
        if not self._check_market_is_open():
             self.logger.warning("⏸️ ПАУЗА: Окно рынка закрыто!")
             self.logger.warning(f"📍 Текущий предмет: {self._current_item_name}")
             self.logger.warning("👆 Откройте рынок заново и нажмите F6 для продолжения.")
             self._is_paused = True

    def _detect_current_city(self):
        """Определить текущий город через OCR названия рынка"""
        start_time = time.time()
        VALID_CITIES = [
            "Bridgewatch", "Martlock", "Lymhurst", "Thetford", 
            "Fort Sterling", "Caerleon", "Brecilien", "Black Market"
        ]
        
        area = self.config.get_coordinate_area("market_name_area")
        if not area:
            self.logger.warning("Область 'Название рынка' не задана! Город: Unknown")
            self._current_city = "Unknown"
            return
        
        from ..utils.ocr import read_screen_text
        from difflib import get_close_matches
        
        # Читаем название рынка (на английском)
        city_text = read_screen_text(area['x'], area['y'], area['w'], area['h'], lang='eng')
        city_text = city_text.strip()
        self._record_time("OCR: Город", (time.time() - start_time) * 1000)
        
        # Строгая проверка с нечетким поиском (на случай ошибок OCR)
        matches = get_close_matches(city_text, VALID_CITIES, n=1, cutoff=0.6)
        
        if matches:
            self._current_city = matches[0]
            self.logger.info(f"🏪 Текущий город: {self._current_city} (OCR: '{city_text}')")
        else:
            self._current_city = "Unknown"
            self.logger.error(f"🛑 Неизвестный город: '{city_text}'! Допустимые: {', '.join(VALID_CITIES)}")
            self.logger.error("Проверьте область OCR 'Название рынка' или переключитесь на английский язык в игре.")
            # Останавливаем бота, так как город критически важен для базы
            self._stop_requested = True
            self.finished.emit()

    def _wait_for_search_result(self, timeout: float = 3.0):
        """
        Ждем появления результатов поиска.
        Проверяем область buy_button на изменение (появление предмета).
        """
        from PIL import ImageGrab
        import time
        
        buy_coord = self.config.get_coordinate("buy_button")
        if not buy_coord:
            time.sleep(0.5)  # Fallback
            return
        
        # Область вокруг кнопки для проверки
        x, y = buy_coord
        check_area = (x - 30, y - 10, x + 30, y + 10)
        
        # Делаем начальный снимок
        initial_screenshot = ImageGrab.grab(bbox=check_area)
        initial_pixels = list(initial_screenshot.getdata())
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self._stop_requested:
                return
            self._check_pause()
            
            time.sleep(0.1)
            
            # Новый снимок
            current_screenshot = ImageGrab.grab(bbox=check_area)
            current_pixels = list(current_screenshot.getdata())
            
            # Сравниваем пиксели (простое сравнение)
            if current_pixels != initial_pixels:
                self.logger.debug("Результаты поиска загружены")
                self._record_time("Ожидание: Поиск", (time.time() - start_time) * 1000)
                return
        
        self._record_time("Ожидание: Поиск", (time.time() - start_time) * 1000)
        self.logger.debug("Таймаут ожидания результатов поиска")

    def _verify_item_name_with_retry(self, expected_name: str, max_retries: int = 2) -> bool:
        """
        Проверка имени предмета с повторными попытками через сортировку.
        1. Считывает OCR.
        2. Сравнивает (Fuzzy Match >= 90%).
        3. Если не подходит -> Закрывает меню, Жмет Сортировку, Жмет Купить, Повторяет.
        """
        from difflib import SequenceMatcher
        import re
        from ..utils.ocr import read_screen_text
        
        # Получаем координаты заранее, чтобы не дергать config в цикле
        item_name_area = self.config.get_coordinate_area("item_name_area")
        sort_btn = self.config.get_coordinate("item_sort")
        buy_btn = self.config.get_coordinate("buy_button")
        menu_close = self.config.get_coordinate("menu_close")
        
        if not item_name_area:
            self.logger.warning("Пропуск проверки имени: не задана область 'item_name_area'")
            return True
        
        expected_clean = expected_name.strip().lower()
        
        for attempt in range(max_retries + 1):
            self._check_pause()
            # 1. Считываем OCR
            # 1. Считываем OCR (rus+eng для поддержки всех предметов)
            ocr_name = read_screen_text(
                item_name_area['x'], item_name_area['y'],
                item_name_area['w'], item_name_area['h'],
                lang='rus+eng'
            )
            # Убираем скобки
            ocr_name_clean = re.sub(r'\s*\([^)]*\)\s*', '', ocr_name).strip()
            ocr_clean = ocr_name_clean.lower()
            
            # 2. Сравниваем
            similarity = SequenceMatcher(None, expected_clean, ocr_clean).ratio()
            
            # Порог 90%
            if similarity >= 0.90:
                # Успех
                # self.logger.debug(f"Имя совпало: '{ocr_name_clean}' ({similarity:.2f})")
                return True
            
            # Неудача
            self.logger.warning(f"⚠️ Имя не совпадает (Попытка {attempt+1}/{max_retries+1}): OCR='{ocr_name_clean}' vs Expected='{expected_name}' (Sim: {similarity:.2f})")
            
            # Если это последняя попытка - выходим
            if attempt == max_retries:
                # Закрываем, чтобы не мешать
                if menu_close:
                    self._human_move_to(*menu_close)
                    self._human_click()
                    time.sleep(0.3)
                
                self.logger.error(f"🛑 Предмет '{expected_name}' не найден после сортировок. Пропускаем.")
                return False
            
            # --- ЛОГИКА RETRY (СОРТИРОВКА) ---
            self.logger.info("🔄 Пробуем найти через сортировку...")
            
            # 1. Закрыть меню предмета
            if menu_close:
                self._human_move_to(*menu_close)
                self._human_click()
                time.sleep(0.5)
            
            # 2. Нажать сортировку
            if sort_btn:
                self._human_move_to(*sort_btn)
                self._human_click()
                # Ждем пока обновится список (можно использовать то же ожидание, что и при поиске)
                self._wait_for_search_result(timeout=2.0)
                time.sleep(0.5) # Небольшая пауза после сортировки
            else:
                self.logger.error("Кнопка 'Сортировка' не задана! Не могу перебрать варианты.")
                return False
                
            # 3. Нажать Купить (чтобы открыть верхний предмет)
            if buy_btn:
                self._human_move_to(*buy_btn)
                self._human_click()
                # Ждем открытия
                time.sleep(1.0)
            
        return False

    def _process_item(self, name: str):
        """Логика обработки одного предмета"""
        if self._stop_requested: return
        
        # 0. ПРОВЕРКА ЭКРАНА (Safety Check) - с повтором до 10 секунд
        market_found = False
        for attempt in range(10):
            if self._stop_requested: return
            self._check_pause()
            
            if self._check_market_is_open():
                market_found = True
                break
            else:
                self.logger.warning(f"⏳ Окно рынка не найдено. Повтор через 1 сек... ({attempt+1}/10)")
                time.sleep(1.0)
        
        if not market_found:
            self.logger.error("🛑 ОШИБКА: Окно рынка не обнаружено после 10 попыток! Бот остановлен.")
            self._stop_requested = True
            return

        self.logger.info(f"--- Начало обработки: {name} ---")
        
        self._consecutive_excellent_streak = 0 # Сброс стрика для нового предмета
        self._current_item_name = name # Сохраняем имя для логики смещений
        self._recovery_attempts = 0 # Сброс счетчика восстановлений
        self._safe_menu_snapshot = None # Сброс снимка меню (на всякий случай)
        
        # 1. Клик на Очистка поиска
        self._check_market_safe_state()
        if self._stop_requested: return

        search_clear_coord = self.config.get_coordinate("search_clear")
        if search_clear_coord:
            self._human_move_to(*search_clear_coord)
            self._human_click()
        else:
            self.logger.debug("Координата 'search_clear' не задана, пропускаем")
            
        # 2. Клик на Поиск
        self._check_market_safe_state()
        if self._stop_requested: return

        search_coord = self.config.get_coordinate("search_input")
        if not search_coord:
            self.logger.error("Не задана координата '🔍 Поле поиска'!")
            self._stop_requested = True
            return
        
        self._human_move_to(*search_coord)
        self._human_click()
        
        # 3. Ввод предмета (pynput)
        self.logger.debug(f"Ввод имени: {name}")
        self._human_type(name)
        pyautogui.press('enter')
        self.logger.debug("Нажат Enter, ждем результаты...")
        
        # 4. Ждем появления кнопки Купить (вместо фиксированной задержки)
        self._check_market_safe_state()
        if self._stop_requested: return

        buy_coord = self.config.get_coordinate("buy_button")
        if buy_coord:
            # Ждем пока кнопка станет кликабельной (появится предмет)
            self._wait_for_search_result(timeout=3.0)
            self._human_move_to(*buy_coord)
            self._human_click()
            self.logger.debug("Клик 'Купить'")
            # Ждем окна покупки
            time.sleep(random.uniform(0.5, 0.8))
        else:
             self.logger.error("Не задана координата '💰 Кнопка Купить'!")
             
        # 5. Условное действие: Раскрыть окно предмета (ПЕРЕД проверкой имени)
        # Проверяем, нужно ли раскрывать - если цена видна, меню уже открыто
        need_expand = True
        from ..utils.ocr import read_price_at
        area = self.config.get_coordinate_area("best_price_area")
        if area:
            existing_price = read_price_at(area)
            if existing_price is not None and existing_price > 0:
                self.logger.debug(f"Меню уже раскрыто (цена: {existing_price})")
                need_expand = False
        
        if need_expand and not self._first_item_processed:
            expand_coord = self.config.get_coordinate("item_expand")
            if expand_coord:
                self.logger.info("Раскрываем детали предмета (первый запуск)")
                self._human_move_to(*expand_coord)
                self._human_click()
                time.sleep(random.uniform(0.5, 0.8))
            else:
                self.logger.warning("Координата 'Раскрыть окно' не задана")

        # 4.1. Проверка названия предмета через OCR (с retry через сортировку)
        if not self._verify_item_name_with_retry(name):
            return  # Предмет не найден после всех попыток

        # 5.1. Клик на вкладку "Заказ на покупку" (Новая фича)
        order_tab_coord = self.config.get_coordinate("create_buy_order")
        if order_tab_coord:
            self.logger.info("Переключение на вкладку 'Заказ на покупку'")
            self._human_move_to(*order_tab_coord)
            self._human_click()
            time.sleep(random.uniform(0.4, 0.6))
                
        # 6. Сброс фильтров (Базовое состояние: T4, E0, Q1)
        self._capture_item_menu_state() # Захватываем "эталон" меню перед работой
        self._reset_filters()
        
        # 7. Перебор вариаций (Тиры -> Энчанты -> Качество)
        self._scan_variations()
        
        # 8. Закрыть меню предмета (Возврат к списку)
        close_coord = self.config.get_coordinate("menu_close")
        if close_coord:
            self._human_move_to(*close_coord)
            self._human_click()
            time.sleep(random.uniform(0.2, 0.4))
        else:
             self.logger.warning("Координата 'Закрыть меню' не задана!")
             
        self.logger.info(f"--- Завершено: {name} ---")

    def _reset_filters(self):
        """Сброс фильтров в базовое состояние: T4, En0, Normal"""
        self.logger.info("Сброс фильтров в T4.0 Normal")
        
        # Сбрасываем внутреннее состояние, так как при открытии нового предмета
        # фильтры в игре могут сброситься или быть непредсказуемыми.
        self._current_tier = None
        self._current_enchant = None
        self._current_quality = None
        self._last_detected_quality = None
        
        # Используем оптимизированные методы выбора
        self._select_tier(4)
        self._select_enchant(0)
        self._select_quality(1)


    def _scan_variations(self):
        """
        Перебор вариантов согласно фильтрам сканирования.
        Использует Opportunistic Scanning: при смене Tier фиксирует
        цену унаследованного Enchant (если он в фильтрах).
        """
        if self._stop_requested: return
        
        filters = self.config.get_scan_filters()
        self.logger.info(f"Начинаем перебор вариаций: {filters}")
        
        # Отслеживание уже отсканированных комбинаций (tier, enchant, quality)
        scanned_variants = set()
        
        # Последняя известная цена (для детекции изменений)
        last_price = 0
        
        # Текущий энчант на экране (после reset_filters = 0)
        current_screen_enchant = 0
        
        tiers = filters.get('tiers', [])
        enchants = filters.get('enchants', [])
        qualities = filters.get('qualities', [])
        target_quality = qualities[0] if qualities else 1
        
        # 1. Цикл по Тирам
        for tier_idx, tier in enumerate(tiers):
            if self._stop_requested: break
            
            # Safety Guard: Проверяем, что меню предмета всё еще открыто
            self._check_safe_state()
            if self._stop_requested: break
            
            # Выбираем Tier
            tier_changed = self._current_tier != tier
            self._select_tier(tier)
            
            # === OPPORTUNISTIC CAPTURE ===
            # Если Tier изменился и текущий энчант на экране входит в фильтры
            if tier_changed and tier_idx > 0 and current_screen_enchant in enchants:
                quality = target_quality
                if True: # Loop removed, single pass
                    if self._stop_requested: break
                    
                    variant_key = (tier, current_screen_enchant, quality)
                    if variant_key in scanned_variants:
                        continue
                    
                    # Выбираем качество (если нужно)
                    self._select_quality(quality)
                    
                    # Ждем обновления цены (Tier только что сменился, цена должна измениться)
                    self.logger.info(f"📸 Opportunistic: T{tier}.{current_screen_enchant} Q{quality}")
                    
                    # Быстрый пропуск: если прошлая цена была 0, не ждем долго (0.8с), иначе 3.0с
                    timeout_val = 0.8 if last_price == 0 else 3.0
                    current_price = self._wait_for_price_update(last_price, timeout=timeout_val)
                    
                    if current_price > 0:
                        self.logger.info(f"💰 Цена: {current_price}")
                        
                        save_quality = self._current_quality if self._current_quality else quality
                        
                        # Сохраняем цену в базу
                        from ..utils.price_storage import get_price_storage
                        get_price_storage().save_price(
                            self._current_city, self._current_item_name,
                            tier, current_screen_enchant, save_quality, current_price
                        )
                        
                        # Если мы сохранили цену для Q3 (вместо Q1), то пометим Q3 как отсканированное
                        actual_variant_key = (tier, current_screen_enchant, save_quality)
                        scanned_variants.add(actual_variant_key)
                        
                    else:
                        self.logger.warning(f"⚠️ Цена не найдена (opportunistic)")
                    
                    # Помечаем и текущую "целевую" вариацию как пройденную, чтобы не стопориться
                    scanned_variants.add(variant_key)
                    last_price = current_price
            
            # 2. Цикл по Зачарованиям
            for enchant in enchants:
                if self._stop_requested: break
                
                # Safety Guard
                self._check_safe_state()
                if self._stop_requested: break
                
                # 3. Цикл по Качеству (УБРАН)
                quality = target_quality
                if True: # Loop removed, single pass
                    if self._stop_requested: break
                    
                    variant_key = (tier, enchant, quality)
                    
                    # Пропускаем если уже отсканировано (opportunistic или ранее)
                    if variant_key in scanned_variants:
                        self.logger.debug(f"⏭️ Пропуск: T{tier}.{enchant} Q{quality} (уже есть)")
                        continue
                    
                    # Выбираем Enchant
                    self._select_enchant(enchant)
                    current_screen_enchant = enchant  # Обновляем текущий экранный энчант
                    
                    # Выбираем Quality
                    self._select_quality(quality)
                    
                    # === SMART SCANNING LOGIC ===
                    self.logger.debug(f">>> Сканирование: T{tier}.{enchant} Q{quality} (Old Price: {last_price})")
                    
                    # Ждем обновления цены
                    # Быстрый пропуск: если прошлая цена была 0, не ждем долго (0.8с), иначе 3.0с
                    timeout_val = 0.8 if last_price == 0 else 3.0
                    current_price = self._wait_for_price_update(last_price, timeout=timeout_val)
                    
                    # Логируем результат
                    if current_price > 0:
                         self.logger.info(f"💰 Цена: {current_price}")
                         
                         # Определяем качество для сохранения.
                         # Используем фактическое качество на экране (_current_quality), 
                         # если оно определено, иначе fallback на целевое (quality).
                         save_quality = self._current_quality if self._current_quality else quality
                         
                         # Сохраняем цену в базу
                         from ..utils.price_storage import get_price_storage
                         get_price_storage().save_price(
                             self._current_city, self._current_item_name,
                             tier, enchant, save_quality, current_price
                         )
                         
                         # Помечаем фактическую вариацию как отсканированную
                         actual_variant_key = (tier, enchant, save_quality)
                         scanned_variants.add(actual_variant_key)
                         
                    else:
                         self.logger.warning(f"⚠️ Цена не найдена или не обновилась (T{tier}.{enchant} Q{quality})")

                    # Запоминаем текущую целевую вариацию
                    scanned_variants.add(variant_key)
                    last_price = current_price


    def _wait_for_price_update(self, old_price: int, timeout: float = 3.0) -> int:
        """
        Ждет, пока цена визуально изменится по сравнению с old_price.
        Если цена исчезает (None) -> продолжаем ждать (загрузка).
        Если цена равна старой -> продолжаем ждать (лаг).
        Если тайм-аут -> возвращаем 0.
        """
        from ..utils.ocr import read_price_at
        
        area = self.config.get_coordinate_area("best_price_area")
        if not area:
            self.logger.error("Не задана область цены 'best_price_area'!")
            return 0

        start_time = time.time()
        same_price_start = None # Время начала стабильного совпадения цены
        
        while time.time() - start_time < timeout:
            if self._stop_requested: return 0
            self._check_pause()
            
            # Считываем цену
            price = read_price_at(area)
            
            # 1. Если цена None (не распозналась или пусто) -> Ждем
            if price is None:
                # self.logger.debug("Цена: None (Loading...)")
                same_price_start = None # Сброс стабильности
                time.sleep(0.1)
                continue
                
            # 2. Если цена новая -> УСПЕХ
            if price != old_price:
                self.logger.debug(f"✅ Цена обновилась: {old_price} -> {price}")
                self._record_time("Ожидание: Цена", (time.time() - start_time) * 1000)
                return price
                
            # 3. Если цена совпадает со старой
            if price == old_price:
                # Если мы видим одну и ту же цену уже более 1.0 секунды -> считаем что она не изменилась
                current_time = time.time()
                if same_price_start is None:
                    same_price_start = current_time
                
                if current_time - same_price_start > 1.0:
                    self.logger.info(f"✅ Цена стабильна (не изменилась): {price}")
                    self._record_time("Ожидание: Цена", (time.time() - start_time) * 1000)
                    return price
                    
                time.sleep(0.1)
                continue
            
        # 4. Таймаут
        self._record_time("Ожидание: Цена", (time.time() - start_time) * 1000)
        self.logger.warning(f"⏰ Таймаут ожидания цены! (Old: {old_price}). Возвращаем 0.")
        return 0


    def _select_tier(self, tier: int):
        """Выбрать тир, если он отличается от текущего"""
        if self._current_tier == tier:
            return # Уже выбран
            
        start_time = time.time()
        anchor = self.config.get_coordinate("tier_dropdown")
        if not anchor: return
        
        self.logger.debug(f"Выбор тира: {tier}")
        # 1. Открыть меню
        self._human_move_to(*anchor)
        self._human_click()
        
        # 2. Кликнуть пункт
        # Передаем текущий энчант, чтобы корректно обработать исключения (смещение)
        point = self.dropdowns.get_tier_click_point(tier, self._current_item_name, self._current_enchant)
        if point:
            self._human_move_to(*point)
            self._human_click()
            self._current_tier = tier # Запомнить
            self._current_quality = None # Сброс качества (игра может поменять)
        
        self._record_time("Выбор: Тир", (time.time() - start_time) * 1000)

    def _select_enchant(self, enchant: int):
        """Выбрать зачарование, если оно отличается от текущего"""
        if self._current_enchant == enchant:
            return # Уже выбран
            
        start_time = time.time()
        anchor = self.config.get_coordinate("enchant_dropdown")
        if not anchor: return
        
        self.logger.debug(f"Выбор чар: {enchant}")
        # 1. Открыть меню
        self._human_move_to(*anchor)
        self._human_click()
        
        # 2. Кликнуть пункт
        point = self.dropdowns.get_enchant_click_point(enchant)
        if point:
             self._human_move_to(*point)
             self._human_click()
             self._current_enchant = enchant # Запомнить
             self._current_quality = None # Сброс качества (игра может поменять)
        
        self._record_time("Выбор: Чары", (time.time() - start_time) * 1000)

    def _select_quality(self, quality: int) -> bool:
        """
        Выбрать качество с проверкой OCR и эвристикой.
        """
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

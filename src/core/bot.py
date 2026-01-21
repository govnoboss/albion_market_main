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
        
        # Задержка перед стартом (по просьбе пользователя)
        self.logger.info("⏳ Задержка старта 2 сек...")
        time.sleep(2.0)
        
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
            
            # Пауза между предметами
            time.sleep(random.uniform(1.0, 2.0))
            
        self.logger.info("Цикл завершен")
        self._is_running = False
        self.finished.emit()
        
    def stop(self):
        """Остановить бота"""
        self._stop_requested = True
        
    def pause(self):
        """Поставить на паузу / Снять с паузы"""
        self._is_paused = not self._is_paused
        status = "паузе" if self._is_paused else "работе"
        self.logger.info(f"Бот на {status}")

    # === Реалистичные действия ===

    def _human_move_to(self, x: int, y: int):
        """Реалистичное движение мыши к координатам с небольшим разбросом"""
        if self._stop_requested: return
        
        start_x, start_y = pyautogui.position()
        
        # Добавляем случайный разброс -5..+5 пикселей (имитация дрожания руки)
        offset_x = random.randint(-5, 5)
        offset_y = random.randint(-5, 5)
        target_x = x + offset_x
        target_y = y + offset_y
        
        # Случайная длительность движения (зависит от расстояния)
        dist = math.hypot(target_x - start_x, target_y - start_y)
        min_duration = 0.2
        max_duration = max(0.4, dist / 1500.0) # Чем дальше, тем дольше
        duration = random.uniform(min_duration, max_duration)
        
        # Используем tweening function для плавного разгона и торможения
        pyautogui.moveTo(target_x, target_y, duration=duration, tween=pyautogui.easeInOutQuad)

    def _human_click(self):
        """Реалистичный клик"""
        if self._stop_requested: return
        time.sleep(random.uniform(0.05, 0.15))
        pyautogui.click()
        time.sleep(random.uniform(0.05, 0.1))

    def _human_type(self, text: str):
        """Имитация ввода текста через pynput (более надежная эмуляция клавиатуры)"""
        if self._stop_requested: return
        
        from pynput.keyboard import Controller
        keyboard = Controller()
        
        # Ввод текста посимвольно для большей совместимости с играми
        for char in text:
            if self._stop_requested: return
            keyboard.type(char)
            # Случайная задержка (ускорено)
            time.sleep(random.uniform(0.01, 0.03))

    def _check_market_is_open(self) -> bool:
        """Проверка, что окно рынка открыто (Pixel Match or OCR)"""
        area = self.config.get_coordinate_area("market_menu_check")
        
        from .validator import ScreenValidator
        is_open, msg = ScreenValidator.check_market_open(area)
        
        if is_open:
            self.logger.debug(f"Market Validation PASS: {msg}")
            return True
        else:
            self.logger.warning(f"Market Validation FAIL: {msg}")
            return False

    def _process_item(self, name: str):
        """Логика обработки одного предмета"""
        if self._stop_requested: return
        
        # 0. ПРОВЕРКА ЭКРАНА (Safety Check)
        if not self._check_market_is_open():
            self.logger.error("🛑 ОШИБКА: Окно рынка не обнаружено! Бот поставлен на паузу.")
            # Пауза и выход из функции
            self.pause() 
            return

        self.logger.info(f"--- Начало обработки: {name} ---")
        
        self._consecutive_excellent_streak = 0 # Сброс стрика для нового предмета
        self._current_item_name = name # Сохраняем имя для логики смещений
        
        # 1. Клик на Очистка поиска
        search_clear_coord = self.config.get_coordinate("search_clear")
        if search_clear_coord:
            self._human_move_to(*search_clear_coord)
            self._human_click()
            time.sleep(random.uniform(0.2, 0.4))
        else:
            self.logger.debug("Координата 'search_clear' не задана, пропускаем")
            
        # 2. Клик на Поиск
        search_coord = self.config.get_coordinate("search_input")
        if not search_coord:
            self.logger.error("Не задана координата '🔍 Поле поиска'!")
            self._stop_requested = True
            return
            
        self._human_move_to(*search_coord)
        self._human_click()
        time.sleep(random.uniform(0.2, 0.4))
        
        # 3. Ввод предмета (pynput)
        self.logger.debug(f"Ввод имени: {name}")
        self._human_type(name)
        time.sleep(random.uniform(0.3, 0.5))
        pyautogui.press('enter')
        self.logger.debug("Нажат Enter, ждем результаты...")
        time.sleep(random.uniform(0.8, 1.2)) # Ждем прогрузки поиска
        
        # 4. Клик Купить
        buy_coord = self.config.get_coordinate("buy_button")
        if buy_coord:
             self._human_move_to(*buy_coord)
             self._human_click()
             self.logger.debug("Клик 'Купить'")
             time.sleep(random.uniform(1.0, 1.5)) # Ждем окна покупки
        else:
             self.logger.error("Не задана координата '💰 Кнопка Купить'!")
             
        # 5. Условное действие: Раскрыть окно предмета
        if not self._first_item_processed:
            expand_coord = self.config.get_coordinate("item_expand")
            if expand_coord:
                self.logger.info("Раскрываем детали предмета (первый запуск)")
                self._human_move_to(*expand_coord)
                self._human_click()
                time.sleep(random.uniform(0.5, 0.8))
            else:
                self.logger.warning("Координата 'Раскрыть окно' не задана")
        
        # 5.1. Клик на вкладку "Заказ на покупку" (Новая фича)
        order_tab_coord = self.config.get_coordinate("create_buy_order")
        if order_tab_coord:
            self.logger.info("Переключение на вкладку 'Заказ на покупку'")
            self._human_move_to(*order_tab_coord)
            self._human_click()
            time.sleep(random.uniform(0.4, 0.6))
                
        # 6. Сброс фильтров (Базовое состояние: T4, E0, Q1)
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
        
        # --- Tier 4 ---
        # TODO: Можно тоже заменить на _select_tier(4) если там будет проверка
        tier_anchor = self.config.get_coordinate("tier_dropdown")
        if tier_anchor:
            self._human_move_to(*tier_anchor)
            self._human_click()
            time.sleep(random.uniform(0.3, 0.5))
            
            tier_point = self.dropdowns.get_tier_click_point(4)
            if tier_point:
                self._human_move_to(*tier_point)
                self._human_click()
                time.sleep(random.uniform(0.3, 0.5))
                self._current_tier = 4 # Обновляем состояние
        
        # --- Enchant 0 ---
        enchant_anchor = self.config.get_coordinate("enchant_dropdown")
        if enchant_anchor:
            self._human_move_to(*enchant_anchor)
            self._human_click()
            time.sleep(random.uniform(0.3, 0.5))
            
            enchant_point = self.dropdowns.get_enchant_click_point(0)
            if enchant_point:
                self._human_move_to(*enchant_point)
                self._human_click()
                time.sleep(random.uniform(0.3, 0.5))
                self._current_enchant = 0 # Обновляем состояние
            
        # --- Quality Normal (1) ---
        # Используем умный метод с OCR проверкой
        self._current_quality = None # Форсируем выбор
        self._select_quality(1)

    def _scan_variations(self):
        """Перебор вариантов согласно фильтрам сканирования"""
        if self._stop_requested: return
        
        filters = self.config.get_scan_filters()
        self.logger.info(f"Начинаем перебор вариаций: {filters}")
        
        # 1. Цикл по Тирам
        for tier in filters.get('tiers', []):
            if self._stop_requested: break
            self._select_tier(tier)
            
            # 2. Цикл по Зачарованиям
            for enchant in filters.get('enchants', []):
                if self._stop_requested: break
                self._select_enchant(enchant)
                
                # 3. Цикл по Качеству
                for quality in filters.get('qualities', []):
                    if self._stop_requested: break
                    
                    self._select_quality(quality)
                    
                    # ПЛЕЙСХОЛДЕР ДЛЯ ОПЕРАЦИИ (Scan/Buy)
                    self.logger.debug(f">>> Сканирование: T{tier}.{enchant} Q{quality}")
                    # Здесь будет вызов проверок цены и покупки
                    # ...
                    
                    time.sleep(0.5) # Временная задержка

    def _select_tier(self, tier: int):
        """Выбрать тир, если он отличается от текущего"""
        if self._current_tier == tier:
            return # Уже выбран
            
        anchor = self.config.get_coordinate("tier_dropdown")
        if not anchor: return
        
        self.logger.debug(f"Выбор тира: {tier}")
        # 1. Открыть меню
        self._human_move_to(*anchor)
        self._human_click()
        time.sleep(random.uniform(0.3, 0.4))
        
        # 2. Кликнуть пункт
        point = self.dropdowns.get_tier_click_point(tier, self._current_item_name)
        if point:
            self._human_move_to(*point)
            self._human_click()
            self._current_tier = tier # Запомнить
            self._current_quality = None # Сброс качества (игра может поменять)
            time.sleep(random.uniform(0.3, 0.4))

    def _select_enchant(self, enchant: int):
        """Выбрать зачарование, если оно отличается от текущего"""
        if self._current_enchant == enchant:
            return # Уже выбран
            
        anchor = self.config.get_coordinate("enchant_dropdown")
        if not anchor: return
        
        self.logger.debug(f"Выбор чар: {enchant}")
        # 1. Открыть меню
        self._human_move_to(*anchor)
        self._human_click()
        time.sleep(random.uniform(0.3, 0.4))
        
        # 2. Кликнуть пункт
        point = self.dropdowns.get_enchant_click_point(enchant)
        if point:
             self._human_move_to(*point)
             self._human_click()
             self._current_enchant = enchant # Запомнить
             self._current_quality = None # Сброс качества (игра может поменять)
             time.sleep(random.uniform(0.3, 0.4))

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

        # Маппинг качеств
        quality_map = {
            1: ["Normal", "Обычное", "Обычное"],
            2: ["Good", "Хорошее"],
            3: ["Outstanding", "Выдающееся"],
            4: ["Excellent", "Отличное"],
            5: ["Masterpiece", "Шедевр"]
        }
        expected_names = quality_map.get(quality, [])

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
                        self._consecutive_excellent_streak = 0 # Сброс стрика
                        return True
                    
                    # 2. Несовпадение -> Анализ того, что стоит
                    self.logger.debug(f"Пассивная проверка: '{passive_text}' != {expected_names}")
                    
                    is_excellent = fuzzy_match_quality(passive_text, ["Excellent", "Отличное"])
                    
                    if is_excellent:
                        if self._consecutive_excellent_streak == 0:
                            # Первый раз видим Отличное вместо Обычного -> Верим игре, пропускаем
                            self.logger.warning("Игра форсирует Отличное. Пропускаем попытку (1-й раз).")
                            self._consecutive_excellent_streak += 1
                            return False # Пропуск сканирования
                        else:
                            # Второй раз видим Отличное -> Возможно, Обычное все же есть? Пробуем кликнуть.
                            self.logger.info("Снова Отличное. Попытаемся форсировать Обычное (Активный выбор).")
                            # streak не сбрасываем пока не удастся переключить
                    else:
                        # Стоит что-то другое (не Отличное и не ТоЧтоНадо)
                        # Например, Хорошее. Значит Обычного точно нет.
                        self.logger.warning(f"Игра форсирует '{passive_text}'. Пропускаем попытку.")
                        self._consecutive_excellent_streak = 0
                        return False

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

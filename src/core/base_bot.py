import time
import random
import math
import pyautogui
from PyQt6.QtCore import QThread, pyqtSignal

from ..utils.config import get_config
from ..utils.logger import get_logger

class BaseBot(QThread):
    """
    Базовый класс для всех режимов бота.
    Содержит общую логику:
    - Управление потоком (Start/Stop/Pause)
    - Эмуляция ввода (Мышь/Клавиатура)
    - Логирование и статистика
    - Базовые проверки (Рынок открыт, Город)
    """
    
    # Общие сигналы
    progress_updated = pyqtSignal(int, int, str)
    finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._is_running = False
        self._is_paused = False
        self._stop_requested = False
        self.config = get_config()
        self.logger = get_logger()
        self._action_timings = {}
        self._current_city = "Unknown"
        self._is_black_market = False
        
    def run(self):
        """Переопределяется в наследниках"""
        pass
        
    def stop(self):
        """Остановить выполнение"""
        self._stop_requested = True
        
    def pause(self):
        """Пауза / Снятие с паузы"""
        self._is_paused = not self._is_paused
        status = "паузе" if self._is_paused else "работе"
        self.logger.info(f"Бот на {status}")
        
    def isRunning(self):
        return self._is_running

    def _check_pause(self):
        """Блокирующая проверка паузы"""
        if not self._is_paused:
            return
            
        self.logger.info("⏸️ Работа приостановлена (Пауза)...")
        while self._is_paused:
            if self._stop_requested: 
                break
            time.sleep(0.1)
        self.logger.info("▶️ Работа возобновлена")

    # === Input Emulation ===

    def _human_move_to(self, x: int, y: int):
        """Реалистичное движение мыши"""
        if self._stop_requested: return
        self._check_pause()
        
        start_time = time.time()
        
        # Разброс (Человечность)
        # По горизонтали: более широкий разброс (5-8 пикселей)
        offset_x = random.randint(-8, 8)
        # По вертикали: минимальный разброс (+- 1-2 пикселя)
        offset_y = random.randint(-2, 2)
        
        target_x = x + offset_x
        target_y = y + offset_y
        
        # Длительность
        duration = random.uniform(0.03, 0.08)
        
        pyautogui.moveTo(target_x, target_y, duration=duration, tween=pyautogui.easeInOutQuad)
        
        self._record_time("Мышь: Движение", (time.time() - start_time) * 1000)

    def _human_click(self):
        """Быстрый клик"""
        if self._stop_requested: return
        self._check_pause()
        start_time = time.time()
        pyautogui.click()
        self._record_time("Мышь: Клик", (time.time() - start_time) * 1000)

    def _human_dbl_click(self):
        """Двойной клик"""
        if self._stop_requested: return
        self._check_pause()
        start_time = time.time()
        pyautogui.doubleClick()
        self._record_time("Мышь: Двойной клик", (time.time() - start_time) * 1000)

    def _human_type(self, text: str):
        """Ввод текста (pynput)"""
        if self._stop_requested: return
        self._check_pause()
        
        start_time = time.time()
        from pynput.keyboard import Controller
        keyboard = Controller()
        
        for char in text:
            if self._stop_requested: return
            keyboard.type(char)
            time.sleep(random.uniform(0.01, 0.03))
        
        self._record_time("Ввод текста", (time.time() - start_time) * 1000)

    # === Shared Helpers ===
    
    def _record_time(self, action_name: str, duration_ms: float):
        if action_name not in self._action_timings:
            self._action_timings[action_name] = {"total_ms": 0.0, "count": 0}
        self._action_timings[action_name]["total_ms"] += duration_ms
        self._action_timings[action_name]["count"] += 1

    def _check_market_is_open(self) -> bool:
        """Проверка, что окно рынка открыто (OCR Name)"""
        start_time = time.time()
        # Changed from 'market_menu_check' to 'market_name_area' as per user request
        area = self.config.get_coordinate_area("market_name_area")
        
        from .validator import ScreenValidator
        is_open, msg = ScreenValidator.check_market_open(area)
        
        self._record_time("Валидация: Рынок", (time.time() - start_time) * 1000)
        
        if is_open:
            if "Market Closed" not in msg:
                 self.logger.debug(f"Market Validation PASS: {msg}")
            return True
        else:
            # Change to debug to avoid spam when Item Menu is open (which is valid state)
            self.logger.debug(f"Market Validation FAIL: {msg}")
            return False

    def _detect_current_city(self):
        """Определить город (OCR)"""
        start_time = time.time()
        VALID_CITIES = [
            "Bridgewatch", "Martlock", "Lymhurst", "Thetford", 
            "Fort Sterling", "Caerleon", "Brecilien", "Black Market",
            "Черный рынок"
        ]
        
        area = self.config.get_coordinate_area("market_name_area")
        if not area:
            self.logger.warning("Область 'Название рынка' не задана! Город: Unknown")
            self._current_city = "Unknown"
            return
        
        from ..utils.ocr import read_screen_text
        from difflib import get_close_matches
        
        city_text = read_screen_text(area['x'], area['y'], area['w'], area['h'], lang='rus+eng')
        city_text = city_text.strip()
        self._record_time("OCR: Город", (time.time() - start_time) * 1000)
        
        matches = get_close_matches(city_text, VALID_CITIES, n=1, cutoff=0.6)
        
        if matches:
            self._current_city = matches[0]
            if self._current_city in ["Black Market", "Черный рынок"]:
                self.logger.info("🕵️ Обнаружен Черный Рынок!")
                self._is_black_market = True
                self._current_city = "Black Market"
            else:
                 self._is_black_market = False
                 
            self.logger.info(f"🏪 Текущий город: {self._current_city}")
        else:
            self._current_city = "Unknown"
            self.logger.error(f"🛑 Неизвестный город: '{city_text}'!")
            
    def _verify_item_name_with_retry(self, expected_name: str, max_retries: int = 2) -> bool:
        """Verification logic (Shared)"""
        # NOTE: Implementation copied from MarketBot, essential for Buyer too
        from difflib import SequenceMatcher
        import re
        from ..utils.ocr import read_screen_text
        
        item_name_area = self.config.get_coordinate_area("item_name_area")
        sort_btn = self.config.get_coordinate("item_sort")
        buy_btn = self.config.get_coordinate("buy_button")
        menu_close = self.config.get_coordinate("menu_close")
        
        if not item_name_area:
            return True
        
        expected_clean = expected_name.strip().lower()
        
        for attempt in range(max_retries + 1):
            self._check_pause()
            
            ocr_name = read_screen_text(
                item_name_area['x'], item_name_area['y'],
                item_name_area['w'], item_name_area['h'],
                lang='rus+eng'
            )
            ocr_name_clean = re.sub(r'\s*\([^)]*\)\s*', '', ocr_name).strip()
            ocr_clean = ocr_name_clean.lower()
            
            similarity = SequenceMatcher(None, expected_clean, ocr_clean).ratio()
            
            if similarity >= 0.90:
                return True
            
            self.logger.warning(f"⚠️ Имя не совпадает (Try {attempt+1}): {ocr_name_clean} vs {expected_name}")
            
            if attempt == max_retries:
                if menu_close:
                    self._human_move_to(*menu_close)
                    self._human_click()
                    time.sleep(0.3)
                return False
            
            # Retry logic (Sort -> Buy)
            self.logger.info("🔄 Пробуем найти через сортировку...")
            if menu_close:
                self._human_move_to(*menu_close)
                self._human_click()
                time.sleep(0.5)
            
            if sort_btn:
                self._human_move_to(*sort_btn)
                self._human_click()
                time.sleep(1.0) # Wait for sort result (simplified wait)
                
            if buy_btn:
                self._human_move_to(*buy_btn)
                self._human_click()
                time.sleep(1.0)
                
        return False

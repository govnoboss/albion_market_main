import time
import random
import math
import pyautogui
from PyQt6.QtCore import QThread, pyqtSignal

from ..utils.config import get_config

from ..utils.logger import get_logger
from ..utils.human_mouse import move_mouse_human
from .interaction import DropdownSelector
from .market_opener import MarketOpener

class BaseBot(QThread):
    """
    Базовый класс для всех режимов бота.
    Содержит общую логику:
    - Управление потоком (Start/Stop/Pause)
    - Эмуляция ввода (Мышь/Клавиатура)
    - Логирование и статистика
    - Базовые проверки (Рынок открыт, Город, Вылеты)
    """
    
    # Общие сигналы
    progress_updated = pyqtSignal(int, int, str)
    finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._is_running = False
        self._is_paused = False
        self._stop_requested = False
        self._recovery_performed_during_item = False # Flag for retrying items
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
        """Реалистичное движение мыши (Bezier)"""
        if self._stop_requested: return
        self._check_pause()
        
        start_time = time.time()
        
        # Используем новую логику с кривыми Безье
        # offset уже включен в реализацию human_mouse (хотя там он start/end, но мы можем добавить final offset и тут)
        
        # Добавляем небольшой случайный оффсет к ЦЕЛЕВОЙ точке, чтобы не кликать в один пиксель
        jitter = self.config.get_mouse_settings().get("jitter", 5)
        target_x = x + random.randint(-jitter, jitter)
        target_y = y + random.randint(-jitter, jitter)
        
        move_mouse_human(target_x, target_y, check_pause_func=self._check_pause)
        
        self.logger.debug(f"Мышь: Движение заняло {(time.time() - start_time) * 1000:.1f} мс")

    def _human_click(self):
        """Быстрый клик"""
        if self._stop_requested: return
        self._check_pause()
        start_time = time.time()
        pyautogui.click()
        self.logger.debug(f"Мышь: Клик занял {(time.time() - start_time) * 1000:.1f} мс")

    def _human_dbl_click(self):
        """Двойной клик"""
        if self._stop_requested: return
        self._check_pause()
        start_time = time.time()
        pyautogui.doubleClick()
        self.logger.debug(f"Мышь: Двойной клик занял {(time.time() - start_time) * 1000:.1f} мс")

    def _human_type(self, text: str, clear: bool = False):
        """Ввод текста (pynput)"""
        if self._stop_requested: return
        self._check_pause()
        
        start_time = time.time()
        from pynput.keyboard import Controller, Key
        keyboard = Controller()
        
        if clear:
             # Ctrl + A -> Backspace
             with keyboard.pressed(Key.ctrl):
                 keyboard.press('a')
                 keyboard.release('a')
             time.sleep(0.05)
             keyboard.press(Key.backspace)
             keyboard.release(Key.backspace)
             time.sleep(0.05)
        
        for char in text:
            if self._stop_requested: return
            keyboard.type(char)
            time.sleep(random.uniform(0.01, 0.03))
        
        self.logger.debug(f"Ввод текста занял {(time.time() - start_time) * 1000:.1f} мс")

    # === Shared Helpers ===
    
    def _check_market_is_open(self, handle_kicks: bool = True) -> bool:
        """Проверка, что окно рынка открыто (OCR Name)"""
        start_time = time.time()
        area = self.config.get_coordinate_area("market_name_area")
        
        from .validator import ScreenValidator
        is_open, msg = ScreenValidator.check_market_open(area)
        
        self.logger.debug(f"Валидация: Рынок заняла {(time.time() - start_time) * 1000:.1f} мс")
        
        if is_open:
            if "Market Closed" not in msg:
                 self.logger.debug(f"Market Validation PASS: {msg}")
            return True
        else:
            self.logger.debug(f"Market Validation FAIL: {msg}")
            
            if handle_kicks:
                # --- НОВОЕ: Проверка на кик в меню ---
                self._detect_and_handle_kicks()
            
            return False

    def _detect_and_handle_kicks(self) -> bool:
        """
        Цикличный процесс восстановления (бесконечный, пока не зайдем или не стоп).
        Возвращает True, если была попытка восстановления.
        """
        from .state_detector import StateDetector
        
        recovery_performed = False
        self._recovery_performed_during_item = False # Reset before check
        
        # Сначала быстрая проверка — есть ли вообще проблемы?
        is_kicked, _ = StateDetector.is_disconnected()
        is_reconnect, _ = StateDetector.is_reconnect_screen()
        is_menu, _ = StateDetector.is_main_menu()
        
        if not (is_kicked or is_reconnect or is_menu):
            return False

        self.logger.info("🔄 Обнаружены окна вылета. Запуск цикла восстановления...")
        
        last_action_time = time.time()
        max_wait_after_action = 60.0 # Общий лимит на весь процесс
        
        # Бесконечный цикл пока не выйдем в мир или не нажмем СТОП
        while not self._stop_requested:
            # Свежая проверка состояний
            is_kicked, _ = StateDetector.is_disconnected()
            is_reconnect, _ = StateDetector.is_reconnect_screen()
            is_menu, menu_msg = StateDetector.is_main_menu()
            
            # Если ни одного окна нет
            if not (is_kicked or is_reconnect or is_menu):
                # Если мы только что что-то нажали — подождем немного (загрузка)
                if recovery_performed and (time.time() - last_action_time < 15.0):
                    time.sleep(1.0)
                    continue
                else:
                    if recovery_performed:
                        self.logger.success("✅ Окна вылета исчезли. Бот в игре (или загрузился).")
                    break

            # --- ШАГ 1: ОК на ошибке ---
            if is_kicked:
                self.logger.error("🛑 ОБНАРУЖЕН ВЫЛЕТ (Окно с OK)")
                ok_point = StateDetector.find_ok_button_coords()
                if ok_point:
                    self.logger.info(f"👉 Нажимаю 'OK': {ok_point}")
                    self._human_move_to(ok_point[0], ok_point[1])
                    self._human_click()
                    recovery_performed = True
                    last_action_time = time.time()
                else:
                    self.logger.warning("⚠️ Не найдена кнопка 'OK' на экране вылета.")
                time.sleep(1.0)
                continue
            
            # --- ШАГ 2: Переподключение ---
            if is_reconnect:
                self.logger.error("🛑 ОБНАРУЖЕН ЭКРАН ПЕРЕПОДКЛЮЧЕНИЯ")
                rec_point = StateDetector.find_reconnect_button_coords()
                if rec_point:
                    self.logger.info(f"👉 Нажимаю 'ПЕРЕПОДКЛЮЧЕНИЕ': {rec_point}")
                    self._human_move_to(rec_point[0], rec_point[1])
                    self._human_click()
                    recovery_performed = True
                    last_action_time = time.time()
                else:
                    self.logger.warning("⚠️ Не найдена кнопка 'ПЕРЕПОДКЛЮЧЕНИЕ' на экране.")
                time.sleep(1.0)
                continue
            
            # --- ШАГ 3: Главное меню (Вход) ---
            if is_menu:
                self.logger.error(f"🛑 ОБНАРУЖЕНО ГЛАВНОЕ МЕНЮ ({menu_msg})")
                login_point = StateDetector.get_login_button()
                if login_point:
                    self.logger.info(f"👉 Нажимаю 'ВОЙТИ': {login_point}")
                    self._human_move_to(login_point[0], login_point[1])
                    self._human_click()
                    recovery_performed = True
                    last_action_time = time.time()
                    # После "Войти" часто идет долгая загрузка
                    time.sleep(5.0)
                else:
                    self.logger.warning("⚠️ Не задана координата 'bm_login_btn' или кнопка не найдена! Остановка цикла.")
                    break
            
            # Если мы видим Главное Меню, но иконки не распознаны (is_menu == False)
            # Это состояние покроется внешним циклом бота, когда он не найдет рынок.
            
            if time.time() - last_action_time > max_wait_after_action:
                self.logger.warning("⏰ Превышено время ожидания в цикле восстановления.")
                break

            time.sleep(0.5)
        
        if recovery_performed:
            self.logger.warning("⏳ Попытка автоматического открытия рынка...")
            opener = MarketOpener(self.logger, self.config)
            
            market_opened = False
            for attempt in range(2): # 2 попытки поиска NPC
                if self._stop_requested: break
                
                if opener.open_market():
                    self.logger.info("⏳ Ожидание появления окна рынка...")
                    time.sleep(2.5) # Даем время на отрисовку
                    
                    if self._check_market_is_open(handle_kicks=False):
                        market_opened = True
                        break
                    else:
                        self.logger.warning(f"❌ Окно рынка не открылось (попытка {attempt+1}/2).")
                        # Проверяем, не вылетели ли мы снова во время клика?
                        is_k, _ = StateDetector.is_disconnected()
                        is_r, _ = StateDetector.is_reconnect_screen()
                        if is_k or is_r:
                            self.logger.error("🛑 Обнаружен повторный вылет во время открытия рынка!")
                            break # Выходим к началу внешнего цикла
                else:
                    self.logger.warning(f"⚠️ NPC Рынка не найден (попытка {attempt+1}/2).")
            
            if market_opened:
                self.logger.success("✅ Рынок успешно открыт автоматически.")
            else:
                self.logger.error("🛑 Не удалось открыть рынок автоматически.")

            self.logger.warning("⏸️ Восстановление завершено. Бот на паузе.")
            self._is_paused = True
            self._recovery_performed_during_item = True
            
        return recovery_performed

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
        
        from ..utils.ocr import read_screen_text_cached
        from difflib import get_close_matches
        
        city_text = read_screen_text_cached(area['x'], area['y'], area['w'], area['h'], lang='rus+eng')
        city_text = city_text.strip()
        self.logger.debug(f"OCR: Город заняло {(time.time() - start_time) * 1000:.1f} мс")
        
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
            

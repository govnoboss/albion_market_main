import time
import os
import pyautogui
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageGrab
from ..utils.logger import get_logger
from ..utils.config import get_config

class Navigator:
    """
    Модуль навигации для режима 'Travel Mode' (Shift+N).
    Управляет картой, определяет положение игрока и рисует дебаг-информацию.
    """
    
    def __init__(self):
        self.logger = get_logger()
        self.config = get_config()
        self._map_open = False
        
        # Константы для Travel Mode (можно вынести в конфиг)
        # В Travel Mode игрок всегда в центре экрана.
        # Карта занимает весь экран.
        
    def toggle_travel_mode(self, expected_state: bool = None) -> bool:
        """
        Переключить режим карты (Shift+N).
        :param expected_state: True (открыть) или False (закрыть). Если None - просто переключить.
        """
        # Пока мы не умеем читать состояние (открыта ли карта),
        # мы просто посылаем нажатие.
        # В будущем можно добавить проверку пикселей (например, уникальный элемент интерфейса карты).
        
        self.logger.info("🗺️ Переключение Travel Mode (Shift+N)...")
        pyautogui.keyDown('shift')
        pyautogui.press('n')
        pyautogui.keyUp('shift')
        time.sleep(1.0) # Ждем анимации
        
        if expected_state is not None:
             self._map_open = expected_state
        else:
             self._map_open = not self._map_open
             
        return True
        
    def toggle_interface(self) -> None:
        """
        Переключить интерфейс (Alt+J).
        Полезно для чистого поиска объектов на экране.
        """
        self.logger.info("👁️ Переключение интерфейса (Alt+J)...")
        pyautogui.keyDown('alt')
        pyautogui.press('j')
        pyautogui.keyUp('alt')
        time.sleep(0.5) # Ждем исчезновения/появления HUD

        screen_w, screen_h = pyautogui.size()
        center_x, center_y = screen_w // 2, screen_h // 2
        
        # Область поиска (центральная часть экрана, чтобы не ловить лишнее)
        # Например, 400x400 пикселей в центре
        search_w, search_h = 400, 400
        left = center_x - search_w // 2
        top = center_y - search_h // 2
        
        # Захват экрана
        img = ImageGrab.grab(bbox=(left, top, left + search_w, top + search_h))
        pixels = img.load()
        
        # Диапазон цвета игрока (Синий/Голубой треугольник)
        # RGB примерно (0, 150-255, 200-255) - очень яркий голубой
        # Нужно калибровать. Пока возьмем эвристику.
        
        x_sum = 0
        y_sum = 0
        count = 0
        
        for y in range(img.height):
            for x in range(img.width):
                r, g, b = pixels[x, y]
                
                # 1. Проверка на СИНИЙ (Blue dominant)
                if b > 180 and g > 150 and r < 100:
                    
                    # 2. Проверка на ЧЕРНЫЙ КОНТУР (по соседству)
                    # Иконка игрока обведена черным. Портал - нет (он светится).
                    has_black_border = False
                    
                    # Проверяем соседей в радиусе 2 пикселей
                    for dy in range(-2, 3):
                        for dx in range(-2, 3):
                            nx, ny = x + dx, y + dy
                            
                            # Проверка границ
                            if 0 <= nx < img.width and 0 <= ny < img.height:
                                nr, ng, nb = pixels[nx, ny]
                                # Черный/Очень темный цвет
                                if nr < 30 and ng < 30 and nb < 30:
                                    has_black_border = True
                                    break
                        if has_black_border: break
                    
                    if has_black_border:
                        x_sum += x
                        y_sum += y
                        count += 1
        
        if count > 0:
            # Смещение относительно области захвата
            # Reconstruct 'left', 'top' since they are local variables in the function
            screen_w, screen_h = pyautogui.size()
            center_x, center_y = screen_w // 2, screen_h // 2
            search_w, search_h = 400, 400
            left = center_x - search_w // 2
            top = center_y - search_h // 2
            
            found_x = left + (x_sum // count)
            found_y = top + (y_sum // count)
            self.logger.debug(f"📍 Игрок найден по цвету (с контуром): {found_x}, {found_y} (px: {count})")
            return (found_x, found_y)
            
        self.logger.warning("⚠️ Игрок не найден! Используем центр экрана.")
        screen_w, screen_h = pyautogui.size()
        return (screen_w // 2, screen_h // 2)

    def get_player_position(self) -> tuple[int, int]:
        """
        Возвращает координаты центра игрока на экране.
        Использует цветовой поиск (Color Blob Detection), так как иконка вращается.
        """
        screen_w, screen_h = pyautogui.size()
        center_x, center_y = screen_w // 2, screen_h // 2
        
        # Область поиска (центральная часть экрана, чтобы не ловить лишнее)
        # Например, 400x400 пикселей в центре
        search_w, search_h = 400, 400
        left = center_x - search_w // 2
        top = center_y - search_h // 2
        
        # Захват экрана
        img = ImageGrab.grab(bbox=(left, top, left + search_w, top + search_h))
        pixels = img.load()
        
        # Диапазон цвета игрока (Синий/Голубой треугольник)
        # RGB примерно (0, 150-255, 200-255) - очень яркий голубой
        # Нужно калибровать. Пока возьмем эвристику.
        
        x_sum = 0
        y_sum = 0
        count = 0
        
        for y in range(img.height):
            for x in range(img.width):
                r, g, b = pixels[x, y]
                
                # 1. Проверка на СИНИЙ (Blue dominant)
                if b > 180 and g > 150 and r < 100:
                    
                    # 2. Проверка на ЧЕРНЫЙ КОНТУР (по соседству)
                    # Иконка игрока обведена черным. Портал - нет (он светится).
                    has_black_border = False
                    
                    # Проверяем соседей в радиусе 2 пикселей
                    for dy in range(-2, 3):
                        for dx in range(-2, 3):
                            nx, ny = x + dx, y + dy
                            
                            # Проверка границ
                            if 0 <= nx < img.width and 0 <= ny < img.height:
                                nr, ng, nb = pixels[nx, ny]
                                # Черный/Очень темный цвет
                                if nr < 30 and ng < 30 and nb < 30:
                                    has_black_border = True
                                    break
                        if has_black_border: break
                    
                    if has_black_border:
                        x_sum += x
                        y_sum += y
                        count += 1
        
        if count > 0:
            # Смещение относительно области захвата
            # Reconstruct 'left', 'top' since they are local variables in the function
            screen_w, screen_h = pyautogui.size()
            center_x, center_y = screen_w // 2, screen_h // 2
            search_w, search_h = 400, 400
            left = center_x - search_w // 2
            top = center_y - search_h // 2
            
            found_x = left + (x_sum // count)
            found_y = top + (y_sum // count)
            self.logger.debug(f"📍 Игрок найден по цвету (с контуром): {found_x}, {found_y} (px: {count})")
            return (found_x, found_y)
            
        self.logger.warning("⚠️ Игрок не найден! Используем центр экрана.")
        screen_w, screen_h = pyautogui.size()
        return (screen_w // 2, screen_h // 2)

    def is_inventory_open(self) -> bool:
        """Проверяет, открыт ли инвентарь (по тексту 'Рюкзак')"""
        area = self.config.get_coordinate_area("inventory_check_area")
        if not area:
            return False
            
        from ..utils.ocr import read_screen_text
        text = read_screen_text(area['x'], area['y'], area['w'], area['h'], lang='rus')
        
        # Fuzzy match for 'Рюкзак'
        normalized = text.lower().strip()
        if "рюкзак" in normalized or "ok3ak" in normalized or "okzak" in normalized: # OCR typos
            return True
            
        return False

    def is_bank_open(self) -> bool:
        """Проверяет, открыт ли Банк (по тексту 'Банк'/'Bank')"""
        area = self.config.get_coordinate_area("bank_check_area")
        if not area:
            return False
            
        from ..utils.ocr import read_screen_text
        text = read_screen_text(area['x'], area['y'], area['w'], area['h'], lang='rus+eng')
        
        normalized = text.lower().strip()
        if "банк" in normalized or "bank" in normalized:
            return True
        return False

    def ensure_inventory_closed(self) -> bool:
        """
        Гарантирует, что инвентарь закрыт.
        Если открыт -> жмет 'I' и проверяет.
        Возвращает True, если в итоге закрыт.
        """
        if self.is_inventory_open():
            self.logger.info("🎒 Инвентарь открыт! Закрываю (I)...")
            pyautogui.press('i')
            time.sleep(1.0)
            
            if self.is_inventory_open():
                self.logger.warning("⚠️ Инвентарь не закрылся после нажатия I!")
                return False
            else:
                self.logger.info("✅ Инвентарь успешно закрыт.")
                return True
        return True
        
    def find_yellow_flags(self) -> list[tuple[int, int]]:
        """
        Ищет желтые флаги (выходы) на карте.
        Возвращает список координат (x, y).
        """
        screen_w, screen_h = pyautogui.size()
        center_x, center_y = screen_w // 2, screen_h // 2
        
        # Область поиска - весь экран (так как флаги могут быть по краям)
        img = ImageGrab.grab()
        pixels = img.load()
        
        detected_points = []
        
        # Сканируем с шагом 5, чтобы было быстрее
        step = 5
        for y in range(0, img.height, step):
            for x in range(0, img.width, step):
                r, g, b = pixels[x, y]
                
                # Желтый цвет (R+G высокие, B низкий)
                if r > 200 and g > 180 and b < 80:
                     detected_points.append((x, y))
        
        # Кластеризация точек (объединяем близкие, чтобы получить одну точку на один флаг)
        flags = []
        while detected_points:
            # Берем первую точку
            curr = detected_points.pop(0)
            
            # Ищем все точки рядом (радиус 30 пикселей)
            cluster = [curr]
            to_remove = []
            
            for p in detected_points:
                dist = ((p[0] - curr[0])**2 + (p[1] - curr[1])**2)**0.5
                if dist < 30:
                    cluster.append(p)
                    to_remove.append(p)
            
            # Удаляем их из общего списка
            for p in to_remove:
                if p in detected_points:
                    detected_points.remove(p)
            
            # Вычисляем среднюю точку кластера
            avg_x = sum(p[0] for p in cluster) // len(cluster)
            avg_y = sum(p[1] for p in cluster) // len(cluster)
            flags.append((avg_x, avg_y))
            
        return flags

    def get_ne_flag(self, origin: tuple[int, int], flags: list[tuple[int, int]]) -> tuple[int, int] | None:
        """
        Ищет флаг, который находится на Северо-Востоке (NE) от origin (обычно сундука).
        NE = X > origin.X (Право) и Y < origin.Y (Верх).
        Возвращает ближайший подходящий или None.
        """
        if not origin or not flags:
            return None
            
        ox, oy = origin
        candidates = []
        
        for fx, fy in flags:
            # Проверка квадранта NE (Top-Right)
            if fx > ox and fy < oy:
                dist = ((fx - ox)**2 + (fy - oy)**2)**0.5
                candidates.append(((fx, fy), dist))
        
        if not candidates:
            return None
            
        # Сортируем по дистанции (берем ближайший)
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]

    def find_chest(self) -> tuple[int, int] | None:
        """
        Ищет сундук (Банк) на карте.
        Использует Template Matching (картинка).
        Возвращает координаты (x, y) или None.
        """
        # Путь к шаблону
        resource_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "resources", "chest_map_icon.png")
        
        if not os.path.exists(resource_path):
            self.logger.error(f"Файл иконки сундука не найден: {resource_path}")
            return None
            
    def find_chest(self) -> tuple[int, int] | None:
        """
        Ищет сундук. Использует Masked Template Matching (если есть прозрачность).
        Сохраняет кроп найденного места для дебага.
        """
        resource_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "resources", "chest_map_icon.png")
        if not os.path.exists(resource_path):
            self.logger.error(f"Файл шаблона не найден: {resource_path}")
            return None
            
        try:
            # 1. Загружаем шаблон С АЛЬФА-КАНАЛОМ
            # IMREAD_UNCHANGED позволяет загрузить 4 канала (BGRA)
            template = cv2.imread(resource_path, cv2.IMREAD_UNCHANGED)
            if template is None:
                self.logger.error("Ошибка загрузки шаблона.")
                return None
            
            # Разделяем каналы
            mask = None
            if template.shape[2] == 4:
                # Если 4 канала -> отделяем маску
                # Берем BGR часть для шаблона
                template_bgr = template[:, :, :3]
                # Берем Alpha часть для маски
                alpha = template[:, :, 3]
                # Ничего не матчим там, где прозрачно?
                # cv2.matchTemplate требует маску того же размера и типа (или CV_8U)
                mask = alpha
                template = template_bgr
            
            # 2. Скриншот
            screen_pil = ImageGrab.grab()
            screen_np = np.array(screen_pil)
            screen_bgr = cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR)
            
            # 3. Матчинг
            if mask is not None:
                # Используем CCORR_NORMED, так как он поддерживает маску в большинстве версий
                method = cv2.TM_CCORR_NORMED
                # Порог для CCORR обычно выше (ближе к 0.9-0.95)
                threshold = 0.85
                res = cv2.matchTemplate(screen_bgr, template, method, mask=mask)
            else:
                # Обычный матчинг (без прозрачности)
                method = cv2.TM_CCOEFF_NORMED
                threshold = 0.65
                res = cv2.matchTemplate(screen_bgr, template, method)
            
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            
            self.logger.info(f"🔎 Score сундука ({'Masked' if mask is not None else 'Normal'}): {max_val:.4f} (Требуется: {threshold})")
            
            # CHECK FOR INF/NAN (Fix for black screen issue)
            import math
            if math.isinf(max_val) or math.isnan(max_val) or max_val > 1.0:
                 self.logger.warning(f"⚠️ Ложное срабатывание (inf/nan) на черной или пустой зоне. Score: {max_val}")
                 return None
            
            # Сохраняем "что мы нашли" для дебага
            h, w = template.shape[:2]
            top_left = max_loc
            bottom_right = (top_left[0] + w, top_left[1] + h)
            
            # Вырезаем найденный кусочек со скрина
            debug_crop = screen_bgr[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]
            cv2.imwrite("debug_chest_match_crop.png", debug_crop)
            
            if max_val >= threshold:
                cx = top_left[0] + w // 2
                cy = top_left[1] + h // 2
                self.logger.info(f"📦 Сундук найден: ({cx}, {cy})")
                return (cx, cy)
            else:
                self.logger.warning("📦 Сундук не найден (Score too low).")
                return None
                
        except Exception as e:
            self.logger.error(f"Ошибка поиска (CV2): {repr(e)}")
            return None

    def move_towards(self, target_x: int, target_y: int) -> None:
        """
        Двигаться к указанной точке (x, y).
        Использует Правый Клик (стандартное управление Albion).
        """
        px, py = self.get_player_position()
        
        # Вектор движения
        dx = target_x - px
        dy = target_y - py
        dist = (dx**2 + dy**2)**0.5
        
        if dist < 10:
            self.logger.info("🏁 Мы уже в точке назначения.")
            return

        self.logger.info(f"🏃 Движение: ({px},{py}) -> ({target_x},{target_y}) [Dist: {dist:.1f}]")
        
        # Движение мыши и клик (Правой кнопкой!)
        pyautogui.moveTo(target_x, target_y, duration=0.2)
        pyautogui.click(button='right')
        
    def open_bank(self) -> bool:
        """
        Robustly opens the bank.
        1. Checks if already open.
        2. Tries to find chest.
        3. If not found -> Presses Shift+N (Open Travel Map) -> Waits -> Tries again.
        4. Moves to chest -> Clicks.
        5. Waits for 'Bank' header (with 2s delay).
        """
        if self.is_bank_open():
            self.logger.info("🏦 Банк уже открыт.")
            return True
            
        self.logger.info("SEARCH: Ищу сундук на экране...")
        chest_pos = self.find_chest()
        
        if not chest_pos:
            self.logger.warning("⚠️ Сундук не найден. Возможно, карта закрыта.")
            self.logger.info("ACTION: Нажимаю Shift+N (Открыть Travel Map)...")
            pyautogui.keyDown('shift')
            pyautogui.press('n')
            pyautogui.keyUp('shift')
            
            self.logger.info("⏳ Жду 1.0 сек (Анимация карты)...")
            time.sleep(1.0)
            
            self.logger.info("SEARCH: Повторный поиск сундука...")
            chest_pos = self.find_chest()
            
            if not chest_pos:
                self.logger.error("❌ Сундук НЕ найден даже после открытия карты! Проверьте шаблон.")
                return False
        
        self.logger.success(f"✅ Сундук найден: {chest_pos}")
        
        # Move and Click
        self.move_towards(*chest_pos)
        time.sleep(0.5)
        
        self.logger.info("ACTION: Клик по сундуку (Right Click)...")
        pyautogui.click(button='right') 
        
        self.logger.info("⏳ Ожидание открытия банка (Start 2s delay)...")
        time.sleep(2.0) # Requested explicit delay
        
        # Ждем открытия (до 5 сек после задержки)
        for i in range(10):
            if self.is_bank_open():
                self.logger.success("✅ Банк успешно открыт!")
                return True
            self.logger.debug(f"⏳ Проверка банка... ({i+1}/10)")
            time.sleep(0.5)
                
        self.logger.error("❌ Таймаут: Банк не открылся.")
        return False

    def equip_loadouts(self, count: int = 2) -> bool:
        """
        Экипирует первые `count` комплектов из вкладки Loadouts.
        Использует смещение по Y из настроек (row_height).
        """
        if not self.open_bank():
            return False
            
        # Координаты
        tabs_point = self.config.get_coordinate("bank_tabs_point") # (Опционально, если нужно переключить на сеты)
        sets_tab = self.config.get_coordinate("bank_sets_tab_point")
        select_set = self.config.get_coordinate("bank_select_set_point")
        equip_btn = self.config.get_coordinate("bank_equip_point")
        
        if not sets_tab or not select_set or not equip_btn:
             self.logger.error("❌ Не заданы координаты для банка (Вкладка сетов, Выбор сета или Кнопка Экипировать)!")
             return False
             
        # 1. Переходим во вкладку Сетов
        self.logger.info("Click -> Вкладка Сетов")
        pyautogui.click(*sets_tab)
        time.sleep(1.0) # Анимация
        
        # 2. Берем высоту строки из конфига
        row_height = self.config.get_dropdown_setting("row_height", 30) # Default 30 if not set
        self.logger.info(f"Using Row Height: {row_height} px")
        
        base_x, base_y = select_set
        
        # 3. Цикл экипировки
        for i in range(count):
            target_y = base_y + (i * row_height)
            
            self.logger.info(f"👘 Экипировка Сета #{i+1} (Y={target_y})...")
            
            # Клик по сету
            pyautogui.click(base_x, target_y)
            time.sleep(0.3)
            
            # Клик Экипировать
            pyautogui.click(*equip_btn)
            time.sleep(1.5) # Ждем пока наденется (Channeling time usually 0 for quick equip, but safe wait)
            
        self.logger.success(f"✅ Экипировано {count} сетов.")
        return True

    def debug_view(self, save_path: str = "nav_debug.png"):
        """
        Создает скриншот с визуализацией того, что видит бот.
        Рисует крест в центре (игрок) и границы.
        """
        screenshot = ImageGrab.grab()
        draw = ImageDraw.Draw(screenshot)
        
        # 1. Рисуем центр (Игрок)
        px, py = self.get_player_position()
        r = 20 # радиус круга
        draw.ellipse((px - r, py - r, px + r, py + r), outline="red", width=3)
        draw.line((px - 50, py, px + 50, py), fill="red", width=2)
        draw.line((px, py - 50, px, py + 50), fill="red", width=2)
        draw.text((px + 25, py + 25), f"PLAYER ({px},{py})", fill="red")
        
        # 2. Рисуем Желтые Флаги
        flags = self.find_yellow_flags()
        for i, (fx, fy) in enumerate(flags):
            draw.ellipse((fx - 15, fy - 15, fx + 15, fy + 15), outline="yellow", width=3)
            draw.text((fx + 20, fy), f"FLAG #{i+1}", fill="yellow")
            # draw.line((px, py, fx, fy), fill="yellow", width=1) # Линия от игрока к флагу
            
        # 3. Рисуем Сундук
        chest_pos = self.find_chest()
        if chest_pos:
            cx, cy = chest_pos
            draw.ellipse((cx - 20, cy - 20, cx + 20, cy + 20), outline="cyan", width=3)
            draw.text((cx + 25, cy), "CHEST (Bank)", fill="cyan")
            draw.text((cx + 25, cy), "CHEST (Bank)", fill="cyan")
            draw.line((px, py, cx, cy), fill="cyan", width=2)
            
            # 4. Рисуем NE маршрут (от сундука к NE флагу)
            ne_flag = self.get_ne_flag(chest_pos, flags)
            if ne_flag:
                nx, ny = ne_flag
                draw.line((cx, cy, nx, ny), fill="#ff00ff", width=4) # Magenta Line
                draw.text((nx, ny - 25), "TARGET (NE)", fill="#ff00ff")
        
        # Сохраняем
        try:
            screenshot.save(save_path)
            self.logger.info(f"📸 Навигационный дебаг сохранен: {save_path}")
            # Пытаемся открыть (Windows)
            os.startfile(save_path)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения дебага: {e}")


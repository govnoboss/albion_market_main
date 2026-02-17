"""
Логика поиска и открытия рынка в игре.
Использует наведение мыши и OCR для детекции тултипа "Рынок".
"""

import time
import random
import pyautogui
from typing import Optional, Tuple
from ..utils.ocr import read_screen_text
from ..utils.human_mouse import move_mouse_human

class MarketOpener:
    def __init__(self, logger, config):
        self.logger = logger
        self.config = config
        self._stop_requested = False

    def open_market(self, max_attempts: int = 50) -> bool:
        """
        Пытается найти NPC рынка, двигая мышь по рядам (слева направо).
        """
        self.logger.info("🔭 Запуск систематического поиска NPC Рынка...")
        
        screen_w, screen_h = pyautogui.size()
        
        # Определяем зону сканирования (центральная часть экрана, чтобы не тыкать в UI)
        # Отступаем по 15% сверху/снизу и 10% по бокам
        margin_x = int(screen_w * 0.1)
        margin_y = int(screen_h * 0.15)
        
        scan_area_w = screen_w - (2 * margin_x)
        scan_area_h = screen_h - (2 * margin_y)
        
        # Шаги сканирования
        step_x = 350 # Как просил юзер (300-400px)
        step_y = int(screen_h * 0.1) # 10% высоты
        
        search_points = []
        for y in range(margin_y, margin_y + scan_area_h, step_y):
            # Чередуем направление (зигзаг) для человечности
            row_points = []
            for x in range(margin_x, margin_x + scan_area_w, step_x):
                row_points.append((x, y))
            
            if (y // step_y) % 2 == 1:
                row_points.reverse()
            
            search_points.extend(row_points)
        
        total_points = len(search_points)
        self.logger.info(f"📍 Сгенерировано {total_points} точек для сканирования.")
        
        for idx, (tx, ty) in enumerate(search_points):
            if self._stop_requested: break
            if idx >= max_attempts: break
            
            # Небольшой «дрожащий» офсет для каждой точки
            target_x = tx + random.randint(-20, 20)
            target_y = ty + random.randint(-20, 20)
            
            # Обеспечиваем границы
            target_x = max(0, min(screen_w - 1, target_x))
            target_y = max(0, min(screen_h - 1, target_y))
            
            # Движение (плавное, человечное)
            move_mouse_human(target_x, target_y)
            # Ждем появления тултипа. Слишком быстро — не успеет отрисоваться. 
            time.sleep(0.35) 
            
            if self._check_for_market_tooltip():
                self.logger.success("🎯 NPC Рынка найден!")
                time.sleep(0.1)
                pyautogui.click()
                time.sleep(1.5) # Ждем открытия
                return True
                
        self.logger.warning("❌ NPC Рынка не обнаружен на экране.")
        return False

    def _check_for_market_tooltip(self) -> bool:
        """
        Проверяет наличие тултипа 'Рынок' в области вокруг курсора.
        """
        x, y = pyautogui.position()
        
        # Центрируем область сканирования вокруг курсора (700x300)
        # Увеличили ширину, чтобы точно захватить весь текст тултипа, даже если он длинный.
        scan_w, scan_h = 700, 300
        scan_x = max(0, x - 350)
        scan_y = max(0, y - 150)
        
        try:
            # Читаем текст. Рынок может быть на русском или английском.
            text = read_screen_text(scan_x, scan_y, scan_w, scan_h, lang='rus+eng')
            text_lower = text.lower()
            
            # Ключевые слова из скриншотов (Обычный и Черный рынки)
            keywords = ["рынок", "market", "покупайте", "маркет", "продавайте", "черный", "black", "экипировку", "loot"]
            for k in keywords:
                if k in text_lower:
                    self.logger.info(f"✨ Детектирован тултип через OCR: '{k}'")
                    return True
                    
        except Exception as e:
            self.logger.debug(f"Ошибка OCR при поиске тултипа: {e}")
            
        return False

    def set_stop(self, value: bool):
        self._stop_requested = value

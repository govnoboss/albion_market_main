"""
Albion Market Bot v3.0 - Smart Automation

Умная автоматизация: комбинация Template Matching + минимальных координат.
"""

import time
import random
import logging
from typing import Tuple, Optional

import pyautogui
import keyboard

from core.template_matcher import (
    get_template_matcher, 
    find_button, 
    find_buy_button, 
    find_ok_button,
    wait_for_button,
    MatchResult
)
from core.automation import get_automation_controller

logger = logging.getLogger(__name__)

# Отключение failsafe
pyautogui.FAILSAFE = False


class SmartAutomation:
    """
    Умная автоматизация с автоопределением кнопок.
    
    Приоритет:
    1. Template Matching (автопоиск)
    2. Fallback на координаты (если есть)
    """
    
    def __init__(self, fallback_coords: dict = None):
        """
        Args:
            fallback_coords: Резервные координаты {button_name: (x, y)}
        """
        self.matcher = get_template_matcher()
        self.controller = get_automation_controller()
        self.fallback_coords = fallback_coords or {}
    
    def click_button(
        self, 
        template_name: str,
        timeout: float = 3.0,
        delay_after: float = 0.2
    ) -> bool:
        """
        Клик по кнопке с автопоиском.
        
        Args:
            template_name: Имя шаблона (buy_button, ok_button, etc.)
            timeout: Таймаут ожидания
            delay_after: Задержка после клика
        
        Returns:
            True если кнопка найдена и нажата.
        """
        # Попытка найти через template matching
        result = self.matcher.wait_for_template(template_name, timeout=timeout)
        
        if result.found:
            cx, cy = result.center
            self.controller.move_and_click(cx, cy, scatter=3, delay_after=delay_after)
            logger.info(f"Clicked '{template_name}' at ({cx}, {cy}) [conf={result.confidence:.2f}]")
            return True
        
        # Fallback на координаты
        if template_name in self.fallback_coords:
            x, y = self.fallback_coords[template_name]
            if x > 0 and y > 0:
                self.controller.move_and_click(x, y, scatter=5, delay_after=delay_after)
                logger.info(f"Clicked '{template_name}' at fallback ({x}, {y})")
                return True
        
        logger.warning(f"Button '{template_name}' not found!")
        return False
    
    def click_buy_in_list(self, row_index: int = 0) -> bool:
        """
        Клик по кнопке "Купить" в списке товаров.
        
        Args:
            row_index: Номер строки (0 = первая)
        
        Returns:
            True если нажата.
        """
        # Найти все кнопки "Купить"
        results = self.matcher.find_all_on_screen('buy_button', max_results=10)
        
        if results and row_index < len(results):
            # Сортируем по Y (сверху вниз)
            results.sort(key=lambda r: r.y)
            target = results[row_index]
            
            cx, cy = target.center
            self.controller.move_and_click(cx, cy, scatter=3)
            logger.info(f"Clicked buy button row {row_index} at ({cx}, {cy})")
            return True
        
        logger.warning(f"Buy button row {row_index} not found (found {len(results)} buttons)")
        return False
    
    def click_confirm(self, timeout: float = 3.0) -> bool:
        """Клик по кнопке подтверждения."""
        # Пробуем разные варианты
        for template in ['ok_button', 'yes_button']:
            result = self.matcher.find_on_screen(template)
            if result.found:
                cx, cy = result.center
                self.controller.move_and_click(cx, cy, scatter=3, delay_after=0.2)
                logger.info(f"Clicked confirm '{template}' at ({cx}, {cy})")
                return True
        
        return False
    
    def click_clear_search(self) -> bool:
        """Клик по кнопке очистки поиска."""
        return self.click_button('clear_button', timeout=2.0)
    
    def type_in_search(self, text: str, search_coords: Tuple[int, int] = None) -> bool:
        """
        Ввод текста в поле поиска.
        
        Args:
            text: Текст для ввода.
            search_coords: Координаты поля поиска (fallback).
        
        Returns:
            True если успешно.
        """
        # Ищем поле поиска через шаблон
        result = self.matcher.find_on_screen('search_button')
        
        if result.found:
            # Клик по центру найденного шаблона
            cx, cy = result.center
            self.controller.move_and_click(cx, cy, scatter=3)
            logger.info(f"Clicked search at ({cx}, {cy})")
        elif search_coords and search_coords[0] > 0:
            self.controller.move_and_click(search_coords[0], search_coords[1], scatter=3)
        else:
            logger.warning("Search field not found")
            return False
        
        time.sleep(random.uniform(0.1, 0.2))
        
        # Ввод текста
        self.controller.type_text(text)
        return True
    
    def wait_and_click_if_found(
        self, 
        template_name: str, 
        timeout: float = 1.0
    ) -> bool:
        """
        Проверить и кликнуть если кнопка есть.
        
        Полезно для обработки popup "OK" или "Истекло время".
        """
        result = self.matcher.find_on_screen(template_name)
        if result.found:
            cx, cy = result.center
            self.controller.click(cx, cy, scatter=3)
            logger.info(f"Auto-clicked popup '{template_name}'")
            return True
        return False
    
    def handle_popups(self) -> bool:
        """Обработка всплывающих окон (OK, Yes, Out of Time)."""
        handled = False
        
        for popup in ['ok_button', 'yes_button', 'outoftime']:
            if self.wait_and_click_if_found(popup, timeout=0.5):
                handled = True
                time.sleep(0.3)
        
        return handled


# Глобальный экземпляр
_smart_auto: Optional[SmartAutomation] = None


def get_smart_automation(fallback_coords: dict = None) -> SmartAutomation:
    """Получение умной автоматизации."""
    global _smart_auto
    if _smart_auto is None or fallback_coords:
        _smart_auto = SmartAutomation(fallback_coords)
    return _smart_auto

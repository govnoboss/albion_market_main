"""
Albion Market Bot v3.0 - Automation Module

Модуль автоматизации: клики, ввод текста, управление мышью.
"""

import random
import time
import logging
from typing import Tuple, Optional

import pyautogui
import keyboard

logger = logging.getLogger(__name__)

# Отключение защиты pyautogui (можно прервать только через F2)
pyautogui.FAILSAFE = False


class AutomationController:
    """Контроллер автоматизации UI."""
    
    def __init__(
        self, 
        scatter: int = 5,
        move_duration_range: Tuple[float, float] = (0.1, 0.2),
        type_delay_range: Tuple[float, float] = (0.01, 0.05),
    ):
        """
        Args:
            scatter: Максимальное смещение при кликах (пикселей).
            move_duration_range: Диапазон времени перемещения курсора.
            type_delay_range: Диапазон задержки между символами.
        """
        self.scatter = scatter
        self.move_duration_range = move_duration_range
        self.type_delay_range = type_delay_range
    
    def click(
        self, 
        x: int, 
        y: int, 
        scatter: Optional[int] = None,
        delay_after: float = 0.0
    ) -> Tuple[int, int]:
        """
        Клик со случайным смещением.
        
        Args:
            x, y: Координаты клика.
            scatter: Максимальное смещение (переопределяет default).
            delay_after: Задержка после клика.
        
        Returns:
            Фактические координаты клика.
        """
        scatter = scatter if scatter is not None else self.scatter
        
        offset_x = random.randint(-scatter, scatter)
        offset_y = random.randint(-scatter, scatter)
        
        final_x = x + offset_x
        final_y = y + offset_y
        
        pyautogui.click(final_x, final_y)
        
        logger.debug(f"Click at ({final_x}, {final_y}) [offset: {offset_x}, {offset_y}]")
        
        if delay_after > 0:
            time.sleep(delay_after)
        
        return (final_x, final_y)
    
    def move_to(
        self, 
        x: int, 
        y: int,
        duration: Optional[float] = None
    ) -> None:
        """
        Плавное перемещение курсора.
        
        Args:
            x, y: Целевые координаты.
            duration: Время перемещения (None = случайное из диапазона).
        """
        if duration is None:
            duration = random.uniform(*self.move_duration_range)
        
        pyautogui.moveTo(x, y, duration=duration)
    
    def move_and_click(
        self, 
        x: int, 
        y: int,
        scatter: Optional[int] = None,
        delay_after: float = 0.0
    ) -> Tuple[int, int]:
        """
        Перемещение и клик.
        
        Args:
            x, y: Координаты.
            scatter: Максимальное смещение.
            delay_after: Задержка после клика.
        
        Returns:
            Фактические координаты клика.
        """
        self.move_to(x, y)
        time.sleep(random.uniform(0.05, 0.1))
        return self.click(x, y, scatter, delay_after)
    
    def type_text(
        self, 
        text: str,
        use_keyboard: bool = True,
        delay_range: Optional[Tuple[float, float]] = None
    ) -> None:
        """
        Ввод текста посимвольно.
        
        Args:
            text: Текст для ввода.
            use_keyboard: Использовать модуль keyboard (лучше для кириллицы).
            delay_range: Диапазон задержки между символами.
        """
        delay_range = delay_range or self.type_delay_range
        
        for char in text:
            if use_keyboard:
                keyboard.write(char)
            else:
                pyautogui.typewrite(char, interval=0)
            
            time.sleep(random.uniform(*delay_range))
    
    def clear_and_type(
        self, 
        x: int, 
        y: int, 
        text: str,
        select_all_first: bool = True
    ) -> None:
        """
        Клик по полю, очистка и ввод текста.
        
        Args:
            x, y: Координаты поля ввода.
            text: Текст для ввода.
            select_all_first: Выделить всё перед вводом (Ctrl+A).
        """
        self.click(x, y)
        time.sleep(random.uniform(0.1, 0.2))
        
        if select_all_first:
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.05)
        
        self.type_text(text)
    
    def press_key(self, key: str, delay_after: float = 0.1) -> None:
        """
        Нажатие клавиши.
        
        Args:
            key: Название клавиши ('enter', 'escape', etc.)
            delay_after: Задержка после нажатия.
        """
        pyautogui.press(key)
        if delay_after > 0:
            time.sleep(delay_after)
    
    def hotkey(self, *keys: str, delay_after: float = 0.1) -> None:
        """
        Комбинация клавиш.
        
        Args:
            *keys: Клавиши комбинации ('ctrl', 'c').
            delay_after: Задержка после нажатия.
        """
        pyautogui.hotkey(*keys)
        if delay_after > 0:
            time.sleep(delay_after)
    
    def random_delay(self, min_delay: float = 0.1, max_delay: float = 0.3) -> None:
        """Случайная задержка."""
        time.sleep(random.uniform(min_delay, max_delay))


# Глобальный экземпляр
_controller: Optional[AutomationController] = None


def get_automation_controller() -> AutomationController:
    """Получение глобального контроллера автоматизации."""
    global _controller
    if _controller is None:
        _controller = AutomationController()
    return _controller


# === Быстрые функции ===

def click(x: int, y: int, scatter: int = 5) -> Tuple[int, int]:
    """Клик со смещением."""
    return get_automation_controller().click(x, y, scatter)


def type_text(text: str) -> None:
    """Ввод текста."""
    get_automation_controller().type_text(text)


def move_and_click(x: int, y: int, scatter: int = 5) -> Tuple[int, int]:
    """Перемещение и клик."""
    return get_automation_controller().move_and_click(x, y, scatter)

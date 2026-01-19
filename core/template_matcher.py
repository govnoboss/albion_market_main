"""
Albion Market Bot v3.0 - Template Matcher

Автоматический поиск кнопок на экране через OpenCV Template Matching.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple, List
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import ImageGrab

from config import BASE_DIR

logger = logging.getLogger(__name__)

# Папка с шаблонами кнопок
TEMPLATES_DIR = BASE_DIR / "buttons_image"


@dataclass
class MatchResult:
    """Результат поиска шаблона."""
    found: bool
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    confidence: float = 0.0
    
    @property
    def center(self) -> Tuple[int, int]:
        """Центр найденной области."""
        return (self.x + self.width // 2, self.y + self.height // 2)


class TemplateMatcher:
    """Поиск элементов интерфейса через шаблоны."""
    
    # Кэш загруженных шаблонов
    _templates: dict = {}
    
    # Пороги уверенности для разных кнопок
    THRESHOLDS = {
        'buy_button': 0.8,
        'clear_button': 0.7,
        'ok_button': 0.8,
        'yes_button': 0.8,
        'sell_button': 0.8,
        'search_button': 0.7,
        'quantity_input_button': 0.75,
        'make_order': 0.8,
        'default': 0.75
    }
    
    def __init__(self):
        """Инициализация и предзагрузка шаблонов."""
        self._load_templates()
    
    def _load_templates(self):
        """Загрузка всех шаблонов из папки."""
        if not TEMPLATES_DIR.exists():
            logger.warning(f"Templates directory not found: {TEMPLATES_DIR}")
            return
        
        for template_path in TEMPLATES_DIR.glob("*.png"):
            name = template_path.stem  # buy_button, ok_button, etc.
            img = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
            if img is not None:
                self._templates[name] = img
                logger.debug(f"Loaded template: {name}")
        
        logger.info(f"Loaded {len(self._templates)} templates")
    
    def find_on_screen(
        self, 
        template_name: str,
        region: Optional[Tuple[int, int, int, int]] = None,
        threshold: Optional[float] = None
    ) -> MatchResult:
        """
        Поиск шаблона на экране.
        
        Args:
            template_name: Имя шаблона (без .png)
            region: Область поиска (left, top, width, height) или None для всего экрана
            threshold: Порог уверенности (0.0-1.0)
        
        Returns:
            MatchResult с координатами или found=False
        """
        if template_name not in self._templates:
            logger.error(f"Template not found: {template_name}")
            return MatchResult(found=False)
        
        template = self._templates[template_name]
        th = template.shape[0]  # height
        tw = template.shape[1]  # width
        
        # Захват экрана
        if region:
            left, top, width, height = region
            bbox = (left, top, left + width, top + height)
            screenshot = ImageGrab.grab(bbox=bbox)
            offset_x, offset_y = left, top
        else:
            screenshot = ImageGrab.grab()
            offset_x, offset_y = 0, 0
        
        # Конвертация в формат OpenCV
        screen_np = np.array(screenshot)
        screen_bgr = cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR)
        
        # Template matching
        result = cv2.matchTemplate(screen_bgr, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        # Порог
        if threshold is None:
            threshold = self.THRESHOLDS.get(template_name, self.THRESHOLDS['default'])
        
        if max_val >= threshold:
            x = max_loc[0] + offset_x
            y = max_loc[1] + offset_y
            return MatchResult(
                found=True,
                x=x,
                y=y,
                width=tw,
                height=th,
                confidence=max_val
            )
        
        logger.debug(f"Template '{template_name}' not found (max_val={max_val:.2f} < {threshold})")
        return MatchResult(found=False, confidence=max_val)
    
    def find_all_on_screen(
        self, 
        template_name: str,
        region: Optional[Tuple[int, int, int, int]] = None,
        threshold: Optional[float] = None,
        max_results: int = 10
    ) -> List[MatchResult]:
        """
        Поиск всех вхождений шаблона на экране.
        
        Args:
            template_name: Имя шаблона
            region: Область поиска
            threshold: Порог уверенности
            max_results: Максимум результатов
        
        Returns:
            Список MatchResult
        """
        if template_name not in self._templates:
            return []
        
        template = self._templates[template_name]
        th, tw = template.shape[:2]
        
        # Захват экрана
        if region:
            left, top, width, height = region
            bbox = (left, top, left + width, top + height)
            screenshot = ImageGrab.grab(bbox=bbox)
            offset_x, offset_y = left, top
        else:
            screenshot = ImageGrab.grab()
            offset_x, offset_y = 0, 0
        
        screen_np = np.array(screenshot)
        screen_bgr = cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR)
        
        result = cv2.matchTemplate(screen_bgr, template, cv2.TM_CCOEFF_NORMED)
        
        if threshold is None:
            threshold = self.THRESHOLDS.get(template_name, self.THRESHOLDS['default'])
        
        # Найти все точки выше порога
        locations = np.where(result >= threshold)
        matches = []
        
        for pt in zip(*locations[::-1]):  # x, y
            x = pt[0] + offset_x
            y = pt[1] + offset_y
            confidence = result[pt[1], pt[0]]
            
            # Фильтр дубликатов (близких точек)
            is_duplicate = False
            for existing in matches:
                if abs(existing.x - x) < tw // 2 and abs(existing.y - y) < th // 2:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                matches.append(MatchResult(
                    found=True, x=x, y=y, width=tw, height=th, confidence=confidence
                ))
            
            if len(matches) >= max_results:
                break
        
        # Сортировка по уверенности
        matches.sort(key=lambda m: m.confidence, reverse=True)
        return matches
    
    def wait_for_template(
        self, 
        template_name: str,
        timeout: float = 5.0,
        check_interval: float = 0.3,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> MatchResult:
        """
        Ожидание появления шаблона на экране.
        
        Args:
            template_name: Имя шаблона
            timeout: Таймаут в секундах
            check_interval: Интервал проверки
            region: Область поиска
        
        Returns:
            MatchResult
        """
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = self.find_on_screen(template_name, region)
            if result.found:
                return result
            time.sleep(check_interval)
        
        return MatchResult(found=False)


# Глобальный экземпляр
_matcher: Optional[TemplateMatcher] = None


def get_template_matcher() -> TemplateMatcher:
    """Получение глобального экземпляра."""
    global _matcher
    if _matcher is None:
        _matcher = TemplateMatcher()
    return _matcher


# === Быстрые функции ===

def find_button(name: str) -> MatchResult:
    """Поиск кнопки на экране."""
    return get_template_matcher().find_on_screen(name)


def find_buy_button() -> MatchResult:
    """Поиск кнопки 'Купить'."""
    return get_template_matcher().find_on_screen('buy_button')


def find_ok_button() -> MatchResult:
    """Поиск кнопки 'OK'."""
    return get_template_matcher().find_on_screen('ok_button')


def find_clear_button() -> MatchResult:
    """Поиск кнопки очистки."""
    return get_template_matcher().find_on_screen('clear_button')


def wait_for_button(name: str, timeout: float = 5.0) -> MatchResult:
    """Ожидание кнопки."""
    return get_template_matcher().wait_for_template(name, timeout)

"""
Логика взаимодействия с элементами интерфейса
Расчет координат для выпадающих меню и других элементов
"""

from typing import Tuple, Optional
from ..utils.config import get_config
from ..utils.logger import get_logger

class DropdownSelector:
    """Класс для расчета координат выбора в выпадающих меню"""
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_logger()
        
    def _get_dropdown_settings(self) -> dict:
        """Получить настройки выпадающих меню"""
        # Если настроек нет, возвращаем дефолтные значения (на случай старого конфига)
        defaults = {"row_height": 28, "list_start_offset": 30}
        return self.config._config.get("dropdowns", defaults)

    def get_dropdown_click_point(self, anchor_key: str, item_index: int) -> Optional[Tuple[int, int]]:
        """
        Рассчитать координату клика для пункта меню
        
        Args:
            anchor_key: Ключ координаты кнопки открытия меню (например, 'tier_dropdown')
            item_index: Индекс элемента в списке (0-based)
            
        Returns:
            Tuple[int, int]: Координаты (x, y) для клика или None, если якорь не найден
        """
        anchor = self.config.get_coordinate(anchor_key)
        
        if not anchor:
            self.logger.error(f"Координата якоря '{anchor_key}' не найдена!")
            return None
            
        anchor_x, anchor_y = anchor
        settings = self._get_dropdown_settings()
        
        row_height = settings.get("row_height", 28)
        start_offset = settings.get("list_start_offset", 30)
        
        # Расчет Y координаты: Якорь + Отступ до списка + (Индекс * Высота строки)
        target_y = anchor_y + start_offset + (item_index * row_height)
        
        return (anchor_x, target_y)

    def get_tier_click_point(self, tier: int) -> Optional[Tuple[int, int]]:
        """
        Получить координату для выбора Тира
        
        Args:
            tier: Уровень тира (4-8)
        """
        if not (4 <= tier <= 8):
            self.logger.warning(f"Запрошен некорректный тир: {tier}. Допустимо 4-8.")
            return None
            
        # Список тиров начинается с 4.0, поэтому индекс 0 соответствует T4
        index = tier - 4
        return self.get_dropdown_click_point("tier_dropdown", index)

    def get_enchant_click_point(self, enchant: int) -> Optional[Tuple[int, int]]:
        """
        Получить координату для выбора Зачарования
        
        Args:
            enchant: Уровень зачарования (0-4)
        """
        if not (0 <= enchant <= 4):
            self.logger.warning(f"Запрошено некорректное зачарование: {enchant}. Допустимо 0-4.")
            return None
            
        # Список зачарований: 0, 1, 2, 3, 4. Индекс совпадает со значением.
        return self.get_dropdown_click_point("enchant_dropdown", enchant)

    def get_quality_click_point(self, quality: int) -> Optional[Tuple[int, int]]:
        """
        Получить координату для выбора Качества
        
        Args:
            quality: Качество (1-5, где 1=Обычное, 2=Хорошее...)
        """
        if not (1 <= quality <= 5):
            self.logger.warning(f"Запрошено некорректное качество: {quality}. Допустимо 1-5.")
            return None
            
        # Список качеств начинается с 1 (Обычное). Индекс = quality - 1
        index = quality - 1
        return self.get_dropdown_click_point("quality_dropdown", index)

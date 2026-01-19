"""
Albion Market Bot v3.0 - Simplified Configuration

Упрощённая конфигурация: только 3 OCR-региона + автопоиск кнопок.
"""

from dataclasses import dataclass, field
from typing import Tuple
import json
from pathlib import Path


@dataclass
class OCRRegion:
    """Регион для OCR распознавания."""
    left: int = 0
    top: int = 0
    width: int = 100
    height: int = 30
    
    def to_tuple(self) -> Tuple[int, int, int, int]:
        """(left, top, width, height)"""
        return (self.left, self.top, self.width, self.height)
    
    def to_bbox(self) -> Tuple[int, int, int, int]:
        """(left, top, right, bottom) для ImageGrab"""
        return (self.left, self.top, self.left + self.width, self.top + self.height)
    
    def is_valid(self) -> bool:
        """Проверка что регион настроен."""
        return self.width > 0 and self.height > 0


@dataclass
class SimplifiedSettings:
    """
    Упрощённые настройки.
    
    Только 3 OCR-региона нужны вручную:
    - price_region: Цена в списке товаров (первая строка)
    - quantity_region: Количество в окне покупки
    - item_name_region: Название предмета для верификации
    
    Все кнопки находятся автоматически через Template Matching!
    """
    
    # === Только 3 обязательных OCR-региона ===
    price_region: OCRRegion = field(default_factory=OCRRegion)
    quantity_region: OCRRegion = field(default_factory=OCRRegion)
    item_name_region: OCRRegion = field(default_factory=OCRRegion)
    
    # === Настройки закупки ===
    budget: int = 10_000_000
    delay: float = 0.3
    start_row: int = 1
    tier6_only: bool = False
    transport_cost_per_kg: int = 350
    
    # === Статистика ===
    cumulative_spent: int = 0
    profile_name: str = "default"
    
    # === Опциональные координаты (fallback если template matching не работает) ===
    search_coords: Tuple[int, int] = (0, 0)  # Поле поиска
    
    def to_dict(self) -> dict:
        return {
            "profile_name": self.profile_name,
            "cumulative_spent": self.cumulative_spent,
            "regions": {
                "price": self.price_region.__dict__,
                "quantity": self.quantity_region.__dict__,
                "item_name": self.item_name_region.__dict__,
            },
            "buy": {
                "budget": self.budget,
                "delay": self.delay,
                "start_row": self.start_row,
                "tier6_only": self.tier6_only,
                "transport_cost_per_kg": self.transport_cost_per_kg,
            },
            "fallback": {
                "search_coords": list(self.search_coords),
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SimplifiedSettings":
        settings = cls()
        settings.profile_name = data.get("profile_name", "default")
        settings.cumulative_spent = data.get("cumulative_spent", 0)
        
        if "regions" in data:
            for name, values in data["regions"].items():
                region = getattr(settings, f"{name}_region", None)
                if region and isinstance(values, dict):
                    for k, v in values.items():
                        if hasattr(region, k):
                            setattr(region, k, v)
        
        if "buy" in data:
            for k, v in data["buy"].items():
                if hasattr(settings, k):
                    setattr(settings, k, v)
        
        if "fallback" in data:
            if "search_coords" in data["fallback"]:
                settings.search_coords = tuple(data["fallback"]["search_coords"])
        
        return settings


# Пути
SETTINGS_FILE = Path(__file__).parent / "data" / "settings_v2.json"


def load_simplified_settings() -> SimplifiedSettings:
    """Загрузка упрощённых настроек."""
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return SimplifiedSettings.from_dict(json.load(f))
    return SimplifiedSettings()


def save_simplified_settings(settings: SimplifiedSettings) -> None:
    """Сохранение настроек."""
    SETTINGS_FILE.parent.mkdir(exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings.to_dict(), f, indent=2, ensure_ascii=False)


# Краткое описание для GUI
REGIONS_DESCRIPTION = {
    "price_region": "📊 Цена в списке — область с ценой первого товара в списке",
    "quantity_region": "🔢 Количество — число доступных единиц в окне покупки", 
    "item_name_region": "📝 Название — текст названия предмета для проверки"
}

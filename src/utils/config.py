"""
Управление конфигурацией приложения
Сохранение и загрузка координат и настроек
"""

import json
import os
from pathlib import Path
from typing import Any, Optional


from .paths import get_app_root


class ConfigManager:
    """Менеджер конфигурации для сохранения координат и настроек"""
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            # Путь по умолчанию относительно корня проекта через централизованную утилиту
            config_path = get_app_root() / "config" / "coordinates.json"
        
        self.config_path = Path(config_path)
        # Убеждаемся, что папка существует
        self.config_path.parent.mkdir(exist_ok=True)
        self._config = self._load_config()
    
    def _load_config(self) -> dict:
        """Загрузка конфигурации из файла"""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Ошибка загрузки конфигурации: {e}")
                return self._default_config()
        return self._default_config()
    
    def _default_config(self) -> dict:
        """Конфигурация по умолчанию"""
        return {
            "coordinates": {},
            "settings": {
                "tesseract_path": "",
                "price_update_timeout": 5.0,
            },
            "dropdowns": {
                "row_height": 28,
                "list_start_offset": 30,
            },
            "scan_filters": {
                "tiers": [4, 5, 6, 7, 8],
                "enchants": [0, 1, 2, 3, 4],
                "qualities": [1, 2, 3, 4, 5]
            },
            "mouse_settings": {
                "speed_pps": 1800.0,
                "min_duration": 0.08,
                "curvature": 0.1
            },
            "items": []  # Список предметов для покупки
        }
    
    def save(self) -> bool:
        """Сохранение конфигурации в файл"""
        try:
            # Создаем директорию если не существует
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"Ошибка сохранения конфигурации: {e}")
            return False
    
    # === Координаты ===
    
    def get_coordinate(self, key: str) -> Optional[tuple]:
        """Получить точку (x, y)"""
        coord = self._config.get("coordinates", {}).get(key)
        # Fix: Default type to 'point' for backward compatibility
        if coord and isinstance(coord, dict) and coord.get("type", "point") == "point":
            return (coord.get("x"), coord.get("y"))
        return None
        
    def get_coordinate_area(self, key: str) -> Optional[dict]:
        """Получить область {x, y, w, h}"""
        coord = self._config.get("coordinates", {}).get(key)
        if coord and isinstance(coord, dict) and coord.get("type") == "area":
             return coord
        return None
    
    def set_coordinate(self, key: str, x: int, y: int) -> None:
        """Установить координату (точку)"""
        if "coordinates" not in self._config:
            self._config["coordinates"] = {}
        
        self._config["coordinates"][key] = {"x": x, "y": y, "type": "point"}
        self.save()

    def set_coordinate_area(self, key: str, x: int, y: int, w: int, h: int) -> None:
        """Установить координату (область)"""
        if "coordinates" not in self._config:
            self._config["coordinates"] = {}
        
        self._config["coordinates"][key] = {"x": x, "y": y, "w": w, "h": h, "type": "area"}
        self.save()

    def get_coordinate_color(self, key: str) -> Optional[tuple]:
        """Получить цвет пикселя (r, g, b)"""
        coord = self._config.get("coordinates", {}).get(key)
        if coord and isinstance(coord, dict) and "color" in coord:
            return tuple(coord["color"])
        return None

    def set_coordinate_color(self, key: str, x: int, y: int, color: tuple) -> None:
        """Установить координату и цвет пикселя"""
        if "coordinates" not in self._config:
            self._config["coordinates"] = {}
        
        self._config["coordinates"][key] = {
            "x": x, 
            "y": y, 
            "color": list(color), 
            "type": "point"
        }
        self.save()
    
    def get_all_coordinates(self) -> dict:
        """Получить все координаты"""
        return self._config.get("coordinates", {})
    
    def clear_coordinate(self, key: str) -> None:
        """Очистить координату"""
        if key in self._config.get("coordinates", {}):
            del self._config["coordinates"][key]
            self.save()
    
    # === Настройки ===
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Получить настройку"""
        return self._config.get("settings", {}).get(key, default)
    
    def set_setting(self, key: str, value: Any) -> None:
        """Установить настройку"""
        if "settings" not in self._config:
            self._config["settings"] = {}
        
        self._config["settings"][key] = value
        self.save()
    

    # === Dropdown Settings ===

    def get_dropdown_setting(self, key: str, default: Any = None) -> Any:
        """Получить настройку выпадающего меню"""
        return self._config.get("dropdowns", {}).get(key, default)

    def set_dropdown_setting(self, key: str, value: Any) -> None:
        """Установить настройку выпадающего меню"""
        if "dropdowns" not in self._config:
            self._config["dropdowns"] = {}
        
        self._config["dropdowns"][key] = value
        self.save()

    # === Scan Filters ===

    def get_scan_filters(self) -> dict:
        """Получить настройки фильтров сканирования"""
        defaults = {
            "tiers": [4, 5, 6, 7, 8],
            "enchants": [0, 1, 2, 3, 4],
            "qualities": [1, 2, 3, 4, 5]
        }
        return self._config.get("scan_filters", defaults)

    def set_scan_filter(self, category: str, values: list) -> None:
        """Установить фильтр сканирования"""
        if "scan_filters" not in self._config:
            self._config["scan_filters"] = {}
        
        self._config["scan_filters"][category] = values
        self.save()

    # === Mouse Settings ===

    def get_mouse_settings(self) -> dict:
        """Получить настройки мыши"""
        defaults = {
            "speed_pps": 1800.0,
            "min_duration": 0.08,
            "curvature": 0.1
        }
        return self._config.get("mouse_settings", defaults)

    def set_mouse_setting(self, key: str, value: Any) -> None:
        """Установить настройку мыши"""
        if "mouse_settings" not in self._config:
            self._config["mouse_settings"] = {}
        
        self._config["mouse_settings"][key] = value
        self.save()


    # === Known Items (Database) ===

    def get_known_items(self) -> list:
        """Получить список известных предметов"""
        return self._config.get("known_items", [])

    def set_known_items(self, items: list) -> None:
        """Установить список известных предметов"""
        self._config["known_items"] = items
        self.save()

    def add_known_item(self, item: str) -> None:
        """Добавить предмет в базу известных"""
        items = self.get_known_items()
        if item not in items:
            items.append(item)
            self._config["known_items"] = items
            self.save()

    # === Предметы ===
    
    def get_items(self) -> list:
        """Получить список предметов для покупки"""
        return self._config.get("items", [])
    
    def add_item(self, name: str, max_price: int = 0, quantity: int = 1) -> None:
        """Добавить предмет в список"""
        if "items" not in self._config:
            self._config["items"] = []
        
        item = {
            "name": name,
            "max_price": max_price,
            "quantity": quantity,
            "enabled": True
        }
        self._config["items"].append(item)
        self.save()
    
    def remove_item(self, index: int) -> None:
        """Удалить предмет из списка"""
        items = self._config.get("items", [])
        if 0 <= index < len(items):
            items.pop(index)
            self.save()
    
    def update_item(self, index: int, **kwargs) -> None:
        """Обновить предмет"""
        items = self._config.get("items", [])
        if 0 <= index < len(items):
            items[index].update(kwargs)
            self.save()
    
    def clear_items(self) -> None:
        """Очистить список предметов"""
        self._config["items"] = []
        self.save()

    # === Tier Exceptions ===

    def get_tier_exceptions(self) -> dict:
        """Получить словарь исключений тиров"""
        return self._config.get("tier_exceptions", {
            "Tier_1": [], 
            "Tier_2": [], 
            "Tier_3": []
        })

    def set_tier_exceptions(self, data: dict):
        """Сохранить словарь исключений тиров"""
        self._config["tier_exceptions"] = data
        self.save()

    def is_tier_exception(self, tier: int, item_name: str) -> bool:
        """
        Проверить, является ли данный предмет исключением для данного тира.
        (Например, если для T4 он не существует или его нельзя скрафтить).
        Возвращает True, если надо пропустить.
        """
        exceptions = self.get_tier_exceptions()

        # Формат ключа: "Tier_{tier}"
        key = f"Tier_{tier}"
        
        # Если в списке исключений для этого тира есть этот предмет -> True
        if key in exceptions:
            # Нормализация для надежности
            target = item_name.strip()
            # Проверяем, есть ли совпадение
            if target in exceptions[key]:
                 return True
                 
        return False

    # === Wholesale Targets (Buyer) ===

    def get_wholesale_targets(self) -> dict:
        """
        Получить настройки оптовой закупки.
        Format: { "Item Name": { "T4.0": {"limit": 10, "enabled": True}, ... } }
        """
        return self._config.get("wholesale_targets", {})
        
    def set_wholesale_target(self, item_name: str, tier: int, enchant: int, limit: int, enabled: bool, min_profit: int = 15):
        """Сохранить настройку для конкретной вариации"""
        if "wholesale_targets" not in self._config:
            self._config["wholesale_targets"] = {}
            
        targets = self._config["wholesale_targets"]
        
        if item_name not in targets:
            targets[item_name] = {}
            
        key = f"T{tier}.{enchant}"
        targets[item_name][key] = {
            "limit": limit,
            "enabled": enabled,
            "min_profit": min_profit
        }
        self.save()
        
    def get_wholesale_limit(self, item_name: str, tier: int, enchant: int) -> tuple[int, bool, int]:
        """Получить (limit, enabled, min_profit) для вариации. Возвращает (0, False, 15) если не задано."""
        targets = self._config.get("wholesale_targets", {})
        key = f"T{tier}.{enchant}"
        
        data = targets.get(item_name, {}).get(key, {})
        return (data.get("limit", 0), data.get("enabled", False), data.get("min_profit", 15))


    # === Profiles ===

    def get_profiles_list(self) -> list:
        """Получить список доступных профилей"""
        profiles_dir = self.config_path.parent / "profiles"
        if not profiles_dir.exists():
            return []
        return sorted([f.stem for f in profiles_dir.glob("*.json")])

    def save_profile(self, name: str) -> bool:
        """Сохранить текущие координаты в профиль"""
        try:
            profiles_dir = self.config_path.parent / "profiles"
            profiles_dir.mkdir(exist_ok=True)
            
            # Простейшая валидация имени
            safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip()
            if not safe_name:
                return False
                
            file_path = profiles_dir / f"{safe_name}.json"
            
            # Сохраняем ТОЛЬКО координаты
            data = {"coordinates": self._config.get("coordinates", {})}
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Ошибка сохранения профиля: {e}")
            return False

    def load_profile(self, name: str) -> bool:
        """Загрузить координаты из профиля"""
        try:
            profiles_dir = self.config_path.parent / "profiles"
            file_path = profiles_dir / f"{name}.json"
            
            if not file_path.exists():
                return False
                
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            if "coordinates" in data:
                self._config["coordinates"] = data["coordinates"]
                self.save() # Сохраняем как текущую активную конфигурацию
                return True
            return False
        except Exception as e:
            print(f"Ошибка загрузки профиля: {e}")
            return False

    def delete_profile(self, name: str) -> bool:
        """Удалить профиль"""
        try:
            profiles_dir = self.config_path.parent / "profiles"
            file_path = profiles_dir / f"{name}.json"
            
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            print(f"Ошибка удаления профиля: {e}")
            return False


# Глобальный экземпляр
_config_manager: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """Получить глобальный экземпляр ConfigManager"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

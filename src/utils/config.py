"""
Управление конфигурацией приложения
Сохранение и загрузка координат и настроек
"""

import json
import os
from pathlib import Path
from typing import Any, Optional


class ConfigManager:
    """Менеджер конфигурации для сохранения координат и настроек"""
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            # Путь по умолчанию относительно корня проекта
            base_dir = Path(__file__).parent.parent.parent
            config_path = base_dir / "config" / "coordinates.json"
        
        self.config_path = Path(config_path)
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
                "click_delay": 100,
                "scan_interval": 500,
                "tesseract_path": "",
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
        """Получить координату по ключу"""
        coord = self._config.get("coordinates", {}).get(key)
        if coord and isinstance(coord, dict):
            return (coord.get("x"), coord.get("y"))
        return None
    
    def set_coordinate(self, key: str, x: int, y: int) -> None:
        """Установить координату"""
        if "coordinates" not in self._config:
            self._config["coordinates"] = {}
        
        self._config["coordinates"][key] = {"x": x, "y": y}
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


# Глобальный экземпляр
_config_manager: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """Получить глобальный экземпляр ConfigManager"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

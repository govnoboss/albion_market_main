"""
Модуль хранения цен предметов по городам
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, List

from .logger import get_logger

# Путь к файлу с ценами
PRICES_FILE = os.path.join(os.getcwd(), "data", "prices.json")


class PriceStorage:
    """Хранилище цен предметов по городам"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.logger = get_logger()
        self._data: Dict = {}
        self._load()
    
    def _load(self):
        """Загрузка данных из файла"""
        try:
            if os.path.exists(PRICES_FILE):
                with open(PRICES_FILE, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
                self.logger.debug(f"Цены загружены: {len(self._data)} городов")
            else:
                self._data = {}
        except Exception as e:
            self.logger.error(f"Ошибка загрузки цен: {e}")
            self._data = {}
    
    def _save(self):
        """Сохранение данных в файл"""
        try:
            # Создаем папку data если нет
            os.makedirs(os.path.dirname(PRICES_FILE), exist_ok=True)
            
            with open(PRICES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения цен: {e}")
    
    def save_price(self, city: str, item_name: str, tier: int, enchant: int, quality: int, price: int):
        """
        Сохранить цену предмета
        
        Args:
            city: Название города (например "Caerleon")
            item_name: Название предмета (например "Авалонский Плащ")
            tier: Тир (4-8)
            enchant: Зачарование (0-4)
            quality: Качество (игнорируется для ключа, цена сохраняется последняя)
            price: Цена
        """
        if price <= 0:
            return  # Не сохраняем нулевые/отрицательные цены
        
        # Создаем структуру если нет
        if city not in self._data:
            self._data[city] = {}
        
        if item_name not in self._data[city]:
            self._data[city][item_name] = {}
        
        # Ключ вариации: "T4.0" (без качества, объединяем всё)
        variant_key = f"T{tier}.{enchant}"
        
        # Сохраняем с временной меткой
        self._data[city][item_name][variant_key] = {
            "price": price,
            "updated": datetime.now().isoformat()
        }
        
        self._save()
    
    def get_cities(self) -> List[str]:
        """Получить список городов"""
        return list(self._data.keys())
    
    def get_city_prices(self, city: str) -> Dict:
        """Получить все цены для города"""
        return self._data.get(city, {})
    
    def get_item_price(self, city: str, item_name: str, tier: int, enchant: int, quality: int) -> Optional[int]:
        """Получить цену конкретного предмета"""
        # Ключ теперь без качества
        variant_key = f"T{tier}.{enchant}"
        try:
            return self._data[city][item_name][variant_key]["price"]
        except KeyError:
            return None
    
    def clear_city(self, city: str):
        """Очистить данные города"""
        if city in self._data:
            del self._data[city]
            self._save()
    
    def reload(self):
        """Перезагрузить данные из файла"""
        self._load()


def get_price_storage() -> PriceStorage:
    """Получить экземпляр хранилища цен (Singleton)"""
    return PriceStorage()

# Экспорт синглтона для удобного импорта
price_storage = get_price_storage()

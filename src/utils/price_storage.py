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
    
    def delete_price(self, city: str, item_name: str, variant: str):
        """Удалить конкретную запись о цене"""
        if city in self._data and item_name in self._data[city]:
            if variant in self._data[city][item_name]:
                del self._data[city][item_name][variant]
                # Clean up empty dicts
                if not self._data[city][item_name]:
                    del self._data[city][item_name]
                self._save()

    def clean_history(self, gap_minutes: int = 30) -> int:
        """
        Удалить записи старых сессий.
        Оставляет только последнюю непрерывную сессию сканирования.
        
        Args:
            gap_minutes: Максимальный разрыв в минутах внутри одной сессии.
            
        Returns:
            Количество удаленных записей.
        """
        all_records = []
        # 1. Собираем все записи
        for city, items in self._data.items():
            for item_name, variants in items.items():
                for variant, info in variants.items():
                    try:
                        dt = datetime.fromisoformat(info['updated'])
                        all_records.append({
                            'dt': dt,
                            'city': city,
                            'item': item_name,
                            'variant': variant
                        })
                    except (ValueError, KeyError):
                        continue
        
        if not all_records:
            return 0

        # 2. Сортируем: новые -> старые
        all_records.sort(key=lambda x: x['dt'], reverse=True)
        
        # 3. Находим границу сессии
        cutoff_index = len(all_records) # По умолчанию оставляем всё
        
        for i in range(len(all_records) - 1):
            current_time = all_records[i]['dt']
            prev_time = all_records[i+1]['dt']
            
            diff = (current_time - prev_time).total_seconds() / 60
            
            if diff > gap_minutes:
                # Нашли разрыв!
                # prev_time и всё что после него - это старая сессия
                cutoff_index = i + 1
                self.logger.info(f"Найдена граница сессии: {current_time} -> {prev_time} (Diff: {diff:.1f} min)")
                break
        
        if cutoff_index == len(all_records):
            self.logger.info("Разрывов сессий не найдено. Удалять нечего.")
            return 0
            
        # 4. Удаляем старые записи
        to_delete = all_records[cutoff_index:]
        count = 0
        
        for rec in to_delete:
            city, item, variant = rec['city'], rec['item'], rec['variant']
            if city in self._data and item in self._data[city] and variant in self._data[city][item]:
                del self._data[city][item][variant]
                count += 1
                
                # Чистим пустые словари
                if not self._data[city][item]:
                    del self._data[city][item]
        
        # Чистим пустые города
        cities_to_drop = [c for c, items in self._data.items() if not items]
        for c in cities_to_drop:
            del self._data[c]
            
        self._save()
        self.logger.info(f"Очищена история: удалено {count} записей")
        return count

    def remove_older_than(self, hours: int) -> int:
        """
        Удалить записи старее чем records_age, относительно текущего времени.
        
        Args:
            hours: Возраст в часах, после которого запись считается устаревшей.
            
        Returns:
            Количество удаленных записей.
        """
        now = datetime.now()
        count = 0
        
        for city, items in list(self._data.items()):
            for item_name, variants in list(items.items()):
                for variant, info in list(variants.items()):
                    try:
                        record_dt = datetime.fromisoformat(info['updated'])
                        age_hours = (now - record_dt).total_seconds() / 3600
                        
                        if age_hours > hours:
                            del self._data[city][item_name][variant]
                            count += 1
                    except (ValueError, KeyError):
                        continue
                        
                # Убираем пустые
                if not self._data[city][item_name]:
                    del self._data[city][item_name]
            
            if not self._data[city]:
                del self._data[city]
                
        if count > 0:
            self._save()
            self.logger.info(f"Очищены устаревшие записи (> {hours} ч.): {count} шт.")
            
        return count

    def reload(self):
        """Перезагрузить данные из файла"""
        self._load()


def get_price_storage() -> PriceStorage:
    """Получить экземпляр хранилища цен (Singleton)"""
    return PriceStorage()

# Экспорт синглтона для удобного импорта
price_storage = get_price_storage()

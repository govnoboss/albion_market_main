"""
Albion Market Bot v3.0 - Configuration Module

Централизованная конфигурация приложения.
"""

import os
import sys
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# === Пути ===
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
LEGACY_DIR = BASE_DIR / "_legacy"
LOGS_DIR = BASE_DIR / "logs"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"

# Создание необходимых директорий
for directory in [DATA_DIR, LOGS_DIR, SCREENSHOTS_DIR]:
    directory.mkdir(exist_ok=True)

# === Tesseract ===
TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Tesseract-OCR\tesseract.exe",
]


def find_tesseract() -> Optional[Path]:
    """Поиск исполняемого файла Tesseract."""
    for path_str in TESSERACT_PATHS:
        path = Path(path_str)
        if path.exists():
            return path
    return None


TESSERACT_PATH = find_tesseract()


# === Настройки по умолчанию ===
@dataclass
class Coordinates:
    """Координаты кнопок интерфейса."""
    search_x: int = 0
    search_y: int = 0
    clear_x: int = 0
    clear_y: int = 0
    buy_x: int = 0
    buy_y: int = 0
    confirm_x: int = 0
    confirm_y: int = 0
    quantity_x: int = 0
    quantity_y: int = 0
    buy_order_x: int = 0
    buy_order_y: int = 0
    price_per_unit_x: int = 0
    price_per_unit_y: int = 0
    minus_x: int = 0
    minus_y: int = 0
    close_x: int = 0
    close_y: int = 0
    quality_x: int = 0
    quality_y: int = 0


@dataclass
class Region:
    """Регион экрана для OCR."""
    left: int = 0
    top: int = 0
    width: int = 100
    height: int = 30
    
    def to_tuple(self) -> tuple:
        """Преобразование в (left, top, width, height)."""
        return (self.left, self.top, self.width, self.height)
    
    def to_bbox(self) -> tuple:
        """Преобразование в (left, top, right, bottom) для ImageGrab."""
        return (self.left, self.top, self.left + self.width, self.top + self.height)


@dataclass
class OCRRegions:
    """Регионы для OCR распознавания."""
    price: Region = field(default_factory=Region)
    quantity: Region = field(default_factory=Region)
    item_name: Region = field(default_factory=Region)
    sell_price: Region = field(default_factory=Region)
    sell_item_price: Region = field(default_factory=Region)


@dataclass
class BuySettings:
    """Настройки закупки."""
    budget: int = 10_000_000
    delay: float = 0.3
    start_row: int = 1
    tier6_only: bool = False
    transport_cost_per_kg: int = 350


@dataclass
class AppSettings:
    """Полные настройки приложения."""
    coordinates: Coordinates = field(default_factory=Coordinates)
    regions: OCRRegions = field(default_factory=OCRRegions)
    buy: BuySettings = field(default_factory=BuySettings)
    cumulative_spent: int = 0
    profile_name: str = "default"
    
    def to_dict(self) -> dict:
        """Сериализация в словарь."""
        return {
            "profile_name": self.profile_name,
            "cumulative_spent": self.cumulative_spent,
            "coordinates": self.coordinates.__dict__,
            "regions": {
                "price": self.regions.price.__dict__,
                "quantity": self.regions.quantity.__dict__,
                "item_name": self.regions.item_name.__dict__,
                "sell_price": self.regions.sell_price.__dict__,
                "sell_item_price": self.regions.sell_item_price.__dict__,
            },
            "buy": self.buy.__dict__,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AppSettings":
        """Десериализация из словаря."""
        settings = cls()
        settings.profile_name = data.get("profile_name", "default")
        settings.cumulative_spent = data.get("cumulative_spent", 0)
        
        if "coordinates" in data:
            for key, value in data["coordinates"].items():
                if hasattr(settings.coordinates, key):
                    setattr(settings.coordinates, key, value)
        
        if "regions" in data:
            for region_name in ["price", "quantity", "item_name", "sell_price", "sell_item_price"]:
                if region_name in data["regions"]:
                    region = getattr(settings.regions, region_name)
                    for key, value in data["regions"][region_name].items():
                        if hasattr(region, key):
                            setattr(region, key, value)
        
        if "buy" in data:
            for key, value in data["buy"].items():
                if hasattr(settings.buy, key):
                    setattr(settings.buy, key, value)
        
        return settings


# === Файлы данных ===
SETTINGS_FILE = DATA_DIR / "settings.json"
ITEMS_FILE = DATA_DIR / "items.xlsx"
PURCHASE_LOG_FILE = DATA_DIR / "purchase_log.csv"

# Для обратной совместимости
LEGACY_SETTINGS_FILE = BASE_DIR / "bot_settings.json"
LEGACY_TABLE_FILE = BASE_DIR / "table.xlsx"


def load_settings() -> AppSettings:
    """Загрузка настроек из файла."""
    # Сначала пробуем новый файл
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return AppSettings.from_dict(json.load(f))
    
    # Fallback на legacy файл
    if LEGACY_SETTINGS_FILE.exists():
        with open(LEGACY_SETTINGS_FILE, "r", encoding="utf-8") as f:
            legacy_data = json.load(f)
            return _migrate_legacy_settings(legacy_data)
    
    return AppSettings()


def save_settings(settings: AppSettings) -> None:
    """Сохранение настроек в файл."""
    DATA_DIR.mkdir(exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings.to_dict(), f, indent=2, ensure_ascii=False)


def _migrate_legacy_settings(legacy: dict) -> AppSettings:
    """Миграция настроек из старого формата."""
    settings = AppSettings()
    
    # Координаты
    coord_mapping = {
        "search_x": "search_x", "search_y": "search_y",
        "clear_x": "clear_x", "clear_y": "clear_y",
        "buy_x": "buy_x", "buy_y": "buy_y",
        "confirm_x": "confirm_x", "confirm_y": "confirm_y",
        "quantity_x": "quantity_x", "quantity_y": "quantity_y",
        "buy_order_x": "buy_order_x", "buy_order_y": "buy_order_y",
        "price_per_unit_x": "price_per_unit_x", "price_per_unit_y": "price_per_unit_y",
        "minus_x": "minus_x", "minus_y": "minus_y",
        "close_x": "close_x", "close_y": "close_y",
        "quality_x": "quality_x", "quality_y": "quality_y",
    }
    
    for legacy_key, new_key in coord_mapping.items():
        if legacy_key in legacy:
            setattr(settings.coordinates, new_key, int(legacy.get(legacy_key, 0) or 0))
    
    # Регионы
    if "left" in legacy:
        settings.regions.price = Region(
            left=int(legacy.get("left", 0) or 0),
            top=int(legacy.get("top", 0) or 0),
            width=int(legacy.get("width", 100) or 100),
            height=int(legacy.get("height", 30) or 30),
        )
    
    if "left_q" in legacy:
        settings.regions.quantity = Region(
            left=int(legacy.get("left_q", 0) or 0),
            top=int(legacy.get("top_q", 0) or 0),
            width=int(legacy.get("width_q", 30) or 30),
            height=int(legacy.get("height_q", 20) or 20),
        )
    
    if "left_item_name" in legacy:
        settings.regions.item_name = Region(
            left=int(legacy.get("left_item_name", 0) or 0),
            top=int(legacy.get("top_item_name", 0) or 0),
            width=int(legacy.get("width_item_name", 300) or 300),
            height=int(legacy.get("height_item_name", 30) or 30),
        )
    
    if "left_sell" in legacy:
        settings.regions.sell_price = Region(
            left=int(legacy.get("left_sell", 0) or 0),
            top=int(legacy.get("top_sell", 0) or 0),
            width=int(legacy.get("width_sell", 90) or 90),
            height=int(legacy.get("height_sell", 30) or 30),
        )
    
    if "left_sell_item_price" in legacy:
        settings.regions.sell_item_price = Region(
            left=int(legacy.get("left_sell_item_price", 0) or 0),
            top=int(legacy.get("top_sell_item_price", 0) or 0),
            width=int(legacy.get("width_sell_item_price", 60) or 60),
            height=int(legacy.get("height_sell_item_price", 25) or 25),
        )
    
    # Настройки закупки
    settings.buy.budget = int(legacy.get("budget", 10_000_000) or 10_000_000)
    settings.buy.delay = float(legacy.get("delay", 0.3) or 0.3)
    settings.buy.start_row = int(legacy.get("start_row", 1) or 1)
    settings.buy.tier6_only = legacy.get("tier6_only", False)
    
    settings.cumulative_spent = int(legacy.get("cumulative_spent", 0) or 0)
    
    return settings


# === Проверка окружения ===
def validate_environment() -> list[str]:
    """Проверка наличия необходимых компонентов. Возвращает список ошибок."""
    errors = []
    
    if TESSERACT_PATH is None:
        errors.append("Tesseract OCR не найден. Установите его и укажите путь.")
    
    # Проверяем таблицу предметов
    if not ITEMS_FILE.exists() and not LEGACY_TABLE_FILE.exists():
        errors.append("Файл с предметами (items.xlsx или table.xlsx) не найден.")
    
    return errors

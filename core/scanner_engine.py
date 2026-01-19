"""
Albion Market Bot v3.0 - Scanner Engine v2

Движок сканирования цен с поддержкой Тир/Энчант/Качество.
"""

import time
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Iterator
from dataclasses import dataclass, field
from datetime import datetime

from core.smart_automation import get_smart_automation
from core.ocr_engine import get_ocr_engine
from core.template_matcher import get_template_matcher

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Результат сканирования одной комбинации предмет+тир+энчант+качество."""
    item_name: str
    tier: int = 0
    enchant: int = 0
    quality: int = 0
    price: int = 0
    quantity: int = 0
    avg_price: int = 0
    scan_time: str = ""
    city: str = ""
    success: bool = False
    error: str = ""
    
    @property
    def full_name(self) -> str:
        """Полное имя с тиром/энчантом."""
        enchant_str = f".{self.enchant}" if self.enchant > 0 else ""
        quality_names = ["", " (Хорошее)", " (Выдающееся)", " (Превосходное)", " (Шедевр)"]
        quality_str = quality_names[self.quality] if 0 <= self.quality < len(quality_names) else ""
        return f"T{self.tier}{enchant_str} {self.item_name}{quality_str}"


@dataclass 
class ScannerConfig:
    """Конфигурация сканера."""
    items_file: Path = Path("data/items_to_scan.json")
    results_dir: Path = Path("data/results")
    current_city: str = "Lymhurst"
    market_mode: str = "regular"  # "regular" или "black"
    
    # Выбранные значения для сканирования (списки)
    selected_tiers: List[int] = field(default_factory=lambda: [4, 5, 6, 7, 8])
    selected_enchants: List[int] = field(default_factory=lambda: [0])
    selected_qualities: List[int] = field(default_factory=lambda: [0])
    
    # Настройки dropdown меню
    dropdown_item_height: int = 25      # Высота элемента в dropdown (px)
    dropdown_first_offset: int = 30     # Смещение до первого элемента (px)
    
    # Задержки
    delay_after_search: float = 0.8
    delay_after_click: float = 0.3
    delay_after_expand: float = 0.5
    delay_after_dropdown: float = 0.3


# Маппинг значений на позиции в dropdown
# Для ОБЫЧНЫХ предметов (начинаются с Tier 4):
# Tier 4 = индекс 0, Tier 5 = индекс 1, и т.д.
# Для ИСКЛЮЧЕНИЙ (начинаются с Tier 1, 2 или 3):
# Индекс вычисляется как (target_tier - min_tier_for_item)
ENCHANT_VALUES = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4}
QUALITY_VALUES = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4}


class ScannerEngineV2:
    """
    Движок сканирования цен v2.
    
    Поддерживает итерацию по Тир/Энчант/Качество.
    
    Flow для каждого предмета:
    1. Поиск и открытие меню предмета
    2. Раскрытие панели
    3. Для каждого Тира (4-8):
       a. Выбор тира в dropdown
       b. Для каждого Энчанта (0-4):
          - Выбор энчанта
          c. Для каждого Качества (0-4):
             - Выбор качества
             - Чтение цены
             - Сохранение результата
    4. Закрытие меню и переход к след. предмету
    """
    
    def __init__(self, config: ScannerConfig = None):
        self.config = config or ScannerConfig()
        self.smart = get_smart_automation()
        self.ocr = get_ocr_engine()
        self.matcher = get_template_matcher()
        
        self.results: List[ScanResult] = []
        self._running = True
        self._paused = False
        
        # Callbacks
        self.on_progress = None  # (current, total, description)
        self.on_status = None    # (message)
        self.on_result = None    # (ScanResult)
        
        # Загрузка исключений (предметы с тирами 1-3)
        self._exceptions = self._load_exceptions()
        self._current_item_min_tier = 4  # Минимальный тир текущего предмета
    
    def _load_exceptions(self) -> Dict[str, int]:
        """
        Загрузка предметов-исключений.
        
        Returns:
            Dict[item_name_lower, min_tier]
        """
        exceptions_path = Path("exceptions.json")
        exceptions = {}
        
        if not exceptions_path.exists():
            logger.warning(f"Exceptions file not found: {exceptions_path}")
            return exceptions
        
        try:
            with open(exceptions_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Обработка структуры {"Tier_1": [...], "Tier_2": [...], "Tier_3": [...]}
            for tier_key, items in data.items():
                tier_num = int(tier_key.split('_')[1])  # "Tier_2" -> 2
                for item in items:
                    exceptions[item.lower()] = tier_num
            
            logger.info(f"Loaded {len(exceptions)} exception items")
            
        except Exception as e:
            logger.error(f"Error loading exceptions: {e}")
        
        return exceptions
    
    def _get_item_min_tier(self, item_name: str) -> int:
        """
        Получение минимального тира для предмета.
        
        Args:
            item_name: Название предмета
        
        Returns:
            Минимальный тир (1, 2, 3 для исключений, 4 для обычных)
        """
        item_lower = item_name.lower()
        
        # Проверка точного совпадения
        if item_lower in self._exceptions:
            return self._exceptions[item_lower]
        
        # Проверка частичного совпадения (без " (знаток)" и т.д.)
        for exc_name, min_tier in self._exceptions.items():
            if exc_name in item_lower or item_lower in exc_name:
                return min_tier
        
        # По умолчанию - обычный предмет с тира 4
        return 4
    
    def load_items(self) -> List[str]:
        """Загрузка списка предметов для сканирования."""
        items_path = Path(self.config.items_file)
        
        if not items_path.exists():
            logger.error(f"Items file not found: {items_path}")
            return []
        
        with open(items_path, 'r', encoding='utf-8') as f:
            items = json.load(f)
        
        logger.info(f"Loaded {len(items)} items to scan")
        return items
    
    def stop(self):
        self._running = False
    
    def pause(self):
        self._paused = True
    
    def resume(self):
        self._paused = False
    
    def _wait_if_paused(self):
        while self._paused and self._running:
            time.sleep(0.1)
    
    def _log_status(self, message: str):
        logger.info(message)
        if self.on_status:
            self.on_status(message)
    
    def _generate_combinations(self) -> Iterator[Tuple[int, int, int]]:
        """
        Генератор комбинаций (tier, enchant, quality).
        
        Порядок: Tier -> Enchant -> Quality
        """
        for tier in sorted(self.config.selected_tiers):
            for enchant in sorted(self.config.selected_enchants):
                for quality in sorted(self.config.selected_qualities):
                    yield (tier, enchant, quality)
    
    def _count_combinations(self) -> int:
        """Подсчёт общего числа комбинаций."""
        tiers = len(self.config.selected_tiers)
        enchants = len(self.config.selected_enchants)
        qualities = len(self.config.selected_qualities)
        return tiers * enchants * qualities
    
    def _check_and_expand_panel(self) -> bool:
        """Проверка и раскрытие панели с ордерами."""
        expand_result = self.matcher.find_on_screen('expand_arrow')
        
        if expand_result.found:
            cx, cy = expand_result.center
            self.smart.controller.move_and_click(cx, cy, scatter=2)
            self._log_status("↔️ Раскрытие панели...")
            time.sleep(self.config.delay_after_expand)
            return True
        
        collapse_result = self.matcher.find_on_screen('collapse_arrow')
        return collapse_result.found
    
    def _close_item_panel(self) -> bool:
        """Закрытие окна предмета."""
        return self.smart.click_button('close_item_panel', timeout=2.0)
    
    def _select_dropdown_value(self, dropdown_template: str, value_index: int) -> bool:
        """
        Выбор значения в dropdown.
        
        Args:
            dropdown_template: Имя шаблона кнопки dropdown
            value_index: Индекс значения (0 = первое)
        
        Returns:
            True если успешно
        """
        # Клик на dropdown кнопку
        result = self.matcher.find_on_screen(dropdown_template)
        if not result.found:
            logger.warning(f"Dropdown '{dropdown_template}' not found")
            return False
        
        cx, cy = result.center
        self.smart.controller.move_and_click(cx, cy, scatter=2)
        time.sleep(self.config.delay_after_dropdown)
        
        # Клик на нужный элемент списка
        # Используем настройки из конфига
        item_height = self.config.dropdown_item_height
        first_offset = self.config.dropdown_first_offset
        target_y = cy + first_offset + (value_index * item_height)
        
        self.smart.controller.move_and_click(cx, target_y, scatter=2)
        time.sleep(self.config.delay_after_click)
        
        return True
    
    def _select_tier(self, tier: int, item_name: str = None) -> bool:
        """
        Выбор тира с учётом исключений.
        
        Args:
            tier: Целевой тир (4-8)
            item_name: Название предмета для проверки исключений
        """
        if tier < 4 or tier > 8:
            return False
        
        # Определяем минимальный тир предмета
        if item_name:
            self._current_item_min_tier = self._get_item_min_tier(item_name)
        
        min_tier = self._current_item_min_tier
        
        # Вычисляем индекс в dropdown
        # Для обычного предмета (min_tier=4): T4=0, T5=1, ...
        # Для исключения (min_tier=2): T4=2, T5=3, ...
        index = tier - min_tier
        
        if index < 0:
            logger.warning(f"Tier {tier} below minimum {min_tier} for item")
            return False
        
        return self._select_dropdown_value('tier_dropdown', index)
    
    def _select_enchant(self, enchant: int) -> bool:
        """Выбор зачарования."""
        if enchant < 0 or enchant > 4:
            return False
        return self._select_dropdown_value('enchant_dropdown', enchant)
    
    def _select_quality(self, quality: int) -> bool:
        """Выбор качества."""
        if quality < 0 or quality > 4:
            return False
        return self._select_dropdown_value('quality_dropdown', quality)
    
    def _read_price(self) -> int:
        """Чтение цены через OCR."""
        if self.config.price_region[2] > 0:
            return self.ocr.scan_digits(self.config.price_region)
        return 0
    
    def _open_item_menu(self, item_name: str) -> bool:
        """
        Открытие меню предмета.
        
        Returns:
            True если меню открыто
        """
        # 1. Очистка поиска
        self.smart.click_button('clear_button', timeout=1.5)
        time.sleep(self.config.delay_after_click)
        
        # 2. Ввод названия
        if not self.smart.type_in_search(item_name):
            return False
        
        time.sleep(self.config.delay_after_search)
        
        # 3. Клик "Купить" в списке
        if not self.smart.click_buy_in_list(row_index=0):
            return False
        
        time.sleep(self.config.delay_after_click)
        
        # 4. Раскрытие панели
        self._check_and_expand_panel()
        
        return True
    
    def scan_item_all_combinations(self, item_name: str) -> List[ScanResult]:
        """
        Сканирование предмета по всем комбинациям Тир/Энчант/Качество.
        
        Args:
            item_name: Название предмета
        
        Returns:
            Список результатов для всех комбинаций
        """
        results = []
        
        try:
            # Открытие меню предмета
            if not self._open_item_menu(item_name):
                result = ScanResult(
                    item_name=item_name,
                    city=self.config.current_city,
                    scan_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    error="Не удалось открыть меню предмета"
                )
                return [result]
            
            # Перебор комбинаций
            prev_tier = None
            prev_enchant = None
            
            for tier, enchant, quality in self._generate_combinations():
                self._wait_if_paused()
                
                if not self._running:
                    break
                
                result = ScanResult(
                    item_name=item_name,
                    tier=tier,
                    enchant=enchant,
                    quality=quality,
                    city=self.config.current_city,
                    scan_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                
                try:
                    # Выбор тира (только если изменился)
                    if tier != prev_tier:
                        # Передаём item_name для первого вызова, чтобы определить min_tier
                        self._select_tier(tier, item_name if prev_tier is None else None)
                        prev_tier = tier
                        # При смене тира сбрасываем enchant tracking
                        prev_enchant = None
                    
                    # Выбор энчанта (только если изменился)
                    if enchant != prev_enchant:
                        self._select_enchant(enchant)
                        prev_enchant = enchant
                    
                    # Выбор качества (всегда)
                    self._select_quality(quality)
                    
                    # Пауза для загрузки данных
                    time.sleep(self.config.delay_after_click)
                    
                    # Чтение цены
                    price = self._read_price()
                    result.price = price
                    result.success = True
                    
                    self._log_status(f"  T{tier}.{enchant} Q{quality}: {price:,}")
                    
                except Exception as e:
                    result.error = str(e)
                    logger.error(f"Error scanning {result.full_name}: {e}")
                
                results.append(result)
                
                if self.on_result:
                    self.on_result(result)
            
        finally:
            # Закрытие меню
            self._close_item_panel()
            time.sleep(self.config.delay_after_click)
        
        return results
    
    def run_full_scan(self, items: List[str] = None) -> List[ScanResult]:
        """
        Запуск полного сканирования всех предметов по всем комбинациям.
        
        Args:
            items: Список предметов (или загрузить из файла)
        
        Returns:
            Список всех результатов
        """
        if items is None:
            items = self.load_items()
        
        if not items:
            self._log_status("❌ Нет предметов для сканирования")
            return []
        
        self.results = []
        total_items = len(items)
        combos_per_item = self._count_combinations()
        total_combos = total_items * combos_per_item
        
        self._log_status(f"🔍 Сканирование: {total_items} предметов × {combos_per_item} комбинаций = {total_combos} записей")
        
        current_combo = 0
        
        for i, item_name in enumerate(items):
            self._wait_if_paused()
            
            if not self._running:
                self._log_status("⛔ Сканирование остановлено")
                break
            
            self._log_status(f"[{i+1}/{total_items}] {item_name}")
            
            # Сканирование всех комбинаций предмета
            item_results = self.scan_item_all_combinations(item_name)
            
            for result in item_results:
                current_combo += 1
                self.results.append(result)
                
                if self.on_progress:
                    self.on_progress(current_combo, total_combos, result.full_name)
            
            success_count = sum(1 for r in item_results if r.success)
            self._log_status(f"✅ {item_name}: {success_count}/{len(item_results)} комбинаций")
        
        self._log_status(f"📊 Завершено: {len(self.results)} записей")
        return self.results
    
    def save_results(self, filename: str = None) -> Path:
        """Сохранение результатов в CSV."""
        results_dir = Path(self.config.results_dir)
        results_dir.mkdir(exist_ok=True)
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"scan_{self.config.current_city}_{timestamp}.csv"
        
        filepath = results_dir / filename
        
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            # Header
            f.write("item_name,tier,enchant,quality,price,quantity,avg_price,scan_time,city,success,error\n")
            
            # Data
            for r in self.results:
                line = f'"{r.item_name}",{r.tier},{r.enchant},{r.quality},{r.price},{r.quantity},{r.avg_price},"{r.scan_time}","{r.city}",{r.success},"{r.error}"\n'
                f.write(line)
        
        logger.info(f"Results saved to {filepath}")
        return filepath

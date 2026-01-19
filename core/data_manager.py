"""
Albion Market Bot v3.0 - Data Manager

Модуль работы с данными: Excel, CSV, настройки.
"""

import csv
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

import pandas as pd

from config import (
    DATA_DIR, ITEMS_FILE, LEGACY_TABLE_FILE, 
    PURCHASE_LOG_FILE, LOGS_DIR
)

logger = logging.getLogger(__name__)


class DataManager:
    """Менеджер данных приложения."""
    
    def __init__(self):
        """Инициализация с проверкой путей."""
        DATA_DIR.mkdir(exist_ok=True)
        LOGS_DIR.mkdir(exist_ok=True)
    
    # === Таблица предметов ===
    
    def load_items(
        self,
        sort_by: str = "profit",
        ascending: bool = False,
        tier6_only: bool = False
    ) -> pd.DataFrame:
        """
        Загрузка таблицы предметов.
        
        Args:
            sort_by: Колонка для сортировки.
            ascending: Порядок сортировки.
            tier6_only: Только предметы 6 тира (с "мастер" в названии).
        
        Returns:
            DataFrame с предметами.
        """
        # Определяем файл
        if ITEMS_FILE.exists():
            file_path = ITEMS_FILE
        elif LEGACY_TABLE_FILE.exists():
            file_path = LEGACY_TABLE_FILE
        else:
            raise FileNotFoundError("Файл с предметами не найден")
        
        df = pd.read_excel(file_path, sheet_name=0, header=0)
        
        # Проверка обязательных колонок
        required_cols = ['name', 'value', 'store', 'present']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"Отсутствуют колонки: {missing}")
        
        # Фильтрация tier6
        if tier6_only:
            df = df[df['name'].str.contains('мастер', case=False, na=False)]
        
        # Сортировка
        if sort_by in df.columns:
            df = df.sort_values(by=sort_by, ascending=ascending)
        
        df = df.reset_index(drop=True)
        
        logger.info(f"Loaded {len(df)} items from {file_path}")
        return df
    
    def get_item_by_name(self, name: str) -> Optional[pd.Series]:
        """Поиск предмета по имени."""
        df = self.load_items()
        matches = df[df['name'].str.lower() == name.lower()]
        if not matches.empty:
            return matches.iloc[0]
        return None
    
    def search_items(self, query: str) -> pd.DataFrame:
        """
        Поиск предметов по части названия.
        
        Args:
            query: Поисковый запрос.
        
        Returns:
            DataFrame с найденными предметами.
        """
        df = self.load_items()
        if not query:
            return df
        
        mask = df['name'].str.contains(query, case=False, na=False)
        return df[mask].reset_index(drop=True)
    
    # === Лог покупок ===
    
    def log_purchase(
        self,
        item_name: str,
        quantity: int,
        price_per_unit: int,
        purchase_type: str = "manual"
    ) -> None:
        """
        Запись покупки в лог.
        
        Args:
            item_name: Название предмета.
            quantity: Количество.
            price_per_unit: Цена за единицу.
            purchase_type: Тип покупки ('manual', 'order').
        """
        file_exists = PURCHASE_LOG_FILE.exists()
        
        with open(PURCHASE_LOG_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['timestamp', 'item_name', 'quantity', 'price_per_unit', 'purchase_type'])
            
            writer.writerow([
                datetime.now().isoformat(),
                item_name,
                quantity,
                price_per_unit,
                purchase_type
            ])
        
        logger.info(f"Logged purchase: {item_name} x{quantity} @ {price_per_unit}")
    
    def load_purchase_log(self) -> pd.DataFrame:
        """Загрузка лога покупок."""
        if not PURCHASE_LOG_FILE.exists():
            return pd.DataFrame(columns=['timestamp', 'item_name', 'quantity', 'price_per_unit', 'purchase_type'])
        
        return pd.read_csv(PURCHASE_LOG_FILE)
    
    def get_item_costs(self) -> pd.DataFrame:
        """
        Получение средневзвешенных цен по предметам.
        
        Returns:
            DataFrame с колонками: item_name, total_quantity, total_cost, wapp
        """
        df = self.load_purchase_log()
        if df.empty:
            return pd.DataFrame(columns=['item_name', 'total_quantity', 'total_cost', 'wapp'])
        
        df['total_cost'] = df['quantity'] * df['price_per_unit']
        
        grouped = df.groupby('item_name').agg(
            total_quantity=('quantity', 'sum'),
            total_cost=('total_cost', 'sum')
        ).reset_index()
        
        grouped['wapp'] = grouped['total_cost'] / grouped['total_quantity']
        
        return grouped
    
    def get_wapp_for_item(self, item_name: str) -> float:
        """Получение WAPP для конкретного предмета."""
        costs = self.get_item_costs()
        match = costs[costs['item_name'].str.lower() == item_name.lower()]
        if not match.empty:
            return match.iloc[0]['wapp']
        return 0.0
    
    # === Логирование сессий ===
    
    def save_session_log(
        self,
        entries: List[str],
        session_type: str = "manual"
    ) -> Path:
        """
        Сохранение лога сессии.
        
        Args:
            entries: Список записей лога.
            session_type: Тип сессии ('manual', 'order', 'sell').
        
        Returns:
            Путь к сохранённому файлу.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"progress_log_{session_type}_{timestamp}.txt"
        log_path = LOGS_DIR / filename
        
        with open(log_path, 'w', encoding='utf-8') as f:
            for entry in entries:
                f.write(entry + '\n')
        
        logger.info(f"Session log saved: {log_path}")
        return log_path
    
    def save_sell_report(
        self,
        sold_items: List[Dict[str, Any]],
        total_income: float,
        total_spent: float,
        entries: List[str]
    ) -> Path:
        """
        Сохранение отчёта о продажах.
        
        Args:
            sold_items: Список проданных предметов.
            total_income: Общий доход.
            total_spent: Общий расход.
            entries: Записи лога.
        
        Returns:
            Путь к отчёту.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sell_report_{timestamp}.txt"
        report_path = LOGS_DIR / filename
        
        final_profit = total_income - total_spent
        
        lines = [
            "--- Итог сессии ---",
            f"Общий доход: {total_income:,.2f}",
            f"Общий расход: {total_spent:,.2f}",
            f"Чистая прибыль: {final_profit:,.2f}",
            "",
            "--- Детализация продаж ---"
        ]
        
        for item in sold_items:
            lines.append(
                f"{item['name']} x{item['quantity']} | "
                f"Продано за: {item.get('sale_price_total', 0):,.2f} | "
                f"Расход: {item.get('cost_for_stack', 0):,.2f} | "
                f"Прибыль за шт: {item.get('profit_per_item', 0):,.2f}"
            )
        
        lines.extend(["", "--- Полный лог сессии ---"])
        lines.extend(entries)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        logger.info(f"Sell report saved: {report_path}")
        return report_path


# Глобальный экземпляр
_manager: Optional[DataManager] = None


def get_data_manager() -> DataManager:
    """Получение глобального менеджера данных."""
    global _manager
    if _manager is None:
        _manager = DataManager()
    return _manager

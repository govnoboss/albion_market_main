"""
Albion Market Bot v3.0 - Price Calculator

Модуль расчёта цен, прибыли и лимитов закупки.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PriceInfo:
    """Информация о ценах и прибыли предмета."""
    name: str
    buy_price: int  # Цена закупки
    sell_price: int  # Цена продажи в другом городе
    limit_price: int  # Максимальная выгодная цена
    profit_per_unit: float  # Прибыль за единицу
    total_profit: float  # Общая прибыль
    quantity: int  # Количество для закупки
    
    @property
    def profit_margin(self) -> float:
        """Маржа прибыли в процентах."""
        if self.buy_price <= 0:
            return 0
        return ((self.sell_price - self.buy_price) / self.buy_price) * 100


# Константы
TAX_RATE = 0.105  # Налог рынка (10.5%)
DEFAULT_TRANSPORT_COST_PER_KG = 350  # Стоимость перевозки за кг


def calculate_limit_price(
    sell_price: int,
    present_ratio: float,
    weight_per_item: float = 0.0,
    transport_cost_per_kg: int = DEFAULT_TRANSPORT_COST_PER_KG
) -> int:
    """
    Расчёт максимальной выгодной цены закупки.
    
    Args:
        sell_price: Цена продажи в целевом городе.
        present_ratio: Коэффициент присутствия (0.0 - 1.0).
        weight_per_item: Вес одного предмета (кг).
        transport_cost_per_kg: Стоимость перевозки за кг.
    
    Returns:
        Максимальная цена закупки, при которой сделка выгодна.
    
    Formula:
        limit_price = (sell_price * present_ratio) - (weight * transport_cost)
    """
    if sell_price <= 0 or present_ratio <= 0:
        return 0
    
    transport_cost = weight_per_item * transport_cost_per_kg
    limit_price = int((sell_price * present_ratio) - transport_cost)
    
    return max(0, limit_price)


def calculate_profit(
    buy_price: int,
    sell_price: int,
    quantity: int = 1,
    tax_rate: float = TAX_RATE
) -> float:
    """
    Расчёт прибыли с учётом налога.
    
    Args:
        buy_price: Цена закупки.
        sell_price: Цена продажи.
        quantity: Количество предметов.
        tax_rate: Налог рынка (по умолчанию 10.5%).
    
    Returns:
        Чистая прибыль.
    """
    if buy_price <= 0 or sell_price <= 0:
        return 0.0
    
    gross_income = sell_price * (1 - tax_rate)
    net_profit_per_unit = gross_income - buy_price
    
    return net_profit_per_unit * quantity


def calculate_wapp(
    purchases: list[tuple[int, int]]
) -> float:
    """
    Расчёт средневзвешенной цены закупки (WAPP).
    
    Args:
        purchases: Список покупок [(quantity, price_per_unit), ...]
    
    Returns:
        Средневзвешенная цена.
    """
    if not purchases:
        return 0.0
    
    total_cost = sum(qty * price for qty, price in purchases)
    total_quantity = sum(qty for qty, _ in purchases)
    
    if total_quantity <= 0:
        return 0.0
    
    return total_cost / total_quantity


def is_profitable(
    buy_price: int,
    limit_price: int
) -> bool:
    """
    Проверка выгодности сделки.
    
    Args:
        buy_price: Предлагаемая цена закупки.
        limit_price: Максимальная выгодная цена.
    
    Returns:
        True если сделка выгодна.
    """
    return buy_price <= limit_price and limit_price > 0


def calculate_batch_cost(
    price_per_unit: int,
    quantity: int,
    current_spent: int,
    budget: int
) -> tuple[int, int]:
    """
    Расчёт стоимости партии с учётом бюджета.
    
    Args:
        price_per_unit: Цена за единицу.
        quantity: Желаемое количество.
        current_spent: Уже потраченная сумма.
        budget: Общий бюджет.
    
    Returns:
        (фактическое количество, стоимость партии)
    """
    available_budget = budget - current_spent
    
    if available_budget <= 0:
        return (0, 0)
    
    max_affordable = available_budget // price_per_unit
    actual_quantity = min(quantity, max_affordable)
    batch_cost = actual_quantity * price_per_unit
    
    return (actual_quantity, batch_cost)


def analyze_item(
    name: str,
    sell_price: int,
    present_ratio: float,
    weight_per_item: float,
    store_quantity: int,
    current_price: Optional[int] = None
) -> PriceInfo:
    """
    Полный анализ предмета для закупки.
    
    Args:
        name: Название предмета.
        sell_price: Цена продажи.
        present_ratio: Коэффициент присутствия.
        weight_per_item: Вес за единицу.
        store_quantity: Желаемое количество для закупки.
        current_price: Текущая цена на рынке (если известна).
    
    Returns:
        PriceInfo с полным анализом.
    """
    limit_price = calculate_limit_price(
        sell_price, present_ratio, weight_per_item
    )
    
    buy_price = current_price if current_price else limit_price
    
    profit_per_unit = calculate_profit(buy_price, sell_price, 1)
    total_profit = profit_per_unit * store_quantity
    
    return PriceInfo(
        name=name,
        buy_price=buy_price,
        sell_price=sell_price,
        limit_price=limit_price,
        profit_per_unit=profit_per_unit,
        total_profit=total_profit,
        quantity=store_quantity
    )

"""
Генератор демо-данных для Dashboard.
Создает случайные сессии закупки за последние 24 часа.

Использование:
    python tools/generate_demo_sessions.py [--sessions N] [--clear]

Параметры:
    --sessions N   Количество сессий (по умолчанию 8)
    --clear        Очистить все данные перед генерацией
"""

import sqlite3
import random
import uuid
import argparse
import time
from datetime import datetime, timedelta
from pathlib import Path

# ── Путь к БД (такой же как в finance.py) ──
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "finance.db"

# ── Города Albion Online ──
CITIES = [
    "Bridgewatch", "Fort Sterling",
    "Lymhurst", "Martlock", "Thetford"
]

# ── Реалистичные предметы Albion ──
ITEMS = [
    # Оружие
    ("Claymore", 4, 0),
    ("Claymore", 5, 1),
    ("Broadsword", 5, 0),
    ("Greataxe", 6, 1),
    ("Halberd", 5, 2),
    ("Longbow", 5, 1),
    ("Warbow", 6, 0),
    ("Crossbow", 4, 1),
    ("Fire Staff", 5, 0),
    ("Great Fire Staff", 6, 1),
    ("Frost Staff", 5, 2),
    ("Cursed Staff", 5, 0),
    ("Great Holy Staff", 6, 1),
    ("Arcane Staff", 5, 0),
    ("Spear", 4, 0),
    ("Pike", 5, 1),
    ("Glaive", 6, 2),
    ("Quarterstaff", 5, 0),
    ("Black Monk Stave", 6, 1),
    ("Dagger", 4, 0),
    ("Dagger Pair", 5, 1),
    ("Bloodletter", 6, 0),
    ("Mace", 5, 0),
    ("Heavy Mace", 6, 1),
    ("Hammer", 5, 2),
    # Броня
    ("Soldier Helmet", 5, 0),
    ("Knight Helmet", 6, 1),
    ("Guardian Helmet", 5, 0),
    ("Soldier Armor", 5, 1),
    ("Knight Armor", 6, 0),
    ("Guardian Armor", 5, 2),
    ("Soldier Boots", 5, 0),
    ("Knight Boots", 6, 1),
    ("Mage Robe", 5, 0),
    ("Cleric Robe", 6, 1),
    ("Assassin Jacket", 5, 0),
    ("Mercenary Jacket", 6, 0),
    ("Hunter Hood", 5, 1),
    ("Stalker Hood", 6, 0),
    # Ресурсы / крафт
    ("Royal Sigil", 5, 0),
    ("Tome of Insight", 4, 0),
    ("Cape of Storms", 5, 0),
    ("Undead Cape", 6, 0),
    ("Demon Cape", 7, 0),
    ("Martlock Cape", 5, 0),
    ("Fort Sterling Cape", 5, 0),
]


def init_db():
    """Создаёт таблицу и колонку session_id, если их нет."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            item_name TEXT,
            tier INTEGER,
            enchant INTEGER,
            price INTEGER,
            qty INTEGER,
            total INTEGER,
            city TEXT,
            profit_est INTEGER,
            is_simulation BOOLEAN
        )
    ''')
    # Миграция session_id
    c.execute("PRAGMA table_info(transactions)")
    columns = [row[1] for row in c.fetchall()]
    if "session_id" not in columns:
        c.execute("ALTER TABLE transactions ADD COLUMN session_id TEXT")
    conn.commit()
    conn.close()


def generate_sessions(num_sessions: int = 8):
    """
    Генерирует демо-сессии.

    Каждая сессия:
      - В пределах последних 24 часов
      - Общие затраты: 100-300 млн серебра
      - Цена предмета: 4 000 - 100 000
      - Профит: 20-30% от затрат
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    now = datetime.now()
    total_generated = 0

    # Равномерно распределяем сессии по 24-часовому окну
    interval = 48 * 3600 / (num_sessions + 1)  # секунды между сессиями

    for s in range(num_sessions):
        session_id = str(uuid.uuid4())[:8]
        city = random.choice(CITIES)

        # Время старта сессии (смещение от now, равномерно)
        offset_sec = int(interval * (num_sessions - s))
        session_start = now - timedelta(seconds=offset_sec)

        # Бюджет сессии: 100-300 млн
        budget = random.randint(100_000_000, 300_000_000)

        # Процент профита для этой сессии: 20-30%
        profit_pct = random.uniform(0.20, 0.30)

        # Генерируем транзакции, пока не заполним бюджет
        spent = 0
        items_in_session = 0
        # Выбираем 5-15 уникальных предметов для этой сессии
        session_items = random.sample(ITEMS, k=min(random.randint(5, 15), len(ITEMS)))

        while spent < budget:
            item_name, tier, enchant = random.choice(session_items)

            # Цена предмета: 4 000 - 100 000
            price = random.randint(4_000, 100_000)

            # Количество: от 1 до разумного числа (чтобы не превысить бюджет)
            remaining = budget - spent
            max_qty_by_budget = max(1, remaining // price)
            qty = random.randint(1, min(max_qty_by_budget, random.randint(5, 50)))

            total = price * qty

            # Не превышаем бюджет
            if spent + total > budget * 1.05:
                # Корректируем qty
                qty = max(1, remaining // price)
                total = price * qty
                if total == 0:
                    break

            # Профит для этой транзакции (в среднем ~profit_pct)
            item_profit_pct = random.uniform(profit_pct - 0.05, profit_pct + 0.05)
            item_profit_pct = max(0.05, item_profit_pct)  # минимум 5%
            profit_est = int(total * item_profit_pct)

            # Timestamp — внутри сессии (сессия длится 5-30 мин)
            session_duration = random.randint(300, 1800)  # 5-30 мин
            tx_offset = random.randint(0, session_duration)
            timestamp = (session_start + timedelta(seconds=tx_offset)).strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute('''
                INSERT INTO transactions 
                (timestamp, item_name, tier, enchant, price, qty, total, city, profit_est, is_simulation, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            ''', (timestamp, item_name, tier, enchant, price, qty, total, city, profit_est, session_id))

            spent += total
            items_in_session += 1
            total_generated += 1

        session_profit = int(spent * profit_pct)
        print(
            f"  ✅ Сессия {s + 1}/{num_sessions}  |  "
            f"{city:<16}  |  "
            f"{items_in_session:>4} предметов  |  "
            f"Затраты: {spent:>14,} с.  |  "
            f"Профит ~{profit_pct:.0%}: {session_profit:>12,} с."
        )

    conn.commit()
    conn.close()

    print(f"\n{'─' * 70}")
    print(f"  Готово! Создано {num_sessions} сессий, {total_generated} транзакций.")
    print(f"  БД: {DB_PATH}")
    print(f"{'─' * 70}")


def clear_data():
    """Удалить все транзакции из БД."""
    if not DB_PATH.exists():
        print("  ⚠  БД не найдена, нечего чистить.")
        return
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM transactions")
    conn.commit()
    conn.close()
    print("  🗑  Все транзакции удалены.")


def main():
    parser = argparse.ArgumentParser(
        description="Генератор демо-данных для Dashboard"
    )
    parser.add_argument(
        "--sessions", "-s", type=int, default=8,
        help="Количество сессий (по умолчанию 8)"
    )
    parser.add_argument(
        "--clear", "-c", action="store_true",
        help="Очистить все данные перед генерацией"
    )
    args = parser.parse_args()

    print(f"\n{'═' * 70}")
    print(f"  🎲  Генератор демо-сессий для Dashboard")
    print(f"{'═' * 70}\n")

    if args.clear:
        clear_data()
        print()

    generate_sessions(args.sessions)


if __name__ == "__main__":
    main()

import sqlite3
import os
from datetime import datetime

class MarketDB:
    def __init__(self, db_path="sniffer/market_data.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Инициализация таблиц базы данных."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица активных ордеров (лотов)
            # Мы используем OrderId как первичный ключ для автоматической дедупликации (через INSERT OR IGNORE)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_orders (
                    order_id INTEGER PRIMARY KEY,
                    item_id TEXT,
                    price REAL,
                    amount INTEGER,
                    quality INTEGER,
                    enchantment INTEGER,
                    auction_type TEXT,
                    expires TEXT,
                    timestamp TEXT
                )
            ''')
            
            # Таблица истории цен (графиков)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id TEXT,
                    price REAL,
                    timestamp TEXT
                )
            ''')
            
            # Таблица цен на золото
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS gold_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    buy_price REAL,
                    sell_price REAL,
                    volume INTEGER,
                    timestamp TEXT
                )
            ''')
            
            conn.commit()

    def save_orders(self, orders):
        """Сохраняет список ордеров в базу."""
        if not orders:
            return
            
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for o in orders:
                cursor.execute('''
                    INSERT OR IGNORE INTO market_orders 
                    (order_id, item_id, price, amount, quality, enchantment, auction_type, expires, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    o.get("Id"),
                    o.get("ItemTypeId"),
                    o.get("UnitPriceSilver"),
                    o.get("Amount"),
                    o.get("QualityLevel"),
                    o.get("EnchantmentLevel"),
                    o.get("AuctionType"),
                    o.get("Expires"),
                    now
                ))
            conn.commit()

    def save_history(self, item_id, history_data):
        """Сохраняет точки из графика цен."""
        if not history_data:
            return
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for entry in history_data:
                cursor.execute('''
                    INSERT INTO market_history (item_id, price, timestamp)
                    VALUES (?, ?, ?)
                ''', (item_id, entry["price"], entry["timestamp"]))
            conn.commit()

    def save_gold(self, gold_data):
        """Сохраняет текущие цены на золото."""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO gold_prices (buy_price, sell_price, volume, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (
                gold_data["buy_price"],
                gold_data["sell_price"],
                gold_data["volume"],
                now
            ))
            conn.commit()

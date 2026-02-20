"""
Менеджер финансов
Управление базой данных транзакций и статистикой.
"""

import sqlite3
import os
import time
from datetime import datetime
from pathlib import Path
from ..utils.paths import get_app_root
from ..utils.logger import get_logger

logger = get_logger()

class FinanceManager:
    def __init__(self):
        self.db_path = get_app_root() / "data" / "finance.db"
        self._init_db()

    def _init_db(self):
        """Инициализация базы данных SQLite"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Таблица транзакций
            cursor.execute('''
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
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Ошибка инициализации БД финансов: {e}")

    def log_transaction(self, item_name, tier, enchant, price, qty, city, profit_est=0, is_simulation=False):
        """Запись новой транзакции"""
        try:
            total = price * qty
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO transactions 
                (item_name, tier, enchant, price, qty, total, city, profit_est, is_simulation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (item_name, tier, enchant, price, qty, total, city, profit_est, is_simulation))
            
            conn.commit()
            conn.close()
            # logger.info(f"💰 Транзакция сохранена: {item_name} x{qty} ({total} s.)")
        except Exception as e:
            logger.error(f"Ошибка записи транзакции: {e}")

    def get_stats_for_period(self, days=None):
        """Получение статистики за период (в днях). Если days=None - за всё время."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if days is not None:
                # В расчетах Albion Market Bot мы учитываем последние N суток (24h * N)
                period_start = datetime.fromtimestamp(time.time() - (days * 86400)).strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute('''
                    SELECT SUM(total), SUM(qty), SUM(profit_est) 
                    FROM transactions 
                    WHERE timestamp >= ? AND is_simulation = 0
                ''', (period_start,))
            else:
                cursor.execute('''
                    SELECT SUM(total), SUM(qty), SUM(profit_est) 
                    FROM transactions 
                    WHERE is_simulation = 0
                ''')
                
            spent, qty, profit = cursor.fetchone()
            conn.close()
            
            return {
                "spent": spent or 0,
                "qty": qty or 0,
                "profit": profit or 0
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики за период: {e}")
            return {"spent": 0, "qty": 0, "profit": 0}

    def get_history_for_period(self, days=None, limit=100):
        """Получение списка транзакций за период"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if days is not None:
                period_start = datetime.fromtimestamp(time.time() - (days * 86400)).strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute('''
                    SELECT * FROM transactions 
                    WHERE timestamp >= ? AND is_simulation = 0
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (period_start, limit))
            else:
                cursor.execute('''
                    SELECT * FROM transactions 
                    WHERE is_simulation = 0
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))
                
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка получения истории за период: {e}")
            return []

    def get_hot_items_for_period(self, days=None, limit=5):
        """Получение топа предметов по количеству за период"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            where_clause = "WHERE is_simulation = 0"
            params = [limit]
            
            if days is not None:
                period_start = datetime.fromtimestamp(time.time() - (days * 86400)).strftime("%Y-%m-%d %H:%M:%S")
                where_clause += " AND timestamp >= ?"
                params = [period_start, limit]
            
            query = f'''
                SELECT item_name, tier, enchant, SUM(qty) as total_qty, SUM(profit_est) as total_profit
                FROM transactions 
                {where_clause}
                GROUP BY item_name, tier, enchant
                ORDER BY total_qty DESC
                LIMIT ?
            '''
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка получения горячих предметов: {e}")
            return []

    def get_stats_summary(self):
        """Получение сводной статистики (Сегодня / Всего)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            today_start = datetime.now().strftime("%Y-%m-%d 00:00:00")
            
            # Сегодня
            cursor.execute('''
                SELECT SUM(total), SUM(qty), SUM(profit_est) 
                FROM transactions 
                WHERE timestamp >= ? AND is_simulation = 0
            ''', (today_start,))
            today_spent, today_qty, today_profit = cursor.fetchone()
            
            # Всего
            cursor.execute('''
                SELECT SUM(total), SUM(qty), SUM(profit_est) 
                FROM transactions 
                WHERE is_simulation = 0
            ''')
            total_spent, total_qty, total_profit = cursor.fetchone()
            
            conn.close()
            
            return {
                "today_spent": today_spent or 0,
                "today_qty": today_qty or 0,
                "today_profit": today_profit or 0,
                "total_spent": total_spent or 0,
                "total_qty": total_qty or 0,
                "total_profit": total_profit or 0
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return None

    def get_recent_history(self, limit=50):
        """Последние транзакции"""
        try:
            conn = sqlite3.connect(self.db_path)
            # Чтобы получать словари
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM transactions 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка получения истории: {e}")
            return []

    def delete_transaction(self, tx_id):
        """Удаление транзакции"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM transactions WHERE id = ?', (tx_id,))
            conn.commit()
            conn.close()
            logger.info(f"🗑️ Транзакция {tx_id} удалена")
        except Exception as e:
            logger.error(f"Ошибка удаления транзакции: {e}")

    def update_transaction(self, tx_id, new_price, new_qty):
        """Обновление цены и количества транзакции с пересчетом профита"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Получаем старые данные для расчета bm_price
            cursor.execute('SELECT price, qty, profit_est FROM transactions WHERE id = ?', (tx_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return

            old_price = row['price']
            old_qty = row['qty']
            old_profit = row['profit_est']
            
            # Реверс-инжиниринг bm_price (ожидаемой цены продажи)
            # Profit = (bm_price * 0.935 - purchase_price) * qty
            # bm_price = ((profit / qty) + purchase_price) / 0.935
            if old_qty > 0:
                approx_bm_price = ((old_profit / old_qty) + old_price) / 0.935
                new_profit = int((approx_bm_price * 0.935 - new_price) * new_qty)
            else:
                new_profit = 0
                
            new_total = new_price * new_qty
            
            cursor.execute('''
                UPDATE transactions 
                SET price = ?, qty = ?, total = ?, profit_est = ? 
                WHERE id = ?
            ''', (new_price, new_qty, new_total, new_profit, tx_id))
            
            conn.commit()
            conn.close()
            logger.info(f"📝 Транзакция {tx_id} обновлена: {new_price} x {new_qty}")
        except Exception as e:
            logger.error(f"Ошибка обновления транзакции: {e}")

    def clear_history(self):
        """Полная очистка (для теста или сброса)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM transactions')
            conn.commit()
            conn.close()
            logger.warning("🧹 История финансов очищена")
        except Exception as e:
            logger.error(f"Ошибка очистки истории: {e}")

# Синглтон
finance_manager = FinanceManager()

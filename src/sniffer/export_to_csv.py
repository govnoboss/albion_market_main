import sqlite3
import csv
import os

def export_table(table_name, csv_path):
    db_path = "sniffer/market_data.db"
    if not os.path.exists(db_path):
        print("База данных не найдена!")
        return

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            if not rows:
                print(f"Таблица {table_name} пуста.")
                return

            colnames = [description[0] for description in cursor.description]
            
            with open(csv_path, "w", newline='', encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(colnames)
                writer.writerows(rows)
                
            print(f"[OK] Данные из {table_name} экспортированы в {csv_path}")
    except Exception as e:
        print(f"[!] Ошибка при экспорте {table_name}: {e}")

if __name__ == "__main__":
    os.makedirs("exports", exist_ok=True)
    export_table("market_orders", "exports/market_orders.csv")
    export_table("market_history", "exports/market_history.csv")
    export_table("gold_prices", "exports/gold_prices.csv")

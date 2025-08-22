import requests
import pandas as pd
from pathlib import Path

# путь куда сохраняем Excel
local_file = Path("table.xlsx")

# ссылка на экспорт в Excel (.xlsx)
url = "https://docs.google.com/spreadsheets/d/1D5MmKgJUaV00Owa3ILBiIg-2Jpu4ZezTkYuP1pJrSWM/export?format=xlsx&id=1D5MmKgJUaV00Owa3ILBiIg-2Jpu4ZezTkYuP1pJrSWM&gid=0"

def update_table():
    # скачиваем
    response = requests.get(url)
    response.raise_for_status()

    # сохраняем/заменяем старый Excel
    with open(local_file, "wb") as f:
        f.write(response.content)

    print("Excel таблица обновлена:", local_file)

def load_table():
    # читаем через pandas
    df = pd.read_excel(local_file, engine="openpyxl")
    return df

# пример использования
update_table()
df = load_table()
print(df.head())

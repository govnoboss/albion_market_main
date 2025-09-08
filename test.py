import pandas as pd
import numpy as np

# Загружаем Excel файл
df = pd.read_excel('table.xlsx')

# Выбираем нужные колонки
columns = ['name', 'valuefromcity', 'value', 'profit', 'store']
df_selected = df[columns]

# Создаем маску для строк, где valuefromcity или value равны 0 или NaN
invalid_mask = (df_selected['valuefromcity'].isna() | (df_selected['valuefromcity'] == 0) |
                df_selected['value'].isna() | (df_selected['value'] == 0))

# Разделяем на валидные и невалидные строки
df_valid = df_selected[~invalid_mask]
df_invalid = df_selected[invalid_mask]

# Сортируем валидные строки по профиту в descending порядке
df_sorted = df_valid.sort_values(by='profit', ascending=False)

# Объединяем отсортированные валидные строки с невалидными (в конец)
df_final = pd.concat([df_sorted, df_invalid])

# Записываем в log.txt
with open('log.txt', 'w', encoding='utf-8') as f:
    for index, row in df_final.iterrows():
        f.write(f"Название - {row['name']}, Цена закупки - {row['valuefromcity']}, Цена продажи - {row['value']}, Полученный профит = {row['profit']} | Закупаем в среднем - {row['store']}\n")

print("Данные успешно записаны в log.txt")
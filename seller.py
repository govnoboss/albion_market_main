import pyautogui
import pytesseract
import pandas as pd
import time
import logging
import random
from datetime import datetime
from pathlib import Path
from PIL import ImageGrab
import csv
def ocr_scan_text(region):
    """Сканирует текст в указанной области."""
    try:
        x, y, w, h = region
        screenshot = ImageGrab.grab(bbox=(x, y, x + w, y + h))
        screenshot.save("screenshot.png")
        whitelist = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя() -"

        custom_config = (
            f'-c tessedit_char_whitelist={whitelist} --psm 6'
        )
        text = pytesseract.image_to_string(screenshot, lang='rus+eng').strip()
        return text.lower()
    except Exception as e:
        logging.error(f"Ошибка OCR текста: {e}")
        return ""

def ocr_scan_digits(region):
    """Сканирует только цифры в указанной области."""
    try:
        x, y, w, h = region
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        screenshot = ImageGrab.grab(bbox=(x, y, x + w, y + h))
        text = pytesseract.image_to_string(screenshot, config='--psm 7 -c tessedit_char_whitelist=0123456789')
        return int(text.strip()) if text.strip() else 0
    except Exception as e:
        logging.error(f"Ошибка OCR цифр: {e}")
        return 0

def click_with_scatter(x, y, scatter=5):

    # Generate random offset within ±scatter
    x_offset = random.randint(-scatter, scatter)
    y_offset = random.randint(-scatter, scatter)
    
    # Calculate final coordinates
    final_x = x + x_offset
    final_y = y + y_offset
    
    # Perform the click
    pyautogui.click(final_x, final_y)
    print(f"Clicked at ({final_x}, {final_y}) with offset ({x_offset}, {y_offset})")

def run_selling_cycle(coords, regions, gui_callback): # <<< ИЗМЕНЕНИЕ: убрали total_spent из аргументов
    """
    Основной цикл продажи предметов с автоматическим расчетом расходов.
    """
    log_entries = []

    def log_and_update(message):
        """Локальная функция для логирования и обновления GUI."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        full_message = f"[{timestamp}] {message}"
        log_entries.append(full_message)
        logging.info(message)
        gui_callback('update_status', message)
        print(full_message)

    log_and_update("=== Начинается сессия продаж ===")

    # --- Шаг 1: Загрузка и обработка журналов ---
    # (Этот блок остается без изменений, он уже правильно готовит данные)
    purchase_log_path = Path(__file__).parent / 'purchase_log.csv'
    log_and_update(f"[DEBUG] Проверка существования purchase_log.csv по пути {purchase_log_path}")
    if not purchase_log_path.exists():
        try:
            with open(purchase_log_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['item_name', 'quantity', 'price_per_unit', 'purchase_type'])
            log_and_update("[DEBUG] Файл purchase_log.csv не найден, создан новый с заголовками.")
        except Exception as e:
            log_and_update(f"[ERROR] Ошибка при создании purchase_log.csv: {e}")
            return False, f"Не удалось создать purchase_log.csv: {e}"

    try:
        required_cols = {'item_name', 'quantity', 'price_per_unit'}
        purchases_df = pd.read_csv(purchase_log_path)
        log_and_update(f"[DEBUG] Загружено {len(purchases_df)} строк из purchase_log.csv")
        missing = required_cols - set(purchases_df.columns)
        if missing:
            log_and_update(f"[ERROR] В purchase_log.csv не хватает колонок: {missing}")
            raise ValueError(f"В purchase_log.csv не хватает колонок: {missing}")

        purchases_df['total_cost'] = purchases_df['quantity'] * purchases_df['price_per_unit']
        item_costs = purchases_df.groupby('item_name').agg(
            total_quantity=('quantity', 'sum'),
            total_cost=('total_cost', 'sum')
        ).reset_index()
        item_costs['wapp'] = item_costs['total_cost'] / item_costs['total_quantity']
        log_and_update(f"[DEBUG] Журнал покупок успешно обработан, {len(item_costs)} уникальных предметов")
    except Exception as e:
        log_and_update(f"[ERROR] Ошибка при чтении или обработке purchase_log.csv: {e}")
        return False, f"Ошибка чтения purchase_log.csv: {e}"

    try:
        items_table_df = pd.read_excel(Path(__file__).parent / 'table.xlsx')
        log_and_update(f"[DEBUG] Загружено {len(items_table_df)} строк из table.xlsx")
        log_and_update(f"[DEBUG] Колонки table.xlsx: {items_table_df.columns.tolist()}")
    except Exception as e:
        log_and_update(f"[ERROR] Ошибка при чтении table.xlsx: {e}")
        return False, f"Ошибка чтения table.xlsx: {e}"

    total_income = 0
    calculated_total_spent = 0  
    sold_items_details = []
    failure_counter = 0

    while failure_counter < 5:
        if not gui_callback('is_running'):
            log_and_update("[DEBUG] Продажа прервана пользователем")
            return False, "Продажа прервана пользователем"
        gui_callback('pause_event_wait')

        item_name = ocr_scan_text(regions['item_name'])
        log_and_update(f"[DEBUG] OCR распознал предмет: '{item_name}'")

        row_purchase = item_costs[item_costs['item_name'] == item_name]
        row_table = items_table_df[items_table_df['name'] == item_name]
        log_and_update(f"[DEBUG] Найдено {len(row_purchase)} в purchase_log, {len(row_table)} в table.xlsx")

        wapp = 0 # Инициализируем себестоимость
        try:
            if not row_purchase.empty:
                failure_counter = 0
                item_data = row_purchase.iloc[0]
                wapp = item_data['wapp']
                log_and_update(f"[DEBUG] Себестоимость (WAPP) для {item_name}: {wapp:.2f}")

            elif not row_table.empty:
                failure_counter = 0
                log_and_update(f"[DEBUG] {item_name} не найден в purchase_log, используем table.xlsx")
                wapp = row_table['value'].iloc[0] if 'value' in row_table.columns else 0
                log_and_update(f"[DEBUG] Себестоимость (из table.xlsx) для {item_name}: {wapp:.2f}")
            else:
                failure_counter += 1
                log_and_update(f"[DEBUG] {item_name} отсутствует и в purchase_log, и в table.xlsx, попытка {failure_counter}")
                time.sleep(1)
                continue
        except Exception as e:
            log_and_update(f"[ERROR] Ошибка при извлечении данных для {item_name}: {type(e).__name__} -> {e}")
            failure_counter += 1
            continue

        # (Блок кликов остается без изменений)
        try:
            log_and_update(f"[DEBUG] Кликаем sell_button для {item_name}")
            click_with_scatter(*coords['sell_button'], scatter=5)
            time.sleep(0.2)
            
            click_with_scatter(*coords['minus_button'], scatter=5)
            log_and_update(f"[DEBUG] Кликаем minus_button для {item_name}")
            time.sleep(0.2)
        except Exception as e:
            log_and_update(f"[ERROR] Ошибка клика кнопок: {e}")

        # (Блок OCR цены продажи остается без изменений)
        try:
            sale_price = ocr_scan_digits(regions['sale_price'])
            log_and_update(f"[DEBUG] Распознана цена продажи: {sale_price}")
            price_per_item = ocr_scan_digits(regions['buy_price'])
            log_and_update(f"[DEBUG] Распознана цена продажи за предмет: {price_per_item-1}")
        except Exception as e:
            log_and_update(f"[ERROR] Ошибка OCR цены продажи: {e}")
            sale_price = 0

        if sale_price > 0 and wapp > 0: # Добавили проверку, что себестоимость найдена
            try:
                total_income += sale_price
                tax = 0.105
                
                # Расчет количества и прибыли
                quantity_in_stack = int(round(sale_price / ((price_per_item-1) * (1 - tax)))) if price_per_item > 1 else 0
                log_and_update(f"[DEBUG] Количество предметов в стеке: {quantity_in_stack}")
                
                profit_per_item = (price_per_item-1) * (1 - tax) - wapp if price_per_item > 1 else 0
                log_and_update(f"[DEBUG] Профит за 1 предмет: {profit_per_item:.2f}")

                # <<< ИЗМЕНЕНИЕ: Расчет и накопление расходов
                cost_for_this_stack = quantity_in_stack * wapp
                calculated_total_spent += cost_for_this_stack
                log_and_update(f"[DEBUG] Расход на этот стак ({quantity_in_stack} * {wapp:.2f}): {cost_for_this_stack:.2f}")
                log_and_update(f"[INFO] Общий расход сессии: {calculated_total_spent:.2f}")

                click_with_scatter(*coords['confirm_button'], scatter=5)
                log_and_update(f"[DEBUG] Кликаем confirm_button для {item_name}")
                sold_items_details.append({
                    'name': item_name,
                    'quantity': quantity_in_stack,
                    'sale_price_total': sale_price,
                    'profit_per_item': profit_per_item,
                    'cost_for_stack': cost_for_this_stack # Можно добавить для детального отчета
                })
                log_and_update(f"[DEBUG] Продажа подтверждена: общий доход={total_income:.2f}")

            except Exception as e:
                log_and_update(f"[ERROR] Ошибка при подтверждении продажи: {e}")
        else:
            log_and_update(f"[DEBUG] Цена продажи не распознана или не найдена себестоимость, пропуск предмета {item_name}")
            time.sleep(0.2)

        log_and_update(f"[DEBUG] Итерация завершена, failure_counter={failure_counter}")
        time.sleep(0.2)

    # --- Формирование отчета ---
    # <<< ИЗМЕНЕНИЕ: Используем calculated_total_spent для итоговых расчетов
    final_profit = total_income - calculated_total_spent
    report_lines = [
        f"--- Итог сессии ---",
        f"Общий доход: {total_income:,.2f}",
        f"Общий расход: {calculated_total_spent:,.2f}",
        f"Чистая прибыль: {final_profit:,.2f}"
    ]
    report_lines.append("\n--- Детализация продаж ---")
    for item in sold_items_details:
        report_lines.append(
            f"{item['name']} x{item['quantity']} | "
            f"Продано за: {item['sale_price_total']:,.2f} | "
            f"Расход: {item['cost_for_stack']:,.2f} | "
            f"Прибыль за шт: {item['profit_per_item']:,.2f}"
        )

    report_str = "\n".join(report_lines)
    log_and_update(f"[DEBUG] Сформирован отчет:\n{report_str}")

    report_path = Path(__file__).parent / "logs"
    report_path.mkdir(exist_ok=True)
    report_file = report_path / f"sell_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_str)
        f.write("\n\n--- Полный лог сессии ---\n")
        f.write("\n".join(log_entries))
    log_and_update(f"[DEBUG] Отчет сохранен: {report_file}")

    return True, f"Продажа завершена! Прибыль: {final_profit:,.0f}"

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
from thefuzz import fuzz
def ocr_scan_text(region):
    """Сканирует текст в указанной области."""
    try:
        x, y, w, h = region
        screenshot = ImageGrab.grab(bbox=(x, y, x + w, y + h))
        custom_config = '--psm 7'
        text = pytesseract.image_to_string(screenshot, lang='rus', config=custom_config).strip()
        return text.lower().replace('\n', ' ')
    except Exception as e:
        logging.error(f"Ошибка OCR текста: {e}")
        return ""

def ocr_scan_digits(region):
    """Сканирует только цифры в указанной области."""
    try:
        x, y, w, h = region
        screenshot = ImageGrab.grab(bbox=(x, y, x + w, y + h))
        text = pytesseract.image_to_string(screenshot, config='--psm 7 -c tessedit_char_whitelist=0123456789')
        return int(text.strip()) if text.strip() else 0
    except Exception as e:
        logging.error(f"Ошибка OCR цифр: {e}")
        return 0

def click_with_scatter(x, y, scatter=5):
    """Кликает с небольшим случайным смещением."""
    x_offset = random.randint(-scatter, scatter)
    y_offset = random.randint(-scatter, scatter)
    final_x = x + x_offset
    final_y = y + y_offset
    pyautogui.click(final_x, final_y)
    print(f"Clicked at ({final_x}, {final_y}) with offset ({x_offset}, {y_offset})")

def verify_item_name_for_selling(expected_name, region, similarity_threshold=90):
    """
    Scans the item name in the sell window and fuzzy matches it.
    This is a standalone function for the seller script.
    """
    try:
        scanned_name = ocr_scan_text(region)
        if not scanned_name:
            logging.warning("OCR for sell verification returned empty string.")
            return False, "OCR не распознал имя"

        normalized_expected = expected_name.lower().strip()
        
        similarity_ratio = fuzz.ratio(normalized_expected, scanned_name)
        
        log_msg = (f"Fuzzy Sell Check: Expected='{normalized_expected}', "
                   f"Recognized='{scanned_name}', Similarity={similarity_ratio}%")
        print(log_msg)
        logging.info(log_msg)

        if similarity_ratio >= similarity_threshold:
            return True, f"Имя подтверждено (Схожесть: {similarity_ratio}%)"
        else:
            return False, f"Имя не совпало (Схожесть: {similarity_ratio}%)"
    except Exception as e:
        logging.error(f"A critical error occurred during sell verification: {e}")
        return False, f"Ошибка верификации: {e}"
    
def run_selling_cycle(coords, regions, gui_callback):
    """
    Основной цикл продажи предметов с верификацией имени.
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
    
    # --- Data loading remains the same ---
    try:
        purchase_log_path = Path(__file__).parent / 'purchase_log.csv'
        if not purchase_log_path.exists():
            with open(purchase_log_path, 'w', newline='', encoding='utf-8') as f:
                csv.writer(f).writerow(['item_name', 'quantity', 'price_per_unit', 'purchase_type'])
        
        purchases_df = pd.read_csv(purchase_log_path)
        purchases_df['total_cost'] = purchases_df['quantity'] * purchases_df['price_per_unit']
        item_costs = purchases_df.groupby('item_name').agg(
            total_quantity=('quantity', 'sum'),
            total_cost=('total_cost', 'sum')
        ).reset_index()
        item_costs['wapp'] = item_costs['total_cost'] / item_costs['total_quantity']

        items_table_df = pd.read_excel(Path(__file__).parent / 'table.xlsx')
    except Exception as e:
        log_and_update(f"[ERROR] Ошибка при загрузке данных: {e}")
        return False, f"Ошибка чтения логов или таблицы: {e}"

    total_income = 0
    calculated_total_spent = 0
    sold_items_details = []
    failure_counter = 0

    while failure_counter < 5:
        if not gui_callback('is_running'):
            log_and_update("Продажа прервана пользователем")
            return False, "Продажа прервана пользователем"
        gui_callback('pause_event_wait')

        # --- NEW LOGIC FLOW STARTS HERE ---
        
        # 1. Click the Sell Button first
        log_and_update("Клик на предмет для продажи...")
        click_with_scatter(*coords['sell_button'], scatter=5)
        time.sleep(0.5) # Wait for the sell window to appear

        # 2. Scan and Verify Item Name
        scanned_item_name = ocr_scan_text(regions['item_name'])
        is_verified, reason = verify_item_name_for_selling(scanned_item_name, regions['item_name'])

        if not is_verified:
            failure_counter += 1
            log_and_update(f"[WARNING] Проверка имени не пройдена: {reason}. Попытка {failure_counter}/5. Отмена продажи.")
            # Click the close button to exit the sell window
            time.sleep(0.2) # Wait before trying the next item
            continue # Skip to the next iteration of the while loop

        # If verification is successful, reset the failure counter and proceed
        failure_counter = 0
        log_and_update(f"Предмет для продажи: '{scanned_item_name}'. {reason}")
        
        # Look up WAPP for the verified item
        row_purchase = item_costs[item_costs['item_name'].str.lower() == scanned_item_name]
        row_table = items_table_df[items_table_df['name'].str.lower() == scanned_item_name]

        wapp = 0
        if not row_purchase.empty:
            wapp = row_purchase.iloc[0]['wapp']
        elif not row_table.empty:
            wapp = row_table.iloc[0].get('value', 0)
        
        if wapp == 0:
            log_and_update(f"[WARNING] Не найдена себестоимость для '{scanned_item_name}'. Пропуск.")
            time.sleep(0.2)
            continue
        
        # 3. Click Minus Button
        log_and_update("Клик на кнопку 'минус'...")
        click_with_scatter(*coords['minus_button'], scatter=5)
        time.sleep(0.2)
        
        # 4. Scan prices and confirm (this part is mostly the same)
        sale_price = ocr_scan_digits(regions['sale_price'])
        price_per_item = ocr_scan_digits(regions['buy_price'])

        if sale_price > 0 and price_per_item > 1:
            total_income += sale_price
            tax = 0.105
            
            # Calculate quantity and profit
            quantity_in_stack = int(round(sale_price / ((price_per_item-1) * (1 - tax))))
            profit_per_item = (price_per_item-1) * (1 - tax) - wapp
            
            cost_for_this_stack = quantity_in_stack * wapp
            calculated_total_spent += cost_for_this_stack
            
            click_with_scatter(*coords['confirm_button'], scatter=5)
            log_and_update(f"Продажа '{scanned_item_name}' x{quantity_in_stack} подтверждена.")
            
            sold_items_details.append({
                'name': scanned_item_name,
                'quantity': quantity_in_stack,
                'sale_price_total': sale_price,
                'profit_per_item': profit_per_item,
                'cost_for_stack': cost_for_this_stack
            })
        else:
            log_and_update(f"[WARNING] Не удалось распознать цену продажи для '{scanned_item_name}'. Отмена.")
            if 'close_button' in coords:
                click_with_scatter(*coords['close_button'], scatter=5)

        time.sleep(0.5) # Wait after each successful or failed sale

    # --- Report generation remains the same ---
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
    report_path = Path(__file__).parent / "logs"
    report_path.mkdir(exist_ok=True)
    report_file = report_path / f"sell_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_str)
        f.write("\n\n--- Полный лог сессии ---\n")
        f.write("\n".join(log_entries))
    log_and_update(f"Отчет сохранен: {report_file}")

    return True, f"Продажа завершена! Прибыль: {final_profit:,.0f}"

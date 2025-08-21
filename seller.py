import pyautogui
import pytesseract
import pandas as pd
import time
import logging
from datetime import datetime
from pathlib import Path
from PIL import ImageGrab
import csv
def ocr_scan_text(region):
    """Сканирует текст в указанной области."""
    try:
        x, y, w, h = region
        screenshot = ImageGrab.grab(bbox=(x, y, x + w, y + h))
        text = pytesseract.image_to_string(screenshot, lang='rus+eng').strip()
        screenshot.save(Path(__file__).parent / "debug_ocr.png")
        return text.lower()
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

def run_selling_cycle(coords, regions, total_spent, gui_callback):
    """
    Основной цикл продажи предметов.
    :param coords: Словарь с координатами кнопок.
    :param regions: Словарь с областями экрана для OCR.
    :param total_spent: Общая сумма затрат на покупку.
    :param gui_callback: Функция для обновления GUI (статус, лог).
    """
    log_entries = []
    
    def log_and_update(message):
        """Локальная функция для логирования и обновления GUI."""
        full_message = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        log_entries.append(full_message)
        logging.info(message)
        gui_callback('update_status', message)
        print(message)

    log_and_update("Начинается сессия продаж...")
    
    # --- Шаг 1: Загрузка и обработка журнала покупок ---
    purchase_log_path = Path(__file__).parent / 'purchase_log.csv'
    if not purchase_log_path.exists():
        try:
            with open(purchase_log_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Записываем заголовки
                writer.writerow(['item_name', 'quantity', 'price_per_unit', 'purchase_type'])
            log_and_update("Файл purchase_log.csv не найден, создан новый с заголовками.")
        except Exception as e:
            log_and_update(f"Ошибка при создании purchase_log.csv: {e}")
            return False, f"Не удалось создать purchase_log.csv: {e}"

    try:
        required_cols = {'item_name', 'quantity', 'price_per_unit'}
        purchases_df = pd.read_csv(purchase_log_path)
        purchases_df['total_cost'] = purchases_df['quantity'] * purchases_df['price_per_unit']
        item_costs = purchases_df.groupby('item_name').agg(
            total_quantity=('quantity', 'sum'),
            total_cost=('total_cost', 'sum')
        ).reset_index()
        item_costs['wapp'] = item_costs['total_cost'] / item_costs['total_quantity'] # WAPP = Weighted Average Purchase Price
        log_and_update("Журнал покупок успешно загружен и обработан.")
    except Exception as e:
        missing = required_cols - set(purchases_df.columns)
        if missing:
            raise ValueError(f"В purchase_log.csv не хватает колонок: {missing}")        
        log_and_update(f"Ошибка при чтении журнала покупок: {e}")
        return False, f"Ошибка чтения purchase_log.csv: {e}"

    # --- Шаг 2: Основной цикл продажи ---
    total_income = 0
    sold_items_details = []
    failure_counter = 0
    
    # Загружаем table.xlsx для получения данных о количестве (store)
    try:
        items_table_df = pd.read_excel(Path(__file__).parent / 'table.xlsx')
        log_and_update("Таблица успешно загружена и обработана.")
    except Exception as e:
        log_and_update(f"Ошибка при чтении table.xlsx: {e}")
        return False, f"Ошибка чтения table.xlsx: {e}"

    while failure_counter < 10:
        # Пауза
        if not gui_callback('is_running'):
            log_and_update("Продажа прервана пользователем.")
            return False, "Продажа прервана пользователем."
        gui_callback('pause_event_wait')

        item_name = ocr_scan_text(regions['item_name'])

        if item_name and not item_costs[item_costs['item_name'] == item_name].empty:
            failure_counter = 0
            log_and_update(f"Обнаружен предмет: {item_name}")
            
            item_data = item_costs[item_costs['item_name'] == item_name].iloc[0]
            wapp = item_data['wapp'] 
            quantity_in_stack = items_table_df[items_table_df['name'] == item_name]['store'].iloc[0]
            log_and_update(f"Выполнены рассчеты: Предметов: {quantity_in_stack}, Средняя стоимость: {wapp}")
        else:
            row = items_table_df.loc[items_table_df['name'] == item_name]
            if not row.empty:
                log_and_update(f"{item_name} не найден в purchase_log, используем table.xlsx")
                value = row['value'].iloc[0]
                quantity_in_stack = row['store'].iloc[0]
                wapp = value
            else:
                failure_counter += 1
                log_and_update(f"{item_name} отсутствует и в purchase_log, и в table.xlsx")
                time.sleep(1)
                continue
            
        # Шаг 2.2: Клики для выставления на продажу
        pyautogui.click(coords['sell_button'], duration=0.1)
        time.sleep(0.3)
        pyautogui.click(coords['minus_button'], duration=0.1)
        time.sleep(0.3)

        # Шаг 2.3: Сканируем итоговую цену продажи
        sale_price = ocr_scan_digits(regions['sale_price'])
        if sale_price > 0:
            log_and_update(f"Цена продажи стака: {sale_price}")
            
            # Шаг 2.4: Подтверждаем продажу
            pyautogui.click(coords['minus_button'], duration=0.1)
            time.sleep(0.3)
            log_and_update("Ордер на продажу создан.")

            # Шаг 2.5: Обновление статистики
            total_income += sale_price
            
            # Расчет прибыли
            item_data = item_costs[item_costs['item_name'] == item_name].iloc[0]
            item_table_data = items_table_df[items_table_df['name'] == item_name].iloc[0]
            
            wapp = item_data['wapp']
            quantity_in_stack = item_table_data['store']
            sale_price_per_item = sale_price / quantity_in_stack
            profit_per_item = sale_price_per_item - wapp

            sold_items_details.append({
                'name': item_name,
                'quantity': quantity_in_stack,
                'sale_price_total': sale_price,
                'profit_per_item': profit_per_item
            })
            
            gui_callback('update_current_item_info', {
                'name': item_name, 'value': f"Прибыль за шт: {profit_per_item:,.0f}",
                'ocr_price': f"Доход: {total_income:,.0f}", 'bought': '', 'store': '',
                'limit_price': '', 'budget': 'Расчет...', 'total_spent': f"Затраты: {total_spent:,.0f}"
            })
        else:
            log_and_update("Не удалось распознать цену продажи, отмена.")
            # Нужен клик для отмены операции, если он требуется
            time.sleep(1)
        try:    
                if failure_counter == 15:
                    log_and_update("Инвентарь пуст. Продажа завершена.")
                    break
        except Exception as e:
            logging.warning(f"Ошибка при поиске inventory_clear.png: {e}")
        
        failure_counter += 1
        log_and_update(f"Предмет не найден или не в списке покупок. Попытка {failure_counter}/100")
        time.sleep(1)

    if failure_counter >= 100:
        log_and_update("Продажа остановлена после 100 неудачных попыток.")

    # --- Шаг 3: Формирование и сохранение итогового отчета ---
    final_profit = total_income - total_spent
    report = [
        f"--- Отчет о продажах ({datetime.now().strftime('%d.%m.%Y %H:%M')}) ---\n",
        "--- Итоговая сводка ---",
        f"Общий доход с продаж: {total_income:,.0f}",
        f"Потраченный бюджет: {-total_spent:,.0f}",
        f"Чистая прибыль: {final_profit:,.0f}\n",
        "--- Детализация по предметам ---"
    ]
    for i, item in enumerate(sold_items_details, 1):
        report.append(
            f"{i}. {item['name']} (x{item['quantity']})\n"
            f"   - Сумма продажи: {item['sale_price_total']:,.0f}      | Прибыль за шт: {item['profit_per_item']:,.0f}"
        )
    
    report_str = "\n".join(report)
    log_and_update("\n" + report_str)
    
    report_filename = f"sell_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    logs_dir = Path(__file__).parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    with open(logs_dir / report_filename, 'w', encoding='utf-8') as f:
        f.write(report_str)
        f.write("\n\n--- Полный лог сессии ---\n")
        f.write("\n".join(log_entries))

    log_and_update(f"Отчет сохранен в {logs_dir / report_filename}")
    
    # Очистка журнала покупок
    try:
        purchase_log_path.unlink()
        log_and_update("Журнал покупок purchase_log.csv очищен.")
    except Exception as e:
        log_and_update(f"Не удалось очистить журнал покупок: {e}")

    return True, f"Продажа завершена! Прибыль: {final_profit:,.0f}"

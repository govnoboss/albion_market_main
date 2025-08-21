# seller.py
import pyautogui
import pytesseract
import pandas as pd
import time
import logging
from datetime import datetime
from pathlib import Path
from PIL import ImageGrab

# --- Вспомогательные функции ---

def ocr_scan_text(region):
    """Сканирует текст в указанной области."""
    try:
        x, y, w, h = region
        screenshot = ImageGrab.grab(bbox=(x, y, x + w, y + h))
        # Улучшение изображения для лучшего распознавания
        gray_image = screenshot.convert('L')
        # Увеличим изображение, чтобы текст стал четче
        upscaled_image = gray_image.resize((w * 2, h * 2))
        text = pytesseract.image_to_string(upscaled_image, lang='rus+eng').strip()
        return text
    except Exception as e:
        logging.error(f"Ошибка OCR текста: {e}")
        return ""

def ocr_scan_digits(region):
    """Сканирует только цифры в указанной области."""
    try:
        x, y, w, h = region
        screenshot = ImageGrab.grab(bbox=(x, y, x + w, y + h))
        gray_image = screenshot.convert('L')
        text = pytesseract.image_to_string(gray_image, config='--psm 7 -c tessedit_char_whitelist=0123456789')
        return int(text.strip()) if text.strip() else 0
    except Exception as e:
        logging.error(f"Ошибка OCR цифр: {e}")
        return 0

# --- Основная функция продажи ---

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
        log_and_update("Ошибка: Журнал покупок purchase_log.csv не найден!")
        return False, "Журнал покупок не найден."

    try:
        purchases_df = pd.read_csv(purchase_log_path)
        # Рассчитываем средневзвешенную цену для каждого предмета
        purchases_df['total_cost'] = purchases_df['quantity'] * purchases_df['price_per_unit']
        item_costs = purchases_df.groupby('item_name').agg(
            total_quantity=('quantity', 'sum'),
            total_cost=('total_cost', 'sum')
        ).reset_index()
        item_costs['wapp'] = item_costs['total_cost'] / item_costs['total_quantity'] # WAPP = Weighted Average Purchase Price
        log_and_update("Журнал покупок успешно загружен и обработан.")
    except Exception as e:
        log_and_update(f"Ошибка при чтении журнала покупок: {e}")
        return False, f"Ошибка чтения purchase_log.csv: {e}"

    # --- Шаг 2: Основной цикл продажи ---
    total_income = 0
    sold_items_details = []
    failure_counter = 0
    
    # Загружаем table.xlsx для получения данных о количестве (store)
    try:
        items_table_df = pd.read_excel(Path(__file__).parent / 'table.xlsx')
    except Exception as e:
        log_and_update(f"Ошибка при чтении table.xlsx: {e}")
        return False, f"Ошибка чтения table.xlsx: {e}"

    while failure_counter < 100:
        # Пауза
        gui_callback('pause_event_wait')

        # Шаг 2.1: Сканируем название предмета
        item_name = ocr_scan_text(regions['item_name'])
        
        # Ищем совпадение в нашем списке покупок
        if item_name and not item_costs[item_costs['item_name'] == item_name].empty:
            failure_counter = 0
            log_and_update(f"Обнаружен предмет: {item_name}")

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
                try:
                    make_order_btn = pyautogui.locateCenterOnScreen(
                        str(Path(__file__).parent / "buttons_image" / 'make_order.png'), 
                        confidence=0.8
                    )
                    if make_order_btn:
                        pyautogui.click(make_order_btn)
                        time.sleep(0.5)
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
                        log_and_update("Кнопка 'make_order.png' не найдена, пропускаем.")
                except Exception as e:
                    log_and_update(f"Ошибка при поиске/клике на make_order.png: {e}")
            else:
                log_and_update("Не удалось распознать цену продажи, отмена.")
                # Нужен клик для отмены операции, если он требуется
                time.sleep(1)
        else:
            # Предмет не распознан или его нет в списке покупок
            try:
                if pyautogui.locateOnScreen(str(Path(__file__).parent / "buttons_image" / 'inventory_clear.png'), confidence=0.8):
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
import cv2
import numpy as np
import os
import sys
import time
from PIL import ImageGrab

def test_matching(target_image_path, template_path="resources/ref_empty_market.png"):
    """
    Проверяет наличие шаблона template_path внутри target_image_path.
    """
    if not os.path.exists(template_path):
        print(f"❌ Ошибка: Файл шаблона не найден: {template_path}")
        return

    if not os.path.exists(target_image_path):
        print(f"❌ Ошибка: Целевой файл не найден: {target_image_path}")
        return

    # 1. Загрузка изображений
    # cv2.IMREAD_GRAYSCALE - загружаем в ч/б для скорости и надежности
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    target = cv2.imread(target_image_path, cv2.IMREAD_GRAYSCALE)

    if template is None:
        print("❌ Не удалось прочитать файл шаблона (формат?)")
        return
    if target is None:
        print("❌ Не удалось прочитать целевой файл")
        return

    # Проверка размеров
    if template.shape[0] > target.shape[0] or template.shape[1] > target.shape[1]:
        print("⚠️ Внимание: Шаблон больше, чем целевое изображение! Поиск невозможен стандартными методами.")
        print(f"Шаблон: {template.shape}, Цель: {target.shape}")
        return

    print(f"🔎 Поиск шаблона '{template_path}' в '{target_image_path}'...")

    # 2. Template Matching
    # TM_CCOEFF_NORMED - хороший метод, возвращает от -1 до 1 (1 = совпадение)
    result = cv2.matchTemplate(target, template, cv2.TM_CCOEFF_NORMED)
    
    # Находим лучшие совпадения
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    
    print(f"📊 Результат совпадения (Score): {max_val:.4f}")
    
    threshold = 0.8 # Порог уверенности (80%)
    
    if max_val >= threshold:
        print(f"✅ НАЙДЕНО! Координаты: {max_loc}")
        
        # Визуализация (опционально, создаст файл результата)
        h, w = template.shape
        top_left = max_loc
        bottom_right = (top_left[0] + w, top_left[1] + h)
        
        # Рисуем прямоугольник на цветной копии
        target_color = cv2.imread(target_image_path)
        cv2.rectangle(target_color, top_left, bottom_right, (0, 255, 0), 2)
        
        out_file = "test_result.png"
        cv2.imwrite(out_file, target_color)
        print(f"🖼️ Сохранено изображение с обводкой: {out_file}")
        
    else:
        print(f"❌ НЕ НАЙДЕНО (Ниже порога {threshold})")

if __name__ == "__main__":
    print("⏳ Задержка 2 секунды... Переключитесь на игру!")
    time.sleep(2)
    
    # Делаем скриншот экрана
    print("� Снимаем скриншот экрана...")
    screenshot = ImageGrab.grab()
    screenshot_path = "live_screenshot.png"
    screenshot.save(screenshot_path)
    print(f"✅ Скриншот сохранен в: {screenshot_path}")
    
    # Запускаем поиск
    test_matching(screenshot_path)


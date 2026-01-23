
import sys
import os
import time
from PyQt6.QtWidgets import QApplication

# Добавляем корень проекта в путь поиска модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.navigator import Navigator
from src.utils.logger import get_logger

def main():
    app = QApplication(sys.argv)
    logger = get_logger()
    
    logger.info("=== DEBUG: Navigation Movement Test ===")
    nav = Navigator()
    
    logger.info(">> Пожалуйста, переключитесь на окно с игрой! У вас 3 секунды...")
    time.sleep(3.0)
    
    # 1. Скрываем интерфейс (для чистоты детекта)
    logger.info("1. Скрываем интерфейс (Alt+J)...")
    nav.toggle_interface()
    time.sleep(1.0) 
    
    # 2. Открываем карту
    logger.info("2. Переключение в Travel Mode (Shift+N)...")
    nav.toggle_travel_mode(expected_state=True)
    time.sleep(1.0)
    
    # 3. Ищем цель (Сначала Сундук, потом Флаги)
    logger.info("🔎 Поиск целей...")
    
    chest_pos = nav.find_chest()
    flags = nav.find_yellow_flags()
    
    target = None
    if chest_pos:
        logger.info(f"📦 СУНДУК найден: {chest_pos}")
        target = chest_pos
    elif flags:
        logger.info(f"🚩 Флаги найдены: {len(flags)} шт")
        target = flags[0]
        logger.info(f"🎯 Цель (Флаг #1): {target}")
    else:
        logger.warning("⚠️ Ни сундук, ни флаги не найдены!")

    # LOGIC CHECK: Chest -> NE Flag
    if chest_pos and flags:
        logger.info("📐 Проверка логики NE Флага...")
        ne_flag = nav.get_ne_flag(chest_pos, flags)
        if ne_flag:
            logger.success(f"✅ NE Флаг найден: {ne_flag}")
            if target is None: target = ne_flag # Override target for movement test
        else:
            logger.warning("⚠️ Флагов в секторе NE (Top-Right) не найдено.")

    if target:
        # 4. Движение
        logger.info("🏃 Пробуем сделать шаг к цели...")
        nav.move_towards(*target)
        time.sleep(2.0)
    else:
        logger.warning("❌ Тест движения невозможен.")
        
    # 5. Возвращаем всё как было
    logger.info("🔄 Восстанавливаем интерфейс...")
    nav.toggle_interface()
    time.sleep(0.5)
    
    logger.info("🔄 Закрываем карту...")
    nav.toggle_travel_mode(expected_state=False)
    
    logger.info("✅ Тест завершен. Персонаж сдвинулся?")

if __name__ == "__main__":
    main()

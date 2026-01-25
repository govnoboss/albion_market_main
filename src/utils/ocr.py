import pytesseract
from PIL import ImageGrab, ImageOps, Image
import os
import shutil
from typing import Optional
from ..utils.logger import get_logger

logger = get_logger()

# Попытка найти путь к Tesseract
TESSERACT_CMD = shutil.which("tesseract")
if not TESSERACT_CMD:
    # Проверяем стандартные пути Windows
    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\Student\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
    ]
    for path in possible_paths:
        if os.path.exists(path):
            TESSERACT_CMD = path
            break

if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    logger.info(f"Tesseract найден по пути: {TESSERACT_CMD}")
    print(f"✅ Tesseract найден: {TESSERACT_CMD}")
else:
    logger.warning("Tesseract не найден! OCR функции будут недоступны.")
    print("❌ Tesseract НЕ найден! OCR недоступен.")

def is_ocr_available() -> bool:
    """Проверка доступности OCR"""
    return TESSERACT_CMD is not None

def read_screen_text(x: int, y: int, w: int, h: int, lang: str = 'rus', whitelist: str = None) -> str:
    """
    Считывает текст с указанной области экрана.
    x, y, w, h: координаты области
    lang: языки ('eng', 'rus', 'eng+rus')
    whitelist: строка разрешенных символов (например '0123456789')
    """
    if not is_ocr_available():
        return ""
    
    try:
        # 1. Снимаем скриншот области
        bbox = (x, y, x + w, y + h)
        screenshot = ImageGrab.grab(bbox=bbox)
        
        # 2. Предобработка (Preprocessing)
        # Масштабирование (очень важно для мелких цифр вроде "1")
        scale = 3
        new_size = (screenshot.width * scale, screenshot.height * scale)
        processed = screenshot.resize(new_size, Image.Resampling.LANCZOS)
        
        from PIL import ImageStat # Import needed

        # Конвертация в Grayscale
        gray = ImageOps.grayscale(processed)
        
        # Адаптивная Инверсия (для поддержки светлых и темных тем)
        # Нам нужно получить "Черный текст на Белом фоне".
        # 1. Считаем среднюю яркость
        stat = ImageStat.Stat(gray)
        mean_brightness = stat.mean[0]
        
        # 2. Если фон темный (< 128), то текст скорее всего светлый -> Инвертируем
        # Если фон светлый (> 128), то текст скорее всего темный -> Оставляем как есть
        if mean_brightness < 128:
            # Темная тема: инверсия делает фон светлым, текст темным
            prepared = ImageOps.invert(gray)
        else:
            # Светлая тема: уже светлый фон, темный текст
            prepared = gray
        
        # Усиление контраста (Thresholding)
        # Все что светлее 140 -> 255 (белый фон), остальное -> 0 (черный текст)
        threshold = 140 
        binarized = prepared.point(lambda p: 255 if p > threshold else 0)

        # 3. Распознавание
        # --psm 7: Treat the image as a single text line.
        config = '--psm 7'
        if whitelist:
            config += f' -c tessedit_char_whitelist={whitelist}'
            
        text = pytesseract.image_to_string(binarized, lang=lang, config=config)
        
        clean_text = text.strip()
        logger.debug(f"OCR Scan [{x},{y},{w},{h}]: '{clean_text}'")
        return clean_text
        
    except Exception as e:
        logger.error(f"Ошибка OCR: {e}")
        return ""

def fuzzy_match_quality(detected_text: str, expected_names: list[str]) -> bool:
    """
    Проверяет, соответствует ли распознанный текст одному из ожидаемых значений.
    Допускает небольшие опечатки (можно использовать Levenshtein, здесь упрощенно).
    """
    normalized_detected = detected_text.lower().replace(" ", "").replace("_", "")
    
    for expected in expected_names:
        normalized_expected = expected.lower().replace(" ", "").replace("_", "")
        
        # Точное совпадение после нормализации
        if normalized_expected in normalized_detected or normalized_detected in normalized_expected:
            return True
            
        # TODO: Добавить Levenshtein distance для более строгого fuzzy match если потребуется
        
    return False


def parse_price(text: str) -> Optional[int]:
    """
    Парсит цену из текста.
    Возвращает int или None, если не удалось распознать число.
    Поддерживает:
    - Разделители тысяч (пробелы, запятые, точки): "1 000", "1,000", "1.000" -> 1000
    - Ошибки OCR: "O" -> "0"
    - Суффиксы: "1.5k" -> 1500, "2m" -> 2000000
    """
    if not text:
        return None
        
    # 1. Нормализация
    clean = text.lower().strip()
    
    # Замена частых ошибок OCR (аккуратно)
    # 'o' -> '0'
    if 'o' in clean and any(c.isdigit() for c in clean):
        clean = clean.replace('o', '0')
    
    # 'l', 'i', '|', ']', '[' -> '1'
    # Часто Tesseract путает 1 с l или I или полосками
    for char in ['l', 'i', '|', ']', '[', '!', 't']:
        if char in clean:
            clean = clean.replace(char, '1')
        
    # 2. Обработка суффиксов
    multiplier = 1.0
    if clean.endswith('k'):
        multiplier = 1000.0
        clean = clean[:-1]
    elif clean.endswith('m') or clean.endswith('kk'):
        multiplier = 1000000.0
        clean = clean[:-1] if clean.endswith('m') else clean[:-2]
        
    # 3. Очистка от мусора (оставляем цифры и точку, если она десятичная для k/m)
    # Если суффикса не было, точку/запятую считаем мусором (разделителем тысяч)
    # Если суффикс был, точка может быть десятичной ("1.5k")
    
    allowed = "0123456789"
    if multiplier > 1.0:
        allowed += "." # Разрешаем точку только если есть множитель
    
    filtered = "".join([c for c in clean if c in allowed])
    
    if not filtered:
        return None
        
    try:
        # Если есть точка и множитель -> float -> int
        if '.' in filtered and multiplier > 1.0:
            val = float(filtered)
            result = int(val * multiplier)
        else:
            # Иначе просто int (игнорируя точки внутри, если они вдруг остались и не удалились)
            # Но выше мы удалили точки если multiplier == 1.
            result = int(int(filtered) * int(multiplier))
        
        # Цена <= 5 скорее всего ошибка OCR (мусор)
        if result <= 5:
            return 0
            
        return result
        
    except ValueError:
        return None

def read_price_at(area: dict) -> Optional[int]:
    """
    Считывает цену из заданной области экрана.
    area: {'x': int, 'y': int, 'w': int, 'h': int}
    """
    if not area:
        return None
        
    # Используем английский язык для цифр и белый список
    whitelist = "0123456789., " # Основные
    whitelist += "oli|][!t" # Для поддержки fallback логики в parse_price
    
    raw_text = read_screen_text(
        area['x'], area['y'], area['w'], area['h'], 
        lang='eng', 
        whitelist=whitelist
    )
    return parse_price(raw_text)

def read_amount_at(area: dict) -> int:
    """
    Считывает количество (целое число) из заданной области.
    """
    if not area: return 1 # Default fallback
    
    # Только цифры
    whitelist = "0123456789"
    # Добавляем возможные OCR ошибки 
    whitelist += "oli|][!t" 
    
    raw_text = read_screen_text(
        area['x'], area['y'], area['w'], area['h'], 
        lang='eng', 
        whitelist=whitelist
    )
    
    val = parse_price(raw_text)
    return val if val is not None else 0

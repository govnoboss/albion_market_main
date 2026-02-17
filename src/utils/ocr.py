import sys
import pytesseract
from PIL import ImageGrab, ImageOps, Image
import time
import os
import shutil
import cv2
import numpy as np
from typing import Optional
from ..utils.logger import get_logger

logger = get_logger()

from .paths import get_app_root, get_logs_dir

# Попытка найти путь к Tesseract
def _find_tesseract():
    """Найти путь к Tesseract OCR"""
    app_dir = get_app_root()
    log_file = get_logs_dir() / "debug_startup.log"
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n--- TESSERACT DETECTION {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        f.write(f"DEBUG: sys.frozen = {getattr(sys, 'frozen', False)}\n")
        f.write(f"DEBUG: app_dir = {app_dir}\n")

    # 1. Проверяем папку 'tesseract' рядом с запускаемым файлом (Portable / Standalone)
    local_tesseract = app_dir / "tesseract" / "tesseract.exe"
    if local_tesseract.exists():
        return str(local_tesseract)
        
    # 2. Проверяем assets/tesseract (для режима разработки/скрипта)
    assets_tesseract = app_dir / "assets" / "tesseract" / "tesseract.exe"
    if assets_tesseract.exists():
        return str(assets_tesseract)

    # 3. Fallback: Проверяем PATH (если вдруг пользователь удалил папку, но у него есть в системе)
    path_tesseract = shutil.which("tesseract")
    if path_tesseract:
        return path_tesseract
    
    # 4. Fallback: Стандартные пути Windows
    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\Student\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None

# Lazy initialization
TESSERACT_CMD = None

def init_ocr():
    """Инициализация Tesseract если еще не была проведена"""
    global TESSERACT_CMD
    if TESSERACT_CMD is None:
        try:
            TESSERACT_CMD = _find_tesseract()
            if TESSERACT_CMD:
                pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
                logger.info(f"Tesseract найден по пути: {TESSERACT_CMD}")
            else:
                logger.warning("Tesseract не найден! OCR функции будут недоступны.")
        except Exception as e:
            logger.error(f"Ошибка при инициализации OCR: {e}")
            TESSERACT_CMD = None
    return TESSERACT_CMD is not None

def is_ocr_available() -> bool:
    """Проверка доступности OCR"""
    return init_ocr()

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
        
        # --- OTSU THRESHOLDING (Implicit Grayscale) ---
        import cv2
        import numpy as np
        
        # Convert PIL to Numpy (RGB)
        img_np = np.array(processed)
        
        # Convert to Grayscale for Otsu
        if len(img_np.shape) == 3:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        
        # Otsu's thresholding
        _, thresh_np = cv2.threshold(img_np, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Convert back to PIL
        binarized = Image.fromarray(thresh_np)
        
        # 3. Распознавание
        # --psm 6: Assume a single uniform block of text.
        config = '--psm 6'
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


def parse_price(text: str, allow_low_values: bool = False) -> Optional[int]:
    """
    Парсит цену из текста.
    allow_low_values: Если True, разрешает значения <= 5 (для Quantity).
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
        
        # Цена <= 5 скорее всего ошибка OCR (мусор), ЕСЛИ не разрешены низкие значения
        if not allow_low_values and result <= 5:
            return 0
            
        # Исключение для 310 (ложное срабатывание OCR при отсутствии цены)
        if result == 310:
            logger.info(" OCR Exception: '310' detected as false positive, recording as 0")
            return 0
            
        return result
        
    except ValueError:
        return None

def _check_empty_market(area: dict, threshold: float = 0.8) -> bool:
    """
    Проверяет наличие надписи 'Нет товара' методом Template Matching.
    Возвращает True, если надпись найдена (рынок пуст).
    """
    template_path = os.path.join(os.path.dirname(__file__), '..', '..', 'resources', 'ref_empty_market.png')
    
    if not os.path.exists(template_path):
        # Если эталон не найден, пропускаем проверку
        return False
        
    try:
        # Загружаем шаблон
        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            return False
            
        # Делаем скриншот области
        bbox = (area['x'], area['y'], area['x'] + area['w'], area['y'] + area['h'])
        screenshot = ImageGrab.grab(bbox=bbox)
        
        # Конвертируем в numpy grayscale
        target = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
        
        # Проверка размеров
        if template.shape[0] > target.shape[0] or template.shape[1] > target.shape[1]:
            return False
            
        # Template Matching
        result = cv2.matchTemplate(target, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        
        if max_val >= threshold:
            logger.info(f"🚫 Empty Market detected (Score: {max_val:.2f})")
            return True
            
        return False
        
    except Exception as e:
        logger.warning(f"Template check error: {e}")
        return False

def read_price_at(area: dict) -> Optional[int]:
    """
    Считывает цену из заданной области экрана.
    area: {'x': int, 'y': int, 'w': int, 'h': int}
    """
    if not area:
        return None
    
    # --- Step 1: Check for Empty Market ---
    if _check_empty_market(area):
        return 0
        
    # --- Step 2: OCR Strict Numeric ---
    # whitelist: Цифры + разделители + суффиксы (k, m, b) + пробел
    whitelist="0123456789.,kKmMBb "
    
    raw_text = read_screen_text(
        area['x'], area['y'], area['w'], area['h'], 
        lang='eng', 
        whitelist=whitelist
    )
    return parse_price(raw_text)

def read_qty_text(area: dict) -> int:
    """
    Специализированный метод для чтения КОЛИЧЕСТВА (buyer_top_lot_qty).
    """
    if not is_ocr_available() or not area:
        return 0
    
    try:
        # 1. Capture
        bbox = (area['x'], area['y'], area['x'] + area['w'], area['y'] + area['h'])
        screenshot = ImageGrab.grab(bbox=bbox)
        
        # 2. Scale x3 (User optimized)
        scale = 3
        new_size = (screenshot.width * scale, screenshot.height * scale)
        processed = screenshot.resize(new_size, Image.Resampling.LANCZOS)
        
        # Convert to numpy
        img_np = np.array(processed)
        
        # 3. Grayscale (Required for Threshold)
        if len(img_np.shape) == 3:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            
        # 4. Invert (User optimized)
        img_np = cv2.bitwise_not(img_np)
        
        # 5. Threshold Binary 125 (User optimized)
        _, img_np = cv2.threshold(img_np, 125, 255, cv2.THRESH_BINARY)
        
        # Convert back to PIL for Tesseract
        final_img = Image.fromarray(img_np)

        # 6. OCR (PSM 6, Numeric Whitelist)
        whitelist = "0123456789"
        config = f'--psm 6 -c tessedit_char_whitelist={whitelist}'
        
        text = pytesseract.image_to_string(final_img, lang='eng', config=config)
        clean_text = text.strip()
        
        logger.debug(f"OCR Qty Scan [{area['x']},{area['y']}]: '{clean_text}'")
        
        # Parse
        val = parse_price(clean_text, allow_low_values=True)
        return val if val is not None else 0
        
    except Exception as e:
        logger.error(f"Ошибка OCR (Qty): {e}")
        return 0

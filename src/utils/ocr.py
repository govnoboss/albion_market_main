import sys
import pytesseract
from PIL import ImageGrab, ImageOps, Image
import time
import os
import shutil
import cv2
import numpy as np
import hashlib
from typing import Optional, Dict, Tuple
from ..utils.logger import get_logger

logger = get_logger()

from .paths import get_app_root, get_logs_dir, get_debug_ocr_dir

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
                logger.debug(f"Tesseract найден по пути: {TESSERACT_CMD}")
            else:
                logger.debug("Tesseract не найден! OCR функции будут недоступны.")
        except Exception as e:
            logger.error(f"Ошибка при инициализации OCR: {e}")
            TESSERACT_CMD = None
    return TESSERACT_CMD is not None

def is_ocr_available() -> bool:
    """Проверка доступности OCR"""
    return init_ocr()


class OCRCache:
    """Кэш для результатов OCR на основе хеширования пикселей"""
    def __init__(self):
        self._cache: Dict[Tuple[int, int, int, int], Tuple[str, str]] = {} # {area: (hash, text)}

    def get(self, area: Tuple[int, int, int, int], current_hash: str) -> Optional[str]:
        if area in self._cache:
            saved_hash, text = self._cache[area]
            if saved_hash == current_hash:
                return text
        return None

    def update(self, area: Tuple[int, int, int, int], new_hash: str, text: str):
        self._cache[area] = (new_hash, text)

    def clear(self):
        self._cache.clear()
        logger.debug("OCR Cache cleared.")

# Глобальный экземпляр кэша
_global_ocr_cache = OCRCache()

def clear_ocr_cache():
    """Публичный метод для сброса кэша при смене контекста"""
    _global_ocr_cache.clear()


def _is_ocr_debug_enabled() -> bool:
    """Проверка включён ли режим отладки OCR (сохранение скриншотов)"""
    try:
        from ..utils.config import get_config
        return bool(get_config().get_setting("ocr_debug_mode", False))
    except Exception:
        return False


def _save_debug_ocr_image(img, prefix: str, suffix: str = "") -> None:
    """Сохраняет изображение в папку debug_ocr при включённом режиме отладки"""
    if not _is_ocr_debug_enabled():
        return
    try:
        from datetime import datetime
        debug_dir = get_debug_ocr_dir()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        ms = int(time.time() * 1000) % 1000
        name = f"{prefix}_{ts}_{ms:03d}{suffix}.png"
        path = debug_dir / name
        img.save(str(path))
        logger.debug(f"OCR debug saved: {path.name}")
    except Exception as e:
        logger.warning(f"Failed to save OCR debug image: {e}")


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
        _save_debug_ocr_image(binarized, "price", f"_x{x}_y{y}_w{w}_h{h}")
        
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

def read_screen_text_cached(x: int, y: int, w: int, h: int, lang: str = 'rus', whitelist: str = None) -> str:
    """
    Версия read_screen_text с кэшированием по пикселям.
    """
    if not is_ocr_available():
        return ""

    try:
        # 1. Снимаем скриншот для хеширования
        bbox = (x, y, x + w, y + h)
        screenshot = ImageGrab.grab(bbox=bbox)
        
        # 2. Вычисляем быстрый хеш пикселей (MD5)
        # Для стабильности переводим в Grayscale (игнорируем мелкие цветовые вариации)
        gray_screenshot = ImageOps.grayscale(screenshot)
        img_data = gray_screenshot.tobytes()
        img_hash = hashlib.md5(img_data).hexdigest()
        
        area_key = (x, y, w, h)
        
        # 3. Проверка кэша
        cached_text = _global_ocr_cache.get(area_key, img_hash)
        if cached_text is not None:
            logger.debug(f"🚀 OCR Cache HIT [{x},{y}]: '{cached_text}'")
            return cached_text
            
        # 4. Если промах — запускаем предобработку и OCR как в оригинале
        # Но используем уже снятый screenshot, чтобы не делать ImageGrab дважды
        scale = 3
        new_size = (screenshot.width * scale, screenshot.height * scale)
        processed = screenshot.resize(new_size, Image.Resampling.LANCZOS)
        
        img_np = np.array(processed)
        if len(img_np.shape) == 3:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        
        _, thresh_np = cv2.threshold(img_np, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        binarized = Image.fromarray(thresh_np)
        
        config = '--psm 6'
        if whitelist:
            config += f' -c tessedit_char_whitelist={whitelist}'
            
        text = pytesseract.image_to_string(binarized, lang=lang, config=config)
        clean_text = text.strip()
        
        # 5. Обновляем кэш (только если считали текст)
        if clean_text:
            _global_ocr_cache.update(area_key, img_hash, clean_text)
            logger.debug(f"📥 OCR Cache MISS [{x},{y}]: '{clean_text}' (saved to cache)")
        else:
            logger.debug(f"⚠️ OCR MISS [{x},{y}]: Empty result, not caching.")
        
        return clean_text

    except Exception as e:
        logger.error(f"Ошибка в read_screen_text_cached: {e}")
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
    
    raw_text = read_screen_text_cached(
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
        
        # --- Кроп краев, чтобы убрать рамки и лишние линии (0% по бокам, 10% сверху/снизу) ---
        h, w = img_np.shape
        dy = int(h * 0.10)
        dx = 0
        img_np = img_np[dy:h-dy, 0:w]
        
        # Convert back to PIL for Tesseract
        final_img = Image.fromarray(img_np)
        _save_debug_ocr_image(final_img, "qty", f"_x{area['x']}_y{area['y']}")

        # 6. OCR (PSM 7 - Single text line, Numeric Whitelist)
        whitelist = "0123456789"
        config = f'--psm 7 -c tessedit_char_whitelist={whitelist}'
        
        # --- CACHING FOR QTY ---
        # Grayscale for stability
        gray_img = ImageOps.grayscale(final_img)
        img_data = gray_img.tobytes()
        img_hash = hashlib.md5(img_data).hexdigest()
        
        area_key = (area['x'], area['y'], area['w'], area['h'], "qty") # 'qty' suffix to distinguish from normal text
        cached_text = _global_ocr_cache.get(area_key, img_hash)
        if cached_text is not None:
             logger.debug(f"🚀 OCR Qty Cache HIT [{area['x']},{area['y']}]: '{cached_text}'")
             return parse_price(cached_text, allow_low_values=True) or 0
             
        text = pytesseract.image_to_string(final_img, lang='eng', config=config)
        clean_text = text.strip()
        
        if clean_text:
            _global_ocr_cache.update(area_key, img_hash, clean_text)
            logger.debug(f"📥 OCR Qty Cache MISS [{area['x']},{area['y']}]: '{clean_text}'")
        else:
             logger.debug(f"⚠️ OCR Qty MISS [{area['x']},{area['y']}]: Empty result, not caching.")
        
        # Parse
        val = parse_price(clean_text, allow_low_values=True)
        return val if val is not None else 0
        
    except Exception as e:
        logger.error(f"Ошибка OCR (Qty): {e}")
        return 0

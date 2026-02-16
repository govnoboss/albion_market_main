import os
from typing import Tuple, Dict, Any
from PIL import Image, ImageGrab
from ..utils.logger import get_logger
from ..utils.image_utils import compare_images
from ..utils.ocr import read_screen_text, is_ocr_available

class ScreenValidator:
    """Класс для проверки состояния экрана (Валидация)"""
    
    @staticmethod
    def check_market_open(area: Dict[str, int]) -> Tuple[bool, str]:
        """
        Проверяет, открыто ли окно рынка.
        (Только по наличию названия города в заголовке)
        """
        if not area:
            return True, "Зона проверки названия рынка не задана (Skip)"

        # 2. OCR Only (Pixel Check removed by user request)
        if not is_ocr_available():
            return True, "OCR N/A (Skip Check)"

        try:
            # Читаем текст (Rus+Eng for Black Market compatibility)
            text = read_screen_text(area['x'], area['y'], area['w'], area['h'], lang='rus+eng')
            text_clean = text.strip().lower()
            
            # Список городов (и ключевых слов заголовка, если вдруг Black Market)
            valid_indicators = [
                "bridgewatch", "martlock", "lymhurst", "thetford", 
                "fort sterling", "caerleon", "brecilien", "black market", 
                "market", "черный рынок", "рынок"
            ]
            
            # Проверяем нечеткое вхождение
            found = [k for k in valid_indicators if k in text_clean]
            
            if found:
                return True, f"Market Open Validated: '{text_clean}' (Found: {found[0]})"
            
            # Если текст слишком короткий (пусто), считаем что закрыто
            if len(text_clean) < 3:
                 return False, f"Market Closed (Empty Text): '{text_clean}'"
                 
            # Если текст есть, но не город?
            # Возможно это другое окно.
            return False, f"Market header mismatch: '{text_clean}' not in cities list"
            
        except Exception as e:
            return True, f"OCR Error: {e}"

    @staticmethod
    def check_item_menu(area: Dict[str, int]) -> Tuple[bool, str]:
        """
        Проверяет, открыто ли меню предмета (детали лота).
        """
        if not area:
            # Если зона не задана, считаем что проверка отключена (True), но с warn
            return True, "Зона item_menu_check не задана (Skip)"

        # 1. Pixel Match
        from ..utils.paths import get_app_root
        resources_dir = get_app_root() / "resources"
        ref_path = resources_dir / "ref_item_menu_check.png"
        
        if os.path.exists(ref_path):
            try:
                ref_img = Image.open(ref_path)
                bbox = (area['x'], area['y'], area['x'] + area['w'], area['y'] + area['h'])
                current_img = ImageGrab.grab(bbox=bbox)
                
                if ref_img.size != current_img.size:
                     current_img = current_img.resize(ref_img.size)

                rms = compare_images(ref_img, current_img)
                threshold = 30.0
                
                if rms < threshold:
                    return True, f"Image Match OK (RMS: {rms:.2f})"
                else:
                    return False, f"Image Mismatch (RMS: {rms:.2f} > {threshold})"
            except Exception as e:
                 get_logger().error(f"Image Method Error (ItemMenu): {e}")
        
        # 2. OCR Fallback
        if not is_ocr_available():
            return True, "OCR N/A, Ref Missing"

        try:
            text = read_screen_text(area['x'], area['y'], area['w'], area['h'])
            text_lower = text.lower()
            # Проверяем ключевые слова, характерные для меню предмета
            keywords = [
                "tier", "quality", "buy", "sell", "enchant", "stats", "load", "weight", "item", # Eng
                "тир", "качество", "купить", "продать", "заказ", "вес", "зачарование" # Rus
            ]
            
            found = [k for k in keywords if k in text_lower]
            if found:
                return True, f"OCR Match OK ('{found[0]}' found)"
            
            return False, f"OCR Mismatch (Text: '{text}')"
            
        except Exception as e:
            return True, f"OCR Error: {e}"

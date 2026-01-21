import os
from typing import Tuple, Dict, Any
from PIL import Image, ImageGrab
from ..utils.logger import get_logger
from ..utils.image_utils import compare_images_rms
from ..utils.ocr import read_screen_text, is_ocr_available

class ScreenValidator:
    """Класс для проверки состояния экрана (Валидация)"""
    
    @staticmethod
    def check_market_open(area: Dict[str, int]) -> Tuple[bool, str]:
        """
        Проверяет, открыто ли окно рынка.
        Возвращает: (is_open, details_message)
        """
        if not area:
            return True, "Зона проверки не задана"

        # 1. Pixel Match (Prioritized)
        resources_dir = os.path.join(os.getcwd(), "resources")
        ref_path = os.path.join(resources_dir, "ref_market_menu_check.png")
        
        if os.path.exists(ref_path):
            try:
                ref_img = Image.open(ref_path)
                bbox = (area['x'], area['y'], area['x'] + area['w'], area['y'] + area['h'])
                current_img = ImageGrab.grab(bbox=bbox)
                
                # Сравниваем размеры, на всякий случай
                if ref_img.size != current_img.size:
                     current_img = current_img.resize(ref_img.size)

                rms = compare_images_rms(ref_img, current_img)
                threshold = 30.0 # Порог
                
                if rms < threshold:
                    return True, f"Image Match OK (RMS: {rms:.2f})"
                else:
                    return False, f"Image Mismatch (RMS: {rms:.2f} > {threshold})"
            except Exception as e:
                get_logger().error(f"Image Method Error: {e}")
                # Fallback to OCR
        
        # 2. OCR Fallback
        if not is_ocr_available():
            return True, "OCR N/A, Image Ref Missing"

        try:
            text = read_screen_text(area['x'], area['y'], area['w'], area['h'])
            text_lower = text.lower()
            keywords = ["рынок", "market", "order", "ордер", "купить", "покупка", "buy"]
            
            found = [k for k in keywords if k in text_lower]
            if found:
                return True, f"OCR Match OK ('{found[0]}' found in '{text}')"
            
            return False, f"OCR Mismatch (Text: '{text}')"
            
        except Exception as e:
            return True, f"OCR Error: {e}"

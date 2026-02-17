import cv2
import numpy as np
import pyautogui
from PIL import Image, ImageGrab
from typing import Optional, Tuple, Dict
from ..utils.ocr import read_screen_text, is_ocr_available
from ..utils.logger import get_logger

logger = get_logger()

class StateDetector:
    """
    Класс для обнаружения специфических состояний игры (вылеты, ошибки).
    Работает независимо от разрешения экрана, используя OCR в центральной области.
    """

    @staticmethod
    def get_center_region(width_pct: float = 0.4, height_pct: float = 0.3) -> Dict[str, int]:
        """
        Рассчитывает центральную область экрана на основе процентов.
        """
        screen_w, screen_h = pyautogui.size()
        
        w = int(screen_w * width_pct)
        h = int(screen_h * height_pct)
        x = int((screen_w - w) / 2)
        y = int((screen_h - h) / 2)
        
        return {'x': x, 'y': y, 'w': w, 'h': h}

    @staticmethod
    def is_disconnected() -> Tuple[bool, str]:
        """
        Проверяет, активно ли окно ошибки подключения (с кнопкой ОК).
        """
        if not is_ocr_available():
            return False, "OCR N/A"

        region = StateDetector.get_center_region(0.7, 0.6)
        
        try:
            text = read_screen_text(region['x'], region['y'], region['w'], region['h'], lang='rus+eng')
            text_lower = text.lower()

            # Ключевые слова именно для окна с "ОК"
            popup_keywords = [
                "ошибка подключения", "повторите попытку", 
                "connection error", "disconnected",
                "вход на сервер", "недоступен"
            ]
            button_keywords = ["ok", "ок", "0k", "qk"]

            found_error = any(k in text_lower for k in popup_keywords)
            found_button = any(k in text_lower for k in button_keywords)

            if found_error:
                return True, f"Detected Disconnection Popup: '{text[:100]}...'"
            
            return False, f"Not a Popup (OCR: '{text[:50]}...')"
            
        except Exception as e:
            logger.error(f"Error in StateDetector (is_disconnected): {e}")
            return False, str(e)

    @staticmethod
    def is_reconnect_screen() -> Tuple[bool, str]:
        """
        Проверяет, находимся ли мы на экране "Информация" с кнопкой "Переподключение".
        """
        if not is_ocr_available():
            return False, "OCR N/A"

        region = StateDetector.get_center_region(0.7, 0.7)
        
        try:
            text = read_screen_text(region['x'], region['y'], region['w'], region['h'], lang='rus+eng')
            text_lower = text.lower()

            # Ключевые слова для экрана переподключения
            reconnect_keywords = [
                "информация", "переподключение", "reconnect", 
                "временно недоступен", "перезагрузка", "maintenance"
            ]

            if any(k in text_lower for k in reconnect_keywords):
                return True, f"Detected Reconnect Screen: '{text[:100]}...'"
            
            return False, f"Not a Reconnect Screen"
            
        except Exception as e:
            logger.error(f"Error in StateDetector (is_reconnect_screen): {e}")
            return False, str(e)

    @staticmethod
    def find_ok_button_coords() -> Optional[Tuple[int, int]]:
        """Координаты кнопки OK (52% высоты)"""
        screen_w, screen_h = pyautogui.size()
        return (int(screen_w / 2), int(screen_h * 0.52))

    @staticmethod
    def find_reconnect_button_coords() -> Optional[Tuple[int, int]]:
        """Координаты кнопки Переподключение (65% высоты)"""
        screen_w, screen_h = pyautogui.size()
        # На экране информации кнопка "Переподключение" находится заметно ниже центра.
        # Судя по скриншоту, это примерно 65-67% высоты экрана. 
        return (int(screen_w / 2), int(screen_h * 0.66))

    @staticmethod
    def is_main_menu() -> Tuple[bool, str]:
        """
        Проверяет, находимся ли мы в главном меню (выбор персонажа).
        Использует эталонные изображения bm_char1_area / bm_char2_area.
        """
        from ..utils.config import get_config
        from ..utils.paths import get_app_root
        from ..utils.image_utils import find_image_on_screen
        import os

        config = get_config()
        resources_dir = get_app_root() / "resources"
        
        # Проверяем наличие персонажей на экране через Template Matching
        missing_refs = []
        for key in ["bm_char1_area", "bm_char2_area"]:
            ref_path = resources_dir / f"ref_{key}.png"
            if os.path.exists(ref_path):
                found = find_image_on_screen(str(ref_path), confidence=0.85)
                if found:
                    return True, f"Detected Main Menu: Found avatar {key}"
            else:
                missing_refs.append(key)
        
        if len(missing_refs) == 2:
            return False, "Main Menu detection failed: Character icon references are missing or not set!"
                    
        return False, "Main Menu not detected (Character icons not found on screen)"

    @staticmethod
    def get_login_button() -> Optional[Tuple[int, int]]:
        """Возвращает координаты кнопки 'Войти' из конфига (bm_login_btn)"""
        from ..utils.config import get_config
        return get_config().get_coordinate("bm_login_btn")

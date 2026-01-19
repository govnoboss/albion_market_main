"""
Albion Market Bot v3.0 - OCR Engine

Модуль распознавания текста с экрана через Tesseract.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageGrab, ImageEnhance, ImageFilter, ImageOps
import pytesseract

from config import TESSERACT_PATH, SCREENSHOTS_DIR

# Настройка Tesseract
if TESSERACT_PATH:
    pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_PATH)

logger = logging.getLogger(__name__)


class OCREngine:
    """Движок OCR для распознавания текста и цифр."""
    
    def __init__(self, save_screenshots: bool = False):
        """
        Args:
            save_screenshots: Сохранять скриншоты для отладки.
        """
        self.save_screenshots = save_screenshots
        self._screenshot_counter = 0
    
    def scan_digits(self, region: Tuple[int, int, int, int]) -> int:
        """
        Распознаёт только цифры в указанной области.
        
        Args:
            region: (left, top, width, height)
        
        Returns:
            Распознанное число или 0 при ошибке.
        """
        try:
            bbox = self._region_to_bbox(region)
            screenshot = ImageGrab.grab(bbox=bbox)
            
            # Предобработка для улучшения распознавания
            processed = self._preprocess_for_digits(screenshot)
            
            if self.save_screenshots:
                self._save_screenshot(processed, "digits")
            
            config = '--psm 7 -c tessedit_char_whitelist=0123456789'
            text = pytesseract.image_to_string(processed, config=config)
            
            # Очистка результата
            digits = ''.join(c for c in text if c.isdigit())
            
            if digits:
                return int(digits)
            return 0
            
        except Exception as e:
            logger.error(f"OCR digits error: {e}")
            return 0
    
    def scan_text(self, region: Tuple[int, int, int, int], lang: str = 'rus') -> str:
        """
        Распознаёт текст в указанной области.
        
        Args:
            region: (left, top, width, height)
            lang: Язык распознавания ('rus', 'eng')
        
        Returns:
            Распознанный текст (в нижнем регистре).
        """
        try:
            bbox = self._region_to_bbox(region)
            screenshot = ImageGrab.grab(bbox=bbox)
            
            # Предобработка для текста
            processed = self._preprocess_for_text(screenshot)
            
            if self.save_screenshots:
                self._save_screenshot(processed, "text")
            
            config = '--psm 7'
            text = pytesseract.image_to_string(processed, lang=lang, config=config)
            
            return text.strip().lower().replace('\n', ' ')
            
        except Exception as e:
            logger.error(f"OCR text error: {e}")
            return ""
    
    def scan_with_confidence(
        self, 
        region: Tuple[int, int, int, int]
    ) -> list[Tuple[str, int]]:
        """
        Распознаёт текст с информацией о достоверности.
        
        Args:
            region: (left, top, width, height)
        
        Returns:
            Список кортежей (текст, достоверность%).
        """
        try:
            bbox = self._region_to_bbox(region)
            screenshot = ImageGrab.grab(bbox=bbox)
            processed = self._preprocess_for_digits(screenshot)
            
            if self.save_screenshots:
                self._save_screenshot(processed, "confidence")
            
            config = '--psm 7 -c tessedit_char_whitelist=0123456789'
            data = pytesseract.image_to_data(
                processed, 
                output_type=pytesseract.Output.DICT,
                config=config
            )
            
            results = []
            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                conf = int(data['conf'][i])
                if text and conf > -1:
                    results.append((text, conf))
            
            return results
            
        except Exception as e:
            logger.error(f"OCR with confidence error: {e}")
            return []
    
    def _region_to_bbox(self, region: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        """Конвертация (left, top, width, height) в (left, top, right, bottom)."""
        left, top, width, height = region
        return (left, top, left + width, top + height)
    
        return sharpened
    
    def _preprocess_for_digits(self, image: Image.Image) -> Image.Image:
        """
        Предобработка: Grayscale -> Invert -> Threshold -> Resize.
        Tesseract лучше читает черные цифры на белом фоне.
        """
        # 1. Grayscale
        gray = image.convert('L')
        
        # 2. Invert (белый текст на темном фоне -> черный на белом)
        inverted = ImageOps.invert(gray)
        
        # 3. Threshold (бинарное изображение)
        # Пиксели светлее 128 становятся 255 (белыми), остальные 0 (черными)
        threshold = 100  # Можно подбирать экспериментально
        binary = inverted.point(lambda p: 255 if p > threshold else 0)
        
        # 4. Resize (увеличение для мелкого текста)
        width, height = binary.size
        if height < 30:
            scale = 3  # Увеличиваем в 3 раза
            new_size = (width * scale, height * scale)
            processed = binary.resize(new_size, Image.Resampling.LANCZOS)
        else:
            processed = binary
            
        return processed
    
    def _preprocess_for_text(self, image: Image.Image) -> Image.Image:
        """Предобработка изображения для распознавания текста."""
        # Конвертация в градации серого
        gray = image.convert('L')
        
        # Мягкое увеличение контраста
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(1.5)
        
        return enhanced
    
    def _save_screenshot(self, image: Image.Image, prefix: str) -> Path:
        """Сохранение скриншота для отладки."""
        self._screenshot_counter += 1
        filename = f"{prefix}_{self._screenshot_counter:04d}.png"
        path = SCREENSHOTS_DIR / filename
        image.save(path)
        logger.debug(f"Screenshot saved: {path}")
        return path


# Глобальный экземпляр
_engine: Optional[OCREngine] = None


def get_ocr_engine(save_screenshots: bool = False) -> OCREngine:
    """Получение глобального экземпляра OCR движка."""
    global _engine
    if _engine is None:
        _engine = OCREngine(save_screenshots=save_screenshots)
    return _engine


def scan_price(region: Tuple[int, int, int, int]) -> int:
    """Быстрая функция для распознавания цены."""
    return get_ocr_engine().scan_digits(region)


def scan_text(region: Tuple[int, int, int, int], lang: str = 'rus') -> str:
    """Быстрая функция для распознавания текста."""
    return get_ocr_engine().scan_text(region, lang)


def scan_quantity(region: Tuple[int, int, int, int]) -> int:
    """Быстрая функция для распознавания количества."""
    return get_ocr_engine().scan_digits(region)

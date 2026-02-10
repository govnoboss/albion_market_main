from PIL import Image, ImageChops, ImageStat
import math

def find_image_on_screen(template_path: str, confidence: float = 0.8, region=None):
    """
    Поиск изображения на экране (Template Matching).
    Возвращает координаты центра (x, y) или None.
    
    Uses pyautogui.locateCenterOnScreen
    """
    import pyautogui
    try:
        # Pyscreeze/PyAutoGUI requires opencv-python for confidence support.
        # If strict match, confidence is ignored by some versions or defaults to exact.
        # We try with confidence first.
        point = pyautogui.locateCenterOnScreen(template_path, confidence=confidence, region=region, grayscale=True)
        return point
    except Exception as e:
        # Fallback without confidence if it fails (e.g. no opencv)
        # print(f"Template match error (first try): {e}")
        try:
             point = pyautogui.locateCenterOnScreen(template_path, region=region, grayscale=True)
             return point
        except Exception as e2:
             print(f"Template match error: {e2}")
             return None

def compare_images(img1: Image, img2: Image) -> float:
    """
    Сравнение двух изображений (RMS Difference).
    Возвращает число: 0 = абсолютно одинаковые.
    Чем больше число, тем больше разница.
    """
    if img1.size != img2.size:
         img2 = img2.resize(img1.size)
    
    diff = ImageChops.difference(img1, img2)
    h = diff.histogram()
    sq = (value*((idx%256)**2) for idx, value in enumerate(h))
    sum_of_squares = sum(sq)
    rms = math.sqrt(sum_of_squares/float(img1.size[0] * img1.size[1]))
    return rms

def find_image_on_screens(template: Image, screen: Image) -> float:
    """
    Алиас для compare_images (так как в коде bot.py 
    используется find_image_on_screens для сравнения snapshot-ов)
    """
    return compare_images(template, screen)

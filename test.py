import pytesseract
import mss
import mss.tools
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def ocr_region(left, top, width, height):
    """
    Делает OCR указанного региона экрана и выводит текст в консоль.

    :param left: координата X верхнего левого угла
    :param top: координата Y верхнего левого угла
    :param width: ширина региона
    :param height: высота региона
    """
    with mss.mss() as sct:
        region = {"left": left, "top": top, "width": width, "height": height}
        screenshot = sct.grab(region)

        # Конвертируем в формат PIL для OCR
        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)

        # Распознаём текст
        text = pytesseract.image_to_string(img, lang="rus")  # можешь поменять lang
        print("Распознанный текст:", text.strip())

# Пример вызова
ocr_region(662, 411, 244, 45)

from PIL import Image, ImageChops
import math
import operator
from functools import reduce

def compare_images_rms(img1: Image.Image, img2: Image.Image) -> float:
    """
    Сравнивает два изображения и возвращает среднеквадратичную ошибку (RMS).
    0 = идентичные изображения.
    Чем больше число, тем больше различие.
    """
    # 1. Приводим к одному размеру (если отличаются)
    if img1.size != img2.size:
        # Если размеры разные, сравнение "пиксель в пиксель" невозможно напрямую.
        # Для валидации UI мы ожидаем, что размеры совпадают (одна и та же зона).
        # Но если нет - ресайзим img2 к img1.
        img2 = img2.resize(img1.size)

    # 2. Конвертируем в RGB (на случай если одна RGBA или Grayscale)
    img1 = img1.convert('RGB')
    img2 = img2.convert('RGB')

    # 3. Вычисляем разницу
    diff = ImageChops.difference(img1, img2)
    h = diff.histogram()

    # 4. Считаем RMS
    sq = (value * ((idx % 256) ** 2) for idx, value in enumerate(h))
    sum_of_squares = sum(sq)
    rms = math.sqrt(sum_of_squares / float(img1.size[0] * img1.size[1]))

    return rms

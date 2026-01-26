from PIL import Image, ImageChops, ImageStat

def compare_images(img1: Image.Image, img2: Image.Image) -> float:
    """
    Сравнивает два изображения и возвращает среднюю разницу (Mean Pixel Difference).
    0.0 = Идентичны
    255.0 = Полностью противоположны
    
    Logic:
    1. Resize target to reference size
    2. RGB conversion
    3. Calculate Absolute Difference
    4. Return Mean value of the difference
    """
    # 1. Resize if needed (Force fit)
    if img1.size != img2.size:
        img2 = img2.resize(img1.size)

    # 2. Convert
    img1 = img1.convert('RGB')
    img2 = img2.convert('RGB')

    # 3. Difference
    diff = ImageChops.difference(img1, img2)
    
    # 4. Calculate Mean Level
    stat = ImageStat.Stat(diff)
    # stat.mean returns [r, g, b]. We take average of them.
    mean_diff = sum(stat.mean) / len(stat.mean)
    
    return mean_diff

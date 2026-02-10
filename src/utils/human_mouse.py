
import time
import random
import math
import pyautogui
import numpy as np

def _get_control_points(start_x, start_y, end_x, end_y, knots_count=2):
    """
    Генерирует контрольные точки для кривой Безье.
    Чем больше дистанция, тем больше может быть отклонение.
    """
    points = [[start_x, start_y]]
    
    dist = math.hypot(end_x - start_x, end_y - start_y)
    
    # Максимальное отклонение (чем дальше ехать, тем больше дуга)
    # Но не слишком много, чтобы не "гуляло" по всему экрану
    max_offset = min(dist * 0.1, 50.0) 
    
    for i in range(1, knots_count + 1):
        # Линейная интерполяция для базы
        t = i / (knots_count + 1)
        base_x = start_x + (end_x - start_x) * t
        base_y = start_y + (end_y - start_y) * t
        
        # Случайное смещение (Noise)
        offset_x = random.uniform(-max_offset, max_offset)
        offset_y = random.uniform(-max_offset, max_offset)
        
        points.append([base_x + offset_x, base_y + offset_y])
        
    points.append([end_x, end_y])
    return np.array(points)

def _bezier_curve(points, n=100):
    """
    Генерация точек кривой Безье по контрольным точкам.
    points: массив контрольных точек [[x,y], ...]
    n: количество точек в итоговой кривой
    """
    P = points
    n_points = len(P)
    
    # t = 0..1
    t = np.linspace(0, 1, n)
    
    # B(t) = Sum (Bi,n(t) * Pi)
    # Где Bi,n - полиномы Бернштейна
    
    curve = np.zeros((n, 2))
    
    for i in range(n_points):
        # Binomial coefficient
        binom = math.comb(n_points - 1, i)
        
        # Bernstein basis polynomial
        bernstein = binom * (t ** i) * ((1 - t) ** (n_points - 1 - i))
        
        # Add contribution of point P[i]
        curve += np.outer(bernstein, P[i])
        
    return curve

def move_mouse_human(target_x, target_y, duration=None):
    """
    Перемещение мыши по человекоподобной кривой.
    """
    start_x, start_y = pyautogui.position()
    
    # Если дистанция очень маленькая, просто двигаем линейно (микро-доводка)
    dist = math.hypot(target_x - start_x, target_y - start_y)
    if dist < 10:
        if duration is None: duration = random.uniform(0.05, 0.1)
        pyautogui.moveTo(target_x, target_y, duration=duration)
        return

    # Расчет длительности, если не задана
    if duration is None:
        # Чем дальше, тем дольше, но с затуханием (логарифмически или корнем)
        # Базовая скорость: 1800px за ~0.5-0.8 сек (Быстрее)
        min_duration = 0.08
        calc_duration = (dist / 1800.0) + random.uniform(0.0, 0.1)
        duration = max(min_duration, calc_duration)
        
    # Количество шагов (чем дольше, тем больше точек)
    # PyAutoGUI по умолчанию делает паузы, поэтому too many steps может тормозить.
    # Оптимально: 60-100 шагов в секунду
    steps = int(duration * 60)
    steps = max(10, min(steps, 200)) # Clamping
    
    # Генерируем 2 контрольные точки (Cubic Bezier)
    knots = _get_control_points(start_x, start_y, target_x, target_y, knots_count=2)
    path = _bezier_curve(knots, n=steps)
    
    # Движение по точкам
    # Используем pyautogui.moveTo c duration=0 (мгновенно к точке), 
    # а задержку делаем сами через sleep для контроля ускорения
    
    # Простейшая реализация: равномерное движение по времени
    step_delay = duration / steps
    
    # PyAutoGUI safe-fail
    # pyautogui.PAUSE = 0 # Временно отключаем
    
    for point in path:
        pyautogui.moveTo(point[0], point[1], _pause=False)
        # Можно добавить микро-вариации задержки для имитации тремора скорости, но sleep(0) ненадежен
        time.sleep(step_delay)
        
    # Гарантированный довод в конечную точку
    pyautogui.moveTo(target_x, target_y, _pause=False)

import tkinter as tk
from tkinter import messagebox
import pytesseract
from PIL import ImageGrab
import pyautogui
import sys
from pathlib import Path
from pynput.keyboard import Key, Listener
from datetime import datetime

# Путь к Tesseract (обновите, если нужно)
tesseract_path = Path(r'C:\Program Files\Tesseract-OCR\tesseract.exe')
if not tesseract_path.exists():
    print(f"Ошибка: Tesseract не найден по пути {tesseract_path}")
    sys.exit(1)
pytesseract.pytesseract.tesseract_cmd = str(tesseract_path)

class OCRCaptureApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OCR Capture")
        self.root.geometry("300x200")

        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        self.capturing = False

        # Кнопка для старта захвата области
        self.capture_button = tk.Button(root, text="Захватить область", command=self.start_capture)
        self.capture_button.pack(pady=20)

        # Метки для отображения координат
        self.label = tk.Label(root, text="Координаты: Не выбрано")
        self.label.pack(pady=10)

        # Запуск глобального слушателя клавиш
        self.listener = Listener(on_press=self.on_press)
        self.listener.start()

    def start_capture(self):
        """Запускает процесс захвата области экрана."""
        self.capturing = True
        self.label.config(text="Зажмите левую кнопку мыши и выделите область...")
        self.root.withdraw()  # Скрываем окно во время захвата

        # Захват координат при зажатии и отпускании мыши
        screen_width, screen_height = pyautogui.size()
        self.screen = tk.Toplevel(self.root)
        self.screen.attributes('-fullscreen', True)
        self.screen.attributes('-alpha', 0.3)  # Полупрозрачный фон
        self.screen.config(bg='gray')

        self.canvas = tk.Canvas(self.screen, bg='gray', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)

        self.canvas.bind('<Button-1>', self.on_press_area)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)

    def on_press_area(self, event):
        """Фиксирует начальную точку при зажатии мыши."""
        self.start_x = self.screen.winfo_pointerx()
        self.start_y = self.screen.winfo_pointery()
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red')

    def on_drag(self, event):
        """Обновляет область выделения при движении мыши."""
        if self.start_x is not None and self.start_y is not None:
            self.end_x = self.screen.winfo_pointerx()
            self.end_y = self.screen.winfo_pointery()
            self.canvas.coords(self.rect, self.start_x, self.start_y, self.end_x, self.end_y)

    def on_release(self, event):
        """Фиксирует конечную точку и завершает захват."""
        if self.start_x is not None and self.start_y is not None:
            self.end_x = self.screen.winfo_pointerx()
            self.end_y = self.screen.winfo_pointery()
            self.canvas.delete(self.rect)
            self.screen.destroy()
            self.root.deiconify()  # Показываем окно обратно

            # Корректируем координаты
            left = min(self.start_x, self.end_x)
            top = min(self.start_y, self.end_y)
            right = max(self.start_x, self.end_x)
            bottom = max(self.start_y, self.end_y)

            self.label.config(text=f"Координаты: ({left}, {top}, {right}, {bottom})")
            self.start_x, self.start_y, self.end_x, self.end_y = left, top, right, bottom
            self.capturing = False

    def on_press(self, key):
        """Обработчик глобальных нажатий клавиш."""
        try:
            if key == Key.f5:  # Реакция на F5
                self.perform_ocr()
        except AttributeError:
            pass  # Игнорируем другие клавиши

    def perform_ocr(self):
        """Выполняет OCR на выбранной области с выводом confidence и сохранением скриншота."""
        if self.start_x is None or self.end_x is None:
            messagebox.showwarning("Предупреждение", "Сначала выберите область!")
            return

        try:
            # Захватываем область экрана
            screenshot = ImageGrab.grab(bbox=(self.start_x, self.start_y, self.end_x, self.end_y))
            
            # Сохраняем скриншот для отладки
            screenshots_dir = Path(__file__).parent / 'screenshots'
            screenshots_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = screenshots_dir / f"screenshot_{timestamp}_{self.start_x}_{self.start_y}.png"
            screenshot.save(screenshot_path)
            print(f"Скриншот сохранен: {screenshot_path}")
            
            # Выполняем OCR с детализированными данными
            data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT, config='--psm 7 -c tessedit_char_whitelist=0123456789')
            
            # Фильтруем результаты, где есть текст
            results = []
            for i in range(len(data['text'])):
                if data['text'][i].strip() and int(data['conf'][i]) > -1:  # -1 означает отсутствие уверенности
                    confidence = int(data['conf'][i])
                    text = data['text'][i].strip()
                    results.append((text, confidence))
            
            # Выводим все результаты с confidence
            if results:
                for text, conf in results:
                    print(f"[{pyautogui.position()}] Результат OCR: '{text}', Confidence: {conf}%")
            else:
                print(f"[{pyautogui.position()}] Результат OCR: 'Нет данных', Confidence: N/A")
                
        except Exception as e:
            print(f"Ошибка при выполнении OCR: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = OCRCaptureApp(root)
    root.mainloop()
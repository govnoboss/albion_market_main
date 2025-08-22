import pandas as pd
import tkinter as tk
import numpy as np
import pyautogui
import time
import keyboard
import pytesseract
import logging
import random
import sys
import threading
import os
import json
import cv2
import csv
import requests
from PIL import ImageGrab
from tkinter import messagebox, ttk
from pynput import mouse
from pathlib import Path
from datetime import datetime
from seller import run_selling_cycle

# Set up logging
logging.basicConfig(filename='log.txt', level=logging.INFO, format='%(asctime)s - %(message)s')

# URL Path to Excel
url = "https://docs.google.com/spreadsheets/d/1D5MmKgJUaV00Owa3ILBiIg-2Jpu4ZezTkYuP1pJrSWM/export?format=xlsx&id=1D5MmKgJUaV00Owa3ILBiIg-2Jpu4ZezTkYuP1pJrSWM&gid=0"

# Path to Tesseract (update if necessary)
try:
    tesseract_path = Path(r'C:\Program Files\Tesseract-OCR\tesseract.exe')
    if not tesseract_path.exists():
        raise FileNotFoundError("Tesseract.exe not found at the specified path.")
    pytesseract.pytesseract.tesseract_cmd = str(tesseract_path)
except FileNotFoundError as e:
    messagebox.showerror("Ошибка Tesseract", f"Пожалуйста, убедитесь, что Tesseract установлен и путь к нему указан верно.\n{e}")
    sys.exit()

# Disable pyautogui failsafe for better control
pyautogui.FAILSAFE = False

# Create screenshots directory
screenshots_dir = Path(__file__).parent / 'screenshots'
screenshots_dir.mkdir(exist_ok=True)

class MarketBotGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Albion Online Buyer Script v2.0")
        self.root.resizable(False, False)
        self.sell_in_progress = False
        
        # Make window always on top initially
        self.root.attributes('-topmost', True)
        
        # Capture state
        self.capturing = False
        self.capture_type = None
        self.mouse_listener = None
        self.region_start = None
        
        # Script state
        self.script_running = False
        self.script_thread = None
        self.log_entries = []
        self.skip_item = False
        
        # Pause state
        self.paused = False
        self.pause_event = threading.Event()
        self.pause_event.set()  # Initially not paused
        
        self.setup_gui()
        self.load_settings()
        
        
    def setup_gui(self):
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Coordinate inputs
        coords_frame = ttk.LabelFrame(main_frame, text="Координаты", padding="5")
        coords_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Search coordinates
        ttk.Label(coords_frame, text="Search X:").grid(row=0, column=0, sticky=tk.W)
        self.search_x_entry = ttk.Entry(coords_frame, width=10)
        self.search_x_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(coords_frame, text="Search Y:").grid(row=0, column=2, sticky=tk.W, padx=(10,0))
        self.search_y_entry = ttk.Entry(coords_frame, width=10)
        self.search_y_entry.grid(row=0, column=3, padx=5)
        
        self.capture_search_btn = ttk.Button(coords_frame, text="Захватить поиск", 
                                           command=self.start_capture_search)
        self.capture_search_btn.grid(row=0, column=4, padx=5)
        
        # Clear coordinates
        ttk.Label(coords_frame, text="Clear X:").grid(row=1, column=0, sticky=tk.W)
        self.clear_x_entry = ttk.Entry(coords_frame, width=10)
        self.clear_x_entry.grid(row=1, column=1, padx=5)
        
        ttk.Label(coords_frame, text="Clear Y:").grid(row=1, column=2, sticky=tk.W, padx=(10,0))
        self.clear_y_entry = ttk.Entry(coords_frame, width=10)
        self.clear_y_entry.grid(row=1, column=3, padx=5)

        self.capture_clear_btn = ttk.Button(coords_frame, text="Захватить очистку", 
                                           command=self.start_capture_clear)
        self.capture_clear_btn.grid(row=1, column=4, padx=5)
        
        # Buy coordinates
        ttk.Label(coords_frame, text="Buy X:").grid(row=2, column=0, sticky=tk.W)
        self.buy_x_entry = ttk.Entry(coords_frame, width=10)
        self.buy_x_entry.grid(row=2, column=1, padx=5)
        
        ttk.Label(coords_frame, text="Buy Y:").grid(row=2, column=2, sticky=tk.W, padx=(10,0))
        self.buy_y_entry = ttk.Entry(coords_frame, width=10)
        self.buy_y_entry.grid(row=2, column=3, padx=5)
        
        self.capture_buy_btn = ttk.Button(coords_frame, text="Захватить покупку", 
                                        command=self.start_capture_buy)
        self.capture_buy_btn.grid(row=2, column=4, padx=5)
        
        # Confirm coordinates
        ttk.Label(coords_frame, text="Confirm X:").grid(row=3, column=0, sticky=tk.W)
        self.confirm_x_entry = ttk.Entry(coords_frame, width=10)
        self.confirm_x_entry.grid(row=3, column=1, padx=5)
        
        ttk.Label(coords_frame, text="Confirm Y:").grid(row=3, column=2, sticky=tk.W, padx=(10,0))
        self.confirm_y_entry = ttk.Entry(coords_frame, width=10)
        self.confirm_y_entry.grid(row=3, column=3, padx=5)
        
        self.capture_confirm_btn = ttk.Button(coords_frame, text="Захватить подтвер.", 
                                            command=self.start_capture_confirm)
        self.capture_confirm_btn.grid(row=3, column=4, padx=5)
        
        # Quantity input coordinates
        ttk.Label(coords_frame, text="Ввод кол-ва X:").grid(row=4, column=0, sticky=tk.W)
        self.quantity_x_entry = ttk.Entry(coords_frame, width=10)
        self.quantity_x_entry.grid(row=4, column=1, padx=5)
        
        ttk.Label(coords_frame, text="Ввод кол-ва Y:").grid(row=4, column=2, sticky=tk.W, padx=(10,0))
        self.quantity_y_entry = ttk.Entry(coords_frame, width=10)
        self.quantity_y_entry.grid(row=4, column=3, padx=5)
        
        self.capture_quantity_btn = ttk.Button(coords_frame, text="Захватить ввод кол-ва", 
                                               command=self.start_capture_quantity_input)
        self.capture_quantity_btn.grid(row=4, column=4, padx=5)
        
        # Buy Order coordinates
        ttk.Label(coords_frame, text="Buy Order X:").grid(row=5, column=0, sticky=tk.W)
        self.buy_order_x_entry = ttk.Entry(coords_frame, width=10)
        self.buy_order_x_entry.grid(row=5, column=1, padx=5)
        
        ttk.Label(coords_frame, text="Buy Order Y:").grid(row=5, column=2, sticky=tk.W, padx=(10,0))
        self.buy_order_y_entry = ttk.Entry(coords_frame, width=10)
        self.buy_order_y_entry.grid(row=5, column=3, padx=5)
        
        self.capture_buy_order_btn = ttk.Button(coords_frame, text="Захватить заказ на покупку", 
                                                command=self.start_capture_buy_order)
        self.capture_buy_order_btn.grid(row=5, column=4, padx=5)
        
        # Price per unit coordinates
        ttk.Label(coords_frame, text="Цена за штуку X:").grid(row=6, column=0, sticky=tk.W)
        self.price_per_unit_x_entry = ttk.Entry(coords_frame, width=10)
        self.price_per_unit_x_entry.grid(row=6, column=1, padx=5)
        
        ttk.Label(coords_frame, text="Цена за штуку Y:").grid(row=6, column=2, sticky=tk.W, padx=(10,0))
        self.price_per_unit_y_entry = ttk.Entry(coords_frame, width=10)
        self.price_per_unit_y_entry.grid(row=6, column=3, padx=5)
        
        self.capture_price_per_unit_btn = ttk.Button(coords_frame, text="Захватить цену за штуку", 
                                                     command=self.start_capture_price_per_unit)
        self.capture_price_per_unit_btn.grid(row=6, column=4, padx=5)
        
        # Minus coords
        ttk.Label(coords_frame, text="Минус X:").grid(row=7, column=0, sticky=tk.W)
        self.minus_x_entry = ttk.Entry(coords_frame, width=10)
        self.minus_x_entry.grid(row=7, column=1, padx=5)
        
        ttk.Label(coords_frame, text="Минус Y:").grid(row=7, column=2, sticky=tk.W, padx=(10,0))
        self.minus_y_entry = ttk.Entry(coords_frame, width=10)
        self.minus_y_entry.grid(row=7, column=3, padx=5)
        
        self.capture_minus_btn = ttk.Button(coords_frame, text="Захватить кнопку минуса", 
                                                     command=self.start_capture_minus)
        self.capture_minus_btn.grid(row=7, column=4, padx=5)
        
        # === Price region frame ===
        price_region_frame = ttk.LabelFrame(main_frame, text="Области цен для OCR", padding="5")
        price_region_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(price_region_frame, text='Координаты цены покупки').grid(row=0, column=0, columnspan=2, sticky=tk.W)
        ttk.Label(price_region_frame, text='Координаты общей цены продажи').grid(row=0, column=4, columnspan=2, sticky=tk.W)
        ttk.Label(price_region_frame, text='Координаты цены предмета продажи').grid(row=0, column=8, columnspan=2, sticky=tk.W)

        # Buy region
        ttk.Label(price_region_frame, text="Left:").grid(row=1, column=0, sticky=tk.W)
        self.left_entry = ttk.Entry(price_region_frame, width=10)
        self.left_entry.grid(row=1, column=1, padx=5, sticky=tk.W)

        ttk.Label(price_region_frame, text="Top:").grid(row=1, column=2, sticky=tk.W)
        self.top_entry = ttk.Entry(price_region_frame, width=10)
        self.top_entry.grid(row=1, column=3, padx=5, sticky=tk.W)

        ttk.Label(price_region_frame, text="Width:").grid(row=2, column=0, sticky=tk.W)
        self.width_entry = ttk.Entry(price_region_frame, width=10)
        self.width_entry.grid(row=2, column=1, padx=5, sticky=tk.W)

        ttk.Label(price_region_frame, text="Height:").grid(row=2, column=2, sticky=tk.W)
        self.height_entry = ttk.Entry(price_region_frame, width=10)
        self.height_entry.grid(row=2, column=3, padx=5, sticky=tk.W)

        self.capture_region_btn = ttk.Button(price_region_frame, text="Захватить область цены покупки", command=self.start_capture_region)
        self.capture_region_btn.grid(row=3, column=0, columnspan=4, pady=5)

        # Sell region
        ttk.Label(price_region_frame, text="Left:").grid(row=1, column=4, sticky=tk.W)
        self.sell_left_entry = ttk.Entry(price_region_frame, width=10)
        self.sell_left_entry.grid(row=1, column=5, padx=5, sticky=tk.W)

        ttk.Label(price_region_frame, text="Top:").grid(row=1, column=6, sticky=tk.W)
        self.sell_top_entry = ttk.Entry(price_region_frame, width=10)
        self.sell_top_entry.grid(row=1, column=7, padx=5, sticky=tk.W)

        ttk.Label(price_region_frame, text="Width:").grid(row=2, column=4, sticky=tk.W)
        self.sell_width_entry = ttk.Entry(price_region_frame, width=10)
        self.sell_width_entry.grid(row=2, column=5, padx=5, sticky=tk.W)

        ttk.Label(price_region_frame, text="Height:").grid(row=2, column=6, sticky=tk.W)
        self.sell_height_entry = ttk.Entry(price_region_frame, width=10)
        self.sell_height_entry.grid(row=2, column=7, padx=5, sticky=tk.W)

        self.capture_sell_region_btn = ttk.Button(price_region_frame, text="Захватить область цены продажи",command=self.start_capture_sell_region)
        self.capture_sell_region_btn.grid(row=3, column=4, columnspan=4, pady=5)

        # Sell item price region
        ttk.Label(price_region_frame, text="Left:").grid(row=1, column=8, sticky=tk.W)
        self.sell_item_price_left_entry = ttk.Entry(price_region_frame, width=10)
        self.sell_item_price_left_entry.grid(row=1, column=9, padx=5, sticky=tk.W)

        ttk.Label(price_region_frame, text="Top:").grid(row=1, column=10, sticky=tk.W)
        self.sell_item_price_top_entry = ttk.Entry(price_region_frame, width=10)
        self.sell_item_price_top_entry.grid(row=1, column=11, padx=5, sticky=tk.W)

        ttk.Label(price_region_frame, text="Width:").grid(row=2, column=8, sticky=tk.W)
        self.sell_item_price_width_entry = ttk.Entry(price_region_frame, width=10)
        self.sell_item_price_width_entry.grid(row=2, column=9, padx=5, sticky=tk.W)

        ttk.Label(price_region_frame, text="Height:").grid(row=2, column=10, sticky=tk.W)
        self.sell_item_price_height_entry = ttk.Entry(price_region_frame, width=10)
        self.sell_item_price_height_entry.grid(row=2, column=11, padx=5, sticky=tk.W)

        self.capture_sell_item_price_region_btn = ttk.Button(price_region_frame, text="Захватить область цены предмета продажи", command=self.start_capture_sell_item_price_region)
        self.capture_sell_item_price_region_btn.grid(row=3, column=8, columnspan=4, pady=5)
        
        # OCR region frame
        quantity_region_frame = ttk.LabelFrame(main_frame, text="Области для OCR", padding="5")
        quantity_region_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        ttk.Label(quantity_region_frame, text='Координаты количества предметов').grid(row=0, column=0, columnspan=2, sticky=tk.W)
        ttk.Label(quantity_region_frame, text='Координаты названия предмета').grid(row=0, column=4, columnspan=2, sticky=tk.W)
        
        # Quantity items
        ttk.Label(quantity_region_frame, text="Left:").grid(row=1, column=0, sticky=tk.W)
        self.left_q_entry = ttk.Entry(quantity_region_frame, width=10)
        self.left_q_entry.grid(row=1, column=1, padx=5, sticky=tk.W)
        
        ttk.Label(quantity_region_frame, text="Top:").grid(row=1, column=2, sticky=tk.W, padx=(10,0))
        self.top_q_entry = ttk.Entry(quantity_region_frame, width=10)
        self.top_q_entry.grid(row=1, column=3, padx=5, sticky=tk.W)
        
        ttk.Label(quantity_region_frame, text="Width:").grid(row=2, column=0, sticky=tk.W)
        self.width_q_entry = ttk.Entry(quantity_region_frame, width=10)
        self.width_q_entry.grid(row=2, column=1, padx=5, sticky=tk.W)
        
        ttk.Label(quantity_region_frame, text="Height:").grid(row=2, column=2, sticky=tk.W, padx=(10,0))
        self.height_q_entry = ttk.Entry(quantity_region_frame, width=10)
        self.height_q_entry.grid(row=2, column=3, padx=5, sticky=tk.W)
        
        self.capture_quantity_region_btn = ttk.Button(quantity_region_frame, text="Захватить область количества", 
                                                      command=self.start_capture_quantity_region)
        self.capture_quantity_region_btn.grid(row=3, column=0, columnspan=4, pady=5)
        
        # Item name
        ttk.Label(quantity_region_frame, text="Left:").grid(row=1, column=4, sticky=tk.W)
        self.left_item_name_entry = ttk.Entry(quantity_region_frame, width=10)
        self.left_item_name_entry.grid(row=1, column=5, padx=5, sticky=tk.W)
        
        ttk.Label(quantity_region_frame, text="Top:").grid(row=1, column=6, sticky=tk.W, padx=(10,0))
        self.top_item_name_entry = ttk.Entry(quantity_region_frame, width=10)
        self.top_item_name_entry.grid(row=1, column=7, padx=5, sticky=tk.W)
        
        ttk.Label(quantity_region_frame, text="Width:").grid(row=2, column=4, sticky=tk.W)
        self.width_item_name_entry = ttk.Entry(quantity_region_frame, width=10)
        self.width_item_name_entry.grid(row=2, column=5, padx=5, sticky=tk.W)
        
        ttk.Label(quantity_region_frame, text="Height:").grid(row=2, column=6, sticky=tk.W, padx=(10,0))
        self.height_item_name_entry = ttk.Entry(quantity_region_frame, width=10)
        self.height_item_name_entry.grid(row=2, column=7, padx=5, sticky=tk.W)
        
        self.capture_item_name_region_btn = ttk.Button(quantity_region_frame, text="Захватить название предмета", 
                                                      command=self.start_capture_item_name_region)
        self.capture_item_name_region_btn.grid(row=3, column=4, columnspan=4, pady=5)
        
        # Settings frame
        settings_frame = ttk.LabelFrame(main_frame, text="Настройки", padding="5")
        settings_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(settings_frame, text="Бюджет:").grid(row=0, column=0, sticky=tk.W)
        self.budget_entry = ttk.Entry(settings_frame, width=15)
        self.budget_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(settings_frame, text="Задержка действий (сек):").grid(row=1, column=0, sticky=tk.W)
        self.delay_entry = ttk.Entry(settings_frame, width=15)
        self.delay_entry.grid(row=1, column=1, padx=5)
        self.delay_entry.insert(0, "0.5")
        
        ttk.Label(settings_frame, text="С какой строки в таблице начать:").grid(row=2, column=0, sticky=tk.W)
        self.start_row_entry = ttk.Entry(settings_frame, width=15)
        self.start_row_entry.grid(row=2, column=1, padx=5)
        self.start_row_entry.insert(0, "1")
        
        ttk.Label(settings_frame, text="Общие затраты бюджета:").grid(row=3, column=0, sticky=tk.W)
        self.cumulative_spent_entry = ttk.Entry(settings_frame, width=15)
        self.cumulative_spent_entry.grid(row=3, column=1, padx=5)
        self.cumulative_spent_entry.insert(0, "0")
        
        # Status frame
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.status_label = ttk.Label(status_frame, text="Готов к работе", font=("Helvetica", 10, "bold"))
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        # Progress bar
        self.progress = ttk.Progressbar(status_frame, mode='determinate')
        self.progress.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=2)
        
        # Current item info label
        self.current_item_label = ttk.Label(status_frame, text="", justify=tk.LEFT, anchor=tk.W, wraplength=380)
        self.current_item_label.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Control buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=5, column=0, columnspan=2, pady=10)
        
        self.manual_btn = ttk.Button(control_frame, text="Ручная закупка", 
                                     command=self.start_manual)
        self.manual_btn.grid(row=0, column=0, padx=5)
        
        self.order_btn = ttk.Button(control_frame, text="Закупка ордерами", 
                                    command=self.start_order)
        self.order_btn.grid(row=0, column=1, padx=5)
        
        self.sell_btn = ttk.Button(control_frame, text="Продажа предметов", 
                                    command=self.start_sell)
        self.sell_btn.grid(row=0, column=2, padx=5)
        
        self.save_btn = ttk.Button(control_frame, text="Сохранить настройки", 
                                 command=self.save_settings)
        self.save_btn.grid(row=0, column=3, padx=5)
        
        # Instructions
        instructions_text = ("1. Захватите все координаты\n"
                           "2. Установите бюджет\n"
                           "3. Убедитесь, что файл table.xlsx существует\n\n"
                           "Горячие клавиши:\n"
                           "F3 - Пропустить текущий предмет\n"
                           "F4 - Пауза/Возобновление\n\n"
                           "Захватите область количества и координаты ввода кол-ва")
        instructions = ttk.Label(main_frame, text=instructions_text, foreground="gray")
        instructions.grid(row=6, column=0, columnspan=2, pady=10)
        
    def update_current_item_info(self, name="", value="", ocr_price="", bought="", store="", limit_price="",budget="", total_spent=""):
        """Update the current item label with provided info"""
        try:
            total_spent = int(float(total_spent)) if total_spent else 0
        except ValueError:
            total_spent = 0
        text = f"Текущий предмет: {name}\nЦена на Черном Рынке: {value}\nТекущая цена: {ocr_price} / {limit_price}\nКуплено: {bought} из {store}\nПотрачено: {int(float(total_spent))} из {budget}"
        self.current_item_label.config(text=text)
        self.root.update_idletasks()
        
    def update_status(self, message):
        """Обновление статуса в GUI"""
        self.status_label.config(text=message)
        self.root.update_idletasks()
        
    def start_capture_search(self):
        self.start_coordinate_capture('search')
        
    def start_capture_buy(self):
        self.start_coordinate_capture('buy')
        
    def start_capture_confirm(self):
        self.start_coordinate_capture('confirm')
        
    def start_capture_clear(self):
        self.start_coordinate_capture('clear')
        
    def start_capture_quantity_input(self):
        self.start_coordinate_capture('quantity_input')
        
    def start_capture_buy_order(self):
        self.start_coordinate_capture('buy_order')
        
    def start_capture_price_per_unit(self):
        self.start_coordinate_capture('price_per_unit')
        
    def start_capture_minus(self):
        self.start_coordinate_capture('minus')
        
    def start_capture_sell_region(self):
        if self.capturing:
            return
        self.capturing = True
        self.capture_type = 'sell_region'
        self.update_status("Нажмите и перетащите для выделения области цены продажи...")
        self.capture_sell_region_btn.config(command=self.cancel_capture)
        
        def on_click(x, y, button, pressed):
            if button == mouse.Button.left and pressed:
                self.region_start = (x, y)
                return True
            elif button == mouse.Button.left and not pressed and self.region_start:
                end_x, end_y = x, y
                start_x, start_y = self.region_start
                
                left = min(start_x, end_x)
                top = min(start_y, end_y)
                width = abs(end_x - start_x)
                height = abs(end_y - start_y)
                
                self.sell_left_entry.delete(0, tk.END)
                self.sell_left_entry.insert(0, str(left))
                self.sell_top_entry.delete(0, tk.END)
                self.sell_top_entry.insert(0, str(top))
                self.sell_width_entry.delete(0, tk.END)
                self.sell_width_entry.insert(0, str(width))
                self.sell_height_entry.delete(0, tk.END)
                self.sell_height_entry.insert(0, str(height))
                
                self.finish_capture(f"Область цены продажи захвачена: {width}x{height}")
                return False
        
        self.mouse_listener = mouse.Listener(on_click=on_click)
        self.mouse_listener.start()
        
    def start_capture_region(self):
        if self.capturing:
            return
        self.capturing = True
        self.capture_type = 'price_region'
        self.update_status("Нажмите и перетащите для выделения области цены покупки...")
        self.capture_region_btn.config(command=self.cancel_capture)
        
        def on_click(x, y, button, pressed):
            if button == mouse.Button.left and pressed:
                self.region_start = (x, y)
                return True
            elif button == mouse.Button.left and not pressed and self.region_start:
                end_x, end_y = x, y
                start_x, start_y = self.region_start
                
                left = min(start_x, end_x)
                top = min(start_y, end_y)
                width = abs(end_x - start_x)
                height = abs(end_y - start_y)
                
                self.left_entry.delete(0, tk.END)
                self.left_entry.insert(0, str(left))
                self.top_entry.delete(0, tk.END)
                self.top_entry.insert(0, str(top))
                self.width_entry.delete(0, tk.END)
                self.width_entry.insert(0, str(width))
                self.height_entry.delete(0, tk.END)
                self.height_entry.insert(0, str(height))
                
                self.finish_capture(f"Область цены покупки захвачена: {width}x{height}")
                return False
        
        self.mouse_listener = mouse.Listener(on_click=on_click)
        self.mouse_listener.start()

    def start_capture_sell_item_price_region(self):
        if self.capturing:
            return
        self.capturing = True
        self.capture_type = 'sell_item_price_region'
        self.update_status("Нажмите и перетащите для выделения области цены предмета продажи...")
        self.capture_sell_item_price_region_btn.config(command=self.cancel_capture)
        
        def on_click(x, y, button, pressed):
            if button == mouse.Button.left and pressed:
                self.region_start = (x, y)
                return True
            elif button == mouse.Button.left and not pressed and self.region_start:
                end_x, end_y = x, y
                start_x, start_y = self.region_start
                
                left = min(start_x, end_x)
                top = min(start_y, end_y)
                width = abs(end_x - start_x)
                height = abs(end_y - start_y)
                
                self.sell_item_price_left_entry.delete(0, tk.END)
                self.sell_item_price_left_entry.insert(0, str(left))
                self.sell_item_price_top_entry.delete(0, tk.END)
                self.sell_item_price_top_entry.insert(0, str(top))
                self.sell_item_price_width_entry.delete(0, tk.END)
                self.sell_item_price_width_entry.insert(0, str(width))
                self.sell_item_price_height_entry.delete(0, tk.END)
                self.sell_item_price_height_entry.insert(0, str(height))
                
                self.finish_capture(f"Область цены предмета продажи захвачена: {width}x{height}")
                return False
        
        self.mouse_listener = mouse.Listener(on_click=on_click)
        self.mouse_listener.start()
        
    def start_capture_quantity_region(self):
        if self.capturing:
            return
        self.capturing = True
        self.capture_type = 'quantity_region'
        self.update_status("Нажмите и перетащите для выделения области количества...")
        self.capture_quantity_region_btn.config(command=self.cancel_capture)
        
        def on_click(x, y, button, pressed):
            if button == mouse.Button.left and pressed:
                self.region_start = (x, y)
                return True
            elif button == mouse.Button.left and not pressed and self.region_start:
                end_x, end_y = x, y
                start_x, start_y = self.region_start
                
                left = min(start_x, end_x)
                top = min(start_y, end_y)
                width = abs(end_x - start_x)
                height = abs(end_y - start_y)
                
                self.left_q_entry.delete(0, tk.END)
                self.left_q_entry.insert(0, str(left))
                self.top_q_entry.delete(0, tk.END)
                self.top_q_entry.insert(0, str(top))
                self.width_q_entry.delete(0, tk.END)
                self.width_q_entry.insert(0, str(width))
                self.height_q_entry.delete(0, tk.END)
                self.height_q_entry.insert(0, str(height))
                
                self.finish_capture(f"Область количества захвачена: {width}x{height}")
                return False
        
        self.mouse_listener = mouse.Listener(on_click=on_click)
        self.mouse_listener.start()
        
    def start_capture_item_name_region(self):
        if self.capturing:
            return
        self.capturing = True
        self.capture_type = 'item_name_region'
        self.update_status("Нажмите и перетащите для выделения области названия предмета...")
        self.capture_item_name_region_btn.config(command=self.cancel_capture)
        
        def on_click(x, y, button, pressed):
            if button == mouse.Button.left and pressed:
                self.region_start = (x, y)
                return True
            elif button == mouse.Button.left and not pressed and self.region_start:
                end_x, end_y = x, y
                start_x, start_y = self.region_start
                
                left = min(start_x, end_x)
                top = min(start_y, end_y)
                width = abs(end_x - start_x)
                height = abs(end_y - start_y)
                
                self.left_item_name_entry.delete(0, tk.END)
                self.left_item_name_entry.insert(0, str(left))
                self.top_item_name_entry.delete(0, tk.END)
                self.top_item_name_entry.insert(0, str(top))
                self.width_item_name_entry.delete(0, tk.END)
                self.width_item_name_entry.insert(0, str(width))
                self.height_item_name_entry.delete(0, tk.END)
                self.height_item_name_entry.insert(0, str(height))
                
                self.finish_capture(f"Область названия предмета захвачена: {width}x{height}")
                return False
        
        self.mouse_listener = mouse.Listener(on_click=on_click)
        self.mouse_listener.start()
        
    def start_coordinate_capture(self, capture_type):
        if self.capturing:
            return
        self.capturing = True
        self.capture_type = capture_type
        self.update_status(f"Кликните для захвата координат {capture_type}...")
        
        btn = None
        if capture_type == 'search':
            btn = self.capture_search_btn
        elif capture_type == 'buy':
            btn = self.capture_buy_btn
        elif capture_type == 'confirm':
            btn = self.capture_confirm_btn
        elif capture_type == 'clear':
            btn = self.capture_clear_btn
        elif capture_type == 'quantity_input':
            btn = self.capture_quantity_btn
        elif capture_type == 'buy_order':
            btn = self.capture_buy_order_btn
        elif capture_type == 'price_per_unit':
            btn = self.capture_price_per_unit_btn
        elif capture_type == 'minus':
            btn = self.capture_minus_btn
        if btn:
            btn.config(command=self.cancel_capture)
        
        def on_click(x, y, button, pressed):
            if button == mouse.Button.left and pressed:
                if capture_type == 'search':
                    self.search_x_entry.delete(0, tk.END)
                    self.search_x_entry.insert(0, str(x))
                    self.search_y_entry.delete(0, tk.END)
                    self.search_y_entry.insert(0, str(y))
                elif capture_type == 'buy':
                    self.buy_x_entry.delete(0, tk.END)
                    self.buy_x_entry.insert(0, str(x))
                    self.buy_y_entry.delete(0, tk.END)
                    self.buy_y_entry.insert(0, str(y))
                elif capture_type == 'confirm':
                    self.confirm_x_entry.delete(0, tk.END)
                    self.confirm_x_entry.insert(0, str(x))
                    self.confirm_y_entry.delete(0, tk.END)
                    self.confirm_y_entry.insert(0, str(y))
                elif capture_type == 'clear':
                    self.clear_x_entry.delete(0, tk.END)
                    self.clear_x_entry.insert(0, str(x))
                    self.clear_y_entry.delete(0, tk.END)
                    self.clear_y_entry.insert(0, str(y))
                elif capture_type == 'quantity_input':
                    self.quantity_x_entry.delete(0, tk.END)
                    self.quantity_x_entry.insert(0, str(x))
                    self.quantity_y_entry.delete(0, tk.END)
                    self.quantity_y_entry.insert(0, str(y))
                elif capture_type == 'buy_order':
                    self.buy_order_x_entry.delete(0, tk.END)
                    self.buy_order_x_entry.insert(0, str(x))
                    self.buy_order_y_entry.delete(0, tk.END)
                    self.buy_order_y_entry.insert(0, str(y))
                elif capture_type == 'price_per_unit':
                    self.price_per_unit_x_entry.delete(0, tk.END)
                    self.price_per_unit_x_entry.insert(0, str(x))
                    self.price_per_unit_y_entry.delete(0, tk.END)
                    self.price_per_unit_y_entry.insert(0, str(y))
                elif capture_type == 'minus':
                    self.minus_x_entry.delete(0,tk.END)
                    self.minus_x_entry.insert(0,str(x))
                    self.minus_y_entry.delete(0,tk.END)
                    self.minus_y_entry.insert(0,str(y))
                self.finish_capture(f"Координаты {capture_type} захвачены: ({x}, {y})")
                return False
        
        self.mouse_listener = mouse.Listener(on_click=on_click)
        self.mouse_listener.start()
        
    def cancel_capture(self):
        if self.mouse_listener:
            self.mouse_listener.stop()
        self.finish_capture("Захват отменен")
        
    def finish_capture(self, message):
        self.capturing = False
        self.capture_type = None
        self.region_start = None
        self.update_status(message)
        
        self.capture_search_btn.config(text="Захватить поиск", command=self.start_capture_search)
        self.capture_buy_btn.config(text="Захватить покупку", command=self.start_capture_buy)
        self.capture_confirm_btn.config(text="Захватить подтвер.", command=self.start_capture_confirm)
        self.capture_clear_btn.config(text="Захватить очистку", command=self.start_capture_clear)
        self.capture_quantity_btn.config(text="Захватить ввод кол-ва", command=self.start_capture_quantity_input)
        self.capture_buy_order_btn.config(text="Захватить заказ на покупку", command=self.start_capture_buy_order)
        self.capture_price_per_unit_btn.config(text="Захватить цену за штуку", command=self.start_capture_price_per_unit)
        self.capture_minus_btn.config(text="Захватить кнопку минуса", command=self.start_capture_minus)
        self.capture_region_btn.config(command=self.start_capture_region)
        self.capture_sell_region_btn.config(command=self.start_capture_sell_region)
        self.capture_sell_item_price_region_btn.config(command=self.start_capture_sell_item_price_region)
        self.capture_quantity_region_btn.config(text="Захватить область количества", command=self.start_capture_quantity_region)
        self.capture_item_name_region_btn.config(text="Захватить область названия предмета", command=self.start_capture_item_name_region)
        
    def validate_inputs(self):
        """Проверка введенных данных"""
        try:
            int(self.search_x_entry.get())
            int(self.search_y_entry.get())
            int(self.clear_x_entry.get())
            int(self.clear_y_entry.get())
            int(self.buy_x_entry.get())
            int(self.buy_y_entry.get())
            int(self.confirm_x_entry.get())
            int(self.confirm_y_entry.get())
            int(self.quantity_x_entry.get())
            int(self.quantity_y_entry.get())
            int(self.buy_order_x_entry.get())
            int(self.buy_order_y_entry.get())
            int(self.price_per_unit_x_entry.get())
            int(self.price_per_unit_y_entry.get())
            int(self.minus_x_entry.get())
            int(self.minus_y_entry.get())
            
            left = int(self.left_entry.get())
            top = int(self.top_entry.get())
            width = int(self.width_entry.get())
            height = int(self.height_entry.get())
            
            left_sell = int(self.sell_left_entry.get())
            top_sell = int(self.sell_top_entry.get())
            width_sell = int(self.sell_width_entry.get())
            height_sell = int(self.sell_height_entry.get())
            
            left_sell_item_price = int(self.sell_item_price_left_entry.get())
            top_sell_item_price = int(self.sell_item_price_top_entry.get())
            width_sell_item_price = int(self.sell_item_price_width_entry.get())
            height_sell_item_price = int(self.sell_item_price_height_entry.get())
            
            left_q = int(self.left_q_entry.get())
            top_q = int(self.top_q_entry.get())
            width_q = int(self.width_q_entry.get())
            height_q = int(self.height_q_entry.get())
            
            left_item_name = int(self.left_item_name_entry.get())
            top_item_name = int(self.top_item_name_entry.get())
            width_item_name = int(self.width_item_name_entry.get())
            height_item_name = int(self.height_item_name_entry.get())
            
            budget = int(self.budget_entry.get())
            delay = float(self.delay_entry.get())
            start_row = int(self.start_row_entry.get())
            
            if width <= 0 or height <= 0 or width_q <= 0 or height_q <= 0 or width_sell <= 0 or height_sell <= 0 or width_item_name <=0 or height_item_name <=0 or width_sell_item_price <= 0 or height_sell_item_price <= 0:
                raise ValueError("Ширина и высота должны быть положительными")
            if budget <= 0:
                raise ValueError("Бюджет должен быть положительным")
            if delay < 0:
                raise ValueError("Задержка не может быть отрицательной")
            if start_row < 1:
                raise ValueError("Начальная строка должна быть не меньше 1")
                
            excel_file_path = Path(__file__).parent / 'table.xlsx'
            if not excel_file_path.exists():
                raise FileNotFoundError(f"Файл {excel_file_path} не найден. Убедитесь, что он находится в той же папке, что и скрипт.")
                
            return True
            
        except ValueError as e:
            messagebox.showerror("Ошибка ввода", f"Некорректные данные: {str(e)}")
            return False
        except FileNotFoundError as e:
            messagebox.showerror("Ошибка файла", str(e))
            return False
            
    def save_settings(self):
        """Сохранение настроек в файл"""
        settings = {
            'search_x': self.search_x_entry.get(),
            'search_y': self.search_y_entry.get(),
            'clear_x': self.clear_x_entry.get(),
            'clear_y': self.clear_y_entry.get(),
            'buy_x': self.buy_x_entry.get(),
            'buy_y': self.buy_y_entry.get(),
            'confirm_x': self.confirm_x_entry.get(),
            'confirm_y': self.confirm_y_entry.get(),
            'quantity_x': self.quantity_x_entry.get(),
            'quantity_y': self.quantity_y_entry.get(),
            'buy_order_x': self.buy_order_x_entry.get(),
            'buy_order_y': self.buy_order_y_entry.get(),
            'price_per_unit_x': self.price_per_unit_x_entry.get(),
            'price_per_unit_y': self.price_per_unit_y_entry.get(),
            'left': self.left_entry.get(),
            'top': self.top_entry.get(),
            'width': self.width_entry.get(),
            'height': self.height_entry.get(),
            'left_q': self.left_q_entry.get(),
            'top_q': self.top_q_entry.get(),
            'width_q': self.width_q_entry.get(),
            'height_q': self.height_q_entry.get(),
            'left_item_name': self.left_item_name_entry.get(),
            'top_item_name': self.top_item_name_entry.get(),
            'width_item_name': self.width_item_name_entry.get(),
            'height_item_name': self.height_item_name_entry.get(),
            'left_sell': self.sell_left_entry.get(),
            'top_sell': self.sell_top_entry.get(),
            'width_sell': self.sell_width_entry.get(),
            'height_sell': self.sell_height_entry.get(),
            'left_sell_item_price': self.sell_item_price_left_entry.get(),
            'top_sell_item_price': self.sell_item_price_top_entry.get(),
            'width_sell_item_price': self.sell_item_price_width_entry.get(),
            'height_sell_item_price': self.sell_item_price_height_entry.get(),
            'minus_x': self.minus_x_entry.get(),
            'minus_y': self.minus_y_entry.get(),
            'cumulative_spent': self.cumulative_spent_entry.get(),
            'budget': self.budget_entry.get(),
            'delay': self.delay_entry.get(),
            'start_row': self.start_row_entry.get(),
        }
        
        try:
            with open('bot_settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
            self.update_status("Настройки сохранены")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки: {str(e)}")
            
    def load_settings(self):
        """Загрузка настроек из файла"""
        try:
            if os.path.exists('bot_settings.json'):
                with open('bot_settings.json', 'r') as f:
                    settings = json.load(f)
                
                self.search_x_entry.insert(0, settings.get('search_x', ''))
                self.search_y_entry.insert(0, settings.get('search_y', ''))
                self.clear_x_entry.insert(0, settings.get('clear_x', ''))
                self.clear_y_entry.insert(0, settings.get('clear_y', ''))
                self.buy_x_entry.insert(0, settings.get('buy_x', ''))
                self.buy_y_entry.insert(0, settings.get('buy_y', ''))
                self.confirm_x_entry.insert(0, settings.get('confirm_x', ''))
                self.confirm_y_entry.insert(0, settings.get('confirm_y', ''))
                self.quantity_x_entry.insert(0, settings.get('quantity_x', ''))
                self.quantity_y_entry.insert(0, settings.get('quantity_y', ''))
                self.buy_order_x_entry.insert(0, settings.get('buy_order_x', ''))
                self.buy_order_y_entry.insert(0, settings.get('buy_order_y', ''))
                self.price_per_unit_x_entry.insert(0, settings.get('price_per_unit_x', ''))
                self.price_per_unit_y_entry.insert(0, settings.get('price_per_unit_y', ''))
                self.left_entry.insert(0, settings.get('left', ''))
                self.top_entry.insert(0, settings.get('top', ''))
                self.width_entry.insert(0, settings.get('width', ''))
                self.height_entry.insert(0, settings.get('height', ''))
                self.left_q_entry.insert(0, settings.get('left_q', ''))
                self.top_q_entry.insert(0, settings.get('top_q', ''))
                self.width_q_entry.insert(0, settings.get('width_q', ''))
                self.height_q_entry.insert(0, settings.get('height_q', ''))
                self.left_item_name_entry.insert(0, settings.get('left_item_name', ''))
                self.top_item_name_entry.insert(0, settings.get('top_item_name', ''))
                self.width_item_name_entry.insert(0, settings.get('width_item_name', ''))
                self.height_item_name_entry.insert(0, settings.get('height_item_name', ''))
                self.sell_left_entry.insert(0, settings.get('left_sell', ''))
                self.sell_top_entry.insert(0, settings.get('top_sell', ''))
                self.sell_width_entry.insert(0, settings.get('width_sell', ''))
                self.sell_height_entry.insert(0, settings.get('height_sell', ''))
                self.sell_item_price_left_entry.insert(0, settings.get('left_sell_item_price', ''))
                self.sell_item_price_top_entry.insert(0, settings.get('top_sell_item_price', ''))
                self.sell_item_price_width_entry.insert(0, settings.get('width_sell_item_price', ''))
                self.sell_item_price_height_entry.insert(0, settings.get('height_sell_item_price', ''))
                self.minus_x_entry.insert(0, settings.get('minus_x', ''))
                self.minus_y_entry.insert(0, settings.get('minus_y', ''))
                self.cumulative_spent_entry.delete(0, tk.END)
                self.cumulative_spent_entry.insert(0, settings.get('cumulative_spent', '0'))
                self.budget_entry.insert(0, settings.get('budget', ''))
                self.delay_entry.delete(0, tk.END)
                self.delay_entry.insert(0, settings.get('delay', '0.5'))
                self.start_row_entry.delete(0, tk.END)
                self.start_row_entry.insert(0, settings.get('start_row', '1'))
        except Exception as e:
            logging.warning(f"Не удалось загрузить настройки: {str(e)}")
            
    def emergency_stop(self):
        """Экстренная остановка скрипта"""
        self.script_running = False
        if self.paused:
            self.pause_event.set()
            self.paused = False
        self.update_status("Остановлено пользователем (F2)")
        self.update_current_item_info()  # Clear current item info
        self.manual_btn.config(state='normal')
        self.order_btn.config(state='normal')
        self.sell_btn.config(state='normal')
        self.progress.stop()
        try:
            keyboard.unhook_all()
        except Exception as e:
            logging.warning(f"Не удалось отменить все горячие клавиши: {e}")
    
    def skip_current_item(self):
        """Пропустить текущий предмет (F3)"""
        if self.script_running:
            self.skip_item = True
            self.update_status("Пропуск текущего предмета (F3)...")

    def toggle_pause(self):
        if not self.script_running:
            return
        self.paused = not self.paused
        if self.paused:
            self.pause_event.clear()
            msg = "Скрипт на паузе (F4)"
            self.update_status(msg)
            self.log_entries.append(f"[{datetime.now()}] {msg}")
            logging.info(msg)
        else:
            self.pause_event.set()
            msg = "Скрипт возобновлен (F4)"
            self.update_status(msg)
            self.log_entries.append(f"[{datetime.now()}] {msg}")
            logging.info(msg)

    def update_table(self):
        try:
            excel_file_path = Path(__file__).parent / 'table.xlsx'
            response = requests.get(url)
            response.raise_for_status()

            with open(excel_file_path, "wb") as f:
                f.write(response.content)
            print('Таблица успешно обновлена')
        except Exception as e:
            print('Не удалось обновить таблицу')

    def start_manual(self):
        if self.script_running:
            return
            
        if not self.validate_inputs():
            return
        
        keyboard.add_hotkey('f2', self.emergency_stop)
        keyboard.add_hotkey('f3', self.skip_current_item)
        keyboard.add_hotkey('f4', self.toggle_pause)
            
        search_x = int(self.search_x_entry.get())
        search_y = int(self.search_y_entry.get())
        clear_x = int(self.clear_x_entry.get())
        clear_y = int(self.clear_y_entry.get())
        buy_x = int(self.buy_x_entry.get())
        buy_y = int(self.buy_y_entry.get())
        confirm_x = int(self.confirm_x_entry.get())
        confirm_y = int(self.confirm_y_entry.get())
        quantity_x = int(self.quantity_x_entry.get())
        quantity_y = int(self.quantity_y_entry.get())
        left = int(self.left_entry.get())
        top = int(self.top_entry.get())
        width = int(self.width_entry.get())
        height = int(self.height_entry.get())
        left_q = int(self.left_q_entry.get())
        top_q = int(self.top_q_entry.get())
        width_q = int(self.width_q_entry.get())
        height_q = int(self.height_q_entry.get())
        budget = int(self.budget_entry.get())
        delay = float(self.delay_entry.get())
        start_row = int(self.start_row_entry.get())
        
        self.manual_btn.config(state='disabled')
        self.order_btn.config(state='disabled')
        self.progress.start()
        
        self.countdown_and_run_manual(search_x, search_y, clear_x, clear_y, buy_x, buy_y, confirm_x, confirm_y, 
                                      quantity_x, quantity_y, left, top, width, height, left_q, top_q, width_q, height_q, 
                                      budget, delay, start_row)
        
    def countdown_and_run_manual(self, search_x, search_y, clear_x, clear_y, buy_x, buy_y, confirm_x, confirm_y, 
                                 quantity_x, quantity_y, left, top, width, height, left_q, top_q, width_q, height_q, 
                                 budget, delay, start_row):
        def countdown():
            try:
                for i in range(5, 0, -1):
                    self.update_status(f"Запуск ручной закупки через {i} секунд...")
                    time.sleep(1)
                
                self.script_running = True
                self.run_script_manual(search_x, search_y, clear_x, clear_y, buy_x, buy_y, confirm_x, confirm_y, 
                                       quantity_x, quantity_y, left, top, width, height, left_q, top_q, width_q, height_q, 
                                       budget, delay, start_row)
            except Exception as e:
                self.emergency_stop()
                messagebox.showerror("Ошибка", f"Ошибка при запуске скрипта: {e}")
        
        self.script_thread = threading.Thread(target=countdown, daemon=True)
        self.script_thread.start()

    def start_order(self):
        if self.script_running:
            return
            
        if not self.validate_inputs():
            return
        
        keyboard.add_hotkey('f2', self.emergency_stop)
        keyboard.add_hotkey('f3', self.skip_current_item)
        keyboard.add_hotkey('f4', self.toggle_pause)
            
        search_x = int(self.search_x_entry.get())
        search_y = int(self.search_y_entry.get())
        clear_x = int(self.clear_x_entry.get())
        clear_y = int(self.clear_y_entry.get())
        buy_x = int(self.buy_x_entry.get())
        buy_y = int(self.buy_y_entry.get())
        confirm_x = int(self.confirm_x_entry.get())
        confirm_y = int(self.confirm_y_entry.get())
        quantity_x = int(self.quantity_x_entry.get())
        quantity_y = int(self.quantity_y_entry.get())
        buy_order_x = int(self.buy_order_x_entry.get())
        buy_order_y = int(self.buy_order_y_entry.get())
        price_per_unit_x = int(self.price_per_unit_x_entry.get())
        price_per_unit_y = int(self.price_per_unit_y_entry.get())
        left = int(self.left_entry.get())
        top = int(self.top_entry.get())
        width = int(self.width_entry.get())
        height = int(self.height_entry.get())
        budget = int(self.budget_entry.get())
        delay = float(self.delay_entry.get())
        start_row = int(self.start_row_entry.get())
        
        self.manual_btn.config(state='disabled')
        self.order_btn.config(state='disabled')
        self.progress.start()
        
        self.countdown_and_run_order(search_x, search_y, clear_x, clear_y, buy_x, buy_y, confirm_x, confirm_y, 
                                     quantity_x, quantity_y, buy_order_x, buy_order_y, price_per_unit_x, price_per_unit_y, 
                                     left, top, width, height, budget, delay, start_row)
        
    def countdown_and_run_order(self, search_x, search_y, clear_x, clear_y, buy_x, buy_y, confirm_x, confirm_y, 
                                quantity_x, quantity_y, buy_order_x, buy_order_y, price_per_unit_x, price_per_unit_y, 
                                left, top, width, height, budget, delay, start_row):
        def countdown():
            try:
                for i in range(5, 0, -1):
                    self.update_status(f"Запуск закупки ордерами через {i} секунд...")
                    time.sleep(1)
                
                self.script_running = True
                self.run_script_order(search_x, search_y, clear_x, clear_y, buy_x, buy_y, confirm_x, confirm_y, 
                                      quantity_x, quantity_y, buy_order_x, buy_order_y, price_per_unit_x, price_per_unit_y, 
                                      left, top, width, height, budget, delay, start_row)
            except Exception as e:
                self.emergency_stop()
                messagebox.showerror("Ошибка", f"Ошибка при запуске скрипта: {e}")
        
        self.script_thread = threading.Thread(target=countdown, daemon=True)
        self.script_thread.start()

    def check_and_click_ok(self):
        try:
            ok_button_location = pyautogui.locateCenterOnScreen(
                str(Path(__file__).parent / "buttons_image" / 'ok_button.png'), 
                confidence=0.7, 
                region=(0, 0, pyautogui.size().width, pyautogui.size().height)
            )
            
            if ok_button_location is not None:
                self.update_status("Найдено всплывающее окно. Нажимаю OK...")
                logging.info(f"[{datetime.now()}] Найдено всплывающее окно. Нажимаю OK.")
                pyautogui.click(ok_button_location)
                time.sleep(0.5)
                return True
        except pyautogui.PyAutoGUIException as e:
            logging.warning(f"Ошибка при поиске кнопки OK: {e}")
            return False
        return False
        
    def check_and_click_yes(self):
        try:
            yes_button_location = pyautogui.locateCenterOnScreen(
                str(Path(__file__).parent / "buttons_image" /'yes_button.png'), 
                confidence=0.7, 
                region=(0, 0, pyautogui.size().width, pyautogui.size().height)
            )
            
            if yes_button_location is not None:
                self.update_status("Найдено подтверждение. Нажимаю Да...")
                logging.info(f"[{datetime.now()}] Найдено подтверждение. Нажимаю Да.")
                pyautogui.click(yes_button_location)
                time.sleep(0.5)
                return True
        except pyautogui.PyAutoGUIException as e:
            logging.warning(f"Ошибка при поиске кнопки Да: {e}")
            return False
        return False
        
    def run_script_manual(self, search_x, search_y, clear_x, clear_y, buy_x, buy_y, confirm_x, confirm_y, 
                        quantity_x, quantity_y, left, top, width, height, left_q, top_q, width_q, height_q, 
                        budget, delay, start_row):
        self.log_entries = []
        try:
            self.update_status("Загрузка данных из Excel...")
            self.log_entries.append(f"[{datetime.now()}] --- Начать сессию с строки {start_row} ---")
            
            excel_file_path = Path(__file__).parent / 'table.xlsx'
            df = pd.read_excel(excel_file_path, sheet_name=0, header=0)
            
            total_spent = 0
            total_items = len(df) - start_row + 1
            if total_items <= 0:
                raise ValueError("Начальная строка больше количества строк в таблице")
            min_budget_threshold = 10000
            for index, row in df.iloc[start_row-1:].iterrows():
                self.pause_event.wait()
                
                if not self.script_running:
                    self.log_entries.append(f"[{datetime.now()}] Сессия остановлена пользователем.")
                    break
                
                if self.skip_item:
                    msg = f"Пропускаю {row['name']} по запросу пользователя (F3)."
                    self.update_status(msg)
                    self.log_entries.append(f"[{datetime.now()}] {msg}")
                    self.skip_item = False
                    continue
                    
                self.progress['value'] = ((index - (start_row - 1)) / total_items) * 100
                self.update_status(f"Обрабатывается {index - start_row + 2}/{total_items}: {row['name']}")
                
                name = str(row['name']).strip()
                
                try:
                    value = int(row['value'])
                    store = int(row['store'])
                    present = float(row['present'])
                except (ValueError, TypeError) as e:
                    msg = f"Некорректные данные для {name}: {str(e)}. Пропускается."
                    print(msg)
                    logging.warning(msg)
                    self.log_entries.append(f"[{datetime.now()}] Ошибка: {msg}")
                    continue
                
                if value <= 0 or store <= 0 or present <= 0:
                    msg = f"Пропускается {name} (некорректные значения)"
                    print(msg)
                    logging.info(msg)
                    self.log_entries.append(f"[{datetime.now()}] Предупреждение: {msg}")
                    continue

                limit_price = int(value * present)
                # Update current item info at start of processing
                self.update_current_item_info(name=name, value=value, ocr_price="N/A", bought=0, store=store, limit_price=limit_price, budget=budget, total_spent=total_spent)

                pyautogui.moveTo(clear_x, clear_y, duration=random.uniform(0.1, 0.2))
                pyautogui.click()
                
                pyautogui.moveTo(search_x, search_y, duration=random.uniform(0.1, 0.2))
                pyautogui.click()
                time.sleep(random.uniform(0.1, 0.2))
                
                for char in name:
                    keyboard.write(char)
                    time.sleep(random.uniform(0.01, 0.05))
                
                time.sleep(random.uniform(0.5, 1))
                
                bought = 0
                failed_ocr_attempts = 0
                max_failed_attempts = 5
                
                while bought < store and self.script_running and failed_ocr_attempts < max_failed_attempts and not self.skip_item:
                    self.pause_event.wait()
                    
                    if self.check_and_click_ok():
                        continue
                        
                    try:
                        screenshot = ImageGrab.grab(bbox=(left, top, left + width, top + height))
                        ocr_text = pytesseract.image_to_string(screenshot, config='--psm 7 -c tessedit_char_whitelist=0123456789')
                        ocr_price = int(ocr_text.strip() or 0)
                        failed_ocr_attempts = 0
                        msg = f"Текущая цена для {name}: {ocr_price}"
                        print(msg)
                        logging.info(msg)
                        self.log_entries.append(f"[{datetime.now()}] {msg}")

                        # Update current item info with OCR price
                        self.update_current_item_info(name=name, value=value, ocr_price=ocr_price, bought=bought, store=store, limit_price=limit_price, budget=budget, total_spent=total_spent)

                    except (ValueError, pytesseract.TesseractError) as e:
                        failed_ocr_attempts += 1
                        try:
                            ocr_text  # to reference for msg
                        except NameError:
                            ocr_text = ''
                        msg = f"OCR ошибка для {name} (попытка {failed_ocr_attempts}): '{ocr_text.strip()}' - {e}"
                        print(msg)
                        logging.warning(msg)
                        self.log_entries.append(f"[{datetime.now()}] Ошибка OCR: {msg}")
                        time.sleep(delay)
                        continue
                    
                    if ocr_price == 0:
                        failed_ocr_attempts += 1
                        msg = f"OCR вернул 0. Попытка {failed_ocr_attempts}. Пропускаю."
                        print(msg)
                        logging.warning(msg)
                        self.log_entries.append(f"[{datetime.now()}] Предупреждение: {msg}")
                        time.sleep(delay)
                        continue

                    if ocr_price > limit_price:
                        msg = f"Цена {ocr_price} не выгодна для {name} (лимит: {limit_price})"
                        print(msg)
                        logging.info(msg)
                        self.log_entries.append(f"[{datetime.now()}] {msg}")
                        break
                        
                    if total_spent + ocr_price > budget:  # Check for at least one
                        msg = f"Бюджет превышен ({total_spent + ocr_price} > {budget})."
                        print(msg)
                        logging.info(msg)
                        self.update_status("Бюджет превышен!")
                        self.log_entries.append(f"[{datetime.now()}] {msg}")
                        self.script_running = False
                        break
                        
                    try:
                        # Click the Buy button to open the purchase dialog
                        pyautogui.moveTo(buy_x, buy_y, duration=random.uniform(0.1, 0.2))
                        pyautogui.click()
                        time.sleep(random.uniform(0.3, 0.5))  # Wait for dialog to open
                        
                        # Захват изображения
                        screenshot_q = ImageGrab.grab(bbox=(left_q, top_q, left_q + width_q, top_q + height_q))
                        
                        # Сохранение скриншота для отладки
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                        screenshot_path = screenshots_dir / f"quantity_{name}_{timestamp}.png"
                        screenshot_q.save(screenshot_path)
                        
                        # Выполнение OCR с учетом confidence
                        data = pytesseract.image_to_data(screenshot_q, output_type=pytesseract.Output.DICT, 
                                                        config='--psm 7 -c tessedit_char_whitelist=0123456789')
                        
                        # Фильтрация результатов с минимальным confidence
                        available = []
                        text = ""
                        for i in range(len(data['text'])):
                            if data['text'][i].strip() and int(data['conf'][i]) > -1:  # -1 означает отсутствие уверенности
                                confidence = int(data['conf'][i])
                                text = data['text'][i].strip()
                                available.append((text, confidence))
                        
                        msg = f"OCR количества для {name}: '{text.strip()}', распознано как {available}, сохранен скриншот: {screenshot_path}"
                        print(msg)
                        logging.info(msg)
                        self.log_entries.append(f"[{datetime.now()}] {msg}")
                        if available:
                            available = max(available, key=lambda x: x[1])[0]  # Берем текст с максимальным confidence
                            available = int(available)  # Преобразуем в число
                        else:
                            available = 0
                        if available <= 0:
                            failed_ocr_attempts += 1
                            msg = f"Недопустимое количество для {name} (OCR: {text.strip()}). Попытка {failed_ocr_attempts}."
                            print(msg)
                            logging.warning(msg)
                            self.log_entries.append(f"[{datetime.now()}] Предупреждение: {msg}")
                            time.sleep(delay)
                            continue
                            
                        to_buy = min(available, store - bought)
                        msg = f"Рассчитано to_buy для {name}: min(доступно={available}, осталось купить={store - bought}) = {to_buy}"
                        print(msg)
                        logging.info(msg)
                        self.log_entries.append(f"[{datetime.now()}] {msg}")
                        
                        # Check budget for batch
                        batch_cost = ocr_price * to_buy
                        if budget - total_spent < min_budget_threshold:
                            msg = f"Остаток бюджета ({budget - total_spent}) меньше порога ({min_budget_threshold}). Завершаем."
                            print(msg)
                            logging.info(msg)
                            self.log_entries.append(f"[{datetime.now()}] {msg}")
                            self.script_running = False
                            break
                        if total_spent + batch_cost > budget:
                            to_buy = (budget - total_spent) // ocr_price
                            batch_cost = ocr_price * to_buy
                            if to_buy > 0:
                                msg = f"Бюджет ограничивает покупку для {name}: to_buy скорректировано до {to_buy}"
                                print(msg)
                                logging.info(msg)
                                self.log_entries.append(f"[{datetime.now()}] {msg}")
                            else:
                                msg = f"Бюджет исчерпан для {name}."
                                print(msg)
                                logging.info(msg)
                                self.log_entries.append(f"[{datetime.now()}] {msg}")
                                self.script_running = False
                                break
                            
                        if to_buy == 1:
                            # Just confirm
                            pyautogui.moveTo(confirm_x, confirm_y, duration=random.uniform(0.1, 0.2))
                            pyautogui.click()
                        else:
                            # Click quantity input field
                            pyautogui.moveTo(quantity_x, quantity_y, duration=random.uniform(0.1, 0.2))
                            pyautogui.click()
                            time.sleep(random.uniform(0.1, 0.2))
                            
                            # Type the quantity
                            for char in str(to_buy):
                                keyboard.write(char)
                                time.sleep(random.uniform(0.01, 0.05))
                            time.sleep(random.uniform(0.1, 0.2))
                            
                            # Confirm
                            pyautogui.moveTo(confirm_x, confirm_y, duration=random.uniform(0.1, 0.2))
                            pyautogui.click()
                        
                        time.sleep(random.uniform(0.1, 0.2))
                        self.check_and_click_ok()
                        
                        bought += to_buy
                        total_spent += ocr_price * to_buy
                        try:
                            log_path = Path(__file__).parent / 'purchase_log.csv'
                            file_exists = log_path.exists()
                            with open(log_path, 'a', newline='', encoding='utf-8') as f:
                                writer = csv.writer(f)
                                if not file_exists:
                                    writer.writerow(['item_name', 'quantity', 'price_per_unit', 'purchase_type'])
                                writer.writerow([name, to_buy, ocr_price, 'manual'])
                        except Exception as e:
                            logging.error(f"Не удалось записать в purchase_log.csv: {e}")
                        
                        msg = f"Куплено {bought}/{store} {name} ({to_buy} шт.) за {ocr_price} each. Потрачено: {total_spent}"
                        print(msg)
                        logging.info(msg)
                        self.log_entries.append(f"[{datetime.now()}] {msg}")

                        # Update current item info after purchase
                        self.update_current_item_info(name=name, value=value, ocr_price=ocr_price, bought=bought, store=store, limit_price=limit_price, budget=budget, total_spent=total_spent)
                        
                    except Exception as e:
                        msg = f"Ошибка покупки: {str(e)}"
                        print(msg)
                        logging.error(msg)
                        self.log_entries.append(f"[{datetime.now()}] Ошибка: {msg}")
                        break
                
                self.skip_item = False
                # Clear current item info after processing
                self.update_current_item_info()
            
            if self.script_running:
                msg = f"Скрипт завершен. Всего потрачено: {total_spent}"
                print(msg)
                logging.info(msg)
                self.log_entries.append(f"[{datetime.now()}] --- Сессия завершена. Всего потрачено: {total_spent} ---")
                self.update_status(f"Завершено! Потрачено: {total_spent}")
                messagebox.showinfo("Завершено", msg)
            
        except Exception as e:
            error_msg = f"Критическая ошибка: {str(e)}"
            print(error_msg)
            logging.error(error_msg)
            self.update_status("Ошибка выполнения")
            self.log_entries.append(f"[{datetime.now()}] Критическая ошибка: {error_msg}")
            messagebox.showerror("Ошибка", error_msg)
        finally:
            try:
                current_cumulative = int(self.cumulative_spent_entry.get() or 0)
                session_spent = int(total_spent)
                new_cumulative = current_cumulative + total_spent
                self.cumulative_spent_entry.delete(0, tk.END)
                self.cumulative_spent_entry.insert(0, str(new_cumulative))
                self.save_settings()
            except Exception as e:
                logging.error(f"Не удалось обновить суммарные затраты: {e}")
            self.emergency_stop()
            self.progress.stop()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            progress_log_filename = f"progress_log_manual_{timestamp}.txt"
            
            logs_dir = Path(__file__).parent / "logs"
            logs_dir.mkdir(exist_ok=True)
            
            log_path = logs_dir / progress_log_filename
            print(f"Попытка сохранить лог прогресса в файл: {log_path}")
            
            try:
                with open(log_path, 'w', encoding='utf-8') as f:
                    for entry in self.log_entries:
                        f.write(entry + '\n')
                print(f"Лог прогресса сохранен в файл: {log_path}")
            except Exception as e:
                print(f"Не удалось сохранить лог прогресса: {e}")

    def run_script_order(self, search_x, search_y, clear_x, clear_y, buy_x, buy_y, confirm_x, confirm_y, 
                         quantity_x, quantity_y, buy_order_x, buy_order_y, price_per_unit_x, price_per_unit_y, 
                         left, top, width, height, budget, delay, start_row):
        self.log_entries = []
        try:
            self.update_status("Загрузка данных из Excel...")
            self.log_entries.append(f"[{datetime.now()}] --- Начать сессию ордерами с строки {start_row} ---")
            
            excel_file_path = Path(__file__).parent / 'table.xlsx'
            df = pd.read_excel(excel_file_path, sheet_name=0, header=0)
            
            total_spent = 0
            total_items = len(df) - start_row + 1
            if total_items <= 0:
                raise ValueError("Начальная строка больше количества строк в таблице")
            min_budget_threshold = 10000

            for index, row in df.iloc[start_row-1:].iterrows():
                self.pause_event.wait()
                
                if not self.script_running:
                    self.log_entries.append(f"[{datetime.now()}] Сессия остановлена пользователем.")
                    break
                
                if self.skip_item:
                    msg = f"Пропускаю {row['name']} по запросу пользователя (F3)."
                    self.update_status(msg)
                    self.log_entries.append(f"[{datetime.now()}] {msg}")
                    self.skip_item = False
                    continue
                    
                self.progress['value'] = ((index - (start_row - 1)) / total_items) * 100
                self.update_status(f"Обрабатывается {index - start_row + 2}/{total_items}: {row['name']}")
                
                name = str(row['name']).strip()
                
                try:
                    value = int(row['value'])
                    store = int(row['store'])
                    present = float(row['present'])
                except (ValueError, TypeError) as e:
                    msg = f"Некорректные данные для {name}: {str(e)}. Пропускается."
                    print(msg)
                    logging.warning(msg)
                    self.log_entries.append(f"[{datetime.now()}] Ошибка: {msg}")
                    continue
                
                if value <= 0 or store <= 0 or present <= 0:
                    msg = f"Пропускается {name} (некорректные значения)"
                    print(msg)
                    logging.info(msg)
                    self.log_entries.append(f"[{datetime.now()}] Предупреждение: {msg}")
                    continue

                limit_price = int(value * present) 
                # Update current item info at start of processing
                self.update_current_item_info(name=name, value=value, ocr_price="N/A", bought=0, store=store, limit_price=limit_price, budget=budget, total_spent=total_spent)

                pyautogui.moveTo(clear_x, clear_y, duration=random.uniform(0.1, 0.2))
                pyautogui.click()
                
                pyautogui.moveTo(search_x, search_y, duration=random.uniform(0.1, 0.2))
                pyautogui.click()
                time.sleep(random.uniform(0.1, 0.2))
                
                for char in name:
                    keyboard.write(char)
                    time.sleep(random.uniform(0.01, 0.05))
                
                time.sleep(random.uniform(0.5, 1))
                
                failed_ocr_attempts = 0
                max_failed_attempts = 5
                
                while self.script_running and failed_ocr_attempts < max_failed_attempts and not self.skip_item:
                    self.pause_event.wait()
                    
                    if self.check_and_click_ok():
                        continue
                        
                    try:
                        screenshot = ImageGrab.grab(bbox=(left, top, left + width, top + height))
                        ocr_text = pytesseract.image_to_string(screenshot, config='--psm 7 -c tessedit_char_whitelist=0123456789')
                        ocr_price = int(ocr_text.strip() or 0)
                        failed_ocr_attempts = 0
                        msg = f"Текущая цена для {name}: {ocr_price}"
                        print(msg)
                        logging.info(msg)
                        self.log_entries.append(f"[{datetime.now()}] {msg}")

                        # Update current item info with OCR price
                        self.update_current_item_info(name=name, value=value, ocr_price=ocr_price, bought=0, store=store, limit_price=limit_price, budget=budget, total_spent=total_spent)

                    except (ValueError, pytesseract.TesseractError) as e:
                        failed_ocr_attempts += 1
                        try:
                            ocr_text 
                        except NameError:
                            ocr_text = ''
                        msg = f"OCR ошибка для {name} (попытка {failed_ocr_attempts}): '{ocr_text.strip()}' - {e}"
                        print(msg)
                        logging.warning(msg)
                        self.log_entries.append(f"[{datetime.now()}] Ошибка OCR: {msg}")
                        time.sleep(delay)
                        continue
                    
                    if ocr_price == 0:
                        failed_ocr_attempts += 1
                        msg = f"OCR вернул 0. Попытка {failed_ocr_attempts}. Пропускаю."
                        print(msg)
                        logging.warning(msg)
                        self.log_entries.append(f"[{datetime.now()}] Предупреждение: {msg}")
                        time.sleep(delay)
                        continue

                    order_limit_price = int(value * present * 0.975)
                    if ocr_price > order_limit_price:
                        msg = f"Цена {ocr_price} не подходит для {name} (лимит: {order_limit_price})"
                        print(msg)
                        logging.info(msg)
                        self.log_entries.append(f"[{datetime.now()}] {msg}")
                        break
                    
                    # Calculate tax-adjusted cost
                    tax_rate = 1.025  # 2.5% tax
                    max_cost = store * limit_price * tax_rate
                    if budget - total_spent < min_budget_threshold:
                        msg = f"Остаток бюджета ({budget - total_spent}) меньше порога ({min_budget_threshold}). Завершаем."
                        print(msg)
                        logging.info(msg)
                        self.log_entries.append(f"[{datetime.now()}] {msg}")
                        self.script_running = False
                        break
                    if total_spent + max_cost > budget:
                        store = int((budget - total_spent) / (limit_price * tax_rate))
                        max_cost = store * limit_price * tax_rate
                        if store > 0:
                            msg = f"Бюджет ограничивает ордер для {name}: store скорректировано до {store}"
                            print(msg)
                            logging.info(msg)
                            self.log_entries.append(f"[{datetime.now()}] {msg}")
                        else:
                            msg = f"Бюджет исчерпан для {name}."
                            print(msg)
                            logging.info(msg)
                            self.log_entries.append(f"[{datetime.now()}] {msg}")
                            break
                    
                    pyautogui.moveTo(buy_x, buy_y, duration=random.uniform(0.1, 0.2))
                    pyautogui.click()
                    time.sleep(random.uniform(0.1, 0.2))  # Wait for dialog to open
                    
                    pyautogui.moveTo(buy_order_x, buy_order_y, duration=random.uniform(0.1, 0.2))
                    pyautogui.click()
                    time.sleep(random.uniform(0.1, 0.2))
                    
                    pyautogui.moveTo(quantity_x, quantity_y, duration=random.uniform(0.1, 0.2))
                    pyautogui.click()
                    time.sleep(random.uniform(0.1, 0.2))
                    
                    for char in str(store):
                        keyboard.write(char)
                        time.sleep(random.uniform(0.01, 0.05))
                    time.sleep(random.uniform(0.1, 0.2))
                    
                    pyautogui.moveTo(price_per_unit_x, price_per_unit_y, duration=random.uniform(0.1, 0.2))
                    pyautogui.click()
                    time.sleep(random.uniform(0.1, 0.2))
                    
                    for char in str(limit_price):
                        keyboard.write(char)
                        time.sleep(random.uniform(0.01, 0.05))
                    time.sleep(random.uniform(0.1, 0.2))
                    
                    pyautogui.moveTo(confirm_x, confirm_y, duration=random.uniform(0.1, 0.2))
                    pyautogui.click()
                    time.sleep(random.uniform(0.1, 0.2))
                    
                    self.check_and_click_yes()
                    
                    total_spent += store * limit_price * tax_rate 
                    try:
                        log_path = Path(__file__).parent / 'purchase_log.csv'
                        file_exists = log_path.exists()
                        with open(log_path, 'a', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            if not file_exists:
                                writer.writerow(['item_name', 'quantity', 'price_per_unit', 'purchase_type'])
                            writer.writerow([name, store, limit_price, 'order'])
                    except Exception as e:
                        logging.error(f"Не удалось записать в purchase_log.csv: {e}")
                    msg = f"Ордер размещен для {name} ({store} шт.) по {limit_price} each. Потрачено (примерно): {total_spent}"
                    print(msg)
                    logging.info(msg)
                    self.log_entries.append(f"[{datetime.now()}] {msg}")
                    
                    # Update current item info
                    self.update_current_item_info(name=name, value=value, ocr_price=ocr_price, bought=store, store=store, limit_price=limit_price)
                    
                    break  # Move to next item
                
                self.skip_item = False
                # Clear current item info after processing
                self.update_current_item_info()
            
            if self.script_running:
                msg = f"Скрипт завершен. Всего потрачено (примерно): {total_spent}"
                print(msg)
                logging.info(msg)
                self.log_entries.append(f"[{datetime.now()}] --- Сессия завершена. Всего потрачено (примерно): {total_spent} ---")
                self.update_status(f"Завершено! Потрачено (примерно): {total_spent}")
                messagebox.showinfo("Завершено", msg)
            
        except Exception as e:
            error_msg = f"Критическая ошибка: {str(e)}"
            print(error_msg)
            logging.error(error_msg)
            self.update_status("Ошибка выполнения")
            self.log_entries.append(f"[{datetime.now()}] Критическая ошибка: {error_msg}")
            messagebox.showerror("Ошибка", error_msg)
        finally:
            try:
                current_cumulative = int(self.cumulative_spent_entry.get() or 0)
                session_spent = int(total_spent)
                new_cumulative = current_cumulative + total_spent
                self.cumulative_spent_entry.delete(0, tk.END)
                self.cumulative_spent_entry.insert(0, str(new_cumulative))
                self.save_settings()
            except Exception as e:
                logging.error(f"Не удалось обновить суммарные затраты: {e}")
            self.emergency_stop()
            self.progress.stop()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            progress_log_filename = f"progress_log_order_{timestamp}.txt"
            
            logs_dir = Path(__file__).parent / "logs"
            logs_dir.mkdir(exist_ok=True)
            
            log_path = logs_dir / progress_log_filename
            print(f"Попытка сохранить лог прогресса в файл: {log_path}")
            
            try:
                with open(log_path, 'w', encoding='utf-8') as f:
                    for entry in self.log_entries:
                        f.write(entry + '\n')
                print(f"Лог прогресса сохранен в файл: {log_path}")
            except Exception as e:
                print(f"Не удалось сохранить лог прогресса: {e}")

    def start_sell(self):
        if self.script_running:
            return
        keyboard.add_hotkey('f2', self.emergency_stop)
        keyboard.add_hotkey('f4', self.toggle_pause)
        
        coords = {
            "sell_button": (int(self.buy_x_entry.get()), int(self.buy_y_entry.get())),
            'minus_button': (int(self.minus_x_entry.get()), int(self.minus_y_entry.get())),
            "confirm_button":(int(self.confirm_x_entry.get()), int(self.confirm_y_entry.get())) 
        }

        regions = {
            'item_name': (int(self.left_item_name_entry.get()), int(self.top_item_name_entry.get()), int(self.width_item_name_entry.get()), int(self.height_item_name_entry.get())),
            'sale_price':(int(self.sell_left_entry.get()), int(self.sell_top_entry.get()), int(self.sell_width_entry.get()), int(self.sell_height_entry.get())),
            'buy_price':(int(self.sell_item_price_left_entry.get()), int(self.sell_item_price_top_entry.get()), int(self.sell_item_price_width_entry.get()), int(self.sell_item_price_height_entry.get())),
        }
        
        total_spent = int(self.cumulative_spent_entry.get() or 0)
        
        self.manual_btn.config(state="disabled")
        self.order_btn.config(state="disabled")
        self.sell_btn.config(state="disabled")
        self.progress.start()
        
        def gui_callback(action, data=None):
            if action == 'update_status':
                self.update_status(data)
            elif action == 'update_current_item_info':
                self.update_current_item_info(**data)
            elif action == 'pause_event_wait':
                self.pause_event.wait()
            elif action == 'is_running':
                return self.script_running
            

        def run_wrapper():
            try:
                for i in range(5,0,-1):
                    self.update_status(f"Запуск продажи через {i} секунд...")
                    time.sleep(1)

                self.script_running = True
                success, message = run_selling_cycle(coords, regions, total_spent, gui_callback)
                
                if success:
                    # Сброс затрат после успешной продажи
                    self.cumulative_spent_entry.delete(0, tk.END)
                    self.cumulative_spent_entry.insert(0, "0")
                    self.save_settings()
                    messagebox.showinfo("Успех", message)
                else:
                    messagebox.showerror("Ошибка", message)
                
            except Exception as e:
                messagebox.showerror("Критическая ошибка", f"Произошла ошибка в процессе продажи: {e}")
            finally:
                self.emergency_stop()     
                
        self.script_thread = threading.Thread(target=run_wrapper, daemon=True)
        self.script_thread.start()           
          
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = MarketBotGUI()
    app.update_table()
    app.run()
import pandas as pd
import tkinter as tk
from tkinter import messagebox, ttk, font
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
from pynput import mouse
from pathlib import Path
from datetime import datetime
from seller import run_selling_cycle
from thefuzz import fuzz

# Set up logging
logging.basicConfig(filename='log.txt', level=logging.INFO, format='%(asctime)s - %(message)s')

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
        self.root.title("Albion Online Buyer Script v2.1 (Refactored)")
        self.root.resizable(False, False)
        
        # Make window always on top initially
        self.root.attributes('-topmost', True)
        
        # --- Стили TTK ---
        self.style = ttk.Style(self.root)
        self.setup_styles()
        
        # --- Состояния ---
        self.sell_in_progress = False
        self.capturing = False
        self.capture_type = None
        self.mouse_listener = None
        self.region_start = None
        self.active_capture_button = None # Для сброса кнопки "Отмена"
        
        self.script_running = False
        self.script_thread = None
        self.log_entries = []
        self.skip_item = False
        
        self.paused = False
        self.pause_event = threading.Event()
        self.pause_event.set()  # Initially not paused
        
        # --- Инициализация GUI ---
        self.setup_gui()
        self.load_settings()
        
    def setup_styles(self):
        """Настройка стилей для ttk виджетов"""
        self.style.theme_use('clam')

        # Шрифты
        self.default_font = font.nametofont("TkDefaultFont")
        self.default_font.configure(family="Helvetica", size=10)
        self.header_font = ("Helvetica", 12, "bold")
        self.status_font = ("Helvetica", 10, "bold")

        # Конфигурация стилей
        self.style.configure('.', font=self.default_font)
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabel', background='#f0f0f0')
        self.style.configure('TButton', padding=5)
        self.style.configure('TEntry', padding=5)
        self.style.configure('TCheckbutton', background='#f0f0f0')
        
        self.style.configure('TNotebook', tabposition='n', background='#f0f0f0')
        self.style.configure('TNotebook.Tab', padding=(10, 5), font=("Helvetica", 10, "bold"))
        self.style.map('TNotebook.Tab', 
                       background=[('selected', '#e0e0e0'), ('active', '#f5f5f5')],
                       foreground=[('selected', '#000000')])

        self.style.configure('TLabelframe', padding=10, background='#f0f0f0')
        self.style.configure('TLabelframe.Label', font=("Helvetica", 10, "bold"), background='#f0f0f0')

        self.style.configure('Header.TLabel', font=self.header_font, background='#f0f0f0')
        self.style.configure('Status.TLabel', font=self.status_font, background='#f0f0f0')
        self.style.configure('Warning.TLabel', foreground='gray', background='#f0f0f0')

    def setup_gui(self):
        """Создание основного интерфейса с вкладками"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # --- Создание вкладок ---
        self.tab_main = self._create_main_tab(self.notebook)
        self.tab_coords = self._create_coords_tab(self.notebook)
        self.tab_ocr = self._create_ocr_tab(self.notebook)
        self.tab_settings = self._create_settings_tab(self.notebook)

        # --- Добавление вкладок ---
        self.notebook.add(self.tab_main, text=' Запуск ')
        self.notebook.add(self.tab_coords, text=' Координаты ')
        self.notebook.add(self.tab_ocr, text=' Области OCR ')
        self.notebook.add(self.tab_settings, text=' Настройки ')
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

    def _create_main_tab(self, parent):
        """Создает вкладку "Запуск" (статус, кнопки, лог)"""
        frame = ttk.Frame(parent, padding=10)
        
        # --- Статус ---
        status_frame = ttk.LabelFrame(frame, text="Статус", padding=10)
        status_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        status_frame.columnconfigure(0, weight=1)
        
        self.status_label = ttk.Label(status_frame, text="Готов к работе", style='Status.TLabel')
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        self.progress = ttk.Progressbar(status_frame, mode='determinate')
        self.progress.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.current_item_label = ttk.Label(status_frame, text="", justify=tk.LEFT, anchor=tk.W, wraplength=400)
        self.current_item_label.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5, ipady=30)
        
        # --- Управление ---
        control_frame = ttk.LabelFrame(frame, text="Управление", padding=10)
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=10)
        
        self.manual_btn = ttk.Button(control_frame, text="Ручная закупка", command=self.start_manual)
        self.manual_btn.grid(row=0, column=0, padx=5, pady=5, ipady=5, sticky='ew')
        
        self.order_btn = ttk.Button(control_frame, text="Закупка ордерами", command=self.start_order)
        self.order_btn.grid(row=0, column=1, padx=5, pady=5, ipady=5, sticky='ew')
        
        self.sell_btn = ttk.Button(control_frame, text="Продажа предметов", command=self.start_sell)
        self.sell_btn.grid(row=0, column=2, padx=5, pady=5, ipady=5, sticky='ew')
        
        self.save_btn = ttk.Button(control_frame, text="Сохранить настройки", command=self.save_settings)
        self.save_btn.grid(row=0, column=3, padx=5, pady=5, ipady=5, sticky='ew')
        
        control_frame.columnconfigure((0,1,2,3), weight=1)

        # --- Инструкции ---
        instructions_text = (
            "Горячие клавиши:\n"
            "F2 - Экстренная остановка скрипта\n"
            "F3 - Пропустить текущий предмет\n"
            "F4 - Пауза / Возобновление"
        )
        instructions = ttk.Label(frame, text=instructions_text, style='Warning.TLabel', justify=tk.LEFT)
        instructions.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=10)
        
        frame.columnconfigure(0, weight=1)
        return frame

    def _create_coords_tab(self, parent):
        """Создает вкладку "Координаты" (X, Y)"""
        frame = ttk.Frame(parent, padding=10)
        
        # --- Группа: Навигация ---
        nav_frame = ttk.LabelFrame(frame, text="Навигация", padding=10)
        nav_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(nav_frame, text="Search (X, Y):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.search_x_entry = ttk.Entry(nav_frame, width=10)
        self.search_x_entry.grid(row=0, column=1, padx=5)
        self.search_y_entry = ttk.Entry(nav_frame, width=10)
        self.search_y_entry.grid(row=0, column=2, padx=5)
        self.capture_search_btn = ttk.Button(nav_frame, text="Захватить", command=self.start_capture_search)
        self.capture_search_btn.grid(row=0, column=3, padx=5)
        
        ttk.Label(nav_frame, text="Clear (X, Y):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.clear_x_entry = ttk.Entry(nav_frame, width=10)
        self.clear_x_entry.grid(row=1, column=1, padx=5)
        self.clear_y_entry = ttk.Entry(nav_frame, width=10)
        self.clear_y_entry.grid(row=1, column=2, padx=5)
        self.capture_clear_btn = ttk.Button(nav_frame, text="Захватить", command=self.start_capture_clear)
        self.capture_clear_btn.grid(row=1, column=3, padx=5)

        # --- Группа: Покупка ---
        buy_frame = ttk.LabelFrame(frame, text="Покупка/Продажа", padding=10)
        buy_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(buy_frame, text="Buy/Sell (X, Y):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.buy_x_entry = ttk.Entry(buy_frame, width=10)
        self.buy_x_entry.grid(row=0, column=1, padx=5)
        self.buy_y_entry = ttk.Entry(buy_frame, width=10)
        self.buy_y_entry.grid(row=0, column=2, padx=5)
        self.capture_buy_btn = ttk.Button(buy_frame, text="Захватить", command=self.start_capture_buy)
        self.capture_buy_btn.grid(row=0, column=3, padx=5)

        ttk.Label(buy_frame, text="Confirm (X, Y):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.confirm_x_entry = ttk.Entry(buy_frame, width=10)
        self.confirm_x_entry.grid(row=1, column=1, padx=5)
        self.confirm_y_entry = ttk.Entry(buy_frame, width=10)
        self.confirm_y_entry.grid(row=1, column=2, padx=5)
        self.capture_confirm_btn = ttk.Button(buy_frame, text="Захватить", command=self.start_capture_confirm)
        self.capture_confirm_btn.grid(row=1, column=3, padx=5)

        ttk.Label(buy_frame, text="Quantity Input (X, Y):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.quantity_x_entry = ttk.Entry(buy_frame, width=10)
        self.quantity_x_entry.grid(row=2, column=1, padx=5)
        self.quantity_y_entry = ttk.Entry(buy_frame, width=10)
        self.quantity_y_entry.grid(row=2, column=2, padx=5)
        self.capture_quantity_btn = ttk.Button(buy_frame, text="Захватить", command=self.start_capture_quantity_input)
        self.capture_quantity_btn.grid(row=2, column=3, padx=5)
        
        ttk.Label(buy_frame, text="Close (Крестик) (X, Y):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.close_x_entry = ttk.Entry(buy_frame, width=10)
        self.close_x_entry.grid(row=3, column=1, padx=5)
        self.close_y_entry = ttk.Entry(buy_frame, width=10)
        self.close_y_entry.grid(row=3, column=2, padx=5)
        self.capture_close_btn = ttk.Button(buy_frame, text="Захватить", command=self.start_capture_close)
        self.capture_close_btn.grid(row=3, column=3, padx=5)

        # --- Группа: Ордера ---
        order_frame = ttk.LabelFrame(frame, text="Ордера", padding=10)
        order_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(order_frame, text="Buy Order (X, Y):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.buy_order_x_entry = ttk.Entry(order_frame, width=10)
        self.buy_order_x_entry.grid(row=0, column=1, padx=5)
        self.buy_order_y_entry = ttk.Entry(order_frame, width=10)
        self.buy_order_y_entry.grid(row=0, column=2, padx=5)
        self.capture_buy_order_btn = ttk.Button(order_frame, text="Захватить", command=self.start_capture_buy_order)
        self.capture_buy_order_btn.grid(row=0, column=3, padx=5)
        
        ttk.Label(order_frame, text="Price per Unit (X, Y):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.price_per_unit_x_entry = ttk.Entry(order_frame, width=10)
        self.price_per_unit_x_entry.grid(row=1, column=1, padx=5)
        self.price_per_unit_y_entry = ttk.Entry(order_frame, width=10)
        self.price_per_unit_y_entry.grid(row=1, column=2, padx=5)
        self.capture_price_per_unit_btn = ttk.Button(order_frame, text="Захватить", command=self.start_capture_price_per_unit)
        self.capture_price_per_unit_btn.grid(row=1, column=3, padx=5)
        
        ttk.Label(order_frame, text="Minus (X, Y):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.minus_x_entry = ttk.Entry(order_frame, width=10)
        self.minus_x_entry.grid(row=2, column=1, padx=5)
        self.minus_y_entry = ttk.Entry(order_frame, width=10)
        self.minus_y_entry.grid(row=2, column=2, padx=5)
        self.capture_minus_btn = ttk.Button(order_frame, text="Захватить", command=self.start_capture_minus)
        self.capture_minus_btn.grid(row=2, column=3, padx=5)

        # --- Группа: Прочее ---
        other_frame = ttk.LabelFrame(frame, text="Прочее", padding=10)
        other_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(other_frame, text="Quality (X, Y):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.quality_x_entry = ttk.Entry(other_frame, width=10)
        self.quality_x_entry.grid(row=0, column=1, padx=5)
        self.quality_y_entry = ttk.Entry(other_frame, width=10)
        self.quality_y_entry.grid(row=0, column=2, padx=5)
        self.capture_quality_btn = ttk.Button(other_frame, text="Захватить", command=self.start_capture_quality)
        self.capture_quality_btn.grid(row=0, column=3, padx=5)
        
        frame.columnconfigure(0, weight=1)
        return frame

    def _create_ocr_tab(self, parent):
        """Создает вкладку "Области OCR" (L, T, W, H)"""
        frame = ttk.Frame(parent, padding=10)
        
        # --- Область 1: Цена Покупки ---
        buy_price_frame = ttk.LabelFrame(frame, text="Цена Покупки (Ручная закупка)", padding=10)
        buy_price_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        self._create_region_widgets(buy_price_frame, 'left_entry', 'top_entry', 'width_entry', 'height_entry')
        self.capture_region_btn = ttk.Button(buy_price_frame, text="Захватить область", command=self.start_capture_region)
        self.capture_region_btn.grid(row=2, column=0, columnspan=4, pady=5, sticky='ew')
        
        # --- Область 2: Цена Продажи (Общая) ---
        sell_price_frame = ttk.LabelFrame(frame, text="Цена Продажи (Общая)", padding=10)
        sell_price_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        self._create_region_widgets(sell_price_frame, 'sell_left_entry', 'sell_top_entry', 'sell_width_entry', 'sell_height_entry')
        self.capture_sell_region_btn = ttk.Button(sell_price_frame, text="Захватить область", command=self.start_capture_sell_region)
        self.capture_sell_region_btn.grid(row=2, column=0, columnspan=4, pady=5, sticky='ew')
        
        # --- Область 3: Цена Продажи (Предмет) ---
        sell_item_price_frame = ttk.LabelFrame(frame, text="Цена Продажи (Цена предмета)", padding=10)
        sell_item_price_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        self._create_region_widgets(sell_item_price_frame, 'sell_item_price_left_entry', 'sell_item_price_top_entry', 'sell_item_price_width_entry', 'sell_item_price_height_entry')
        self.capture_sell_item_price_region_btn = ttk.Button(sell_item_price_frame, text="Захватить область", command=self.start_capture_sell_item_price_region)
        self.capture_sell_item_price_region_btn.grid(row=2, column=0, columnspan=4, pady=5, sticky='ew')

        # --- Область 4: Количество ---
        quantity_frame = ttk.LabelFrame(frame, text="Количество предметов", padding=10)
        quantity_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        self._create_region_widgets(quantity_frame, 'left_q_entry', 'top_q_entry', 'width_q_entry', 'height_q_entry')
        self.capture_quantity_region_btn = ttk.Button(quantity_frame, text="Захватить область", command=self.start_capture_quantity_region)
        self.capture_quantity_region_btn.grid(row=2, column=0, columnspan=4, pady=5, sticky='ew')
        
        # --- Область 5: Название Предмета ---
        item_name_frame = ttk.LabelFrame(frame, text="Название предмета", padding=10)
        item_name_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=5)
        self._create_region_widgets(item_name_frame, 'left_item_name_entry', 'top_item_name_entry', 'width_item_name_entry', 'height_item_name_entry')
        self.capture_item_name_region_btn = ttk.Button(item_name_frame, text="Захватить область", command=self.start_capture_item_name_region)
        self.capture_item_name_region_btn.grid(row=2, column=0, columnspan=4, pady=5, sticky='ew')

        frame.columnconfigure(0, weight=1)
        return frame

    def _create_region_widgets(self, parent, left_var, top_var, width_var, height_var):
        """Вспомогательная функция для создания L/T/W/H полей"""
        ttk.Label(parent, text="Left:").grid(row=0, column=0, sticky=tk.W, pady=2)
        setattr(self, left_var, ttk.Entry(parent, width=10))
        getattr(self, left_var).grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(parent, text="Top:").grid(row=0, column=2, sticky=tk.W, padx=(10,0), pady=2)
        setattr(self, top_var, ttk.Entry(parent, width=10))
        getattr(self, top_var).grid(row=0, column=3, padx=5, pady=2)
        
        ttk.Label(parent, text="Width:").grid(row=1, column=0, sticky=tk.W, pady=2)
        setattr(self, width_var, ttk.Entry(parent, width=10))
        getattr(self, width_var).grid(row=1, column=1, padx=5, pady=2)
        
        ttk.Label(parent, text="Height:").grid(row=1, column=2, sticky=tk.W, padx=(10,0), pady=2)
        setattr(self, height_var, ttk.Entry(parent, width=10))
        getattr(self, height_var).grid(row=1, column=3, padx=5, pady=2)
        
        parent.columnconfigure((1,3), weight=1)

    def _create_settings_tab(self, parent):
        """Создает вкладку "Настройки" (Бюджет, Задержки и т.д.)"""
        frame = ttk.Frame(parent, padding=10)

        settings_frame = ttk.LabelFrame(frame, text="Параметры закупки", padding=10)
        settings_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))

        ttk.Label(settings_frame, text="Бюджет:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.budget_entry = ttk.Entry(settings_frame, width=20)
        self.budget_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(settings_frame, text="Задержка действий (сек):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.delay_entry = ttk.Entry(settings_frame, width=20)
        self.delay_entry.grid(row=1, column=1, padx=5, pady=5)
        self.delay_entry.insert(0, "0.5")
        
        ttk.Label(settings_frame, text="С какой строки в таблице начать:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.start_row_entry = ttk.Entry(settings_frame, width=20)
        self.start_row_entry.grid(row=2, column=1, padx=5, pady=5)
        self.start_row_entry.insert(0, "1")
        
        ttk.Label(settings_frame, text="Общие затраты (сессия):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.cumulative_spent_entry = ttk.Entry(settings_frame, width=20)
        self.cumulative_spent_entry.grid(row=3, column=1, padx=5, pady=5)
        self.cumulative_spent_entry.insert(0, "0")
        
        self.tier6_only_var = tk.BooleanVar(value=False)
        self.tier6_only_check = ttk.Checkbutton(settings_frame, text="Закупать только 6 тир (мастер)", variable=self.tier6_only_var)
        self.tier6_only_check.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=10, padx=5)

        frame.columnconfigure(0, weight=1)
        return frame

    def update_current_item_info(self, name="", value="", ocr_price="", bought="", store="", limit_price="",budget="", total_spent=""):
        """Update the current item label with provided info"""
        try:
            total_spent_val = int(float(total_spent)) if total_spent else 0
            budget_val = int(float(budget)) if budget else 0
        except ValueError:
            total_spent_val = 0
            budget_val = 0
        text = (
            f"Текущий предмет: {name}\n"
            f"Цена на ЧР: {value}\n"
            f"Текущая цена: {ocr_price} / {limit_price} (Лимит)\n"
            f"Куплено: {bought} из {store}\n"
            f"Потрачено: {total_spent_val} из {budget_val}"
        )
        self.current_item_label.config(text=text)
        self.root.update_idletasks()
        
    def update_status(self, message):
        """Обновление статуса в GUI"""
        self.status_label.config(text=message)
        self.root.update_idletasks()
        
    # --------------------------------------------------------------------
    # РЕФАКТОРИНГ: УНИВЕРСАЛЬНЫЕ ФУНКЦИИ ЗАХВАТА
    # --------------------------------------------------------------------
    
    def _start_coordinate_capture_generic(self, capture_type, x_entry, y_entry, button):
        """Универсальная функция для захвата ОДНОЙ точки (X, Y)"""
        if self.capturing:
            return
        self.capturing = True
        self.capture_type = capture_type
        self.active_capture_button = button  # Сохраняем кнопку для сброса
        self.update_status(f"Кликните для захвата координат '{capture_type}'...")
        
        if button:
            button.config(text="Отмена", command=self.cancel_capture)
        
        def on_click(x, y, button_mouse, pressed):
            if button_mouse == mouse.Button.left and pressed:
                x_entry.delete(0, tk.END)
                x_entry.insert(0, str(x))
                y_entry.delete(0, tk.END)
                y_entry.insert(0, str(y))
                self.finish_capture(f"Координаты '{capture_type}' захвачены: ({x}, {y})")
                return False
        
        self.mouse_listener = mouse.Listener(on_click=on_click)
        self.mouse_listener.start()

    def _start_region_capture_generic(self, capture_type, l_entry, t_entry, w_entry, h_entry, button):
        """Универсальная функция для захвата ОБЛАСТИ (L, T, W, H)"""
        if self.capturing:
            return
        self.capturing = True
        self.capture_type = capture_type
        self.active_capture_button = button # Сохраняем кнопку для сброса
        self.update_status(f"Нажмите и перетащите, чтобы выделить '{capture_type}'...")
        
        if button:
            button.config(text="Отмена", command=self.cancel_capture)

        def on_click(x, y, button_mouse, pressed):
            if button_mouse == mouse.Button.left and pressed:
                self.region_start = (x, y)
                return True
            elif button_mouse == mouse.Button.left and not pressed and self.region_start:
                end_x, end_y = x, y
                start_x, start_y = self.region_start
                
                left = min(start_x, end_x)
                top = min(start_y, end_y)
                width = abs(end_x - start_x)
                height = abs(end_y - start_y)
                
                l_entry.delete(0, tk.END); l_entry.insert(0, str(left))
                t_entry.delete(0, tk.END); t_entry.insert(0, str(top))
                w_entry.delete(0, tk.END); w_entry.insert(0, str(width))
                h_entry.delete(0, tk.END); h_entry.insert(0, str(height))
                
                self.finish_capture(f"Область '{capture_type}' захвачена: {width}x{height}")
                return False
        
        self.mouse_listener = mouse.Listener(on_click=on_click)
        self.mouse_listener.start()

    # --------------------------------------------------------------------
    # ОБЕРТКИ ДЛЯ ЗАХВАТА (вызывают универсальные функции)
    # --------------------------------------------------------------------
    
    # --- Координаты (X, Y) ---
    def start_capture_search(self):
        self._start_coordinate_capture_generic('Search', self.search_x_entry, self.search_y_entry, self.capture_search_btn)
        
    def start_capture_buy(self):
        self._start_coordinate_capture_generic('Buy/Sell', self.buy_x_entry, self.buy_y_entry, self.capture_buy_btn)
        
    def start_capture_confirm(self):
        self._start_coordinate_capture_generic('Confirm', self.confirm_x_entry, self.confirm_y_entry, self.capture_confirm_btn)
        
    def start_capture_clear(self):
        self._start_coordinate_capture_generic('Clear', self.clear_x_entry, self.clear_y_entry, self.capture_clear_btn)
        
    def start_capture_quantity_input(self):
        self._start_coordinate_capture_generic('Quantity Input', self.quantity_x_entry, self.quantity_y_entry, self.capture_quantity_btn)
        
    def start_capture_buy_order(self):
        self._start_coordinate_capture_generic('Buy Order', self.buy_order_x_entry, self.buy_order_y_entry, self.capture_buy_order_btn)
        
    def start_capture_price_per_unit(self):
        self._start_coordinate_capture_generic('Price per Unit', self.price_per_unit_x_entry, self.price_per_unit_y_entry, self.capture_price_per_unit_btn)
        
    def start_capture_minus(self):
        self._start_coordinate_capture_generic('Minus', self.minus_x_entry, self.minus_y_entry, self.capture_minus_btn)
    
    def start_capture_close(self):
        self._start_coordinate_capture_generic('Close', self.close_x_entry, self.close_y_entry, self.capture_close_btn)

    def start_capture_quality(self):
        self._start_coordinate_capture_generic('Quality', self.quality_x_entry, self.quality_y_entry, self.capture_quality_btn)

    # --- Области (L, T, W, H) ---
    def start_capture_region(self):
        self._start_region_capture_generic('Цена Покупки', 
            self.left_entry, self.top_entry, self.width_entry, self.height_entry, 
            self.capture_region_btn)
        
    def start_capture_sell_region(self):
        self._start_region_capture_generic('Цена Продажи (Общая)', 
            self.sell_left_entry, self.sell_top_entry, self.sell_width_entry, self.sell_height_entry, 
            self.capture_sell_region_btn)

    def start_capture_sell_item_price_region(self):
        self._start_region_capture_generic('Цена Продажи (Предмет)', 
            self.sell_item_price_left_entry, self.sell_item_price_top_entry, self.sell_item_price_width_entry, self.sell_item_price_height_entry, 
            self.capture_sell_item_price_region_btn)
        
    def start_capture_quantity_region(self):
        self._start_region_capture_generic('Количество', 
            self.left_q_entry, self.top_q_entry, self.width_q_entry, self.height_q_entry, 
            self.capture_quantity_region_btn)
        
    def start_capture_item_name_region(self):
        self._start_region_capture_generic('Название Предмета', 
            self.left_item_name_entry, self.top_item_name_entry, self.width_item_name_entry, self.height_item_name_entry, 
            self.capture_item_name_region_btn)
        
    # --------------------------------------------------------------------
    # ЛОГИКА ЗАВЕРШЕНИЯ ЗАХВАТА (осталась без изменений)
    # --------------------------------------------------------------------
        
    def cancel_capture(self):
        if self.mouse_listener:
            self.mouse_listener.stop()
        self.finish_capture("Захват отменен")
        
    def finish_capture(self, message):
        self.capturing = False
        self.capture_type = None
        self.region_start = None
        self.active_capture_button = None # Сбрасываем активную кнопку
        self.update_status(message)
        
        # Сбрасываем ВСЕ кнопки захвата в их исходное состояние
        # (Этот блок остался от вашего кода и работает)
        self.capture_search_btn.config(text="Захватить", command=self.start_capture_search)
        self.capture_buy_btn.config(text="Захватить", command=self.start_capture_buy)
        self.capture_confirm_btn.config(text="Захватить", command=self.start_capture_confirm)
        self.capture_clear_btn.config(text="Захватить", command=self.start_capture_clear)
        self.capture_quantity_btn.config(text="Захватить", command=self.start_capture_quantity_input)
        self.capture_buy_order_btn.config(text="Захватить", command=self.start_capture_buy_order)
        self.capture_price_per_unit_btn.config(text="Захватить", command=self.start_capture_price_per_unit)
        self.capture_minus_btn.config(text="Захватить", command=self.start_capture_minus)
        self.capture_close_btn.config(text="Захватить", command=self.start_capture_close)
        self.capture_quality_btn.config(text="Захватить", command=self.start_capture_quality)
        
        self.capture_region_btn.config(text="Захватить область", command=self.start_capture_region)
        self.capture_sell_region_btn.config(text="Захватить область", command=self.start_capture_sell_region)
        self.capture_sell_item_price_region_btn.config(text="Захватить область", command=self.start_capture_sell_item_price_region)
        self.capture_quantity_region_btn.config(text="Захватить область", command=self.start_capture_quantity_region)
        self.capture_item_name_region_btn.config(text="Захватить область", command=self.start_capture_item_name_region)
        
    def validate_inputs(self):
        """Проверка введенных данных"""
        try:
            # Координаты
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
            int(self.close_x_entry.get())
            int(self.close_y_entry.get())
            int(self.quality_x_entry.get())
            int(self.quality_y_entry.get())
            
            # Области
            regions = [
                (self.left_entry, self.top_entry, self.width_entry, self.height_entry),
                (self.sell_left_entry, self.sell_top_entry, self.sell_width_entry, self.sell_height_entry),
                (self.sell_item_price_left_entry, self.sell_item_price_top_entry, self.sell_item_price_width_entry, self.sell_item_price_height_entry),
                (self.left_q_entry, self.top_q_entry, self.width_q_entry, self.height_q_entry),
                (self.left_item_name_entry, self.top_item_name_entry, self.width_item_name_entry, self.height_item_name_entry)
            ]
            
            for l, t, w, h in regions:
                if int(w.get()) <= 0 or int(h.get()) <= 0:
                    raise ValueError("Ширина и высота области должны быть положительными")
            
            # Настройки
            budget = int(self.budget_entry.get())
            delay = float(self.delay_entry.get())
            start_row = int(self.start_row_entry.get())
            
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
            # Координаты
            'search_x': self.search_x_entry.get(), 'search_y': self.search_y_entry.get(),
            'clear_x': self.clear_x_entry.get(), 'clear_y': self.clear_y_entry.get(),
            'buy_x': self.buy_x_entry.get(), 'buy_y': self.buy_y_entry.get(),
            'confirm_x': self.confirm_x_entry.get(), 'confirm_y': self.confirm_y_entry.get(),
            'quantity_x': self.quantity_x_entry.get(), 'quantity_y': self.quantity_y_entry.get(),
            'buy_order_x': self.buy_order_x_entry.get(), 'buy_order_y': self.buy_order_y_entry.get(),
            'price_per_unit_x': self.price_per_unit_x_entry.get(), 'price_per_unit_y': self.price_per_unit_y_entry.get(),
            'minus_x': self.minus_x_entry.get(), 'minus_y': self.minus_y_entry.get(),
            'close_x': self.close_x_entry.get(), 'close_y': self.close_y_entry.get(),
            'quality_x': self.quality_x_entry.get(), 'quality_y': self.quality_y_entry.get(),
            
            # Области OCR
            'left': self.left_entry.get(), 'top': self.top_entry.get(), 'width': self.width_entry.get(), 'height': self.height_entry.get(),
            'left_q': self.left_q_entry.get(), 'top_q': self.top_q_entry.get(), 'width_q': self.width_q_entry.get(), 'height_q': self.height_q_entry.get(),
            'left_item_name': self.left_item_name_entry.get(), 'top_item_name': self.top_item_name_entry.get(), 'width_item_name': self.width_item_name_entry.get(), 'height_item_name': self.height_item_name_entry.get(),
            'left_sell': self.sell_left_entry.get(), 'top_sell': self.sell_top_entry.get(), 'width_sell': self.sell_width_entry.get(), 'height_sell': self.sell_height_entry.get(),
            'left_sell_item_price': self.sell_item_price_left_entry.get(), 'top_sell_item_price': self.sell_item_price_top_entry.get(), 'width_sell_item_price': self.sell_item_price_width_entry.get(), 'height_sell_item_price': self.sell_item_price_height_entry.get(),
            
            # Настройки
            'cumulative_spent': self.cumulative_spent_entry.get(),
            'budget': self.budget_entry.get(),
            'delay': self.delay_entry.get(),
            'start_row': self.start_row_entry.get(),
            'tier6_only': self.tier6_only_var.get(),
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
                
                # Координаты
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
                self.minus_x_entry.insert(0, settings.get('minus_x', ''))
                self.minus_y_entry.insert(0, settings.get('minus_y', ''))
                self.close_x_entry.insert(0, settings.get('close_x', ''))
                self.close_y_entry.insert(0, settings.get('close_y', ''))
                self.quality_x_entry.insert(0, settings.get('quality_x', ''))
                self.quality_y_entry.insert(0, settings.get('quality_y', ''))
                
                # Области
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
                
                # Настройки
                self.cumulative_spent_entry.delete(0, tk.END)
                self.cumulative_spent_entry.insert(0, settings.get('cumulative_spent', '0'))
                self.budget_entry.insert(0, settings.get('budget', ''))
                self.delay_entry.delete(0, tk.END)
                self.delay_entry.insert(0, settings.get('delay', '0.5'))
                self.start_row_entry.delete(0, tk.END)
                self.start_row_entry.insert(0, settings.get('start_row', '1'))
                self.tier6_only_var.set(settings.get('tier6_only', False))
        except Exception as e:
            logging.warning(f"Не удалось загрузить настройки: {str(e)}")
            
    # --------------------------------------------------------------------
    # УПРАВЛЕНИЕ СКРИПТОМ (без изменений)
    # --------------------------------------------------------------------
    
    def emergency_stop(self):
        """Экстренная остановка скрипта"""
        self.script_running = False
        if self.paused:
            self.pause_event.set()
            self.paused = False
        self.update_status("Остановлено пользователем (F2)")
        self.update_current_item_info()  # Clear current item info
        
        # Разблокируем кнопки
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
            # Здесь может быть логика обновления, если она нужна
            print('Таблица успешно обновлена (симуляция)')
        except Exception as e:
            print(f'Не удалось обновить таблицу: {e}')

    # --------------------------------------------------------------------
    # ЗАПУСК РЕЖИМОВ (небольшие правки)
    # --------------------------------------------------------------------

    def _start_script_common(self, mode_name, countdown_func, *args):
        """Общая логика для запуска любого режима"""
        if self.script_running:
            return
            
        if not self.validate_inputs():
            return
        
        keyboard.add_hotkey('f2', self.emergency_stop)
        keyboard.add_hotkey('f3', self.skip_current_item)
        keyboard.add_hotkey('f4', self.toggle_pause)
            
        # Блокируем кнопки
        self.manual_btn.config(state='disabled')
        self.order_btn.config(state='disabled')
        self.sell_btn.config(state='disabled')
        self.progress.start()
        
        # Запуск обратного отсчета в потоке
        self.script_thread = threading.Thread(
            target=countdown_func, 
            args=(mode_name, *args), 
            daemon=True
        )
        self.script_thread.start()

    def _countdown_and_run(self, mode_name, run_function, *args):
        """Общий обратный отсчет"""
        try:
            for i in range(5, 0, -1):
                self.update_status(f"Запуск '{mode_name}' через {i} секунд...")
                time.sleep(1)
            
            self.script_running = True
            run_function(*args) # Вызов основной логики
            
        except Exception as e:
            self.emergency_stop()
            messagebox.showerror("Ошибка", f"Ошибка при запуске скрипта: {e}")

    def start_manual(self):
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
        
        self._start_script_common(
            "Ручная закупка",
            self._countdown_and_run,
            self.run_script_manual, # Функция, которую надо запустить
            search_x, search_y, clear_x, clear_y, buy_x, buy_y, confirm_x, confirm_y, 
            quantity_x, quantity_y, left, top, width, height, left_q, top_q, width_q, height_q, 
            budget, delay, start_row
        )
    
    def start_order(self):
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
        quality_x = int(self.quality_x_entry.get())
        quality_y = int(self.quality_y_entry.get())
        left = int(self.left_entry.get())
        top = int(self.top_entry.get())
        width = int(self.width_entry.get())
        height = int(self.height_entry.get())
        budget = int(self.budget_entry.get())
        delay = float(self.delay_entry.get())
        start_row = int(self.start_row_entry.get())
        
        self._start_script_common(
            "Закупка ордерами",
            self._countdown_and_run,
            self.run_script_order, # Функция, которую надо запустить
            search_x, search_y, clear_x, clear_y, buy_x, buy_y, confirm_x, confirm_y, 
            quantity_x, quantity_y, buy_order_x, buy_order_y, price_per_unit_x, price_per_unit_y, 
            left, top, width, height, budget, delay, start_row, quality_x, quality_y
        )

    # --------------------------------------------------------------------
    # ЛОГИКА ПРОВЕРКИ И OCR
    # --------------------------------------------------------------------

    def verify_item_name(self, expected_name, region):
        """
        Does a screenshot of the item name region, recognizes the text, 
        and does a "fuzzy" comparison with the expected name.
        Returns True if the names are similar enough, otherwise False.
        """
        try:
            screenshot = ImageGrab.grab(bbox=region)
            
            # Use a config that works well for single lines of text
            config = '--psm 7' 
            ocr_text = pytesseract.image_to_string(screenshot, lang='rus+eng', config=config).strip()

            # --- FUZZY MATCHING LOGIC ---
            # Normalize both strings for the best comparison
            # The replace('\n', ' ') is still important for multi-line items
            normalized_ocr = ocr_text.replace('\n', ' ').lower()
            normalized_expected = expected_name.lower().strip()

            # Calculate the similarity ratio (0 to 100)
            similarity_ratio = fuzz.ratio(normalized_expected, normalized_ocr)
            
            log_msg = (f"Fuzzy Name Check: Expected='{normalized_expected}', "
                       f"Recognized='{normalized_ocr}', Similarity={similarity_ratio}%")
            print(log_msg)
            logging.info(log_msg)
            self.log_entries.append(f"[{datetime.now()}] {log_msg}")

            # Set a threshold. 90% is a good starting point.
            # This will allow for about 1 wrong character for every 10 correct ones.
            similarity_threshold = 92 

            if similarity_ratio >= similarity_threshold:
                return True
            else:
                return False
                
        except Exception as e:
            error_msg = f"A critical error occurred while verifying the item name: {e}"
            print(error_msg)
            logging.error(error_msg)
            self.log_entries.append(f"[{datetime.now()}] {error_msg}")
            return False # Assume failure on any error

        
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

    # --------------------------------------------------------------------
    # ОСНОВНАЯ ЛОГИКА БОТА (без изменений)
    # --------------------------------------------------------------------
        
    def run_script_manual(self, search_x, search_y, clear_x, clear_y, buy_x, buy_y, confirm_x, confirm_y, 
                            quantity_x, quantity_y, left, top, width, height, left_q, top_q, width_q, height_q, 
                            budget, delay, start_row):
        self.log_entries = []
        total_spent = 0
        try:
            self.update_status("Загрузка данных из Excel и сортировка по прибыли...")
            self.log_entries.append(f"[{datetime.now()}] --- Начать сессию с сортировкой по прибыли ---")
            
            excel_file_path = Path(__file__).parent / 'table.xlsx'
            df = pd.read_excel(excel_file_path, sheet_name=0, header=0)
            
            # Сортировка DataFrame по колонке 'profit' в порядке убывания
            df = df.sort_values(by='profit', ascending=False).reset_index(drop=True)
            if self.tier6_only_var.get():
                df = df[df['name'].str.contains('мастер', case=False, na=False)].reset_index(drop=True)
            
            total_items = len(df)
            if total_items <= 0:
                raise ValueError("Таблица пуста")
            min_budget_threshold = 10000
            
            # Итерация по строкам, начиная с указанной
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
                    
                self.progress['value'] = ((index) / total_items) * 100
                self.update_status(f"Обрабатывается {index + 1}/{total_items}: {row['name']}")
                
                name = str(row['name']).strip()
                
                try:
                    value = int(row['value'])
                    store = int(row['store'])
                    present = float(row['present'])
                    weightforitem = float(row['weightforitem']) # <--- Ваша новая логика
                except (ValueError, TypeError) as e:
                    msg = f"Некорректные данные для {name} (value, store, present или weightforitem): {str(e)}. Пропускается."
                    print(msg)
                    logging.warning(msg)
                    self.log_entries.append(f"[{datetime.now()}] Ошибка: {msg}")
                    continue
                
                if value <= 0 or store <= 0 or present <= 0 or weightforitem < 0:
                    msg = f"Пропускается {name} (некорректные значения, < 0)"
                    print(msg)
                    logging.info(msg)
                    self.log_entries.append(f"[{datetime.now()}] Предупреждение: {msg}")
                    continue

                # Новая формула расчета пороговой цены
                transport_cost = weightforitem * 350
                limit_price = int((value * present) - transport_cost)

                # Проверка на рентабельность после учета веса
                if limit_price <= 0:
                    msg = f"Пропускается {name} (невыгоден после учета веса. Расчетный лимит: {limit_price})"
                    print(msg); logging.info(msg); self.log_entries.append(f"[{datetime.now()}] Предупреждение: {msg}")
                    continue
                
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
                        
                    # --- ШАГ 1: Распознаем цену из списка ---
                    try:
                        screenshot = ImageGrab.grab(bbox=(left, top, left + width, top + height))
                        ocr_text = pytesseract.image_to_string(screenshot, config='--psm 7 -c tessedit_char_whitelist=0123456789')
                        ocr_price = int(ocr_text.strip() or 0)
                        
                        msg = f"Текущая цена для {name}: {ocr_price}"
                        print(msg); logging.info(msg); self.log_entries.append(f"[{datetime.now()}] {msg}")
                        self.update_current_item_info(name=name, value=value, ocr_price=ocr_price, bought=bought, store=store, limit_price=limit_price, budget=budget, total_spent=total_spent)

                        if ocr_price == 0:
                            failed_ocr_attempts += 1
                            msg = f"OCR вернул 0. Попытка {failed_ocr_attempts}. Пропускаю."
                            print(msg); logging.warning(msg); self.log_entries.append(f"[{datetime.now()}] Предупреждение: {msg}")
                            time.sleep(delay)
                            continue

                        # --- ШАГ 2: Сравниваем цену с лимитом ---
                        if ocr_price > limit_price:
                            msg = f"Цена {ocr_price} не выгодна для {name} (лимит: {limit_price})"
                            print(msg); logging.info(msg); self.log_entries.append(f"[{datetime.now()}] {msg}")
                            break # Выходим из while, переходим к следующему предмету
                        
                        if total_spent + ocr_price > budget:
                            msg = f"Бюджет превышен ({total_spent + ocr_price} > {budget})."
                            print(msg); logging.info(msg); self.update_status("Бюджет превышен!"); self.log_entries.append(f"[{datetime.now()}] {msg}")
                            self.script_running = False
                            break
                        
                        failed_ocr_attempts = 0 # Сбрасываем счетчик, если цена распознана успешно
                        
                    except (ValueError, pytesseract.TesseractError) as e:
                        failed_ocr_attempts += 1
                        ocr_text_val = ocr_text if 'ocr_text' in locals() else ''
                        msg = f"OCR ошибка для {name} (попытка {failed_ocr_attempts}): '{ocr_text_val.strip()}' - {e}"
                        print(msg); logging.warning(msg); self.log_entries.append(f"[{datetime.now()}] Ошибка OCR: {msg}")
                        time.sleep(delay)
                        continue
                    
                    # --- ШАГ 3: Если цена выгодна, кликаем "Купить" ---
                    pyautogui.moveTo(buy_x, buy_y, duration=random.uniform(0.1, 0.2))
                    pyautogui.click()
                    time.sleep(random.uniform(0.3, 0.5))
                    
                    # --- ШАГ 4: Проверяем название предмета в окне покупки ---
                    item_name_region = (
                        int(self.left_item_name_entry.get()),
                        int(self.top_item_name_entry.get()),
                        int(self.left_item_name_entry.get()) + int(self.width_item_name_entry.get()),
                        int(self.top_item_name_entry.get()) + int(self.height_item_name_entry.get())
                    )
                    
                    if self.verify_item_name(name, item_name_region):
                        # --- ШАГ 5A: Имя совпало -> продолжаем покупку ---
                        try:
                            screenshot_q = ImageGrab.grab(bbox=(left_q, top_q, left_q + width_q, top_q + height_q))
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                            screenshot_path = screenshots_dir / f"quantity_{name.replace(':', '_')}_{timestamp}.png"
                            screenshot_q.save(screenshot_path)
                            data = pytesseract.image_to_data(screenshot_q, output_type=pytesseract.Output.DICT, config='--psm 7 -c tessedit_char_whitelist=0123456789')
                            
                            available_list = []
                            text = ""
                            for i in range(len(data['text'])):
                                if data['text'][i].strip() and int(data['conf'][i]) > -1:
                                    confidence = int(data['conf'][i])
                                    text = data['text'][i].strip()
                                    available_list.append((text, confidence))
                            
                            msg = f"OCR количества для {name}: '{text.strip()}', распознано как {available_list}, сохранен скриншот: {screenshot_path}"
                            print(msg); logging.info(msg); self.log_entries.append(f"[{datetime.now()}] {msg}")
                            
                            if available_list:
                                available_str = max(available_list, key=lambda x: x[1])[0]
                                available = int(available_str)
                            else:
                                available = 0

                            if available <= 0:
                                failed_ocr_attempts += 1
                                msg = f"Недопустимое количество для {name} (OCR: {text.strip()}). Попытка {failed_ocr_attempts}."
                                print(msg); logging.warning(msg); self.log_entries.append(f"[{datetime.now()}] Предупреждение: {msg}")
                                pyautogui.click(int(self.close_x_entry.get()), int(self.close_y_entry.get())) # Закрываем окно
                                time.sleep(delay)
                                continue

                            to_buy = min(available, store - bought)
                            batch_cost = ocr_price * to_buy
                            
                            if budget - total_spent < min_budget_threshold:
                                msg = f"Остаток бюджета ({budget - total_spent}) меньше порога ({min_budget_threshold}). Завершаем."
                                print(msg); logging.info(msg); self.log_entries.append(f"[{datetime.now()}] {msg}")
                                self.script_running = False
                                pyautogui.click(int(self.close_x_entry.get()), int(self.close_y_entry.get()))
                                break
                            
                            if total_spent + batch_cost > budget:
                                to_buy = (budget - total_spent) // ocr_price
                                if to_buy <= 0:
                                    msg = f"Бюджет исчерпан для {name}."
                                    print(msg); logging.info(msg); self.log_entries.append(f"[{datetime.now()}] {msg}")
                                    self.script_running = False
                                    pyautogui.click(int(self.close_x_entry.get()), int(self.close_y_entry.get()))
                                    break
                            
                            if to_buy == 1:
                                pyautogui.moveTo(confirm_x, confirm_y, duration=random.uniform(0.1, 0.2))
                                pyautogui.click()
                            else:
                                pyautogui.moveTo(quantity_x, quantity_y, duration=random.uniform(0.1, 0.2))
                                pyautogui.click(); time.sleep(random.uniform(0.1, 0.2))
                                keyboard.write(str(to_buy))
                                time.sleep(random.uniform(0.1, 0.2))
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
                            print(msg); logging.info(msg); self.log_entries.append(f"[{datetime.now()}] {msg}")
                            self.update_current_item_info(name=name, value=value, ocr_price=ocr_price, bought=bought, store=store, limit_price=limit_price, budget=budget, total_spent=total_spent)
                        
                        except Exception as e:
                            msg = f"Ошибка покупки: {str(e)}"
                            print(msg); logging.error(msg); self.log_entries.append(f"[{datetime.now()}] Ошибка: {msg}")
                            pyautogui.click(int(self.close_x_entry.get()), int(self.close_y_entry.get()))
                            break
                    else:
                        # --- ШАГ 5B: Имя не совпало -> кликаем "Крестик" и выходим ---
                        msg = f"Имя не совпало после клика на покупку ('{name}'). Отмена."
                        print(msg); logging.warning(msg); self.log_entries.append(f"[{datetime.now()}] {msg}")
                        
                        close_x = int(self.close_x_entry.get())
                        close_y = int(self.close_y_entry.get())
                        pyautogui.moveTo(close_x, close_y, duration=random.uniform(0.1, 0.2))
                        pyautogui.click()
                        time.sleep(delay)
                        break 

                self.skip_item = False
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
                new_cumulative = current_cumulative + session_spent
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
                        left, top, width, height, budget, delay, start_row, quality_x, quality_y):
        self.log_entries = []
        total_spent = 0
        try:
            self.update_status("Загрузка данных из Excel и сортировка по прибыли...")
            self.log_entries.append(f"[{datetime.now()}] --- Начало сессии закупки ордерами ---")

            excel_file_path = Path(__file__).parent / 'table.xlsx'
            df = pd.read_excel(excel_file_path, sheet_name=0, header=0)
            df['unit_profit'] = df['value'] * (1 - df['present'])
            df['total_profit'] = df['unit_profit'] * df['store']
            # df = df.sort_values(by='total_profit', ascending=False).reset_index(drop=True)

            if self.tier6_only_var.get():
                df = df[df['name'].str.contains('мастер', case=False, na=False)].reset_index(drop=True)

            
            total_items = len(df)
            if total_items == 0:
                raise ValueError("Таблица пуста")

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

                self.progress['value'] = ((index) / total_items) * 100
                name = str(row['name']).strip()
                self.update_status(f"Обрабатывается {index + 1}/{total_items}: {name}")

                try:
                    value = int(row['value'])
                    store = int(row['store'])
                    present = float(row['present'])
                    weightforitem = float(row['weightforitem'])
                except (ValueError, TypeError) as e:
                    msg = f"Ошибка данных для {name} (value, store, present или weightforitem): {e}. Пропускаю."
                    logging.warning(msg)
                    self.log_entries.append(f"[{datetime.now()}] {msg}")
                    continue

                if value <= 0 or store <= 0 or present <= 0 or weightforitem < 0:
                    msg = f"Пропуск {name} — некорректные значения (< 0)."
                    logging.info(msg)
                    self.log_entries.append(f"[{datetime.now()}] {msg}")
                    continue

                transport_cost = weightforitem * 350
                limit_price = int((value * present) - transport_cost)

                if limit_price <= 0:
                    msg = f"Пропускается {name} (невыгоден после учета веса. Расчетный лимит: {limit_price})"
                    print(msg); logging.info(msg)
                    self.log_entries.append(f"[{datetime.now()}] {msg}")
                    continue
                
                self.update_current_item_info(name=name, value=value, ocr_price="N/A", bought=0, store=store,
                                            limit_price=limit_price, budget=budget, total_spent=total_spent)

                pyautogui.moveTo(clear_x, clear_y, duration=random.uniform(0.1, 0.2))
                pyautogui.click()
                pyautogui.moveTo(search_x, search_y, duration=random.uniform(0.1, 0.2))
                pyautogui.click()
                time.sleep(0.2)
                keyboard.write(name)
                time.sleep(0.7)

                bought = 0
                if store > 30:
                    part_size = max(1, store // 3)
                else:
                    part_size = max(1, store // 10)

                while bought < store and self.script_running and not self.skip_item:
                    self.pause_event.wait()
                    if not self.script_running or self.skip_item:
                        break
                    if self.check_and_click_ok():
                        continue

                    try:
                        screenshot = ImageGrab.grab(bbox=(left, top, left + width, top + height))
                        ocr_text = pytesseract.image_to_string(screenshot,
                            config='--psm 7 -c tessedit_char_whitelist=0123456789')
                        ocr_price = int(ocr_text.strip() or 0)
                    except Exception as e:
                        msg = f"OCR ошибка для {name}: {e}"
                        print(msg); logging.warning(msg)
                        self.log_entries.append(f"[{datetime.now()}] {msg}")
                        time.sleep(delay)
                        continue
                    if not self.script_running or self.skip_item:
                        break

                    if ocr_price == 0 or ocr_price > limit_price:
                        msg = f"Цена {ocr_price} не выгодна для {name} (лимит: {limit_price}). Прекращаю закупку."
                        print(msg); logging.info(msg)
                        self.log_entries.append(f"[{datetime.now()}] {msg}")
                        break

                    remaining_budget = budget - total_spent
                    if remaining_budget < limit_price: 
                        msg = f"Бюджет закончился ({remaining_budget} < {limit_price}). Остановка закупки."
                        print(msg); logging.info(msg)
                        self.log_entries.append(f"[{datetime.now()}] {msg}")
                        self.script_running = False
                        break
                    
                    to_buy = min(part_size, store - bought)
                    batch_cost = to_buy * limit_price 
                    
                    if batch_cost > remaining_budget:
                        to_buy = max(1, remaining_budget // limit_price)
                        if to_buy <= 0:
                            msg = f"Бюджет исчерпан перед покупкой {name}."
                            print(msg); logging.info(msg)
                            self.log_entries.append(f"[{datetime.now()}] {msg}")
                            break
                            
                    pyautogui.moveTo(buy_x, buy_y, duration=random.uniform(0.1, 0.2))
                    pyautogui.click()
                    time.sleep(random.uniform(0.2, 0.4))
                    if not self.script_running or self.skip_item:
                        break                   
                    item_name_region = (
                        int(self.left_item_name_entry.get()),   
                        int(self.top_item_name_entry.get()),
                        int(self.left_item_name_entry.get()) + int(self.width_item_name_entry.get()),
                        int(self.top_item_name_entry.get()) + int(self.height_item_name_entry.get())
                    )
                    if not self.verify_item_name(name, item_name_region):
                        msg = f"Имя не совпало после клика на покупку ('{name}'). Отмена."
                        print(msg); logging.warning(msg)
                        self.log_entries.append(f"[{datetime.now()}] {msg}")
                        close_x = int(self.close_x_entry.get())
                        close_y = int(self.close_y_entry.get())
                        pyautogui.moveTo(close_x, close_y, duration=random.uniform(0.1, 0.2))
                        pyautogui.click()
                        time.sleep(delay)
                        break
                    
                    pyautogui.moveTo(buy_order_x, buy_order_y, duration=random.uniform(0.1, 0.2))
                    pyautogui.click()
                    time.sleep(random.uniform(0.2, 0.4))

                    pyautogui.moveTo(price_per_unit_x, price_per_unit_y, duration=random.uniform(0.1, 0.2))
                    pyautogui.click()
                    time.sleep(0.1)
                    keyboard.write(str(limit_price))
                    time.sleep(0.1)

                    pyautogui.moveTo(quantity_x, quantity_y, duration=random.uniform(0.1, 0.2))
                    pyautogui.click()
                    time.sleep(0.1)
                    keyboard.write(str(to_buy))
                    time.sleep(0.1)
                    if not self.script_running or self.skip_item:
                        break 
                    
                    pyautogui.moveTo(confirm_x, confirm_y, duration=random.uniform(0.1, 0.2))
                    pyautogui.click()
                    time.sleep(random.uniform(0.2, 0.3))
                    
                    self.check_and_click_yes() 
                    
                    time.sleep(random.uniform(0.1, 0.2))
                    self.check_and_click_ok() 

                    bought += to_buy
                    total_spent += limit_price * to_buy 

                    msg = (f"Выставлен ордер ({to_buy} шт.) на '{name}' по {limit_price} each. "
                        f"Всего в ордерах: {bought}/{store}. Зарезервировано: {total_spent}.")
                    print(msg); logging.info(msg)
                    self.log_entries.append(f"[{datetime.now()}] {msg}")
                    self.update_current_item_info(name=name, value=value, ocr_price=f"Ордер по {limit_price}", bought=bought,
                                                store=store, limit_price=limit_price, budget=budget,
                                                total_spent=total_spent)
                    
                    pyautogui.moveTo(clear_x, clear_y, duration=random.uniform(0.1, 0.2))
                    pyautogui.click()
                    pyautogui.moveTo(search_x, search_y, duration=random.uniform(0.1, 0.2))
                    pyautogui.click()
                    time.sleep(0.2)
                    keyboard.write(name)
                    time.sleep(0.5)
                    
                    if bought >= store:
                        break

                    time.sleep(random.uniform(delay, delay + 0.5))

                self.skip_item = False
                self.update_current_item_info()

            if self.script_running:
                msg = f"Закупка ордерами завершена. Всего зарезервировано: {total_spent}"
                print(msg)
                logging.info(msg)
                self.log_entries.append(f"[{datetime.now()}] --- Сессия завершена. Зарезервировано: {total_spent} ---")
                self.update_status(f"Завершено! Зарезервировано: {total_spent}")
                messagebox.showinfo("Завершено", msg)

        except Exception as e:
            error_msg = f"Критическая ошибка в run_script_order: {str(e)}"
            print(error_msg)
            logging.error(error_msg)
            self.update_status("Ошибка выполнения")
            self.log_entries.append(f"[{datetime.now()}] Критическая ошибка: {error_msg}")
            messagebox.showerror("Ошибка", error_msg)
        finally:
            try:
                current_cumulative = int(self.cumulative_spent_entry.get() or 0)
                session_spent = int(total_spent)
                new_cumulative = current_cumulative + session_spent
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
        # --- Сбор данных для `run_selling_cycle` ---
        try:
            coords = {
                "sell_button": (int(self.buy_x_entry.get()), int(self.buy_y_entry.get())),
                'minus_button': (int(self.minus_x_entry.get()), int(self.minus_y_entry.get())),
                "confirm_button": (int(self.confirm_x_entry.get()), int(self.confirm_y_entry.get())) 
            }

            regions = {
                'item_name': (int(self.left_item_name_entry.get()), int(self.top_item_name_entry.get()), int(self.width_item_name_entry.get()), int(self.height_item_name_entry.get())),
                'sale_price': (int(self.sell_left_entry.get()), int(self.sell_top_entry.get()), int(self.sell_width_entry.get()), int(self.sell_height_entry.get())),
                'buy_price': (int(self.sell_item_price_left_entry.get()), int(self.sell_item_price_top_entry.get()), int(self.sell_item_price_width_entry.get()), int(self.sell_item_price_height_entry.get())),
            }
        except ValueError as e:
            messagebox.showerror("Ошибка ввода", f"Некорректные данные для продажи (проверьте вкладки Координаты и OCR): {str(e)}")
            return
        
        # --- GUI Callbacks ---
        def gui_callback(action, data=None):
            if action == 'update_status':
                self.update_status(data)
            elif action == 'update_current_item_info':
                self.update_current_item_info(**data)
            elif action == 'pause_event_wait':
                self.pause_event.wait()
            elif action == 'is_running':
                return self.script_running
            
        # --- Запуск потока ---
        def run_wrapper():
            try:
                self.script_running = True
                
                success, message = run_selling_cycle(coords, regions, gui_callback)
                
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
                
        self._start_script_common(
            "Продажа",
            self._countdown_and_run,
            run_wrapper # Функция, которую надо запустить
        )
          
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = MarketBotGUI()
    app.update_table()
    app.run()
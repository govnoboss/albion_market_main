"""
Главное окно приложения Albion Market Scanner & Buyer
"""

import sys
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QLabel, QTabWidget, QTextEdit, QSplitter,
    QFrame, QCheckBox, QPushButton
)
from PyQt6.QtGui import QFont, QIcon

from .styles import MAIN_STYLE, COLORS
from .coordinate_panel import CoordinatePanel
from .control_panel import ControlPanel
from .items_panel import ItemsPanel
from .settings_panel import SettingsPanel  # Панель настроек
from .mini_overlay import MiniOverlay  # Импорт мини-оверлея
from ..utils.logger import get_logger
from ..utils.config import get_config
from ..core.bot import MarketBot  # Импорт бота


class LogViewer(QTextEdit):
    """Виджет для отображения логов"""
    
    def __init__(self):
        super().__init__()
        self.setObjectName("logViewer")
        self.setReadOnly(True)
        self.setMinimumHeight(120)
        
        # Подключаем логгер
        logger = get_logger()
        logger.connect_ui(self.add_log)
    
    def add_log(self, message: str, level: str):
        """Добавить сообщение в лог"""
        color_map = {
            "debug": COLORS["text_secondary"],
            "info": COLORS["text_primary"],
            "warning": COLORS["warning"],
            "error": COLORS["error"],
        }
        color = color_map.get(level, COLORS["text_primary"])
        
        # Форматируем с цветом
        html = f'<span style="color: {color};">{message}</span>'
        self.append(html)
        
        # Прокручиваем вниз
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


class MainWindow(QMainWindow):
    """Главное окно приложения"""
    
    # Сигнал для переключения по хоткею (из потока pynput в GUI поток)
    toggle_hotkey_signal = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        
        # Инициализация оверлея перед UI, чтобы можно было подключить логгер
        self.mini_overlay = MiniOverlay()
        self.mini_overlay.pause_clicked.connect(self._on_pause_bot)
        self.mini_overlay.stop_clicked.connect(self._on_stop_bot)
        self.mini_overlay.restore_clicked.connect(self._switch_to_normal_mode)
        
        self._setup_window()
        self._setup_ui()
        self._init_bot()
        
        # Настройка глобальных хоткеев
        self._setup_hotkeys()
        
        # Подключение логгера к оверлею
        # Используем lambda, чтобы передавать только сообщение или форматировать его
        logger = get_logger()
        logger.connect_ui(lambda msg, lvl: self.mini_overlay.set_last_log(msg))
        
        # Приветственное сообщение (после подключения UI)
        logger.info("Albion Market Scanner & Buyer запущен")
    
    def _setup_window(self):
        """Настройка окна"""
        self.setWindowTitle("Albion Market Scanner & Buyer")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        self.setStyleSheet(MAIN_STYLE)

    def _switch_to_mini_mode(self):
        """Переключение в мини-режим"""
        # Скрыть главное окно
        self.hide()
        
        # Позиционировать оверлей в правом верхнем углу (с небольшим отступом)
        screen_geo = QApplication.primaryScreen().availableGeometry()
        overlay_w = self.mini_overlay.width()
        overlay_h = self.mini_overlay.height()
        
        x = screen_geo.width() - overlay_w - 20
        y = screen_geo.top() + 20
        
        self.mini_overlay.move(x, y)
        self.mini_overlay.show()
        
    def _switch_to_normal_mode(self):
        """Переключение в обычный режим"""
        self.mini_overlay.hide()
        self.show()
        self.activateWindow()
    
    def _setup_hotkeys(self):
        """Настройка глобальной клавиши F5"""
        from pynput import keyboard
        
        def on_f5():
            self.toggle_hotkey_signal.emit()
            
        self.hotkey_listener = keyboard.GlobalHotKeys({
            '<f5>': on_f5
        })
        self.toggle_hotkey_signal.connect(self._toggle_bot_state)
        self.hotkey_listener.start()
        
    def _toggle_bot_state(self):
        """Переключение состояния бота (Start/Stop)"""
        if self.bot.isRunning():
            get_logger().info("F5: Остановка бота...")
            self._on_stop_bot()
        else:
            get_logger().info("F5: Запуск бота...")
            self._on_start_bot()

    def _setup_ui(self):
        """Создание UI"""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # === Заголовок ===
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        title = QLabel("👽 Albion Market Scanner")
        title.setObjectName("title")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Кнопка 'Мини режим'
        self.mini_mode_btn = QPushButton("↘ Mini Mode")
        self.mini_mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mini_mode_btn.setStyleSheet("""
            QPushButton { 
                background-color: #21262d; 
                color: #8b949e; 
                border: 1px solid #30363d; 
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 12px;
            }
            QPushButton:hover { 
                background-color: #30363d; 
                color: #f0f6fc; 
            }
        """)
        self.mini_mode_btn.clicked.connect(self._switch_to_mini_mode)
        header_layout.addWidget(self.mini_mode_btn)
        
        # Переключатель "Поверх всех окон"
        self.always_on_top_checkbox = QCheckBox("📌 Поверх всех окон")
        self.always_on_top_checkbox.setStyleSheet("""
            QCheckBox { color: #8b949e; font-size: 13px; spacing: 8px; }
            QCheckBox:checked { color: #3fb950; }
        """)
        self.always_on_top_checkbox.toggled.connect(self._toggle_always_on_top)
        header_layout.addWidget(self.always_on_top_checkbox)
        
        main_layout.addLayout(header_layout)
        
        # === Основные вкладки приложения (QTabWidget) ===
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; }
            QTabBar::tab { 
                background: #161b22; 
                color: #8b949e; 
                padding: 10px 20px; 
                border: 1px solid #30363d; 
                border-bottom: none; 
                border-top-left-radius: 6px; 
                border-top-right-radius: 6px; 
                margin-right: 4px;
                min-width: 120px;
            }
            QTabBar::tab:selected { 
                background: #0d1117; 
                color: #f0f6fc; 
                border-bottom-color: #0d1117; 
            }
            QTabBar::tab:hover {
                color: #f0f6fc;
            }
        """)
        
        # --- Вкладка 1: Главная (Управление) ---
        self.control_tab = QWidget()
        control_layout = QVBoxLayout(self.control_tab)
        
        self.control_panel = ControlPanel()
        self.control_panel.start_clicked.connect(self._on_start_bot)
        self.control_panel.stop_clicked.connect(self._on_stop_bot)
        self.control_panel.pause_clicked.connect(self._on_pause_bot)
        
        control_layout.addWidget(self.control_panel)
        self.tabs.addTab(self.control_tab, "🎮 Главная")
    
        # --- Вкладка 2: Предметы ---
        self.items_panel = ItemsPanel()
        self.tabs.addTab(self.items_panel, "📦 Предметы")

        # --- Вкладка 3: Координаты ---
        from .coordinates_tab import CoordinatesTab
        self.coords_tab = CoordinatesTab()
        self.tabs.addTab(self.coords_tab, "🗺️ Координаты")

        # --- Вкладка 4: Настройки ---
        self.settings_panel = SettingsPanel()
        self.tabs.addTab(self.settings_panel, "⚙️ Настройки")
        
        main_layout.addWidget(self.tabs, stretch=1)
        
        # === Панель логов (внизу, общая) ===
        log_frame = QFrame()
        log_frame.setStyleSheet("QFrame { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; }")
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(15, 10, 15, 10)
        log_layout.setSpacing(5)
        
        log_header = QLabel("📋 Журнал событий")
        log_header.setStyleSheet("font-size: 13px; font-weight: 600; color: #8b949e;")
        log_layout.addWidget(log_header)
        
        self.log_viewer = LogViewer()
        log_layout.addWidget(self.log_viewer)
        
        main_layout.addWidget(log_frame)

    def _init_bot(self):
        """Инициализация бота"""
        self.bot = MarketBot()
        self.bot.progress_updated.connect(self.control_panel.update_progress)
        self.bot.progress_updated.connect(self.mini_overlay.update_progress) # Sync to overlay
        self.bot.finished.connect(self._on_bot_finished)

        # Проверка OCR модуля (выведет статус в консоль при импорте)
        from ..utils.ocr import is_ocr_available
        is_ocr_available()
        
    def _on_start_bot(self):
        """Запуск бота"""
        if not self.bot.isRunning():
            self.bot.start()
            self.control_panel.set_running_state(True)
            self.mini_overlay.update_status(True, False)
            # Автоматический переход в мини-режим
            self._switch_to_mini_mode()

    def _on_pause_bot(self):
        """Пауза бота"""
        self.bot.pause()
        # Обновляем состояние в оверлее
        is_paused = self.bot._is_paused
        self.mini_overlay.update_status(True, is_paused)
            
    def _on_stop_bot(self):
        """Остановка бота"""
        if self.bot.isRunning():
            self.bot.stop()
            self.bot.wait()
            self.control_panel.set_running_state(False)
            self.mini_overlay.update_status(False, False)
            # Автоматический возврат в обычный режим
            self._switch_to_normal_mode()
            
    def _on_bot_finished(self):
        """Бот завершил работу"""
        self.control_panel.set_running_state(False)
        self.control_panel.update_progress(0, 0, "Завершено")
        self.mini_overlay.update_status(False, False)
        self.mini_overlay.update_progress(0, 0, "Завершено")
        # Автоматический возврат в обычный режим
        self._switch_to_normal_mode()
        
    def _toggle_always_on_top(self, checked: bool):
        """Переключить режим 'поверх всех окон'"""
        if checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
            get_logger().info("Режим 'Поверх всех окон' включен")
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
            get_logger().info("Режим 'Поверх всех окон' выключен")
        self.show()
    
    def closeEvent(self, event):
        """Обработчик закрытия окна"""
        # Close hotkey listener
        if hasattr(self, 'hotkey_listener') and self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
            except:
                pass
                
        if self.bot.isRunning():
            self.bot.stop()
            self.bot.wait()
        
        # Close overlay too
        self.mini_overlay.close()
        
        get_logger().info("Приложение закрыто")
        event.accept()


def run_app():
    """Запуск приложения"""
    app = QApplication(sys.argv)
    
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

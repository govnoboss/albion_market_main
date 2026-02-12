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
from .control_panel import ControlPanel
from .items_panel import ItemsPanel
from .settings_panel import SettingsPanel  # Панель настроек
from .mini_overlay import MiniOverlay  # Импорт мини-оверлея
from ..utils.logger import get_logger
from ..utils.config import get_config
from ..core.bot import MarketBot  # Импорт бота
from .log_overlay import LogOverlay  # Импорт лог-оверлея


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
    pause_hotkey_signal = pyqtSignal()
    
    def __init__(self, launcher=None):
        with open("debug_startup.log", "a", encoding="utf-8") as f: f.write("DEBUG: MainWindow.__init__ started\n")
        super().__init__()
        self.launcher = launcher
        
        # Инициализация оверлея перед UI, чтобы можно было подключить логгер
        self.mini_overlay = MiniOverlay()
        self.mini_overlay.start_clicked.connect(self._on_start_bot)
        self.mini_overlay.pause_clicked.connect(self._on_pause_bot)
        self.mini_overlay.stop_clicked.connect(self._on_stop_bot)
        self.mini_overlay.stop_clicked.connect(self._on_stop_bot)
        self.mini_overlay.restore_clicked.connect(self._switch_to_normal_mode)
        
        # Инициализация Log Overlay
        self.log_overlay = LogOverlay()
        
        self._setup_window()
        self._setup_ui()
        self._init_bot()
        
        # Настройка глобальных хоткеев
        self._setup_hotkeys()
        
        # Подключение логгера к оверлею
        # Используем lambda, чтобы передавать только сообщение или форматировать его
        logger = get_logger()
        # logger.connect_ui(lambda msg, lvl: self.mini_overlay.set_last_log(msg)) # Removed
        
        # Filter for LogOverlay: Show prices, errors, warnings, and status
        def log_filter(msg, lvl):
            # Always show errors and warnings
            if lvl.lower() in ["error", "warning", "critical", "success"]:
                self.log_overlay.add_log(msg, lvl)
                return

            # Show status messages
            if any(x in msg for x in ["Запуск", "Остановка", "Start", "Stop", "Paused", "Пауза", "Завершено"]):
                self.log_overlay.add_log(msg, lvl)
                return

            # Show price indicators (main goal)
            if any(x in msg for x in ["💰", "Цена:", "Price:", "Профит:", "Profit:"]):
                 self.log_overlay.add_log(msg, lvl)
                 
        logger.connect_ui(log_filter)
        
        # Приветственное сообщение (после подключения UI)
        logger.info("Albion Market Scanner & Buyer запущен")
    
    def _setup_window(self):
        """Настройка окна"""
        self.setWindowTitle("Albion Market Scanner & Buyer")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        self.setStyleSheet(MAIN_STYLE)

    def _switch_to_mini_mode(self):
        """Переключение в мини-режим"""
        self.is_mini_mode = True
        # Скрыть главное окно
        self.hide()
        
        # Позиционировать оверлей по ЦЕНТРУ сверху (чтобы не закрывать Settings/Avatar)
        screen_geo = QApplication.primaryScreen().availableGeometry()
        overlay_w = self.mini_overlay.width()
        
        x = (screen_geo.width() - overlay_w) // 2
        y = screen_geo.top() + 20
        
        self.mini_overlay.move(x, y)
        self.mini_overlay.show()
        
    def _switch_to_normal_mode(self):
        """Переключение в обычный режим"""
        self.is_mini_mode = False
        self.mini_overlay.hide()
        self.show()
        self.activateWindow()
    
    def _setup_hotkeys(self):
        """Настройка глобальной клавиши F5"""
        from pynput import keyboard
        
        def on_f5():
            self.toggle_hotkey_signal.emit()

        def on_f6():
            self.pause_hotkey_signal.emit()
            
        # Сохраняем листенер, но не запускаем его сразу
        self.hotkey_listener = keyboard.GlobalHotKeys({
            '<f5>': on_f5,
            '<f6>': on_f6
        })
        
        # Подключаем сигналы только один раз
        if not hasattr(self, '_signals_connected'):
            self.toggle_hotkey_signal.connect(self._toggle_bot_state)
            self.pause_hotkey_signal.connect(self._on_pause_bot)
            self._signals_connected = True
        
    def showEvent(self, event):
        """Включаем хоткеи при показе окна"""
        super().showEvent(event)
        if not hasattr(self, 'hotkey_listener'):
            self._setup_hotkeys()
            
        try:
            if not self.hotkey_listener.running:
                self.hotkey_listener.start()
        except RuntimeError:
            # Если listener был остановлен, его нельзя перезапустить - нужно создать новый
            self._setup_hotkeys()
            self.hotkey_listener.start()

    def hideEvent(self, event):
        """Выключаем хоткеи при скрытии окна"""
        super().hideEvent(event)
        
        # Если это просто сворачивание в мини-режим, не выключаем хоткеи!
        if getattr(self, 'is_mini_mode', False):
            return
            
        if hasattr(self, 'hotkey_listener') and self.hotkey_listener.running:
            self.hotkey_listener.stop()
        
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
        
        title = QLabel("GBot Market Scanner")
        title.setObjectName("title")
        header_layout.addWidget(title)
        
        hotkeys_info = QLabel("  [ F5: Start/Stop  |  F6: Pause ]")
        hotkeys_info.setStyleSheet("color: #636e7b; font-size: 12px; font-weight: bold;")
        header_layout.addWidget(hotkeys_info)
        
        header_layout.addStretch()
        
        # Кнопка 'Меню' (если запущен через лаунчер)
        if self.launcher:
            menu_btn = QPushButton("Меню")
            menu_btn.setFixedSize(100, 30)
            menu_btn.setStyleSheet("""
                QPushButton { background: #21262d; color: #8b949e; border: 1px solid #30363d; border-radius: 4px; padding: 5px 15px; font-size: 13px; }
                QPushButton:hover { background: #30363d; color: #f0f6fc; }
            """)
            menu_btn.clicked.connect(self.close) # Закрытие вернет в меню через closeEvent
            header_layout.addWidget(menu_btn)
        
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
                padding: 10px 15px; 
                border: 1px solid #30363d; 
                border-bottom: none; 
                border-top-left-radius: 6px; 
                border-top-right-radius: 6px; 
                margin-right: 4px;
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
        
        # === Панель логов (только для вкладки Главная) ===
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
        
        control_layout.addWidget(log_frame)
        
        self.tabs.addTab(self.control_tab, "🎮 Главная")
    
        # --- Вкладка 2: Профиты (NEW) ---
        from .profits_tab import ProfitsTab
        self.profits_tab = ProfitsTab()
        self.tabs.addTab(self.profits_tab, "📈 Профиты")

        # --- Вкладка 3: Цены ---
        from .prices_tab import PricesTab
        self.prices_tab = PricesTab()
        self.tabs.addTab(self.prices_tab, "💰 Цены")

        # --- Вкладка 4: Предметы ---
        self.items_panel = ItemsPanel()
        self.tabs.addTab(self.items_panel, "📦 Предметы")

        # --- Вкладка 5: Координаты ---
        from .coordinates_tab import CoordinatesTab
        self.coords_tab = CoordinatesTab()
        self.tabs.addTab(self.coords_tab, "🗺️ Координаты")

        # --- Вкладка 6: Настройки ---
        self.settings_panel = SettingsPanel()
        self.tabs.addTab(self.settings_panel, "⚙️ Настройки")
        
        main_layout.addWidget(self.tabs, stretch=1)

    def _init_bot(self):
        """Инициализация бота"""
        self.bot = MarketBot()
        self.bot.progress_updated.connect(self.control_panel.update_progress)
        self.bot.progress_updated.connect(self.mini_overlay.update_progress) # Sync to overlay
        self.bot.finished.connect(self._on_bot_finished)
        self.bot.overlay_status.connect(self._on_overlay_status_changed) # Connect overlay visibility signal

        # Проверка OCR модуля (выведет статус в консоль при импорте)
        from ..utils.ocr import is_ocr_available
        is_ocr_available()
        
    def _on_start_bot(self):
        """Запуск бота"""
        if not self.bot.isRunning():
            # self.mini_overlay.clear_logs() # Removed
            # Получаем стартовый индекс (spinbox 1-based -> list 0-based)
            start_index = self.control_panel.start_index_spin.value() - 1
            self.bot.start_index = start_index
            
            self.bot.start()
            self.control_panel.set_running_state(True)
            self.mini_overlay.update_status(True, False)
            # Показываем лог-оверлей при старте
            self.log_overlay.show()
            self.log_overlay.clear_logs()
            
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
            self.control_panel.refresh_resume_button()  # Обновляем кнопку "Продолжить"
            self.mini_overlay.update_status(False, False)
            self.log_overlay.hide()
            # Автоматический возврат в обычный режим
            self._switch_to_normal_mode()
            
    def _on_bot_finished(self):
        """Бот завершил работу"""
        self.control_panel.set_running_state(False)
        self.control_panel.update_progress(0, 0, "Завершено")
        self.control_panel.refresh_resume_button()  # Обновляем кнопку "Продолжить"
        self.mini_overlay.update_status(False, False)
        self.mini_overlay.update_progress(0, 0, "Завершено")
        self.log_overlay.hide()
        # Автоматический возврат в обычный режим
        self._switch_to_normal_mode()
        
    def _on_overlay_status_changed(self, visible: bool):
        """Обработка сигнала видимости оверлея"""
        if visible:
            # Show only if bot is running (don't show if stopped)
            if self.bot.isRunning():
                self.log_overlay.show()
        else:
            self.log_overlay.hide()
        
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
        self.log_overlay.close()
        
        # Если есть лаунчер -> возвращаемся в меню
        if self.launcher:
            self.launcher.show()
            get_logger().info("Возврат в главное меню")
        else:
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

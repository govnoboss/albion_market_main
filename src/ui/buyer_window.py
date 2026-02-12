from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFrame, QTextEdit, QGroupBox,
    QMessageBox, QTabWidget, QScrollArea, QSpinBox
)
from PyQt6.QtGui import QIntValidator
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QFont

from .styles import MAIN_STYLE, COLORS
from .log_overlay import LogOverlay  # Импорт лог-оверлея

class BuyerWindow(QMainWindow):
    """
    Отдельное окно для режима 'ЗАКУПЩИК'.
    Фокусируется на автоматической покупке предметов по выгодным ценам.
    """
    
    
    # Signals for thread-safe hotkey handling
    hotkey_stop_sig = pyqtSignal()
    hotkey_pause_sig = pyqtSignal()
    hotkey_toggle_sig = pyqtSignal() # F5 Toggle

    def __init__(self, launcher=None):
        super().__init__()
        self.launcher = launcher
        self.setWindowTitle("GBot - Закупщик")
        self.resize(720, 550) 
        self.setStyleSheet(MAIN_STYLE)
        
        # State
        self.last_mode = "wholesale" # Default start mode for F5
        self._is_starting = False  # Блокировка двойного запуска
        
        # Основной контейнер
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # === Глобальный заголовок (над всеми вкладками) ===
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        title = QLabel("🛒 GBot Закупщик")
        title.setStyleSheet("font-size: 18px; color: #3fb950; font-weight: bold;")
        header_layout.addWidget(title)
        
        hotkeys_info = QLabel("  [ F5: Start/Stop  |  F6: Pause ]")
        hotkeys_info.setStyleSheet("color: #636e7b; font-size: 12px; font-weight: bold;")
        header_layout.addWidget(hotkeys_info)
        
        header_layout.addStretch()
        
        # Кнопка 'Меню' (всегда видна)
        if self.launcher:
            menu_btn = QPushButton("Меню")
            menu_btn.setFixedSize(80, 30)
            menu_btn.setStyleSheet("""
                QPushButton { background: #21262d; color: #8b949e; border: 1px solid #30363d; border-radius: 4px; }
                QPushButton:hover { background: #30363d; color: #f0f6fc; }
            """)
            menu_btn.clicked.connect(self._on_back_clicked)
            header_layout.addWidget(menu_btn)
        
        main_layout.addLayout(header_layout)
        
        # === Вкладки ===
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; }
            QTabBar::tab { 
                background: #161b22; 
                color: #8b949e; 
                padding: 10px 15px; 
                border: 1px solid #30363d;
                border-bottom: none;
                margin-right: 2px;
            }
            QTabBar::tab:selected { 
                background: #0d1117; 
                color: #f0f6fc; 
            }
        """)
        main_layout.addWidget(self.tabs)

        # --- Вкладка 1: Управление (Monitor) ---
        self.monitor_tab = QWidget()
        self.monitor_layout = QVBoxLayout(self.monitor_tab)
        self.monitor_layout.setSpacing(15)
        self.monitor_layout.setContentsMargins(10, 10, 10, 10)
        
        self._setup_controls(self.monitor_layout)
        self._setup_log_area(self.monitor_layout)
        
        self.tabs.addTab(self.monitor_tab, "🎮 Главная")
        
        # --- Вкладка 2: План закупки ---
        from .buyer.purchase_plan_tab import PurchasePlanTab
        self.plan_tab = PurchasePlanTab()
        self.tabs.addTab(self.plan_tab, "📋 План закупки")
        
        # --- Вкладка 3: Координаты ---
        from .coordinates_tab import CoordinatesTab
        self.coords_tab = CoordinatesTab()
        self.tabs.addTab(self.coords_tab, "📍 Координаты")
        
        # --- Вкладка 4: Настройки (из сканера) ---
        from .settings_panel import SettingsPanel
        self.settings_tab = SettingsPanel()
        self.tabs.addTab(self.settings_tab, "⚙️ Настройки")
        
        # --- Вкладка 5: Профиты (из сканера) ---
        from .profits_tab import ProfitsTab
        self.profit_tab = ProfitsTab()
        self.tabs.addTab(self.profit_tab, "📊 Профиты")
        
        # Connect Hotkey Signals (Thread-Safe)
        self.hotkey_stop_sig.connect(self._on_stop_clicked)
        self.hotkey_pause_sig.connect(self._toggle_pause)
        self.hotkey_toggle_sig.connect(self._toggle_bot)



    def _setup_controls(self, layout):
        """Основные кнопки управления"""
        control_group = QGroupBox("Управление")
        ctrl_layout = QVBoxLayout(control_group)
        ctrl_layout.setSpacing(10)
        
        # Бюджет
        budget_layout = QHBoxLayout()
        budget_lbl = QLabel("Бюджет:")
        budget_lbl.setStyleSheet("color: #8b949e; font-weight: bold;")
        
        self.budget_spin = QSpinBox()
        self.budget_spin.setRange(0, 999_999_999)
        self.budget_spin.setSingleStep(100_000)
        self.budget_spin.setSpecialValueText("Безлимит")
        self.budget_spin.setValue(0)
        self.budget_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)  # Убираем +/-
        self.budget_spin.setStyleSheet("""
            QSpinBox { 
                background: #0d1117; 
                color: #c9d1d9; 
                border: 1px solid #30363d; 
                padding: 8px; 
                font-size: 13px;
                border-radius: 4px;
            }
            QSpinBox:focus {
                border: 1px solid #58a6ff;
            }
        """)
        
        budget_layout.addWidget(budget_lbl)
        budget_layout.addWidget(self.budget_spin)
        ctrl_layout.addLayout(budget_layout)

        # Кнопка СТАРТ
        self.start_btn = QPushButton("▶ Старт")
        self.start_btn.setObjectName("primary")
        self.start_btn.setMinimumHeight(45)
        self.start_btn.setStyleSheet("font-size: 14px; font-weight: bold; background-color: #238636;")
        self.start_btn.clicked.connect(self._on_start_clicked)
        ctrl_layout.addWidget(self.start_btn)
        
        # Чекбокс "Умный закупщик"
        from PyQt6.QtWidgets import QCheckBox
        self.smart_mode_check = QCheckBox("🧠 Умный закупщик (Smart Buyer)")
        self.smart_mode_check.setToolTip("Покупать самые выгодные товары на основе сканирования,\nа не по фиксированному списку.")
        self.smart_mode_check.setStyleSheet("color: #c9d1d9; font-weight: bold; padding: 4px;")
        ctrl_layout.addWidget(self.smart_mode_check)
        
        # Чекбокс "Сортировать по %"
        self.sort_by_percent_check = QCheckBox("   📊 Сортировать по % профита")
        self.sort_by_percent_check.setToolTip("Если включено — приоритет предметам с высоким процентом прибыли.\nЕсли выключено — приоритет предметам с высокой абсолютной прибылью в серебре.")
        self.sort_by_percent_check.setStyleSheet("color: #8b949e; margin-left: 20px;")
        self.sort_by_percent_check.setVisible(False)  # Скрыт по умолчанию
        ctrl_layout.addWidget(self.sort_by_percent_check)
        
        # Связываем видимость с smart_mode_check
        self.smart_mode_check.toggled.connect(self.sort_by_percent_check.setVisible)

        
        # Кнопка СТОП
        self.stop_btn = QPushButton("⏹ ОСТАНОВИТЬ (F5)")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setVisible(False)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        ctrl_layout.addWidget(self.stop_btn)
        

        
        layout.addWidget(control_group)

        # --- BOT LOGIC & OVERLAY ---
        from ..core.buyer import BuyerBot
        from .mini_overlay import MiniOverlay
        import keyboard
        
        self.bot = BuyerBot()
        self.overlay = MiniOverlay()
        
        # Connect Bot Signals
        self.bot.progress_updated.connect(self._on_progress)
        self.bot.finished.connect(self._on_finished)
        
        # Connect Overlay Signals
        self.overlay.stop_clicked.connect(self._on_stop_clicked)
        self.overlay.pause_clicked.connect(self._toggle_pause)
        self.overlay.restore_clicked.connect(self._restore_window)
        
        # Log Overlay
        self.log_overlay = LogOverlay()
        
        # Connect Logger to LogOverlay
        from ..utils.logger import get_logger
        logger = get_logger()
        logger.connect_ui(lambda msg, lvl: self.log_overlay.add_log(msg, lvl))
        
        # Хоткеи регистрируются в showEvent, убираются в hideEvent
        self._hotkeys_registered = False

    def _setup_log_area(self, layout):
        """Лог событий"""
        self.log_viewer = QTextEdit()
        self.log_viewer.setObjectName("logViewer")
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setPlaceholderText("Лог событий закупки...")
        self.log_viewer.setMaximumHeight(100)
        layout.addWidget(self.log_viewer)

    def showEvent(self, event):
        """Регистрация хоткеев при показе окна"""
        super().showEvent(event)
        if not self._hotkeys_registered:
            import keyboard
            try:
                keyboard.add_hotkey("F5", self.hotkey_toggle_sig.emit)
                keyboard.add_hotkey("F6", self.hotkey_pause_sig.emit)
                self._hotkeys_registered = True
            except Exception as e:
                print(f"Ошибка регистрации хоткеев Buyer: {e}")
    
    def hideEvent(self, event):
        """Удаление хоткеев при скрытии окна"""
        super().hideEvent(event)
        
        # Если это просто сворачивание в мини-режим, не выключаем хоткеи!
        if getattr(self, 'is_mini_mode', False):
            return

        if self._hotkeys_registered:
            import keyboard
            try:
                keyboard.remove_hotkey("F5")
                keyboard.remove_hotkey("F6")
                self._hotkeys_registered = False
            except Exception as e:
                pass  # Игнорируем если хоткеи уже удалены

    def _toggle_bot(self):
        """Переключить состояние бота (Start/Stop)"""
        if self.bot.isRunning():
            self._on_stop_clicked()
        else:
            self._on_start_clicked()

    def _on_start_clicked(self):
        # Блокировка двойного запуска
        if self._is_starting or self.bot.isRunning():
            return
        self._is_starting = True
        
        # 0. Проверка наличия данных о ценах
        from ..utils.price_storage import price_storage
        from datetime import datetime
        
        cities = price_storage.get_cities()
        bm_prices = price_storage.get_city_prices("Black Market")
        
        if not cities or len(cities) == 0:
            QMessageBox.warning(
                self,
                "⚠️ Нет данных",
                "Таблица профитов пуста!\n\n"
                "Сначала запустите Сканер для сбора цен,\n"
                "затем возвращайтесь в Закупщик."
            )
            self._is_starting = False
            return
        
        if not bm_prices or len(bm_prices) == 0:
            QMessageBox.warning(
                self,
                "⚠️ Нет цен ЧР",
                "Нет данных о ценах Чёрного Рынка!\n\n"
                "Без них невозможно рассчитать профит.\n"
                "Сначала просканируйте ЧР."
            )
            self._is_starting = False
            return
        
        is_smart = self.smart_mode_check.isChecked()
        
        if is_smart:
            
            # Simple check: Iterate valid items in current config city (if known) or just all cities
            # Since we don't know the city yet (bot detects it), we check ALL data?
            # Or assume Config uses current location?
            # Let's check "Any stale data" in the storage.
            
            has_stale = False
            
            # Helper to check
            now = datetime.now()
            hours_threshold = 10
            
            # Direct access to verify (Optimization: backend execution)
            # We can use a simple logic: Check ALL items.
            cities = price_storage.get_cities()
            for city in cities:
                if city == "Black Market": continue 
                
                prices = price_storage.get_city_prices(city)
                for item, variants in prices.items():
                    for variant, data in variants.items():
                        try:
                            updated = datetime.fromisoformat(data['updated'])
                            age = (now - updated).total_seconds() / 3600
                            if age > hours_threshold:
                                has_stale = True
                                break
                        except: pass
                    if has_stale: break
                if has_stale: break
            
            if has_stale:
                reply = QMessageBox.question(
                    self, 
                    "⚠️ Данные устарели",
                    f"Найдена информация о ценах старше {hours_threshold} часов.\n"
                    "Рынок мог измениться. Продолжить?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    self._is_starting = False
                    return

        self.log_viewer.clear()
        # self.overlay.clear_logs()  # Removed
        mode_str = "🧠 УМНЫЙ" if is_smart else "📦 СТАНДАРТНЫЙ"
        self.log_viewer.append(f"🚀 Инициализация... Режим: {mode_str}")
        
        self.start_btn.setVisible(False)
        self.stop_btn.setVisible(True)
        
        # Update Bot configuration
        self.bot.mode = "smart" if is_smart else "wholesale"
        self.bot.manual_confirm_mode = False
        self.bot.max_budget = self.budget_spin.value()
        self.bot.sort_by_percent = self.sort_by_percent_check.isChecked()  # Сортировка по %
        self.bot.start()
        
        # После успешного запуска сбрасываем флаг
        self._is_starting = False
        
        # Show Overlay (Top Center)
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().geometry()
        x = (screen.width() - self.overlay.width()) // 2
        y = 0 # Top
        self.overlay.move(x, y)
        
        self.overlay.show()
        self.overlay.update_status(True, False)
        
        # Show Log Overlay
        self.log_overlay.show()
        self.log_overlay.clear_logs()
        
        self.is_mini_mode = True
        self.hide() # Скрываем основное окно
        
    def _on_stop_clicked(self):
        if not self.bot.isRunning(): return
        
        self.log_viewer.append("🛑 Остановка...")
        self.bot.stop()
        
        # Update Overlay
        self.overlay.update_status(False, False)
        self.log_overlay.hide()
        
    def _toggle_pause(self):
        if not self.bot.isRunning(): return
        
        self.bot.pause()
        is_paused = self.bot._is_paused
        
        self.overlay.update_status(True, is_paused)
        self.log_viewer.append(f"⏯️ Пауза: {is_paused}")

    def _on_progress(self, current, total, message):
        self.log_viewer.append(f"[{current}/{total}] {message}")
        try:
            sb = self.log_viewer.verticalScrollBar()
            sb.setValue(sb.maximum())
        except:
            pass
            
        # Update Overlay
        self.overlay.update_progress(current, total, message)
        # self.overlay.set_last_log(message) # Removed
        
    def _on_finished(self):
        self.is_mini_mode = False
        self.start_btn.setVisible(True)
        self.stop_btn.setVisible(False)
        self.log_viewer.append("🏁 Завершена.")
        
        self.overlay.update_status(False, False)
        self.overlay.hide()
        self.log_overlay.hide()
        
        # Восстанавливаем окно
        self.show()
        self.activateWindow()

    def _restore_window(self):
        self.is_mini_mode = False
        self.show()
        self.activateWindow()

    def _on_back_clicked(self):
        if self.launcher:
            self.launcher.show()
            self.close()
        else:
            self.close()
            
    def closeEvent(self, event):
        """Очистка ресурсов при закрытии"""
        import keyboard
        try:
            keyboard.remove_hotkey("F5")
            keyboard.remove_hotkey("F6")
        except:
            pass
            
        if self.bot.isRunning():
            self.bot.stop()
            self.bot.wait()
            
        self.overlay.close()
        self.log_overlay.close()
        event.accept()

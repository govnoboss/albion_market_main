from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFrame, QTextEdit, QGroupBox,
    QMessageBox, QTabWidget, QScrollArea, QSpinBox, QCheckBox, QComboBox
)
from PyQt6.QtGui import QIntValidator
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QFont

from .styles import MAIN_STYLE, COLORS
from .log_overlay import LogOverlay  # Импорт лог-оверлея
from .log_viewer import LogViewer, LogPanel # Импорт общего компонента логов
from ..utils.logger import get_logger

logger = get_logger()

class BudgetSpinBox(QSpinBox):
    """Спинбокс, который прячет 0, чтобы показать Placeholder"""
    def textFromValue(self, value):
        if value == 0:
            return ""
        return super().textFromValue(value)

class BuyerWindow(QMainWindow):
    """
    Отдельное окно для режима 'ЗАКУПЩИК'.
    Фокусируется на автоматической покупке предметов по выгодным ценам.
    """
    
    
    # Signals for thread-safe hotkey handling
    hotkey_stop_sig = pyqtSignal()
    hotkey_pause_sig = pyqtSignal()
    hotkey_toggle_sig = pyqtSignal() # F5 Toggle
    hotkey_skip_sig = pyqtSignal()   # F7 Skip

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
        
        # Кнопка 'Меню' (всегда видна)
        if self.launcher:
            menu_btn = QPushButton("Меню")
            menu_btn.setFixedSize(110, 36)
            menu_btn.setStyleSheet("""
                QPushButton { 
                    background: #21262d; 
                    color: #c9d1d9; 
                    border: 1px solid #8b949e; 
                    border-radius: 6px; 
                    font-size: 14px; 
                    font-weight: bold;
                }
                QPushButton:hover { 
                    background: #30363d; 
                    color: #ffffff; 
                    border-color: #f0f6fc;
                }
            """)
            menu_btn.clicked.connect(self._on_back_clicked)
            header_layout.addWidget(menu_btn)
        
        title = QLabel("🛒 GBot Закупщик")
        title.setStyleSheet("font-size: 18px; color: #3fb950; font-weight: bold;")
        header_layout.addWidget(title)
        
        hotkeys_info = QLabel("  [ F5: Start/Stop  |  F6: Pause  |  F7: Skip ]")
        hotkeys_info.setStyleSheet("color: #636e7b; font-size: 12px; font-weight: bold;")
        header_layout.addWidget(hotkeys_info)
        
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
        self.monitor_layout.setSpacing(10)
        self.monitor_layout.setContentsMargins(10, 10, 10, 10)
        
        self._setup_controls(self.monitor_layout)
        self._setup_log_area(self.monitor_layout)
        
        self.tabs.addTab(self.monitor_tab, "🎮 Главная")
        
        # --- Вкладка 2: План закупки ---
        from .buyer.purchase_plan_tab import PurchasePlanTab
        self.plan_tab = PurchasePlanTab()
        self.tabs.addTab(self.plan_tab, "📋 План закупки")
        
        # --- Вкладка 3: Профиты ---
        from .profits_tab import ProfitsTab
        self.profit_tab = ProfitsTab()
        self.tabs.addTab(self.profit_tab, "📊 Профиты")
        
        # Connect Hotkey Signals (Thread-Safe)
        self.hotkey_stop_sig.connect(self._on_stop_clicked)
        self.hotkey_pause_sig.connect(self._toggle_pause)
        self.hotkey_toggle_sig.connect(self._toggle_bot)
        self.hotkey_skip_sig.connect(lambda: self.bot.skip_item() if self.bot.isRunning() else None)



    def _setup_controls(self, layout):
        """Основные кнопки управления"""
        control_group = QGroupBox("Управление")
        ctrl_layout = QVBoxLayout(control_group)
        ctrl_layout.setSpacing(10)
        
        # Бюджет
        budget_layout = QHBoxLayout()
        budget_lbl = QLabel("Бюджет:")
        budget_lbl.setStyleSheet("color: #8b949e; font-weight: bold;")
        
        self.budget_spin = BudgetSpinBox()
        self.budget_spin.setRange(0, 999_999_999)
        self.budget_spin.setSingleStep(100_000)
        self.budget_spin.setValue(0)
        self.budget_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.budget_spin.lineEdit().setPlaceholderText("Безлимит")
        self.budget_spin.setStyleSheet("""
            QSpinBox { 
                background: #0d1117; 
                color: #c9d1d9; 
                border: 1px solid #30363d; 
                padding: 8px; 
                font-size: 13px;
                border-radius: 4px;
            }
            QSpinBox:focus { border: 1px solid #58a6ff; }
        """)
        
        budget_layout.addWidget(budget_lbl)
        budget_layout.addWidget(self.budget_spin)
        ctrl_layout.addLayout(budget_layout)

        # --- Выбор города (Закупка/Продажа) ---
        city_group = QHBoxLayout()
        city_group.setSpacing(10)
        
        buy_lbl = QLabel("Закупаем из:")
        buy_lbl.setStyleSheet("color: #c9d1d9; font-weight: bold;")
        self.buy_city_combo = QComboBox()
        self.buy_city_combo.setFixedWidth(130)
        
        sell_lbl = QLabel("Продаем в:")
        sell_lbl.setStyleSheet("color: #c9d1d9; font-weight: bold;")
        self.sell_city_combo = QComboBox()
        self.sell_city_combo.setFixedWidth(130)
        
        # Тёмная тема для комбобоксов городов
        city_combo_style = """
            QComboBox {
                background: #0d1117;
                color: #c9d1d9;
                border: 1px solid #30363d;
                padding: 5px;
                border-radius: 4px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox::down-arrow {
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #8b949e;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background: #161b22;
                color: #c9d1d9;
                selection-background-color: #1f6feb;
                border: 1px solid #30363d;
            }
        """
        self.buy_city_combo.setStyleSheet(city_combo_style)
        self.sell_city_combo.setStyleSheet(city_combo_style)
        
        city_group.addWidget(buy_lbl)
        city_group.addWidget(self.buy_city_combo)
        city_group.addSpacing(10)
        city_group.addWidget(sell_lbl)
        city_group.addWidget(self.sell_city_combo)
        city_group.addStretch()
        
        ctrl_layout.addLayout(city_group)

        # Режимы
        self.smart_mode_check = QCheckBox("Сортировать по чистому профиту серебра")
        self.smart_mode_check.setToolTip("Покупать самые выгодные товары на основе сканирования,\nа не по фиксированному списку.")
        self.smart_mode_check.setStyleSheet("color: #c9d1d9; font-weight: bold; padding: 4px;")
        ctrl_layout.addWidget(self.smart_mode_check)
        
        self.sort_by_percent_check = QCheckBox("Сортировать по % профита")
        self.sort_by_percent_check.setStyleSheet("color: #8b949e; margin-left: 20px;")
        self.sort_by_percent_check.setVisible(False)
        ctrl_layout.addWidget(self.sort_by_percent_check)

        # Кнопки Старт/Стоп
        self.start_btn = QPushButton("▶ ЗАПУСТИТЬ")
        self.start_btn.setObjectName("primary")
        self.start_btn.setMinimumHeight(45)
        self.start_btn.clicked.connect(self._on_start_clicked)
        ctrl_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("🛑 ОСТАНОВИТЬ")
        self.stop_btn.setMinimumHeight(45)
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setVisible(False)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        ctrl_layout.addWidget(self.stop_btn)

        # Загрузка городов
        self._load_cities()
        
        # Связываем видимость
        self.smart_mode_check.toggled.connect(self.sort_by_percent_check.setVisible)
        
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
        self.log_panel = LogPanel()
        self.log_panel.connect_logger()
        self.log_viewer = self.log_panel.viewer # Совместимость
        
        # Ограничиваем высоту для закупщика, но через панель
        self.log_panel.setMaximumHeight(150) 
        layout.addWidget(self.log_panel)

    def showEvent(self, event):
        """Регистрация хоткеев при показе окна"""
        super().showEvent(event)
        if not self._hotkeys_registered:
            import keyboard
            try:
                keyboard.add_hotkey("F5", self.hotkey_toggle_sig.emit)
                keyboard.add_hotkey("F6", self.hotkey_pause_sig.emit)
                keyboard.add_hotkey("F7", self.hotkey_skip_sig.emit)
                self._hotkeys_registered = True
            except Exception as e:
                logger.error(f"Ошибка регистраци хоткеев Buyer: {e}")

        # Автоматическое обновление данных при открытии
        self._load_cities()
        if hasattr(self, 'plan_tab'):
            self.plan_tab.refresh_data()
    
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
                keyboard.remove_hotkey("F7")
                self._hotkeys_registered = False
            except Exception as e:
                pass  # Игнорируем если хоткеи уже удалены

    def _toggle_bot(self):
        """Переключить состояние бота (Start/Stop)"""
        if self.bot.isRunning():
            self._on_stop_clicked()
        else:
            self._on_start_clicked()

    def _load_cities(self):
        """Загрузка доступных городов из хранилища"""
        from ..utils.price_storage import price_storage
        all_cities = price_storage.get_cities()
        all_cities.sort()
        
        # Сохраняем текущий выбор, чтобы не сбрасывать его при каждом открытии
        old_buy = self.buy_city_combo.currentText()
        old_sell = self.sell_city_combo.currentText()
        
        self.buy_city_combo.blockSignals(True)
        self.sell_city_combo.blockSignals(True)
        
        self.buy_city_combo.clear()
        self.sell_city_combo.clear()
        
        self.buy_city_combo.addItems(all_cities)
        self.sell_city_combo.addItems(all_cities)
        
        # Восстанавливаем или ставим дефолты
        if old_buy in all_cities:
            self.buy_city_combo.setCurrentText(old_buy)
        elif "Martlock" in all_cities:
            self.buy_city_combo.setCurrentText("Martlock")
        
        if old_sell in all_cities:
            self.sell_city_combo.setCurrentText(old_sell)
        elif "Black Market" in all_cities:
            self.sell_city_combo.setCurrentText("Black Market")
        elif "Черный рынок" in all_cities:
            self.sell_city_combo.setCurrentText("Черный рынок")
            
        self.buy_city_combo.blockSignals(False)
        self.sell_city_combo.blockSignals(False)

    def _on_start_clicked(self):
        # Блокировка двойного запуска
        if self._is_starting or self.bot.isRunning():
            return
        self._is_starting = True
        
        buy_city = self.buy_city_combo.currentText()
        sell_city = self.sell_city_combo.currentText()
        
        if not buy_city or not sell_city:
            QMessageBox.warning(self, "Ошибка", "Выберите города закупки и продажи!")
            self._is_starting = False
            return

        # 0. Проверка наличия данных о ценах
        from ..utils.price_storage import price_storage
        from datetime import datetime
        
        buy_prices = price_storage.get_city_prices(buy_city)
        sell_prices = price_storage.get_city_prices(sell_city)
        
        if not buy_prices:
            QMessageBox.warning(self, "⚠️ Нет данных", f"В базе нет цен для города закупки: {buy_city}")
            self._is_starting = False
            return
        
        if not sell_prices:
            QMessageBox.warning(self, "⚠️ Нет данных", f"В базе нет цен для города продажи: {sell_city}")
            self._is_starting = False
            return
        
        is_smart = self.smart_mode_check.isChecked()
        
        if is_smart:
            # Проверка устаревания данных (только для выбранных городов)
            has_stale = False
            now = datetime.now()
            hours_threshold = 10
            
            for prices in [buy_prices, sell_prices]:
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
        self.log_viewer.append_styled(f"🚀 Инициализация... Режим: {mode_str}", "info")
        
        self.start_btn.setVisible(False)
        self.stop_btn.setVisible(True)
        
        # Update Bot configuration
        self.bot.buy_city = buy_city
        self.bot.sell_city = sell_city
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
        
        self._switch_to_mini_mode()
        
    def _on_stop_clicked(self):
        if not self.bot.isRunning(): return
        
        self.log_viewer.append_styled("🛑 Остановка...", "warning")
        self.bot.stop()
        
        # Update Overlay
        self.overlay.update_status(False, False)
        self.log_overlay.hide()
        
    def _toggle_pause(self):
        if not self.bot.isRunning(): return
        
        self.bot.pause()
        is_paused = self.bot._is_paused
        
        self.overlay.update_status(True, is_paused)
        self.log_viewer.append_styled(f"⏯️ Пауза: {is_paused}", "warning")

    def _on_progress(self, current, total, message):
        self.log_viewer.append_styled(f"[{current}/{total}] {message}", "info")
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
        self.log_viewer.append_styled("🏁 Завершена.", "success")
        
        self.overlay.update_status(False, False)
        self.overlay.hide()
        self.log_overlay.hide()
        
        # Восстанавливаем окно
        self.show()
        self.activateWindow()

    def _switch_to_mini_mode(self):
        """Переключение в мини-режим"""
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QGuiApplication
        
        self.is_mini_mode = True
        self.hide()
        
        # Позиционировать оверлей по ЦЕНТРУ сверху
        screen_geo = QGuiApplication.primaryScreen().availableGeometry()
        overlay_w = self.overlay.width()
        
        x = (screen_geo.width() - overlay_w) // 2
        y = screen_geo.top() + 20
        
        self.overlay.move(x, y)
        self.overlay.show()
        self.overlay.update_status(self.bot.isRunning(), self.bot._is_paused)

    def _restore_window(self):
        """Возврат из мини-режима"""
        self.is_mini_mode = False
        self.overlay.hide()
        self.show()
        self.activateWindow()

    def _toggle_always_on_top(self, checked: bool):
        """Переключить режим 'поверх всех окон'"""
        from ..utils.logger import get_logger
        if checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
            get_logger().info("Buyer: Режим 'Поверх всех окон' включен")
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
            get_logger().info("Buyer: Режим 'Поверх всех окон' выключен")
        self.show()

    def _on_back_clicked(self):
        if self.bot.isRunning():
            self._on_stop_clicked()
            
        if self.launcher:
            self.launcher.show()
            self.hide()
        else:
            self.close()
            
    def closeEvent(self, event):
        """Очистка ресурсов при закрытии"""
        import keyboard
        try:
            keyboard.remove_hotkey("F5")
            keyboard.remove_hotkey("F6")
            keyboard.remove_hotkey("F7")
        except:
            pass
            
        if self.bot.isRunning():
            self.bot.stop()
            self.bot.wait()
            
        self.overlay.close()
        self.log_overlay.close()
        
        from PyQt6.QtWidgets import QApplication
        from ..utils.logger import get_logger
        get_logger().info("Закрытие программы через закупщик")
        QApplication.quit()
        event.accept()

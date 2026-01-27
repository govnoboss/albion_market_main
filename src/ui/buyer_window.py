from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFrame, QTextEdit, QGroupBox,
    QMessageBox, QTabWidget, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QFont

from .styles import MAIN_STYLE, COLORS

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
        self.setWindowTitle("Albion Market - BUYER MODE")
        self.resize(600, 750) 
        self.setStyleSheet(MAIN_STYLE)
        
        # State
        self.last_mode = "wholesale" # Default start mode for F5
        
        # Основной виджет (теперь с вкладками)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; }
            QTabBar::tab { 
                background: #161b22; 
                color: #8b949e; 
                padding: 10px 20px; 
                border: 1px solid #30363d;
                border-bottom: none;
                margin-right: 2px;
            }
            QTabBar::tab:selected { 
                background: #0d1117; 
                color: #f0f6fc; 
            }
        """)

        # --- Вкладка 1: Управление (Monitor) ---
        self.monitor_tab = QWidget()
        self.monitor_layout = QVBoxLayout(self.monitor_tab)
        self.monitor_layout.setSpacing(15)
        self.monitor_layout.setContentsMargins(20, 20, 20, 20)
        
        self._setup_header(self.monitor_layout)
        self._setup_status_panel(self.monitor_layout)
        self._setup_controls(self.monitor_layout)
        self._setup_log_area(self.monitor_layout)
        
        self.tabs.addTab(self.monitor_tab, "🚀 Монитор")
        
        # --- Вкладка 2: План закупки ---
        from .buyer.purchase_plan_tab import PurchasePlanTab
        self.plan_tab = PurchasePlanTab()
        self.tabs.addTab(self.plan_tab, "📋 План закупки")
        
        # --- Вкладка 3: Координаты (Настройки) ---
        from .coordinates_tab import CoordinatesTab
        self.coords_tab = CoordinatesTab()
        self.tabs.addTab(self.coords_tab, "⚙️ Координаты")
        
        # Connect Hotkey Signals (Thread-Safe)
        self.hotkey_stop_sig.connect(self._on_stop_clicked)
        self.hotkey_pause_sig.connect(self._toggle_pause)
        self.hotkey_toggle_sig.connect(self._toggle_bot)

    def _setup_header(self, layout):
        """Заголовок окна"""
        header_layout = QHBoxLayout()
        
        title_layout = QVBoxLayout()
        title = QLabel("🛒 AUTOMATIC BUYER")
        title.setObjectName("title")
        title.setStyleSheet("font-size: 20px; color: #3fb950; font-weight: bold;")
        
        subtitle = QLabel("Режим автоматической закупки")
        subtitle.setObjectName("subtitle")
        
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        # Кнопка "Назад в меню"
        back_btn = QPushButton("Меню")
        back_btn.setFixedSize(80, 30)
        back_btn.clicked.connect(self._on_back_clicked)
        header_layout.addWidget(back_btn)
        
        layout.addLayout(header_layout)
        
        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {COLORS['border']};")
        layout.addWidget(line)

    def _setup_status_panel(self, layout):
        """Панель текущего статуса"""
        self.status_card = QFrame()
        self.status_card.setObjectName("card")
        card_layout = QVBoxLayout(self.status_card)
        
        lbl = QLabel("Статус работы (F5)")
        lbl.setStyleSheet("color: #8b949e; font-size: 12px; text-transform: uppercase;")
        card_layout.addWidget(lbl)
        
        self.status_val_label = QLabel("ОЖИДАНИЕ")
        self.status_val_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #8b949e;")
        card_layout.addWidget(self.status_val_label)
        
        layout.addWidget(self.status_card)

    def _setup_controls(self, layout):
        """Основные кнопки управления"""
        control_group = QGroupBox("Управление")
        ctrl_layout = QVBoxLayout(control_group)
        ctrl_layout.setSpacing(10)
        
        # Кнопка СТАРТ РОЗНИЦА (Retail/Sniper)
        self.start_retail_btn = QPushButton("🛒 СТАРТ: РОЗНИЦА (Sniper)")
        self.start_retail_btn.setObjectName("primary")
        self.start_retail_btn.setMinimumHeight(45)
        self.start_retail_btn.setStyleSheet("font-size: 14px; font-weight: bold; background-color: #d29922; border-color: #d29922;")
        self.start_retail_btn.clicked.connect(lambda: self._on_start_clicked(mode="retail"))
        ctrl_layout.addWidget(self.start_retail_btn)

        # Кнопка СТАРТ ОПТ (Wholesale/Order)
        self.start_wholesale_btn = QPushButton("📦 СТАРТ: ОПТ (Orders)")
        self.start_wholesale_btn.setObjectName("primary")
        self.start_wholesale_btn.setMinimumHeight(45)
        self.start_wholesale_btn.setStyleSheet("font-size: 14px; font-weight: bold; background-color: #238636;")
        self.start_wholesale_btn.clicked.connect(lambda: self._on_start_clicked(mode="wholesale"))
        ctrl_layout.addWidget(self.start_wholesale_btn)
        
        # Кнопка СТОП
        self.stop_btn = QPushButton("⏹ ОСТАНОВИТЬ (F5)")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setVisible(False)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        ctrl_layout.addWidget(self.stop_btn)
        
        # Чекбокс Ручное подтверждение (Debug)
        from PyQt6.QtWidgets import QCheckBox
        self.debug_confirm_check = QCheckBox("Ручное подтверждение (F1/F2)")
        self.debug_confirm_check.setChecked(True) # Default On as requested for testing
        self.debug_confirm_check.setStyleSheet("color: #8b949e;")
        ctrl_layout.addWidget(self.debug_confirm_check)
        
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
        
        # Setup Hotkeys
        try:
            keyboard.add_hotkey("F5", self.hotkey_toggle_sig.emit) # Changed to TOGGLE
            keyboard.add_hotkey("F6", self.hotkey_pause_sig.emit)
        except Exception as e:
            print(f"Ошибка регистрации хоткеев: {e}")

    def _setup_log_area(self, layout):
        """Лог событий"""
        self.log_viewer = QTextEdit()
        self.log_viewer.setObjectName("logViewer")
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setPlaceholderText("Лог событий закупки...")
        layout.addWidget(self.log_viewer)

    def _toggle_bot(self):
        """Переключить состояние бота (Start/Stop)"""
        if self.bot.isRunning():
            self._on_stop_clicked()
        else:
            self._on_start_clicked(mode=self.last_mode)

    def _on_start_clicked(self, mode="wholesale"):
        self.last_mode = mode # Remember mode logic
        self.log_viewer.clear()
        mode_name = "РОЗНИЦА (Sniper)" if mode == "retail" else "ОПТ (Orders)"
        self.log_viewer.append(f"🚀 Инициализация... Режим: {mode_name}")
        
        self.start_retail_btn.setVisible(False)
        self.start_wholesale_btn.setVisible(False)
        self.stop_btn.setVisible(True)
        self.status_val_label.setText(f"РАБОТАЕТ: {mode_name}")
        self.status_val_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #3fb950;")
        
        # Update Bot configuration
        self.bot.mode = mode
        self.bot.manual_confirm_mode = self.debug_confirm_check.isChecked()
        self.bot.start()
        
        # Show Overlay (Top Center)
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().geometry()
        x = (screen.width() - self.overlay.width()) // 2
        y = 0 # Top
        self.overlay.move(x, y)
        
        self.overlay.show()
        self.overlay.update_status(True, False)
        self.hide() # Скрываем основное окно
        
    def _on_stop_clicked(self):
        if not self.bot.isRunning(): return
        
        self.log_viewer.append("🛑 Остановка...")
        self.bot.stop()
        self.status_val_label.setText("ОСТАНОВКА...")
        
        # Update Overlay
        self.overlay.update_status(False, False)
        
    def _toggle_pause(self):
        if not self.bot.isRunning(): return
        
        self.bot.pause()
        is_paused = self.bot._is_paused
        
        status_text = "ПАУЗА" if is_paused else "РАБОТАЕТ"
        color = "#d29922" if is_paused else "#3fb950"
        self.status_val_label.setText(status_text)
        self.status_val_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {color};")
        
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
        self.overlay.set_last_log(message)
        
    def _on_finished(self):
        self.status_val_label.setText("ОЖИДАНИЕ")
        self.status_val_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #8b949e;")
        self.start_retail_btn.setVisible(True)
        self.start_wholesale_btn.setVisible(True)
        self.stop_btn.setVisible(False)
        self.log_viewer.append("🏁 Завершена.")
        
        self.overlay.update_status(False, False)
        self.overlay.hide()
        
        # Восстанавливаем окно
        self.show()
        self.activateWindow()

    def _restore_window(self):
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
        event.accept()

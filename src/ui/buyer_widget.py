from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGroupBox, QSpinBox, QComboBox, QCheckBox,
    QMessageBox, QTabWidget
)
from .styles import MAIN_STYLE, COLORS
from .log_viewer import LogPanel
from ..utils.logger import get_logger
from ..core.buyer import BuyerBot
from .buyer.purchase_plan_tab import PurchasePlanTab

class BudgetSpinBox(QSpinBox):
    def textFromValue(self, value):
        if value == 0: return ""
        return super().textFromValue(value)

class BuyerWidget(QWidget):
    """Модуль закупщика (виджет)"""
    
    hotkey_toggle_sig = pyqtSignal()
    hotkey_pause_sig = pyqtSignal()
    hotkey_skip_sig = pyqtSignal()
    
    def __init__(self, dashboard=None, mini_overlay=None, log_overlay=None):
        super().__init__()
        self.dashboard = dashboard
        self._is_starting = False
        
        # Оверлеи (shared from dashboard)
        self.overlay = mini_overlay
        self.log_overlay = log_overlay
        
        if self.overlay:
            self.overlay.start_clicked.connect(self._on_start_clicked)
            self.overlay.pause_clicked.connect(self._toggle_pause)
            self.overlay.stop_clicked.connect(self._on_stop_clicked)
            self.overlay.restore_clicked.connect(self._restore_from_mini)
        
        self._setup_ui()
        self._init_bot()
        # self._setup_logging() # Centralized in Dashboard
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("🛒 Market Buyer")
        title.setObjectName("title")
        header.addWidget(title)
        
        header.addStretch()
        
        self.mini_btn = QPushButton("↘ Mini Mode")
        self.mini_btn.setObjectName("sidebarItem")
        self.mini_btn.setFixedWidth(120)
        self.mini_btn.clicked.connect(self._switch_to_mini)
        header.addWidget(self.mini_btn)
        
        layout.addLayout(header)

        # Content Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {COLORS['border']}; border-radius: 8px; background: {COLORS['bg_card']}; }}
            QTabBar::tab {{ background: {COLORS['bg']}; color: {COLORS['text_dark']}; padding: 8px 20px; border: 1px solid {COLORS['border']}; }}
            QTabBar::tab:selected {{ background: {COLORS['bg_card']}; color: {COLORS['accent']}; font-weight: bold; }}
            QTabBar::tab:hover {{ background: {COLORS['item_bg']}; }}
        """)
        
        # Tab 1: Control & Logs
        mgmt_tab = QWidget()
        mgmt_layout = QVBoxLayout(mgmt_tab)
        
        # Controls Group
        ctrl_group = QGroupBox("Управление")
        ctrl_layout = QVBoxLayout(ctrl_group)
        
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Бюджет:"))
        self.budget_spin = BudgetSpinBox()
        self.budget_spin.setRange(0, 999_999_999)
        self.budget_spin.lineEdit().setPlaceholderText("Безлимит")
        row1.addWidget(self.budget_spin)
        
        row1.addWidget(QLabel("Купить в:"))
        self.buy_city_combo = QComboBox()
        row1.addWidget(self.buy_city_combo)
        
        row1.addWidget(QLabel("Продать в:"))
        self.sell_city_combo = QComboBox()
        row1.addWidget(self.sell_city_combo)
        ctrl_layout.addLayout(row1)
        
        self.smart_mode_check = QCheckBox("🧠 Умный закупщик (Smart Buyer)")
        ctrl_layout.addWidget(self.smart_mode_check)
        
        self.sort_by_percent_check = QCheckBox("   📊 Сортировать по % профита")
        self.sort_by_percent_check.setStyleSheet(f"color: {COLORS['text_dark']}; margin-left: 20px;")
        self.sort_by_percent_check.setVisible(False)
        self.smart_mode_check.toggled.connect(self.sort_by_percent_check.setVisible)
        ctrl_layout.addWidget(self.sort_by_percent_check)
        
        self.start_btn = QPushButton("▶ ЗАПУСТИТЬ")
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(self._on_start_clicked)
        ctrl_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("🛑 ОСТАНОВИТЬ")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setVisible(False)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        ctrl_layout.addWidget(self.stop_btn)
        
        mgmt_layout.addWidget(ctrl_group)
        
        self.log_panel = LogPanel()
        self.log_panel.connect_logger()
        mgmt_layout.addWidget(self.log_panel, stretch=1)
        
        self.tabs.addTab(mgmt_tab, "🎮 Управление")
        
        # Tab 2: Purchase Plan
        self.plan_tab = PurchasePlanTab()
        self.tabs.addTab(self.plan_tab, "📅 План закупки (Wholesale)")
        
        layout.addWidget(self.tabs)
        
        self._load_cities()

    def _init_bot(self):
        self.bot = BuyerBot()
        self.bot.progress_updated.connect(self._on_progress)
        self.bot.finished.connect(self._on_finished)
        
    def _setup_logging(self):
        """Устарело, логи теперь централизованы в Dashboard"""
        pass

    def _load_cities(self):
        from ..utils.price_storage import price_storage
        cities = price_storage.get_cities()
        cities.sort()
        self.buy_city_combo.addItems(cities)
        self.sell_city_combo.addItems(cities)
        if "Martlock" in cities: self.buy_city_combo.setCurrentText("Martlock")
        if "Black Market" in cities: self.sell_city_combo.setCurrentText("Black Market")

    def _on_start_clicked(self):
        if self._is_starting or self.bot.isRunning(): return
        
        buy_city = self.buy_city_combo.currentText()
        sell_city = self.sell_city_combo.currentText()
        
        if not buy_city or not sell_city:
            QMessageBox.warning(self, "Ошибка", "Выберите города!")
            return

        self.bot.buy_city = buy_city
        self.bot.sell_city = sell_city
        self.bot.mode = "smart" if self.smart_mode_check.isChecked() else "wholesale"
        self.bot.sort_by_percent = self.sort_by_percent_check.isChecked()
        self.bot.max_budget = self.budget_spin.value()
        self.bot.start()
        
        self.start_btn.setVisible(False)
        self.stop_btn.setVisible(True)
        self.overlay.show()
        self.log_overlay.show()
        self.overlay.update_status(True, False)
        self._switch_to_mini()

    def _on_stop_clicked(self):
        if self.bot.isRunning():
            self.bot.stop()
            self.overlay.update_status(False, False)
            self.log_overlay.hide()
            self._restore_from_mini()

    def _toggle_pause(self):
        if self.bot.isRunning():
            self.bot.pause()
            self.overlay.update_status(True, self.bot._is_paused)

    # --- Hotkey Handlers (Called from Dashboard) ---
    def _on_hotkey_toggle(self):
        if self.bot.isRunning():
            self._on_stop_clicked()
        else:
            self._on_start_clicked()

    def _on_hotkey_pause(self):
        self._toggle_pause()

    def _on_hotkey_skip(self):
        if self.bot.isRunning():
            self.bot.skip_item()

    def _on_progress(self, current, total, message):
        self.overlay.update_progress(current, total, message)

    def _on_finished(self):
        self.start_btn.setVisible(True)
        self.stop_btn.setVisible(False)
        self.overlay.hide()
        self.log_overlay.hide()
        self._restore_from_mini()

    def _switch_to_mini(self):
        if self.dashboard: self.dashboard.hide()
        self.overlay.show()

    def _restore_from_mini(self):
        self.overlay.hide()
        if self.dashboard:
            self.dashboard.show()
            self.dashboard.activateWindow()

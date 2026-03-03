from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGroupBox, QSpinBox, QComboBox, QCheckBox,
    QMessageBox, QTabWidget, QGridLayout
)
from .styles import MAIN_STYLE, COLORS
from .log_viewer import LogPanel
from ..utils.logger import get_logger
from ..utils.localization import get_text
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
        title = QLabel(get_text("buyer_title", "🛒 Market Buyer"))
        title.setObjectName("title")
        header.addWidget(title)
        
        header.addStretch()
        
        layout.addLayout(header)

        # Content Tabs (Custom style removed, uses global)
        self.tabs = QTabWidget()
        
        # Tab 1: Control & Logs
        mgmt_tab = QWidget()
        mgmt_layout = QVBoxLayout(mgmt_tab)
        
        # Controls Group
        ctrl_group = QGroupBox(get_text("buyer_params_group", "Параметры закупки"))
        ctrl_layout = QVBoxLayout(ctrl_group)
        ctrl_layout.setSpacing(15)
        
        # Grid for city selection
        grid = QGridLayout()
        grid.addWidget(QLabel(get_text("buyer_budget_lbl", "Бюджет:")), 0, 0)
        self.budget_spin = BudgetSpinBox()
        self.budget_spin.setRange(0, 999_999_999)
        self.budget_spin.lineEdit().setPlaceholderText(get_text("buyer_budget_unlimited", "Безлимит"))
        grid.addWidget(self.budget_spin, 0, 1)
        
        grid.addWidget(QLabel(get_text("buyer_buy_in_lbl", "Купить в:")), 1, 0)
        self.buy_city_combo = QComboBox()
        grid.addWidget(self.buy_city_combo, 1, 1)
        
        grid.addWidget(QLabel(get_text("buyer_sell_in_lbl", "Продать в:")), 2, 0)
        self.sell_city_combo = QComboBox()
        grid.addWidget(self.sell_city_combo, 2, 1)
        ctrl_layout.addLayout(grid)
        
        # Smart Mode Section
        smart_layout = QVBoxLayout()
        self.smart_mode_check = QCheckBox(get_text("buyer_sort_profit", " Сортировать по чистому профиту серебра"))
        smart_layout.addWidget(self.smart_mode_check)
        
        self.sort_by_percent_check = QCheckBox(get_text("buyer_sort_percent", " Сортировать по % профита"))
        smart_layout.addWidget(self.sort_by_percent_check)
        ctrl_layout.addLayout(smart_layout)
        
        # Action Buttons
        self.start_btn = QPushButton(get_text("ctrl_start_btn", "▶ ЗАПУСТИТЬ"))
        self.start_btn.setObjectName("primary")
        self.start_btn.setMinimumHeight(45)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self._on_start_clicked)
        ctrl_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton(get_text("ctrl_stop_btn", "🛑 ОСТАНОВИТЬ (F5)"))
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setMinimumHeight(45)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setVisible(False)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        ctrl_layout.addWidget(self.stop_btn)
        
        # Подсказка по горячим клавишам
        hotkeys_hint = QLabel(get_text("buyer_hotkeys_hint", "⌨ F5 — Старт/Стоп  |  F6 — Пауза  |  F7 — Пропустить предмет"))
        hotkeys_hint.setStyleSheet("color: #64748b; font-size: 12px; margin-top: 5px;")
        hotkeys_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ctrl_layout.addWidget(hotkeys_hint)
        
        mgmt_layout.addWidget(ctrl_group)
        mgmt_layout.addStretch()  # Пустое пространство вместо логов
        
        self.log_panel = LogPanel()
        self.log_panel.connect_logger()
        self.log_panel.hide()
        
        self.tabs.addTab(mgmt_tab, get_text("ui_mgmt_tab", "🎮 Управление"))
        
        # Tab 2: Purchase Plan
        self.plan_tab = PurchasePlanTab()
        self.tabs.addTab(self.plan_tab, get_text("buyer_wholesale_tab", "📅 План закупки (Wholesale)"))
        
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
            QMessageBox.warning(self, get_text("coord_msg_error", "Ошибка"), get_text("buyer_err_select_city", "Выберите города!"))
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
        # Clear logs on session finish
        self.log_panel.clear()
        if self.log_overlay:
            self.log_overlay.clear_logs()
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

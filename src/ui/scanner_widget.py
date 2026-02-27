from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGroupBox, QSpinBox, QComboBox, QCheckBox,
    QMessageBox, QTabWidget
)
from .styles import MAIN_STYLE, COLORS
from .control_panel import ControlPanel
from .log_viewer import LogPanel
from ..utils.logger import get_logger
from ..core.bot import MarketBot
from .items_panel import ItemsPanel

class ScannerWidget(QWidget):
    """Модуль сканера (виджет)"""
    
    toggle_hotkey_signal = pyqtSignal()
    pause_hotkey_signal = pyqtSignal()
    
    def __init__(self, dashboard=None, mini_overlay=None, log_overlay=None):
        super().__init__()
        self.dashboard = dashboard
        
        # Оверлеи (shared from dashboard)
        self.mini_overlay = mini_overlay
        self.log_overlay = log_overlay
        
        if self.mini_overlay:
            self.mini_overlay.start_clicked.connect(self._on_start_bot)
            self.mini_overlay.pause_clicked.connect(self._on_pause_bot)
            self.mini_overlay.stop_clicked.connect(self._on_stop_bot)
            self.mini_overlay.restore_clicked.connect(self._restore_from_mini)
        
        self._setup_ui()
        self._init_bot()
        # self._setup_logging() # Logging is now centralized in Dashboard
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("📡 Market Scanner")
        title.setObjectName("title")
        header.addWidget(title)
        
        header.addStretch()
        
        # Mini Mode
        self.mini_btn = QPushButton("↘ Mini Mode")
        self.mini_btn.setObjectName("sidebarItem")
        self.mini_btn.setFixedWidth(120)
        self.mini_btn.clicked.connect(self._switch_to_mini)
        header.addWidget(self.mini_btn)
        
        layout.addLayout(header)

        # Content Tabs (Custom style removed, uses global)
        self.tabs = QTabWidget()
        
        # Tab 1: Control & Logs
        mgmt_tab = QWidget()
        mgmt_layout = QVBoxLayout(mgmt_tab)
        
        self.control_panel = ControlPanel()
        self.control_panel.start_clicked.connect(self._on_start_bot)
        self.control_panel.stop_clicked.connect(self._on_stop_bot)
        self.control_panel.pause_clicked.connect(self._on_pause_bot)
        mgmt_layout.addWidget(self.control_panel)
        
        self.log_panel = LogPanel()
        self.log_panel.connect_logger()
        mgmt_layout.addWidget(self.log_panel, stretch=1)
        
        self.tabs.addTab(mgmt_tab, "🎮 Управление")
        
        # Tab 2: Items & Exclusions
        self.items_tab = ItemsPanel()
        self.tabs.addTab(self.items_tab, "📚 База и Исключения")
        
        layout.addWidget(self.tabs)
        
    def _init_bot(self):
        self.bot = MarketBot()
        self.bot.progress_updated.connect(self.control_panel.update_progress)
        if self.mini_overlay:
            self.bot.progress_updated.connect(self.mini_overlay.update_progress)
        self.bot.finished.connect(self._on_bot_finished)
        self.bot.overlay_status.connect(self._on_overlay_status_changed)

    def _setup_logging(self):
        """Устарело, логи теперь централизованы в Dashboard"""
        pass

    def _on_start_bot(self):
        if not self.bot.isRunning():
            start_index = self.control_panel.start_index_spin.value() - 1
            self.bot.start_index = start_index
            self.bot.start()
            self.control_panel.set_running_state(True)
            self.mini_overlay.update_status(True, False)
            self.log_overlay.show()
            self._switch_to_mini()

    def _on_pause_bot(self):
        self.bot.pause()
        self.mini_overlay.update_status(True, self.bot._is_paused)

    def _on_stop_bot(self):
        if self.bot.isRunning():
            self.bot.stop()
            self.bot.wait()
            self.control_panel.set_running_state(False)
            self.mini_overlay.update_status(False, False)
            self.log_overlay.hide()
            self._restore_from_mini()

    # --- Hotkey Handlers (Called from Dashboard) ---
    def _on_hotkey_toggle(self):
        if self.bot.isRunning():
            self._on_stop_bot()
        else:
            self._on_start_bot()

    def _on_hotkey_pause(self):
        if self.bot.isRunning():
            self._on_pause_bot()

    def _on_bot_finished(self):
        self.control_panel.set_running_state(False)
        self.mini_overlay.update_status(False, False)
        # Clear logs on session finish
        self.log_panel.clear()
        if self.log_overlay:
            self.log_overlay.clear_logs()
        self.log_overlay.hide()
        self._restore_from_mini()

    def _switch_to_mini(self):
        if self.dashboard:
            self.dashboard.hide()
        self.mini_overlay.show()
        # TODO: Positioning logic

    def _restore_from_mini(self):
        self.mini_overlay.hide()
        if self.dashboard:
            self.dashboard.show()
            self.dashboard.activateWindow()

    def _on_overlay_status_changed(self, visible):
        if visible and self.bot.isRunning():
            self.log_overlay.show()
        else:
            self.log_overlay.hide()

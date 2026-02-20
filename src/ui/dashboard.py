"""
Главное окно Dashboard
Единый интерфейс с сайдбаром и аналитикой
"""

import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QStackedWidget, QLabel, QFrame, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QIcon

from .styles import MAIN_STYLE, COLORS
from ..utils.logger import get_logger
import keyboard

class SidebarItem(QPushButton):
    """Элемент бокового меню"""
    def __init__(self, text, icon_name=None, parent=None):
        super().__init__(text, parent)
        self.setObjectName("sidebarItem")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.setFixedHeight(40)

class Sidebar(QFrame):
    """Боковая панель навигации"""
    nav_changed = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(200)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Заголовок
        self.title = QLabel("ALBION BOT")
        self.title.setObjectName("sidebarTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.title)
        
        # Группа кнопок
        self.buttons = []
        self._add_nav_item("📊 Home", 0)
        self._add_nav_item("📡 Scanner", 1)
        self._add_nav_item("💰 Buyer", 2)
        self._add_nav_item("📈 Finance", 3)
        self._add_nav_item("🏷️ Prices", 4)
        self._add_nav_item("🎯 Coordinates", 5)
        self._add_nav_item("⚙️ Settings", 6)
        self._add_nav_item("❓ Guide & FAQ", 7)
        
        self.layout.addStretch()
        
        # Футер (Версия)
        self.footer = QFrame()
        self.footer.setObjectName("sidebarFooter")
        footer_layout = QVBoxLayout(self.footer)
        self.version_label = QLabel("v2.0.0")
        self.version_label.setStyleSheet("color: #484f58; font-size: 11px;")
        footer_layout.addWidget(self.version_label)
        self.layout.addWidget(self.footer)

    def _add_nav_item(self, text, index):
        btn = SidebarItem(text)
        btn.clicked.connect(lambda: self._on_clicked(index))
        self.layout.addWidget(btn)
        self.buttons.append(btn)
        if index == 0:
            btn.setChecked(True)
            btn.setProperty("active", "true")

    def _on_clicked(self, index):
        for i, btn in enumerate(self.buttons):
            is_active = (i == index)
            btn.setChecked(is_active)
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.nav_changed.emit(index)

class MainDashboard(QMainWindow):
    """Главное окно приложения (Dashboard)"""
    
    # Сигнал для потокобезопасной обработки хоткеев
    hotkey_signal = pyqtSignal(str) # "f5", "f6", "f7"
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Albion Market Bot - Dashboard")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet(MAIN_STYLE)
        
        # Set Icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 1. Сайдбар
        self.sidebar = Sidebar()
        self.sidebar.nav_changed.connect(self._on_nav_changed)
        self.main_layout.addWidget(self.sidebar)
        
        # 2. Область контента
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("dashboardContent")
        self.main_layout.addWidget(self.content_stack)
        
        # 3. Общие оверлеи (Singleton-like)
        from .mini_overlay import MiniOverlay
        from .log_overlay import LogOverlay
        self.mini_overlay = MiniOverlay()
        self.log_overlay = LogOverlay()
        
        # Инициализация вкладок
        self._init_tabs()
        
        # Централизованное логирование
        self._setup_logging()
        
        # Глобальные хоткеи
        self._setup_hotkeys()
        self.hotkey_signal.connect(self._handle_hotkey_safe)
        
        # Вывести на передний план
        self._force_foreground()

    def _force_foreground(self):
        flags = self.windowFlags()
        self.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
        self.show()
        QTimer.singleShot(500, lambda: self.setWindowFlags(flags) or self.show() or self.activateWindow())

    def _setup_logging(self):
        """Единая точка подключения логов к UI"""
        logger = get_logger()
        def unified_log_filter(msg, lvl):
            # Отображаем только важные статусы или сообщения с эмодзи (для сканера)
            is_important = lvl.lower() in ["error", "warning", "critical", "success"]
            is_market_data = any(x in msg for x in ["💰", "Цена:", "Price:", "Профит:", "Profit:"])
            
            if is_important or is_market_data:
                self.log_overlay.add_log(msg, lvl)
                
        logger.connect_ui(unified_log_filter)

    def _setup_hotkeys(self):
        """Регистрация глобальных хоткеев"""
        try:
            keyboard.add_hotkey("F5", lambda: self.hotkey_signal.emit("f5"))
            keyboard.add_hotkey("F6", lambda: self.hotkey_signal.emit("f6"))
            keyboard.add_hotkey("F7", lambda: self.hotkey_signal.emit("f7"))
        except Exception as e:
            get_logger().error(f"Failed to register global hotkeys: {e}")

    def _handle_hotkey_safe(self, key):
        """Обработка хоткея в основном потоке UI"""
        active = self.content_stack.currentWidget()
        if key == "f5":
            if hasattr(active, "_on_hotkey_toggle"): active._on_hotkey_toggle()
        elif key == "f6":
            if hasattr(active, "_on_hotkey_pause"): active._on_hotkey_pause()
        elif key == "f7":
            if hasattr(active, "_on_hotkey_skip"): active._on_hotkey_skip()

    def closeEvent(self, event):
        """Очистка при закрытии"""
        try:
            keyboard.unhook_all()
        except:
            pass
        super().closeEvent(event)

    def _init_tabs(self):
        """Создание и добавление реальных виджетов во вкладки"""
        from .scanner_widget import ScannerWidget
        from .buyer_widget import BuyerWidget
        from .profits_tab import ProfitsTab
        from .prices_tab import PricesTab
        from .coordinates_tab import CoordinatesTab
        from .settings_panel import SettingsPanel
        from .faq_tab import FAQTab
        
        # 0: Home / Statistics
        self.home_module = self._create_home_page()
        self.content_stack.addWidget(self.home_module)
        
        # 1: Scanner
        self.scanner_module = ScannerWidget(dashboard=self, mini_overlay=self.mini_overlay, log_overlay=self.log_overlay)
        self.content_stack.addWidget(self.scanner_module)
        
        # 2: Buyer
        self.buyer_module = BuyerWidget(dashboard=self, mini_overlay=self.mini_overlay, log_overlay=self.log_overlay)
        self.content_stack.addWidget(self.buyer_module)
        
        # 3: Profits
        self.profits_module = ProfitsTab()
        self.content_stack.addWidget(self.profits_module)
        
        # 4: Prices
        self.prices_module = PricesTab()
        self.content_stack.addWidget(self.prices_module)
        
        # 5: Coordinates
        self.coords_module = CoordinatesTab()
        self.content_stack.addWidget(self.coords_module)
        
        # 6: Settings
        self.settings_module = SettingsPanel()
        self.content_stack.addWidget(self.settings_module)
        
        # 7: FAQ
        self.faq_module = FAQTab()
        self.content_stack.addWidget(self.faq_module)

    def _create_home_page(self):
        from .components.kpi_card import KPICard
        from .components.summary_box import SummaryBox
        
        page = QWidget()
        page.setObjectName("homePage")
        main_v_layout = QVBoxLayout(page)
        main_v_layout.setContentsMargins(40, 40, 40, 40)
        main_v_layout.setSpacing(30)
        
        # --- HEADER ---
        header = QVBoxLayout()
        welcome_label = QLabel("Welcome back, Trader")
        welcome_label.setStyleSheet(f"font-size: 14px; color: {COLORS['accent']}; font-weight: 600;")
        header.addWidget(welcome_label)
        
        title = QLabel("Market Dashboard")
        title.setObjectName("title")
        title.setStyleSheet("font-size: 32px; padding: 0;")
        header.addWidget(title)
        main_v_layout.addLayout(header)
        
        # --- KPI ROW ---
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(20)
        kpi_row.addWidget(KPICard("Portfolio Value", "---", "Calculating...", "💎"))
        kpi_row.addWidget(KPICard("Active Orders", "---", "Updating...", "📦"))
        kpi_row.addWidget(KPICard("Total Profit", "---", "Today's net", "💰"))
        kpi_row.addWidget(KPICard("Success Rate", "---", "OCR Check", "🎯"))
        main_v_layout.addLayout(kpi_row)
        
        # --- BOTTOM SECTION (Recaps & Tools) ---
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(30)
        
        # Performance Box (Placeholder for Chart/Main Table)
        perf_container = QFrame()
        perf_container.setObjectName("kpiCard")
        perf_layout = QVBoxLayout(perf_container)
        perf_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        perf_label = QLabel("Performance Insights")
        perf_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #94a3b8;")
        perf_layout.addWidget(perf_label)
        perf_desc = QLabel("Detailed charts and transaction logs will be integrated here.")
        perf_desc.setStyleSheet(f"color: {COLORS['text_dark']}; font-size: 13px;")
        perf_layout.addWidget(perf_desc)
        
        bottom_layout.addWidget(perf_container, stretch=2)
        
        # Right: Quick Recap
        recap_layout = QVBoxLayout()
        recap_layout.setSpacing(20)
        
        recap_layout.addWidget(SummaryBox("🔥 HOT ITEMS", 
            ["• Data sync pending..."], 
            color="#f59e0b"))
            
        recap_layout.addWidget(SummaryBox("📍 BEST CITIES", 
            ["• Analyzing market flows..."], 
            color="#10b981"))
            
        recap_layout.addStretch()
        bottom_layout.addLayout(recap_layout, stretch=1)
        
        main_v_layout.addLayout(bottom_layout, stretch=1)
        
        return page

    def _on_nav_changed(self, index):
        self.content_stack.setCurrentIndex(index)

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainDashboard()
    sys.exit(app.exec())

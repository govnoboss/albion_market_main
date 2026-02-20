"""
Главное окно Dashboard
Единый интерфейс с сайдбаром и аналитикой
"""

import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QStackedWidget, QLabel, QFrame, QSpacerItem, QSizePolicy, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView
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
        
        self.kpi_revenue = KPICard("Всего потрачено", "0", "За период", "💰")
        self.kpi_profit = KPICard("Всего прибыли", "0", "Ожидаемый профит", "📈")
        self.kpi_items = KPICard("Куплено предметов", "0", "Шт.", "📦")
        
        kpi_row.addWidget(self.kpi_revenue)
        kpi_row.addWidget(self.kpi_profit)
        kpi_row.addWidget(self.kpi_items)
        main_v_layout.addLayout(kpi_row)
        
        # --- BOTTOM SECTION (Recaps & Tools) ---
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(30)
        
        # Performance Box (Placeholder for Chart/Main Table)
        perf_container = QFrame()
        perf_container.setObjectName("kpiCard")
        perf_layout = QVBoxLayout(perf_container)
        perf_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        # Filter Row
        filter_layout = QHBoxLayout()
        perf_label = QLabel("Performance Insights")
        perf_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #94a3b8;")
        filter_layout.addWidget(perf_label)
        
        filter_layout.addStretch()
        
        period_lbl = QLabel("За период:")
        period_lbl.setStyleSheet("color: #94a3b8; font-size: 13px;")
        filter_layout.addWidget(period_lbl)
        
        self.period_combo = QComboBox()
        self.period_combo.addItems(["1 день", "1 неделя", "1 месяц", "Всё время"])
        self.period_combo.setFixedWidth(120)
        self.period_combo.currentIndexChanged.connect(self._on_period_changed)
        filter_layout.addWidget(self.period_combo)
        
        perf_layout.addLayout(filter_layout)
        perf_layout.addSpacing(10)

        # Performance Table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "Дата", "Город", "Кол-во", "Потрачено", "Получено", "Профит"
        ])
        
        # Настройка заголовков
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive) # Дату можно крутить вручную
        self.history_table.setColumnWidth(0, 150) # Начальная ширина для даты
        
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        perf_layout.addWidget(self.history_table)
        
        bottom_layout.addWidget(perf_container, stretch=2)
        
        # Right: Quick Recap
        recap_layout = QVBoxLayout()
        recap_layout.setSpacing(20)
        
        self.hot_items_box = SummaryBox("🔥 HOT ITEMS", 
            ["• Data sync pending..."], 
            color="#f59e0b")
        recap_layout.addWidget(self.hot_items_box)
            
        recap_layout.addStretch()
        bottom_layout.addLayout(recap_layout, stretch=1)
        
        main_v_layout.addLayout(bottom_layout, stretch=1)
        
        # Начальное обновление
        QTimer.singleShot(500, self._update_home_stats)
        
        return page

    def _on_period_changed(self):
        """Обработка смены периода в выпадающем списке"""
        self._update_home_stats()

    def _update_home_stats(self):
        """Обновление KPI на главной странице"""
        from ..core.finance import finance_manager
        
        period_txt = self.period_combo.currentText()
        days_map = {
            "1 день": 1,
            "1 неделя": 7,
            "1 месяц": 30,
            "Всё время": None
        }
        days = days_map.get(period_txt)
        
        stats = finance_manager.get_stats_for_period(days)
        if stats:
            self.kpi_revenue.update_value(f"{stats['spent']:,}".replace(',', ' '), "Альбион Серебро")
            self.kpi_profit.update_value(f"{stats['profit']:,}".replace(',', ' '), "Ожидаемый профит")
            self.kpi_items.update_value(f"{stats['qty']:,}".replace(',', ' '), "Количество")

        # Обновление таблицы
        history = finance_manager.get_history_for_period(days, limit=50)
        self.history_table.setRowCount(len(history))
        
        for i, tx in enumerate(history):
            # Дата (укорачиваем)
            dt = tx['timestamp'].split('.')[0] # 2026-02-20 22:38:31
            self.history_table.setItem(i, 0, QTableWidgetItem(dt))
            self.history_table.setItem(i, 1, QTableWidgetItem(tx['city']))
            self.history_table.setItem(i, 2, QTableWidgetItem(str(tx['qty'])))
            
            spent_str = f"{tx['total']:,}".replace(',', ' ')
            self.history_table.setItem(i, 3, QTableWidgetItem(spent_str))
            
            # Доход (ожидаемая продажа в BM - налоги)
            # Profit = Inc * 0.935 - Spent => Inc * 0.935 = Profit + Spent
            # Но в БД у нас нет Inc напрямую, у нас есть profit_est и total
            income_est = tx['profit_est'] + tx['total']
            income_str = f"{income_est:,}".replace(',', ' ')
            self.history_table.setItem(i, 4, QTableWidgetItem(income_str))
            
            profit_str = f"{tx['profit_est']:,}".replace(',', ' ')
            prof_item = QTableWidgetItem(profit_str)
            if tx['profit_est'] > 0:
                prof_item.setForeground(Qt.GlobalColor.green)
            elif tx['profit_est'] < 0:
                prof_item.setForeground(Qt.GlobalColor.red)
            self.history_table.setItem(i, 5, prof_item)

        # Обновление Hot Items
        hot_items = finance_manager.get_hot_items_for_period(days, limit=5)
        hot_list = []
        for item in hot_items:
            # Формат: Название предмета Тир.Энчант Кол-во, Сколько профита
            profit_str = f"{item['total_profit']:,}".replace(',', ' ')
            hot_list.append(
                f"• {item['item_name']} T{item['tier']}.{item['enchant']} "
                f"{item['total_qty']} шт, {profit_str} с."
            )
        
        if not hot_list:
            hot_list = ["• Нет данных за период"]
            
        self.hot_items_box.update_items(hot_list)

    def _on_nav_changed(self, index):
        self.content_stack.setCurrentIndex(index)

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainDashboard()
    sys.exit(app.exec())

"""
Главное окно Dashboard
Единый интерфейс с сайдбаром и аналитикой
"""

import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QStackedWidget, QLabel, QFrame, QSpacerItem, QSizePolicy, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QIcon, QCursor

from .styles import MAIN_STYLE, COLORS
from ..utils.logger import get_logger
from ..core.version import CURRENT_VERSION
from ..core.updater import UpdateCheckWorker, UpdateDownloadWorker, install_update
from ..utils.startup_profiler import get_startup_profiler
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
        
        # Футер (Версия и Обновление)
        self.footer = QFrame()
        self.footer.setObjectName("sidebarFooter")
        self.footer_layout = QVBoxLayout(self.footer)
        self.footer_layout.setContentsMargins(10, 10, 10, 10)
        self.footer_layout.setSpacing(5)
        
        # Область обновления (скрыта по умолчанию)
        self.update_frame = QFrame()
        self.update_frame.setObjectName("updateFrame")
        self.update_frame.setStyleSheet("""
            #updateFrame {
                background-color: #1c2128;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 5px;
            }
        """)
        self.update_frame.hide()
        update_v_layout = QVBoxLayout(self.update_frame)
        update_v_layout.setContentsMargins(5, 5, 5, 5)
        update_v_layout.setSpacing(5)
        
        self.update_lbl = QLabel("Update Available")
        self.update_lbl.setStyleSheet("color: #adbac7; font-size: 11px; font-weight: bold;")
        update_v_layout.addWidget(self.update_lbl)
        
        self.update_progress = QProgressBar()
        self.update_progress.setFixedHeight(4)
        self.update_progress.setTextVisible(False)
        self.update_progress.setStyleSheet("""
            QProgressBar { background-color: #22272e; border: none; border-radius: 2px; }
            QProgressBar::chunk { background-color: #2da44e; border-radius: 2px; }
        """)
        self.update_progress.hide()
        update_v_layout.addWidget(self.update_progress)
        
        self.btn_update = QPushButton("Update Now")
        self.btn_update.setObjectName("btnUpdate")
        self.btn_update.setFixedHeight(24)
        self.btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_update.setStyleSheet(f"""
            #btnUpdate {{
                background-color: #238636;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
            }}
            #btnUpdate:hover {{ background-color: #2ea043; }}
            #btnUpdate:disabled {{ background-color: #161b22; color: #484f58; }}
        """)
        update_v_layout.addWidget(self.btn_update)
        
        self.footer_layout.addWidget(self.update_frame)

        self.version_label = QLabel(f"v{CURRENT_VERSION}")
        self.version_label.setStyleSheet("color: #484f58; font-size: 11px;")
        self.footer_layout.addWidget(self.version_label)
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
    
    def __init__(self, splash=None):
        super().__init__()
        _p = get_startup_profiler()
        self.splash = splash
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
        _p.start("sidebar_init")
        self.sidebar = Sidebar()
        self.sidebar.nav_changed.connect(self._on_nav_changed)
        self.main_layout.addWidget(self.sidebar)
        _p.end("sidebar_init")
        
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
        _p.start("init_tabs")
        self._init_tabs()
        _p.end("init_tabs")
        
        # Централизованное логирование
        _p.start("setup_logging")
        self._setup_logging()
        _p.end("setup_logging")
        
        # Глобальные хоткеи
        _p.start("setup_hotkeys")
        self._setup_hotkeys()
        self.hotkey_signal.connect(self._handle_hotkey_safe)
        _p.end("setup_hotkeys")
        
        # Вывести на передний план
        self._force_foreground()
        
        # 4. Проверка обновлений
        self._check_for_updates()

        # Final Splash Status
        if self.splash:
            self.splash.set_progress(100)
            self.splash.set_status("Готово!")
            QTimer.singleShot(500, self.splash.close)

    def _check_for_updates(self):
        """Запускает фоновую проверку обновлений"""
        self._update_info = None
        self._update_worker = UpdateCheckWorker()
        self._update_worker.update_available.connect(self._on_update_found)
        self._update_worker.start()

    def _on_update_found(self, info):
        """Когда обновление найдено, показываем плашку в сайдбаре"""
        self._update_info = info
        sidebar = self.sidebar
        sidebar.update_lbl.setText(f"New Version: {info['version']}")
        sidebar.btn_update.clicked.connect(self._start_update_download)
        sidebar.update_frame.show()

    def _start_update_download(self):
        """Начинает скачивание обновления"""
        if not self._update_info: return
        
        sidebar = self.sidebar
        sidebar.btn_update.setEnabled(False)
        sidebar.btn_update.setText("Downloading...")
        sidebar.update_progress.setValue(0)
        sidebar.update_progress.show()
        
        self._download_worker = UpdateDownloadWorker(self._update_info["download_url"])
        self._download_worker.progress.connect(self._on_download_progress)
        self._download_worker.download_complete.connect(self._on_download_complete)
        self._download_worker.download_error.connect(self._on_download_error)
        self._download_worker.start()

    def _on_download_progress(self, downloaded, total):
        if total > 0:
            percent = int(downloaded * 100 / total)
            self.sidebar.update_progress.setValue(percent)

    def _on_download_complete(self, zip_path):
        self.sidebar.update_lbl.setText("Installing...")
        QTimer.singleShot(500, lambda: install_update(zip_path))

    def _on_download_error(self, error):
        sidebar = self.sidebar
        sidebar.btn_update.setEnabled(True)
        sidebar.btn_update.setText("Retry")
        sidebar.update_lbl.setText("Error updating")
        sidebar.update_lbl.setStyleSheet("color: #f85149; font-size: 11px;")
        get_logger().error(f"Update error: {error}")

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
        _p = get_startup_profiler()
        
        def update_splash(status, progress):
            if self.splash:
                self.splash.set_status(status)
                self.splash.set_progress(progress)
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()

        update_splash("Загрузка Сканера...", 30)
        _p.start("import_scanner")
        from .scanner_widget import ScannerWidget
        _p.end("import_scanner")
        
        update_splash("Загрузка Закупщика...", 40)
        _p.start("import_buyer")
        from .buyer_widget import BuyerWidget
        _p.end("import_buyer")
        
        update_splash("Загрузка Профитов...", 50)
        _p.start("import_profits")
        from .profits_tab import ProfitsTab
        _p.end("import_profits")
        
        update_splash("Загрузка Цен...", 60)
        _p.start("import_prices")
        from .prices_tab import PricesTab
        _p.end("import_prices")
        
        update_splash("Загрузка Координат...", 70)
        _p.start("import_coordinates")
        from .coordinates_tab import CoordinatesTab
        _p.end("import_coordinates")
        
        update_splash("Загрузка Настроек...", 80)
        _p.start("import_settings")
        from .settings_panel import SettingsPanel
        _p.end("import_settings")
        
        update_splash("Загрузка FAQ...", 90)
        _p.start("import_faq")
        from .faq_tab import FAQTab
        _p.end("import_faq")
        
        # 0: Home / Statistics
        _p.start("init_home_page")
        self.home_module = self._create_home_page()
        self.content_stack.addWidget(self.home_module)
        _p.end("init_home_page")
        
        # 1: Scanner
        _p.start("init_scanner")
        self.scanner_module = ScannerWidget(dashboard=self, mini_overlay=self.mini_overlay, log_overlay=self.log_overlay)
        self.content_stack.addWidget(self.scanner_module)
        _p.end("init_scanner")
        
        # 2: Buyer
        _p.start("init_buyer")
        self.buyer_module = BuyerWidget(dashboard=self, mini_overlay=self.mini_overlay, log_overlay=self.log_overlay)
        self.content_stack.addWidget(self.buyer_module)
        _p.end("init_buyer")
        
        # 3: Profits
        _p.start("init_profits")
        self.profits_module = ProfitsTab()
        self.content_stack.addWidget(self.profits_module)
        _p.end("init_profits")
        
        # 4: Prices
        _p.start("init_prices")
        self.prices_module = PricesTab()
        self.content_stack.addWidget(self.prices_module)
        _p.end("init_prices")
        
        # 5: Coordinates
        _p.start("init_coordinates")
        self.coords_module = CoordinatesTab()
        self.content_stack.addWidget(self.coords_module)
        _p.end("init_coordinates")
        
        # 6: Settings
        _p.start("init_settings")
        self.settings_module = SettingsPanel()
        self.content_stack.addWidget(self.settings_module)
        _p.end("init_settings")
        
        # 7: FAQ
        _p.start("init_faq")
        self.faq_module = FAQTab()
        self.content_stack.addWidget(self.faq_module)
        _p.end("init_faq")

    def _create_home_page(self):
        from .components.kpi_card import KPICard
        from .components.summary_box import SummaryBox
        
        page = QWidget()
        page.setObjectName("homePage")
        main_v_layout = QVBoxLayout(page)
        main_v_layout.setContentsMargins(50, 50, 50, 50)
        main_v_layout.setSpacing(40)
        
        # --- HEADER ---
        header = QVBoxLayout()
        header.setSpacing(8)
        
        welcome_label = QLabel("Welcome back, Trader")
        welcome_label.setObjectName("subtitle")
        header.addWidget(welcome_label)
        
        title = QLabel("Market Dashboard")
        title.setObjectName("title")
        header.addWidget(title)
        
        main_v_layout.addLayout(header)
        
        # --- KPI ROW ---
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(25)
        
        self.kpi_revenue = KPICard("Всего потрачено", "0", "", "💰")
        self.kpi_profit = KPICard("Всего прибыли", "0", "", "📈")
        self.kpi_items = KPICard("Куплено предметов", "0", "", "📦")
        
        kpi_row.addWidget(self.kpi_revenue)
        kpi_row.addWidget(self.kpi_profit)
        kpi_row.addWidget(self.kpi_items)
        main_v_layout.addLayout(kpi_row)
        
        # --- BOTTOM SECTION (Recaps & Tools) ---
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(35)
        
        # Performance Box (Table)
        perf_container = QFrame()
        perf_container.setObjectName("summaryBox") # Reusing summaryBox for consistent card style
        perf_layout = QVBoxLayout(perf_container)
        perf_layout.setContentsMargins(20, 20, 20, 20)
        perf_layout.setSpacing(15)
        
        # Filter Row
        filter_layout = QHBoxLayout()
        perf_label = QLabel("Performance Insights")
        perf_label.setObjectName("summaryTitle")
        filter_layout.addWidget(perf_label)
        
        filter_layout.addStretch()
        
        period_lbl = QLabel("За период:")
        period_lbl.setStyleSheet("color: #94a3b8; font-size: 13px; font-weight: 500;")
        filter_layout.addWidget(period_lbl)
        
        self.period_combo = QComboBox()
        self.period_combo.addItems(["1 день", "1 неделя", "1 месяц", "Всё время"])
        self.period_combo.setFixedWidth(140)
        self.period_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.period_combo.currentIndexChanged.connect(self._on_period_changed)
        filter_layout.addWidget(self.period_combo)
        
        perf_layout.addLayout(filter_layout)

        # Performance Table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "Дата", "Город", "Кол-во", "Потрачено", "Получено", "Профит"
        ])
        
        # Настройка заголовков
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        self.history_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setShowGrid(False)
        
        perf_layout.addWidget(self.history_table)
        
        bottom_layout.addWidget(perf_container, stretch=2)
        
        # Right: Quick Recap (Hot Items)
        recap_layout = QVBoxLayout()
        recap_layout.setContentsMargins(0, 0, 0, 0)
        
        self.hot_items_box = SummaryBox("🔥 HOT ITEMS", 
            ["• Data sync pending..."], 
            color="#f59e0b")
        recap_layout.addWidget(self.hot_items_box)
            
        recap_layout.addStretch()
        bottom_layout.addLayout(recap_layout, stretch=1)
        
        main_v_layout.addLayout(bottom_layout, stretch=1)
        
        # Начальное обновление
        QTimer.singleShot(500, self._update_home_stats)
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
            self.kpi_revenue.update_value(f"{stats['spent']:,}".replace(',', ' '), "")
            self.kpi_profit.update_value(f"{stats['profit']:,}".replace(',', ' '), "")
            self.kpi_items.update_value(f"{stats['qty']:,}".replace(',', ' '), "")

        # Обновление таблицы (сессии закупки — одна строка = одна сессия)
        sessions = finance_manager.get_sessions_for_period(days, limit=50)
        self.history_table.setRowCount(len(sessions))
        
        for i, sess in enumerate(sessions):
            # Дата начала сессии
            ts = sess.get('session_start', '')
            dt = str(ts).split('.')[0] if ts else ''
            self.history_table.setItem(i, 0, QTableWidgetItem(dt))
            self.history_table.setItem(i, 1, QTableWidgetItem(sess.get('city', '')))
            self.history_table.setItem(i, 2, QTableWidgetItem(str(sess.get('total_qty', 0))))
            
            total_spent = sess.get('total_spent', 0) or 0
            spent_str = f"{total_spent:,}".replace(',', ' ')
            self.history_table.setItem(i, 3, QTableWidgetItem(spent_str))
            
            # Ожидаемый доход (профит + потрачено)
            total_profit = sess.get('total_profit', 0) or 0
            income_est = total_profit + total_spent
            income_str = f"{income_est:,}".replace(',', ' ')
            self.history_table.setItem(i, 4, QTableWidgetItem(income_str))
            
            profit_str = f"{total_profit:,}".replace(',', ' ')
            prof_item = QTableWidgetItem(profit_str)
            if total_profit > 0:
                prof_item.setForeground(Qt.GlobalColor.green)
            elif total_profit < 0:
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

"""
Главное окно Dashboard
Единый интерфейс с сайдбаром и аналитикой
"""

import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QStackedWidget, QLabel, QFrame, QSpacerItem, QSizePolicy, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QIcon, QCursor

from .styles import MAIN_STYLE, COLORS
from ..utils.logger import get_logger
from ..core.version import CURRENT_VERSION
from ..core.updater import UpdateCheckWorker, UpdateDownloadWorker, install_update
from ..core.license import license_manager
from ..utils.startup_profiler import get_startup_profiler
from ..utils.localization import get_text
from ..utils.hotkeys import HotkeyManager

class SidebarItem(QPushButton):
    """Элемент бокового меню"""
    def __init__(self, text, icon_name=None, parent=None):
        super().__init__(text, parent)
        self.setObjectName("sidebarItem")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.setFixedHeight(45)

class Sidebar(QFrame):
    """Боковая панель навигации"""
    nav_changed = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(200)
        
        # Get project root for icon paths
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        tg_icon = os.path.join(root_dir, "resources", "telegram.png")
        ds_icon = os.path.join(root_dir, "resources", "discord.png")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Заголовок
        self.title = QLabel("ALBION GBOT")
        self.title.setObjectName("sidebarTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.title)
        
        # Группа кнопок
        self.buttons = []
        self._add_nav_item(get_text("sidebar_home", "📊 Home"), 0)
        self._add_nav_item(get_text("sidebar_scanner", "📡 Scanner"), 1)
        self._add_nav_item(get_text("sidebar_buyer", "💰 Buyer"), 2)
        self._add_nav_item(get_text("sidebar_finance", "📈 Finance"), 3)
        self._add_nav_item(get_text("sidebar_prices", "🏷️ Prices"), 4)
        self._add_nav_item(get_text("sidebar_coordinates", "🎯 Coordinates"), 5)
        self._add_nav_item(get_text("sidebar_settings", "⚙️ Settings"), 6)
        # self._add_nav_item(get_text("sidebar_faq", "❓ Guide & FAQ"), 7)
        
        self.layout.addStretch()
        
        # --- Bottom Container (Socials & Version) ---
        bottom_container = QFrame()
        bottom_container.setObjectName("sidebarBottom")
        bottom_container.setStyleSheet("""
            #sidebarBottom {
                border-top: 1px solid #1e2923;
                background-color: rgba(0,0,0,0.1);
            }
        """)
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(10, 15, 10, 15)
        bottom_layout.setSpacing(12)
        bottom_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Заголовок соцсетей (центрированный)
        social_title = QLabel(get_text("sidebar_social_title", "СВЯЗЬ С НАМИ"))
        social_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        social_title.setStyleSheet(f"""
            color: {COLORS['text_muted']};
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1.5px;
        """)
        bottom_layout.addWidget(social_title)
        
        # Ряд иконок (центрированный)
        social_h_layout = QHBoxLayout()
        social_h_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        social_h_layout.setSpacing(15)
        
        tg_btn = self._create_social_button("Telegram", tg_icon, "https://t.me/nobrainchel")
        ds_btn = self._create_social_button("Discord", ds_icon, "https://discordapp.com/users/dendidima228")
        
        social_h_layout.addWidget(tg_btn)
        social_h_layout.addWidget(ds_btn)
        bottom_layout.addLayout(social_h_layout)

        # Область обновления (укороченная для сайдбара)
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
        
        self.update_lbl = QLabel(get_text("sidebar_update_available", "Update Available"))
        self.update_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_lbl.setStyleSheet("color: #adbac7; font-size: 10px; font-weight: bold;")
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
        
        self.btn_update = QPushButton(get_text("sidebar_btn_update", "Update"))
        self.btn_update.setObjectName("btnUpdate")
        self.btn_update.setFixedHeight(22)
        self.btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_update.setStyleSheet(f"""
            #btnUpdate {{
                background-color: #238636;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 10px;
                font-weight: 600;
            }}
            #btnUpdate:hover {{ background-color: #2ea043; }}
        """)
        update_v_layout.addWidget(self.btn_update)
        bottom_layout.addWidget(self.update_frame)

        # Версия (центрированная)
        self.version_label = QLabel(f"v{CURRENT_VERSION}")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.version_label.setStyleSheet("color: #484f58; font-size: 11px; font-weight: 600;")
        bottom_layout.addWidget(self.version_label)
        
        self.layout.addWidget(bottom_container)



    def _create_social_button(self, name, icon_path, url):
        """Создает кнопку-ссылку для соцсетей с иконкой"""
        btn = QPushButton()
        btn.setFixedSize(32, 32)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(name)
        
        if os.path.exists(icon_path):
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QSize(20, 20))
        else:
            # Fallback to text if icon missing
            btn.setText(name[0])

        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #121916;
                border: 1px solid #1e2923;
                border-radius: 8px;
                color: #10b981;
            }}
            QPushButton:hover {{
                background-color: #1a2521;
                border-color: #10b981;
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1e2d27, stop:1 #151e1b);
            }}
        """)
        
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
        return btn

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

    def update_license_display(self, expires_str):
        """Обновляет отображение лицензии в сайдбаре"""
        if not expires_str:
            self.license_label.setText(get_text("sidebar_license_unknown", "Лицензия: Неизвестно"))
            self.license_label.setStyleSheet("color: #8b949e; font-size: 10px; font-weight: 600;")
            return
        try:
            from datetime import datetime
            clean = expires_str.split('.')[0]  # Убираем микросекунды
            expires_at = datetime.fromisoformat(clean)
            now = datetime.now()
            days_left = (expires_at - now).days
            date_display = expires_at.strftime("%d.%m.%Y")

            if days_left < 0:
                text = get_text("sidebar_license_expired", "ЛИЦЕНЗИЯ ИСТЕКЛА ({date})").format(date=date_display)
                color = "#da3633"
            elif days_left < 3:
                text = get_text("sidebar_license_expiring", "Лицензия: {date} ({days} дн.) ⚠️").format(date=date_display, days=days_left)
                color = "#d29922"
            else:
                text = get_text("sidebar_license_active", "Лицензия: {date} ({days} дн.)").format(date=date_display, days=days_left)
                color = "#3fb950"

            self.license_label.setText(text)
            self.license_label.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: 600;")
        except Exception:
            self.license_label.setText(f"Лицензия: {expires_str}")
            self.license_label.setStyleSheet("color: #3fb950; font-size: 10px; font-weight: 600;")


class MainDashboard(QMainWindow):
    """Главное окно приложения (Dashboard)"""
    
    # Сигнал для потокобезопасной обработки хоткеев
    hotkey_signal = pyqtSignal(str) # "f5", "f6", "f7"
    
    def __init__(self, splash=None, license_expires=None):
        super().__init__()
        _p = get_startup_profiler()
        self.splash = splash
        self._license_expires = license_expires
        self.setWindowTitle("Albion Market Bot - Dashboard")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet(MAIN_STYLE)
        
        # Set Icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Не перехватываем клавиатуру — пусть OBS и другие приложения получают все нажатия
        self.setAttribute(Qt.WidgetAttribute.WA_KeyCompression, False)

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

        # 5. Фоновая проверка лицензии
        self._setup_daily_license_check()

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
        """Регистрация глобальных хоткеев через Windows API (не блокирует OBS и другие приложения)"""
        try:
            self._hotkey_mgr = HotkeyManager(self)
            self._hotkey_mgr.register("F5", lambda: self.hotkey_signal.emit("f5"))
            self._hotkey_mgr.register("F6", lambda: self.hotkey_signal.emit("f6"))
            self._hotkey_mgr.register("F7", lambda: self.hotkey_signal.emit("f7"))
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

    # --- License Checking Logic (Continuous) ---
    def _setup_daily_license_check(self):
        """Setup timer for daily license validation"""
        self.license_check_timer = QTimer(self)
        self.license_check_timer.timeout.connect(self._daily_license_check)
        self.license_check_timer.start(10 * 60 * 1000)  # 10 minutes (matching Launcher)
    
    def _daily_license_check(self):
        """Perform daily license check"""
        if not license_manager.should_check_today():
            return
        
        res = license_manager.validate_key()
        if res.get('success'):
            license_manager.mark_checked()
        else:
            self._start_graceful_shutdown(res.get('message', 'License expired'))
    
    def _start_graceful_shutdown(self, reason: str):
        """Start 1-minute graceful shutdown with warning"""
        self.shutdown_seconds = 60
        
        self.shutdown_dialog = QMessageBox(self)
        self.shutdown_dialog.setIcon(QMessageBox.Icon.Warning)
        self.shutdown_dialog.setWindowTitle("Лицензия недействительна")
        self.shutdown_dialog.setText(f"Причина: {reason}\n\nПриложение закроется через 60 секунд.")
        self.shutdown_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        self.shutdown_dialog.button(QMessageBox.StandardButton.Ok).setText("Понятно")
        self.shutdown_dialog.show()
        
        self.shutdown_timer = QTimer(self)
        self.shutdown_timer.timeout.connect(self._shutdown_tick)
        self.shutdown_timer.start(1000)
    
    def _shutdown_tick(self):
        """Update shutdown countdown"""
        self.shutdown_seconds -= 1
        if self.shutdown_seconds <= 0:
            from PyQt6.QtWidgets import QApplication
            QApplication.quit()
        elif hasattr(self, 'shutdown_dialog') and self.shutdown_dialog.isVisible():
            self.shutdown_dialog.setText(
                f"Приложение закроется через {self.shutdown_seconds} секунд.\n"
                f"Сохраните свою работу."
            )

    def closeEvent(self, event):
        """Очистка при закрытии"""
        try:
            if hasattr(self, '_hotkey_mgr'):
                self._hotkey_mgr.unregister_all()
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
        
        # update_splash("Загрузка FAQ...", 90)
        # _p.start("import_faq")
        # from .faq_tab import FAQTab
        # _p.end("import_faq")
        
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
        # _p.start("init_faq")
        # self.faq_module = FAQTab()
        # self.content_stack.addWidget(self.faq_module)
        # _p.end("init_faq")

    def _create_home_page(self):
        from .components.kpi_card import KPICard
        from .components.summary_box import SummaryBox
        
        page = QWidget()
        page.setObjectName("homePage")
        main_v_layout = QVBoxLayout(page)
        main_v_layout.setContentsMargins(40, 40, 40, 40)
        main_v_layout.setSpacing(30)
        
        # --- HEADER ---
        header_row = QHBoxLayout()
        header_row.setSpacing(0)
        
        header_left = QVBoxLayout()
        header_left.setSpacing(5)
        
        welcome_label = QLabel(get_text("home_welcome", "Welcome back, Trader"))
        welcome_label.setObjectName("subtitle")
        header_left.addWidget(welcome_label)
        
        title = QLabel(get_text("home_title", "Market Dashboard"))
        title.setObjectName("title")
        header_left.addWidget(title)
        
        header_row.addLayout(header_left)
        header_row.addStretch()
        
        # Лицензия (правый верхний угол)
        self.license_label = QLabel(get_text("sidebar_license_unknown", "Лицензия: Неизвестно"))
        self.license_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        self.license_label.setStyleSheet("color: #8b949e; font-size: 12px; font-weight: 600;")
        header_row.addWidget(self.license_label)
        
        if self._license_expires:
            self._update_license_label(self._license_expires)
        
        main_v_layout.addLayout(header_row)
        
        # --- KPI ROW ---
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(20)
        
        self.kpi_revenue = KPICard(get_text("home_kpi_spent", "Всего потрачено"), "0", get_text("home_kpi_spent_desc", "Invested Silver"), "💰")
        self.kpi_profit = KPICard(get_text("home_kpi_profit", "Всего прибыли"), "0", get_text("home_kpi_profit_desc", "Net Earnings"), "📈")
        self.kpi_items = KPICard(get_text("home_kpi_items", "Куплено предметов"), "0", get_text("home_kpi_items_desc", "Total Acquisitions"), "📦")
        
        kpi_row.addWidget(self.kpi_revenue)
        kpi_row.addWidget(self.kpi_profit)
        kpi_row.addWidget(self.kpi_items)
        main_v_layout.addLayout(kpi_row)
        
        # --- BOTTOM SECTION (Recaps & Tools) ---
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(25)
        
        # Performance Box (Table)
        perf_container = QFrame()
        perf_container.setObjectName("summaryBox")
        perf_layout = QVBoxLayout(perf_container)
        perf_layout.setContentsMargins(0, 0, 0, 0) # Margins handled by nested items
        perf_layout.setSpacing(0)
        
        # Filter Row Header
        filter_header = QWidget()
        filter_header.setStyleSheet("background: transparent; border-bottom: 1px solid rgba(255,255,255,0.05);")
        filter_header_layout = QHBoxLayout(filter_header)
        filter_header_layout.setContentsMargins(20, 15, 20, 15)
        
        perf_label = QLabel(get_text("home_perf_insights", "Performance Insights"))
        perf_label.setObjectName("summaryTitle")
        filter_header_layout.addWidget(perf_label)
        
        filter_header_layout.addStretch()
        
        period_lbl = QLabel(get_text("home_period", "Period:"))
        period_lbl.setStyleSheet(f"color: {COLORS['text_dark']}; font-size: 12px; font-weight: 600;")
        filter_header_layout.addWidget(period_lbl)
        
        self.period_combo = QComboBox()
        self.period_combo.addItems([
            get_text("home_period_1d", "1 день"),
            get_text("home_period_1w", "1 неделя"),
            get_text("home_period_1m", "1 месяц"),
            get_text("home_period_all", "Всё время")
        ])
        self.period_combo.setFixedWidth(120)
        self.period_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.period_combo.currentIndexChanged.connect(self._on_period_changed)
        filter_header_layout.addWidget(self.period_combo)
        
        perf_layout.addWidget(filter_header)

        # Performance Table Wrapper
        table_container = QWidget()
        table_container_layout = QVBoxLayout(table_container)
        table_container_layout.setContentsMargins(10, 10, 10, 10)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "TIME", "LOCATION", "QTY", "INVESTMENT", "REVENUE", "PROFIT"
        ])
        
        # Header setup
        thead = self.history_table.horizontalHeader()
        thead.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        thead.setStretchLastSection(True)
        thead.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.history_table.setShowGrid(False)
        self.history_table.setAlternatingRowColors(True)
        
        table_container_layout.addWidget(self.history_table)
        perf_layout.addWidget(table_container)
        
        bottom_layout.addWidget(perf_container, stretch=2)
        
        # Right: Quick Recap (Hot Items)
        recap_layout = QVBoxLayout()
        recap_layout.setContentsMargins(0, 0, 0, 0)
        
        self.hot_items_box = SummaryBox(get_text("home_hot_items", "🔥 HOT ITEMS"), 
            [f"• {get_text('home_sync_pending', 'Data sync pending...')}"], 
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
            get_text("home_period_1d", "1 день"): 1,
            get_text("home_period_1w", "1 неделя"): 7,
            get_text("home_period_1m", "1 месяц"): 30,
            get_text("home_period_all", "Всё время"): None
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
            # Дата (Time) - Muted color
            ts = sess.get('session_start', '')
            dt = str(ts).split('.')[0] if ts else ''
            time_item = QTableWidgetItem(dt)
            time_item.setForeground(Qt.GlobalColor.gray)
            self.history_table.setItem(i, 0, time_item)
            
            # Локация (City) - Accent color
            city_item = QTableWidgetItem(sess.get('city', ''))
            city_item.setForeground(Qt.GlobalColor.cyan)
            self.history_table.setItem(i, 1, city_item)
            
            # Кол-во (Qty)
            self.history_table.setItem(i, 2, QTableWidgetItem(str(sess.get('total_qty', 0))))
            
            # Инвестиции (Spent)
            total_spent = sess.get('total_spent', 0) or 0
            spent_str = f"{total_spent:,}".replace(',', ' ') + " Silver"
            spent_item = QTableWidgetItem(spent_str)
            spent_item.setForeground(Qt.GlobalColor.white)
            self.history_table.setItem(i, 3, spent_item)
            
            # Ожидаемый доход (Revenue)
            total_profit = sess.get('total_profit', 0) or 0
            income_est = total_profit + total_spent
            income_str = f"{income_est:,}".replace(',', ' ') + " Silver"
            income_item = QTableWidgetItem(income_str)
            income_item.setForeground(Qt.GlobalColor.white)
            self.history_table.setItem(i, 4, income_item)
            
            # Профит (Profit) - Success/Danger color
            profit_str = f"{total_profit:,}".replace(',', ' ') + " Silver"
            prof_item = QTableWidgetItem(profit_str)
            if total_profit > 0:
                prof_item.setForeground(Qt.GlobalColor.green)
            elif total_profit < 0:
                prof_item.setForeground(Qt.GlobalColor.red)
            self.history_table.setItem(i, 5, prof_item)

        # Обновление Hot Items
        hot_items = finance_manager.get_hot_items_for_period(days, limit=5)
        hot_list = []
        silver_suffix = get_text("home_hot_item_silver", "с.")
        for item in hot_items:
            profit_str = f"{item['total_profit']:,}".replace(',', ' ') + f" {silver_suffix}"
            hot_list.append({
                "name": f"{item['item_name']} T{item['tier']}.{item['enchant']}",
                "qty": item['total_qty'],
                "profit": profit_str
            })
        
        if not hot_list:
            hot_list = [get_text("home_no_data", "• Нет данных за период")]
            
        self.hot_items_box.update_items(hot_list)

    def _update_license_label(self, expires_str):
        """Обновляет отображение лицензии в хедере Home"""
        if not expires_str:
            return
        try:
            from datetime import datetime
            clean = expires_str.split('.')[0]
            expires_at = datetime.fromisoformat(clean)
            now = datetime.now()
            days_left = (expires_at - now).days
            date_display = expires_at.strftime("%d.%m.%Y")

            if days_left < 0:
                text = get_text("sidebar_license_expired", "ЛИЦЕНЗИЯ ИСТЕКЛА ({date})").format(date=date_display)
                color = "#da3633"
            elif days_left < 3:
                text = get_text("sidebar_license_expiring", "Лицензия: {date} ({days} дн.) ⚠️").format(date=date_display, days=days_left)
                color = "#d29922"
            else:
                text = get_text("sidebar_license_active", "Лицензия: {date} ({days} дн.)").format(date=date_display, days=days_left)
                color = "#3fb950"

            self.license_label.setText(text)
            self.license_label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 600;")
        except Exception:
            self.license_label.setText(f"License: {expires_str}")
            self.license_label.setStyleSheet("color: #3fb950; font-size: 12px; font-weight: 600;")

    def keyPressEvent(self, event):
        """Пропускаем все F-клавиши в систему (для OBS и других приложений)"""
        if Qt.Key.Key_F1 <= event.key() <= Qt.Key.Key_F12:
            event.ignore()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """Пропускаем все F-клавиши в систему"""
        if Qt.Key.Key_F1 <= event.key() <= Qt.Key.Key_F12:
            event.ignore()
            return
        super().keyReleaseEvent(event)

    def _on_nav_changed(self, index):
        self.content_stack.setCurrentIndex(index)

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainDashboard()
    sys.exit(app.exec())

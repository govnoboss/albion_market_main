"""
Albion Market Bot v3.0 - Main Window

Главное окно приложения с вкладками.
"""

import sys
import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QGroupBox, QStatusBar,
    QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QFont, QAction, QKeySequence

from config import load_settings, save_settings, AppSettings, validate_environment, BASE_DIR

logger = logging.getLogger(__name__)

# Путь к стилям
STYLES_DIR = Path(__file__).parent / "styles"


class MainWindow(QMainWindow):
    """Главное окно Albion Market Bot."""
    
    def __init__(self):
        super().__init__()
        
        self.settings = load_settings()
        self._setup_window()
        self._setup_menu()
        self._setup_ui()
        self._setup_status_bar()
        self._apply_theme()
        self._check_environment()
    
    def _setup_window(self):
        """Настройка окна."""
        self.setWindowTitle("Albion Market Bot v3.0")
        self.setMinimumSize(900, 700)
        
        # Всегда поверх (опционально)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
    
    def _setup_menu(self):
        """Создание меню."""
        menubar = self.menuBar()
        
        # Файл
        file_menu = menubar.addMenu("&Файл")
        
        save_action = QAction("&Сохранить настройки", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save_settings)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("&Выход", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Вид
        view_menu = menubar.addMenu("&Вид")
        
        topmost_action = QAction("Поверх всех окон", self)
        topmost_action.setCheckable(True)
        topmost_action.setChecked(True)
        topmost_action.triggered.connect(self._toggle_topmost)
        view_menu.addAction(topmost_action)
        
        # Помощь
        help_menu = menubar.addMenu("&Помощь")
        
        about_action = QAction("&О программе", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_ui(self):
        """Создание основного UI."""
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Заголовок
        header = QLabel("Albion Market Bot")
        header.setProperty("class", "header")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Вкладки
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Создание вкладок
        self.tabs.addTab(self._create_run_tab(), "🚀 Закупка")
        self.tabs.addTab(self._create_scanner_tab(), "📊 Сканер")  # NEW!
        self.tabs.addTab(self._create_items_tab(), "📦 Предметы")
        self.tabs.addTab(self._create_simple_settings_tab(), "✨ Настройка")
        self.tabs.addTab(self._create_template_manager_tab(), "🎯 Шаблоны")
        self.tabs.addTab(self._create_coords_tab(), "📍 Координаты (legacy)")
        self.tabs.addTab(self._create_settings_tab(), "⚙️ Дополнительно")
    
    def _create_run_tab(self) -> QWidget:
        """Вкладка запуска."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        
        # Статус
        status_group = QGroupBox("Статус")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("Готов к работе")
        self.status_label.setProperty("class", "status")
        status_layout.addWidget(self.status_label)
        
        self.progress = QProgressBar()
        self.progress.setValue(0)
        status_layout.addWidget(self.progress)
        
        self.current_item_label = QLabel("")
        self.current_item_label.setWordWrap(True)
        status_layout.addWidget(self.current_item_label)
        
        layout.addWidget(status_group)
        
        # Кнопки управления
        control_group = QGroupBox("Управление")
        control_layout = QHBoxLayout(control_group)
        
        self.btn_manual = QPushButton("Ручная закупка")
        self.btn_manual.clicked.connect(self._start_manual)
        control_layout.addWidget(self.btn_manual)
        
        self.btn_order = QPushButton("Закупка ордерами")
        self.btn_order.clicked.connect(self._start_order)
        control_layout.addWidget(self.btn_order)
        
        self.btn_sell = QPushButton("Продажа")
        self.btn_sell.clicked.connect(self._start_sell)
        control_layout.addWidget(self.btn_sell)
        
        layout.addWidget(control_group)
        
        # Горячие клавиши
        hotkeys_group = QGroupBox("Горячие клавиши")
        hotkeys_layout = QVBoxLayout(hotkeys_group)
        
        hotkeys_text = (
            "F2 — Экстренная остановка\n"
            "F3 — Пропустить текущий предмет\n"
            "F4 — Пауза / Возобновление"
        )
        hotkeys_label = QLabel(hotkeys_text)
        hotkeys_label.setProperty("class", "muted")
        hotkeys_layout.addWidget(hotkeys_label)
        
        layout.addWidget(hotkeys_group)
        layout.addStretch()
        
        return tab
    
    def _create_items_tab(self) -> QWidget:
        """Вкладка с таблицей предметов (будет расширена)."""
        from gui.widgets.item_table import ItemTableWidget
        return ItemTableWidget()
    
    def _create_scanner_tab(self) -> QWidget:
        """Вкладка сканера цен."""
        from gui.widgets.scanner_widget import ScannerWidget
        return ScannerWidget()
    
    def _create_simple_settings_tab(self) -> QWidget:
        """Вкладка упрощённых настроек (рекомендуется)."""
        from gui.widgets.simple_settings import SimplifiedSettingsPanel
        return SimplifiedSettingsPanel()
    
    def _create_template_manager_tab(self) -> QWidget:
        """Вкладка управления шаблонами кнопок."""
        from gui.widgets.template_manager import TemplateManagerWidget
        return TemplateManagerWidget()
    
    def _create_coords_tab(self) -> QWidget:
        """Вкладка координат (legacy, для совместимости)."""
        from gui.widgets.settings_panel import CoordinatesPanel
        return CoordinatesPanel(self.settings)
    
    def _create_settings_tab(self) -> QWidget:
        """Вкладка настроек."""
        from gui.widgets.settings_panel import SettingsPanel
        return SettingsPanel(self.settings)
    
    def _setup_status_bar(self):
        """Настройка статус бара."""
        self.statusBar().showMessage("Готов к работе")
    
    def _apply_theme(self):
        """Применение тёмной темы."""
        theme_path = STYLES_DIR / "dark_theme.qss"
        if theme_path.exists():
            with open(theme_path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())
    
    def _check_environment(self):
        """Проверка окружения."""
        errors = validate_environment()
        if errors:
            msg = "Обнаружены проблемы:\n\n" + "\n".join(f"• {e}" for e in errors)
            QMessageBox.warning(self, "Предупреждение", msg)
    
    # === Действия ===
    
    def _save_settings(self):
        """Сохранение настроек."""
        save_settings(self.settings)
        self.statusBar().showMessage("Настройки сохранены", 3000)
    
    def _toggle_topmost(self, checked: bool):
        """Переключение режима 'поверх всех окон'."""
        if checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()
    
    def _show_about(self):
        """Диалог 'О программе'."""
        QMessageBox.about(
            self,
            "О программе",
            "<h2>Albion Market Bot v3.0</h2>"
            "<p>Автоматизация торговли на рынке Albion Online</p>"
            "<p>© 2024-2025</p>"
        )
    
    def _start_manual(self):
        """Запуск ручной закупки."""
        # Проверка что не запущено
        if hasattr(self, '_worker') and self._worker and self._worker.isRunning():
            QMessageBox.warning(self, "Ошибка", "Процесс уже запущен!")
            return
        
        # Подтверждение
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Начать ручную закупку?\n\n"
            "Горячие клавиши:\n"
            "F2 — Остановить\n"
            "F3 — Пропустить предмет\n"
            "F4 — Пауза",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.status_label.setText("Запуск ручной закупки...")
        self.statusBar().showMessage("Подготовка...")
        
        # Импорт и запуск Smart worker (с Template Matching)
        from workers.smart_buy_worker import SmartBuyWorker
        
        self._worker = SmartBuyWorker()
        self._worker.progress.connect(self.progress.setValue)
        self._worker.status.connect(self.update_status)
        self._worker.item_info.connect(self._on_item_info)
        self._worker.finished_with_result.connect(self._on_worker_finished)
        self._worker.error.connect(self._on_worker_error)
        
        # Регистрация горячих клавиш
        self._register_hotkeys()
        
        # Старт
        self._worker.start()
        
        # Обновляем кнопки
        self.btn_manual.setEnabled(False)
        self.btn_order.setEnabled(False)
        self.btn_sell.setEnabled(False)
    
    def _start_order(self):
        """Запуск закупки ордерами."""
        QMessageBox.information(
            self, 
            "В разработке", 
            "Режим ордеров будет добавлен позже.\n"
            "Используйте ручную закупку."
        )
    
    def _start_sell(self):
        """Запуск продажи."""
        QMessageBox.information(
            self, 
            "В разработке", 
            "Режим продажи будет добавлен позже."
        )
    
    def _register_hotkeys(self):
        """Регистрация горячих клавиш."""
        import keyboard
        
        keyboard.add_hotkey('F2', self._stop_worker)
        keyboard.add_hotkey('F3', self._skip_item)
        keyboard.add_hotkey('F4', self._toggle_pause)
    
    def _unregister_hotkeys(self):
        """Снятие горячих клавиш."""
        import keyboard
        
        try:
            keyboard.remove_hotkey('F2')
            keyboard.remove_hotkey('F3')
            keyboard.remove_hotkey('F4')
        except:
            pass
    
    def _stop_worker(self):
        """Остановка worker."""
        if hasattr(self, '_worker') and self._worker:
            self._worker.stop()
            self.update_status("Остановка...")
    
    def _skip_item(self):
        """Пропуск текущего предмета."""
        if hasattr(self, '_worker') and self._worker:
            self._worker.skip_item()
            self.update_status("Пропуск...")
    
    def _toggle_pause(self):
        """Пауза/возобновление."""
        if hasattr(self, '_worker') and self._worker:
            if self._worker._paused:
                self._worker.resume()
                self.update_status("Возобновлено")
            else:
                self._worker.pause()
                self.update_status("Пауза (F4 для продолжения)")
    
    def _on_item_info(self, info: dict):
        """Обновление информации о текущем предмете."""
        name = info.get('name', '')
        limit = info.get('limit_price', 0)
        spent = info.get('total_spent', 0)
        budget = info.get('budget', 0)
        
        text = f"Предмет: {name}\nЛимит: {limit:,} | Потрачено: {spent:,} / {budget:,}"
        self.current_item_label.setText(text)
    
    def _on_worker_finished(self, success: bool, message: str):
        """Обработка завершения worker."""
        self._unregister_hotkeys()
        
        self.btn_manual.setEnabled(True)
        self.btn_order.setEnabled(True)
        self.btn_sell.setEnabled(True)
        
        self.progress.setValue(100 if success else 0)
        self.update_status(message)
        
        icon = QMessageBox.Icon.Information if success else QMessageBox.Icon.Warning
        QMessageBox.information(self, "Завершено", message)
    
    def _on_worker_error(self, error: str):
        """Обработка ошибки."""
        self.update_status(f"Ошибка: {error}")
        QMessageBox.critical(self, "Ошибка", error)
    
    def update_status(self, message: str):
        """Обновление статуса."""
        self.status_label.setText(message)
        self.statusBar().showMessage(message)
    
    def update_progress(self, value: int):
        """Обновление прогресса."""
        self.progress.setValue(value)
    
    def closeEvent(self, event):
        """Обработка закрытия окна."""
        reply = QMessageBox.question(
            self,
            "Выход",
            "Сохранить настройки перед выходом?",
            QMessageBox.StandardButton.Yes | 
            QMessageBox.StandardButton.No | 
            QMessageBox.StandardButton.Cancel
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._save_settings()
            event.accept()
        elif reply == QMessageBox.StandardButton.No:
            event.accept()
        else:
            event.ignore()


def run_app():
    """Запуск приложения."""
    app = QApplication(sys.argv)
    app.setApplicationName("Albion Market Bot")
    app.setApplicationVersion("3.0")
    
    window = MainWindow()
    window.show()
    
    return app.exec()

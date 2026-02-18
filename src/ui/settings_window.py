"""
Окно глобальных настроек — координаты и параметры.
Доступно из Лаунчера.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTabWidget
)
from PyQt6.QtCore import Qt

from .styles import MAIN_STYLE, COLORS, SETTINGS_STYLE
from .coordinates_tab import CoordinatesTab
from .settings_panel import SettingsPanel


class SettingsWindow(QMainWindow):
    """Окно настроек: Координаты + Настройки"""

    def __init__(self, launcher=None):
        super().__init__()
        self.launcher = launcher
        self.setWindowTitle("GBot - Настройки")
        self.resize(750, 600)
        self.setStyleSheet(MAIN_STYLE)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # === Заголовок ===
        header = QHBoxLayout()
        header.setSpacing(10)

        if self.launcher:
            back_btn = QPushButton("Меню")
            back_btn.setFixedSize(110, 36)
            back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            back_btn.setStyleSheet("""
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
            back_btn.clicked.connect(self._on_back)
            header.addWidget(back_btn)

        title = QLabel("⚙️ Настройки")
        title.setStyleSheet(SETTINGS_STYLE["title"])
        header.addWidget(title)
        header.addStretch()

        layout.addLayout(header)

        # === Вкладки ===
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(SETTINGS_STYLE["tabs"])

        # Вкладка 1: Координаты
        self.coords_tab = CoordinatesTab()
        self.tabs.addTab(self.coords_tab, "📍 Координаты")

        # Вкладка 2: Настройки
        self.settings_tab = SettingsPanel()
        self.tabs.addTab(self.settings_tab, "⚙️ Настройки")

        layout.addWidget(self.tabs, stretch=1)

    def _on_back(self):
        if self.launcher:
            self.launcher.show()
            self.hide()

    def closeEvent(self, event):
        if self.launcher:
            self.launcher.show()
        event.accept()

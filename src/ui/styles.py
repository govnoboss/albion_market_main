"""
Стили для Albion Market Scanner & Buyer
Современный темный дизайн с glassmorphism эффектами
"""

# Цветовая палитра
COLORS = {
    "bg_dark": "#0d1117",
    "bg_card": "#161b22",
    "bg_hover": "#21262d",
    "border": "#30363d",
    "text_primary": "#f0f6fc",
    "text_secondary": "#8b949e", 
    "accent_green": "#238636",
    "accent_green_hover": "#2ea043",
    "accent_blue": "#1f6feb",
    "accent_blue_hover": "#388bfd",
    "accent_red": "#da3633",
    "accent_orange": "#d29922",
    "success": "#3fb950",
    "warning": "#d29922",
    "error": "#f85149",
    "accent": "#1f6feb",
    "accent_hover": "#388bfd",
}

MAIN_STYLE = """
QMainWindow {
    background-color: #0d1117;
}

QWidget {
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 13px;
    color: #f0f6fc;
}

/* Заголовки */
QLabel#title {
    font-size: 24px;
    font-weight: bold;
    color: #f0f6fc;
    padding: 10px 0;
}

QLabel#subtitle {
    font-size: 14px;
    color: #8b949e;
    padding: 5px 0;
}

QLabel#sectionHeader {
    font-size: 16px;
    font-weight: 600;
    color: #f0f6fc;
    padding: 15px 0 10px 0;
    border-bottom: 1px solid #30363d;
    margin-bottom: 10px;
}

/* Карточки */
QFrame#card {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 15px;
}

QFrame#card:hover {
    border-color: #1f6feb;
    background-color: #21262d;
}

/* Кнопки */
QPushButton {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 16px;
    color: #f0f6fc;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #30363d;
    border-color: #8b949e;
}

QPushButton:pressed {
    background-color: #161b22;
}

QPushButton#primary {
    background-color: #238636;
    border-color: #238636;
}

QPushButton#primary:hover {
    background-color: #2ea043;
    border-color: #2ea043;
}

QPushButton#primary:disabled {
    background-color: #21262d;
    border-color: #30363d;
    color: #484f58;
}

QPushButton#danger {
    background-color: #da3633;
    border-color: #da3633;
}

QPushButton#danger:hover {
    background-color: #f85149;
    border-color: #f85149;
}

QPushButton#capture {
    background-color: #1f6feb;
    border-color: #1f6feb;
    min-width: 100px;
}

QPushButton#capture:hover {
    background-color: #388bfd;
    border-color: #388bfd;
}

QPushButton#capture:disabled {
    background-color: #21262d;
    border-color: #30363d;
    color: #484f58;
}

/* Поля ввода */
QLineEdit {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 12px;
    color: #f0f6fc;
    selection-background-color: #1f6feb;
}

QLineEdit:focus {
    border-color: #1f6feb;
}

QLineEdit:disabled {
    background-color: #161b22;
    color: #484f58;
}

/* Текстовое поле для логов */
QTextEdit#logViewer {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 10px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    color: #8b949e;
}

/* Список предметов */
QListWidget {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 5px;
    outline: none;
}

QListWidget::item {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 10px;
    margin: 3px;
}

QListWidget::item:selected {
    background-color: #21262d;
    border-color: #1f6feb;
}

QListWidget::item:hover {
    background-color: #21262d;
    border-color: #8b949e;
}

/* Скроллбар */
QScrollBar:vertical {
    background-color: #0d1117;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #30363d;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #484f58;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #0d1117;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background-color: #30363d;
    border-radius: 5px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #484f58;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* TabWidget */
QTabWidget::pane {
    border: 1px solid #30363d;
    border-radius: 8px;
    background-color: #161b22;
    padding: 10px;
}

QTabBar::tab {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 10px 20px;
    margin-right: 2px;
    color: #8b949e;
}

QTabBar::tab:selected {
    background-color: #161b22;
    color: #f0f6fc;
    border-color: #30363d;
}

QTabBar::tab:hover:!selected {
    background-color: #30363d;
    color: #f0f6fc;
}

/* Группа */
QGroupBox {
    border: 1px solid #30363d;
    border-radius: 8px;
    margin-top: 15px;
    padding-top: 15px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 5px;
    color: #f0f6fc;
}

/* Статус индикаторы */
QLabel#statusReady {
    color: #3fb950;
    font-weight: 600;
}

QLabel#statusCapturing {
    color: #d29922;
    font-weight: 600;
}

QLabel#statusError {
    color: #f85149;
    font-weight: 600;
}

/* SpinBox */
QSpinBox, QDoubleSpinBox {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 10px;
    color: #f0f6fc;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #1f6feb;
}

QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background-color: #21262d;
    border: none;
    width: 20px;
}

QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #30363d;
}

/* CheckBox */
QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #30363d;
    background-color: #0d1117;
}

QCheckBox::indicator:checked {
    background-color: #238636;
    border-color: #238636;
}

QCheckBox::indicator:hover {
    border-color: #1f6feb;
}

/* ProgressBar */
QProgressBar {
    border: 1px solid #30363d;
    border-radius: 6px;
    background-color: #0d1117;
    text-align: center;
    color: #f0f6fc;
}

QProgressBar::chunk {
    background-color: #238636;
    border-radius: 5px;
}

/* Tooltip */
QToolTip {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px;
    color: #f0f6fc;
}

/* QMessageBox */
QMessageBox {
    background-color: #161b22;
    color: #f0f6fc;
}

QMessageBox QLabel {
    color: #f0f6fc;
}

/* Таблицы (QTableWidget) */
QTableWidget {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    gridline-color: #30363d;
    color: #f0f6fc;
    selection-background-color: #1f6feb;
    selection-color: #f0f6fc;
    outline: none;
}

QTableWidget::item {
    padding: 5px;
    border-bottom: 1px solid #161b22;
}

QTableWidget::item:selected {
    background-color: #21262d; 
    border-bottom: 1px solid #1f6feb;
}

QHeaderView::section {
    background-color: #161b22;
    color: #8b949e;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #30363d;
    font-weight: 600;
}

QTableWidget QTableCornerButton::section {
    background-color: #161b22;
    border: none;
}
"""

# Стиль для оверлея захвата координат
CAPTURE_OVERLAY_STYLE = """
QWidget#captureOverlay {
    background-color: rgba(13, 17, 23, 200);
}

QLabel#captureInstruction {
    font-size: 24px;
    font-weight: bold;
    color: #f0f6fc;
    background-color: rgba(31, 111, 235, 200);
    border-radius: 10px;
    padding: 20px 40px;
}

QLabel#captureHint {
    font-size: 14px;
    color: #8b949e;
    margin-top: 10px;
}
"""

# --- Стили компонентов ---

SPLASH_STYLE = {
    "window": "background-color: #0d1117;",
    "title": "font-size: 24px; font-weight: bold; color: #58a6ff;",
    "status": "font-size: 12px; color: #8b949e;",
    "progress": """
        QProgressBar {
            background-color: #21262d;
            border: none;
            border-radius: 2px;
        }
        QProgressBar::chunk {
            background-color: #58a6ff;
            border-radius: 2px;
        }
    """
}

SETTINGS_STYLE = {
    "title": "font-size: 18px; font-weight: bold; color: #f0f6fc;",
    "back_btn": """
        QPushButton { 
            background: #21262d; 
            color: #8b949e; 
            border: 1px solid #30363d; 
            border-radius: 6px; 
            font-size: 13px; 
        }
        QPushButton:hover { 
            background: #30363d; 
            color: #f0f6fc; 
        }
    """,
    "tabs": """
        QTabWidget::pane { border: none; }
        QTabBar::tab {
            background: #161b22;
            color: #8b949e;
            padding: 10px 15px;
            border: 1px solid #30363d;
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            margin-right: 4px;
        }
        QTabBar::tab:selected {
            background: #0d1117;
            color: #f0f6fc;
            border-bottom-color: #0d1117;
        }
        QTabBar::tab:hover { color: #f0f6fc; }
    """
}

PANEL_STYLE = """
    QScrollArea { border: none; background-color: #0d1117; }
    QWidget { background-color: #0d1117; color: #f0f6fc; }
    QGroupBox { background-color: transparent; }
    QLabel { background-color: transparent; }
    QCheckBox { background-color: transparent; }
"""

HELP_DIALOG_STYLE = """
    QDialog {
        background-color: #0d1117;
    }
    QLabel {
        color: #f0f6fc;
    }
"""

PROFITS_STYLE = {
    "label": "font-weight: bold; color: #8b949e;",
    "combo": """
        QComboBox {
            background-color: #161b22;
            color: #c9d1d9;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 5px;
        }
        QComboBox::drop-down { border: none; }
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #8b949e;
            margin-right: 5px;
        }
        QComboBox QAbstractItemView {
            background-color: #161b22;
            color: #c9d1d9;
            selection-background-color: #1f6feb;
            border: 1px solid #30363d;
        }
    """,
    "refresh_btn": """
        QPushButton {
            background-color: #21262d;
            color: #c9d1d9;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 5px 15px;
        }
        QPushButton:hover {
            background-color: #30363d;
        }
        QPushButton:disabled {
            background-color: #161b22;
            color: #484f58;
        }
    """,
    "clean_btn": """
        QPushButton {
            background-color: #21262d;
            color: #f85149;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 5px 15px;
        }
        QPushButton:hover {
            background-color: #30363d;
            background-color: #b31d28;
            color: #ffffff;
        }
    """,
    "table": """
        QTableWidget {
            background-color: #0d1117;
            color: #c9d1d9;
            gridline-color: #30363d;
            selection-background-color: #1f6feb;
            selection-color: #ffffff;
        }
        QTableWidget QLineEdit {
            background-color: #161b22;
            color: #ffffff;
            border: 1px solid #1f6feb;
            border-radius: 2px;
            padding: 1px;
        }
    """
}

PRICES_STYLE = {
    "header": "font-size: 16px; font-weight: bold; margin-bottom: 5px;",
    "search": """
        QLineEdit {
            background-color: #161b22;
            color: #c9d1d9;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 5px;
        }
    """,
    "btn_danger": """
        QPushButton {
            background-color: #21262d;
            color: #f85149;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 5px 15px;
        }
        QPushButton:hover {
            background-color: #b31d28;
            color: #ffffff;
        }
    """,
    "btn_normal": """
        QPushButton {
            background-color: #21262d;
            color: #c9d1d9;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 5px 15px;
        }
        QPushButton:hover {
            background-color: #30363d;
        }
    """,
    "btn_delete": """
        QPushButton {
            background-color: #21262d;
            color: #c9d1d9;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 5px 15px;
        }
        QPushButton:hover {
            background-color: #b33e3e; /* Red hover */
            color: white;
            border-color: #b33e3e;
        }
        QPushButton:disabled {
            background-color: #161b22;
            color: #484f58;
            border-color: #30363d;
        }
    """,
    "dialog": """
        QInputDialog {
            background-color: #0d1117;
            color: #f0f6fc;
        }
        QLabel {
            color: #f0f6fc;
        }
        QSpinBox {
            background-color: #161b22;
            color: #f0f6fc;
            border: 1px solid #30363d;
            border-radius: 4px;
            padding: 5px;
        }
        QPushButton {
            background-color: #21262d;
            color: #f0f6fc;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 5px 15px;
            min-width: 60px;
        }
        QPushButton:hover {
            background-color: #30363d;
        }
    """,
    "msgbox": """
        QMessageBox {
            background-color: #0d1117;
        }
        QLabel {
            color: #f0f6fc;
        }
        QPushButton {
            background-color: #21262d;
            color: #f0f6fc;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 5px 15px;
            min-width: 60px;
        }
        QPushButton:hover {
            background-color: #30363d;
        }
    """
}

MINI_OVERLAY_STYLE = {
    "container_ready": """
        QFrame {
            background-color: rgba(22, 27, 34, 230);
            border: 1px solid #30363d;
            border-radius: 8px;
        }
    """,
    "container_paused": """
        QFrame {
            background-color: rgba(22, 27, 34, 230);
            border: 1px solid #d29922;
            border-radius: 8px;
        }
    """,
    "container_running": """
        QFrame {
            background-color: rgba(22, 27, 34, 230);
            border: 1px solid #3fb950;
            border-radius: 8px;
        }
    """,
    "status_ready": "color: #8b949e; font-weight: bold; border: none; background: transparent;",
    "status_paused": "color: #d29922; font-weight: bold; border: none; background: transparent;",
    "status_running": "color: #3fb950; font-weight: bold; border: none; background: transparent;",
    "restore_btn": """
        QPushButton { 
            background-color: transparent; 
            color: #8b949e; 
            border: none; 
            font-size: 14px;
            font-weight: bold;
        }
        QPushButton:hover { color: #58a6ff; }
    """,
    "start_btn": """
        QPushButton {
            background-color: #238636;
            color: #ffffff;
            border: none;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover { background-color: #2ea043; }
    """,
    "pause_btn": """
        QPushButton {
            background-color: #d29922;
            color: #ffffff;
            border: none;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover { background-color: #ac7c18; }
    """,
    "resume_btn": """
        QPushButton {
            background-color: #238636;
            color: #ffffff;
            border: none;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover { background-color: #2ea043; }
    """,
    "stop_btn": """
        QPushButton {
            background-color: #f85149;
            color: #ffffff;
            border: none;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover { background-color: #bd3832; }
    """,
    # This was slightly different in code (10px margin vs 5), 
    # but let's stick to what's used or define base.
    "base_frame": """
        QFrame {
            background-color: rgba(22, 27, 34, 240); 
            border: 1px solid #30363d;
            border-radius: 8px;
        }
    """
}

LOG_OVERLAY_STYLE = {
    "frame": """
        QFrame {
            background-color: rgba(13, 17, 23, 180); 
            border: 1px solid #30363d;
            border-radius: 8px;
        }
    """,
    "title": """
        color: #8b949e; 
        font-weight: bold; 
        font-size: 12px;
        background: transparent;
        border: none;
    """,
    "close_btn": """
        QPushButton {
            background: transparent;
            color: #8b949e;
            border: none;
            font-size: 16px;
            font-weight: bold;
        }
        QPushButton:hover { color: #f0f6fc; }
    """,
    "viewer": """
        QTextEdit {
            background-color: transparent;
            border: none;
            color: #f0f6fc;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 11px;
        }
    """
}


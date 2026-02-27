"""
Стили для Albion Market Scanner & Buyer
Современный темный дизайн с изумрудными акцентами
"""

# Цветовая палитра
COLORS = {
    "bg": "#0b0f0d",          # Deep Onyx Emerald
    "bg_card": "#121916",     # Dark Card Background
    "sidebar": "#090d0b",     # Darker Sidebar
    "accent": "#10b981",      # Pure Emerald
    "accent_hover": "#34d399", 
    "accent_soft": "rgba(16, 185, 129, 0.08)",
    "accent_glow": "rgba(16, 185, 129, 0.2)",
    "text": "#e2e8f0",        # Soft White
    "text_dark": "#64748b",   # Slate Grey
    "text_muted": "#475569",  # Muted Grey
    "border": "#1e2923",      # Subtle Border
    "border_bright": "#2d3c35",
    "danger": "#f43f5e",      # Rose Red
    "success": "#10b981",     # Success Emerald
    "warning": "#f59e0b",     # Amber
    "item_bg": "#161f1b",     # Row background
    "silver": "#94a3b8",      # Silver color
}

MAIN_STYLE = f"""
* {{
    font-family: 'Inter', 'Segoe UI', sans-serif;
    color: {COLORS['text']};
    outline: none;
}}

QMainWindow, QWidget {{
    background-color: {COLORS['bg']};
}}

/* KPI Cards */
QFrame#kpiCard {{
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1a2521, stop:1 #121916);
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
}}

QFrame#kpiCard:hover {{
    border: 1px solid {COLORS['accent_glow']};
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1e2d27, stop:1 #151e1b);
}}

QFrame#kpiCard QLabel {{
    background: transparent;
}}

QFrame#iconContainer {{
    background-color: {COLORS['accent_soft']};
    border-radius: 8px;
    min-width: 42px;
    max-width: 42px;
    min-height: 42px;
    max-height: 42px;
}}

QLabel#kpiIcon {{
    font-size: 18px;
    background: transparent;
}}

QLabel#kpiTitle {{
    color: {COLORS['text_dark']};
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
}}

QLabel#kpiValue {{
    color: {COLORS['text']};
    font-size: 26px;
    font-weight: 800;
    letter-spacing: -0.5px;
}}

QLabel#kpiSubtext {{
    color: {COLORS['text_muted']};
    font-size: 11px;
    font-weight: 500;
}}

/* Summary Boxes & Hot Items */
QFrame#summaryBox {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    padding: 10px;
}}

QFrame#summaryBox QLabel {{
    background: transparent;
}}

QLabel#summaryTitle {{
    font-size: 13px;
    font-weight: 800;
    color: {COLORS['text']};
    text-transform: uppercase;
    letter-spacing: 1.2px;
    padding-bottom: 2px;
}}

QFrame#hotItemRow {{
    background-color: {COLORS['bg']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 8px;
    margin-bottom: 5px;
}}

QFrame#hotItemRow:hover {{
    border-color: {COLORS['accent_soft']};
    background-color: #1a2521;
}}

QFrame#hotItemRow QLabel {{
    background: transparent;
}}

QLabel#hotItemName {{
    font-size: 13px;
    font-weight: 600;
    color: {COLORS['text']};
}}

QLabel#hotItemStats {{
    font-size: 11px;
    color: {COLORS['text_dark']};
}}

QLabel#hotItemProfit {{
    font-size: 12px;
    font-weight: 700;
    color: {COLORS['accent']};
}}

/* Dashboard Shell */
QWidget#dashboardContent {{
    background-color: {COLORS['bg']};
}}

QFrame#sidebar {{
    background-color: {COLORS['sidebar']};
    border-right: 1px solid {COLORS['border']};
    min-width: 220px;
    max-width: 220px;
}}

/* Sidebar Item */
QPushButton#sidebarItem {{
    background-color: transparent;
    border: none;
    border-radius: 10px;
    padding: 10px 16px;
    text-align: left;
    font-size: 14px;
    font-weight: 500;
    color: {COLORS['text_dark']};
    margin: 4px 12px;
}}

QPushButton#sidebarItem:hover {{
    background-color: #1a2521;
    color: {COLORS['text']};
}}

QPushButton#sidebarItem[active="true"] {{
    background-color: {COLORS['accent']};
    color: #ffffff;
    font-weight: 600;
}}

/* Sidebar Title */
QLabel#sidebarTitle {{
    font-size: 20px;
    font-weight: 900;
    color: {COLORS['accent']};
    padding: 32px 20px;
    letter-spacing: 1px;
}}

/* Tables */
QTableWidget {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
    gridline-color: rgba(255, 255, 255, 0.02);
    font-size: 13px;
}}

QTableWidget::item {{
    padding: 10px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.01);
}}

QTableWidget QLineEdit {{
    background-color: {COLORS['bg_card']} !important;
    border: 1px solid {COLORS['accent']};
    border-radius: 4px;
    padding: 2px 5px;
    margin: 0px;
    color: {COLORS['text']};
    selection-background-color: {COLORS['accent_soft']};
}}

QHeaderView::section {{
    background-color: transparent;
    border: none;
    padding: 10px;
    font-weight: 700;
    font-size: 11px;
    text-transform: uppercase;
    color: {COLORS['text_dark']};
    letter-spacing: 0.5px;
}}

/* Заголовки */
QLabel#title {{
    font-size: 36px;
    font-weight: 800;
    color: {COLORS['text']};
    padding: 0;
}}

QLabel#subtitle {{
    font-size: 15px;
    color: {COLORS['text_dark']};
    padding: 0;
}}

/* Кнопки */
QPushButton#primary {{
    background-color: {COLORS['accent']};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-weight: bold;
}}

QPushButton#danger:hover {{
    background-color: {COLORS['danger_hover'] if 'danger_hover' in COLORS else '#c52d2a'};
}}

/* Global Components */
QTabWidget::pane {{
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    background-color: {COLORS['bg_card']};
    margin-top: -1px;
}}

QTabBar::tab {{
    background-color: {COLORS['bg']};
    color: {COLORS['text_dark']};
    padding: 10px 20px;
    border: 1px solid {COLORS['border']};
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 4px;
    font-weight: 500;
}}

QTabBar::tab:selected {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['accent']};
    font-weight: 700;
    border-bottom: none;
}}

QTabBar::tab:hover:!selected {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text']};
}}

QGroupBox {{
    background-color: transparent;
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
    margin-top: 25px;
    padding-top: 20px;
    font-weight: 700;
    text-transform: uppercase;
    color: {COLORS['text_dark']};
    letter-spacing: 0.8px;
    font-size: 11px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 15px;
    padding: 0 5px;
}}

/* Inputs */
QLineEdit, QSpinBox, QComboBox {{
    background-color: {COLORS['bg']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 12px;
    color: {COLORS['text']};
    font-size: 13px;
}}

QLineEdit:hover, QSpinBox:hover, QComboBox:hover {{
    border-color: {COLORS['accent_soft']};
}}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: {COLORS['accent']};
    background-color: rgba(0, 255, 157, 0.02);
}}

QComboBox::drop-down {{
    border: none;
    width: 30px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid {COLORS['text_dark']};
    margin-right: 10px;
}}

/* Progress Bar */
QProgressBar {{
    background-color: {COLORS['bg']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    text-align: center;
    color: {COLORS['text']};
    font-weight: 600;
    font-size: 11px;
    height: 18px;
}}

QProgressBar::chunk {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLORS['accent_soft']}, stop:1 {COLORS['accent']});
    border-radius: 3px;
}}
"""

# Мини-оверлей
MINI_OVERLAY_STYLE = {
    "container_ready": f"background-color: {COLORS['bg_card']}; border: 1px solid {COLORS['border']}; border-radius: 10px;",
    "container_running": f"background-color: {COLORS['bg_card']}; border: 1px solid {COLORS['accent']}; border-radius: 10px;",
    "container_paused": f"background-color: {COLORS['bg_card']}; border: 1px solid {COLORS['warning']}; border-radius: 10px;",
    "status_ready": f"color: {COLORS['text_dark']}; font-weight: bold; font-size: 12px;",
    "status_running": f"color: {COLORS['accent']}; font-weight: bold; font-size: 12px;",
    "status_paused": f"color: {COLORS['warning']}; font-weight: bold; font-size: 12px;",
    "restore_btn": f"background: {COLORS['bg']}; color: white; border-radius: 4px; border: 1px solid {COLORS['border']};",
    "start_btn": f"background-color: {COLORS['accent']}; color: white; border-radius: 4px; border: none; font-weight: bold;",
    "pause_btn": f"background-color: {COLORS['warning']}; color: white; border-radius: 4px; border: none; font-weight: bold;",
    "resume_btn": f"background-color: {COLORS['accent']}; color: white; border-radius: 4px; border: none; font-weight: bold;",
    "stop_btn": f"background-color: {COLORS['danger']}; color: white; border-radius: 4px; border: none; font-weight: bold;",
}

# Оверлей логов
LOG_OVERLAY_STYLE = {
    "frame": f"background-color: rgba(11, 18, 15, 230); border: 1px solid {COLORS['border']}; border-radius: 8px;",
    "header": f"background-color: rgba(26, 37, 33, 200); border-bottom: 1px solid {COLORS['border']};",
    "title": f"color: {COLORS['text']}; font-weight: bold; font-size: 12px;",
    "close_btn": f"background: transparent; color: {COLORS['text_dark']}; border: none; font-size: 16px; font-weight: bold;",
    "viewer": f"background: transparent; border: none; color: {COLORS['text']}; font-family: 'Consolas', monospace; font-size: 11px;",
}

# Вкладка Профита
PROFITS_STYLE = {
    "label": f"color: {COLORS['text_dark']}; font-weight: bold;",
    "refresh_btn": f"background-color: {COLORS['accent']}; color: white; border-radius: 6px; padding: 8px 15px; font-weight: bold;",
    "clean_btn": f"background-color: {COLORS['danger']}; color: white; border-radius: 6px; padding: 8px 15px; font-weight: bold;",
    "table": MAIN_STYLE,
    "combo": f"background-color: {COLORS['bg_card']}; border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 5px; color: {COLORS['text']};",
}

# Вкладка Цен
PRICES_STYLE = {
    "header": f"color: {COLORS['accent']}; font-size: 18px; font-weight: bold;",
    "search": f"background-color: {COLORS['bg_card']}; border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 6px 10px; color: {COLORS['text']};",
    "btn_delete": f"background-color: {COLORS['danger']}; color: white; border-radius: 6px; padding: 6px 12px;",
    "btn_danger": f"background-color: {COLORS['danger']}; color: white; border-radius: 6px; padding: 6px 12px;",
    "btn_normal": f"background-color: {COLORS['accent']}; color: white; border-radius: 6px; padding: 6px 12px;",
    "dialog": f"background-color: {COLORS['bg']}; color: {COLORS['text']};",
    "msgbox": f"background-color: {COLORS['bg_card']}; color: {COLORS['text']};",
}

# Помощь в координатах
HELP_DIALOG_STYLE = f"""
    QDialog {{ background-color: {COLORS['bg']}; color: {COLORS['text']}; }}
    QLabel {{ color: {COLORS['text']}; }}
    QPushButton {{ background-color: {COLORS['accent']}; color: white; border-radius: 4px; padding: 5px 15px; }}
"""

# Оверлей захвата координат
CAPTURE_OVERLAY_STYLE = f"""
QWidget#captureOverlay {{
    background-color: rgba(11, 18, 15, 200);
}}

QLabel#captureInstruction {{
    font-size: 20px;
    font-weight: bold;
    color: {COLORS['text']};
    background-color: {COLORS['accent']};
    border-radius: 10px;
    padding: 15px 30px;
}}
"""

SPLASH_STYLE = {
    "window": f"background-color: {COLORS['bg']};",
    "title": f"font-size: 24px; font-weight: bold; color: {COLORS['accent']};",
    "status": f"font-size: 12px; color: {COLORS['text_dark']};",
    "progress": f"""
        QProgressBar {{
            background-color: #1a2521;
            border: none;
            border-radius: 2px;
        }}
        QProgressBar::chunk {{
            background-color: {COLORS['accent']};
            border-radius: 2px;
        }}
    """
}

SETTINGS_STYLE = {
    "title": f"font-size: 18px; font-weight: bold; color: {COLORS['text']};",
    "back_btn": f"""
        QPushButton {{ 
            background: #1a2521; 
            color: {COLORS['text_dark']}; 
            border: 1px solid {COLORS['border']}; 
            border-radius: 6px; 
            font-size: 13px; 
        }}
        QPushButton:hover {{ 
            background: #24332e; 
            color: {COLORS['text']}; 
        }}
    """,
    "tabs": f"""
        QTabWidget::pane {{ border: none; }}
        QTabBar::tab {{
            background: {COLORS['sidebar']};
            color: {COLORS['text_dark']};
            padding: 8px 15px;
            border: 1px solid {COLORS['border']};
            border-bottom: none;
            margin-right: 2px;
        }}
        QTabBar::tab:selected {{
            background: {COLORS['bg']};
            color: {COLORS['text']};
        }}
    """
}

PANEL_STYLE = f"""
    QScrollArea {{ border: none; background-color: {COLORS['bg']}; }}
    QWidget {{ background-color: {COLORS['bg']}; color: {COLORS['text']}; }}
    QGroupBox {{ background-color: transparent; border: 1px solid {COLORS['border']}; border-radius: 8px; margin-top: 15px; padding-top: 15px; font-weight: bold; }}
    QLabel {{ background-color: transparent; }}
    QCheckBox {{ background-color: transparent; }}
"""

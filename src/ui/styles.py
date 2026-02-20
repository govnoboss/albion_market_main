"""
Стили для Albion Market Scanner & Buyer
Современный темный дизайн с изумрудными акцентами
"""

# Цветовая палитра
COLORS = {
    "bg": "#0b120f",          # Black Emerald
    "bg_card": "#151e1b",     # Dark Slate Teal
    "sidebar": "#0d1613",     # Side panel
    "accent": "#10b981",      # Emerald Green
    "accent_hover": "#34d399", 
    "accent_soft": "rgba(16, 185, 129, 0.1)",
    "text": "#f0fdf4",        # Minty White
    "text_dark": "#94a3b8",   # Slate Grey
    "border": "#1e2923",      # Dark border
    "danger": "#ef4444",      # Red
    "success": "#10b981",     # Success Green
    "warning": "#f59e0b",     # Gold/Amber
    "item_bg": "#1a2521",     # Item row background
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
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 16px;
    padding: 20px;
}}

QFrame#kpiCard:hover {{
    border: 1px solid {COLORS['accent']};
    background-color: #1a2521;
}}

QFrame#iconContainer {{
    background-color: {COLORS['accent_soft']};
    border-radius: 12px;
    min-width: 44px;
    max-width: 44px;
    min-height: 44px;
    max-height: 44px;
}}

QLabel#kpiIcon {{
    font-size: 20px;
    background: transparent;
}}

QLabel#kpiTitle {{
    color: {COLORS['text_dark']};
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

QLabel#kpiValue {{
    color: {COLORS['text']};
    font-size: 24px;
    font-weight: 700;
}}

QLabel#kpiSubtext {{
    color: {COLORS['text_dark']};
    font-size: 11px;
}}

/* Activity Pulse Feed */
QFrame#activityItem {{
    background-color: transparent;
    border-bottom: 1px solid {COLORS['border']};
    padding: 8px 0;
}}

QLabel#activityTime {{
    color: {COLORS['text_dark']};
    font-size: 10px;
}}

QLabel#activityText {{
    color: {COLORS['text']};
    font-size: 12px;
}}

/* Summary Boxes */
QFrame#summaryBox {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    padding: 15px;
}}

QLabel#summaryTitle {{
    font-size: 12px;
    font-weight: 700;
    color: {COLORS['accent']};
    text-transform: uppercase;
    letter-spacing: 1px;
}}

/* Dashboard Shell */
QWidget#dashboardContent {{
    background-color: {COLORS['bg']};
}}

QFrame#sidebar {{
    background-color: {COLORS['sidebar']};
    border-right: 1px solid {COLORS['border']};
    min-width: 200px;
    max-width: 200px;
}}

/* Sidebar Item */
QPushButton#sidebarItem {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 8px 12px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
    color: {COLORS['text_dark']};
    margin: 2px 8px;
}}

QPushButton#sidebarItem:hover {{
    background-color: #1a2521;
    color: {COLORS['text']};
}}

QPushButton#sidebarItem[active="true"] {{
    background-color: {COLORS['accent']};
    color: #ffffff;
}}

/* Sidebar Title */
QLabel#sidebarTitle {{
    font-size: 18px;
    font-weight: bold;
    color: {COLORS['accent']};
    padding: 24px 16px;
}}

/* Tables */
QTableWidget {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    gridline-color: transparent;
}}

QHeaderView::section {{
    background-color: #1a2521;
    border: none;
    padding: 8px;
    font-weight: bold;
    color: {COLORS['text_dark']};
}}

/* Заголовки */
QLabel#title {{
    font-size: 24px;
    font-weight: bold;
    color: {COLORS['text']};
    padding: 10px 0;
}}

QLabel#subtitle {{
    font-size: 13px;
    color: {COLORS['text_dark']};
    padding: 2px 0;
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

QPushButton#primary:hover {{
    background-color: {COLORS['accent_hover']};
}}

QPushButton#danger {{
    background-color: {COLORS['danger']};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-weight: bold;
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

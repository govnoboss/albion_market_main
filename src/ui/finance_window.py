"""
Окно статистики финансов
Отображение расходов, доходов и истории транзакций.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QFrame, QInputDialog, QMessageBox, QAbstractItemView,
    QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from .styles import MAIN_STYLE, COLORS
from ..core.finance import finance_manager
from datetime import datetime
class FinanceWindow(QWidget):
    def __init__(self, launcher=None):
        super().__init__()
        self.launcher = launcher
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("Финансы и Статистика")
        self.resize(900, 600)
        self.setStyleSheet(MAIN_STYLE)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Заголовок
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        # Кнопка 'Меню'
        if self.launcher:
            menu_btn = QPushButton("Меню")
            menu_btn.setFixedSize(110, 36)
            menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            menu_btn.setStyleSheet("""
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
            menu_btn.clicked.connect(self._go_back)
            header_layout.addWidget(menu_btn)

        title_lbl = QLabel("💰 ФИНАНСОВАЯ АНАЛИТИКА")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #f0f6fc;")
        header_layout.addWidget(title_lbl)
        
        header_layout.addStretch()
        
        self.btn_refresh = QPushButton("🔄 Обновить")
        self.btn_refresh.setFixedWidth(100)
        self.btn_refresh.clicked.connect(self.refresh_stats)
        
        self.btn_delete_selected = QPushButton("🗑️ Удалить выбранные")
        self.btn_delete_selected.clicked.connect(self._on_delete_selected)
        self.btn_delete_selected.setStyleSheet("background-color: #3e1a1a; color: #f85149;")
        
        header_layout.addWidget(self.btn_refresh)
        header_layout.addWidget(self.btn_delete_selected)
        
        layout.addLayout(header_layout)
        
        # Сводные карточки
        stats_layout = QGridLayout()
        stats_layout.setSpacing(10)
        
        self.card_today = self._create_stat_card("ТРАТЫ СЕГОДНЯ", "0 s.", COLORS["error"])
        self.card_total = self._create_stat_card("ОБЩИЕ ТРАТЫ", "0 s.", COLORS["error"])
        self.card_profit = self._create_stat_card("ПРОГНОЗ ПРИБЫЛИ", "+0 s.", COLORS["success"])
        self.card_net_profit = self._create_stat_card("ЧИСТАЯ ПРИБЫЛЬ", "0 s.", COLORS["accent_orange"])
        
        stats_layout.addWidget(self.card_today, 0, 0)
        stats_layout.addWidget(self.card_total, 1, 0)
        stats_layout.addWidget(self.card_profit, 0, 1)
        stats_layout.addWidget(self.card_net_profit, 1, 1)
        
        layout.addLayout(stats_layout)
        
        # Таблица истории
        layout.addWidget(QLabel("📜 ПОСЛЕДНИЕ ТРАНЗАКЦИИ"))
        
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Время", "Предмет", "Тир", "Цена", "Кол-во", "Итого", "Профит"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        # Настройка колонок
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.table)
        
        self.refresh_stats()

    def _create_stat_card(self, title, value, color):
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumHeight(80)
        card.setStyleSheet(f"""
            QFrame#card {{
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 10px;
                padding: 10px;
            }}
        """)
        
        l = QVBoxLayout(card)
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size: 11px; color: #8b949e; font-weight: bold;")
        t_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        v_lbl = QLabel(value)
        v_lbl.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {color};")
        v_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        l.addWidget(t_lbl)
        l.addWidget(v_lbl)
        
        # Сохраняем ссылку на Label значения, чтобы обновлять его
        card.value_lbl = v_lbl
        return card

    def refresh_stats(self):
        """Обновление данных в окне"""
        stats = finance_manager.get_stats_summary()
        if stats:
            self.card_today.value_lbl.setText(f"{stats['today_spent']:,} s.")
            self.card_total.value_lbl.setText(f"{stats['total_spent']:,} s.")
            self.card_profit.value_lbl.setText(f"+{stats['total_profit']:,} s.")
            
            net_profit = stats['total_profit'] - stats['total_spent']
            self.card_net_profit.value_lbl.setText(f"{net_profit:+,} s.")
            
            # Динамический цвет для чистой прибыли
            if net_profit > 0:
                self.card_net_profit.value_lbl.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['success']};")
            elif net_profit < 0:
                self.card_net_profit.value_lbl.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['error']};")
            else:
                self.card_net_profit.value_lbl.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['text_secondary']};")
        
        # Загрузка истории
        history = finance_manager.get_recent_history(50)
        self.table.setRowCount(len(history))
        
        for i, row in enumerate(history):
            # Форматирование времени
            try:
                dt = datetime.fromisoformat(row['timestamp'].replace(' ', 'T'))
                time_str = dt.strftime("%H:%M:%S")
            except:
                time_str = row['timestamp']
            
            # Название предмета
            display_name = row['item_name']
            if row.get('is_simulation'):
                display_name = f"💊 {display_name}"
            
            # Создаем айтемы
            items = [
                QTableWidgetItem(time_str),
                QTableWidgetItem(display_name),
                QTableWidgetItem(f"T{row['tier']}.{row['enchant']}"),
                QTableWidgetItem(f"{row['price']:,}"),
                QTableWidgetItem(str(row['qty'])),
                QTableWidgetItem(f"{row['total']:,}"),
                QTableWidgetItem(f"{row['profit_est']:,}")
            ]
            
            # Сохраняем данные во втором айтеме (название предмета) для удобства
            items[0].setData(Qt.ItemDataRole.UserRole, row)
            
            for col, item in enumerate(items):
                if col == 6: # Профит
                    item.setForeground(QColor(COLORS["success"]))
                
                # Центрирование (кроме названия предмета)
                if col != 1:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                self.table.setItem(i, col, item)

    def _on_delete_selected(self):
        selection = self.table.selectionModel().selectedRows()
        if not selection:
            return
            
        confirm = QMessageBox.question(
            self, "Удаление", f"Удалить выбранные транзакции ({len(selection)} шт.)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            for index in selection:
                row = index.row()
                # Retrieve row data from first column
                data = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                if data:
                    finance_manager.delete_transaction(data['id'])
            self.refresh_stats()

    def _on_item_double_clicked(self, item):
        column = item.column()
        row = item.row()
        data = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if not data: return
        
        if column == 3: # Цена
            self._edit_field(data, "price")
        elif column == 4: # Кол-во
            self._edit_field(data, "qty")

    def _edit_field(self, row_data, field):
        if field == "price":
            new_val, ok = QInputDialog.getInt(
                self, "Редактирование", f"Новая цена для {row_data['item_name']}:", 
                row_data['price'], 0, 1000000000
            )
            if ok:
                finance_manager.update_transaction(row_data['id'], new_val, row_data['qty'])
                self.refresh_stats()
        elif field == "qty":
            new_val, ok = QInputDialog.getInt(
                self, "Редактирование", f"Новое количество для {row_data['item_name']}:", 
                row_data['qty'], 1, 1000000
            )
            if ok:
                finance_manager.update_transaction(row_data['id'], row_data['price'], new_val)
                self.refresh_stats()

    def _on_edit_clicked(self, row):
        # 1. Изменение Цены
        new_price, ok1 = QInputDialog.getInt(
            self, "Редактирование", f"Новая цена для {row['item_name']}:", 
            row['price'], 0, 1000000000
        )
        if not ok1: return
        
        # 2. Изменение Количества
        new_qty, ok2 = QInputDialog.getInt(
            self, "Редактирование", f"Новое количество:", 
            row['qty'], 1, 1000000
        )
        if not ok2: return
        
        finance_manager.update_transaction(row['id'], new_price, new_qty)
        self.refresh_stats()

    def _go_back(self):
        if self.launcher:
            self.launcher.show()
            self.hide()

    def showEvent(self, event):
        """Автообновление при открытии"""
        super().showEvent(event)
        self.refresh_stats()

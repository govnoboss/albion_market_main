from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QSpinBox, QCheckBox, QPushButton, QHeaderView, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush

from ...utils.config import get_config
from ...utils.logger import get_logger
from ..styles import COLORS

class PurchasePlanTab(QWidget):
    """
    Вкладка настройки оптовой закупки (Wholesale).
    Позволяет задать лимиты покупки для каждого предмета/тира/энчанта.
    """
    
    def __init__(self):
        super().__init__()
        self.config = get_config()
        self.logger = get_logger()
        self._items_cache = {} # Map: item_name -> QTreeWidgetItem
        
        self._init_ui()
        self.refresh_data()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # --- Toolbar ---
        toolbar = QHBoxLayout()
        
        expand_btn = QPushButton("Развернуть всё")
        expand_btn.clicked.connect(lambda: self.tree.expandAll())
        toolbar.addWidget(expand_btn)
        
        collapse_btn = QPushButton("Свернуть всё")
        collapse_btn.clicked.connect(lambda: self.tree.collapseAll())
        toolbar.addWidget(collapse_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # --- Tree Widget ---
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Предмет / Вариация", "Лимит (шт.)", "Мин. Профит %"])
        self.tree.setColumnWidth(0, 300)
        self.tree.setColumnWidth(1, 100)
        self.tree.setColumnWidth(2, 100)
        self.tree.setAlternatingRowColors(True)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #0d1117;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #161b22;
                color: #8b949e;
                padding: 4px;
                border: none;
            }
            QTreeWidget::item {
                padding: 4px;
            }
        """)
        
        layout.addWidget(self.tree)
        
        # --- Footer Info ---
        info_lbl = QLabel("ℹ️ Установите лимит > 0 и минимальный % профита для активации.")
        info_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(info_lbl)
        
        # --- Auto-Apply Defaults on First Run ---
        if not self.config.get_wholesale_targets():
             self._apply_default_presets(silent=True)

    def _apply_default_presets(self, silent=False):
        """Применить дефолтные лимиты ко всем предметам"""
        if not silent:
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, "Применение пресетов",
                "Это перезапишет текущие лимиты...\nПродолжить?",
                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            
        items = self.config.get_known_items()
        count = 0
        
        for item in items:
            for tier in range(4, 9):
                for enchant in range(5):
                    limit = 0
                    if enchant == 0:
                        if tier == 4: limit = 100
                        elif tier == 5: limit = 75
                        elif tier == 6: limit = 35
                        elif tier == 7: limit = 10
                        elif tier == 8: limit = 5
                    else:
                        if tier <= 6: limit = 5  # T4-T6
                        else: limit = 1          # T7-T8
                        
                    self.config.set_wholesale_target(item, tier, enchant, limit, True, min_profit=25)
                    count += 1
        
        if silent:
             self.logger.info(f"Первый запуск: Применены дефолт-лимиты ({count})")
        else:
             self.logger.info(f"Пресеты применены: {count}")
             self.refresh_data()

    def refresh_data(self):
        """Пересоздать дерево на основе списка предметов сканера"""
        self.tree.clear()
        self._items_cache = {}
        
        items = self.config.get_known_items() # Или get_items()? Лучше items (активные)
        # Используем known_items, так как именно они сканируются ботом
        target_items = self.config.get_known_items()
        
        if not target_items:
            # Fallback если активно ничего не сканится
            return

        for item_name in sorted(target_items):
            # Root Item Node
            item_node = QTreeWidgetItem(self.tree)
            item_node.setText(0, item_name)
            item_node.setExpanded(False)
            
            # Добавляем Tiers (4-8)
            for tier in range(4, 9):
                tier_node = QTreeWidgetItem(item_node)
                tier_node.setText(0, f"Tier {tier}")
                
                # Enchant (0-4)
                for enchant in range(5):
                    self._create_variant_row(tier_node, item_name, tier, enchant)
                    
    def _create_variant_row(self, parent, item_name, tier, enchant):
        """Создать строку для конкретной вариации"""
        node = QTreeWidgetItem(parent)
        label = f"T{tier}.{enchant}"
        node.setText(0, label)
        
        # Загружаем текущие настройки
        limit, enabled, min_profit = self.config.get_wholesale_limit(item_name, tier, enchant)
        
        # 1. SpinBox (Limit)
        spin_limit = QSpinBox()
        spin_limit.setRange(0, 9999)
        spin_limit.setValue(limit)
        spin_limit.setSingleStep(10)
        spin_limit.setFixedWidth(80)
        spin_limit.setStyleSheet("background: #0d1117; color: #f0f6fc; border: 1px solid #30363d;")
        spin_limit.valueChanged.connect(lambda val, i=item_name, t=tier, e=enchant: 
                                  self._on_limit_changed(i, t, e, val))
        
        self.tree.setItemWidget(node, 1, spin_limit)
        
        # 2. SpinBox (Min Profit %)
        spin_profit = QSpinBox()
        spin_profit.setRange(0, 1000)
        spin_profit.setValue(min_profit)
        spin_profit.setSuffix("%")
        spin_profit.setFixedWidth(80)
        spin_profit.setStyleSheet("background: #0d1117; color: #f0f6fc; border: 1px solid #30363d;")
        spin_profit.valueChanged.connect(lambda val, i=item_name, t=tier, e=enchant: 
                                  self._on_min_profit_changed(i, t, e, val))
        
        self.tree.setItemWidget(node, 2, spin_profit)
        
    def _on_limit_changed(self, item, tier, enchant, value):
        # Автоматически ставим enabled True если лимит > 0
        is_enabled = (value > 0)
        _, _, min_profit = self.config.get_wholesale_limit(item, tier, enchant)
        self.config.set_wholesale_target(item, tier, enchant, value, is_enabled, min_profit)

    def _on_min_profit_changed(self, item, tier, enchant, value):
        limit, enabled, _ = self.config.get_wholesale_limit(item, tier, enchant)
        self.config.set_wholesale_target(item, tier, enchant, limit, enabled, value)

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QSpinBox, QCheckBox, QPushButton, QHeaderView, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush

from ...utils.config import get_config
from ...utils.logger import get_logger
from ...utils.localization import get_text
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
        
        expand_btn = QPushButton(get_text("pp_expand_all", "Развернуть всё"))
        expand_btn.clicked.connect(lambda: self.tree.expandAll())
        toolbar.addWidget(expand_btn)
        
        collapse_btn = QPushButton(get_text("pp_collapse_all", "Свернуть всё"))
        collapse_btn.clicked.connect(lambda: self.tree.collapseAll())
        toolbar.addWidget(collapse_btn)
        
        self.refresh_btn = QPushButton(get_text("pp_refresh_list", "🔄 Обновить список"))
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {COLORS['bg_card']}; 
                color: {COLORS['text']}; 
                border: 1px solid {COLORS['border']}; 
                border-radius: 6px;
                padding: 5px 15px;
            }}
            QPushButton:hover {{ background-color: {COLORS['item_bg']}; }}
        """)
        self.refresh_btn.clicked.connect(self.refresh_data)
        toolbar.addWidget(self.refresh_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # --- Tree Widget ---
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([
            get_text("pp_header_item", "Предмет / Вариация"), 
            get_text("pp_header_limit", "Лимит (шт.)"), 
            get_text("pp_header_profit", "Мин. Профит %")
        ])
        self.tree.setColumnWidth(0, 300)
        self.tree.setColumnWidth(1, 100)
        self.tree.setColumnWidth(2, 100)
        self.tree.setAlternatingRowColors(True)
        self.tree.setAnimated(False) # Отключаем анимацию для скорости
        self.tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
            }}
            QHeaderView::section {{
                background-color: {COLORS['item_bg']};
                color: {COLORS['text_dark']};
                padding: 4px;
                border: none;
            }}
            QTreeWidget::item {{
                padding: 4px;
            }}
        """)
        
        layout.addWidget(self.tree)
        
        # --- Footer Info ---
        info_lbl = QLabel(get_text("pp_footer_info", "ℹ️ Установите лимит > 0 и минимальный % профита для активации."))
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
                self, get_text("pp_preset_title", "Применение пресетов"),
                get_text("pp_preset_confirm", "Это перезапишет текущие лимиты...\nПродолжить?"),
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
         """Инкрементальное обновление дерева на основе списка предметов сканера"""
         self.tree.setUpdatesEnabled(False)
         try:
            target_items = set(self.config.get_known_items())
            
            # 1. Находим что удалить
            existing_items = set(self._items_cache.keys())
            to_remove = existing_items - target_items
            
            for item_name in to_remove:
                root_node = self._items_cache.pop(item_name)
                index = self.tree.indexOfTopLevelItem(root_node)
                if index >= 0:
                    self.tree.takeTopLevelItem(index)
            
            # 2. Находим что добавить
            to_add = target_items - existing_items
            
            # Сохраняем порядок из конфига для новых предметов
            order = self.config.get_known_items()
            to_add_ordered = [x for x in order if x in to_add]
            
            for item_name in to_add_ordered:
                # Root Item Node
                item_node = QTreeWidgetItem(self.tree)
                item_node.setText(0, item_name)
                item_node.setExpanded(False)
                self._items_cache[item_name] = item_node
                
                # Добавляем Tiers (4-8)
                for tier in range(4, 9):
                    tier_node = QTreeWidgetItem(item_node)
                    tier_node.setText(0, f"Tier {tier}")
                    
                    # Enchant (0-4)
                    for enchant in range(5):
                        self._create_variant_row(tier_node, item_name, tier, enchant)
            
            # 3. Если дерево было пустое (первая загрузка)
            if not self._items_cache and target_items:
                # В этом случае cache пустой, проходим по всем в порядке конфига
                for item_name in order:
                    item_node = QTreeWidgetItem(self.tree)
                    item_node.setText(0, item_name)
                    self._items_cache[item_name] = item_node
                    for tier in range(4, 9):
                        tier_node = QTreeWidgetItem(item_node)
                        tier_node.setText(0, f"Tier {tier}")
                        for enchant in range(5):
                            self._create_variant_row(tier_node, item_name, tier, enchant)

         finally:
            self.tree.setUpdatesEnabled(True)
            self.tree.update()
                    
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
        spin_limit.setStyleSheet(f"background: {COLORS['bg']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
        spin_limit.valueChanged.connect(lambda val, i=item_name, t=tier, e=enchant: 
                                  self._on_limit_changed(i, t, e, val))
        
        self.tree.setItemWidget(node, 1, spin_limit)
        
        # 2. SpinBox (Min Profit %)
        spin_profit = QSpinBox()
        spin_profit.setRange(0, 1000)
        spin_profit.setValue(min_profit)
        spin_profit.setSuffix("%")
        spin_profit.setFixedWidth(80)
        spin_profit.setStyleSheet(f"background: {COLORS['bg']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']};")
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

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLineEdit, QListWidget, QLabel, QCompleter,
    QTabWidget, QTextEdit, QMessageBox, QGroupBox, QGridLayout
)
import json

from ..utils.config import get_config
from ..utils.logger import get_logger
from ..utils.items_db import get_default_items
from ..utils.default_exceptions import get_default_exceptions
from ..utils.localization import get_text


class ItemsPanel(QWidget):
    """Панель управления базой предметов и исключениями"""
    
    def __init__(self):
        super().__init__()
        self.exception_lists = {} # {key: QListWidget}
        self.exception_inputs = {} # {key: QLineEdit}
        
        self._init_known_items()
        self._setup_ui()
        self._load_database_list()
        self._load_exceptions()
    
    def showEvent(self, event):
        """Обновить данные при каждом показе вкладки"""
        super().showEvent(event)
        self._load_database_list()
        self._load_exceptions()
    
    def _init_known_items(self):
        """Инъекция базы предметов в конфиг при запуске (только если база пуста)"""
        config = get_config()
        current_db = config.get_known_items()
        
        # Если база уже содержит предметы, не восстанавливаем дефолтные
        if current_db:
            return
            
        # Если база пуста — загружаем стандартный набор для текущего языка
        default_items = get_default_items()
        config.set_known_items(default_items)
        get_logger().info(f"База предметов инициализирована: {len(default_items)} дефолтных записей")

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_database_tab(), get_text("items_db_tab", "База предметов"))
        self.tabs.addTab(self._create_exceptions_tab(), get_text("items_exc_tab", "Исключения тиров"))
        
        layout.addWidget(self.tabs)

    def _create_database_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # Заголовок
        header = QLabel(get_text("items_db_title", "📚 База предметов"))
        header.setObjectName("summaryTitle")
        layout.addWidget(header)
        
        # Описание
        desc = QLabel(get_text("items_db_desc", "Предметы, которые бот умеет распознавать (используются для автодополнения)"))
        desc.setStyleSheet("color: #8b949e; margin-bottom: 10px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # === Добавление в базу ===
        add_db_layout = QHBoxLayout()
        self.db_input = QLineEdit()
        self.db_input.setPlaceholderText(get_text("items_db_placeholder", "Новое название предмета..."))
        self.db_input.setClearButtonEnabled(True)
        add_db_layout.addWidget(self.db_input)
        
        add_db_btn = QPushButton(get_text("items_btn_add", "Добавить"))
        add_db_btn.setObjectName("primary")
        add_db_btn.clicked.connect(self._add_to_database)
        add_db_layout.addWidget(add_db_btn)
        
        del_db_btn = QPushButton(get_text("items_btn_delete", "Удалить"))
        del_db_btn.setStyleSheet("background-color: #da3633; color: white;")
        del_db_btn.clicked.connect(self._remove_from_database)
        add_db_layout.addWidget(del_db_btn)
        
        layout.addLayout(add_db_layout)
        
        # === Список базы ===
        self.db_list = QListWidget()
        self.db_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.db_list.setDragEnabled(True)
        self.db_list.setAcceptDrops(True)
        self.db_list.setDropIndicatorShown(True)
        self.db_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.db_list.model().rowsMoved.connect(self._save_database_order)
        layout.addWidget(self.db_list)
        return tab

    def _create_exceptions_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab) # Горизонтальное расположение колонок
        layout.setSpacing(10)
        
        # Колонки
        layout.addWidget(self._create_tier_group(get_text("items_tier_group", "Tier {n} (T{a}-T8)").format(n=1, a=1), "Tier_1"))
        layout.addWidget(self._create_tier_group(get_text("items_tier_group", "Tier {n} (T{a}-T8)").format(n=2, a=2), "Tier_2"))
        layout.addWidget(self._create_tier_group(get_text("items_tier_group", "Tier {n} (T{a}-T8)").format(n=3, a=3), "Tier_3"))
        
        return tab

    def _create_tier_group(self, title, key):
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        
        # Список
        list_widget = QListWidget()
        layout.addWidget(list_widget)
        self.exception_lists[key] = list_widget
        
        # Поле ввода
        input_field = QLineEdit()
        input_field.setPlaceholderText(get_text("home_no_data", "Предмет...")[2:]) # Reuse similar if needed or create new
        layout.addWidget(input_field)
        self.exception_inputs[key] = input_field
        
        # Кнопки
        btn_layout = QHBoxLayout()
        add_btn = QPushButton(get_text("items_btn_add", "Добавить"))
        add_btn.clicked.connect(lambda: self._add_exception(key))
        
        del_btn = QPushButton(get_text("items_btn_delete", "Удалить"))
        del_btn.setStyleSheet("background-color: #da3633; color: white;")
        del_btn.clicked.connect(lambda: self._remove_exception(key))
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        layout.addLayout(btn_layout)
        
        return group

    def _load_database_list(self):
        self.db_list.blockSignals(True)
        self.db_list.clear()
        items = get_config().get_known_items()
        self.db_list.addItems(items)
        self.db_list.blockSignals(False)

    def _save_database_order(self, *args):
        """Сохранить текущий порядок элементов в конфиг"""
        # Считываем названия предметов из списка
        items = [self.db_list.item(i).text() for i in range(self.db_list.count())]
        get_config().set_known_items(items)
        # get_logger().debug(f"Порядок базы предметов сохранен: {len(items)} записей")

    def _load_exceptions(self):
        """Загрузка исключений (с мержа дефолтных значений)"""
        current_data = get_config().get_tier_exceptions()
        default_exceptions = get_default_exceptions()
        
        # Проверка и мерж дефолтных, если пусто
        updated = False
        for key, default_items in default_exceptions.items():
            if key not in current_data:
                current_data[key] = []
            
            # Если список пуст, заполняем дефолтными (только один раз при инициализации)
            # Логика: Если в конфиге ПУСТО ДЛЯ ЭТОГО КЛЮЧА, то заливаем дефолт.
            if not current_data[key] and default_items:
                 current_data[key] = default_items
                 updated = True
        
        if updated:
            get_config().set_tier_exceptions(current_data)
            
        # Отображение
        for key, items in current_data.items():
            if key in self.exception_lists:
                self.exception_lists[key].clear()
                self.exception_lists[key].addItems(sorted(items))

    def _add_exception(self, key):
        input_field = self.exception_inputs.get(key)
        list_widget = self.exception_lists.get(key)
        
        if not input_field or not list_widget: return
        
        text = input_field.text().strip()
        if not text: return
        
        # Добавляем если нет
        items = [list_widget.item(i).text() for i in range(list_widget.count())]
        if text not in items:
            list_widget.addItem(text)
            list_widget.sortItems()
            input_field.clear()
            self._save_current_exceptions()
            get_logger().info(f"Исключение добавлено в {key}: {text}")

    def _remove_exception(self, key):
        list_widget = self.exception_lists.get(key)
        if not list_widget: return
        
        selected_items = list_widget.selectedItems()
        if not selected_items: return
        
        for item in selected_items:
            list_widget.takeItem(list_widget.row(item))
            
        self._save_current_exceptions()
        get_logger().info(f"Исключение удалено из {key}")

    def _save_current_exceptions(self):
        data = {}
        for key, list_widget in self.exception_lists.items():
            items = [list_widget.item(i).text() for i in range(list_widget.count())]
            data[key] = items
        
        get_config().set_tier_exceptions(data)

    def _add_to_database(self):
        name = self.db_input.text().strip()
        if name:
            get_config().add_known_item(name)
            self._load_database_list()
            self.db_input.clear()
            get_logger().info(f"В базу добавлен: {name}")

    def _remove_from_database(self):
        """Удалить выбранные предметы из базы"""
        selected_items = self.db_list.selectedItems()
        if not selected_items:
            return
        
        config = get_config()
        current_items = config.get_known_items()
        
        removed_count = 0
        for item in selected_items:
            item_name = item.text()
            if item_name in current_items:
                current_items.remove(item_name)
                removed_count += 1
        
        config.set_known_items(current_items)
        self._load_database_list()
        get_logger().info(f"Удалено из базы: {removed_count} предметов")

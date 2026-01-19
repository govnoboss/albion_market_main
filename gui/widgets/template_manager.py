"""
Albion Market Bot v3.0 - Template Manager Widget

Виджет для просмотра и захвата шаблонов кнопок.
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QGroupBox, QScrollArea,
    QMessageBox, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QImage

from PIL import ImageGrab
import numpy as np

from config import BASE_DIR

TEMPLATES_DIR = BASE_DIR / "buttons_image"


class TemplateItem(QFrame):
    """Виджет одного шаблона кнопки."""
    
    def __init__(self, name: str, image_path: Path, parent=None):
        super().__init__(parent)
        self.name = name
        self.image_path = image_path
        
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #313244;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # Название
        name_label = QLabel(name.replace('_', ' ').title())
        name_label.setStyleSheet("font-weight: bold; color: #cdd6f4;")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)
        
        # Превью изображения
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(50)
        self._load_preview()
        layout.addWidget(self.preview_label)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        
        self.capture_btn = QPushButton("📷 Захватить")
        self.capture_btn.clicked.connect(self._start_capture)
        buttons_layout.addWidget(self.capture_btn)
        
        self.test_btn = QPushButton("🔍 Тест")
        self.test_btn.clicked.connect(self._test_template)
        buttons_layout.addWidget(self.test_btn)
        
        layout.addLayout(buttons_layout)
        
        # Статус
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #a6adc8; font-size: 9pt;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        self._overlay = None
    
    def _load_preview(self):
        """Загрузка превью шаблона."""
        if self.image_path.exists():
            pixmap = QPixmap(str(self.image_path))
            # Масштабируем для превью
            scaled = pixmap.scaled(
                QSize(100, 50), 
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled)
        else:
            self.preview_label.setText("❌ Нет изображения")
            self.preview_label.setStyleSheet("color: #f38ba8;")
    
    def _start_capture(self):
        """Начать захват шаблона."""
        from gui.widgets.region_capture import RegionCaptureOverlay
        
        main_window = self.window()
        if main_window:
            main_window.hide()
        
        self._overlay = RegionCaptureOverlay()
        self._overlay.region_captured.connect(self._on_region_captured)
        self._overlay.capture_cancelled.connect(self._on_capture_cancelled)
        self._overlay.start_capture()
    
    def _on_region_captured(self, left: int, top: int, width: int, height: int):
        """Сохранение захваченной области как шаблона."""
        try:
            # Скриншот области
            bbox = (left, top, left + width, top + height)
            screenshot = ImageGrab.grab(bbox=bbox)
            
            # Сохранение
            TEMPLATES_DIR.mkdir(exist_ok=True)
            screenshot.save(str(self.image_path))
            
            # Обновление превью
            self._load_preview()
            self.status_label.setText(f"✅ Сохранено ({width}×{height})")
            self.status_label.setStyleSheet("color: #a6e3a1; font-size: 9pt;")
            
            # Перезагрузка шаблонов
            from core.template_matcher import get_template_matcher
            matcher = get_template_matcher()
            matcher._load_templates()
            
        except Exception as e:
            self.status_label.setText(f"❌ Ошибка: {e}")
            self.status_label.setStyleSheet("color: #f38ba8; font-size: 9pt;")
        
        main_window = self.window()
        if main_window:
            main_window.show()
    
    def _on_capture_cancelled(self):
        main_window = self.window()
        if main_window:
            main_window.show()
    
    def _test_template(self):
        """Тестирование поиска шаблона на экране."""
        from core.template_matcher import get_template_matcher
        
        if not self.image_path.exists():
            self.status_label.setText("❌ Шаблон не найден")
            self.status_label.setStyleSheet("color: #f38ba8; font-size: 9pt;")
            return
        
        matcher = get_template_matcher()
        result = matcher.find_on_screen(self.name)
        
        if result.found:
            self.status_label.setText(f"✅ Найдено ({result.confidence:.0%}) @ ({result.center[0]}, {result.center[1]})")
            self.status_label.setStyleSheet("color: #a6e3a1; font-size: 9pt;")
        else:
            conf_text = f" (макс: {result.confidence:.0%})" if result.confidence > 0 else ""
            self.status_label.setText(f"❌ Не найдено{conf_text}")
            self.status_label.setStyleSheet("color: #f38ba8; font-size: 9pt;")


class TemplateManagerWidget(QWidget):
    """
    Менеджер шаблонов кнопок.
    
    Позволяет:
    - Просматривать текущие шаблоны
    - Захватывать новые шаблоны с экрана
    - Тестировать распознавание
    """
    
    # Список шаблонов для управления
    TEMPLATE_NAMES = [
        # Закупка
        'buy_button',
        'ok_button', 
        'clear_button',
        'search_button',
        'sell_button',
        'yes_button',
        'quantity_input_button',
        'make_order',
        # Сканер - панель
        'expand_arrow',       # Стрелка раскрытия панели ◀
        'collapse_arrow',     # Стрелка свёрнутой панели ▶
        'close_item_panel',   # Крестик закрытия окна предмета
        # Сканер - dropdown фильтры
        'tier_dropdown',      # Кнопка "Уровень N" (тир)
        'enchant_dropdown',   # Кнопка "Зачарован..." (энчант)
        'quality_dropdown',   # Кнопка "Обычное" (качество)
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Заголовок
        header = QLabel("🎯 Менеджер шаблонов кнопок")
        header.setStyleSheet("font-size: 14pt; font-weight: bold; color: #89b4fa;")
        layout.addWidget(header)
        
        # Инструкция
        info = QLabel(
            "Если кнопки не находятся автоматически — захватите их заново.\n"
            "Откройте окно рынка в игре, затем нажмите '📷 Захватить' и выделите кнопку."
        )
        info.setStyleSheet("color: #a6adc8;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Сетка шаблонов
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(12)
        
        for i, name in enumerate(self.TEMPLATE_NAMES):
            image_path = TEMPLATES_DIR / f"{name}.png"
            item = TemplateItem(name, image_path)
            
            row = i // 2
            col = i % 2
            grid_layout.addWidget(item, row, col)
        
        scroll.setWidget(grid_widget)
        layout.addWidget(scroll)
        
        # Кнопки внизу
        buttons_layout = QHBoxLayout()
        
        test_all_btn = QPushButton("🔍 Тестировать все")
        test_all_btn.clicked.connect(self._test_all)
        buttons_layout.addWidget(test_all_btn)
        
        reload_btn = QPushButton("🔄 Перезагрузить шаблоны")
        reload_btn.clicked.connect(self._reload_templates)
        buttons_layout.addWidget(reload_btn)
        
        layout.addLayout(buttons_layout)
    
    def _test_all(self):
        """Тестирование всех шаблонов."""
        from core.template_matcher import get_template_matcher
        
        matcher = get_template_matcher()
        results = []
        found_count = 0
        
        for name in self.TEMPLATE_NAMES:
            result = matcher.find_on_screen(name)
            status = "✅" if result.found else "❌"
            if result.found:
                found_count += 1
            conf = f"{result.confidence:.0%}" if result.confidence > 0 else "N/A"
            results.append(f"{status} {name}: {conf}")
        
        msg = f"Найдено: {found_count}/{len(self.TEMPLATE_NAMES)}\n\n"
        msg += "\n".join(results)
        msg += "\n\nОткройте окно рынка в игре для корректного теста."
        
        QMessageBox.information(self, "Результат тестирования", msg)
    
    def _reload_templates(self):
        """Перезагрузка шаблонов."""
        from core.template_matcher import get_template_matcher
        
        matcher = get_template_matcher()
        matcher._templates.clear()
        matcher._load_templates()
        
        QMessageBox.information(
            self, 
            "Готово", 
            f"Загружено {len(matcher._templates)} шаблонов"
        )

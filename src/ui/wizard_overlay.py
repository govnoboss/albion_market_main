from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication, QMainWindow, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRect, QPoint
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QPixmap

from ..core.coordinate_capture import get_capture_manager
from ..utils.paths import get_app_root
from ..utils.logger import get_logger
from .dim_overlay import DimOverlay
from .resizable_panel import ResizablePanel

class WizardOverlay(QWidget):
    """
    Полноэкранный оверлей для мастера настройки.
    Основная логика затемнения вынесена в DimOverlay.
    Этот класс управляет UI элементами.
    """
    wizard_finished = pyqtSignal(bool)
    
    def __init__(self, categories: dict):
        super().__init__()
        self.categories = categories
        self.steps = self._flatten_steps(categories)
        self.current_step_index = 0
        self.points = {} # Initialize points dictionary
        
        # Dimming flags (managed in DimOverlay)
        self.dim_enabled = True 
        self.dim_right_enabled = True 
        self._success = False 

        self.capture_manager = get_capture_manager()
        self.logger = get_logger()
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool 
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Explicitly set full screen geometry
        screen_geometry = QApplication.primaryScreen().geometry()
        self.setGeometry(screen_geometry)

        # Initialize Dim Overlay
        self.dim_overlay = DimOverlay()
        self.dim_overlay.setGeometry(screen_geometry)
        self.dim_overlay.show()
        
        self._setup_ui()
        self._connect_signals()
        
        # Таймер для запуска первого шага с небольшой задержкой
        QTimer.singleShot(500, self._next_step)

    def keyPressEvent(self, event):
        """Обработка нажатий клавиш (ESC для выхода)"""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        super().keyPressEvent(event)

    def closeEvent(self, event):
        """Обработка закрытия окна (ESC или программно)"""
        # Close Dim Overlay
        if hasattr(self, 'dim_overlay'):
            self.dim_overlay.close()

        # Останавливаем любые действия
        if hasattr(self, 'capture_manager') and self.capture_manager.is_capturing:
            self.capture_manager.cancel_capture()

        # Испускаем сигнал завершения
        # В coordinates_tab это вызовет восстановление главного окна
        self.wizard_finished.emit(self._success) 
        super().closeEvent(event)

    def _flatten_steps(self, categories):
        """Преобразует словарь категорий в плоский список шагов с сохранением группировки по разделам"""
        flat_steps = []
        
        # Порядок категорий
        cat_order = ["Основное меню рынка", "Окно меню предмета", "Black Market"]
        
        # Добавляем известные категории в нужном порядке
        for cat_name in cat_order:
            if cat_name in categories:
                items = categories[cat_name]
                for i, (key, name, mode) in enumerate(items):
                    flat_steps.append({
                        "category": cat_name,
                        "key": key,
                        "name": name,
                        "mode": mode,
                        "local_index": i + 1, 
                        "total_in_cat": len(items)
                    })
                    
        # Если есть какие-то другие категории
        for cat_name, items in categories.items():
            if cat_name not in cat_order:
                for i, (key, name, mode) in enumerate(items):
                    flat_steps.append({
                        "category": cat_name,
                        "key": key,
                        "name": name,
                        "mode": mode,
                        "local_index": i + 1,
                        "total_in_cat": len(items)
                    })
                    
        return flat_steps

    def _setup_ui(self):
        # Основной layout (прозрачный, чтобы растянуть элементы)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0) # No margins for full screen
        
        # --- MOVABLE INFO PANEL ---
        # Instead of adding directly to layout, we add a ResizablePanel to the widget
        # Since self is a Window, we can just parent ResizablePanel to self and move it.
        
        self.info_panel_container = ResizablePanel(self)
        self.info_panel_container.resize(600, 500) # Initial size
        self.info_panel_container.move(20, 20) # Initial pos

        # Inner Widget for styling
        self.info_content = QWidget()
        self.info_content.setStyleSheet("""
            QWidget {
                background-color: rgba(13, 17, 23, 0.95);
                border: 2px solid #58a6ff;
                border-radius: 10px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)
        
        self.info_layout = QVBoxLayout(self.info_content)
        
        # Заголовок панели
        panel_title = QLabel("Справка (Можно двигать)")
        panel_title.setStyleSheet("color: #8b949e; font-size: 14px; font-weight: bold;")
        self.info_layout.addWidget(panel_title)

        # Счетчик
        self.counter_label = QLabel(f"Шаг 0 / 0")
        self.counter_label.setStyleSheet("color: #58a6ff; font-size: 16px;")
        self.info_layout.addWidget(self.counter_label)
        
        # Картинка подсказки
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(300) 
        # Allow image to shrink/grow
        self.image_label.setScaledContents(True) 
        self.info_layout.addWidget(self.image_label)
        
        # Кнопка пропуска
        self.skip_label = QLabel("ESC - Отмена")
        self.skip_label.setStyleSheet("color: #8b949e; font-size: 12px; margin-top: 10px;")
        self.skip_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.info_layout.addWidget(self.skip_label)

        # Add content to container
        self.info_panel_container.addWidget(self.info_content)
        
        # --- ЦЕНТРАЛЬНАЯ НАДПИСЬ (ПОВЕРХ ВСЕГО) ---
        self.center_widget = QWidget(self)
        self.center_widget.setStyleSheet("background: transparent;")
        self.center_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents) 
        
        center_layout = QVBoxLayout(self.center_widget)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.step_label = QLabel("КЛИКНИТЕ СЮДА")
        self.step_label.setStyleSheet("""
            color: #ff4444;  /* RED TEXT */
            font-size: 42px; 
            font-weight: bold; 
            background-color: rgba(0,0,0,0.7);
            padding: 20px;
            border-radius: 20px;
        """)
        self.step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.instruction_label = QLabel("Инструкция")
        self.instruction_label.setStyleSheet("""
            color: white; 
            font-size: 24px; 
            font-weight: bold;
            background-color: rgba(0,0,0,0.5);
            padding: 10px;
            border-radius: 10px;
        """)
        self.instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        center_layout.addWidget(self.step_label)
        center_layout.addWidget(self.instruction_label)
        
        self.center_widget.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        # Sync DimOverlay size
        if hasattr(self, 'dim_overlay'):
             self.dim_overlay.resize(self.size())

        # Центрируем виджет с текстом, но СВЕРХУ (Top Center)
        if hasattr(self, 'center_widget'):
            cw = 1000 
            ch = 200 
            self.center_widget.setGeometry(
                (self.width() - cw) // 2,
                20, 
                cw, ch
            )
            self.center_widget.show()

    def _connect_signals(self):
        self.capture_manager.coordinate_captured.connect(self._on_captured)
        self.capture_manager.area_captured.connect(self._on_area_captured)
        self.capture_manager.capture_cancelled.connect(self._on_cancelled)

    def _next_step(self):
        if self.current_step_index >= len(self.steps):
             self._finish_wizard()
             return
            
        step = self.steps[self.current_step_index]
        self.current_step = step
        
        # --- DYNAMIC DIMMING LOGIC ---
        dim_enabled = True
        dim_right_enabled = True
        
        if step['category'] == "Black Market":
            # В разделе Black Market убираем затемнение справа для шагов из меню (1-6)
            if step['local_index'] < 7:
                dim_right_enabled = False
            
            # Навигация (Выход -> Вход -> ...)
            nav_keys = ["bm_sell_tab", "bm_settings_btn", "bm_logout_btn", "bm_login_btn", "bm_char1_area", "bm_char2_area"]
            
            if step['key'] in nav_keys:
                dim_enabled = False
        
        # Update DimOverlay
        self.dim_overlay.set_dim_state(dim_enabled, dim_right_enabled)
        
        # Обновляем UI с учетом номера шага внутри категории
        step_text = f"Шаг {step['local_index']}: {step['name']}"
        self.step_label.setText(step_text)
        
        instruction_text = (
            "Наведите курсор и нажмите 'F1' (если точка)\nили Выделите область (если OCR)"
        )
        if step['mode'] == 'point':
            instruction_text = "🎯 Наведите курсор на центр элемента и нажмите 'F1'"
        elif step['mode'] == 'area':
            instruction_text = "📐 Выделите прямоугольную область с зажатой ЛКМ"
        
        # Особый текст для Шага 7 (Список Тиров) в BM
        if step['category'] == "Black Market" and step['local_index'] == 7:
             instruction_text = "👋 Входим в игру...\n\n👉 ОТКРОЙТЕ РЫНОК ДЛЯ ПРОДОЛЖЕНИЯ"
             
        self.instruction_label.setText(instruction_text)
        
        # Обновляем счетчик
        self.counter_label.setText(f"Раздел: {step['category']} | Шаг {step['local_index']} из {step['total_in_cat']}")
        
        self._load_help_image(step['category'])

        # --- AUTO CLICK BUTTON ---
        # Если перешли к разделу "Окно меню предмета" (первый шаг - item_expand), 
        # нужно кликнуть "Купить" (buy_button), чтобы открыть это меню.
        if step['category'] == "Окно меню предмета" and step['local_index'] == 1:
            if "buy_button" in self.points:
                self._auto_click_point(self.points["buy_button"], "Открытие меню предмета...")
                # Даем время на открытие меню, задержка перед захватом
                QTimer.singleShot(800, lambda: self.capture_manager.start_capture(
                    step['key'], step['name'], step['mode']
                ))
                return 

        # Если перешли к "Black Market" (первый шаг), 
        # нужно кликнуть "Крестик" (menu_close), чтобы закрыть меню предмета.
        if step['category'] == "Black Market" and step['local_index'] == 1:
            if "menu_close" in self.points:
                self._auto_click_point(self.points["menu_close"], "Закрытие меню предмета...")
                QTimer.singleShot(800, lambda: self.capture_manager.start_capture(
                    step['key'], step['name'], step['mode']
                ))
                return
        
        QTimer.singleShot(100, lambda: self.capture_manager.start_capture(
            step['key'], step['name'], step['mode']
        ))

    def _load_help_image(self, category_name):
        help_dir = get_app_root() / "resources" / "help"
        
        # Determine image name based on category and step index
        image_name = category_name # Default
        
        step_idx = self.current_step['local_index']
        
        if category_name == "Окно меню предмета":
            if step_idx == 1:
                image_name = "Раскрытие меню предмета"
            else:
                image_name = "Окно меню предмета"
                
        elif category_name == "Black Market":
            if step_idx == 1:
                image_name = "Вкладка продать"
            elif 2 <= step_idx <= 3:
                image_name = "Настройки"
            elif 4 <= step_idx <= 6:
                 image_name = "Аватарки"
            elif step_idx >= 7:
                 image_name = "Тиры"

        image_path = help_dir / f"{image_name}.png"
        
        self.logger.debug(f"Wizard: Loading help image '{image_name}' for step {step_idx}")

        if image_path.exists():
            pixmap = QPixmap(str(image_path))
            self.image_label.setPixmap(pixmap)
            self.image_label.show()
        else:
            self.image_label.hide()
            self.image_label.setPixmap(QPixmap()) 
            
    def _on_captured(self, key, x, y):
        self.points[key] = (x, y)
        if self.current_step['key'] != key: return
        self.logger.info(f"[Wizard] Captured Point {key}: {x}, {y}")
        
        if key == "search_input":
             self._auto_type_alebarda(x, y)
             return 
             
        if key == "tier_dropdown":
            self._prompt_dropdown_calibration()
            return
            
        if key == "bm_logout_btn":
            self._perform_auto_logout(x, y)
            return

        self._advance_step_delayed()

    logout_performed = pyqtSignal() # Signal for thread synchronization

    def _perform_auto_logout(self, logout_x, logout_y):
        """Автоматический клик Настройки -> Выход и таймер 10 сек"""
        settings_pos = self.points.get("bm_settings_btn")
        if not settings_pos:
            self.logger.error("Wizard: Settings button pos not found for auto-logout")
            self._advance_step_delayed()
            return

        self.instruction_label.setText("⏳ Выполняется авто-выход...")
        
        # Connect signal securely
        try:
            self.logout_performed.disconnect()
        except:
            pass
        self.logout_performed.connect(self._start_logout_timer)
        
        QApplication.processEvents()
        
        def _run_logout_sequence():
            import time
            from pynput.mouse import Button, Controller as MouseController
            mouse_c = MouseController()
            
            try:
                # 1. Click Settings
                mouse_c.position = settings_pos
                time.sleep(0.5)
                mouse_c.click(Button.left)
                time.sleep(1.0) # Wait for menu
                
                # 2. Click Logout
                mouse_c.position = (logout_x, logout_y)
                time.sleep(0.5)
                mouse_c.click(Button.left)
                
                # Signal that logout is clicked
                self.logout_performed.emit()
                
            except Exception as e:
                self.logger.error(f"Auto-Logout Error: {e}")

        from threading import Thread
        t = Thread(target=_run_logout_sequence)
        t.start()
        
    def _start_logout_timer(self):
        """Запуск таймера после клика"""
        # Start Countdown Timer on UI thread
        self._logout_timer_left = 10
        self.instruction_label.setText(f"⏳ Ожидание выхода: {self._logout_timer_left} сек...")
        
        self._logout_timer = QTimer(self)
        self._logout_timer.timeout.connect(self._update_logout_timer)
        self._logout_timer.start(1000)

    def _update_logout_timer(self):
        self._logout_timer_left -= 1
        self.instruction_label.setText(f"⏳ Ожидание выхода: {self._logout_timer_left} сек...")
        
        if self._logout_timer_left <= 0:
            self._logout_timer.stop()
            self._logout_timer.deleteLater()
            self._advance_step_delayed()

    def _perform_auto_login(self):
        """Авто клик по кнопке Войти"""
        login_pos = self.points.get("bm_login_btn")
        if not login_pos:
             self.logger.error("Wizard: Login button pos not found")
             self._advance_step_delayed()
             return

        self.instruction_label.setText("🤖 Вход в игру...")
        QApplication.processEvents()
        
        def _run_login():
            import time
            from pynput.mouse import Button, Controller as MouseController
            mouse_c = MouseController()
            try:
                 mouse_c.position = login_pos
                 time.sleep(0.5)
                 mouse_c.click(Button.left)
                 time.sleep(0.5)
            except Exception as e:
                 pass
                 
        from threading import Thread
        t = Thread(target=_run_login)
        t.start()
        
        # Proceed immediately (or with small delay) to next step, 
        # where we will ask user to open market
        QTimer.singleShot(1000, self._advance_step_delayed)

    def _auto_click_point(self, pos, msg):
        x, y = pos
        self.instruction_label.setText(f"🤖 {msg}")
        QApplication.processEvents()
        
        def _run_click():
            import time
            try:
                from pynput.mouse import Button, Controller as MouseController
                mouse_c = MouseController()
                mouse_c.position = (x, y)
                time.sleep(0.1)
                mouse_c.click(Button.left)
                time.sleep(0.1)
            except Exception as e:
                self.logger.error(f"Auto-Click Error: {e}")

        from threading import Thread
        t = Thread(target=_run_click)
        t.start()

    def _on_area_captured(self, key, x, y, w, h):
        if self.current_step['key'] != key: return
        self.logger.info(f"[Wizard] Captured Area {key}")
        
        if key == "market_name_area":
            self.instruction_label.setText("🕵️ Проверка рынка (OCR)...")
            QApplication.processEvents()
            
            from ..utils.ocr import read_screen_text
            text = read_screen_text(x, y, w, h, lang='rus+eng')
            text_lower = text.lower()
            
            if "black" in text_lower or "черны" in text_lower or "ёрны" in text_lower:
                 self.logger.warning(f"Wizard: Detected Black Market ({text})!")
                 self.instruction_label.setText("⛔ ОБНАРУЖЕН ЧЕРНЫЙ РЫНОК!")
                 self.step_label.setText("ОШИБКА")
                 
                 msg = QMessageBox(self)
                 msg.setWindowTitle("Ошибка настройки")
                 msg.setText("Настройка должна проводиться в ОБЫЧНОМ (Королевском) городе!\n\nПожалуйста, переместитесь в другой город и попробуйте снова.")
                 msg.setIcon(QMessageBox.Icon.Critical)
                 msg.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint) 
                 msg.exec()
                 
                 self.close() 
                 return

        if key == "bm_char2_area":
             self._perform_auto_login()
             return

        self._advance_step_delayed()

    def paintEvent(self, event):
        """Рисование точек калибровки"""
        if getattr(self, '_calibration_active', False):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Блокировка ввода (рисуем почти прозрачный фон)
            painter.setBrush(QColor(0, 0, 0, 1))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(self.rect())
            
            # Настройки пера для точек
            pen = QPen(QColor(255, 0, 0), 2)
            painter.setPen(pen)
            painter.setBrush(QColor(255, 0, 0))
            
            x, y = self._calibration_start_pos
            offset = self._calibration_params['offset']
            height = self._calibration_params['height']
            
            # Рисуем 9 точек (как запрошено)
            for i in range(9):
                # Координата Y: точка клика + смещение + (индекс * высота)
                dot_y = y + offset + (i * height)
                painter.drawEllipse(QPoint(x, int(dot_y)), 4, 4)

    def wheelEvent(self, event):
        """Блокировка колеса мыши при калибровке"""
        if getattr(self, '_calibration_active', False):
            event.accept()
        else:
            super().wheelEvent(event)

    def _prompt_dropdown_calibration(self):
        """Диалог калибровки выпадающего списка"""
        # 1. Авто-клик для раскрытия списка
        dropdown_pos = self.points.get("tier_dropdown")
        if dropdown_pos:
            from pynput.mouse import Button, Controller
            import time
            mouse = Controller()
            mouse.position = dropdown_pos
            time.sleep(0.1)
            mouse.click(Button.left)
            time.sleep(0.2) # Ждем анимации раскрытия
        else:
            dropdown_pos = (0, 0) # Fallback

        # 2. Инициализация переменных для отрисовки
        self._calibration_active = True
        self._calibration_start_pos = dropdown_pos
        
        from PyQt6.QtWidgets import QDialog, QFormLayout, QSpinBox, QDialogButtonBox
        from ..utils.config import get_config
        config = get_config()
        
        current_height = config.get_dropdown_setting("row_height", 28)
        current_offset = config.get_dropdown_setting("list_start_offset", 30)
        
        self._calibration_params = {
            'height': int(current_height),
            'offset': int(current_offset)
        }
        
        # Обновляем отрисовку сразу
        self.update()
        
        dialog = QDialog(self)
        dialog.setWindowTitle("📏 Калибровка Списка")
        dialog.setStyleSheet("""
            QDialog {
                background-color: #0d1117;
                color: #c9d1d9;
                border: 2px solid #58a6ff;
                border-radius: 8px;
            }
            QLabel { color: #c9d1d9; font-size: 14px; }
            QSpinBox {
                background-color: #0d1117;
                color: #58a6ff;
                border: 1px solid #30363d;
                padding: 5px;
                font-size: 14px;
                min-width: 80px; 
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 25px;
                background-color: #21262d;
                border-left: 1px solid #30363d;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #30363d;
            }
        """)
        dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        
        layout = QVBoxLayout(dialog)
        
        info = QLabel("Отрегулируйте параметры так, чтобы красные точки попадали в центры строк списка:")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        form = QFormLayout()
        
        sb_height = QSpinBox()
        sb_height.setRange(10, 100)
        sb_height.setValue(int(current_height))
        form.addRow("Высота строки (px):", sb_height)
        
        sb_offset = QSpinBox()
        sb_offset.setRange(0, 100)
        sb_offset.setValue(int(current_offset))
        form.addRow("Смещение начала (px):", sb_offset)
        
        # Live Update
        def update_params():
            self._calibration_params['height'] = sb_height.value()
            self._calibration_params['offset'] = sb_offset.value()
            self.update() # Перерисовка оверлея
            
        sb_height.valueChanged.connect(update_params)
        sb_offset.valueChanged.connect(update_params)
        
        layout.addLayout(form)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dialog.accept)
        buttons.setStyleSheet("QPushButton { background-color: #238636; color: white; border-radius: 4px; padding: 6px; }")
        layout.addWidget(buttons)
        
        # Центрируем диалог (сдвигаем, чтобы не закрывал список)
        dialog.resize(350, 220)
        screen_geo = self.geometry()
        # Сдвигаем вправо от центра, чтобы видеть список слева (обычно список под курсором)
        dialog.move(
            screen_geo.x() + (screen_geo.width() // 2) + 100,
            screen_geo.y() + (screen_geo.height() - 200) // 2
        )
        
        if dialog.exec():
            # Сохраняем
            config.set_dropdown_setting("row_height", sb_height.value())
            config.set_dropdown_setting("list_start_offset", sb_offset.value())
            self.instruction_label.setText("✅ Параметры сохранены!")
            QApplication.processEvents()
            
        # Выключаем режим калибровки
        self._calibration_active = False
        self.update()
            
        self._advance_step_delayed()

    def _advance_step_delayed(self):
        self.current_step_index += 1
        
        # Fix UI Glitch: Ensure geometry is correct before next step
        # Force update geometry in case of resolution change or interaction
        self.setGeometry(QApplication.primaryScreen().geometry())
        if hasattr(self, 'dim_overlay'):
             self.dim_overlay.setGeometry(self.geometry())
             
        QTimer.singleShot(300, self._next_step)

    def _auto_type_alebarda(self, x, y):
        self.instruction_label.setText("🤖 Авто-настройка: Ввод 'Алебарда'...")
        QApplication.processEvents()
        
        def _run_typing():
            import time 
            try:
                from pynput.mouse import Button, Controller as MouseController
                from pynput.keyboard import Key, Controller as KeyboardController
                
                mouse_c = MouseController()
                kb_c = KeyboardController()
                
                mouse_c.position = (x, y)
                time.sleep(0.1)
                mouse_c.click(Button.left)
                time.sleep(0.2)
                
                with kb_c.pressed(Key.ctrl):
                    kb_c.press('a')
                    kb_c.release('a')
                time.sleep(0.1)
                kb_c.press(Key.backspace)
                kb_c.release(Key.backspace)
                time.sleep(0.1)
                
                for char in "Алебарда":
                     # Pynput might have issues with cyrillic depending on layout, 
                     # but assuming it works or system layout matches
                    kb_c.type(char)
                    time.sleep(0.05)
                
                time.sleep(0.2)
                kb_c.press(Key.enter)
                kb_c.release(Key.enter)
                time.sleep(0.5) 
                
            except Exception as e:
                self.logger.error(f"Automation Error: {e}")
            finally:
                QTimer.singleShot(100, self._advance_step_delayed)

        from threading import Thread
        t = Thread(target=_run_typing)
        t.start()

    def _finish_wizard(self):
        """Завершение мастера"""
        self.instruction_label.setText("✅ Настройка завершена!")
        self.step_label.setText("Готово")
        self.image_label.hide()
        
        self._success = True 
        QTimer.singleShot(1000, self.close)

    def _on_cancelled(self, key):
        self.close()

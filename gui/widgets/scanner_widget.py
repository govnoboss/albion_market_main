"""
Albion Market Bot v3.0 - Scanner Widget v2

Виджет для сканирования цен с поддержкой Tier/Enchant/Quality.
"""

from pathlib import Path
from typing import List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QProgressBar, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QSpinBox, QLineEdit, QComboBox, QMessageBox,
    QFileDialog, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from core.scanner_engine import ScannerConfig, ScanResult
from workers.scan_worker import ScanWorker


class ScannerWidget(QWidget):
    """
    Виджет сканера цен v2.
    
    Поддерживает:
    - Настройка диапазонов Tier/Enchant/Quality
    - Сканирование всех комбинаций
    - Таблица результатов с tier/enchant/quality
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ScannerConfig()
        self.worker: ScanWorker = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # === Настройки города ===
        city_group = QGroupBox("🏰 Город")
        city_layout = QHBoxLayout(city_group)
        
        city_layout.addWidget(QLabel("Город:"))
        self.city_combo = QComboBox()
        self.city_combo.addItems([
            "Lymhurst", "Bridgewatch", "Fort Sterling", 
            "Martlock", "Thetford", "Caerleon"
        ])
        city_layout.addWidget(self.city_combo)
        
        city_layout.addWidget(QLabel("Файл:"))
        self.items_file_input = QLineEdit("data/items_to_scan.json")
        city_layout.addWidget(self.items_file_input)
        
        browse_btn = QPushButton("📂")
        browse_btn.setFixedWidth(40)
        browse_btn.clicked.connect(self._browse_items_file)
        city_layout.addWidget(browse_btn)
        
        layout.addWidget(city_group)
        
        # === Тиры (чекбоксы) ===
        tier_group = QGroupBox("🎯 Какие тиры сканировать?")
        tier_layout = QHBoxLayout(tier_group)
        
        self.tier_checks = {}
        for tier in [4, 5, 6, 7, 8]:
            cb = QCheckBox(f"T{tier}")
            cb.setChecked(True)  # Все включены по умолчанию
            cb.stateChanged.connect(self._update_combo_count)
            self.tier_checks[tier] = cb
            tier_layout.addWidget(cb)
        
        layout.addWidget(tier_group)
        
        # === Энчанты (чекбоксы) ===
        enchant_group = QGroupBox("✨ Какие зачарования?")
        enchant_layout = QHBoxLayout(enchant_group)
        
        self.enchant_checks = {}
        enchant_names = {0: ".0 (нет)", 1: ".1", 2: ".2", 3: ".3", 4: ".4"}
        for ench in [0, 1, 2, 3, 4]:
            cb = QCheckBox(enchant_names[ench])
            cb.setChecked(ench == 0)  # Только .0 по умолчанию
            cb.stateChanged.connect(self._update_combo_count)
            self.enchant_checks[ench] = cb
            enchant_layout.addWidget(cb)
        
        layout.addWidget(enchant_group)
        
        # === Качества (чекбоксы) ===
        quality_group = QGroupBox("⭐ Какие качества?")
        quality_layout = QHBoxLayout(quality_group)
        
        self.quality_checks = {}
        quality_names = {0: "Обычное", 1: "Хорошее", 2: "Выдающ.", 3: "Превосх.", 4: "Шедевр"}
        for qual in [0, 1, 2, 3, 4]:
            cb = QCheckBox(quality_names[qual])
            cb.setChecked(qual == 0)  # Только обычное по умолчанию
            cb.stateChanged.connect(self._update_combo_count)
            self.quality_checks[qual] = cb
            quality_layout.addWidget(cb)
        
        layout.addWidget(quality_group)
        
        # === Подсказка о количестве ===
        combo_label = QLabel("")
        combo_label.setStyleSheet("color: #89b4fa; font-size: 10pt; font-weight: bold;")
        combo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(combo_label)
        self.combo_label = combo_label
        
        self._update_combo_count()
        
        # === Настройки dropdown ===
        dropdown_group = QGroupBox("📏 Отступы в dropdown меню")
        dropdown_layout = QGridLayout(dropdown_group)
        
        dropdown_layout.addWidget(QLabel("Высота элемента (px):"), 0, 0)
        self.item_height_spin = QSpinBox()
        self.item_height_spin.setRange(15, 50)
        self.item_height_spin.setValue(25)
        self.item_height_spin.setToolTip("Расстояние между элементами в выпадающем списке")
        dropdown_layout.addWidget(self.item_height_spin, 0, 1)
        
        dropdown_layout.addWidget(QLabel("Смещение до первого (px):"), 0, 2)
        self.first_item_offset_spin = QSpinBox()
        self.first_item_offset_spin.setRange(10, 60)
        self.first_item_offset_spin.setValue(30)
        self.first_item_offset_spin.setToolTip("Расстояние от кнопки dropdown до первого элемента")
        dropdown_layout.addWidget(self.first_item_offset_spin, 0, 3)
        
        hint_label = QLabel("💡 Если клик попадает мимо — увеличьте высоту элемента")
        hint_label.setStyleSheet("color: #a6adc8; font-size: 9pt;")
        dropdown_layout.addWidget(hint_label, 1, 0, 1, 4)
        
        layout.addWidget(dropdown_group)
        
        # === Управление ===
        control_group = QGroupBox("🎮 Управление")
        control_layout = QHBoxLayout(control_group)
        
        self.start_btn = QPushButton("▶️ Начать сканирование")
        self.start_btn.clicked.connect(self._start_scan)
        control_layout.addWidget(self.start_btn)
        
        self.pause_btn = QPushButton("⏸️ Пауза")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._toggle_pause)
        control_layout.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton("⏹️ Стоп")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_scan)
        control_layout.addWidget(self.stop_btn)
        
        layout.addWidget(control_group)
        
        # === Прогресс ===
        progress_group = QGroupBox("📊 Прогресс")
        progress_layout = QVBoxLayout(progress_group)
        
        self.status_label = QLabel("Готов к сканированию")
        progress_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.current_item_label = QLabel("")
        self.current_item_label.setStyleSheet("color: #a6adc8;")
        progress_layout.addWidget(self.current_item_label)
        
        layout.addWidget(progress_group)
        
        # === Результаты ===
        results_group = QGroupBox("📋 Результаты")
        results_layout = QVBoxLayout(results_group)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "Предмет", "Тир", "Энчант", "Качество", "Цена", "Статус"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.results_table.setAlternatingRowColors(True)
        results_layout.addWidget(self.results_table)
        
        export_btn = QPushButton("💾 Экспорт в CSV")
        export_btn.clicked.connect(self._export_results)
        results_layout.addWidget(export_btn)
        
        layout.addWidget(results_group)
    
    def _update_combo_count(self):
        """Обновление счётчика комбинаций."""
        tiers = sum(1 for cb in self.tier_checks.values() if cb.isChecked())
        enchants = sum(1 for cb in self.enchant_checks.values() if cb.isChecked())
        qualities = sum(1 for cb in self.quality_checks.values() if cb.isChecked())
        total = tiers * enchants * qualities
        
        if total == 0:
            self.combo_label.setText("⚠️ Выберите хотя бы один вариант в каждой категории")
            self.combo_label.setStyleSheet("color: #f38ba8; font-size: 10pt; font-weight: bold;")
        else:
            self.combo_label.setText(f"📊 {tiers} тиров × {enchants} энчантов × {qualities} качеств = {total} комбинаций на предмет")
            self.combo_label.setStyleSheet("color: #89b4fa; font-size: 10pt; font-weight: bold;")
    
    def _get_selected_values(self):
        """Получение выбранных значений из чекбоксов."""
        tiers = [t for t, cb in self.tier_checks.items() if cb.isChecked()]
        enchants = [e for e, cb in self.enchant_checks.items() if cb.isChecked()]
        qualities = [q for q, cb in self.quality_checks.items() if cb.isChecked()]
        return tiers, enchants, qualities
    
    def _browse_items_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Выбрать файл предметов",
            "data", "JSON Files (*.json)"
        )
        if filepath:
            self.items_file_input.setText(filepath)
    
    def _get_config(self) -> ScannerConfig:
        """Получение конфигурации из UI."""
        tiers, enchants, qualities = self._get_selected_values()
        
        config = ScannerConfig(
            items_file=Path(self.items_file_input.text()),
            current_city=self.city_combo.currentText(),
        )
        # Добавляем списки и настройки dropdown
        config.selected_tiers = tiers
        config.selected_enchants = enchants
        config.selected_qualities = qualities
        config.dropdown_item_height = self.item_height_spin.value()
        config.dropdown_first_offset = self.first_item_offset_spin.value()
        return config
    
    def _start_scan(self):
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Ошибка", "Сканирование уже запущено!")
            return
        
        config = self._get_config()
        
        # Проверка выбора
        if not config.selected_tiers or not config.selected_enchants or not config.selected_qualities:
            QMessageBox.warning(
                self, "Ошибка", 
                "Выберите хотя бы один вариант в каждой категории!\n"
                "(Тиры, Зачарования, Качества)"
            )
            return
        
        # Очистка результатов
        self.results_table.setRowCount(0)
        
        # Создание worker
        self.worker = ScanWorker(config)
        self.worker.progress.connect(self._on_progress)
        self.worker.status.connect(self._on_status)
        self.worker.result.connect(self._on_result)
        self.worker.finished_scan.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        
        # UI
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        
        self.worker.start()
    
    def _toggle_pause(self):
        if self.worker:
            if self.pause_btn.text() == "⏸️ Пауза":
                self.worker.pause()
                self.pause_btn.setText("▶️ Продолжить")
                self.status_label.setText("⏸️ Пауза")
            else:
                self.worker.resume()
                self.pause_btn.setText("⏸️ Пауза")
    
    def _stop_scan(self):
        if self.worker:
            self.worker.stop()
    
    def _on_progress(self, current: int, total: int, description: str):
        pct = int(current / total * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)
        self.current_item_label.setText(f"[{current}/{total}] {description}")
    
    def _on_status(self, message: str):
        self.status_label.setText(message)
    
    def _on_result(self, result: ScanResult):
        """Добавление результата в таблицу."""
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        # Данные
        self.results_table.setItem(row, 0, QTableWidgetItem(result.item_name))
        self.results_table.setItem(row, 1, QTableWidgetItem(f"T{result.tier}"))
        self.results_table.setItem(row, 2, QTableWidgetItem(f".{result.enchant}" if result.enchant else "-"))
        self.results_table.setItem(row, 3, QTableWidgetItem(str(result.quality) if result.quality else "-"))
        self.results_table.setItem(row, 4, QTableWidgetItem(f"{result.price:,}" if result.price else "-"))
        
        status_item = QTableWidgetItem("✅" if result.success else f"❌")
        if not result.success:
            status_item.setForeground(QColor("#f38ba8"))
        self.results_table.setItem(row, 5, status_item)
        
        self.results_table.scrollToBottom()
    
    def _on_finished(self, success: bool, message: str, filepath: str):
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setText("⏸️ Пауза")
        
        self.progress_bar.setValue(100 if success else 0)
        self.status_label.setText(message)
        
        if success and filepath:
            QMessageBox.information(
                self, "Готово",
                f"{message}\n\nРезультаты сохранены:\n{filepath}"
            )
    
    def _on_error(self, error: str):
        QMessageBox.critical(self, "Ошибка", error)
    
    def _export_results(self):
        if self.results_table.rowCount() == 0:
            QMessageBox.information(self, "Пусто", "Нет результатов для экспорта")
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Сохранить результаты",
            "scan_results.csv", "CSV Files (*.csv)"
        )
        
        if filepath:
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                f.write("Предмет,Тир,Энчант,Качество,Цена,Статус\n")
                for row in range(self.results_table.rowCount()):
                    cols = []
                    for col in range(self.results_table.columnCount()):
                        item = self.results_table.item(row, col)
                        cols.append(f'"{item.text()}"' if item else '""')
                    f.write(",".join(cols) + "\n")
            
            QMessageBox.information(self, "Готово", f"Сохранено: {filepath}")

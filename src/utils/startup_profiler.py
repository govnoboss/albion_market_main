"""
Профайлер запуска приложения.
Замеряет время каждого этапа загрузки и выводит структурированный отчёт.
"""

import time
import os
from datetime import datetime


class StartupProfiler:
    """
    Singleton-профайлер для измерения времени запуска.
    
    Использование:
        profiler = get_startup_profiler()
        profiler.start("phase_name")
        ...
        profiler.end("phase_name")
        profiler.report()  # Выводит итоговый отчёт
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._t0 = time.perf_counter()  # Абсолютный момент создания профайлера
        self._phases = {}        # name -> {"start": float, "end": float | None}
        self._phase_order = []   # Порядок создания фаз
        self._marks = []         # (label, timestamp_relative_ms)
        self._parent_map = {}    # child_name -> parent_name (для иерархии)
        self._active_stack = []  # Стек текущих активных фаз
    
    def start(self, name: str):
        """Начать замер фазы"""
        now = time.perf_counter()
        self._phases[name] = {"start": now, "end": None}
        
        # Определяем родителя — текущая активная фаза в стеке
        if self._active_stack:
            self._parent_map[name] = self._active_stack[-1]
        
        self._active_stack.append(name)
        
        if name not in self._phase_order:
            self._phase_order.append(name)
    
    def end(self, name: str):
        """Закончить замер фазы"""
        now = time.perf_counter()
        if name in self._phases and self._phases[name]["end"] is None:
            self._phases[name]["end"] = now
        
        # Убираем из стека
        if name in self._active_stack:
            self._active_stack.remove(name)
    
    def mark(self, label: str):
        """Одноразовая метка времени (checkpoint)"""
        elapsed = (time.perf_counter() - self._t0) * 1000
        self._marks.append((label, elapsed))
    
    def _get_duration_ms(self, name: str) -> float:
        """Получить длительность фазы в мс"""
        phase = self._phases.get(name)
        if not phase:
            return 0.0
        start = phase["start"]
        end = phase["end"] if phase["end"] is not None else time.perf_counter()
        return (end - start) * 1000
    
    def _get_children(self, parent_name: str) -> list:
        """Получить дочерние фазы в порядке создания"""
        children = []
        for name in self._phase_order:
            if self._parent_map.get(name) == parent_name:
                children.append(name)
        return children
    
    def _get_roots(self) -> list:
        """Получить корневые фазы (без родителя)"""
        roots = []
        for name in self._phase_order:
            if name not in self._parent_map:
                roots.append(name)
        return roots
    
    def _format_line(self, name: str, duration_ms: float, prefix: str, is_last: bool, width: int) -> str:
        """Форматировать строку отчёта"""
        if prefix == "":
            # Корневой элемент
            connector = ""
        else:
            connector = "└─ " if is_last else "├─ "
        
        label = f"{prefix}{connector}{name}"
        dots_count = max(1, width - len(label) - len(f"{duration_ms:.0f}ms") - 2)
        dots = "·" * dots_count
        
        # Цветовая маркировка по времени
        if duration_ms > 2000:
            marker = "🔴"
        elif duration_ms > 500:
            marker = "🟡"
        else:
            marker = "🟢"
        
        return f"║ {label} {dots} {duration_ms:.0f}ms {marker}"
    
    def _build_tree_lines(self, name: str, prefix: str, is_last: bool, width: int) -> list:
        """Рекурсивная сборка строк дерева"""
        lines = []
        duration = self._get_duration_ms(name)
        lines.append(self._format_line(name, duration, prefix, is_last, width))
        
        children = self._get_children(name)
        if children:
            for i, child in enumerate(children):
                child_is_last = (i == len(children) - 1)
                if prefix == "":
                    child_prefix = "  "
                else:
                    child_prefix = prefix + ("   " if is_last else "│  ")
                lines.extend(self._build_tree_lines(child, child_prefix, child_is_last, width))
        
        return lines
    
    def report(self) -> str:
        """
        Вывести итоговый отчёт.
        Возвращает строку отчёта.
        """
        width = 52
        border = "═" * width
        
        lines = []
        lines.append(f"╔{border}╗")
        lines.append(f"║{'⏱ STARTUP PROFILING REPORT':^{width}}║")
        lines.append(f"╠{border}╣")
        
        # Дерево фаз
        roots = self._get_roots()
        for i, root in enumerate(roots):
            tree_lines = self._build_tree_lines(root, "", i == len(roots) - 1, width)
            for line in tree_lines:
                # Выравниваем правый край
                padding = width + 2 - self._visible_len(line)
                lines.append(f"{line}{' ' * max(0, padding)}║")
        
        # Метки-чекпоинты
        if self._marks:
            lines.append(f"╠{border}╣")
            lines.append(f"║{'CHECKPOINTS':^{width}}║")
            for label, ts_ms in self._marks:
                mark_line = f"║  ⚑ {label} @ {ts_ms:.0f}ms"
                padding = width + 2 - self._visible_len(mark_line)
                lines.append(f"{mark_line}{' ' * max(0, padding)}║")
        
        lines.append(f"╚{border}╝")
        
        report_text = "\n".join(lines)
        
        # Вывод в консоль
        print("\n" + report_text + "\n")
        
        # Запись в файл
        self._save_to_file(report_text)
        
        return report_text
    
    def _visible_len(self, s: str) -> int:
        """Длина строки без учёта emoji (приблизительно)"""
        # Emoji занимают ~2 символа ширины, но для простоты считаем 1
        return len(s)
    
    def _save_to_file(self, report_text: str):
        """Сохранить отчёт в debug_startup.log"""
        try:
            # Определяем путь относительно корня проекта
            from .paths import get_app_root
            log_path = get_app_root() / "debug_startup.log"
        except Exception:
            log_path = "debug_startup.log"
        
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n--- SESSION START {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                f.write(report_text + "\n")
        except Exception:
            pass  # Не критично


# Глобальный экземпляр
_profiler = None


def get_startup_profiler() -> StartupProfiler:
    """Получить глобальный экземпляр профайлера"""
    global _profiler
    if _profiler is None:
        _profiler = StartupProfiler()
    return _profiler

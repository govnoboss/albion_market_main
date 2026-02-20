# Отчет по дизайну интерфейса (Dashboard V2)

На основе анализа предоставленного скриншота Smugden Dashboard, ниже приведен детальный разбор визуальных элементов и техническая схема реализации аналогичного интерфейса в нашем приложении на PyQt6.

## 1. Визуальная иерархия и структура

Интерфейс строится по принципу **"Dashboard-first"**, где пользователю сразу видны ключевые метрики, а детальное управление скрыто во вкладках.

### Основные слои:
- **Вертикальный Сайдбар (Navigation):** Тёмный фон, акцент на иконки, индикатор активной вкладки (вертикальная полоса).
- **Сетка карточек (KPI Cards):** Верхний ряд с ключевыми цифрами (Revenue, Profit и др.). Каждая карта имеет иконку и вторичный текст.
- **Инфографика и таблицы (Data):** Центральная часть с таблицей сделок и правая панель с "Топ" списками.
- **Верхний бар (Title bar):** Брендинг слева, системные иконки справа.

## 2. Сводная цветовая палитра (QSS)

| Элемент | Цвет (Hex) | Назначение |
| :--- | :--- | :--- |
| **Background Main** | `#1b1b2f` | Основной фон контента |
| **Background Card/Sidebar** | `#242442` | Карточки и боковая панель |
| **Text Primary** | `#ffffff` | Заголовки, главные цифры |
| **Text Secondary** | `#8b949e` | Описания, подписи |
| **Accent Positive** | `#4caf50` | Профит, Live статус |
| **Accent Gold** | `#fdd835` | Revenue, иконки наград |
| **Border Active** | `#e91e63` | Полоса активного раздела (розовый/пурпурный) |

## 3. Схема компонентов (Mermaid)

```mermaid
graph TD
    Main[MainWindow] --> TopBar[Top Bar: Logo + App Actions]
    Main --> Layout[Horizontal Layout]
    
    Layout --> Sidebar[Sidebar: Nav Buttons + Active Indicator]
    Layout --> Content[Main Content: QStackedWidget]
    
    Content --> DashboardPage[Dashboard Page]
    DashboardPage --> KPIRow[KPI Row: Revenue | Profit | Items | Margin]
    DashboardPage --> FilterRow[Filter Row: Location Dropdown | Period Dropdown]
    DashboardPage --> LogRow[Horizontal Layout]
    
    LogRow --> TransactionTable[Transaction Table: Date | Item | Profit]
    LogRow --> SummaryPanel[Summary Panel: Top Traded | Top City | Best Item]
```

## 4. План реализации в коде

### A. Виджет KPI Карточки
Создание класса `KPICard(QFrame)`:
```python
def __init__(self, icon, title, value, subtext):
    # Layout: Icon (Left) + VBox (Right: Title, Value, Subtext)
    # Styling: Скругленные углы (12px), фон darker than main, border 1px solid
```

### B. Репорлинг Сайдбара
- Добавление `activeIndicator = QFrame` (ширина 4px) слева от кнопки.
- Использование SVG иконок вместо текста или юникода для "премиального" вида.

### C. Стилизация Таблиц (QTableWidget)
- Удаление границ между ячейками.
- Кастомный `QHeaderView` с тёмным фоном.
- Цветовая маркировка строк (например, положительный профит — зелёный текст).

### D. Summary блоки (Правая панель)
- Цветные границы слева (`border-left: 4px solid #color`).
- Иерархические списки (1. Item, 2. Item) с выраженным отступом.

## 5. Следующие шаги для реализации
1. Обновить `src/ui/styles.py` новыми цветовыми токенами.
2. Создать `src/ui/components/kpi_card.py` для переиспользуемых метрик.
3. Прописать QSS для `SummaryBox` с динамическим цветом границы.
4. Переверстать `DashboardWidget` (текущий заглушка) в структурированную сетку.

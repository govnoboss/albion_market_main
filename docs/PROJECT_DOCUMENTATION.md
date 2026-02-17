# Project Documentation: Albion Market Scanner & Buyer

## 1. Project Overview

**Applies to:** `albion_market_main`
**Type:** Automation Tool (Market Bot) for Albion Online
**Tech Stack:** Python 3.14, PyQt6 (GUI), PyAutoGUI/Pynput (Input), OpenCV/Tesseract (OCR).

### Core Purpose
A desktop application that automates market data collection (Scanner) and item purchasing (Buyer) in the Albion Online MMORPG. It uses Optical Character Recognition (OCR) and template matching to read the game state and emulates human input (mouse/keyboard) to interact with the game UI.

### Key Features
*   **Scanner:** Automatically iterates through items, tiers, and enchants to record market prices. Supports **Black Market** specific logic (character switching).
*   **Buyer (Wholesale):** Purchases specific items up to a configured limit with loop-based buying and budget tracking.
*   **Buyer (Smart):** Automatically identifies and purchases profitable items based on the spread between any two cities (configurable buy/sell city arbitrage).
*   **Multi-City Arbitrage:** Динамический выбор города покупки и продажи (не только Black Market).
*   **Mini Overlay:** A compact, always-on-top interface for monitoring bot status without blocking the game view.
*   **Auto-Recovery:** Автоматическое восстановление при вылетах, дисконнектах и закрытии рынка.
*   **License System:** HWID-based licensing system to restrict usage. RSA-signed server responses.
*   **Auto-Update:** Проверка и скачивание новых версий через GitHub Releases с автоматической установкой.

---

## 2. Architecture & Directory Structure

The project follows a layered architecture: **Launcher** → **Logic** (`core`) → **Interface** (`ui`) → **Helpers** (`utils`).

```text
src/
├── main.py                 # Точка входа (создаёт LauncherWindow)
├── core/                   # Business Logic & Bot Engines
│   ├── base_bot.py         # Base thread, input emulation, common checks, kick recovery
│   ├── bot.py              # Scanner Mode logic (incl. Black Market)
│   ├── buyer.py            # Buyer Mode logic (Wholesale/Smart, multi-city)
│   ├── coordinate_capture.py # Захват координат по клику (pynput)
│   ├── interaction.py      # UI Element calculation (Dropdowns)
│   ├── license.py          # HWID generation, RSA verification, license validation
│   ├── market_opener.py    # Поиск и открытие NPC Рынка через OCR тултипов
│   ├── state_detector.py   # Обнаружение вылетов, дисконнектов, экрана переподключения
│   ├── updater.py          # Auto-Update: проверка/скачивание/установка через GitHub Releases
│   ├── validator.py        # Screen state validation (OCR/Visual)
│   └── version.py          # Single source of truth: CURRENT_VERSION, APP_NAME, GITHUB_REPO
├── ui/                     # PyQt6 Interface
│   ├── launcher.py         # ★ ENTRY POINT: Launcher window, режим выбора, auto-update banner
│   ├── login_window.py     # Окно ввода лицензионного ключа
│   ├── splash_screen.py    # Splash screen при загрузке
│   ├── main_window.py      # Scanner Window: Tabs, Hotkeys (F5/F6)
│   ├── buyer_window.py     # Buyer Window: управление закупкой
│   ├── buyer/              # Компоненты Buyer-окна
│   │   ├── profit_preview_tab.py   # Превью прибыли
│   │   └── purchase_plan_tab.py    # План закупок
│   ├── mini_overlay.py     # Compact status overlay (Always on Top)
│   ├── log_overlay.py      # Оверлей логов
│   ├── overlay.py          # (Legacy) HUD components
│   ├── calibration_overlay.py # Оверлей калибровки координат
│   ├── styles.py           # Стили и цветовая схема (MAIN_STYLE, COLORS)
│   └── [tabs]              # Вкладки Scanner Window:
│       ├── control_panel.py       # Start/Stop controls
│       ├── profits_tab.py         # Smart Buyer analysis view
│       ├── prices_tab.py          # Database viewer
│       ├── items_panel.py         # Item management
│       ├── coordinates_tab.py     # UI calibration
│       └── settings_panel.py      # General config
├── utils/                  # Shared Utilities
│   ├── config.py           # JSON Config Manager (Singleton)
│   ├── logger.py           # Thread-safe logging system
│   ├── price_storage.py    # Price database (JSON)
│   ├── image_utils.py      # Image comparison & search
│   ├── ocr.py              # Tesseract/Image-processing wrappers
│   ├── paths.py            # Определение путей приложения (get_app_root)
│   ├── human_mouse.py      # Человекоподобное движение мыши (кривые Безье)
│   ├── items_db.py         # База данных предметов
│   ├── default_exceptions.py # Исключения по тирам (items без T1-T3)
│   └── text_utils.py       # Утилиты обработки текста
├── legacy/                 # Устаревший код
│   └── debug_overlay.py    # Legacy debug overlay
server/                     # License Server (FastAPI) — ОБЯЗАТЕЛЕН для работы бота
tools/                      # Утилиты разработчика
│   ├── release_manager.py  # GUI для сборки, упаковки и публикации релизов
│   ├── ocr_tester.py       # GUI для тестирования OCR фильтров с превью и пресетами
│   ├── generate_keys.py    # Генерация RSA ключей
│   ├── migrate_db.py       # Миграция БД сервера
│   ├── migrate_db_ip.py    # Миграция БД (IP поля)
│   └── deploy_server.ps1   # Деплой сервера на Fly.io
```

---

## 3. Application Flow

```text
main.py → LauncherWindow
             ├── [Нет лицензии] → LoginWindow → (ввод ключа) → LauncherWindow
             ├── [Лицензия ОК] → Splash Screen → LauncherWindow
             │                     ├── Фоновая проверка обновлений (GitHub API)
             │                     │    └── [Есть обновление] → Баннер "🔄 Обновить"
             │                     ├── Кнопка "СКАНЕР"  → MainWindow (Scanner)
             │                     └── Кнопка "ЗАКУПЩИК" → BuyerWindow (Buyer)
```

---

## 4. Core Components ("The Brain")

### BaseBot (`src/core/base_bot.py`)
*   **Role:** Abstract parent class (QThread).
*   **Responsibilities:**
    *   Thread management (`start`, `stop`, `pause`).
    *   **Human-like Input:** `_human_move_to` (Bezier curves), `_human_click`, `_human_type` (pynput).
    *   **Market Validation:** Checks if the Market or Item Menu is open (`_check_market_is_open`, `_detect_current_city`).
    *   **Kick Recovery:** `_detect_and_handle_kicks` — полный цикл восстановления при дисконнекте (OCR-детекция → нажатие OK → переподключение → вход → повторное открытие рынка через `MarketOpener`).
    *   **Item Name Verification:** `_verify_item_name_with_retry` — OCR-верификация имени предмета с нормализацией текста и SequenceMatcher (порог 90%).
    *   **Pause Logic:** Handles graceful pausing via `_check_pause`.

### MarketBot (Scanner) (`src/core/bot.py`)
*   **Role:** Iterates through items to collect price data.
*   **Key Logic:**
    *   **Loop:** Iterates items -> Tiers (4-8) -> Enchants (0-4).
    *   **Safety:** Uses `_capture_item_menu_state` & `_check_safe_state` to ensuring valid context. Implements **Auto-Recovery** if the menu closes unexpectedly.
    *   **Black Market:** Handles inventory limits (Item 48 trigger) by executing a character switch sequence.
    *   **Opportunistic Capture:** If a price for another tier/enchant is visible while working on the current one, it captures it to save time.

### BuyerBot (Buyer) (`src/core/buyer.py`)
*   **Role:** Executes buy orders based on logic.
*   **Multi-City:** Динамический выбор `buy_city` и `sell_city` — поддержка произвольных маршрутов (не только Black Market).
*   **Modes:**
    1.  **Wholesale**: Buys items from a user-defined list up to a specific limit. Циклическая покупка всего лота.
    2.  **Smart**: Analyzes `PriceStorage`, finds items where `(SellCityPrice * 0.935) - MarketPrice` > `MinProfit`, and buys them.
*   **Key Logic:**
    *   **Target Price Calculation:** `Target = (SellCity_Price * 0.935) / (1 + MinProfitPercent / 100)`.
    *   **Loop-Based Buying:** `_process_variant` содержит цикл `while items_bought < limit` — покупает несколько лотов подряд до выполнения лимита.
    *   **Budget Tracking:** `max_budget` / `spent_amount` — отслеживание трат, автоматическая остановка при превышении бюджета.
    *   **Verification:** Reads the "Total Buy Order" price via OCR ensuring the total cost matches expected `Price * Qty` (5% buffer).
    *   **Input:** Uses keyboard input with mouse-hold logic for setting quantities.
    *   **Simulation Mode:** `simulation_mode = True` по умолчанию — безопасный режим без реальных покупок.
    *   **Sort Options:** Сортировка профитов по % или абсолютному серебру.

### Interaction (`src/core/interaction.py`)
*   **Role:** UI Coordinate Logic.
*   **DropdownSelector:** Calculates `(x, y)` for dynamic dropdowns (Tier, Enchant, Quality) handling specific offsets and row heights.
*   **Tier Exceptions:** database of items that don't have specific tiers (e.g., T1 for some artifacts), adjusting dropdown clicks accordingly.

### CoordinateCapture (`src/core/coordinate_capture.py`)
*   **Role:** Глобальный захват координат по клику мыши.
*   **Логика:** Использует `pynput` для прослушивания кликов, поддерживает захват точки и области.
*   **Singleton:** Глобальный экземпляр через `get_capture_manager()`.

### StateDetector (`src/core/state_detector.py`)
*   **Role:** Обнаружение специфических состояний игры (вылеты, ошибки).
*   **Methods:**
    *   `is_disconnected()` — OCR-детекция окна ошибки подключения (popup с кнопкой OK).
    *   `is_reconnect_screen()` — детекция экрана «Информация» с кнопкой «Переподключение».
    *   `is_main_menu()` — проверка главного меню через Template Matching аватаров персонажей.
    *   `find_ok_button_coords()` / `find_reconnect_button_coords()` — расчёт координат кнопок относительно экрана.
*   **Resolution-Independent:** Работает на любом разрешении, используя процентные отступы от центра экрана.

### MarketOpener (`src/core/market_opener.py`)
*   **Role:** Систематический поиск и открытие NPC Рынка на экране.
*   **Logic:** Зигзагообразное сканирование экрана (шаг 350px по X, 10% по Y) с человекоподобным движением мыши. Детекция тултипа «Рынок» через OCR.
*   **Integration:** Используется в `BaseBot._detect_and_handle_kicks` для автоматического повторного открытия рынка после восстановления.

### LicenseManager (`src/core/license.py`)
*   **Role:** Security & Access Control.
*   **Logic:** Generates a stable HWID (Motherboard + CPU + MachineGUID), encrypts/decrypts keys locally, and validates against a remote server. Verifies RSA-signed responses.

---

## 5. Auto-Update System

### Компоненты
| Файл | Роль |
|:---|:---|
| `src/core/version.py` | Единственный источник версии: `CURRENT_VERSION`, `APP_NAME`, `GITHUB_REPO` |
| `src/core/updater.py` | Проверка, скачивание и установка обновлений |
| `tools/release_manager.py` | GUI-инструмент для публикации релизов |

### Как это работает
1.  При запуске `LauncherWindow` вызывает `UpdateCheckWorker` (QThread).
2.  Воркер делает `GET` к GitHub API: `/repos/{GITHUB_REPO}/releases/latest`.
3.  Парсит `tag_name` (например `v1.2.0`) и сравнивает с `CURRENT_VERSION` как кортеж `(1, 2, 0)`.
4.  Если `latest > current` — в UI появляется баннер с кнопкой **"🔄 Обновить"**.
5.  По нажатию — `UpdateDownloadWorker` скачивает ZIP с прогресс-баром.
6.  `install_update()` распаковывает ZIP, генерирует `update.bat`, запускает его и завершает приложение.
7.  `update.bat`: ждёт завершения GBot.exe → копирует файлы (кроме `config/`, `data/`, `logs/`) → перезапускает.

### Release Manager (`tools/release_manager.py`)
GUI-приложение (PyQt6) для разработчика:
1.  Обновляет `CURRENT_VERSION` в `version.py`.
2.  Запускает `build.bat` (Nuitka сборка).
3.  Упаковывает в `GBot.zip` через `package.bat`.
4.  Публикует GitHub Release с тегом `vX.Y.Z` и приложенным ZIP.

---

## 6. UI Architecture

### LauncherWindow (`src/ui/launcher.py`) — ★ Entry Point
*   **Features:**
    *   Splash Screen при загрузке.
    *   Проверка лицензии (silent → LoginWindow если нет ключа).
    *   Выбор режима: **Сканер** или **Закупщик**.
    *   Фоновая проверка обновлений с баннером.
    *   Отображение срока лицензии в footer.
    *   Ежедневная ре-валидация лицензии с graceful shutdown.

### MainWindow / Scanner Window (`src/ui/main_window.py`)
*   **Features:**
    *   **Tabs:** Control, Profits, Prices, Items, Coordinates, Settings.
    *   **Hotkeys:** Global `F5` (Start/Stop) and `F6` (Pause) using `pynput` listener.
    *   **Mini Overlay Integration:** Automatically hides the main window and shows `MiniOverlay` on start.

### BuyerWindow (`src/ui/buyer_window.py`)
*   **Role:** Отдельное окно для режима закупки.
*   **Features:**
    *   Управление Wholesale/Smart buyer, прогресс, логи.
    *   **Multi-City:** Дропдауны «Откуда» (`buy_city_combo`) и «Куда» (`sell_city_combo`) для выбора маршрута.
    *   **Budget Input:** Поле бюджета с placeholder «Безлимит» (кастомный `BudgetSpinBox`).
    *   **Always on Top:** Чекбокс для закрепления окна поверх всех.
    *   **Mini Overlay:** Интеграция с компактным оверлеем при запуске бота.
    *   **Auto-Refresh:** Списки городов и План закупки обновляются автоматически при каждом показе окна (`showEvent`).
    *   Вложенные табы: `buyer/profit_preview_tab.py` и `buyer/purchase_plan_tab.py`.

### MiniOverlay (`src/ui/mini_overlay.py`)
*   **Role:** Compact widget showing Status, Progress Bar, and Last Log Message.
*   **Behavior:** "Always on Top", draggable. Allows controlling the bot (Pause/Stop) without alt-tabbing.

### Tabs
*   **ProfitsTab:** Displays calculated profit margins based on scanned data.
*   **CoordinatesTab:** Interactive calibration tool. Allows users to "Set" coordinates by pressing Ctrl, auto-saving to config.
*   **PricesTab:** View and query the history of scanned prices.

---

## 7. Data Flow & Configuration

### ConfigManager (`src/utils/config.py`)
*   **File:** `config/coordinates.json`.
*   **Profiles:** Supports multiple coordinate profiles (e.g., for different screen resolutions or window positions).
*   **Capabilities:** Load/Save coordinates, Settings (`tesseract_path`), Dropdown tweaks, and Item Lists.

### PriceStorage (`src/utils/price_storage.py`)
*   **File:** `data/prices.json` (JSON Database).
*   **Structure:** `{ City: { ItemName: { "T4.0": { "price": 100, "updated": ISO_TIMESTAMP } } } }`.
*   **Features:** History cleaning (removing old sessions), City management.

### OCR Pipeline
1.  **Capture:** `ImageGrab` captures a defined area.
2.  **Pre-process:** Grayscale/Thresholding (`image_utils`).
3.  **Read:** `pytesseract` converts to text.
4.  **Validate:** `Validator` checks expected text (e.g., "Market Marketplace").

---

## 8. License Server

The project includes a standalone **License Server** (FastAPI) to manage access control via HWID locking. **Сервер обязателен** — без него бот не запустится.

*   **Documentation:** [LICENSE_SERVER.md](LICENSE_SERVER.md)
*   **Source Code:** `server/` directory.
*   **Features:** HWID Validation, RSA Response Signing, Admin Panel, REST API.

---

## 9. How AI Agents Should Use This Document

*   **Refactoring:**
    *   `base_bot.py` is the foundation. Changes here affect BOTH Scanner and Buyer.
    *   UI changes should be modular (create new Tab classes).
    *   `launcher.py` is the actual entry point — NOT `main_window.py`.
*   **New Features:**
    *   **Logic:** Add to `src/core/` (inherit BaseBot).
    *   **UI:** Add to `src/ui/` and register in the appropriate Window.
*   **Version & Updates:**
    *   Version is defined ONLY in `src/core/version.py`.
    *   To release: use `tools/release_manager.py` (GUI) or manually update version → build → package → GitHub Release.
*   **Critical Constraints:**
    *   **Coordinates:** The bot is blind without accurate coordinates. Any UI change in the Game requires recalibration.
    *   **OCR Reliability:** Always verify OCR output (`isdigit()`, `>0`) before critical actions (Buying).
    *   **Safety:** The `_check_safe_state()` in `bot.py` is the primary crash-prevention mechanism. Do not remove it.

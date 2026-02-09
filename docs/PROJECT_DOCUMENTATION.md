# Project Documentation: Albion Market Scanner & Buyer

## 1. Project Overview

**Applies to:** `albion_market_main`
**Type:** Automation Tool (Market Bot) for Albion Online
**Tech Stack:** Python 3.x, PyQt6 (GUI), PyAutoGUI/Pynput (Input), OpenCV/Tesseract (OCR).

### Core Purpose
A desktop application that automates market data collection (Scanner) and item purchasing (Buyer) in the Albion Online MMORPG. It uses Optical Character Recognition (OCR) and template matching to read the game state and emulates human input (mouse/keyboard) to interact with the game UI.

### Key Features
*   **Scanner:** Automatically iterates through items, tiers, and enchants to record market prices. Supports **Black Market** specific logic (character switching).
*   **Buyer (Wholesale):** Purchases specific items up to a configured limit.
*   **Buyer (Smart):** Automatically identifies and purchases profitable items based on the spread between City Market and Black Market prices.
*   **Mini Overlay:** A compact, always-on-top interface for monitoring bot status without blocking the game view.
*   **License System:** HWID-based licensing system to restrict usage.

---

## 2. Architecture & Directory Structure

The project follows a layered architecture separating Logic (`core`), Interface (`ui`), and Helpers (`utils`).

```text
src/
├── core/               # Business Logic & Bot Engines
│   ├── base_bot.py     # Base thread, input emulation, common checks
│   ├── bot.py          # Scanner Mode logic (incl. Black Market)
│   ├── buyer.py        # Buyer Mode logic (Wholesale/Smart)
│   ├── interaction.py  # UI Element calculation (Dropdowns)
│   ├── license.py      # HWID generation and license validation
│   └── validator.py    # Screen state validation (OCR/Visual)
├── ui/                 # PyQt6 Interface
│   ├── main_window.py  # Entry point, Tab management, Hotkeys
│   ├── mini_overlay.py # Compact status overlay
│   ├── overlay.py      # (Legacy) HUD components
│   └── [tabs]          # Specific tab implementations:
│       ├── control_panel.py   # Start/Stop controls
│       ├── profits_tab.py     # Smart Buyer analysis view
│       ├── prices_tab.py      # Database viewer
│       ├── items_panel.py     # Item management
│       ├── coordinates_tab.py # UI calibration
│       └── settings_panel.py  # General config
├── utils/              # Shared Utilities
│   ├── config.py       # JSON Config Manager (Singleton)
│   ├── logger.py       # Thread-safe logging system
│   ├── price_storage.py# Price database (JSON)
│   ├── image_utils.py  # Image comparison & search
│   └── ocr.py          # Tesseract/Image-processing wrappers
├── server/             # (Optional) Web Server for License/Distribution
└── main.py             # Application Entry Point
```

---

## 3. Core Components ("The Brain")

### BaseBot (`src/core/base_bot.py`)
*   **Role:** Abstract parent class (QThread).
*   **Responsibilities:**
    *   Thread management (`start`, `stop`, `pause`).
    *   **Human-like Input:** `_human_move_to` (with randomization), `_human_click`, `_human_type`.
    *   **Market Validation:** Checks if the Market or Item Menu is open (`_check_market_is_open`, `_detect_current_city`).
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
*   **Modes:**
    1.  **Wholesale**: Buys items from a user-defined list up to a specific limit.
    2.  **Smart**: Analyzes `PriceStorage`, finds items where `(BlackMarketPrice * 0.935) - MarketPrice` > `MinProfit`, and buys them.
*   **Key Logic:**
    *   **Target Price Calculation:** `Target = (BM_Price * 0.935) / (1.025 * Margin)`.
    *   **Verification:** Reads the "Total Buy Order" price via OCR ensuring the total cost matches expected `Price * Qty`.
    *   **Input:** Uses keyboard input with mouse-hold logic for setting quantities.

### Interaction (`src/core/interaction.py`)
*   **Role:** UI Coordinate Logic.
*   **DropdownSelector:** Calculates `(x, y)` for dynamic dropdowns (Tier, Enchant, Quality) handling specific offsets and row heights.
*   **Tier Exceptions:** database of items that don't have specific tiers (e.g., T1 for some artifacts), adjusting dropdown clicks accordingly.

### LicenseManager (`src/core/license.py`)
*   **Role:** Security & Access Control.
*   **Logic:** Generates a stable HWID (Motherboard + CPU + MachineGUID), encrypts/decrypts keys locally, and validates against a remote server.

---

## 4. UI Architecture

### MainWindow (`src/ui/main_window.py`)
*   **Features:**
    *   **Tabs:** Control, Profits, Prices, Items, Coordinates, Settings.
    *   **Hotkeys:** Global `F5` (Start/Stop) and `F6` (Pause) using `pynput` listener.
    *   **Mini Overlay Integration:** Automatically hides the main window and shows `MiniOverlay` on start.

### MiniOverlay (`src/ui/mini_overlay.py`)
*   **Role:** Compact widget showing Status, Progress Bar, and Last Log Message.
*   **Behavior:** "Always on Top", draggable. Allows controlling the bot (Pause/Stop) without alt-tabbing.

### Tabs
*   **ProfitsTab:** Displays calculated profit margins based on scanned data.
*   **CoordinatesTab:** Interactive calibration tool. Allows users to "Set" coordinates by pressing Ctrl, auto-saving to config.
*   **PricesTab:** View and query the history of scanned prices.

---

## 5. Data Flow & Configuration

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

## 6. License Server

The project includes a standalone **License Server** (FastAPI) to manage access control via HWID locking.

*   **Documentation:** [LICENSE_SERVER.md](LICENSE_SERVER.md)
*   **Source Code:** `server/` directory.
*   **Features:** HWID Validation, Admin Panel, REST API.

---

## 7. How AI Agents Should Use This Document

*   **Refactoring:**
    *   `base_bot.py` is the foundation. Changes here affect BOTH Scanner and Buyer.
    *   UI changes should be modular (create new Tab classes).
*   **New Features:**
    *   **Logic:** Add to `src/core/` (inherit BaseBot).
    *   **UI:** Add to `src/ui/` and register in `MainWindow`.
*   **Critical Constraints:**
    *   **Coordinates:** The bot is blind without accurate coordinates. Any UI change in the Game requires recalibration.
    *   **OCR Reliability:** Always verify OCR output (`isdigit()`, `>0`) before critical actions (Buying).
    *   **Safety:** The `_check_safe_state()` in `bot.py` is the primary crash-prevention mechanism. Do not remove it.

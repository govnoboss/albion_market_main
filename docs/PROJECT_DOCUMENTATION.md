# Project Documentation: Albion Market Scanner & Buyer

## 1. Project Overview

**Applies to:** `albion_market_main`
**Type:** Automation Tool (Market Bot) for Albion Online
**Tech Stack:** Python 3.x, PyQt6 (GUI), PyAutoGUI/Pynput (Input), OpenCV/Tesseract (OCR).

### Core Purpose
A desktop application that automates market data collection (Scanner) and item purchasing (Buyer) in the Albion Online MMORPG. It uses Optical Character Recognition (OCR) and template matching to read the game state and emulates human input (mouse/keyboard) to interact with the game UI.

### High-Level Workflow
1.  **Configuration**: User sets coordinates for UI elements and defines items/filters via the GUI.
2.  **Scanning**: Bot iterates through items, changing Tiers/Enchants/Qualities, reads prices via OCR, and saves them to a local database/cache.
3.  **Buying**: Bot monitors prices (or uses scan data) to purchase items that meet profit criteria (Smart Mode) or specific quantity limits (Wholesale Mode).

---

## 2. Architecture & Directory Structure

The project follows a layered architecture separating Logic (`core`), Interface (`ui`), and Helpers (`utils`).

```text
src/
├── core/               # Business Logic & Bot Engines
│   ├── base_bot.py     # Base thread, input emulation, common checks
│   ├── bot.py          # Scanner Mode logic
│   ├── buyer.py        # Buyer Mode logic (Wholesale/Smart)
│   ├── interaction.py  # UI Element calculation (Dropdowns)
│   └── validator.py    # Screen state validation (OCR/Visual)
├── ui/                 # PyQt6 Interface
│   ├── main_window.py  # Entry point, Tab management, Hotkeys
│   ├── overlay.py      # HUD components
│   └── ...tabs         # Specific tab implementations
├── utils/              # Shared Utilities
│   ├── config.py       # JSON Config Manager (Singleton)
│   ├── logger.py       # Thread-safe logging system
│   ├── image_utils.py  # Image comparison & search
│   └── ocr.py          # Tesseract/Image-processing wrappers
└── main.py             # Application Entry Point
```

### Dependency Rules
*   **UI** depends on **Core** (to start/stop bots) and **Utils** (config/logging).
*   **Core** depends on **Utils** (config, logger, ocr) but **NOT** on UI (signals are used).
*   **Utils** should be independent.

---

## 3. Core Components ("The Brain")

### BaseBot (`src/core/base_bot.py`)
*   **Role:** Abstract parent class (QTread).
*   **Responsibilities:**
    *   Thread management (`start`, `stop`, `pause`).
    *   Human-like Input (`_human_move_to`, `_human_click`, `_human_type`).
    *   Market Validation (`_check_market_is_open`, `_detect_current_city`).
    *   Logging actions.

### MarketBot (`src/core/bot.py`)
*   **Role:** The Scanner. Iterates through items to collect price data.
*   **Key Logic:**
    *   **Iteration:** Loops through a list of items (`config.known_items`).
    *   **Variations:** For each item, iterates active Tiers (4-8) and Enchants (0-4).
    *   **Character Switch:** Specific logic for "Black Market" to switch characters when inventory is full (Item 48 trigger).
    *   **Collision/Opportunistic:** Captures prices for other tiers if visible on screen to speed up scanning.
*   **Safety:** Uses `_capture_item_menu_state` & `_check_safe_state` to ensure the bot is looking at the correct item menu. Re-opens it if lost.

### BuyerBot (`src/core/buyer.py`)
*   **Role:** The Purchaser. Executes buy orders based on logic.
*   **Modes:**
    1.  **Wholesale**: Buying specific items up to a configured limit.
    2.  **Smart**: Buying items based on calculated profitability (Market vs Black Market diff).
*   **Key Logic (`_process_variant_wholesale`):**
    *   Reads current price (OCR).
    *   Calculates target price: `Target = (BM_Price * 0.935) / (1.025 * Margin)`.
    *   Verifies total cost before clicking confirm to prevent OCR errors.
    *   Batched buying (Quantity input).

### Interaction (`src/core/interaction.py`)
*   **Role:** Calculates coordinates for dynamic UI elements.
*   **Components:**
    *   `DropdownSelector`: Calculates `(x, y)` for dropdown items based on `row_height` and `offset`.
    *   **Tier Exceptions**: Handles UI quirks where "Tier 1" items offset the dropdown list (e.g. T2 starts at index 1 instead of 0).

---

## 4. UI Architecture

### MainWindow (`src/ui/main_window.py`)
*   **Initialization:** Sets up specific tabs (`Control`, `Profits`, `Prices`, `Items`, `Coordinates`, `Settings`).
*   **Hotkeys:** Global `F5` (Start/Stop) and `F6` (Pause) via `pynput`.
*   **Mini Overaly:** Automatically switches to a compact `MiniOverlay` when the bot starts.

### Event Flow
1.  **Start:** User clicks "Start" or presses F5 -> `MainWindow._on_start_bot` -> `Bot.start()`.
2.  **Progress:** `Bot.progress_updated` (Signal) -> `MainWindow` -> `ControlPanel/Overlay`.
3.  **Logs:** `Logger` emits signal -> `LogViewer` (TextEdit) appends HTML formatted text.

---

## 5. Data Flow & Configuration

### Configuration (`config/coordinates.json`)
Managed by `src/utils/config.py` (Singleton `get_config()`).
*   **Coordinates:** `{ "key": {"x": 100, "y": 200, "type": "point"} }`
*   **Items/Targets:** `{ "wholesale_targets": { "Sword": { "T4.0": { "limit": 10 ... } } } }`
*   **Persisted:** Auto-saves on change. Supports "Profiles" to swap coordinate sets.

### OCR Pipeline
1.  **Capture:** `ImageGrab` captures a region defined in config (`price_area`).
2.  **Pre-process:** Grayscale/Thresholding (`image_utils`).
3.  **Read:** `pytesseract` converts image to text/numbers.
4.  **Validation:** `Validator.check_market_open` verifies context (Header text).
5.  **Logic:** Bot decides to Buy/Skip based on the integer value.

### Logging
Managed by `src/utils/logger.py`.
*   **Dual Output:** Console (Standard `logging`) + GUI (Qt Signal).
*   **Levels:** INFO (User actions), DEBUG (Tech details), WARNING (Retries), ERROR (Failures).

---

## 6. Key Data Structures

### Item Verification
*   **Logic:** `_verify_item_name_with_retry` (Bot).
*   **Mechanism:** SequenceMatcher ratio > 0.90 between Config Name and OCR Name.

### Validation Schemas (Implicit)
*   **Coordinates:** Must have `x`, `y`. Optional: `w`, `h` (for areas).
*   **Price Storage:** `{ City: { ItemName: { "T4.0": { price: 100, updated: timestamp } } } }`

---

## 7. Invariants & Constraints
1.  **Input Exclusivity:** Bot assumes it controls the mouse. User interference pauses or breaks the loop (Anti-AFK logic not fully detailed, relies on `check_pause`).
2.  **OCR Dependency:** Cannot work if game language differs from OCR expectations (Rus/Eng supported).
3.  **Resolution:** Coordinates are absolute. Changing window size/position breaks the config (Requires Recalibration).
4.  **Menu State:** Both Bots heavily rely on the "Left-side list, Right-side details" layout of the Albion Market UI.

## 8. How AI Agents Should Use This Document
*   **Refactoring:** `base_bot.py` is the safest place for shared input/logic improvements.
*   **New Features:**
    *   To add a new Mode: Inherit `BaseBot` in `core/`, add Tab in `ui/`.
    *   To improve OCR: Modify `utils/ocr.py`, do not change usage in `bot.py` without verifying return types (int vs str).
*   **Warning:** `src/core/bot.py` contains complex state machines (Recovery/Switching). Modify with extreme caution and always preserve `_check_safe_state()` calls.

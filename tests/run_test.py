import sys
import os
import requests
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

def run_health_check():
    print("="*50)
    print("🔍 GBot System Health Check")
    print("="*50)

    # 1. Check Imports & Dependencies
    print("\n[1/4] Checking dependencies...")
    try:
        from PyQt6.QtWidgets import QApplication
        import cv2
        import numpy as np
        import pytesseract
        print("✅ Core libraries (PyQt6, OpenCV, Tesseract-lib) are ready.")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return

    # 2. Check Tesseract OCR
    print("\n[2/4] Checking Tesseract OCR...")
    try:
        from src.utils.ocr import init_ocr, is_ocr_available
        if init_ocr():
            print("✅ Tesseract OCR found and initialized.")
        else:
            print("⚠️ Tesseract OCR NOT FOUND! Recognition will not work.")
    except Exception as e:
        print(f"❌ OCR Error: {e}")

    # 3. Check Server Connection
    print("\n[3/4] Checking License Server...")
    from src.core.license import SERVER_URL
    try:
        resp = requests.get(f"{SERVER_URL}/validate", timeout=5)
        # We expect 405 or 422 because we don't send POST data, but 200/404 is fine as "connected"
        if resp.status_code < 500:
            print(f"✅ Server is alive at {SERVER_URL}")
        else:
            print(f"❌ Server returned error {resp.status_code}")
    except Exception as e:
        print(f"❌ Server connection failed: {e}")

    # 4. Check App Integrity
    print("\n[4/4] Checking Project Structure...")
    critical_paths = [
        "src/main.py",
        "resources/ref_market_menu_check.png",
        "assets/tesseract/tesseract.exe"
    ]
    all_ok = True
    for p in critical_paths:
        if (BASE_DIR / p).exists():
            print(f"✅ Found: {p}")
        else:
            print(f"❌ MISSING: {p}")
            all_ok = False

    print("\n" + "="*50)
    if all_ok:
        print("🚀 ALL SYSTEMS GO! You are ready to run the bot.")
    else:
        print("⚠️ Some issues were found. Please check the logs above.")
    print("="*50)

if __name__ == "__main__":
    run_health_check()

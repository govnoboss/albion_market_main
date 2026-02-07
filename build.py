"""
GBot Build Script - Nuitka Compilation
Run: python build.py
"""

import subprocess
import sys
import os
from pathlib import Path

# Configuration
APP_NAME = "GBot"
VERSION = "1.0.0"
MAIN_FILE = "src/main.py"
ICON_FILE = None  # Set to "assets/icon.ico" if you have one

# Output directory
OUTPUT_DIR = Path("dist")
OUTPUT_DIR.mkdir(exist_ok=True)

def build():
    print(f"🔨 Building {APP_NAME} v{VERSION}...")
    print("=" * 50)
    
    # Nuitka command
    cmd = [
        sys.executable, "-m", "nuitka",
        
        # Basic options
        "--standalone",              # Create standalone exe
        "--onefile",                 # Single file output
        "--windows-console-mode=disable",  # No console window (GUI app)
        
        # Output
        f"--output-dir={OUTPUT_DIR}",
        f"--output-filename={APP_NAME}.exe",
        
        # Include data files
        "--include-data-dir=src/ui=src/ui",           # UI files
        "--include-data-dir=assets/tesseract=tesseract",  # Tesseract OCR
        "--include-data-dir=resources=resources",     # Resources (templates, etc.)
        
        # PyQt6 plugin
        "--enable-plugin=pyqt6",
        
        # Performance
        "--jobs=4",                  # Parallel compilation
        
        # Windows specific
        "--windows-icon-from-ico=assets/icon.ico" if ICON_FILE and os.path.exists(ICON_FILE) else "",
        
        # Company info (optional)
        f"--product-name={APP_NAME}",
        f"--product-version={VERSION}",
        f"--file-description={APP_NAME} - Albion Market Bot",
        "--copyright=2026",
        
        # Main file
        MAIN_FILE,
    ]
    
    # Remove empty strings
    cmd = [c for c in cmd if c]
    
    print("Command:", " ".join(cmd))
    print("=" * 50)
    print()
    
    # Run Nuitka
    result = subprocess.run(cmd, cwd=os.getcwd())
    
    if result.returncode == 0:
        exe_path = OUTPUT_DIR / f"{APP_NAME}.exe"
        print()
        print("=" * 50)
        print(f"✅ Build successful!")
        print(f"📁 Output: {exe_path.absolute()}")
        print(f"📊 Size: {exe_path.stat().st_size / 1024 / 1024:.1f} MB" if exe_path.exists() else "")
    else:
        print()
        print("❌ Build failed!")
        sys.exit(1)

if __name__ == "__main__":
    build()

"""
Script to convert assets/icon.png to assets/icon.ico for Windows build.
Requires Pillow (pip install Pillow).
"""

import os
import sys
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
ICON_PNG = ASSETS_DIR / "icon.png"
ICON_ICO = ASSETS_DIR / "icon.ico"

def convert_icon():
    """Convert PNG to ICO if source exists."""
    print(f"Checking for icon at: {ICON_PNG}")
    
    if not ICON_PNG.exists():
        print("⚠️  Warning: assets/icon.png not found. skipping icon conversion.")
        return

    try:
        img = Image.open(ICON_PNG)
        # Convert to RGBA if not already (to preserve transparency)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
            
        print(f"Converting {ICON_PNG} -> {ICON_ICO}...")
        # Save as ICO with multiple sizes for best scaling in Windows
        img.save(ICON_ICO, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
        print(f"✅ Icon created successfully: {ICON_ICO}")
        
    except Exception as e:
        print(f"❌ Error converting icon: {e}")
        sys.exit(1)

if __name__ == "__main__":
    convert_icon()

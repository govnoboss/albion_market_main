"""
GBot Build Script - Nuitka Compilation
Usage:
    python build.py dev      # Fast build for testing (folder output)
    python build.py release  # Full build for distribution (single .exe)
"""

import subprocess
import sys
import os
from pathlib import Path

# ============== CONFIGURATION ==============
APP_NAME = "GBot"
VERSION = "1.0.0"
MAIN_FILE = "src/main.py"
ICON_FILE = "assets/icon.ico"
OUTPUT_DIR = Path("dist")

# Number of parallel jobs (auto-detect CPU cores)
JOBS = os.cpu_count() or 4
# ============================================

def get_mode():
    """Get build mode from command line"""
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode in ["dev", "release"]:
            return mode
    
    print("Usage: python build.py [dev|release]")
    print("  dev     - Fast build, folder output (3-5 min)")
    print("  release - Full build, single .exe (10-15 min)")
    sys.exit(1)

def build():
    mode = get_mode()
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    print(f"🔨 Building {APP_NAME} v{VERSION} [{mode.upper()}]")
    print("=" * 60)
    
    # Base command
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        f"--output-dir={OUTPUT_DIR}",
        f"--jobs={JOBS}",
        "--windows-console-mode=disable",
        
        # PyQt6 support
        "--enable-plugin=pyqt6",
        
        # Include data files
        "--include-data-dir=assets/tesseract=tesseract",
        "--include-data-dir=resources=resources",
        
        # Exclude unused modules (faster compile, smaller size)
        "--nofollow-import-to=unittest",
        "--nofollow-import-to=pytest",
        "--nofollow-import-to=test",
        "--nofollow-import-to=tkinter",
        "--nofollow-import-to=doctest",
        "--nofollow-import-to=pdb",
        
        # Product info
        f"--product-name={APP_NAME}",
        f"--product-version={VERSION}",
        f"--file-description={APP_NAME} - Albion Market Bot",
        "--copyright=2026",
    ]
    
    # Mode-specific flags
    if mode == "dev":
        # DEV: Fast build, folder output
        cmd.extend([
            f"--output-filename={APP_NAME}_dev.exe",
            # No LTO for speed
        ])
        print("📦 Mode: DEV (standalone folder)")
        
    elif mode == "release":
        # RELEASE: Full optimizations, single file
        cmd.extend([
            "--onefile",
            f"--output-filename={APP_NAME}.exe",
            "--onefile-compression=zstd",
            "--lto=yes",
        ])
        print("📦 Mode: RELEASE (single .exe with LTO)")
    
    # Add icon if exists
    if ICON_FILE and os.path.exists(ICON_FILE):
        cmd.append(f"--windows-icon-from-ico={ICON_FILE}")
    
    # Main file
    cmd.append(MAIN_FILE)
    
    # Remove empty strings
    cmd = [c for c in cmd if c]
    
    print(f"⚙️  Jobs: {JOBS}")
    print("=" * 60)
    print()
    
    # Run Nuitka
    result = subprocess.run(cmd, cwd=os.getcwd())
    
    if result.returncode == 0:
        print()
        print("=" * 60)
        print(f"✅ Build successful!")
        
        if mode == "dev":
            exe_path = OUTPUT_DIR / "main.dist" / f"{APP_NAME}_dev.exe"
        else:
            exe_path = OUTPUT_DIR / f"{APP_NAME}.exe"
            
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / 1024 / 1024
            print(f"📁 Output: {exe_path.absolute()}")
            print(f"📊 Size: {size_mb:.1f} MB")
    else:
        print()
        print("❌ Build failed!")
        sys.exit(1)

if __name__ == "__main__":
    build()

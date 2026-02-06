@echo off
echo ===========================================
echo       GBOT COMPILATION SCRIPT
echo ===========================================

echo [1/4] Installing Compiler Tools (Nuitka)...
pip install nuitka zstandard

echo [2/4] Cleaning old builds...
rmdir /s /q dist
rmdir /s /q build

echo [3/4] Compiling GBot.exe...
echo This may take 5-10 minutes. Please wait...
echo.

python -m nuitka ^
    --standalone ^
    --onefile ^
    --windows-disable-console ^
    --enable-plugin=pyqt6 ^
    --include-package=src ^
    --include-data-dir=resources=resources ^
    --include-data-dir=config=config ^
    --include-data-dir=data=data ^
    --output-dir=dist ^
    --output-filename=GBot.exe ^
    --product-name="GBot" ^
    --file-version=1.0.0 ^
    src/main.py

echo.
if exist dist\GBot.exe (
    echo [4/4] SUCCESS! Check 'dist' folder for GBot.exe
    start dist
) else (
    echo [ERROR] Compilation failed. Check output above.
)


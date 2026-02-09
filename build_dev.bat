@echo off
setlocal

:: Define Tesseract Path
set "TESSERACT_PATH=C:\Program Files\Tesseract-OCR"

:: Check if Tesseract exists
if not exist "%TESSERACT_PATH%" (
    echo [ERROR] Tesseract not found at: %TESSERACT_PATH%
    echo Please install Tesseract-OCR or update the path in this script.
    pause
    exit /b 1
)

echo [BUILD] Starting DEV build (Fast, Standalone)...
echo [INFO] Tesseract Path: %TESSERACT_PATH%

:: Nuitka Build Command (DEV PROFILE)
:: --jobs: Use all CPU cores for C compilation
:: --lto=no: Disable LTO for speed
python -m nuitka ^
    --standalone ^
    --enable-console ^
    --plugin-enable=pyside6 ^
    --include-data-dir=assets=assets ^
    --include-data-dir="%TESSERACT_PATH%=tesseract" ^
    --output-dir=dist_dev ^
    --jobs=2 ^
    --lto=no ^
    --main=src/main.py

if %ERRORLEVEL% equ 0 (
    echo [SUCCESS] Build complete! Run dist_dev\main.dist\main.exe
) else (
    echo [FAILURE] Build failed.
)
pause

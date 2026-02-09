@echo off
setlocal

:: Define Tesseract Path
set "TESSERACT_PATH=C:\Program Files\Tesseract-OCR"

:: Check if Tesseract exists
if not exist "%TESSERACT_PATH%" (
    echo [ERROR] Tesseract not found at: %TESSERACT_PATH%
    pause
    exit /b 1
)

echo [BUILD] Starting RELEASE build (Slow, Onefile, Optimized)...
echo [INFO] This can take 5-10 minutes. Please wait...
echo [INFO] Using %NUMBER_OF_PROCESSORS% CPU cores.

:: Nuitka Build Command (RELEASE PROFILE)
:: --jobs: Use all CPU cores
python -m nuitka ^
    --onefile ^
    --windows-disable-console ^
    --lto=yes ^
    --plugin-enable=anti-bloat ^
    --plugin-enable=pyside6 ^
    --include-data-dir=assets=assets ^
    --include-data-dir="%TESSERACT_PATH%=tesseract" ^
    --output-filename=GBot.exe ^
    --output-dir=dist_release ^
    --noinclude-pytest-mode=nofollow ^
    --noinclude-unittest-mode=nofollow ^
    --jobs=%NUMBER_OF_PROCESSORS% ^
    --main=src/main.py

if %ERRORLEVEL% equ 0 (
    echo [SUCCESS] Build complete! File: dist_release\GBot.exe
) else (
    echo [FAILURE] Build failed.
)
pause

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
    --windows-uac-admin ^
    --plugin-enable=pyside6 ^
    --include-data-dir=assets=assets ^
    --include-data-dir="%TESSERACT_PATH%=tesseract" ^
    --output-dir=dist_dev ^
    --jobs=%NUMBER_OF_PROCESSORS% ^
    --report=compilation-report.xml ^
    --lto=no ^
    --nofollow-import-to=sqlalchemy.dialects.mysql ^
    --nofollow-import-to=sqlalchemy.dialects.postgresql ^
    --nofollow-import-to=sqlalchemy.dialects.oracle ^
    --nofollow-import-to=sqlalchemy.dialects.mssql ^
    --nofollow-import-to=fastapi ^
    --nofollow-import-to=uvicorn ^
    --nofollow-import-to=slowapi ^
    --nofollow-import-to=jinja2 ^
    --nofollow-import-to=multipart ^
    --main=src/main.py

if %ERRORLEVEL% equ 0 (
    echo [SUCCESS] Build complete! Run dist_dev\main.dist\main.exe
) else (
    echo [FAILURE] Build failed.
)
pause

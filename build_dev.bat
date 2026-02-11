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

:: Clean previous build
if exist dist_dev (
    echo [CLEAN] Removing old dist_dev...
    rd /s /q dist_dev
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
    --plugin-enable=anti-bloat ^
    --no-progress ^
    --plugin-enable=pyqt6 ^
    --include-data-dir=assets=assets ^
    --include-data-dir="%TESSERACT_PATH%=tesseract" ^
    --output-dir=dist_dev ^
    --product-version=1.0.0 ^
    --file-version=1.0.0 ^
    --nofollow-import-to=sqlalchemy ^
    --nofollow-import-to=fastapi ^
    --nofollow-import-to=uvicorn ^
    --nofollow-import-to=starlette ^
    --nofollow-import-to=slowapi ^
    --nofollow-import-to=jinja2 ^
    --nofollow-import-to=multipart ^
    --nofollow-import-to=pandas ^
    --nofollow-import-to=matplotlib ^
    --nofollow-import-to=scipy ^
    --nofollow-import-to=sklearn ^
    --nofollow-import-to=kivy ^
    --nofollow-import-to=openpyxl ^
    --nofollow-import-to=PIL._tkinter_finder ^
    --nofollow-import-to=tkinter ^
    --nofollow-import-to=email_validator ^
    --nofollow-import-to=dnspython ^
    --nofollow-import-to=httpcore ^
    --nofollow-import-to=httptools ^
    --nofollow-import-to=h11 ^
    --nofollow-import-to=annotated_types ^
    --nofollow-import-to=anyio ^
    --nofollow-import-to=sniffio ^
    --nofollow-import-to=trio ^
    --nofollow-import-to=outcome ^
    --nofollow-import-to=wsproto ^
    --nofollow-import-to=selenium ^
    --nofollow-import-to=zstandard ^
    --nofollow-import-to=lxml ^
    --nofollow-import-to=pygments ^
    --nofollow-import-to=ipython ^
    --nofollow-import-to=notebook ^
    --nofollow-import-to=jedi ^
    --nofollow-import-to=parso ^
    --nofollow-import-to=wcwidth ^
    --nofollow-import-to=prompt_toolkit ^
    --jobs=%NUMBER_OF_PROCESSORS% ^
    --report=compilation-report.xml ^
    --lto=no ^
    --main=src/main.py

if %ERRORLEVEL% equ 0 (
    echo [SUCCESS] Build complete! Run dist_dev\main.dist\main.exe
) else (
    echo [FAILURE] Build failed.
)
pause

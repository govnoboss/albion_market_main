@echo off
setlocal

:: Define Tesseract Path
:: Define Tesseract Path (Portable)
set "TESSERACT_PATH=assets\tesseract"

:: Check if Tesseract exists locally
if not exist "%TESSERACT_PATH%\tesseract.exe" (
    echo [ERROR] Portable Tesseract not found at: %TESSERACT_PATH%\tesseract.exe
    echo Please copy your Tesseract files to assets\tesseract
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

:: Nuitka Build Command (DEV PROFILE - DEBUGGING RELEASE)
:: --jobs: Use all CPU cores for C compilation
:: --lto=no: Disable LTO for speed
:: ONEFILE + CONSOLE: To see why release crashes
python -m nuitka ^
    --onefile ^
    --enable-console ^
    --windows-uac-admin ^
    --lto=no ^
    --plugin-enable=anti-bloat ^
    --plugin-enable=pyqt6 ^
    --include-data-dir=resources=resources ^
    --output-dir=dist_dev ^
    --product-version=1.0.0 ^
    --file-version=1.0.0 ^
    --python-flag=no_docstrings ^
    --remove-output ^
    --noinclude-dlls=opencv_videoio_ffmpeg* ^
    --nofollow-import-to=PyQt6.QtPdf ^
    --nofollow-import-to=PyQt6.QtSvg ^
    --nofollow-import-to=PyQt6.QtQuick ^
    --nofollow-import-to=PyQt6.QtQml ^
    --nofollow-import-to=PyQt6.QtMultimedia ^
    --nofollow-import-to=PyQt6.QtDesigner ^
    --nofollow-import-to=PyQt6.QtHelp ^
    --nofollow-import-to=PyQt6.QtSensors ^
    --nofollow-import-to=PyQt6.QtWebEngine ^
    --nofollow-import-to=PyQt6.QtWebEngineCore ^
    --nofollow-import-to=PyQt6.QtWebEngineWidgets ^
    --nofollow-import-to=sqlalchemy ^
    --nofollow-import-to=fastapi ^
    --nofollow-import-to=uvicorn ^
    --nofollow-import-to=starlette ^
    --nofollow-import-to=slowapi ^
    --nofollow-import-to=jinja2 ^
    --nofollow-import-to=multipart ^
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
    --main=src/main.py

if %ERRORLEVEL% equ 0 (
    echo [COPY] Copying Portable Tesseract to dist path...
    if not exist "dist_dev\tesseract" mkdir "dist_dev\tesseract"
    xcopy /E /I /Y "assets\tesseract" "dist_dev\tesseract"
    
    echo [SUCCESS] Build complete! Run dist_dev\main.exe
) else (
    echo [FAILURE] Build failed.
)
pause

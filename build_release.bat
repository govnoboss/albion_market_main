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
if exist dist_release (
    echo [CLEAN] Removing old dist_release...
    rd /s /q dist_release
)

echo [BUILD] Starting RELEASE build (Standalone, Optimized)...
echo [INFO] This can take 5-10 minutes. Please wait...
echo [INFO] Using %NUMBER_OF_PROCESSORS% CPU cores.

:: Nuitka Build Command (RELEASE PROFILE)
:: --jobs: Use all CPU cores
:: OPTIMIZED: LTO disabled for speed, bloat removed for size
:: ONEFILE: Single exe output
python -m nuitka ^
    --onefile ^
    --windows-disable-console ^
    --windows-uac-admin ^
    --lto=no ^
    --plugin-enable=anti-bloat ^
    --plugin-enable=pyqt6 ^
    --include-data-dir=resources=resources ^
    --output-filename=GBot.exe ^
    --output-dir=dist_release ^
    --product-version=1.0.0 ^
    --file-version=1.0.0 ^
    --noinclude-pytest-mode=nofollow ^
    --noinclude-unittest-mode=nofollow ^
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
    --main=src/main.py

if %ERRORLEVEL% equ 0 (
    echo [COPY] Copying Portable Tesseract to dist path...
    if not exist "dist_release\tesseract" mkdir "dist_release\tesseract"
    xcopy /E /I /Y "assets\tesseract" "dist_release\tesseract"

    echo [SUCCESS] Build complete! 
    echo [INFO] You can now ZIP the folder: dist_release\main.dist
) else (
    echo [FAILURE] Build failed.
)
pause

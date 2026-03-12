@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ============================================
:: Albion Market Scanner - Package for Distribution
:: ============================================
:: Creates a ZIP archive from the compiled standalone
:: Run this AFTER build.bat
:: ============================================

set "APP_NAME=GBot"
set "DIST_DIR=dist\%APP_NAME%.dist"
set "PACKAGE_DIR=dist\%APP_NAME%"

echo.
echo ==========================================
echo   Albion Market Scanner - Package
echo   Creating distribution package
echo ==========================================
echo.

:: --- Warnings ---
if not exist "%DIST_DIR%\%APP_NAME%.exe" (
    echo [ERROR] Build not found! Please run build.bat first.
    exit /b 1
)

:: --- Preparing Distribution Directory ---
echo [1/3] Preparing distribution folder...
if exist "%PACKAGE_DIR%" rmdir /s /q "%PACKAGE_DIR%"
mkdir "%PACKAGE_DIR%"

:: Copy everything from .dist EXCEPT local config/data/logs
robocopy "%DIST_DIR%" "%PACKAGE_DIR%" /E /XD config data logs /NFL /NDL /NJH /NJS >nul
echo [OK] Files copied (without local configs)
echo.

:: --- Creating Shortcut Helper ---
echo [2/4] Creating desktop shortcut helper...
(
echo @echo off
echo echo Creating desktop shortcut...
echo powershell -Command "$s=^(New-Object -ComObject WScript.Shell^).CreateShortcut^('%%USERPROFILE%%\Desktop\GBot.lnk'^);$s.TargetPath='%%~dp0%APP_NAME%.exe';$s.WorkingDirectory='%%~dp0';$s.Save^()"
echo echo [OK] Shortcut "GBot" created on the desktop!
echo pause
) > "%PACKAGE_DIR%\Create Shortcut.bat"

:: --- Cleaning up ---
echo [3/4] Cleaning up unused files...

:: Removing __pycache__ folders
for /d /r "%PACKAGE_DIR%" %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d" 2>nul
)

:: Removing remaining .pyc files
del /s /q "%PACKAGE_DIR%\*.pyc" >nul 2>nul

echo [OK] Clenup done
echo.

:: --- Archiving ---
echo [3/3] Creating ZIP archive...

set "ZIP_FILE=dist\%APP_NAME%.zip"
if exist "%ZIP_FILE%" del "%ZIP_FILE%"

powershell -Command "Compress-Archive -Path '%PACKAGE_DIR%\*' -DestinationPath '%ZIP_FILE%' -Force"

if errorlevel 1 (
    echo [WARNING] Failed to create ZIP. Folder %PACKAGE_DIR% is ready for manual packaging.
) else (
    echo [OK] ZIP created: %ZIP_FILE%
)

echo.
echo ==========================================
echo [OK] PACKAGING COMPLETE!
echo.
echo    Folder: %PACKAGE_DIR%\
echo    Archive: %ZIP_FILE%
echo.

:: Show Sizes
echo Sizes:
echo   Folder:
powershell -Command "'{0:N2} MB' -f ((Get-ChildItem '%PACKAGE_DIR%' -Recurse | Measure-Object Length -Sum).Sum / 1MB)"
if exist "%ZIP_FILE%" (
    echo   ZIP:
    powershell -Command "'{0:N2} MB' -f ((Get-Item '%ZIP_FILE%').Length / 1MB)"
)

echo.
echo Structure:
echo.
echo   %APP_NAME%\
echo   +-- %APP_NAME%.exe          - main executable
echo   +-- resources\              - reference images
echo   ^|   +-- ref_*.png
echo   +-- tesseract\              - OCR engine
echo   ^|   +-- tesseract.exe
echo   ^|   +-- tessdata\
echo   ^|   ^|   +-- eng.traineddata
echo   ^|   ^|   +-- rus.traineddata
echo   ^|   +-- *.dll
echo   +-- *.dll                   - PyQt6 / Python runtime
echo.
pause

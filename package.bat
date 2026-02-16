@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ============================================
:: Albion Market Scanner — Package for Distribution
:: ============================================
:: Создаёт zip-архив из собранного standalone
:: Запускать ПОСЛЕ build.bat
:: ============================================

set "APP_NAME=GBot"
set "DIST_DIR=dist\%APP_NAME%.dist"
set "PACKAGE_DIR=dist\%APP_NAME%"

echo.
echo ╔══════════════════════════════════════════╗
echo ║   Albion Market Scanner — Package        ║
echo ║   Создание дистрибутива для раздачи      ║
echo ╚══════════════════════════════════════════╝
echo.

:: --- Проверка ---
if not exist "%DIST_DIR%\%APP_NAME%.exe" (
    echo ❌ Сборка не найдена! Сначала запустите build.bat
    exit /b 1
)

:: --- Подготовка чистой папки ---
echo [1/3] Подготовка папки дистрибутива...
if exist "%PACKAGE_DIR%" rmdir /s /q "%PACKAGE_DIR%"
mkdir "%PACKAGE_DIR%"

:: Копируем всё из .dist, исключая локальные данные (config, data, logs)
robocopy "%DIST_DIR%" "%PACKAGE_DIR%" /E /XD config data logs /NFL /NDL /NJH /NJS >nul
echo ✅ Файлы скопированы (без локальных конфигов)
echo.

:: --- Создание помощника для ярлыка ---
echo [2/4] Создание помощника для ярлыка...
(
echo @echo off
echo echo Создание ярлыка на рабочем столе...
echo powershell -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%%USERPROFILE%%\Desktop\GBot.lnk');$s.TargetPath='%%~dp0%APP_NAME%.exe';$s.WorkingDirectory='%%~dp0';$s.Save()"
echo echo ✅ Ярлык "GBot" создан на рабочем столе!
echo pause
) > "%PACKAGE_DIR%\Создать ярлык.bat"

:: --- Очистка мусора ---
echo [3/4] Очистка ненужных файлов...

:: Удаляем __pycache__
for /d /r "%PACKAGE_DIR%" %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d" 2>nul
)

:: Удаляем .pyc если остались
del /s /q "%PACKAGE_DIR%\*.pyc" >nul 2>nul

echo ✅ Очищено
echo.

:: --- Архивация ---
echo [3/3] Создание ZIP-архива...

set "ZIP_FILE=dist\%APP_NAME%.zip"
if exist "%ZIP_FILE%" del "%ZIP_FILE%"

powershell -Command "Compress-Archive -Path '%PACKAGE_DIR%\*' -DestinationPath '%ZIP_FILE%' -Force"

if errorlevel 1 (
    echo ⚠️ Не удалось создать ZIP. Папка %PACKAGE_DIR% готова для ручной упаковки.
) else (
    echo ✅ ZIP создан: %ZIP_FILE%
)

echo.
echo ══════════════════════════════════════════
echo ✅ УПАКОВКА ЗАВЕРШЕНА!
echo.
echo    Папка:  %PACKAGE_DIR%\
echo    Архив:  %ZIP_FILE%
echo.

:: Показать размеры
echo Размеры:
echo   Папка:
powershell -Command "'{0:N2} MB' -f ((Get-ChildItem '%PACKAGE_DIR%' -Recurse | Measure-Object Length -Sum).Sum / 1MB)"
if exist "%ZIP_FILE%" (
    echo   ZIP:
    powershell -Command "'{0:N2} MB' -f ((Get-Item '%ZIP_FILE%').Length / 1MB)"
)

echo.
echo Структура дистрибутива:
echo.
echo   %APP_NAME%\
echo   ├── %APP_NAME%.exe          — главное приложение
echo   ├── resources\              — справочные изображения
echo   │   └── ref_*.png
echo   ├── tesseract\              — OCR движок
echo   │   ├── tesseract.exe
echo   │   ├── tessdata\
echo   │   │   ├── eng.traineddata
echo   │   │   └── rus.traineddata
echo   │   └── *.dll
echo   └── *.dll                   — PyQt6 / Python runtime
echo.
pause

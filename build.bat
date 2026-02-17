@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ============================================
:: Albion Market Scanner — Nuitka Build Script
:: ============================================
:: Режим: standalone (папка с .exe + зависимости)
:: Результат: dist\GBot\GBot.exe
:: ============================================

set "APP_NAME=GBot"
set "ENTRY_POINT=src\main.py"
set "OUTPUT_DIR=dist"

:: Читаем версию из version.py (единый источник)
for /f "tokens=2 delims=^""" %%v in ('findstr "CURRENT_VERSION" src\core\version.py') do set "APP_VERSION=%%v"
if not defined APP_VERSION set "APP_VERSION=0.0.0"

echo.
echo ╔══════════════════════════════════════════╗
echo ║   Albion Market Scanner — Build          ║
echo ║   Mode: Standalone (Nuitka)              ║
echo ╚══════════════════════════════════════════╝
echo.

:: --- Проверки ---
echo [1/5] Проверка окружения...

where python >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден в PATH!
    exit /b 1
)

python -c "import nuitka" >nul 2>&1
if errorlevel 1 (
    echo ❌ Nuitka не установлена! Установите: pip install nuitka
    exit /b 1
)

if not exist "%ENTRY_POINT%" (
    echo ❌ Точка входа %ENTRY_POINT% не найдена!
    echo    Запускайте скрипт из корня проекта.
    exit /b 1
)

echo ✅ Окружение готово
echo.

:: --- Тесты ---
echo [2/5] Запуск Unit-тестов...
python -m pytest tests/test_core_systems.py
if errorlevel 1 (
    echo.
    echo ❌ ТЕСТЫ НЕ ПРОШЛИ! Сборка отменена.
    echo    Исправьте ошибки и попробуйте снова.
    exit /b 1
)
echo ✅ Тесты пройдены!
echo.

:: --- Очистка предыдущей сборки ---
echo [3/5] Очистка предыдущей сборки...
if exist "%OUTPUT_DIR%\%APP_NAME%.dist" rmdir /s /q "%OUTPUT_DIR%\%APP_NAME%.dist"
if exist "%OUTPUT_DIR%\%APP_NAME%.build" rmdir /s /q "%OUTPUT_DIR%\%APP_NAME%.build"
echo ✅ Очищено
echo.

:: --- Компиляция ---
echo [4/5] Компиляция через Nuitka (это займёт 5-15 минут)...
echo.

python -m nuitka ^
    --standalone ^
    --jobs=%NUMBER_OF_PROCESSORS% ^
    --output-dir=%OUTPUT_DIR% ^
    --output-filename=%APP_NAME%.exe ^
    --enable-plugin=pyqt6 ^
    --include-package=src ^
    --include-data-dir=resources=resources ^
    --windows-console-mode=attach ^
    --windows-uac-admin ^
    --python-flag=no_docstrings ^
    --python-flag=no_asserts ^
    --nofollow-import-to=tkinter ^
    --nofollow-import-to=unittest ^
    --nofollow-import-to=test ^
    --nofollow-import-to=setuptools ^
    --nofollow-import-to=pip ^
    --nofollow-import-to=distutils ^
    --nofollow-import-to=pydoc ^
    --nofollow-import-to=doctest ^
    --nofollow-import-to=xmlrpc ^
    --nofollow-import-to=sqlite3 ^
    --nofollow-import-to=matplotlib ^
    --nofollow-import-to=scipy ^
    --nofollow-import-to=pandas ^
    --product-name="Albion Market Scanner" ^
    --product-version=%APP_VERSION% ^
    --file-description="Albion Market Scanner & Buyer Bot" ^
    --copyright="© 2026" ^
    --assume-yes-for-downloads ^
    %ENTRY_POINT%

if errorlevel 1 (
    echo.
    echo ❌ Ошибка компиляции! Проверьте вывод выше.
    exit /b 1
)

echo.
echo ✅ Компиляция завершена!
echo.

:: Nuitka именует папку по имени entry-point (main.py → main.dist)
:: Переименовываем в GBot.dist
if exist "%OUTPUT_DIR%\main.dist" (
    if exist "%OUTPUT_DIR%\%APP_NAME%.dist" rmdir /s /q "%OUTPUT_DIR%\%APP_NAME%.dist"
    ren "%OUTPUT_DIR%\main.dist" "%APP_NAME%.dist"
    echo    ✅ Переименовано main.dist → %APP_NAME%.dist
)
if exist "%OUTPUT_DIR%\main.build" (
    if exist "%OUTPUT_DIR%\%APP_NAME%.build" rmdir /s /q "%OUTPUT_DIR%\%APP_NAME%.build"
    ren "%OUTPUT_DIR%\main.build" "%APP_NAME%.build"
)

echo.

:: Копируем Tesseract (только eng + rus)
set "TESS_SRC=assets\tesseract"
set "TESS_DST=%OUTPUT_DIR%\%APP_NAME%.dist\tesseract"

if exist "%TESS_SRC%" (
    echo    Копирование Tesseract OCR...
    
    :: Копируем всё кроме tessdata
    robocopy "%TESS_SRC%" "%TESS_DST%" /E /XD tessdata /NFL /NDL /NJH /NJS >nul
    
    :: Копируем только нужные языки из tessdata
    mkdir "%TESS_DST%\tessdata" 2>nul
    mkdir "%TESS_DST%\tessdata\configs" 2>nul
    mkdir "%TESS_DST%\tessdata\tessconfigs" 2>nul
    
    if exist "%TESS_SRC%\tessdata\eng.traineddata" (
        copy /Y "%TESS_SRC%\tessdata\eng.traineddata" "%TESS_DST%\tessdata\" >nul
        echo    ✅ eng.traineddata
    )
    if exist "%TESS_SRC%\tessdata\rus.traineddata" (
        copy /Y "%TESS_SRC%\tessdata\rus.traineddata" "%TESS_DST%\tessdata\" >nul
        echo    ✅ rus.traineddata
    )
    if exist "%TESS_SRC%\tessdata\osd.traineddata" (
        copy /Y "%TESS_SRC%\tessdata\osd.traineddata" "%TESS_DST%\tessdata\" >nul
        echo    ✅ osd.traineddata
    )
    if exist "%TESS_SRC%\tessdata\pdf.ttf" (
        copy /Y "%TESS_SRC%\tessdata\pdf.ttf" "%TESS_DST%\tessdata\" >nul
    )
    
    :: Копируем конфиги tessdata
    robocopy "%TESS_SRC%\tessdata\configs" "%TESS_DST%\tessdata\configs" /E /NFL /NDL /NJH /NJS >nul 2>nul
    robocopy "%TESS_SRC%\tessdata\tessconfigs" "%TESS_DST%\tessdata\tessconfigs" /E /NFL /NDL /NJH /NJS >nul 2>nul
    
    echo    ✅ Tesseract скопирован ^(eng + rus^)
) else (
    echo    ⚠️ Папка %TESS_SRC% не найдена — Tesseract не включён
)

echo.
echo ══════════════════════════════════════════
echo ✅ СБОРКА ЗАВЕРШЕНА!
echo.
echo    Результат: %OUTPUT_DIR%\%APP_NAME%.dist\
echo    Запуск:    %OUTPUT_DIR%\%APP_NAME%.dist\%APP_NAME%.exe
echo ══════════════════════════════════════════

:: Показать размер
echo.
echo Размер дистрибутива:
powershell -Command "'{0:N2} MB' -f ((Get-ChildItem '%OUTPUT_DIR%\%APP_NAME%.dist' -Recurse | Measure-Object Length -Sum).Sum / 1MB)"

echo.
pause

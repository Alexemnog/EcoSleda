@echo off
title ЕкоСледа - Компилиране на .exe
color 0A
echo.
echo  ============================================================
echo    ЕкоСледа v4.0  --  Компилиране на ЕкоСледа.exe
echo  ============================================================
echo.

REM ── 1. Провери Python ──────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ГРЕШКА]  Python не е намерен!
    echo  Изтегли от: https://python.org
    echo  Слагай отметка на "Add Python to PATH" при инсталация!
    pause & exit /b 1
)
echo  [OK]  Python е намерен.

REM ── 2. Инсталирай зависимости ──────────────────────────────────
echo  [...]  Инсталиране на Python пакети...
pip install requests geopy matplotlib beautifulsoup4 reportlab pyinstaller ^
    --quiet --disable-pip-version-check
if errorlevel 1 (
    echo  [ГРЕШКА]  Инсталирането на пакети се провали.
    pause & exit /b 1
)
echo  [OK]  Пакетите са инсталирани.

REM ── 3. Компилирай .exe ─────────────────────────────────────────
echo  [...]  Компилиране... (може да отнеме 1-3 минути)
echo.
cd /d "%~dp0"

pyinstaller main.py ^
    --onefile ^
    --windowed ^
    --noconsole ^
    --name ЕкоСледа ^
    --add-data "theme.py;." ^
    --add-data "database.py;." ^
    --add-data "map_server.py;." ^
    --add-data "config.py;." ^
    --add-data "auth.py;." ^
    --add-data "app.py;." ^
    --hidden-import geopy ^
    --hidden-import geopy.geocoders ^
    --hidden-import geopy.distance ^
    --hidden-import matplotlib ^
    --hidden-import matplotlib.backends.backend_tkagg ^
    --hidden-import bs4 ^
    --hidden-import requests ^
    --hidden-import PIL ^
    --clean ^
    --noconfirm

if errorlevel 1 (
    echo.
    echo  [ГРЕШКА]  Компилирането се провали. Виж съобщенията по-горе.
    pause & exit /b 1
)

REM ── 4. Провери резултата ───────────────────────────────────────
if exist "dist\ЕкоСледа.exe" (
    echo.
    echo  ============================================================
    echo    [УСПЕХ]  ЕкоСледа.exe е готов!
    echo    Намери го в:  dist\ЕкоСледа.exe
    echo  ============================================================
    echo.
    echo  Можеш да копираш ЕкоСледа.exe навсякъде и да го
    echo  стартираш директно - без Command Prompt, без Python!
    echo.
    explorer dist
) else (
    echo  [ГРЕШКА]  .exe файлът не беше намерен след компилирането.
)

pause

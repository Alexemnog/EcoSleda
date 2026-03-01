@echo off
REM ── ЕкоСледа v4.0 — Стартер без Command Prompt ──

REM Провери Python
python --version >nul 2>&1
if errorlevel 1 (
    msg * "Python не е намерен! Изтегли от https://python.org"
    exit /b 1
)

REM Инсталирай пакети тихо
pip install requests geopy matplotlib beautifulsoup4 reportlab --quiet --disable-pip-version-check >nul 2>&1

REM Стартирай БЕЗ команден прозорец (pythonw)
cd /d "%~dp0"
start "" pythonw main.py

@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "NOPAUSE="
if /I "%~1"=="--no-pause" set "NOPAUSE=1"
where py >nul 2>nul
if not errorlevel 1 (set "PY=py -3") else (set "PY=python")
if not exist ".venv\Scripts\python.exe" (
  %PY% -m venv .venv
  if errorlevel 1 goto :failed
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt "pyinstaller>=6,<7"
if errorlevel 1 goto :failed
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name "BssBooster" --icon "assets\bss_booster_icon.ico" --add-data "assets\bss_booster_icon.png;assets" --add-data "assets\booster_alarm.wav;assets" main.py
if errorlevel 1 goto :failed
echo.
echo Built standalone app: dist\BssBooster.exe
if not defined NOPAUSE pause
exit /b 0
:failed
echo.
echo Build failed. Ensure you have Python 3.11+ and an internet connection.
if not defined NOPAUSE pause
exit /b 1

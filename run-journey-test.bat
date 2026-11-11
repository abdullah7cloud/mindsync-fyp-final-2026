@echo off
setlocal
set PYTHONUTF8=1
set "LOGS=%~dp0_update_backup\logs"
if not exist "%LOGS%" mkdir "%LOGS%"
cd /d "%~dp0backend"
call .venv\Scripts\activate.bat
echo MindSync must be running (start-backend.bat and start-frontend.bat). Results are written to the docs folder.
echo.
python -m scripts.journey_probe 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath '%LOGS%\journey.txt'"
echo.
pause

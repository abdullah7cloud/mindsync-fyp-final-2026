@echo off
setlocal
set PYTHONUTF8=1
set "LOGS=%~dp0_update_backup\logs"
if not exist "%LOGS%" mkdir "%LOGS%"
cd /d "%~dp0backend"
call .venv\Scripts\activate.bat
echo Make sure start-backend.bat is running in another window first!
echo.
python -m scripts.diagnose_concurrency 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath '%LOGS%\diagnose_concurrency.txt'"
echo.
pause

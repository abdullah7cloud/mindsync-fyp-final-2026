@echo off
setlocal
set PYTHONUTF8=1
set "LOGS=%~dp0_update_backup\logs"
if not exist "%LOGS%" mkdir "%LOGS%"
cd /d "%~dp0backend"
call .venv\Scripts\activate.bat
echo This tests MindSync's OpenAI code against a LOCAL stand-in. No key, no internet, no cost.
echo (It uses ports 8002 and 9000 for a few seconds; your normal backend can keep running.)
echo.
python -m scripts.ai_integration_probe 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath '%LOGS%\ai_integration.txt'"
echo.
pause

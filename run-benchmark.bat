@echo off
setlocal
set PYTHONUTF8=1
set "LOGS=%~dp0_update_backup\logs"
if not exist "%LOGS%" mkdir "%LOGS%"
cd /d "%~dp0backend"
call .venv\Scripts\activate.bat
echo Make sure start-backend.bat is running in another window first!
echo.
echo --- Ranking engine speed ---
python -m scripts.benchmark_latency engine 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath '%LOGS%\benchmark_engine.txt'"
echo.
echo --- End-to-end API speed (target: under 3000 ms) ---
python -m scripts.benchmark_latency api --runs 50 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath '%LOGS%\benchmark_api.txt'"
echo.
echo Results were saved to docs\latency_results.md
pause

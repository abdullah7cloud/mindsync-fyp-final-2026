@echo off
setlocal
set PYTHONUTF8=1
set "LOGS=%~dp0_update_backup\logs"
if not exist "%LOGS%" mkdir "%LOGS%"
cd /d "%~dp0backend"
call .venv\Scripts\activate.bat
echo Checking test dependencies...
pip install -r requirements.txt --quiet --disable-pip-version-check
echo.
echo ===== BACKEND TESTS (Python, pytest) =====
python -m pytest -q 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath '%LOGS%\tests_backend.txt'"
echo.
echo ===== FRONTEND TESTS (React, vitest) =====
cd /d "%~dp0frontend"
if not exist node_modules\vitest call npm install --no-audit --no-fund
call npm test 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath '%LOGS%\tests_frontend.txt'"
echo.
echo The full output was also saved in _update_backup\logs
pause

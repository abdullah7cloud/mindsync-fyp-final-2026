@echo off
setlocal
set PYTHONUTF8=1
set "LOGS=%~dp0_update_backup\logs"
if not exist "%LOGS%" mkdir "%LOGS%"
cd /d "%~dp0backend"
call .venv\Scripts\activate.bat
pip install playwright --quiet --disable-pip-version-check
set E2E_CHANNEL=chrome
echo MindSync must be running (start-backend.bat and start-frontend.bat). Restart start-backend.bat first if you ran a test just before.
if not exist "%TEMP%\e2e_files" mkdir "%TEMP%\e2e_files"
python "%~dp0e2e\make_test_files.py" "%TEMP%\e2e_files"
echo.
python "%~dp0e2e\a11y_audit_four_pages.py" 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath '%LOGS%\a11y_four_pages.txt'"
echo.
pause

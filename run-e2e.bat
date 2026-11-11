@echo off
setlocal
set PYTHONUTF8=1
set "LOGS=%~dp0_update_backup\logs"
if not exist "%LOGS%" mkdir "%LOGS%"
cd /d "%~dp0backend"
call .venv\Scripts\activate.bat
echo Make sure start-backend.bat AND start-frontend.bat are running in other windows first!
echo Restart start-backend.bat first if you ran this twice in a row, because sign-ups are limited per hour.
echo.
pip install playwright --quiet --disable-pip-version-check
set E2E_CHANNEL=chrome
set E2E_TIMEZONE=Europe/Copenhagen
if not exist "%TEMP%\e2e_files" mkdir "%TEMP%\e2e_files"
python "%~dp0e2e\make_test_files.py" "%TEMP%\e2e_files"
python "%~dp0e2e\browser_e2e_four_pages.py" "%LOGS%\e2e_four_pages_screenshots" --ai-off 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath '%LOGS%\e2e_four_pages.txt'"
echo.
echo (This ran with AI OFF, which is how MindSync starts. The quiz is then correctly "not available".)
pause

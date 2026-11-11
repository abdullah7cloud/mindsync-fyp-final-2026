@echo off
setlocal
set "LOGS=%~dp0_update_backup\logs"
if not exist "%LOGS%" mkdir "%LOGS%"
cd /d "%~dp0backend"
call .venv\Scripts\activate.bat
echo This checks your email settings in backend\.env. Your password is never shown.
echo.
set /p TO=Type your email address to send a real test email (or just press Enter to only test the login): 
if "%TO%"=="" (
  python -m scripts.check_email 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath '%LOGS%\email_check.txt'"
) else (
  python -m scripts.check_email --to "%TO%" 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath '%LOGS%\email_check.txt'"
)
echo.
pause

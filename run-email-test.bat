@echo off
setlocal
set PYTHONUTF8=1
set "LOGS=%~dp0_update_backup\logs"
if not exist "%LOGS%" mkdir "%LOGS%"
cd /d "%~dp0backend"
call .venv\Scripts\activate.bat
echo This tests MindSync's e-mail reminder code against a LOCAL mail-collecting server. Nothing is sent to the internet.
pip install aiosmtpd --quiet --disable-pip-version-check
python -m scripts.email_integration_probe 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath '%LOGS%\email_integration.txt'"
echo.
echo To test a REAL provider (Gmail App password), use test-email.bat after filling backend\.env.
pause

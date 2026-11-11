@echo off
setlocal
set PYTHONUTF8=1
set "LOGS=%~dp0_update_backup\logs"
if not exist "%LOGS%" mkdir "%LOGS%"
cd /d "%~dp0backend"
call .venv\Scripts\activate.bat
echo Make sure start-backend.bat is running in another window first! (Restart it first if you ran this test just before: sign-ups are limited per hour.)
echo.
python -m scripts.security_probe_four_pages 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath '%LOGS%\security_probe_four_pages.txt'"
echo.
echo Now the older probe of the original endpoints (still in the backend):
python -m scripts.security_probe 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath '%LOGS%\security_probe.txt'"
echo.
pause

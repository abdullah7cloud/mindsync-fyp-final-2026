@echo off
setlocal
cd /d "%~dp0frontend"

if not exist .env (
    echo VITE_API_BASE_URL=http://localhost:8000 > .env
)

if not exist node_modules (
    echo Installing website dependencies for the first time - this may take a minute...
    call npm install
)

echo.
echo ===== MindSync website =====
echo Running from folder: %cd%
echo If it says port 5173 is already in use, an OLD copy is still running: double-click stop-old-mindsync.bat first, then start again.
echo.
echo Starting the MindSync website... leave this window open while you use the site.
echo Once it shows "Local: http://localhost:5173/", open that address in Chrome.
echo.
call npm run dev

pause

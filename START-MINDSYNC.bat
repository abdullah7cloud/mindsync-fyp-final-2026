@echo off
setlocal
cd /d "%~dp0"
echo ===== MindSync: one-click start =====
echo Running from folder: %cd%
echo.
echo Step 1: closing any OLD MindSync still running...
for %%P in (5173 5174 8000) do (
  for /f "tokens=5" %%A in ('netstat -ano ^| findstr ":%%P " ^| findstr LISTENING') do taskkill /F /PID %%A >nul 2>&1
)
echo.
echo Step 2: settings file...
if not exist backend\.env python backend\scripts\make_env.py
if not exist backend\.env (
  echo Could not create backend\.env - is Python installed? Send a photo of this window.
  pause
  exit /b 1
)
echo.
echo Step 3: starting the backend and the website in two new windows (leave them open)...
start "MindSync backend" "%~dp0start-backend.bat"
echo Waiting about 40 seconds for the backend to be ready...
timeout /t 40 /nobreak >nul
start "MindSync website" "%~dp0start-frontend.bat"
timeout /t 15 /nobreak >nul
echo Step 4: opening the browser...
start "" http://localhost:5173/
echo.
echo If the page looks old, press Ctrl+Shift+R in the browser.
echo If the backend window shows an error, send a photo of it.
pause

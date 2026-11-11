@echo off
setlocal
echo Stopping any old MindSync backend on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /T /PID %%a >nul 2>&1
timeout /t 2 /nobreak >nul
call "%~dp0start-backend.bat"

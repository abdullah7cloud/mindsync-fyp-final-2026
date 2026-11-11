@echo off
setlocal
cd /d "%~dp0backend"
echo.
echo ===== MindSync backend =====
echo Running from folder: %cd%
echo.
if not exist .env echo No backend\.env file yet - creating one now.
if not exist .env python scripts\make_env.py
if not exist .env echo Could not create .env. Is Python installed? Send a photo of this window.
if not exist .env pause
if not exist .env exit /b 1
if not exist .venv\Scripts\activate.bat echo Setting up Python environment for the first time - please wait...
if not exist .venv\Scripts\activate.bat python -m venv .venv
call .venv\Scripts\activate.bat
echo Installing dependencies...
pip install -r requirements.txt --quiet --disable-pip-version-check
echo.
echo Starting MindSync backend. Leave this window open.
echo When you see "Application startup complete" it is ready.
echo.
uvicorn app.main:app
echo.
echo The backend stopped. Read the messages above to see why.
pause

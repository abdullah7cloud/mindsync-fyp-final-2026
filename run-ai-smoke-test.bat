@echo off
setlocal
set PYTHONUTF8=1
cd /d "%~dp0backend"
call .venv\Scripts\activate.bat
echo This sends ONE tiny test question to your chosen AI provider, but only after you type YES.
echo If AI is still switched off in backend\.env, it sends nothing at all.
echo.
python -m scripts.ai_smoke_test
echo.
pause

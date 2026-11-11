@echo off
setlocal
set "LOGS=%~dp0_update_backup\logs"
if not exist "%LOGS%" mkdir "%LOGS%"
cd /d "%~dp0backend"
if not exist data (
    echo There is no backend\data folder. Create it and put the downloaded dataset CSV inside - see docs\WELLBEING_MODEL.md
    pause
    exit /b 1
)
set "CSV="
for %%f in (data\*.csv) do set "CSV=%%f"
if not defined CSV (
    echo No .csv file found in backend\data. Put the dataset CSV there first - see docs\WELLBEING_MODEL.md
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat
echo Installing the training libraries (only needed for training, not for running the website)...
pip install -r requirements-train.txt --quiet --disable-pip-version-check
echo.
echo ===== 1. WHAT IS IN THE FILE (no training yet) =====
python -m ml_training.wellbeing_train --csv "%CSV%" --inspect 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath '%LOGS%\wellbeing_inspect.txt'"
echo.
echo ===== 2. TRAINING AND EVALUATION =====
python -m ml_training.wellbeing_train --csv "%CSV%" 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath '%LOGS%\wellbeing_train.txt'"
echo.
echo Done. Now double-click restart-backend.bat so the website loads the new model.
pause

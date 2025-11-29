@echo off
SETLOCAL ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION

echo --------------------------------------------
echo  Deploying Trading Application
echo --------------------------------------------

REM Define source and destination paths
set "SOURCE=%~dp0.."
set "DEST=C:\Apps\TradingSystem"

REM Create destination folder if missing
if not exist "%DEST%" (
    echo Creating destination folder: "%DEST%"
    mkdir "%DEST%"
)

REM Copy application directories, excluding .env, config.yaml, and state.json
echo Copying application files...
robocopy "%SOURCE%\app" "%DEST%\app" /E /XF *.env config.yaml state.json /NFL /NDL /NJH /NJS /NC /NS >nul
robocopy "%SOURCE%\history" "%DEST%\history" /E /XF *.env config.yaml state.json /NFL /NDL /NJH /NJS /NC /NS >nul

REM Copy configuration and startup scripts (excluding .env)
echo Copying configuration files...
copy /Y "%SOURCE%\requirements.txt" "%DEST%\requirements.txt" >nul

echo Copying startup scripts...
copy /Y "%SOURCE%\startup\run_app_prod.bat" "%DEST%\run_app_prod.bat" >nul
copy /Y "%SOURCE%\startup\restart_terminals.bat" "%DEST%\restart_terminals.bat" >nul

REM Navigate to destination
cd /d "%DEST%"

REM Create virtual environment if missing
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate venv and install dependencies
echo Installing Python dependencies...
call "venv\Scripts\activate.bat"
pip install --upgrade pip >nul
pip install -r requirements.txt
call "venv\Scripts\deactivate.bat"

echo.
echo ✅ Deployment complete!
echo Run "%DEST%\run_app_prod.bat" to start the Trading application.
echo --------------------------------------------

ENDLOCAL
exit /b 0

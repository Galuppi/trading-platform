@echo off
SETLOCAL ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION

echo --------------------------------------------
echo  Trading System - Backup and Deploy
echo --------------------------------------------

REM ==== CONFIGURATION ====
set "SOURCE=%~dp0.."
set "DEST=C:\Apps\TradingSystem"
set "BACKUP_DIR=C:\Backups\prd_trading_system"
set "PUBLIC_REPO_DIR=C:\Development\trading-platform"

REM ---- BACKUP ----
echo Backing up current app...

if not exist "%BACKUP_DIR%" md "%BACKUP_DIR%" >nul 2>&1

REM Generate timestamp YYYY-MM-DD_HHMMSS
for /f %%A in ('wmic OS Get localdatetime ^| find "."') do set "dt=%%A"
set "TS=%dt:~0,4%-%dt:~4,2%-%dt:~6,2%_%dt:~8,6%"

if exist "%DEST%\app" (
    xcopy "%DEST%\app" "%BACKUP_DIR%\%TS%_prd_app\" /E /I /Y /Q >nul 2>&1
    echo Backup created: %BACKUP_DIR%\%TS%_prd_app\
) else (
    echo No existing app found - skipping backup.
)

if exist "%DEST%\history" (
    xcopy "%DEST%\history" "%BACKUP_DIR%\%TS%_prd_history\" /E /I /Y /Q >nul 2>&1
    echo Backup created: %BACKUP_DIR%\%TS%_prd_history\
) else (
    echo No existing history found - skipping backup.
)

echo --------------------------------------------

REM ---- DEPLOY ----
echo Deploying Trading Application...

if not exist "%DEST%" (
    echo Creating destination folder: "%DEST%"
    mkdir "%DEST%"
)

REM Copy application directories, excluding .env and state.json (config.yaml is now deployed)
echo Copying application files...
robocopy "%SOURCE%\app" "%DEST%\app" /E /XF *.env state.json /NFL /NDL /NJH /NJS /NC /NS >nul
robocopy "%SOURCE%\history" "%DEST%\history" /E /XF *.env state.json /NFL /NDL /NJH /NJS /NC /NS >nul

REM Copy configuration and startup scripts (excluding .env)
echo Copying configuration files...
copy /Y "%SOURCE%\requirements.txt" "%DEST%\requirements.txt" >nul

echo Copying startup scripts...
copy /Y "%SOURCE%\startup\run_app_prod.bat" "%DEST%\run_app_prod.bat" >nul
copy /Y "%SOURCE%\startup\restart_terminals.bat" "%DEST%\restart_terminals.bat" >nul
copy /Y "%SOURCE%\startup\deploy_to_production.bat" "%DEST%\deploy_to_production.bat" >nul

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

echo --------------------------------------------

REM ---- PUBLISH TO PUBLIC REPO FOLDER ----
echo Copying to public repo folder: "%PUBLIC_REPO_DIR%"

if not exist "%PUBLIC_REPO_DIR%" (
    echo Creating public repo folder: "%PUBLIC_REPO_DIR%"
    mkdir "%PUBLIC_REPO_DIR%"
)

REM Mirror the whole project into the public repo working copy, excluding
REM secrets, runtime state, local envs, and generated/data folders.
robocopy "%SOURCE%" "%PUBLIC_REPO_DIR%" /E ^
    /XD .git venv venv-dev __pycache__ historical-data backtest-results logs .vscode ^
    /XF *.env state.json *.log ^
    /NFL /NDL /NJH /NJS /NC /NS >nul

echo Public repo folder updated. Review and push from "%PUBLIC_REPO_DIR%" manually.

echo.
echo Deployment complete!
echo Run "%DEST%\run_app_prod.bat" to start the Trading application.
echo --------------------------------------------

ENDLOCAL
exit /b 0
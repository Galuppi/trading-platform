@echo off
SETLOCAL ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION

echo --------------------------------------------
echo  Trader (cTrader/MT5) - Backup and Deploy
echo --------------------------------------------

REM ==== CONFIGURATION ====
set "SOURCE=%~dp0.."
set "DEST=C:\Apps\Trader"
set "BACKUP_DIR=C:\Backups\prd_trader"
set "PUBLIC_REPO_DIR=C:\Development\trading-platform"
set "PYTHON_VERSION=3.12"

REM ---- LOCATE PYTHON 3.12 ----
echo Looking for Python %PYTHON_VERSION% via the py launcher...
set "PY312="
for /f "delims=" %%P in ('py -%PYTHON_VERSION% -c "import sys; print(sys.executable)" 2^>nul') do set "PY312=%%P"

if not defined PY312 (
    echo ERROR: Python %PYTHON_VERSION% was not found.
    echo Install it from https://www.python.org/downloads/release/python-31210/
    echo ^(Python 3.12 is required - Twisted/cTrader dependencies don't have
    echo  prebuilt Windows wheels for newer Python versions yet.^)
    exit /b 1
)
echo Found Python %PYTHON_VERSION% at: %PY312%
echo --------------------------------------------

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

echo --------------------------------------------

REM ---- DEPLOY ----
echo Deploying Trader Application...
if not exist "%DEST%" (
    echo Creating destination folder: "%DEST%"
    mkdir "%DEST%"
)

REM Copy application directories, excluding .env and state.json (config.yaml is now deployed)
echo Copying application files...
robocopy "%SOURCE%\app" "%DEST%\app" /E /XF *.env state.json ctrader_token.json /NFL /NDL /NJH /NJS /NC /NS >nul
robocopy "%SOURCE%\history" "%DEST%\history" /E /XF *.env state.json /NFL /NDL /NJH /NJS /NC /NS >nul
robocopy "%SOURCE%\scripts" "%DEST%\scripts" /E /XF *.env /NFL /NDL /NJH /NJS /NC /NS >nul

REM Copy configuration and startup scripts (excluding .env)
echo Copying configuration files...
copy /Y "%SOURCE%\requirements.txt" "%DEST%\requirements.txt" >nul

echo Copying startup scripts...
copy /Y "%SOURCE%\startup\run_app_prod.bat" "%DEST%\run_app_prod.bat" >nul
copy /Y "%SOURCE%\startup\restart_terminals.bat" "%DEST%\restart_terminals.bat" >nul
copy /Y "%SOURCE%\startup\deploy_to_production.bat" "%DEST%\deploy_to_production.bat" >nul
copy /Y "%SOURCE%\startup\release_app_prod.bat" "%DEST%\release_app_prod.bat" >nul

REM Navigate to destination
cd /d "%DEST%"

REM Create or recreate the virtual environment, ensuring it's on Python 3.12
set "RECREATE_VENV=0"
if not exist "venv" (
    set "RECREATE_VENV=1"
) else (
    set "VENV_VER="
    for /f "delims=" %%V in ('"venv\Scripts\python.exe" -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')" 2^>nul') do set "VENV_VER=%%V"
    if not "!VENV_VER!"=="%PYTHON_VERSION%" (
        echo Existing venv is Python !VENV_VER!, not %PYTHON_VERSION% - recreating...
        set "RECREATE_VENV=1"
    )
)

if "!RECREATE_VENV!"=="1" (
    if exist "venv" (
        echo Removing outdated virtual environment...
        rmdir /s /q "venv"
    )
    echo Creating virtual environment with Python %PYTHON_VERSION%...
    "%PY312%" -m venv venv
) else (
    echo Existing virtual environment is already Python %PYTHON_VERSION% - reusing.
)

REM Activate venv and install dependencies
echo Installing Python dependencies...
call "venv\Scripts\activate.bat"
pip install --upgrade pip >nul
pip install -r requirements.txt
call "venv\Scripts\deactivate.bat"
REM echo --------------------------------------------

REM ---- PUBLISH TO PUBLIC REPO FOLDER ----
REM echo Copying to public repo folder: "%PUBLIC_REPO_DIR%"
REM if not exist "%PUBLIC_REPO_DIR%" (
REM     echo Creating public repo folder: "%PUBLIC_REPO_DIR%"
REM     mkdir "%PUBLIC_REPO_DIR%"
REM )

REM REM Mirror the whole project into the public repo working copy, excluding
REM REM secrets, runtime state, local envs, and generated/data folders.
REM robocopy "%SOURCE%" "%PUBLIC_REPO_DIR%" /E ^
REM     /XD .git venv venv-dev __pycache__ historical-data backtest-results logs .vscode ^
REM     /XF *.env state.json ctrader_token.json *.log ^
REM     /NFL /NDL /NJH /NJS /NC /NS >nul
REM echo Public repo folder updated. Review and push from "%PUBLIC_REPO_DIR%" manually.

echo.
echo Deployment complete!
echo Run "%DEST%\run_app_prod.bat" to start the Trader application.
echo --------------------------------------------

ENDLOCAL
exit /b 0

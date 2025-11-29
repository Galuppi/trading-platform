@echo off
title Run Prod

REM Ensure we're in the Production folder
cd /d %~dp0

REM Set console buffer and window size for better visibility
mode con: cols=100 lines=20

REM Set PYTHONPATH for production
set PYTHONPATH=%CD%

REM Activate the production virtual environment
call venv\Scripts\activate.bat

REM Set environment variable
set ENVIRONMENT=production

REM Run the main application
python app\runtime\main.py

REM Keep console window open so we can see logs/status
pause
@echo off
title Run Prod

@echo off
title Run History

REM Navigate to project root (one level above this .bat file)
cd /d %~dp0\..

REM Set PYTHONPATH to project root so 'app', 'downloader', etc. are top-level
set PYTHONPATH=%CD%

REM Activate the development virtual environment
call venv-dev\Scripts\activate.bat

REM Set environment variable for development
set ENVIRONMENT=development

REM Run the main application
python history\runtime\main.py

REM Keep terminal open to show logs
pause

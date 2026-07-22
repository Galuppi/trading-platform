@echo off
title cTrader OAuth Setup

REM This file lives in scripts\, but venv and PYTHONPATH are rooted at the
REM project root (one level up) -- same convention as startup\run_app_prod.bat.
cd /d %~dp0..

mode con: cols=100 lines=25

set PYTHONPATH=%CD%

call venv\Scripts\activate.bat

python scripts\ctrader_oauth_setup.py

REM Keep the window open so you can read the printed URL / any errors
REM before it closes, even though the script itself also opens a browser.
pause

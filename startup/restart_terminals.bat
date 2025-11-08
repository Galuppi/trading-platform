@echo off
echo [Restarting trading apps] %date% %time%

REM Kill Dev and Prod terminals by their window titles
taskkill /FI "WINDOWTITLE eq Run Dev" /F /T
taskkill /FI "WINDOWTITLE eq Run Prod" /F /T

REM Optional delay before restart
timeout /t 3 /nobreak

REM Restart both in new visible terminal windows
start "Run Dev" cmd /k "cd /d C:\Development\trading-system\startup && run_app_dev.bat"
start "Run Prod" cmd /k "cd /d C:\Production && run_app_prod.bat"

echo [Restart complete]

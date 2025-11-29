@echo off
echo Cleaning logs and state...
 
REM Delete all subdirectories in the logs folder
for /d %%G in ("C:\Development\trading-system\app\runtime\logs\*") do rmdir /S /Q "%%G"

REM Delete state.json file
del /Q "C:\Development\trading-system\app\runtime\state\state.json"

echo Reset complete.
pause

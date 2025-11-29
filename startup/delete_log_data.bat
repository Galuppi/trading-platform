@echo off
echo Cleaning logs and state...
 
REM Delete all subdirectories in the logs folder
for /d %%G in ("C:\Development\trading-system\history\runtime\logs\*") do rmdir /S /Q "%%G"

REM Delete data
for /d %%G in ("C:\Development\trading-system\data\mt5tester\*") do rmdir /S /Q "%%G"

echo Reset complete.
pause

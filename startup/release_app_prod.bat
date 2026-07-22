@echo off
REM ------------------------------------------
REM Release script: deletes the signal lock file
REM ------------------------------------------

set LOCK_FILE=app\runtime\trader.lck

if exist "%~dp0%LOCK_FILE%" (
    del "%~dp0%LOCK_FILE%"
    echo Lock file "%LOCK_FILE%" deleted successfully.
) else (
    echo No lock file found. Nothing to delete.
)

pause

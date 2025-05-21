@echo off
REM Dream.OS Daily Verification Script
REM This script runs the verification suite and logs the results

set TIMESTAMP=%date:~-4,4%%date:~-7,2%%date:~-10,2%-%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set LOG_DIR=logs\verification\daily
set LOG_FILE=%LOG_DIR%\verification_%TIMESTAMP%.log

REM Create log directory if it doesn't exist
if not exist %LOG_DIR% mkdir %LOG_DIR%

echo Running Dream.OS verification suite...
echo Timestamp: %TIMESTAMP%
echo Log file: %LOG_FILE%
echo.

REM Run verification
python -m src.dreamos.testing.run_verification --markdown --html > %LOG_FILE% 2>&1

REM Check the result
findstr /C:"Overall Status: PASS" %LOG_FILE% > nul
if %ERRORLEVEL% == 0 (
    echo Verification PASSED
    exit /b 0
) else (
    echo Verification FAILED
    type %LOG_FILE%
    exit /b 1
) 
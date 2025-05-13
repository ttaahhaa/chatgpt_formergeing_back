@echo off
echo Starting Document QA Assistant...

REM Create logs directory if it doesn't exist
mkdir logs 2>nul

REM Get current date in YYYYMMDD format
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (
    set day=%%a
    set month=%%b
    set year=%%c
)
set date=%year%%month%%day%

REM Set log file path
set logfile=logs\app_%date%.log

REM Remove existing log file for today
del /f /q %logfile% 2>nul

REM Check if AraberT model directory exists
if not exist data\embeddings\arabert (
    echo.
    echo WARNING: AraberT model directory not found!
    echo.
    echo Please place your AraberT model files in: %CD%\data\embeddings\arabert
    echo.
    pause
)

REM Check if Ollama is running
echo Checking if Ollama is running...
curl -s http://localhost:11434/api/version >nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo WARNING: Ollama does not appear to be running.
    echo Please start Ollama before continuing.
    echo.
    pause
)

REM Start the FastAPI application and log to file
echo.
echo =========================================
echo Starting FastAPI (http://localhost:8000)
echo Logs will be saved to %logfile%
echo Press Ctrl + C to stop the server
echo =========================================
echo.

REM Redirect stdout and stderr to log file
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload >> %logfile% 2>&1

REM After exit
echo.
echo =========================================
echo Uvicorn has exited or crashed.
echo Opening the log file for review...
start notepad %logfile%
pause

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

REM Remove any existing log files with today's date
del /f /q logs\app_%date%.log 2>nul

REM Check if AraberT model directory exists
if not exist data\embeddings\arabert (
    echo.
    echo WARNING: AraberT model directory not found!
    echo.
    echo Please place your AraberT model files in the following directory:
    echo %CD%\data\embeddings\arabert
    echo.
    echo The directory should contain files like:
    echo - config.json
    echo - pytorch_model.bin
    echo - tokenizer_config.json
    echo - vocab.txt
    echo.
    pause
)

REM Check if Ollama is running
echo Checking if Ollama is running...
curl -s http://localhost:11434/api/version >nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo WARNING: Ollama does not appear to be running
    echo Please start Ollama before continuing
    echo.
    pause
)

REM Start the FastAPI application
echo Starting FastAPI application on http://localhost:8000 ...
uvicorn app.main_mongodb:app --host 0.0.0.0 --port 8000 --reload

pause

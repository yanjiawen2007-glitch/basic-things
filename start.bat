@echo off
echo 🚀 Starting Task Scheduler...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.8+ first.
    exit /b 1
)

REM Create virtual environment if not exists
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo 📥 Installing dependencies...
pip install -q -r requirements.txt

REM Create necessary directories
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "scripts" mkdir scripts

REM Start the application
echo ✨ Starting server on http://localhost:8000
echo 📊 Dashboard: http://localhost:8000
echo 🛑 Press Ctrl+C to stop
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

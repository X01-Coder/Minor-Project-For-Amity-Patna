@echo off
echo ===============================================
echo AudioImageCarrier API - Quick Start
echo ===============================================
echo.

echo Starting the server...
echo.
echo The server will run at: http://127.0.0.1:8000
echo.
echo Press Ctrl+C to stop the server
echo.
echo ===============================================
echo.

cd /d "%~dp0"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

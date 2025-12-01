@echo off
echo ===============================================
echo AudioImageCarrier API - Test Suite
echo ===============================================
echo.
echo IMPORTANT: Make sure the server is running first!
echo Run start_server.bat in another window before running this test.
echo.
echo Testing server at: http://127.0.0.1:8000
echo.
echo ===============================================
echo.

cd /d "%~dp0"
timeout /t 2 /nobreak >nul
python standalone_test.py

echo.
echo ===============================================
echo Testing complete! Press any key to exit.
pause >nul

@echo off
echo Testing AudioImageCarrier API...
timeout /t 2 /nobreak >nul
curl -X GET "http://127.0.0.1:8000/health"
echo.
echo.
curl -X GET "http://127.0.0.1:8000/"
echo.

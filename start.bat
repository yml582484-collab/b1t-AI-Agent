@echo off
chcp 65001 >nul
title b1t-AI
cd /d "%~dp0"

echo ========================================
echo   b1t-AI
echo ========================================
echo.

netstat -ano | findstr ":8005" >nul
if %errorlevel% == 0 (
    echo [INFO] Closing port 8005...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8005"') do taskkill /F /PID %%a >nul 2>&1
    timeout /t 2 /nobreak >nul
)

echo [INFO] Starting server...
start /min "b1t-AI Server" cmd /c "python main.py --port 8005"

echo [INFO] Waiting 8 seconds for server...
timeout /t 8 /nobreak >nul

echo.
echo [OK] Server should be ready!
echo Opening browser...
start http://localhost:8005

echo.
echo ========================================
echo   http://localhost:8005
echo ========================================
pause

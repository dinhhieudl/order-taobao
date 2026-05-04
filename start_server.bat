@echo off
chcp 65001 >nul 2>&1
title Quan ly Van don Taobao - Server

echo ============================================
echo   📦 QUAN LY VAN DON TAOBAO - KHOI DONG
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Khong tim thay Python. Vui long cai dat Python 3.10+
    echo    Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Install dependencies if needed
if not exist ".venv" (
    echo 📥 Lan dau chay - Cai dat thu vien...
    pip install -r requirements.txt
    echo.
)

:: Get local IP
echo 🌐 Dang lay dia chi IP...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set "LOCAL_IP=%%a"
    goto :found_ip
)
:found_ip
set LOCAL_IP=%LOCAL_IP: =%

echo.
echo ============================================
echo   ✅ Server san sang!
echo.
echo   🖥️  May chu: http://localhost:8000
if defined LOCAL_IP (
    echo   📱 LAN:     http://%LOCAL_IP%:8000
)
echo.
echo   💡 Nhan Ctrl+C de dung server
echo ============================================
echo.

:: Start server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

pause

@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0.."

echo ========================================
echo  Run built EXE for testing
echo ========================================
echo.

set "EXE_PATH=dist\GameTools_Package\GameTools_HealthMonitor.exe"

if not exist "%EXE_PATH%" (
    echo [ERROR] Not found: %EXE_PATH%
    echo Please run scripts\build_exe.bat first.
    pause
    exit /b 1
)

echo Launching: %EXE_PATH%
start "" "%EXE_PATH%"
echo [OK] EXE launched.
pause

@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0.."

echo ========================================
echo  Run from Python source
echo ========================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "src\health_monitor.py"
) else (
    python "src\health_monitor.py"
)

echo.
if %errorlevel% neq 0 (
    echo [ERROR] Failed to run src\health_monitor.py
) else (
    echo [OK] Source run finished.
)
pause
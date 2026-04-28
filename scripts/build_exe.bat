@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0.."

echo ========================================
echo  Build EXE (one click)
echo ========================================
echo.

if not exist "tools\build.py" (
    echo [ERROR] Missing tools\build.py
    pause
    exit /b 1
)

if exist "src\health_monitor.py" (
    copy /Y "src\health_monitor.py" "src for DEVELOPER\health_monitor.py" >nul
)
if exist "src\language_packs.json" (
    copy /Y "src\language_packs.json" "src for DEVELOPER\language_packs.json" >nul
)

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "tools\build.py"
) else (
    python "tools\build.py"
)

echo.
if %errorlevel% neq 0 (
    echo [ERROR] EXE build failed.
) else (
    echo [OK] Build finished.
    echo Output is usually under dist\GameTools_Package\
)
pause

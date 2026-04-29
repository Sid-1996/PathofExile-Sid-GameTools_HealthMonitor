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

if exist "build\GameTools_HealthMonitor" (
    attrib -R "build\GameTools_HealthMonitor\*" /S /D >nul 2>nul
    rmdir /s /q "build\GameTools_HealthMonitor" >nul 2>nul
)

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY_CMD=py -3"
) else (
    set "PY_CMD=python"
)
call %PY_CMD% "tools\build.py"

echo.
if %errorlevel% neq 0 (
    echo [WARN] Build failed, retrying once after cleanup...
    if exist "build\GameTools_HealthMonitor" (
        attrib -R "build\GameTools_HealthMonitor\*" /S /D >nul 2>nul
        rmdir /s /q "build\GameTools_HealthMonitor" >nul 2>nul
    )
    call %PY_CMD% "tools\build.py"
    echo.
    if %errorlevel% neq 0 (
        echo [ERROR] EXE build failed.
    ) else (
        echo [OK] Build finished after retry.
        echo Output is usually under dist\GameTools_Package\
    )
) else (
    echo [OK] Build finished.
    echo Output is usually under dist\GameTools_Package\
)
pause

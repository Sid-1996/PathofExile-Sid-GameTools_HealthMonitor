@echo off
title GameTools Health Monitor

:: Clean up stale restart flag
if exist "%~dp0restart.flag" del /f /q "%~dp0restart.flag" >nul 2>&1

:restart
echo [INFO] Starting GameTools Health Monitor...

:: 1. Try EXE in same directory
if exist "%~dp0GameTools_HealthMonitor.exe" (
    start /WAIT "" "%~dp0GameTools_HealthMonitor.exe"
    if errorlevel 1 echo [WARN] GameTools_HealthMonitor.exe exited with code %ERRORLEVEL%
    goto check_restart
)

:: 2. Try EXE in dist directory
if exist "%~dp0dist\GameTools_HealthMonitor.exe" (
    start /WAIT "" "%~dp0dist\GameTools_HealthMonitor.exe"
    if errorlevel 1 echo [WARN] dist\GameTools_HealthMonitor.exe exited with code %ERRORLEVEL%
    goto check_restart
)

:: 3. Run from source
echo [INFO] EXE not found, running from source...

:: 3a. Look for Python
where python >nul 2>&1
if not errorlevel 1 (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python interpreter failed to start
        pause
        exit /b 1
    )
    python -c "import tkinter, cv2" 2>nul
    if errorlevel 1 (
        echo [ERROR] Missing dependencies. Please run scripts\install_dependencies.bat first.
        pause
        exit /b 1
    )
    python "%~dp0src\health_monitor.py"
    if errorlevel 1 echo [WARN] Script exited with code %ERRORLEVEL%
    goto check_restart
)

where py >nul 2>&1
if not errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python interpreter failed to start
        pause
        exit /b 1
    )
    py -c "import tkinter, cv2" 2>nul
    if errorlevel 1 (
        echo [ERROR] Missing dependencies. Please run scripts\install_dependencies.bat first.
        pause
        exit /b 1
    )
    py "%~dp0src\health_monitor.py"
    if errorlevel 1 echo [WARN] Script exited with code %ERRORLEVEL%
    goto check_restart
)

where python3 >nul 2>&1
if not errorlevel 1 (
    python3 --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python interpreter failed to start
        pause
        exit /b 1
    )
    python3 -c "import tkinter, cv2" 2>nul
    if errorlevel 1 (
        echo [ERROR] Missing dependencies. Please run scripts\install_dependencies.bat first.
        pause
        exit /b 1
    )
    python3 "%~dp0src\health_monitor.py"
    if errorlevel 1 echo [WARN] Script exited with code %ERRORLEVEL%
    goto check_restart
)

echo [ERROR] Python not found. Tried: python, py, python3
echo [ERROR] Please install Python 3.10+ and add it to PATH.
pause
exit /b 1

:check_restart
if exist "%~dp0restart.flag" (
    del /f /q "%~dp0restart.flag" >nul 2>&1
    echo [INFO] Restart flag detected, restarting...
    goto restart
)

echo [INFO] Tool exited.
pause

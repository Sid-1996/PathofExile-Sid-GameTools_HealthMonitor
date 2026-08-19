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

:: 3a. Prefer python (unified Python 3.13)
where python >nul 2>&1
if not errorlevel 1 (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python interpreter failed to start
        pause
        exit /b 1
    )
    python -c "import PySide6, cv2" 2>nul
    if errorlevel 1 (
        echo [ERROR] Missing dependencies. Please run scripts\install_dependencies.bat first.
        pause
        exit /b 1
    )
    python "%~dp0src\app.py"
    if errorlevel 1 echo [WARN] Script exited with code %ERRORLEVEL%
    goto check_restart
)

:: 3b. Fallback to py launcher (Python 3.13)
where py >nul 2>&1
if not errorlevel 1 (
    py -3.13 --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python interpreter failed to start
        pause
        exit /b 1
    )
    py -3.13 -c "import PySide6, cv2" 2>nul
    if errorlevel 1 (
        echo [ERROR] Missing dependencies. Please run scripts\install_dependencies.bat first.
        pause
        exit /b 1
    )
    py -3.13 "%~dp0src\app.py"
    if errorlevel 1 echo [WARN] Script exited with code %ERRORLEVEL%
    goto check_restart
)

echo [ERROR] Python 3.13 not found. Tried: python, py -3.13
echo [ERROR] Please install Python 3.13 and add it to PATH.
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

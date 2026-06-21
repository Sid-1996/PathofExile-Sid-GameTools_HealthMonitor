@echo off
chcp 65001 >nul
title GameTools Health Monitor

:restart
echo [INFO] 啟動 GameTools Health Monitor...

if exist "%~dp0GameTools_HealthMonitor.exe" (
    start /WAIT "" "%~dp0GameTools_HealthMonitor.exe"
) else if exist "%~dp0dist\GameTools_HealthMonitor.exe" (
    start /WAIT "" "%~dp0dist\GameTools_HealthMonitor.exe"
) else (
    python "%~dp0src\health_monitor.py"
)

if exist "%~dp0restart.flag" (
    del "%~dp0restart.flag"
    echo [INFO] 偵測到重啟標記，重新啟動...
    goto restart
)

echo [INFO] 工具已結束。
pause

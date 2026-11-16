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

REM 建置必須使用專案 .venv（uv sync --locked 依 uv.lock 安裝的鎖定版本）。
REM 找不到 .venv 或缺少 PyInstaller 時直接中止，絕不退回系統 Python，
REM 否則建置結果取決於開發機的環境狀態，無法重現。
set "VENV_PY=.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo [ERROR] 找不到 .venv，無法保證可重現建置。
    echo        請先執行 scripts\install_dependencies.bat
    echo        該腳本會以 uv sync --locked 建立 .venv 並安裝 uv.lock 鎖定版本。
    pause
    exit /b 1
)

call "%VENV_PY%" -c "import PyInstaller" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] .venv 中缺少 PyInstaller，無法建置。
    echo        請先執行 scripts\install_dependencies.bat
    pause
    exit /b 1
)

if exist "build\GameTools_HealthMonitor" (
    attrib -R "build\GameTools_HealthMonitor\*" /S /D >nul 2>nul
    rmdir /s /q "build\GameTools_HealthMonitor" >nul 2>nul
)

call "%VENV_PY%" "tools\build.py"

echo.
if errorlevel 1 (
    echo [WARN] Build failed, retrying once after cleanup...
    if exist "build\GameTools_HealthMonitor" (
        attrib -R "build\GameTools_HealthMonitor\*" /S /D >nul 2>nul
        rmdir /s /q "build\GameTools_HealthMonitor" >nul 2>nul
    )
    call "%VENV_PY%" "tools\build.py"
    echo.
    if errorlevel 1 (
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

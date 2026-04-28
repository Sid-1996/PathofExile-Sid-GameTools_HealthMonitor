@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0.."

echo ========================================
echo  GameTools Health Monitor - 依賴項安裝
echo ========================================
echo.
echo 正在檢查 Python...
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 --version
) else (
    python --version
)

if %errorlevel% neq 0 (
    echo 錯誤: 未找到 Python! 請先安裝 Python 3.10+
    pause
    exit /b 1
)

echo.
echo 正在安裝依賴項...
if not exist "scripts\requirements.txt" (
    echo 錯誤: 找不到 scripts\requirements.txt
    pause
    exit /b 1
)

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -m pip install -r "scripts\requirements.txt"
) else (
    python -m pip install -r "scripts\requirements.txt"
)

if %errorlevel% neq 0 (
    echo.
    echo 錯誤: 依賴項安裝失敗!
    echo 請檢查網路連接或手動運行: pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo ========================================
echo  安裝完成!
echo.
echo 運行方法:
echo   python src/health_monitor.py
echo.
echo 或雙擊 scripts\run_monitor.bat
echo ========================================
pause
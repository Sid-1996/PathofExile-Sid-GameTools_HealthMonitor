@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0.."

echo ========================================
echo  GameTools Health Monitor - 依賴項安裝
echo ========================================
echo.
echo 正在檢查 uv...
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo 錯誤: 未找到 uv! 請先安裝 uv (https://docs.astral.sh/uv/getting-started/installation/)
    pause
    exit /b 1
)

echo 正在檢查 Python 3.13...
where py >nul 2>nul
if %errorlevel%==0 (
    py -3.13 --version
) else (
    python --version
)

if %errorlevel% neq 0 (
    echo 錯誤: 未找到 Python 3.13! 請先安裝 Python 3.13
    pause
    exit /b 1
)

echo.
echo 正在以全域模式安裝依賴項（uv，統一 Python 3.13）...
if not exist "scripts\requirements.txt" (
    echo 錯誤: 找不到 scripts\requirements.txt
    pause
    exit /b 1
)

uv pip install --system -p 3.13 -r "scripts\requirements.txt"

if %errorlevel% neq 0 (
    echo.
    echo 錯誤: 依賴項安裝失敗!
    echo 請檢查網路連接或手動運行: uv pip install --system -p 3.13 -r scripts\requirements.txt
    pause
    exit /b 1
)

echo.
echo ========================================
echo  安裝完成!
echo.
echo 運行方法:
echo   python src/health_monitor.py
echo ========================================
pause

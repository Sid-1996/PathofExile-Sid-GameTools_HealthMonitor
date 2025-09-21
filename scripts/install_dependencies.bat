@echo off
echo ========================================
echo  GameTools Health Monitor - 依賴項安裝
echo ========================================
echo.
echo 正在檢查 Python...
python --version
if %errorlevel% neq 0 (
    echo 錯誤: 未找到 Python! 請先安裝 Python 3.8+
    pause
    exit /b 1
)

echo.
echo 正在安裝依賴項...
pip install -r requirements.txt

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
echo 或者雙擊 src/health_monitor.py
echo ========================================
pause
@echo off
echo ========================================
echo  GameTools Health Monitor - 輕量版啟動器
echo ========================================
echo.
echo 正在檢查 Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 錯誤: 未找到 Python!
    echo 請確保 Python 已安裝並添加到 PATH
    pause
    exit /b 1
)

echo.
echo 正在檢查依賴項...
python -c "import tkinter, cv2, numpy, mss, keyboard, pygetwindow, PIL, pyautogui, psutil, requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo 錯誤: 缺少必要的依賴項!
    echo 請運行 scripts/install_dependencies.bat 安裝依賴項
    pause
    exit /b 1
)

echo.
echo 正在啟動 GameTools Health Monitor...
python ../src/health_monitor.py

pause
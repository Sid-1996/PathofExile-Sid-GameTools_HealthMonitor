@echo off
chcp 65001 >nul
echo ========================================
echo  自動化發布流程 v1.0.7
echo ========================================
echo.

echo [1/4] 清理舊檔案...
call scripts\cleanup.bat
echo.

echo [2/4] 檢查 Git 狀態...
git status
git pull origin master
echo.

echo [3/4] 建構 EXE...
python tools\build.py
if %ERRORLEVEL% neq 0 (
    echo ❌ 建構失敗！
    pause
    exit /b 1
)
echo.

echo [4/4] 準備發布包...
if exist "dist\GameTools_Package\GameTools_HealthMonitor.exe" (
    echo ✅ 發布包已準備完成
    echo 📦 位置: dist\GameTools_Package\
    echo 📁 檔案: GameTools_HealthMonitor_v1.0.7_Final.zip
    echo.
    echo 🚀 請手動上傳到 GitHub Release:
    echo    1. 前往: https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/releases/new
    echo    2. 標籤: v1.0.7
    echo    3. 標題: GameTools_HealthMonitor_v1.0.7
    echo    4. 上傳: dist\GameTools_HealthMonitor_v1.0.7_Final.zip
) else (
    echo ❌ 發布包準備失敗！
    pause
    exit /b 1
)

echo.
echo ✅ 自動化發布流程完成！
echo.
pause

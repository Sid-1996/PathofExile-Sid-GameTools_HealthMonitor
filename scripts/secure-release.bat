@echo off
chcp 65001 >nul
echo ========================================
echo  安全發布流程
echo ========================================
echo.

echo [1/6] 安全檢查...
whoami /groups | findstr /i "Administrators" >nul
if %ERRORLEVEL% neq 0 (
    echo ❌ 需要管理員權限！
    pause
    exit /b 1
)
echo ✅ 管理員權限確認

echo.
echo [2/6] Git 狀態檢查...
git status
if %ERRORLEVEL% neq 0 (
    echo ❌ Git 狀態異常！
    pause
    exit /b 1
)
echo ✅ Git 狀態正常

echo.
echo [3/6] 清理舊檔案...
call scripts\cleanup.bat
echo.

echo [4/6] 依賴完整性檢查...
python -c "import cv2, numpy, PIL, mss, keyboard, pygetwindow, pyautogui, psutil, requests; print('✅ 所有依賴正常')" 2>nul
if %ERRORLEVEL% neq 0 (
    echo ❌ 依賴檢查失敗！
    pause
    exit /b 1
)
echo ✅ 依賴完整性確認

echo.
echo [5/6] 建構 EXE...
python tools/build.py
if %ERRORLEVEL% neq 0 (
    echo ❌ 建構失敗！
    pause
    exit /b 1
)
echo ✅ 建構成功

echo.
echo [6/6] 安全驗證...
if exist "dist\GameTools_Package\GameTools_HealthMonitor.exe" (
    for %%f in ("dist\GameTools_Package\GameTools_HealthMonitor.exe") do (
        if %%~zf GTR 100000000 (
            echo ❌ EXE 檔案大小異常：%%~zf bytes
            pause
            exit /b 1
        )
    )
    echo ✅ 檔案大小正常
    echo ✅ 安全驗證通過
    echo.
    echo 🚀 安全發布包已準備完成
    echo 📦 位置: dist\GameTools_Package\
    echo 📁 檔案: GameTools_HealthMonitor_v%APP_VERSION%_Final.zip
    echo.
    echo 🔒 安全提醒：
    echo   - 此版本已通過基本安全檢查
    echo   - 建議在上傳前進行病毒掃描
    echo   - 請確認發布目標正確
) else (
    echo ❌ 發布包準備失敗！
    pause
    exit /b 1
)

echo.
echo ✅ 安全發布流程完成！
echo.
pause

@echo off
chcp 65001 >nul
echo ========================================
echo  清理建構檔案和臨時檔案
echo ========================================
echo.

echo 清理 PyInstaller 建構檔案...
if exist "build\pyinstaller_work_*" (
    for /d %%d in ("build\pyinstaller_work_*") do (
        echo 刪除: %%d
        rmdir /s /q "%%d"
    )
)

echo 清理舊的發布包...
if exist "dist\GameTools_HealthMonitor_v1.0.7_*.zip" (
    del /q "dist\GameTools_HealthMonitor_v1.0.7_*.zip"
    echo 已刪除舊的發布包
)

echo 清理臨時檔案...
if exist ".tmp.driveupload" (
    rmdir /s /q ".tmp.driveupload"
    echo 已清理臨時上傳目錄
)

echo.
echo ✅ 清理完成！
echo.
pause

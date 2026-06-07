@echo off
chcp 65001 >nul
echo ========================================
echo 審核後推送
echo ========================================
echo.

echo [1/3] 執行推送前審核...
call scripts\pre-push-check.bat
if %ERRORLEVEL% neq 0 (
    echo ❌ 審核失敗，推送中止！
    pause
    exit /b 1
)

echo [2/3] 推送到 GitHub...
git push origin master
if %ERRORLEVEL% neq 0 (
    echo ❌ 推送失敗！
    pause
    exit /b 1
)

echo [3/3] 推送成功！
echo ✅ 已安全推送到 GitHub
echo 📋 推送摘要：
echo   - 審核檢查：通過
echo   - 安全檢查：通過
echo   - 文檔完整性：確認
echo.
echo 🌐 查看推送結果：https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor
echo.
pause

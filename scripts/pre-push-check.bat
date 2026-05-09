@echo off
chcp 65001 >nul
echo ========================================
echo 推送前審核檢查 v1.0.7
echo ========================================
echo.

echo [1/6] 檢查 Git 狀態...
git status
if %ERRORLEVEL% neq 0 (
    echo ❌ Git 狀態檢查失敗！
    pause
    exit /b 1
)

echo [2/6] 檢查未提交的變更...
git diff --cached --name-only
if %ERRORLEVEL% neq 0 (
    echo ❌ 變更檢查失敗！
    pause
    exit /b 1
)

echo [3/6] 檢查本地化檔案是否意外包含...
if exist "LOCAL_DEVELOPMENT.md" (
    echo ⚠️  警告：LOCAL_DEVELOPMENT.md 應該在 .gitignore 中
    echo 請確認此檔案是否需要推送
    choice /M "是否繼續推送？" /C "繼續" /C "取消"
    if errorlevel 2 (
        echo ❌ 用戶取消推送
        pause
        exit /b 1
    )
)

echo [4/6] 檢查敏感資訊...
git log --oneline -5 | findstr /i "password\|secret\|key\|token\|backdoor"
if %ERRORLEVEL% equ 0 (
    echo ❌ 檢測到敏感資訊在最近的提交中！
    echo 請檢查並清理敏感資訊
    pause
    exit /b 1
)

echo [5/6] 檢查檔案大小異常...
if exist "dist\GameTools_Package\*.exe" (
    for %%f in (dist\GameTools_Package\*.exe) do (
        if %%~zf GTR 100000000 (
            echo ❌ 檔案大小異常：%%~zf bytes
            echo 請檢查是否有惡意注入
            pause
            exit /b 1
        )
    )
    echo ✅ 檔案大小正常
)

echo [6/6] 檢查開源文檔完整性...
if not exist "README.md" (
    echo ❌ 缺少 README.md！
    pause
    exit /b 1
)
if not exist "CHANGELOG.md" (
    echo ❌ 缺少 CHANGELOG.md！
    pause
    exit /b 1
)
if not exist "LICENSE" (
    echo ❌ 缺少 LICENSE！
    pause
    exit /b 1
)

echo.
echo ✅ 所有檢查通過！
echo 🚀 準備推送到 GitHub
echo.
echo 📋 檢查摘要：
echo   - Git 狀態：正常
echo   - 敏感資訊：無
echo   - 檔案大小：正常
echo   - 開源文檔：完整
echo.
pause

@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0.."

echo ========================================
echo  GameTools Health Monitor - 依賴項安裝
echo  主路徑: uv sync --locked（依 uv.lock 安裝鎖定版本，自動建 .venv）
echo  備援:   scripts\requirements.txt（未鎖定版本，無法保證完全可重現）
echo ========================================
echo.

where uv >nul 2>nul
if errorlevel 1 goto :no_uv

echo 正在檢查 Python 3.13...
where py >nul 2>nul
if not errorlevel 1 goto :use_py
call python --version
if errorlevel 1 goto :no_py
goto :check_lock

:use_py
call py -3.13 --version
if errorlevel 1 goto :no_py

:check_lock
echo.
if not exist "uv.lock" goto :no_lock

echo 正在以 uv sync --locked 建立 .venv 並安裝鎖定版本...
call uv sync --locked
if errorlevel 1 goto :sync_failed

echo.
echo ========================================
echo  安裝完成（uv sync --locked，.venv 已建立）。
echo.
echo 運行方法:
echo   uv run python src/app.py
echo   或 Run.bat（會優先偵測 .venv）
echo ========================================
pause
exit /b 0

:no_uv
echo [ERROR] 找不到 uv，請先安裝:
echo        https://docs.astral.sh/uv/getting-started/installation/
pause
exit /b 1

:no_py
echo [ERROR] 找不到 Python 3.13，請先安裝 Python 3.13:
echo        https://www.python.org/downloads/
pause
exit /b 1

:no_lock
echo [ERROR] 找不到 uv.lock
echo        uv.lock 是受 Git 追蹤的依賴鎖定檔，缺少它就無法保證可重現安裝。
echo        請重新取得完整原始碼（git clone 或 git pull）後再試。
pause
exit /b 1

:sync_failed
echo.
echo [ERROR] uv sync --locked 失敗，請勿忽略此錯誤。
echo        uv.lock 是鎖定檔，失敗代表鎖定版本無法安裝。
echo        若確實要走備援路徑（未鎖定版本，無法保證完全可重現），請手動執行:
echo          uv pip install --system -p 3.13 -r scripts\requirements.txt
pause
exit /b 1

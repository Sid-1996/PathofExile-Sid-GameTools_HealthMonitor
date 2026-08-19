# 技術規格

## 環境

- Python 3.13（開發機與目標）；`pyproject.toml` target-version `py310`（相容下限）
- 套件管理：**uv 全域環境**（無專案 venv）——`uv pip install --system -p 3.13`，開發機 `python` 指令統一為 3.13
- 打包：PyInstaller onedir（`tools/build.py`，exe + `_internal/` 樹）
- Lint/格式：ruff（line-length 200、select E/F/W/C90、mccabe 20）
- 型別檢查：pyright（`src/app.py` + `src/qt/`）
- 測試：pytest（`tests/` + 純邏輯模組 `__main__` self-check）

## 主要依賴

| 依賴 | 用途 |
|---|---|
| OpenCV (cv2) | 影像分析、HSV 轉換 |
| numpy | 影像陣列處理 |
| mss | 截圖 |
| Pillow (PIL) | 影像繪製/預覽 |
| keyboard | 全域熱鍵（F12） |
| psutil | 子進程管理 |
| pyautogui / pygetwindow | 按鍵/視窗控制 |
| pyperclip | F5 返回藏身處剪貼簿指令 |
| requests | 版本檢查、下載 |
| PySide6 + PySide6-Fluent-Widgets (qfluentwidgets) | GUI（Qt 原生 + Fluent 深色主題） |
| pywin32 (win32gui) | 視窗/前景視窗偵測 |

## 監控分析

- `monitor_analyzer.analyze_health/mana`：18 個等距偵測點 → 有顏色像素比例 → 百分比
- 滿血/滿魔偵測：3 條規則（下半部比例、核心區比例、全部偵測點）
- 觸發：優先最低百分比設定，支援 cooldown 與 multi-trigger

## Config

- `src/health_monitor_config.json`（runtime 產生，勿當 source）
- 儲存前自動 `.backup`，異常時從備份恢復

## 更新引擎（updater_core.py）

移植自 ocr-trigger-clicker `core/12_updater.py`，**目前無 delta 支援**（只整包 ZIP）。

- `_parse_version()`：`1.2.2-beta` → `(1,2,2,0)`，stable `1.2.2` → `(1,2,2,1)`（stable 勝 pre-release）
- `check_for_update()`：抓 raw `latest_version.txt`，`allow_prerelease` 時併比 pre-release 檔
- `download_update()`：stream 下載 → 解整棵 onedir 樹 → 驗 MZ header → 回傳路徑
- `apply_update()`：啟動 `updater.exe` 背景整樹交換（staging→swap→rollback）

## 已知限制

見 AGENTS.md「Known Issues」：PrintWindow 全黑、mss/dxcam 截合成桌面。

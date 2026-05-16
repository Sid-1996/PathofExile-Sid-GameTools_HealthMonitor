---
description: Summary of AI work completed for project understanding
---

# AI 工作報告

## 任務

分析 Path of Exile 自動化工具專案結構與開發者習慣，並撰寫 AI 技能文檔供日後快速理解。

## 完成工作

### 1. 專案結構分析

- **主程式**: `src/health_monitor.py`（10,554 行單一檔案）
- **雙源目錄**: `src/`（主要編輯區）與 `src for DEVELOPER/`（相容層）
- **建構系統**: `tools/build.py` 使用 PyInstaller 打包
- **一鍵腳本**: `scripts/` 目錄包含安裝、執行、建構、測試腳本
- **文檔**: 雙語文檔（中文 + 英文）在 `docs/` 目錄

### 2. 開發者習慣識別

- **版本管理**: `APP_VERSION` 在 `tools/build.py`（目前 "1.0.7"）
- **編碼規範**: snake_case 命名，單體架構設計
- **配置管理**: JSON 格式，原子性保存（.tmp 檔案模式）
- **執行緒模式**: 監控與連段系統使用獨立執行緒
- **語言支援**: 雙語 UI（中文預設 + 英文）
- **錯誤處理**: 優雅降級（OpenCV 可選）

### 3. AI 技能文檔創建

**位置**: `.windsurf/workflows/project-understanding.md`

**內容涵蓋**:

- 專案概述與技術堆疊
- 標準目錄結構（編輯規則：僅編輯 `src/`）
- 開發者習慣與慣例
- 關鍵工作流程（安裝 → 執行 → 建構 → 測試）
- 建構系統細節（PyInstaller 打包規則）
- 常見陷阱與解決方案
- 快速參考（檔案位置、熱鍵綁定、配置結構）
- 架構模式（影像處理、執行緒模型、狀態管理）
- 未來重構建議

### 4. Markdown 格式修正

- 新增標題周圍空白行
- 新增列表周圍空白行
- 新增程式碼區塊周圍空白行
- 新增程式碼語言標記（batch, json, text）
- 移除重複空白行

### 5. 新增技能計時器模組（skill_timer.py）

- **新增檔案**: `src/skill_timer.py`
- **功能**: 循環計時自動釋放技能按鍵
- **支援單鍵**（Q/W/E/R）**和組合鍵**（ctrl+1, shift+Q）
- 毫秒精度，最低 50ms
- 每個技能槽獨立 `threading.Timer` 迴圈，互不干擾
- **接入點**: `create_combo_tab()` 底部
- **存檔**: 整合進現有 `save_config` / `load_config`
- **關閉**: `on_closing` 自動 `stop_all()`
- **語言**: 支援雙語，透過 `update_combo_tab_language()` → `refresh_language()` 切換

**語言包新增 key**（`language_packs.json` zh-tw + en）:

```
skill_timer_title, skill_timer_enable, skill_timer_slot,
skill_timer_modifier, skill_timer_key, skill_timer_interval,
skill_timer_status, skill_timer_running, skill_timer_stopped,
skill_timer_start_all, skill_timer_stop_all, skill_timer_error,
skill_timer_log_start, skill_timer_log_stop,
skill_timer_log_all_start, skill_timer_log_all_stop,
skill_timer_no_pyautogui
```

**health_monitor.py 修改點**:

- `import`: 加入 `from skill_timer import SkillTimerModule`
- `create_combo_tab()`: 末端建立 `self.skill_timer`
- `on_closing()`: 加入 `self.skill_timer.stop_all()`
- `save_combo_config()`: 加入 `skill_timer` 存檔
- `load_combo_config()`: 加入 `skill_timer` 載入
- `update_combo_tab_language()`: 加入 `self.skill_timer.refresh_language()`

## 關鍵發現

**重要規則**:

- 永遠編輯 `src/` 目錄，不要編輯 `src for DEVELOPER/`
- 建構腳本會自動將 `src/` 複製到 `src for DEVELOPER/`
- 版本號需在 `tools/build.py` 和 `src/health_monitor.py` 同步更新

**打包規則**:

- 最終套件必須包含：GameTools_HealthMonitor.exe, auto_click.exe, language_packs.json, 使用說明.md, 啟動工具.bat, README.txt
- 排除：screenshots/, health_monitor_config.json（使用者生成）
- **新增**: `skill_timer.py` 需納入打包（`tools/build.py` 的 `datas` 或直接放 `src/`）

**常見問題**:

- PyInstaller 快取鎖定（WinError 5）：清除 `build/GameTools_HealthMonitor` 目錄
- 雙源目錄不同步：建構腳本自動處理
- 版本不一致：檢查兩處版本號格式（build.py 用 "1.0.7"，health_monitor.py 用 "v1.0.7"）

## 文檔位置

- **AI 技能文檔**: `.windsurf/workflows/project-understanding.md`
- **專案結構**: `PROJECT_STRUCTURE.md`
- **開發者手冊**: `DEVELOPER_HANDBOOK.md`（908 行詳細技術文檔）
- **AI 快速指南**: `AGENTS.md`

## 完成狀態

✅ 專案結構分析完成
✅ 開發者習慣識別完成
✅ AI 技能文檔創建完成
✅ Markdown 格式修正完成
✅ skill_timer.py 模組開發與整合完成

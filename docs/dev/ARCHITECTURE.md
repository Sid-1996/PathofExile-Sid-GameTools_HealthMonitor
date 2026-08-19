# 系統架構

## 總覽

Windows 上的 Path of Exile 日常自動化工具：健康/魔力監控、技能連招、背包整理、自動點擊。

```text
src/
├── app.py                  # Qt 入口（PySide6 + qfluentwidgets，取代 tkinter 世代）
├── qt/                     # GUI 層（main_window + 7 tabs：status/monitor/inventory/combo/help/version/about）
├── monitor_analyzer.py     # 健康/魔力 HSV 分析、觸發邏輯（純邏輯）
├── capture_utils.py        # 截圖、mss singleton
├── image_utils.py          # 影像繪製、resize、預覽
├── inventory_utils.py      # 背包格分析、物品偵測（純邏輯）
├── config_manager.py       # JSON config 讀寫 + 備份
├── language_system.py      # 雙語字串查詢
├── auto_click_manager.py   # 自動點擊（AHK）
├── usage_tracker.py        # 使用時間統計
├── window_key_sender.py    # 視窗聚焦按鍵發送
├── updater_core.py         # 更新引擎（版本檢查、下載、套用）
└── _version.py             # 版本唯一事實來源
```

## 執行流程

1. `app.py` 啟動 → 載入 config + 語言包 → `MainWindow`（FluentWindow）建 7 個 tabs
2. 監控 loop：截圖 → `monitor_analyzer` HSV 分析 → 低於閾值觸發按鍵
3. 關閉：`closeEvent → _shutdown()`（敏感路徑，見 AGENTS.md；F12 走 `close_app()`）

## 相依方向

```text
app.py ──→ qt/main_window.py ──→ qt/tab_*.py ──→ 純邏輯模組（monitor_analyzer / capture_utils /
            inventory_utils / config_manager / language_system / updater_core / utils …）
```

純邏輯模組（`monitor_analyzer`、`inventory_utils`、`config_manager`、`updater_core._parse_version`）不含 tkinter，可直接單元測試。

## 更新流程

- 版本檢查：dual-track（`latest_version.txt` / pre-release 檔），見 AGENTS.md
- 下載：整包 ZIP → 解出主 EXE + `updater.exe` → 驗 MZ header
- 套用：`updater.exe` 背景整樹交換（onedir：exe + `_internal/`，含 rollback；delta 為下一階段）

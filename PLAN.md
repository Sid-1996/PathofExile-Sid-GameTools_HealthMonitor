# 水平拆分計畫

## 目標

將 `health_monitor.py`（~10,500 行）逐步拆分為專門模組，以提升可維護性與可測試性。

## 拆分原則

- **純函式優先**：不依賴 `self`、不依賴 tkinter 的函式優先抽出
- **一層深**：僅抽一層 module，不做 `engine/` 子目錄
- **不改變行為**：每次抽出後執行 `ruff` + `py_compile` 驗證

## 執行順序

### Phase 1 ✅ `src/image_utils.py`
**狀態：已完成**
- `draw_scale_lines`、`resize_and_center_image`、`draw_health_indicator`、`draw_mana_indicator`
- `get_region_text`、`get_mana_region_text`、`get_interface_ui_region_text`
- 減少 `health_monitor.py` ~220 行

### Phase 2 ⏳ `src/monitor_analyzer.py`
**候選函式（約 400 行）：**
- `analyze_health` — 血量分析（讀取 self 屬性，需傳入參數）
- `is_health_color` — 紅色判定（純函式？需確認）
- `get_health_color_ratio`
- `analyze_mana` — 魔力分析
- `is_mana_color` — 藍色判定（純函式）
- `get_mana_color_ratio`
- `get_main_color` — 主要顏色判定（純函式）
- `check_triggers` — 觸發條件檢查
- `trigger_actions` — 觸發動作執行
- `_interruptible_sleep` — 可中斷睡眠

### Phase 3 🔲 `src/capture_utils.py`
**候選函式（約 150 行）：**
- 所有 `with _mss_singleton as sct:` 區塊中通用的截圖邏輯
- 遊戲視窗截圖 helper
- 區域截圖 helper

### Phase 4 🔲 `src/hotkey_manager.py`
**候選函式（約 300 行）：**
- `setup_hotkeys` / `remove_hotkeys`
- combo hotkey 管理
- F-key 註冊/清理

### Phase 5 🔲 `src/inventory_utils.py`
**候選函式（約 200 行）：**
- `should_clear_inventory` — 背包清理判定
- `find_inventory_items` — 尋物品位置
- `clear_inventory_item` — 逐一清物品

## 驗收標準

- 每個 Phase 完成後：`ruff check src/ --statistics` 無新增錯誤
- `python -c "import py_compile; py_compile.compile('src/health_monitor.py')"` 通過
- 功能無回歸（啟動 + 主要功能路徑正常）

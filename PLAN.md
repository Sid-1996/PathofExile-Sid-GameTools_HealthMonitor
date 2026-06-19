# 水平拆分計畫 — 完成報告

## 目標

將 `health_monitor.py`（~10,500 行）逐步拆分為專門模組。

## 拆分原則

- **純函式優先**：不依賴 `self`、不依賴 tkinter 的函式優先抽出
- **一層深**：僅抽一層 module，不做 `engine/` 子目錄
- **不改變行為**：每次抽出後執行 `ruff` + `py_compile` 驗證

## 執行結果

| Phase | 模組 | 行數 | 函式數 | 狀態 |
|---|---|---|---|---|
| 1 | `image_utils.py` | 203 | 7 | ✅ |
| 2 | `monitor_analyzer.py` | 349 | 10 | ✅ |
| 3 | `capture_utils.py` | 72 | 5 | ✅ |
| 4 | `hotkey_manager.py` | — | — | ⏭️ 跳過（程式碼過度耦合） |
| 5 | `inventory_utils.py` | 95 | 3 | ✅ |
| **合計** | | **719** | **25** | |

## 最終成果

| 指標 | 拆分前 | 拆分後 |
|---|---|---|
| `health_monitor.py` 行數 | ~10,500 | **9,841** |
| Ruff 錯誤 | 100（含 45 個可修復） | **11**（僅 C901 複雜函式） |
| 獨立模組數 | 6 | **10** |
| F821 undefined-name | 5 | **0** |
| E722 bare-except | 39 | **0** |
| E402 import-order | 18 | **0** |

## 未拆分原因

- **hotkey_manager.py**：熱鍵註冊/清理程式碼僅 ~50 行且散佈各處，每個 call site 深度依賴 self 回呼，抽出反而增加複雜度
- **clear_inventory_item** (~290 行)：高度耦合 tkinter 與 self 狀態，抽出需傳入 10+ 參數，不符「純函式優先」原則
- **test_inventory_clearing** (~200 行)：大量 messagebox／self.get_text／self 方法呼叫，不適合抽出

## 後續方向

若需進一步減少 `health_monitor.py`，建議方向：
1. 將 `change_language` + `update_ui_text` 等 UI 更新邏輯抽出為 `ui_text_manager.py`
2. 將 `load_config` / `save_config` 中 UI 相關部分（非 config_manager 處理的）抽出
3. 將 `test_inventory_clearing` 等測試輔助功能抽出

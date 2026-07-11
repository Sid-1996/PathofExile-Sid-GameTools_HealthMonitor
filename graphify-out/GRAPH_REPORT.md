# Graph Report - C:\Code play first\PathofExile-Sid-GameTools_HealthMonitor  (2026-07-12)

## Corpus Check
- Corpus is ~46,356 words - fits in a single context window. You may not need a graph.

## Summary
- 612 nodes · 1150 edges · 37 communities (23 shown, 14 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 137 edges (avg confidence: 0.75)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- AGPL-3.0 License / AppState Shared State
- health_monitor.py / emergency_exit_handl
- ComboTab / .create_combo_set_frame_horiz
- HealthMonitor / .center_window() / .chan
- InventoryTab / .calculate_safe_gui_posit
- Misc / 送鍵 → 排下一次；在 lock 外送鍵避免死鎖 / 啟動迴圈，回
- config_manager.py / ConfigManager / .bac
- Path / updater_core.py / apply_update()
- build.py / GameToolBuilder / ._add_binar
- .monitor_health() / monitor_analyzer.py 
- MonitorTab / .add_setting_new() / .cance
- on_close() / 從 GitHub API 取 release note
- capture_utils.py / build_game_window_mon
- .check_game_window_minimized() / .is_glo
- image_utils.py / draw_health_indicator()
- language_system.py / get_app_dir() / get
- WindowKeySender / .activate_game_window(
- .adjust_window_for_current_tab() / .adju
- Any / app_state.py / AppState
- CustomMessageBox / .ask_yes_no() / ._bui
- auto_click_manager.py / AutoClickManager
- capture_region_to_cv2() / calculate_inve
- custom_dialogs.py / 自訂對話框模組 提供動態尺寸調整的本地化
- inventory_utils.py / find_inventory_item
- .cancel_interface_ui_selection() / .end_
- .add_status_message() / .finish_startup_
- .check_gui_overlap_with_inventory() / .c
- ._draw_exclusion_overlay() / ._on_previe
- .create_child_window() / .create_setting
- ._get_game_window_rect() / ._hide_global
- HelpTab / .create_help_tab() / .create_i
- _MssSingleton / .__enter__() / .__exit__
- .is_interface_ui_visible() / 檢查介面UI是否可見（

## God Nodes (most connected - your core abstractions)
1. `InventoryTab` - 86 edges
2. `HealthMonitor` - 85 edges
3. `MonitorTab` - 46 edges
4. `AI Contributor Quick Guide (AGENTS.md)` - 29 edges
5. `ComboTab` - 24 edges
6. `VersionTab` - 21 edges
7. `Tooltip` - 19 edges
8. `health_monitor.py Main Application` - 19 edges
9. `ConfigManager` - 18 edges
10. `SkillTimerModule` - 18 edges

## Surprising Connections (you probably didn't know these)
- `GameTools Health Monitor Project` --conceptually_related_to--> `Path of Exile`  [EXTRACTED]
  AGENTS.md → README.md
- `GitHub Issue Template: Bug Report` --references--> `GameTools Health Monitor Project`  [EXTRACTED]
  .github/ISSUE_TEMPLATE/bug_report.md → AGENTS.md
- `GitHub Issue Template: Feature Request` --references--> `GameTools Health Monitor Project`  [EXTRACTED]
  .github/ISSUE_TEMPLATE/feature_request.md → AGENTS.md
- `GitHub FUNDING.yml` --references--> `GameTools Health Monitor Project`  [EXTRACTED]
  .github/FUNDING.yml → AGENTS.md
- `latest_version.txt (v1.2.1)` --references--> `GameTools Health Monitor Project`  [EXTRACTED]
  latest_version.txt → AGENTS.md

## Import Cycles
- None detected.

## Communities (37 total, 14 thin omitted)

### Community 0 - "AGPL-3.0 License / AppState Shared State"
Cohesion: 0.08
Nodes (57): AGPL-3.0 License, AppState Shared State Module, Auto-Click Integration, In-App Auto-Update System, AutoHotkey, capture_utils Module, CI Lint & Type Check Workflow, Commitizen (+49 more)

### Community 1 - "health_monitor.py / emergency_exit_handl"
Cohesion: 0.07
Nodes (21): emergency_exit_handler(), global_exception_handler(), 緊急退出處理器 - 確保在任何異常情況下都能關閉應用程序, skill_timer.py 循環計時自動釋放技能模組 ──────────────────────────────────────────────────, AboutTab, tab_version.py 版本檢查分頁 — 版本比對、程式內下載更新、重啟套用 ──────────────────────────────────────, UsageTracker, emergency_cleanup() (+13 more)

### Community 2 - "ComboTab / .create_combo_set_frame_horiz"
Cohesion: 0.08
Nodes (4): ComboTab, StatusTab, 可重複使用的 Tooltip：懸浮 widget 顯示說明文字，支援延遲, Tooltip

### Community 3 - "HealthMonitor / .center_window() / .chan"
Cohesion: 0.10
Nodes (4): HealthMonitor, Wait for monitor thread exit without freezing the GUI., 處理多鍵序列，按順序按下每個鍵 - 血魔監控專用, Delegate to inventory_tab - wrapper for backward compatibility.

### Community 5 - "Misc / 送鍵 → 排下一次；在 lock 外送鍵避免死鎖 / 啟動迴圈，回"
Cohesion: 0.13
Nodes (9): Misc, 送鍵 → 排下一次；在 lock 外送鍵避免死鎖, 啟動迴圈，回傳 False 代表設定不合法, 建立一個 ttk.LabelFrame（self.frame），     可直接 pack / grid 進任何父容器。, parent    : 父容器         max_slots : 最多幾個技能槽（上限 _MAX_SLOTS）         on_log    :, 每個 SkillSlot 持有自己的 tk 變數（直接綁定 UI）     和一個 threading.Timer 遞迴迴圈。, root：任何 tk widget，讓 StringVar/IntVar 正確綁到主 Tcl 解釋器。, SkillSlot (+1 more)

### Community 6 - "config_manager.py / ConfigManager / .bac"
Cohesion: 0.11
Nodes (7): ConfigManager, get_config_manager(), get_config_value(), load_config(), 配置管理模組 處理應用程式的設定載入、保存、註冊表操作等功能, save_config(), set_config_value()

### Community 7 - "Path / updater_core.py / apply_update()"
Cohesion: 0.14
Nodes (20): Path, apply_update(), check_for_update(), _clean_stale_temp_dirs(), current_exe_path(), download_update(), is_frozen(), _parse_version() (+12 more)

### Community 8 - "build.py / GameToolBuilder / ._add_binar"
Cohesion: 0.15
Nodes (10): GameToolBuilder, main(), Collect binary dependencies (DLLs, pyds), Move built exe into package directory, Build updater_main.py → updater.exe (lightweight, no GUI deps)., Create installation package., Return the first existing path from candidates, else None., Run full build pipeline (+2 more)

### Community 9 - ".monitor_health() / monitor_analyzer.py "
Cohesion: 0.13
Nodes (20): analyze_health(), analyze_mana(), check_triggers(), get_health_color_ratio(), get_main_color(), get_mana_color_ratio(), interruptible_sleep(), is_health_color() (+12 more)

### Community 11 - "on_close() / 從 GitHub API 取 release note"
Cohesion: 0.12
Nodes (3): on_close(), 從 GitHub API 取 release notes（僅在有新版時觸發）, VersionTab

### Community 12 - "capture_utils.py / build_game_window_mon"
Cohesion: 0.17
Nodes (8): build_game_window_monitor(), capture_region_to_pil(), Capture utility functions extracted from health_monitor.py., save_screenshot(), draw_scale_lines(), Draw 10 equally-spaced horizontal scale lines on a preview image.      Args:, Resize an image proportionally to fit a target preview size.      The image is, resize_and_center_image()

### Community 13 - ".check_game_window_minimized() / .is_glo"
Cohesion: 0.17
Nodes (5): 檢查遊戲視窗是否最小化，如果最小化則顯示提醒視窗, Stop monitoring without blocking the Tk main thread., F9: 全域暫停開關 - 暫停/恢復所有熱鍵功能（線程安全）, 檢查是否應該保持GUI在最上方（根據用戶設定）, 管理視窗層級系統         層級從高到低: CHILD > SETTINGS > MAIN         - CHILD: 子視窗（提示視窗、測試視

### Community 14 - "image_utils.py / draw_health_indicator()"
Cohesion: 0.15
Nodes (11): draw_health_indicator(), draw_mana_indicator(), get_interface_ui_region_text(), get_mana_region_text(), get_region_text(), Image utility functions for Path of Exile game tools.  This module contains im, Draw a mana percentage indicator line and label on a preview image.      Args:, Format the health bar region configuration as a display string.      Args: (+3 more)

### Community 15 - "language_system.py / get_app_dir() / get"
Cohesion: 0.17
Nodes (9): get_app_dir(), get_current_language(), get_language_manager(), get_text(), LanguageManager, load_language_packs(), 語言系統模組 處理多語言支援、語言包載入、UI文字更新等功能, 獲取應用程式目錄，適用於開發環境和打包後的exe (+1 more)

### Community 18 - "Any / app_state.py / AppState"
Cohesion: 0.15
Nodes (3): Any, AppState, Shared application state context.      Holds cross-cutting state (monitoring,

### Community 20 - "auto_click_manager.py / AutoClickManager"
Cohesion: 0.21
Nodes (3): AutoClickManager, 自動點擊循環 - 模擬AHK的while循環行為, 啟動AHK自動點擊腳本 - 支援EXE版本優先

### Community 21 - "capture_region_to_cv2() / calculate_inve"
Cohesion: 0.23
Nodes (3): capture_region_to_cv2(), calculate_inventory_grid_positions(), 計算背包格子位置 (5x12 布局，總共60個格子)

### Community 22 - "custom_dialogs.py / 自訂對話框模組 提供動態尺寸調整的本地化"
Cohesion: 0.24
Nodes (5): 自訂對話框模組 提供動態尺寸調整的本地化對話框，支援長文本顯示, 設置自訂對話框為預設 messagebox, setup_custom_messagebox(), _validate_float_input(), _validate_int_input()

### Community 23 - "inventory_utils.py / find_inventory_item"
Cohesion: 0.29
Nodes (6): find_inventory_items(), Inventory utility functions for Path of Exile game tools.  This module contain, 檢查背包是否需要清空 - 檢查60個格子，可選擇跳過指定格子和之前的格子, should_clear_inventory(), 清空背包物品 - 動態辨識版：每次點擊後重新辨識，適應大物品清空多格的情況          包含智能跳過機制：當遇到無法存放進倉庫的物品時，自動跳過該物品, 更新背包預覽，顯示60個格子的狀態和處理進度 - 優化版本

## Knowledge Gaps
- **15 isolated node(s):** `Path of Exile`, `mss (Screenshot Library)`, `NumPy`, `Pillow`, `psutil` (+10 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `HealthMonitor` connect `HealthMonitor / .center_window() / .chan` to `HelpTab / .create_help_tab() / .create_i`, `health_monitor.py / emergency_exit_handl`, `ComboTab / .create_combo_set_frame_horiz`, `InventoryTab / .calculate_safe_gui_posit`, `Misc / 送鍵 → 排下一次；在 lock 外送鍵避免死鎖 / 啟動迴圈，回`, `.monitor_health() / monitor_analyzer.py `, `MonitorTab / .add_setting_new() / .cance`, `on_close() / 從 GitHub API 取 release note`, `.check_game_window_minimized() / .is_glo`, `WindowKeySender / .activate_game_window(`, `.adjust_window_for_current_tab() / .adju`, `Any / app_state.py / AppState`, `CustomMessageBox / .ask_yes_no() / ._bui`, `auto_click_manager.py / AutoClickManager`, `.add_status_message() / .finish_startup_`, `.create_child_window() / .create_setting`, `._get_game_window_rect() / ._hide_global`?**
  _High betweenness centrality (0.423) - this node is a cross-community bridge._
- **Why does `InventoryTab` connect `InventoryTab / .calculate_safe_gui_posit` to `._capture_and_prepare_f3_gui() / ._hide_`, `ComboTab / .create_combo_set_frame_horiz`, `HealthMonitor / .center_window() / .chan`, `.is_interface_ui_visible() / 檢查介面UI是否可見（`, `CustomMessageBox / .ask_yes_no() / ._bui`, `capture_region_to_cv2() / calculate_inve`, `custom_dialogs.py / 自訂對話框模組 提供動態尺寸調整的本地化`, `inventory_utils.py / find_inventory_item`, `.cancel_interface_ui_selection() / .end_`, `.check_gui_overlap_with_inventory() / .c`, `.cancel_inventory_selection() / .cancel_`, `.clear_all_coordinates() / .save_pickup_`, `._draw_exclusion_overlay() / ._on_previe`?**
  _High betweenness centrality (0.237) - this node is a cross-community bridge._
- **Why does `MonitorTab` connect `MonitorTab / .add_setting_new() / .cance` to `ComboTab / .create_combo_set_frame_horiz`, `HealthMonitor / .center_window() / .chan`, `capture_utils.py / build_game_window_mon`, `image_utils.py / draw_health_indicator()`, `CustomMessageBox / .ask_yes_no() / ._bui`, `custom_dialogs.py / 自訂對話框模組 提供動態尺寸調整的本地化`?**
  _High betweenness centrality (0.119) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `InventoryTab` (e.g. with `HealthMonitor` and `.create_widgets()`) actually correct?**
  _`InventoryTab` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `HealthMonitor` (e.g. with `AppState` and `AutoClickManager`) actually correct?**
  _`HealthMonitor` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `MonitorTab` (e.g. with `HealthMonitor` and `.create_widgets()`) actually correct?**
  _`MonitorTab` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `ComboTab` (e.g. with `HealthMonitor` and `.create_widgets()`) actually correct?**
  _`ComboTab` has 4 INFERRED edges - model-reasoned connections that need verification._
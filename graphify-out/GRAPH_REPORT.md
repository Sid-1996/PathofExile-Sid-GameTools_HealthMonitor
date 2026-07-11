# Graph Report - C:\Code play first\PathofExile-Sid-GameTools_HealthMonitor  (2026-07-12)

## Corpus Check
- Corpus is ~46,198 words - fits in a single context window. You may not need a graph.

## Summary
- 628 nodes · 1122 edges · 42 communities (26 shown, 16 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 128 edges (avg confidence: 0.73)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Auto Click & App State
- Combo/Skill Combo
- Skill Timer
- Inventory Tab UI
- Health Monitor Main
- About Tab
- Usage Tracker
- Config Management
- Build System
- Health/Mana Analysis
- Window Management
- Monitor Tab
- Version Updates
- Language System
- Release Process
- Update Core
- Settings & Dynamic UI
- App State
- Custom Dialogs
- Inventory Grid
- Image Utilities
- Auto Click Manager
- Capture Utilities
- App Startup & Hotkeys
- Health/Mana Display
- Inventory Detection
- UI Selection
- GUI Overlap Detection
- Inventory Preview
- Toast Notifications
- Settings Validation
- Custom Dialogs Module
- Interface Region Selection
- UI Visibility Check
- Hotkey: F10
- Hotkey: F5
- Skill Timer

## God Nodes (most connected - your core abstractions)
1. `InventoryTab` - 86 edges
2. `HealthMonitor` - 85 edges
3. `MonitorTab` - 46 edges
4. `ComboTab` - 24 edges
5. `health_monitor.py` - 22 edges
6. `VersionTab` - 21 edges
7. `Tooltip` - 19 edges
8. `ConfigManager` - 18 edges
9. `SkillTimerModule` - 18 edges
10. `WindowKeySender` - 18 edges

## Surprising Connections (you probably didn't know these)
- `Skill Combo System` --semantically_similar_to--> `skill_timer.py`  [INFERRED] [semantically similar]
  README.md → AGENTS.md
- `Bug Report Template` --references--> `GameTools Health Monitor`  [EXTRACTED]
  .github/ISSUE_TEMPLATE/bug_report.md → README.md
- `Feature Request Template` --references--> `GameTools Health Monitor`  [EXTRACTED]
  .github/ISSUE_TEMPLATE/feature_request.md → README.md
- `GitHub Pages Site` --references--> `GameTools Health Monitor`  [EXTRACTED]
  index.html → README.md
- `F3 (Inventory Clear)` --references--> `tab_inventory.py`  [EXTRACTED]
  DEVELOPER_HANDBOOK.md → AGENTS.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Refactor Four Phase Plan** — opencode_plans_refactor_health_monitor_plan, phase_1_appstate_domain_extraction, phase_2_tab_extraction, phase_3_cross_component_dedup, phase_4_core_slimming [EXTRACTED 1.00]
- **Main App Orchestration** — health_monitor, app_state, tab_monitor, tab_inventory, tab_combo, tab_status, tab_help, tab_version, tab_about [EXTRACTED 1.00]
- **Health Monitoring Stack** — tab_monitor, monitor_analyzer, capture_utils, image_utils [EXTRACTED 1.00]

## Communities (42 total, 16 thin omitted)

### Community 0 - "Auto Click & App State"
Cohesion: 0.05
Nodes (68): AppState, AppState Context Pattern, Auto Click Integration, AutoClickManager, AutoHotkey, capture_utils.py, CHANGELOG, Close Lifecycle Pattern (+60 more)

### Community 1 - "Combo/Skill Combo"
Cohesion: 0.08
Nodes (4): ComboTab, StatusTab, 可重複使用的 Tooltip：懸浮 widget 顯示說明文字，支援延遲, Tooltip

### Community 2 - "Skill Timer"
Cohesion: 0.11
Nodes (11): Misc, on_close(), skill_timer.py 循環計時自動釋放技能模組 ──────────────────────────────────────────────────, 送鍵 → 排下一次；在 lock 外送鍵避免死鎖, 啟動迴圈，回傳 False 代表設定不合法, 建立一個 ttk.LabelFrame（self.frame），     可直接 pack / grid 進任何父容器。, parent    : 父容器         max_slots : 最多幾個技能槽（上限 _MAX_SLOTS）         on_log    :, 每個 SkillSlot 持有自己的 tk 變數（直接綁定 UI）     和一個 threading.Timer 遞迴迴圈。 (+3 more)

### Community 5 - "About Tab"
Cohesion: 0.09
Nodes (3): AboutTab, HelpTab, WindowKeySender

### Community 6 - "Usage Tracker"
Cohesion: 0.11
Nodes (15): UsageTracker, emergency_cleanup(), emergency_exit_handler(), format_usage_time(), get_app_dir(), global_exception_handler(), global_f12_handler(), 工具函數模組 包含應用程式的通用工具函數、緊急處理、系統級功能等 (+7 more)

### Community 7 - "Config Management"
Cohesion: 0.11
Nodes (7): ConfigManager, get_config_manager(), get_config_value(), load_config(), 配置管理模組 處理應用程式的設定載入、保存、註冊表操作等功能, save_config(), set_config_value()

### Community 8 - "Build System"
Cohesion: 0.15
Nodes (10): GameToolBuilder, main(), Collect binary dependencies (DLLs, pyds), Move built exe into package directory, Build updater_main.py → updater.exe (lightweight, no GUI deps)., Create installation package., Return the first existing path from candidates, else None., Run full build pipeline (+2 more)

### Community 9 - "Health/Mana Analysis"
Cohesion: 0.13
Nodes (20): analyze_health(), analyze_mana(), check_triggers(), get_health_color_ratio(), get_main_color(), get_mana_color_ratio(), interruptible_sleep(), is_health_color() (+12 more)

### Community 10 - "Window Management"
Cohesion: 0.16
Nodes (5): 檢查遊戲視窗是否最小化，如果最小化則顯示提醒視窗, Stop monitoring without blocking the Tk main thread., F9: 全域暫停開關 - 暫停/恢復所有熱鍵功能（線程安全）, 檢查是否應該保持GUI在最上方（根據用戶設定）, 管理視窗層級系統         層級從高到低: CHILD > SETTINGS > MAIN         - CHILD: 子視窗（提示視窗、測試視

### Community 13 - "Language System"
Cohesion: 0.17
Nodes (9): get_app_dir(), get_current_language(), get_language_manager(), get_text(), LanguageManager, load_language_packs(), 語言系統模組 處理多語言支援、語言包載入、UI文字更新等功能, 獲取應用程式目錄，適用於開發環境和打包後的exe (+1 more)

### Community 14 - "Release Process"
Cohesion: 0.17
Nodes (13): commitizen, Dual-Track Version Check, latest_version.txt, Pre-release Testing Pattern, release.ps1, Release Workflow, _log(), main() (+5 more)

### Community 15 - "Update Core"
Cohesion: 0.20
Nodes (15): Path, apply_update(), check_for_update(), _clean_stale_temp_dirs(), current_exe_path(), download_update(), is_frozen(), _parse_version() (+7 more)

### Community 17 - "App State"
Cohesion: 0.15
Nodes (3): Any, AppState, Shared application state context.      Holds cross-cutting state (monitoring,

### Community 19 - "Inventory Grid"
Cohesion: 0.23
Nodes (3): capture_region_to_cv2(), calculate_inventory_grid_positions(), 計算背包格子位置 (5x12 布局，總共60個格子)

### Community 20 - "Image Utilities"
Cohesion: 0.23
Nodes (4): draw_scale_lines(), Draw 10 equally-spaced horizontal scale lines on a preview image.      Args:, Resize an image proportionally to fit a target preview size.      The image is, resize_and_center_image()

### Community 21 - "Auto Click Manager"
Cohesion: 0.24
Nodes (3): AutoClickManager, 自動點擊循環 - 模擬AHK的while循環行為, 啟動AHK自動點擊腳本 - 支援EXE版本優先

### Community 22 - "Capture Utilities"
Cohesion: 0.25
Nodes (5): build_game_window_monitor(), capture_region_to_pil(), _MssSingleton, Capture utility functions extracted from health_monitor.py., save_screenshot()

### Community 23 - "App Startup & Hotkeys"
Cohesion: 0.20
Nodes (4): Run non-critical startup tasks after the main window is already visible., Refresh heavier previews after startup so the main window appears sooner., get_region_text(), Format the health bar region configuration as a display string.      Args:

### Community 24 - "Health/Mana Display"
Cohesion: 0.20
Nodes (9): draw_health_indicator(), draw_mana_indicator(), get_interface_ui_region_text(), get_mana_region_text(), Image utility functions for Path of Exile game tools.  This module contains im, Draw a mana percentage indicator line and label on a preview image.      Args:, Format the mana bar region configuration as a display string.      Args:, Format the interface UI region as a display string.      Args:         interf (+1 more)

### Community 25 - "Inventory Detection"
Cohesion: 0.29
Nodes (6): find_inventory_items(), Inventory utility functions for Path of Exile game tools.  This module contain, 檢查背包是否需要清空 - 檢查60個格子，可選擇跳過指定格子和之前的格子, should_clear_inventory(), 清空背包物品 - 動態辨識版：每次點擊後重新辨識，適應大物品清空多格的情況          包含智能跳過機制：當遇到無法存放進倉庫的物品時，自動跳過該物品, 更新背包預覽，顯示60個格子的狀態和處理進度 - 優化版本

### Community 35 - "Custom Dialogs Module"
Cohesion: 0.50
Nodes (3): 自訂對話框模組 提供動態尺寸調整的本地化對話框，支援長文本顯示, 設置自訂對話框為預設 messagebox, setup_custom_messagebox()

## Knowledge Gaps
- **21 isolated node(s):** `Path of Exile`, `Inventory Clear/Pickup`, `Auto Click Integration`, `language_packs.json`, `ruff` (+16 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `HealthMonitor` connect `Health Monitor Main` to `Auto Click & App State`, `Toast Notifications`, `Skill Timer`, `Combo/Skill Combo`, `Interface Region Selection`, `About Tab`, `Inventory Tab UI`, `Usage Tracker`, `Health/Mana Analysis`, `Window Management`, `Monitor Tab`, `Version Updates`, `Settings & Dynamic UI`, `App State`, `Custom Dialogs`, `Auto Click Manager`, `App Startup & Hotkeys`?**
  _High betweenness centrality (0.590) - this node is a cross-community bridge._
- **Why does `InventoryTab` connect `Inventory Tab UI` to `Auto Click & App State`, `Quick Action Panels`, `Combo/Skill Combo`, `Health Monitor Main`, `UI Visibility Check`, `Custom Dialogs`, `Inventory Grid`, `Inventory Detection`, `UI Selection`, `GUI Overlap Detection`, `Inventory Selection`, `Pickup Coordinates`, `Inventory Preview`?**
  _High betweenness centrality (0.275) - this node is a cross-community bridge._
- **Why does `MonitorTab` connect `Monitor Tab` to `Auto Click & App State`, `Combo/Skill Combo`, `Settings Validation`, `Health Monitor Main`, `Custom Dialogs`, `Image Utilities`, `Capture Utilities`, `Health/Mana Display`, `Region Selection`?**
  _High betweenness centrality (0.152) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `InventoryTab` (e.g. with `HealthMonitor` and `.create_widgets()`) actually correct?**
  _`InventoryTab` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `HealthMonitor` (e.g. with `AppState` and `AutoClickManager`) actually correct?**
  _`HealthMonitor` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `MonitorTab` (e.g. with `HealthMonitor` and `.create_widgets()`) actually correct?**
  _`MonitorTab` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `ComboTab` (e.g. with `HealthMonitor` and `.create_widgets()`) actually correct?**
  _`ComboTab` has 4 INFERRED edges - model-reasoned connections that need verification._
# 重構計畫：Health Monitor 瘦身

## 目標

將 `src/health_monitor.py` 從 **~9,800 行 / 225 個方法** 降為 **~1,500 行**（純編排層），
透過以下方式：

1. 共享應用狀態 → `AppState` 上下文
2. 獨立領域類別（自動點擊、按鍵發送、使用時間追蹤）
3. 每個 Notebook 分頁 → 獨立檔案中的獨立類別
4. 跨元件重用（選取器、預覽管理器）

---

## 分支策略

```
master
 └── refactor/health-monitor-slim    ← 所有工作在此進行
       ├── Phase 1 (4 次提交)
       ├── Phase 2 (7 次提交)
       ├── Phase 3 (1-2 次提交)
       └── Phase 4 (1 次提交)
```

每個 Phase 完成後，透過 PR 合回 `master`。

---

## 回滾 / 恢復協議

**每次提交都是一個安全檢查點。** 如果工作中斷：

1. 下一個代理讀取此文件，確定當前階段/步驟
2. 執行 `git log --oneline -5` 查看上次提交
3. 閱讀下方階段章節，在最後完成的步驟之後繼續
4. 執行 `git status` 確認工作目錄乾淨

**回滾一步：** `git revert <commit-hash>`
**回滾整個階段：** `git reset --hard <phase-start-commit>`（僅在未推送時）

---

## 提交前驗證閘門

在每次提交前，執行以下命令以確保不引入新問題：

```powershell
# 1. 編譯檢查
python -m py_compile src/health_monitor.py

# 2. Ruff 檢查（不應增加複雜度問題以外的錯誤）
ruff check src/ --statistics

# 3. Pyright（僅檢查目標檔案）
pyright src/health_monitor.py

# 注意：pyright 基準線約 185 個錯誤（tkinter/cv2 可選型別）。
# 目標：不增加此計數。改進為額外紅利。
```

---

# Phase 1：AppState + 領域抽取

> **模式**：抽取 → 委派 → 測試 → 提交
> 每一步都是安全的，因為原始方法仍然存在（在內部委派）。

## ✅ 1.1 — `AppState` 上下文物件

**建立檔案：** `src/app_state.py`
**類別：** `AppState`

**內容：** 抽取共享應用狀態 + 鎖 + 旗標到專用上下文。

- 監控狀態：`monitoring`, `monitor_thread`, `monitor_interval`
- 連段狀態：`combo_sets`, `combo_enabled`, `combo_running`, `combo_thread`, `combo_hotkeys`
- 暫停狀態：`global_pause`, `monitoring_was_active`, `combo_was_running`
- 鎖：`monitoring_lock`, `combo_lock`, `global_pause_lock`
- 雜項共享：`config`（引用）, `root`（引用）, `last_trigger_times`, `_is_closing`
- 視窗狀態：`original_gui_geometry`, `original_gui_state`, `gui_was_foreground_before_minimize`, `gui_minimized_for_clear`

**在 HealthMonitor 中：**
```python
self.state = AppState(self)  # 在 __init__ 早期建立
# 舊的 self.monitoring → self.state.monitoring
# 舊的 self.monitoring_lock → self.state.monitoring_lock
# 依此類推
```

**影響範圍：** 約 15-20% 的實例變數存取從 `self.xxx` 變為 `self.state.xxx`。
**回滾：** `git revert` — 所有委派保留。

## ✅ 1.2 — `AutoClickManager`

**建立檔案：** `src/auto_click_manager.py`
**類別：** `AutoClickManager`

**搬移方法：** `setup_auto_click_listener`, `start_auto_click_ahk`, `stop_auto_click_ahk`, `toggle_auto_click`, `start_auto_click`, `stop_auto_click`, `auto_click_loop`（7 個方法，約 230 行）

**HealthMonitor 委派：**
```python
self.auto_click = AutoClickManager(self, self.state)
# 舊的 self.start_auto_click() → self.auto_click.start()
```

## ✅ 1.3 — `UsageTracker`

**建立檔案：** `src/usage_tracker.py`
**類別：** `UsageTracker`

**搬移方法：** `load_usage_time_from_registry`, `save_usage_time_to_registry`, `track_usage_time`, `update_usage_time_display`, `update_usage_time_periodically`（5 個方法，約 75 行）

## ✅ 1.4 — `WindowKeySender`

**建立檔案：** `src/window_key_sender.py`
**類別：** `WindowKeySender`

**搬移方法：** `get_game_window_handle`, `map_key_to_vk_code`, `send_key_to_window`, `send_key_to_window_combo`, `_send_with_postmessage`, `vk_to_key_name`, `map_key_name`, `activate_game_window`, `is_game_window_foreground`, `is_gui_foreground`, `_start_window_focus_watcher`, `_focus_watcher_tick`, `_is_game_window_active`, `_is_game_window_visible`（14 個方法，約 300 行）

**同時搬移常數：** VK_* 常數、WM_KEYDOWN/UP/CHAR、GetWindowTextW 等。

---

# Phase 2：分頁抽取

> **模式**：每個分頁 = 獨立的檔案
> 建構子：`XxxTab(app, state, parent_frame, notebook)`
> 分頁方法透過 `self.state.xxx` 和 `self.app.xxx` 參考跨分頁狀態。
> 分頁專用小工具成為分頁類別上的 `self.`（不再在 HealthMonitor 上）。

**順序：靜態（簡單）分頁優先 → 動態（複雜）分頁最後。**

## 2.1 — HelpTab → `src/tab_help.py`

**搬移：** `create_help_tab`（196 行）、`create_info_card`（20 行）、`setup_global_scroll`（13 行）、`on_tab_changed`（7 行）、`handle_mousewheel`（28 行）、`update_help_tab_language`（14 行）

## 2.2 — AboutTab → `src/tab_about.py`

**搬移：** `create_about_tab`（161 行）、`update_about_tab_language`（14 行）

## 2.3 — StatusTab → `src/tab_status.py`

**搬移：** `create_status_tab`（59 行）、`configure_status_text_tags`（15 行）、`add_status_message`（56 行）、`schedule_ui_callback`（30 行）、`refresh_status_display`（19 行）、`clear_status_log`（13 行）、`update_status_count`（6 行）、`update_status_tab_language`（17 行）

## 2.4 — VersionTab → `src/tab_version.py`

**搬移：** `create_version_tab`（74 行）、`check_for_updates`（55 行）、`compare_versions`（28 行）、`open_download_page`（14 行）、`test_github_connection`（15 行）、`format_release_notes`（37 行）、`update_release_notes_display`（10 行）、`silent_version_check`（93 行）、`show_update_notification`（79 行）、`update_version_tab_language`（14 行）

## 2.5 — MonitorTab → `src/tab_monitor.py`

**搬移（35 個方法，約 900 行）：** `create_monitor_tab`, `on_type_changed`, `test_preview`、區域選取（HP + Mana + UI）、預覽擷取/顯示、`adjust_colors`, `adjust_interface_ui_thresholds`

**分頁專用狀態：** `selected_region`, `selected_mana_region`、顏色閾值、預覽變數。移至 `MonitorTab`。

## 2.6 — ComboTab → `src/tab_combo.py`

**搬移（18 個方法，約 650 行）：** `create_combo_tab`, `initialize_combo_sets`, `create_combo_set_frame_horizontal`, `toggle_combo_set`, `update_trigger_key/delay`, `update_combo_key/delay`, `update_stationary_attack`, `update_combo_ui_from_config`, `save/load_combo_config`, `execute_combo`, `run/start/stop/restart_combo_system`, `update_combo_tab_language`

**分頁專用狀態：** `combo_ui_refs` → 移至 `ComboTab`。

**⚠ 跨領域：** `combo_sets`, `combo_enabled`, `combo_thread`, `combo_running`, `combo_hotkeys` 保留在 `AppState` 中（核心需要它們）。

## 2.7 — InventoryTab → `src/tab_inventory.py`

**搬移（48 個方法，約 2,500 行）：** `create_inventory_tab`, `adjust_grid_offset`, `reset_grid_offset`, `update_offset_labels`, `update_inventory_preview_from_current`, `select_inventory_region`, `create_inventory_selection_window`, `start_inventory_selection`, `update_inventory_selection`, `end_inventory_selection`, `cancel_inventory_selection`, `record_empty_inventory_color`, `select_inventory_ui_region`, `select_interface_ui_region`, `create_inventory_ui_selection_window`, `create_interface_ui_selection_window`, `start_inventory_ui_selection`, `update_inventory_ui_selection`, `end_inventory_ui_selection`, `cancel_inventory_ui_selection`, `start_interface_ui_selection`, `update_interface_ui_selection`, `end_interface_ui_selection`, `cancel_interface_ui_selection`, `load_ui_screenshot_from_file`, `load_interface_ui_screenshot_from_file`, `update_ui_preview`, `update_interface_ui_preview`, `is_inventory_ui_visible`, `is_interface_ui_visible`, `clear_inventory_item`, `_draw_exclusion_overlay`, `_on_preview_click`, `_on_click_mode_changed`, `update_inventory_preview_with_items`, `update_inventory_preview_with_progress`, `test_inventory_clearing`, `save_inventory_config`, `quick_clear_inventory`, `check_gui_overlap_with_inventory`, `check_gui_overlap_with_inventory_ui`, `minimize_gui_for_clear`, `calculate_safe_gui_position`, `calculate_safe_gui_position_with_preview`, `restore_gui_after_clear`, `minimize_all_guis`, `restore_all_guis`, `check_inventory_ui_exists`（48 個方法）

**已在 Phase 2.7 之後的項目（F6 拾取）：** `f6_pickup_items`, `load_pickup_coordinates`, `save_pickup_coordinates`, `setup_pickup_coordinates`, `start_continuous_setup`, `update_coordinate_display`, `clear_all_coordinates`, `test_pickup`, `update_pickup_status`（9 個方法）

---

# Phase 3：跨元件去重

## 3.1 — `RegionSelector` 共享元件

**建立檔案：** `src/region_selector.py`
**類別：** `RegionSelector`

**問題：** 5 套幾乎相同的選取實作：
- HP 區域選取（start_selection / on_selection_start/drag/end/cancel / esc_listener）
- Mana 區域選取（start_mana_selection / on_mana_selection_start/drag/end/cancel）
- 背包區域選取（start_inventory_selection / ...）
- 背包 UI 區域選取（start_inventory_ui_selection / ...）
- 介面 UI 區域選取（start_interface_ui_selection / ...）

**解決方案：**
```python
selector = RegionSelector(
    canvas=self.preview_canvas,
    on_selected=lambda x1,y1,x2,y2: self._on_health_region_selected(x1,y1,x2,y2),
    on_cancelled=lambda: self._on_selection_cancelled(),
    esc_tag="health_selector",
    app=self.app,
)
selector.start()
```

每個分頁使用不同回呼實例化。節省約 500 行重複程式碼。

## 3.2 —（可選）`PreviewManager`

**問題：** HP 預覽和 Mana 預覽遵循相同模式（擷取 → 分析 → 渲染 → 更新畫布）。兩組幾乎相同的方法：`capture_preview` / `capture_mana_preview`、`capture_preview_async` / `capture_mana_preview_async`、`load_preview_image` / `load_mana_preview_image`、`update_live_preview` / `update_live_mana_preview`、`_update_preview_image` / `_update_mana_preview_image`。

**解決方案：** 共享的 `PreviewManager(health_or_mana)`，搭配分析函數的回呼。

---

# Phase 4：核心瘦身

## 4.1 — 移除委派樁

在 Phase 2 之後，HealthMonitor 將剩下約 70-80 個方法（從 225 個減少）。許多將是 1 行的委派樁，例如：
```python
def start_monitoring(self):
    return self.state.start_monitoring()
```

**動作：** 在呼叫者可以直接呼叫 `self.state.xxx` 或 `self.tab_monitor.xxx` 的地方內聯或移除樁。

**預期結果：** HealthMonitor 保留：
- `__init__`（約 150 行）：編排模組/分頁建立
- `create_widgets`（約 30 行）：建立 Notebook + 實例化分頁
- `close_app` / `on_closing`（約 50 行）：生命週期
- `load_config` / `save_config`（約 100 行）：跨領域配置 I/O
- `setup_hotkeys`（約 20 行）：全域熱鍵註冊
- `main` 進入點（約 60 行）
- 雜項跨分頁接線（約 100 行）

**目標：** HealthMonitor 類別約 500-600 行 + `__main__` 約 100 行。

---

# 總結

| Phase | 提交次數 | 抽取行數 | 風險 |
|---|---|---|---|
| 1. AppState + 領域 | 4 | ~600 | 低（無 UI） |
| 2. 分頁抽取 | 7 | ~6,500 | 中（UI、回呼） |
| 3. 跨元件去重 | 1-2 | ~500 | 中（修改 5 處呼叫點） |
| 4. 核心瘦身 | 1 | ~800 | 低（移除樁） |
| **總計** | **13-14** | **~8,400** | |

**最終狀態（預估行數）：**

| 檔案 | 行數 | 職責 |
|---|---|---|
| `health_monitor.py` | ~1,400 | 僅編排（init、lifecycle、hotkeys） |
| `app_state.py` | ~200 | 共享狀態 + 鎖 + 旗標 |
| `auto_click_manager.py` | ~250 | 自動點擊邏輯 |
| `usage_tracker.py` | ~100 | 註冊表使用時間 |
| `window_key_sender.py` | ~350 | 遊戲視窗 PostMessage 按鍵 |
| `tab_help.py` | ~300 | 使用說明分頁 |
| `tab_about.py` | ~200 | 關於分頁 |
| `tab_status.py` | ~200 | 執行狀態分頁 |
| `tab_version.py` | ~400 | 版本檢查分頁 |
| `tab_monitor.py` | ~1,000 | 血魔監控分頁 |
| `tab_combo.py` | ~700 | 技能連段分頁 |
| `tab_inventory.py` | ~2,500 | 背包清理分頁（含 F6 拾取） |
| `region_selector.py` | ~200 | 可重用區域選取元件 |
| **總計** | **~7,800** | 分散到 13 個檔案，無單一檔案超過 2,500 行 |

---

## 每次提交的檢查清單

```markdown
- [ ] `python -m py_compile src/health_monitor.py` 通過
- [ ] `ruff check src/` 無新增錯誤（允許原有 11 個 C901）
- [ ] `pyright src/health_monitor.py` 無新增錯誤（基準 ~185）
- [ ] 手動冒煙測試：應用程式啟動並關閉
- [ ] `cz commit` 使用 Conventional Commit 格式提交
```

---

## 對代理的注意事項

- 本檔案是**中繼文件**：如果在任務中間中斷，下一個代理應從此檔案恢復。
- 恢復時的第一件事：檢查 `git log --oneline -5` 以確認最後狀態。
- 使用 `--fix` 的 Ruff 可能會重新排序匯入。在執行後始終檢查 `git diff --stat`。
- 每個階段都是一個 `cz commit`，功能標記如 `refactor(phase1):`。
- 不要在一次提交中混合兩個階段。

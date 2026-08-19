# 專案筆記

## 專案理念與方向

### 核心原則
- **最小主義，務實**。最好的程式碼是從未被寫出的程式碼（YAGNI）。
- **社群標準優先，不造輪子**。有現成函式庫就用、不重做別人做過的事。
- **普通使用者面向**。進階選項摺疊隱藏、預設行為簡單直覺、不讓使用者看到實作細節。
- **刪除優先於新增**。功能不必要就砍，減少維護負擔。
- **不懶惰的地方**：信任邊界驗證、資料遺失防止（config backup）、安全性。

### 目標方向
Windows 上給 Path of Exile 玩家的日常自動化工具：健康/魔力監控、技能連招、背包整理、自動點擊。

---

## 文件索引

| 路徑 | 對象 | 用途 |
|---|---|---|
| `docs/` | 使用者 | 使用者導向說明（使用說明、運作原理） |
| `docs/index.html` | 使用者 | GitHub Pages 教學網站 |
| `CHANGELOG.md` | 開發者 | 版本記錄（commitizen 自動維護） |
| `AGENTS.md` | AI agent | 本檔案 — 工作規範與流程 |

---

## 工作完成規範

每個獨立任務完成後應立即單獨 commit，不得累積多個不相關任務到同一個 commit。若同一輪對話涉及多個檔案的不同修改目的，必須拆成多次 git add + commit，逐一提交。

每次完成任何程式碼修改後，**必須主動依序跑完以下檢查清單，不得等待使用者提醒**。使用者是 vibe coding，不會提醒你做這些事——這份清單就是你的提醒：

1. **Lint / 格式化**（本次有改 `.py` 檔才需要，純文件/設定變更跳過）：
   ```powershell
   ruff check src/ --fix
   ruff format src/
   ```
   確認無殘留 error 才進下一步。注意：`health_monitor.py` 有 11 個既有 `C901`，是 backlog 非本次新增。

2. **自檢測試**（本次有改非 trivial 邏輯——有分支、迴圈、解析、信任邊界/資料安全路徑——才需要）：
   檢查該檔案是否有 `if __name__ == "__main__":` self-check，有就執行：
   ```powershell
   python -c "import sys,runpy; sys.path.insert(0,'src'); runpy.run_path('src/<改動的檔案>', run_name='__main__')"
   ```
   同時跑 pytest 套件：
   ```powershell
   python -m pytest --no-cov -q
   ```
   改 `src/` 邏輯後不跑 pytest 視為未完成。

3. **add + commit + push**（一次完成）：
   ```powershell
   [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
   git add -A
   '類型: 中文說明' | Out-File -FilePath __commit_msg.txt -Encoding utf8
   git commit -F __commit_msg.txt
   Remove-Item __commit_msg.txt
   git push origin master
   ```

commit 訊息格式：`feat` / `fix` / `refactor` / `docs` / `chore` + 冒號 + 中文說明。
注意：`cz commit` 在無互動 console 會失敗（`NoConsoleScreenBufferError`），一律用上面的 `git commit -F` 方式。

---

## Shell / Git 指令規範

### PowerShell 7+

本專案在 Windows 上以 **PowerShell 7+** 為 shell。所有指令使用 PowerShell 7 語法（`&&` / `||` pipeline chain、`Set-Content`、`Get-ChildItem`）。避免 `cmd.exe` batch idioms，除非是執行明確的 `.bat` 腳本。

中文 commit 訊息用 `-F` 暫存檔方式，避免引號截斷（見上方工作完成規範第 3 步）。

---

## Coding 風格（Ponytail）

你是一個懶惰的資深開發者。懶惰代表高效，不代表不認真。最好的程式碼是從未被寫出的程式碼。

寫任何程式之前，先停在第一個能撐住的台階：

1. 這個需要存在嗎？→ 不：跳過（YAGNI）
2. 標準函式庫能做？→ 用它
3. 原生平台功能能用？→ 用它
4. 已安裝的 dependency 能解？→ 用它
5. 一行搞定？→ 就一行
6. 以上都不是：才寫最少能跑的程式碼

**不做的事：**
- 沒被要求的抽象層
- 能避免就避免的新 dependency
- 沒人要求的 boilerplate
- 刪除優先於新增
- 無聊優先於聰明
- 檔案數量越少越好

兩個 stdlib 方案大小相同？選在 edge case 正確的那個。懶惰是寫更少程式碼，不是選更脆弱的演算法。

刻意的簡化用 `# ponytail:` 註解標記。

**懶惰程式碼沒有檢查就是未完成的。** 非平凡邏輯（有分支、迴圈、解析、信任邊界路徑）留下一個可執行的檢查——最小的、邏輯壞掉就會失敗的東西：assert-based demo() / `__main__` self-check 或一個小 `test_*.py`。單行 trivial 程式碼不需要測試。

**不懶惰的地方：**
- 信任邊界的輸入驗證
- 防止資料遺失的錯誤處理（config 備份）
- 安全性
- 任何被明確要求的事項

---

## 可用工具

### ripgrep（`rg`）
搜尋程式碼時**一律用 `rg`，不用 `grep` 或 `findstr`**。

### Ruff（`ruff`）
Lint 和格式化一律用 `ruff`，不用 flake8 / black / isort。
設定在 `pyproject.toml` `[tool.ruff]`：line-length 200、select E/F/W/C90、mccabe max-complexity 20。

```powershell
ruff check src/ --statistics   # 摘要（大型檔案好用）
ruff check src/ --fix          # 自動修復安全問題
ruff format src/
```

- `[*]` = auto-fixable，跑 `ruff check src/ --fix`
- `C901`（complex-structure）= 既有 backlog（health_monitor.py 11 個），不在此任務處理
- `[ ]` = manual fix，case by case

### pyright（`pyright`）
`pyright src/health_monitor.py` — type-check 主程式。
碰 `close_app()`、threading、tkinter callbacks 前先跑。

### py-spy（`py-spy`）
`py-spy top --pid <PID>` / `py-spy record -o profile.svg --pid <PID>`。

### commitizen（`cz`）
`cz bump` 管理版本（同步 `_version.py` + `CHANGELOG.md`）。`cz commit` 互動失敗時改用 `git commit -F`。

### pytest
```powershell
python -m pytest --no-cov -q
```
設定在 `pyproject.toml` `[tool.pytest.ini_options]`。

---

## CodeGraph

專案已用 `codegraph init` 建過索引（`.codegraph/`），透過 MCP server 自動接給 agent 使用，不需要在這裡寫使用規則——`codegraph_explore` 由 agent 依需求自行判斷呼叫，索引也由檔案監控自動同步，commit 流程不需要任何額外步驟。

---

## 目錄結構

```text
src/                          # 執行期程式碼唯一事實來源
scripts/                      # 一鍵本地工作流（install/build）
tools/build.py                # PyInstaller 打包管線
docs/                         # 使用者導向文件
.github/workflows/ci.yml      # push/PR 時 lint + type check
latest_version.txt            # 原始 GitHub 版本檢查（無 API 限制）
release.ps1                   # 一鍵發版腳本
updater_main.py               # 獨立更新程式（打包為 updater.exe）
```

### src/ Module 職責

| Module | Role | Dependencies |
|---|---|---|
| `health_monitor.py` | 主入口、UI 編排、事件迴圈（~2,185 行，主要 refactor 目標） | 全部 |
| `monitor_analyzer.py` | 健康/魔力 HSV 分析、觸發邏輯 | cv2, numpy |
| `capture_utils.py` | 截圖、mss singleton | mss, PIL, numpy |
| `image_utils.py` | 影像繪製、resize、預覽工具 | PIL |
| `inventory_utils.py` | 背包格分析、物品偵測 | numpy |
| `config_manager.py` | JSON config 讀寫 + 備份 | none |
| `custom_dialogs.py` | 動態尺寸 modal dialog | tkinter |
| `language_system.py` | 雙語字串查詢 | JSON |
| `skill_timer.py` | 技能冷卻計時 | tkinter |
| `utils.py` | 緊急清理、F12 handler、Tooltip | keyboard, psutil |
| `tab_inventory.py` | 背包清理 + 拾取 UI 與邏輯 | cv2, numpy, PIL, mss, pyautogui |
| `tab_monitor.py` | 健康/魔力監控 tab UI 與邏輯 | cv2, numpy, PIL, mss, keyboard |
| `tab_combo.py` | 技能連招 tab | — |
| `tab_version.py` | 版本檢查 + 應用內下載/更新 | requests, updater_core |
| `tab_about.py` / `tab_help.py` / `tab_status.py` | 關於/說明/狀態 tab | tkinter |
| `app_state.py` | 共用應用狀態容器 | none |
| `auto_click_manager.py` | 自動點擊管理（AHK） | subprocess, psutil |
| `usage_tracker.py` | 使用時間統計 | none |
| `window_key_sender.py` | 視窗聚焦按鍵發送 | pygetwindow, pyautogui |
| `updater_core.py` | 更新引擎：版本檢查、下載、套用 | requests, zipfile |
| `_version.py` | 版本唯一事實來源（commitizen 管理） | none |

Runtime-generated 檔案（非 source，勿當程式碼改）：
- `src/health_monitor_config.json` / `.backup`
- `src/screenshots/`

## 一鍵工作流

1. 安裝依賴：`scripts/install_dependencies.bat`
2. 從 source 或 EXE 執行：`Run.bat`
3. 建 EXE：`scripts/build_exe.bat`
4. 測試建出的 EXE：`Run.bat`

## 版本管理與發行流程

### 版本資訊
- 目前：**v1.2.1**；唯一事實來源 `src/_version.py`（`__version__ = "1.2.1"`）
- `health_monitor.py`: `CURRENT_VERSION = f"v{__version__}"`
- `build.py`: `APP_VERSION = __version__`
- 由 commitizen 管理（`cz bump` 同步 `_version.py` + `CHANGELOG.md`）

### Dual-Track 版本檢查

使用者落在兩種版本檢查機制之一：

| 使用者版本 | 檢查方式 | Endpoint |
|---|---|---|
| ≤ v1.2.0（舊） | GitHub API `/releases/latest` | `api.github.com/repos/.../releases/latest` |
| ≥ v1.2.1（新） | `latest_version.txt` | `raw.githubusercontent.com/.../master/latest_version.txt` |

GitHub API `/releases/latest` **只回傳非 pre-release、非 draft 的 release**。這讓 pre-release 版本自動對舊用戶不可見。

### Pre-release 測試（不通知用戶）

要測試新版本但不通知用戶：

1. 設 `_version.py` 為 pre-release：`__version__ = "1.2.2-beta"`
2. `.\release.ps1 -Preview` — 建 EXE、建立 GitHub **Pre-release**、只更新 `latest_version_prerelease.txt`
3. `latest_version.txt` **不更新** → 所有現有用戶看不到變化
4. 你的 config：`"allow_prerelease": true` → 你的 app 偵測到 `1.2.2-beta`
5. 測試完整自動下載流程（download → extract → updater.exe → restart）
6. 穩定後：`_version.py` = `"1.2.2"`，跑 `.\release.ps1`（一般）→ 更新 `latest_version.txt` → 通知所有用戶

### 穩定發版

跑 `.\release.ps1` — 更新 `latest_version.txt`、建立正常 GitHub Release、所有用戶下次啟動被通知。

### 關鍵規則

- **絕不把 pre-release 版本寫進 `latest_version.txt`** — 這會通知所有用戶
- `allow_prerelease` config 預設 `false` — 只有開發者應為測試設為 `true`
- `_parse_version()` 把 `1.2.2-beta` 視為低於 `1.2.2`（stable 勝 pre-release）
- Pre-release assets 在 GitHub Releases 可用與正常 release 相同的 URL pattern 下載

### 使用者提到發版關鍵字時

使用者說「發版」、「release」、「測試更新」、「不通知用戶」、「pre-release」等：
- 提醒 `-Preview` flag 與 `allow_prerelease` config
- 確認要「先測試（preview）」還是「直接發給所有人（stable）」
- 引導正確流程

## 打包規則（Critical）

- `tools/build.py` 從 `src/` 與 `docs/` 收集 assets。
- 建出內容包含：
  - `GameTools_HealthMonitor.exe`、`auto_click.exe`、`updater.exe`、`language_packs.json`
  - `使用說明.md`（from `docs/`）、`啟動工具.bat`、`README.txt`
- `updater_main.py` 建為 `updater.exe`（輕量、無 GUI deps）。
- 若 PyInstaller cache 在 Windows 被鎖（`WinError 5`），清 `build/GameTools_HealthMonitor` 重建。

## commit 前安全檢查

- 無 secrets/tokens/private keys。
- 無意外鏡像目錄（例如重複的專案副本）。
- README 版本/連結符合目前 release 狀態。
- Build + launch smoke test 通過。
- worktree 混雜時只 stage request-scoped 檔案。

## Close 生命週期注意事項

- `close_app()` 是敏感路徑。小心 `_is_closing`、排程中的 `after(...)` callbacks、背景 threads。
- 背景 workers 在 shutdown 開始後不得碰 Tk widgets。
- 修改 startup/shutdown 邏輯時，重測正常關閉流程，不只測 app 啟動。

## Future Refactor 筆記

- **GUI 換血：tkinter/ttkbootstrap → PySide6 + qfluentwidgets（進行中）。** 動機：tk 單執行緒軟渲染，捲動掉幀無法根治；決策結論為 PySide6+qfluentwidgets（Qt 原生效能、透明 overlay/topmost 原生支援），Flet 已評估放棄（JSON bridge 架構不適合本 app 的 overlay 與高頻影像）。遷移策略：只重寫 GUI 層，`config_manager`/`monitor_analyzer`/`capture_utils`/`inventory_utils`/`image_utils`/`window_key_sender`/`usage_tracker`/`updater_core`/`language_system` 全保留。tk 與 Qt 無法共存於同一 process，故為整套 GUI 重寫。
- **Qt 遷移進度：** Phase 1-3（deps/skeleton/StatusTab）+ Phase 4 MonitorTab + **Phase 5 InventoryTab** 已完成並 push：`src/qt/monitor.py`（UI+觸發列表+預覽+`_SelectionOverlay` 框選+thread-safe signal 更新）、`src/qt/monitor_dialogs.py`（血條校準/介面UI閾值）、`src/qt/inventory.py`（框選/空格顏色/預覽/排除格、F3 清包、F6 拾取、取物座標設定對話窗、`is_interface_ui_visible`）、`src/qt/main_window.py`（`monitor_health` 迴圈 + `press_key_sequence` + start/stop 狀態 + F3/F6 全域熱鍵）。smoke 含 `SMOKE MONITOR LOOP OK` / `SMOKE INVENTORY 5C OK`。待辦：Phase 6 ComboTab、7 Help/About/Version、8 SkillTimerModule、9 刪 tk + 打包。
- **qfluentwidgets 1.11.3 注意：** `MessageBox` 無 static `warning/information/critical/question`（用原生 `QMessageBox`）；PySide6 6.11 enum 用完整命名空間（如 `Qt.AlignmentFlag.AlignCenter`）否則 pyright 報 `reportAttributeAccessIssue`。
- **PyInstaller + PySide6 打包地雷（Phase 1 實測結論）：** 只要 `--collect-all qfluentwidgets` 就夠，**絕不加 `--exclude-module PySide6.*`**——那會打斷 PySide6 hook 的 plugin/qt.conf 處理導致啟動掛住。plugin 由 hook 收進 `PySide6/plugins/`（位於 Qt DLL 相對路徑，Qt 自動找得到，不需 qt.conf）。onedir 包約 179MB（Phase 9 可再瘦身：剔 unused plugins/translations）。EXE 啟動約 3-4s（PySide6 import 較重）。
- `health_monitor.py`（~2,185 行，從 ~9,842 降下來）是主要 refactor 目標。剩 11 個 `C901` 是既有複雜函式。
- Inventory exclusion：`excluded_inventory_slots`（set of ints），存 config JSON、preview 上畫藍色 overlay、F3 清理路徑都尊重。
- `_on_preview_click()` 處理 Canvas click → toggle exclusion → re-render。
- `_preview_meta` 存渲染影像尺寸供 click coordinate mapping。
- `updater_core.py` 移植自 ocr-trigger-clicker `core/12_updater.py`，但**尚無 delta 支援**（只整包 ZIP）——delta 產生端與用戶端樹狀套用是下一階段工作。
- 不要假設 `README_EN.md` 存在。要雙語公開文件就明確新增。

## Known Issues

- `PrintWindow`（GDI）對 Path of Exile 2（DirectX）回傳全黑 frame。
- `dxcam` / `mss` 都截合成桌面 — 被遮蓋/最小化視窗得到桌面內容而非遊戲內容。
- Activation guard（`_is_game_window_active()`）是目前 mitigation；沒有 Windows.Graphics.Capture（Win10+）就沒有可靠的 capture-before-activation 方案。

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
| `docs/` | 使用者 | 使用者導向說明（使用說明、運作原理、GitHub Pages） |
| `CHANGELOG.md` | 開發者 | 版本記錄（commitizen 自動維護） |
| `AGENTS.md` | AI agent | 本檔案 — 工作規範與流程 |

> **程式碼結構問題一律用 `codegraph_explore` 查，不讀靜態文件**——所有 Python 已被索引，動態查詢比靜態文件準確且省 token。CodeGraph 不索引 markdown/config/scripts；那些要問的放這裡。
>
> Runtime-generated（非 source，勿當程式碼改）：config / screenshots 已改存 `%LOCALAPPDATA%\GameTools_HealthMonitor\`（`get_user_data_dir()`，首次啟動會從舊位置 `src/` 或 exe 同層一次性複製遷移，只複製不刪除）。開發機舊的 `src/health_monitor_config.json` 可能還在（遷移來源殘留），勿當 source。

---

## 工作完成規範

每個獨立任務完成後應立即單獨 commit，不得累積多個不相關任務到同一個 commit。若同一輪對話涉及多個檔案的不同修改目的，必須拆成多次 git add + commit，逐一提交。

每次完成任何程式碼修改後，**必須主動依序跑完以下檢查清單，不得等待使用者提醒**。使用者是 vibe coding，不會提醒你做這些事——這份清單就是你的提醒：

1. **Lint / 格式化**（有改 `.py` 檔才需要，純文件/設定變更跳過）：
   ```powershell
   ruff check src/ --fix
   ruff format src/
   ```
   確認無殘留 error 才進下一步。

2. **pytest**（有改 `src/` 邏輯就必須，trivial 單行除外）：
   ```powershell
   python -m pytest --no-cov -q
   ```
   若改動含非 trivial 邏輯（分支、迴圈、解析、信任邊界/資料安全路徑），另跑該檔的 `__main__` self-check：
   ```powershell
   python -c "import sys,runpy; sys.path.insert(0,'src'); runpy.run_path('src/<檔案>', run_name='__main__')"
   ```

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

- Agent 的 shell 是 **PowerShell 5.1**（`pwsh` 7.6.5 在 PATH 可用但預設不跑）：**`&&` / `||` 不可用**，相依指令用 `;` + `if ($?)`；需要 7+ 語法時用 `pwsh -NoProfile -Command '...'` 包一層。
- 避免 `cmd.exe` batch idioms，除非是執行明確的 `.bat` 腳本。
- 中文 commit 訊息用 `-F` 暫存檔方式，避免引號截斷（見上方第 3 步）。

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

**懶惰程式碼沒有檢查就是未完成的。** 非平凡邏輯（有分支、迴圈、解析、信任邊界路徑）留下一個可執行的檢查——assert-based demo() / `__main__` self-check 或一個小 `test_*.py`。單行 trivial 程式碼不需要測試。

**不懶惰的地方：**
- 信任邊界的輸入驗證
- 防止資料遺失的錯誤處理（config 備份）
- 安全性
- 任何被明確要求的事項

---

## 可用工具

- **ruff**：lint/format 一律用它，不用 flake8 / black / isort。設定見 `pyproject.toml`（line-length 200、select E/F/W/C90）。常用：`ruff check src/ --fix`、`ruff format src/`、`ruff check src/ --statistics`。
- **pyright**：`pyright src/app.py src/qt/`。碰 `close_app()`、threading、Qt signal callbacks 前先跑。
- **pytest**：`python -m pytest --no-cov -q`。
- **commitizen（`cz`）**：`cz bump` 管理版本（同步 `_version.py` + `CHANGELOG.md`）。`cz commit` 互動失敗時改用 `git commit -F`。

---

## 一鍵工作流

1. 安裝依賴：`scripts/install_dependencies.bat`（uv 全域 + Python 3.13；含 `velopack`）
2. 從 source 或 EXE 執行：`Run.bat`
3. 建 EXE：`scripts/build_exe.bat`（PyInstaller onedir）
4. 測試建出的 EXE：`Run.bat`

發版額外需求：`.NET SDK 8+` 與 `dotnet tool install -g vpk`（Velopack CLI），僅開發機需要。

---

## 版本管理與發行流程

- 版本唯一事實來源：`src/_version.py`（commitizen 管理，同步 `qt/version.py` 與 `tools/build.py`）。目前 **v1.2.1**。
- **Dual-track 版本檢查**：≤ v1.2.0 走 GitHub API `/releases/latest`；≥ v1.2.1 走 `latest_version.txt`（raw.githubusercontent，無 API 限制）。GitHub API 只回傳非 pre-release、非 draft 的 release。
- **Velopack 更新鏈（v1.3+ 新安裝走這條）**：Setup.exe 安裝 → `auto_update.py` 經 `GithubSource` 檢查 GitHub Releases 的 nupkg 資產 → 下載（delta 自動處理）→ 重啟套用。channel 模型：stable＝預設 channel、搶先版＝beta channel（`--channel beta`）；client 端 config `"allow_prerelease": true` 對應 `ExplicitChannel("beta")`。
- **過渡期雙軌**：release.ps1 同時上傳舊鏈資產（ZIP + latest_version.txt + make_delta）與 Velopack 資產（Setup.exe + nupkg）。**方案 A 遷移**：v1.3.0 為最後一版支援舊鏈更新的版本，其 release notes 請用戶改下載 Setup.exe 安裝一次；過渡期結束後（v1.4+）刪除 `updater_main.py`、`tools/make_delta.py`、`latest_version*.txt` 機制與 `updater_core.py` 主體。

### 測試倉發版（`-TestRepo`，發版前實測）

測試倉 `Sid-1996/PathofExile-Sid-GameTools_HealthMonitor_release-test` 與主倉 Releases 完全隔離。client 端更新源解析順序（`auto_update.py resolve_repo_url()`）：環境變數 `GTOOLS_UPDATE_REPO` → `%LOCALAPPDATA%\GameTools_HealthMonitor\update_repo_override.txt` → 主倉。override 檔放在使用者資料目錄，可活過 Velopack 更新。

```powershell
# ── 發布端 ──
.\release.ps1 -TestRepo -Version 1.2.1-test.1          # 輪次 1：基準版（測試後手動還原 _version.py）
.\release.ps1 -TestRepo -Version 1.2.2-test.1          # 輪次 2：更新靶版（不清 dist/vpk → 自動產 delta）

# ── client 端切換到測試倉（一次）──
'https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor_release-test' |
    Out-File "$env:LOCALAPPDATA\GameTools_HealthMonitor\update_repo_override.txt" -Encoding utf8

# 移除 override 即回歸主倉
Remove-Item "$env:LOCALAPPDATA\GameTools_HealthMonitor\update_repo_override.txt"
```

**兩輪實測劇本**（驗證完整更新鏈 + config 存活）：
1. 輪次 1 發基準版 → 手動下載測試倉 Setup.exe 安裝 → 寫 override 檔 → 啟動確認版本
2. 輪次 2 發較高版本 → 啟動已安裝的程式 → 版本頁應偵測到新版 → 下載（delta 或整包）→ 重啟套用
3. 更新後驗證：版本號正確、config / override 檔仍在（使用者資料目錄不被 Velopack 清掉）

**channel 矩陣**（client 收不到更新的第一排查點）：`-Preview` 打包成 beta channel，安裝該版後需 config `"allow_prerelease": true` 才查得到 beta 資產；不加 `-Preview` 的 TestRepo 為 default channel，直接可測。

**注意事項**：
- TestRepo 版本號用 `-test.N` 後綴且**必須高於 client 目前版本**才會被偵測（SemVer 原生比較）
- `-TestRepo -Version X` 會改 `_version.py` 但不 commit——測試後手動還原（腳本結束會提醒）
- 測完回歸 stable：override 刪掉後若測試版 > 主倉 stable，不會自動降級；重裝一次主倉 Setup.exe 即可

### Pre-release 測試（不通知用戶）

1. `_version.py` 設 pre-release（如 `1.2.2-beta`）
2. `.\release.ps1 -Preview` — 建 EXE、vpk pack（beta channel）、建 GitHub **Pre-release**、只更新 `latest_version_prerelease.txt`
3. `latest_version.txt` 不動 → 現有用戶看不到
4. 你的 config `"allow_prerelease": true` → 偵測到 pre-release（beta channel），測試完整下載流程
5. 穩定後：`_version.py` = `1.2.2`，跑 `.\release.ps1`（一般）→ 更新 `latest_version.txt` → 通知所有用戶

### 穩定發版

跑 `.\release.ps1` — 更新 `latest_version.txt`、建正常 GitHub Release（含 Velopack Setup.exe/nupkg）、所有用戶下次啟動被通知。

### 關鍵規則

- **絕不把 pre-release 版本寫進 `latest_version.txt`** — 這會通知所有用戶
- `allow_prerelease` config 預設 `false` — 只有開發者應為測試設為 `true`
- `_parse_version()` 讓 pre-release 低於 stable（`1.2.2-beta` < `1.2.2`）（舊鏈專屬；Velopack 用 SemVer 原生比較）
- Velopack 只接受 SemVer 3 段版本（可帶 `-beta` 後綴），不能四段
- Velopack delta nupkg 只在同一 outputDir 存在前一版 full nupkg 時產生；`cleanup.bat` 清 dist 後首版無 delta，用戶端自動退回整包下載
- 使用者提到「發版 / release / 測試更新 / 不通知用戶 / pre-release」時：確認要 **Preview（先測）** 還是 **stable（發所有人）**，並提醒 `-Preview` flag 與 `allow_prerelease` config。

---

## 打包規則（Critical）

- `tools/build.py` 從 `src/` 與 `docs/` 收集 assets。建出內容：`GameTools_HealthMonitor.exe`、`auto_click.exe`、`updater.exe`、`language_packs.json`、`使用說明.md`、`啟動工具.bat`、`README.txt`。
- `updater_main.py` 建為 `updater.exe`（輕量、無 GUI deps）。（過渡期保留；Velopack 接管後刪除）
- **velopack 打包**：套件只含 `velopack.pyd` 原生擴充，PyInstaller import 分析會自動帶入，build.py 無需額外處理；發版時 `vpk pack`（release.ps1 [5.6]）以 `dist/GameTools_Package` 為 packDir 產生 Setup.exe / nupkg。
- 若 PyInstaller cache 在 Windows 被鎖（`WinError 5`），清 `build/GameTools_HealthMonitor` 重建。
- **PySide6 打包地雷**：只要 `--collect-all qfluentwidgets` 就夠，**絕不加 `--exclude-module PySide6.*`**（會打斷 hook 的 plugin/qt.conf 處理導致啟動掛住）。
- qfluentwidgets 1.11.3：`MessageBox` 無 static 方法（用原生 `QMessageBox`）；PySide6 6.11 enum 用完整命名空間（如 `Qt.AlignmentFlag.AlignCenter`）。

---

## commit 前安全檢查

- 無 secrets/tokens/private keys。
- 無意外鏡像目錄（例如重複的專案副本）。
- README 版本/連結符合目前 release 狀態。
- Build + launch smoke test 通過。
- worktree 混雜時只 stage request-scoped 檔案。

---

## Close 生命週期注意事項

- `close_app()` 是敏感路徑。小心 `_is_closing`、排程中的 `after(...)` callbacks、背景 threads。
- 背景 workers 在 shutdown 開始後不得碰 Qt widgets。
- 修改 startup/shutdown 邏輯時，重測正常關閉流程，不只測 app 啟動。

---

## Known Issues

- `PrintWindow`（GDI）對 Path of Exile 2（DirectX）回傳全黑 frame。
- 背景截圖已由 Windows.Graphics.Capture（`windows-capture` 套件，Win10 1903+）提供：被遮擋/失焦視窗仍可正確截取；mss 為自動降級（僅前景時正確）。**最小化視窗無法截圖**（Windows 限制，監控會暫停）。
- 操控一律在前景執行（`game_foreground` gate）：遊戲非前景時只分析、不按鍵，不背景注入。
- WGC 在「獨佔全螢幕」遊戲或無 frame 情境會降級 mss；mss 需視窗為前景才正確。
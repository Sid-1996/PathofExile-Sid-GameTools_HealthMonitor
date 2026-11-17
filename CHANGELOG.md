# 📋 更新日誌

所有重要的變更將記錄在此文件中。

格式基於 [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)，
並且本項目遵循 [Semantic Versioning](https://semver.org/spec/v2.0.0.html)。

## [1.4.1] - 2026-11-17

### Feat
- Frozen EXE 的 `--smoke` 診斷結果持久化至 smoke_result.txt，無 stdout/stderr 環境仍可取得成功與失敗證據
- 設定檔損壞時會自動從有效備份還原並修復正式設定檔，避免設定一次意外就全部遺失
- 應用程式啟動失敗或發生未捕捉例外時會留下診斷記錄，無法恢復時會明確提示使用者
- 應用程式會保留一份常駐日誌，方便日後回報問題時排查原因
- 新增深色／淺色外觀主題，可在「工具設置 > 外觀主題」切換，所有頁面、對話框與控制項皆套用同一主題，選擇會保存在設定檔並於下次啟動沿用

### Fix
- 設定檔與備份同時損壞時的提示更準確：說明損壞檔保留供診斷、設定檔將於下次儲存時被覆寫
- 修正測試 fixture 的 sys.argv 洩漏，避免後續測試誤判為 smoke 模式
- 設定從備份還原後的提示不會再被後續的設定載入清除，使用者一定會收到還原通知
- 設定儲存改用安全的整檔替換，寫入途中失敗時會保留原本可用的設定檔
- 設定儲存失敗時會即時回饋使用者，不再靜默忽略
- 修正版本資訊檔含 UTF-8 BOM 時更新檢查可能偵測不到新版本的問題

### Refactor
- 主題切換改為儲存後提示重新啟動程式，重新啟動後才套用完整主題，不再於執行期間即時切換

### Chore
- scripts\build_exe.bat 改用專案鎖定的 .venv，缺少環境或 PyInstaller 時明確失敗而非退回系統 Python
- pytest 於 session 期間使用隔離的 LOCALAPPDATA，不再寫入開發者正式使用者資料目錄
- release.ps1 正式發布流程改用專案鎖定的 .venv，缺少環境或必要套件時明確失敗而非退回系統 Python

## [1.4.0] - 2026-11-06

### Feat
- 新增簡體中文語言包 zh-cn（661 keys），並以系統語系自動區分繁簡
- GUI 語言選單補上簡體中文選項

### Fix
- 修正 Velopack 下載進度回呼參數（單一 int 0-100）

### Chore
- 升級依賴到最新安全版本並對齊版本號至 1.3.2

### Docs
- README 英文化主體並新增中簡繁多語快速入口
- 新增安全自建頁並重整三條路徑說明
- 使用說明與安全自建同步三語說明
- 領域模型詞彙落盤（GameWindow / Monitor / Combo / Inventory）
- 詞彙凍結 CaptureResult 三態 contract（wgc / mss / None）
- 同步斷鏈手動重裝指引至 README 與 GitHub Pages
- 補低調技術感謝（致謝開源專案）

## [1.3.2] - 2026-08-30

### Feat
- 工具設置新增「資料與重設」精簡版：開啟資料夾、重設為預設

### Fix
- 守衛型提醒改為右下浮層黃字，統一通知與攔截，減少彈窗層級
- 「重設為預設」改為一律重啟，雙路徑刪除截圖並清除記憶體預覽
- 「重設」改單一路徑僅清 LOCALAPPDATA，攔截保存避免刪後復活
- 修復 F9 全域暫停浮層不現與卡死（回歸跨執行緒問題）
- 移除 release.ps1 中不存在的 src/tab_version.py，導致發布提交失敗

## [1.3.1] - 2026-08-30（未正式發布）

### Feat
- 技能計時器全部切換綁定 Ins 熱鍵，並支援在設置頁改鍵
- 合併技能計時器全部按鈕並動態顯示熱鍵（含長鍵縮寫與截斷後備）

### Fix
- 去父化取物對話框並延後置頂旗標，修復關閉閃退並隱藏設定期間視窗
- 連續設定期間同時隱藏取物座標視窗，避免遮擋遊戲
- 修復設定取物座標 5 個座標後完成彈窗關閉即閃退
- 修復技能計時器英文語系仍顯示中文（\_t 誤判 [] 前綴）

### Perf
- \_internal 瘦身：排除 tkinter、PySide6 降級為 Essentials、cv2 改用 headless

### Refactor
- 中文導覽四字對齊、移除飛機圖示，「設置」改名為「工具設置」
- 移除英文「關於作者」飛機圖示

### Chore
- 正式發版改為先建 draft 再手動 publish
- latest_version.txt 以 ASCII 編碼重寫，避免 BOM 破壞舊鏈解析
- 緊急下架 v1.3.0，latest_version.txt 還原為 1.2.1
- 忽略根目錄建置產生的 delta_info.json 與 manifest.json

## [1.3.0] - 2026-08-30（已下架）

### Feat
- 介面全面移植到 PySide6 + qfluentwidgets（監控 / 連段 / 背包 / 設置 / 狀態 / 說明 / 版本 共 7 分頁）
- 背景截圖改用 Windows.Graphics.Capture（WGC），視窗被遮擋或失焦仍可截圖
- 血魔監控 ROI 全面等比化（全新 v2 JSON，同比例解析度自適應）
- 背包 UI 匹配改用 TM_CCOEFF_NORMED 多尺度，比對結果以 b64 內聯持久化
- F6 一鍵取物加入防呆與置頂浮層提示
- F10 未截到介面 UI 時一次警示（可選過濾，不阻擋監控）
- 主視窗底部新增狀態列（監控 / 連點 / 全域暫停 / 版本燈號，zh/en）
- 背景執行期沉默失敗補浮層（combo / 監控迴圈 / 自動點擊）
- 背景熱鍵浮層擴大與執行緒安全（F3 / F5 / F6 失敗取消補 toast）
- Velopack 更新鏈打通（Setup.exe + nupkg + feed + delta 差異更新）
- 使用者資料（config / screenshots）改存 LOCALAPPDATA 並一次性遷移
- 語言切換改為重啟生效，補齊詞彙與 ADR
- 設置分頁與熱鍵自定義（Issue #1：底區設置，F3 / F5 等可改）
- 補齊各頁控件 tooltip 並同步雙語語言包與語言切換重刷
- 記住上次選取的遊戲視窗並於啟動自動回填
- F9 / F10 開關補置頂浮層反饋（各顯示一次，不用切回 GUI 即知狀態）

### Fix
- 框選血量閃退，補正 region 正規化與等比 base 容錯
- 血魔監控頁等比化後內容消失，統一走 prop 現算入口恢復預覽與監控鏈路
- 背包預覽 label 加尺寸上限，預防同型 pixmap 迴圈
- 監控語言刷新對 QGroupBox 改 setTitle，修設置切語言閃退
- 血魔檢查「未設定介面 UI 區域」洗版，恢復戰鬥狀態檢查
- 熱鍵白名單移除 F12（F1-F11 為限），改 per-key 註冊 / combo 重綁 / 置底排序
- 浮層跨執行緒改 Signal queued，修 F9 / F5 / worker 浮層不顯示
- 英文語系下血條校準對話框疊影
- 版本頁在非 Velopack 安裝環境顯示可攜模式提示，不再誤導為「已是最新版」
- 修復 Velopack 更新鏈 feed 缺漏，補齊 releases.win.json 等必要資產上傳

### Refactor
- 全量 logging 重製（DEBUG 分級 + 時間戳 + `--debug` 開 log 檔）
- 移除啟動圖 splash（純外觀無實質用途，且造成啟動殘留麻煩）
- 移除搶先版開關（正式倉穩定版唯一，測試倉隔離預覽）
- 左側選單圖示優化（背包 SHOPPING_CART→BROOM、連段 GAME→ROBOT）

### Chore
- cleanup 重寫為 PowerShell 腳本，支援 dist/vpk 瘦身與 delta 鏈保留
- 修正 pyright 型別檢查 110 個錯誤（region / on_refresh 屬性型別註解）

### Docs
- README 改主推 Setup.exe，校正專案結構與 Tech Stack（Velopack / WGC / PySide6）
- 補自動更新章節（Velopack delta、測試倉、UserDataDir 存活）
- 同步 Velopack 更新架構與使用者資料新位置至工作規範與使用說明
- 補充視窗全螢幕提示（README / 使用說明 / 運作原理 / 官網）

## [1.2.1] - 2026-07-12

### Feat
- 程式內自動更新：版本檢查（`latest_version.txt`）→ 下載 ZIP → 解壓驗證 → `updater.exe` 替換重啟
- 新增 `updater_core.py`（更新引擎）、`updater_main.py`（獨立更新程序）
- 版本頁新增「下載更新」按鈕、進度條、取消支援
- 新增 `release.ps1` 一鍵發佈腳本（版本同步 → build → ZIP → tag → gh release）
- 新增 `latest_version.txt` 供 raw GitHub 版本檢查（無 API 限制）

### Fix
- F9 全域暫停現在正確停止 SkillTimer（`restore_slots()` 只恢復原本運行的槽位）
- 新增愛發電 Donate 按鈕
- 自動更新 ZIP 解壓精確匹配 `GameTools_HealthMonitor.exe`，避免 `auto_click.exe` 被誤選覆蓋主程式
- 版本更新通知窗口防重複（同一時間只顯示一個）
- 自動更新 ZIP 僅包含核心檔案，排除 `auto_click.exe`

### Chore
- `tools/build.py` 新增 `build_updater()` 步驟，updater.exe 打包進 release ZIP
- 全域暫停改用 `set[int]` 追蹤運行中槽位（非 boolean），精確還原狀態

## [1.2.0] - 2026-06-21

### Refactor
- 將 `health_monitor.py` 從 ~9,800 行拆分為 11 個獨立模組（↓80%）
- `tab_monitor` / `tab_inventory` / `tab_combo` / `tab_status` / `tab_help` / `tab_version` / `tab_about` — 各分頁獨立模組
- `app_state` / `auto_click_manager` / `usage_tracker` / `window_key_sender` — 共用邏輯模組
- F3 清包改為非阻塞背景執行緒，移植 F6 視窗管理邏輯
- 技能連段分頁 UI 重新設計為左右雙欄 + Tab 切換套組

### Fix
- 修復重構後大量跨模組屬性引用路徑錯誤（monitor_tab、inventory_tab）
- 修復 config 存取路徑錯誤（combo、monitor-interval、pickup-coordinates）
- 修復 capture_utils threading 問題（mss 跨執行緒 GDI handle）
- 修復啟動時視窗幾何跳動（withdraw/deiconify + 尊重已儲存尺寸）
- 修復 F3 清包在「保持最上方」模式下無法移除置頂的問題
- 修復測試清包結果無視覺回饋問題，現在顯示結果對話框
- 修復動態語言切換殘留：17 個 Tooltip、Canvas placeholder、Status tab widget 全部覆蓋

### Feat
- 關閉確認對話框新增「不再詢問」選項
- F10 切換監控時顯示 toast 通知
- F9 全域暫停時在遊戲視窗顯示持續 overlay
- 語言切換改為即時動態切換，無需重啟工具
- 版本更新通知新增「不再提醒此版本」選項
- 新增 `Run.bat` 統一啟動器，支援開發版與 EXE 版

### Chore
- 移除廢棄腳本（run_monitor.bat、launch_built_exe.bat、Light.bat）
- 更新 `tools/build.py` 打包範本，啟動工具.bat 支援 restart flag
- ruff C901 / F841 全面清零

## [1.1.0] - 2026-06-08

### 🐛 修復

- **CTRL+Click 連點根本原因修復**：移除 `ShellExecuteW runas` 強制提升管理員權限，改用 `subprocess.Popen` 繼承父進程完整性層級。原本以管理員權限啟動的 `auto_click.exe` 因 Windows UIPI 機制無法向普通權限的 PoE2 注入點擊，導致功能完全失效。現在兩者完整性層級一致，點擊正常運作。
- **更新通知視窗**：將 `ttk.Label` + 300 字截斷改為 `tk.Text` + `ttk.Scrollbar`，顯示完整 release notes，並支援拖曳調整視窗大小

### 🔧 優化

- 移除 `config_manager.py` 中未使用的使用時間追蹤副本函數（`load_usage_time_from_registry`、`save_usage_time_to_registry` 等 6 個函數）及相關死碼

## [1.0.9] - 2026-06-08

### 🐛 修復

- **CTRL+Click 連點功能修復**: 修復 UAC 管理員權限啟動後進程無法追蹤的問題（`ShellExecuteW runas` 後 `self.auto_click_process` 永遠為 `None`，導致程式無法終止 AHK 進程）
- 修復連點功能失敗時完全無使用者可見提示的問題（所有失敗路徑補入 `add_status_message` UI 提示）
- `stop_auto_click_ahk()` 同時支援 `psutil.Process` 與 `subprocess.Popen` 兩種物件類型

## [1.0.8] - 2026-06-08

### ✨ 新增

- **清包點擊模式切換**: 支援左鍵/右鍵兩種模式，左鍵適合一般存倉，右鍵適合大量重複通貨。設定自動儲存，保留到下次啟動
- **Tooltip 提示系統**: 抽離為 `utils.Tooltip` 獨立類別，支援延遲顯示。19 組按鈕/核取方塊加 tooltip（血魔監控/清包/連段/狀態/版本檢查分頁）
- **獨立視窗焦點監聽**: 背包預覽在遊戲視窗重新獲得焦點時自動刷新，非清包分頁時停止輪詢以節省資源
- **技能計時器模組**: 支援自訂技能槽位、毫秒級精度間隔、單鍵與組合鍵
- **版本集中管理**: 透過 `src/_version.py` 統一管理版本號，`build.py` 自動讀取

### 🐛 修復

- 修復 Canvas 白邊問題，技能組合與關於作者分頁滾輪無反應
- 修復未記錄背包 UI 時的分頁切換路由與焦點監聽同步問題
- 修復 F821 未定義名稱、F841 未使用變數/賦值
- 修復語言系統初始化與切換、模組化拆分後的 load_config 與 close lifecycle
- 修正錯誤的版本號 v1.0.9 → v1.0.8
- 補齊 f3_retry_final 英文翻譯，中英語言包完全對應 479 keys
- 更新版本資訊日期 2025年9月 → 2026年6月

### 🔧 優化

- 非清包分頁停止輪詢背包預覽（效能改善）
- 清包時若未檢測到背包 UI 則跳過預覽，顯示提示
- 移除偵測迴圈中的 debug print 陳述
- 自動修復 536 處 whitespace 和 f-string 問題
- 移除無用變數和無效賦值

### 🏗️ 內部整理

- 核心元件拆分為獨立模組（config_manager、language_system、utils、custom_dialogs、skill_timer）
- 移除 `src for DEVELOPER/` 相容層，簡化 build pipeline
- 停止追蹤 runtime 產生的螢幕截圖與設定備份
- 移除 .windsurf 工作流程與測試產物
- 清理重複文檔、更新 AGENTS.md
- 移除 `LOCAL_DEVELOPMENT.md` 追蹤

### 🛠️ Build

- `tools/build.py`: Pillow pyd 後綴動態偵測（cp310→cp312）、批次檔編碼問題修復、打包完成後自動清理 `build/` 目錄

## [歷史版本] - 2026-06-07

### ✨ 新增

- **背包排除格子功能**: 可在背包預覽中點擊格子切換排除狀態，F3 一鍵清包時自動跳過被排除的格子
- 預覽即時刷新：點擊排除後立即重新繪製顯示藍色標記
- 排除設定持久化：排除狀態自動儲存至 `health_monitor_config.json`
- **視窗激活保護**: 所有預覽（血量、魔力、背包）在遊戲視窗未激活時顯示「等待遊戲視窗激活」替代畫面，不再擷取被遮蓋或桌面內容
- **排除疊加層**: 使用 Canvas 疊加層獨立繪製排除標記，避免每次排除後重繪整張圖片
- 背包預覽支援更大的顯示尺寸（700×500）

### 🐛 修復

- 背包預覽改為 `tk.Canvas`，解決 `ttk.Label` 無法可靠接收滑鼠點擊事件的問題
- 監控迴圈改為扁平檢查（非 busy-wait），視窗失焦時 0.5 秒後自動重試
- Canvas 鎖定尺寸 = 圖片尺寸，避免父容器截斷第 12 欄格子
- 移除預覽擷取中的無用 debug print

### 📝 備註

- 已知問題：PrintWindow GDI 擷取在 Path of Exile 2 (DirectX) 上全面失效，無法用於無遮蓋擷取；dxcam 與 mss 在視窗被遮蓋/最小化時均無法取得遊戲內容

## [歷史版本] - 2026-05-15

### 🐛 修復

- 修復模組化拆分過程中 `load_config()` 縮排錯誤導致程式無法啟動的問題
- 修復 `self.config` 初始化順序，避免 `create_widgets()` 執行期間發生 AttributeError
- 修復關閉流程：正確取消 `after(...)` callback，防止視窗銷毀後殘留排程觸發
- 修復背景執行緒在關閉後仍嘗試操作 Tk widget 導致 RuntimeError 的問題
- 清除 36 處含 emoji 的 `print()` 輸出，修復 Windows cp950 終端機 UnicodeEncodeError
- 框選背包 UI 完成流程對齊其他框選按鈕，統一由 `finalize_selection_restore_gui()` 負責反饋
- 所有共享彈出視窗新增 `Return` / `KP_Enter` 熱鍵支援與預設按鈕高亮
- 修復拾取座標儲存後焦點未回到 GUI 的問題
- 修復單點座標擷取結束後設定視窗未重新取得 modal 狀態的問題
- 更新示範影片連結

### 📚 文檔

- 全面更新 `AGENTS.md`、`PROJECT_STRUCTURE.md`、`DEVELOPER_HANDBOOK.md` 至現況
- 更新 `.windsurf/workflows/` 所有 SOP 文件，反映模組化修復後的架構與驗證標準
- 新增 `modularization-recovery.md` 與 `safe-modularization.md` 作為後續維護參考

### 🏗️ 內部整理

- 清理 `tools/build.py` dead code，版本號更新至 1.0.8
- 整理 `src for DEVELOPER/`，移除與 `src/` 重複的檔案

## [歷史版本]7] - 2026-04-29

### GUI maintenance update
- Improved shared popup sizing and layout so long Traditional Chinese / English messages no longer hide confirmation buttons.
- Fixed the language-switch restart prompt and other confirmation popups to remain visible even when the parent window is hidden.
- Fixed the continuous pickup-coordinate setup flow after dialog parenting changes.
- Reduced perceived startup delay by deferring preview loading, hotkey setup, and heavy visual refresh work until after the main window is shown.
- Improved `Stop Monitoring` responsiveness by making the shutdown wait non-blocking for the Tk main thread.

### ✨ 新增
- 新增可中斷睡眠機制，提升停止響應速度
- 新增統一的選擇完成GUI恢復helper函數

### 🔧 優化
- 優化啟動載入邏輯，移除耗時的即時截圖操作
- 優化監控線程停止響應，延遲從1秒降至10毫秒
- 統一所有UI選擇流程的GUI恢復邏輯
- 改善系統資源管理和記憶體使用效率

### 🐛 修復
- 修復選擇完成後GUI卡住的問題
- 修復停止監控按鈕延遲響應的問題
- 修復多個選擇流程中的重複代碼問題

### 📚 文檔
- 更新專案結構文檔
- 更新版本說明和功能比較表
- 新增開發規範和貢獻指南

## [歷史版本]6] - 2025-10-01

### ✨ 新增
- 完整雙語言支援系統
- 載入視窗本地化
- 工具使用時間追蹤器

### 🔧 優化
- 載入順序優化
- 狀態訊息本地化完善

### 🐛 修復
- 修復無限迴圈問題
- 修復語言設定載入問題

## [歷史版本]5] - 2025-09-25

### ✨ 新增
- 一鍵清包系統全面升級
- 動態辨識機制
- 智能倉庫滿載檢測

### 🔧 優化
- 演算法優化
- 錯誤處理強化
- 性能提升

## [歷史版本]4] - 2025-09-23

### ✨ 新增
- 完整多語言支援系統
- 語言切換功能
- Windows註冊表儲存功能

### 🔧 優化
- 狀態消息系統完善
- 翻譯鍵擴充

## [歷史版本]3] - 2025-09-20

### ✨ 新增
- 技能連段系統
- 連段設定UI
- 熱鍵綁定功能

## [歷史版本]2] - 2025-09-18

### ✨ 新增
- 介面UI檢測系統
- 戰鬥狀態檢查
- UI相似度分析

## [歷史版本]1] - 2025-09-15

### ✨ 新增
- 背包UI檢測系統
- 背包顏色記錄功能
- 格子偏移調整

## [歷史版本]0] - 2025-09-10

### ✨ 新增
- 初始版本發佈
- 血量/魔力監控功能
- 基本UI介面
- 設定保存功能

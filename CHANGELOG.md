# 📋 更新日誌

所有重要的變更將記錄在此文件中。

格式基於 [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)，
並且本項目遵循 [Semantic Versioning](https://semver.org/spec/v2.0.0.html)。

## [1.0.9] - 2026-06-07

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

## [1.0.8] - 2026-05-15

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

## [1.0.7] - 2026-04-29

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

## [1.0.6] - 2025-10-01

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

## [1.0.5] - 2025-09-25

### ✨ 新增
- 一鍵清包系統全面升級
- 動態辨識機制
- 智能倉庫滿載檢測

### 🔧 優化
- 演算法優化
- 錯誤處理強化
- 性能提升

## [1.0.4] - 2025-09-23

### ✨ 新增
- 完整多語言支援系統
- 語言切換功能
- Windows註冊表儲存功能

### 🔧 優化
- 狀態消息系統完善
- 翻譯鍵擴充

## [1.0.3] - 2025-09-20

### ✨ 新增
- 技能連段系統
- 連段設定UI
- 熱鍵綁定功能

## [1.0.2] - 2025-09-18

### ✨ 新增
- 介面UI檢測系統
- 戰鬥狀態檢查
- UI相似度分析

## [1.0.1] - 2025-09-15

### ✨ 新增
- 背包UI檢測系統
- 背包顏色記錄功能
- 格子偏移調整

## [1.0.0] - 2025-09-10

### ✨ 新增
- 初始版本發佈
- 血量/魔力監控功能
- 基本UI介面
- 設定保存功能

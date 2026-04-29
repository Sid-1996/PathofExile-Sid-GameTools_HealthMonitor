# 📋 更新日誌

所有重要的變更將記錄在此文件中。

格式基於 [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)，
並且本項目遵循 [Semantic Versioning](https://semver.org/spec/v2.0.0.html)。

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
# Path of Exile Sid 輔助工具

> 以影像辨識與輸入模擬為核心的 Windows 工具，提供血魔監控、技能連段與背包自動化功能。  
> 不讀取遊戲記憶體、不修改遊戲檔案。

> 🌐 **Language / 語言**: [English](README_EN.md) | [中文](README.md)

![Windows](https://img.shields.io/badge/platform-Windows-blue?color=blue) ![GitHub release](https://img.shields.io/github/v/release/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor?color=green) ![GitHub downloads](https://img.shields.io/github/downloads/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/total?color=orange) ![GitHub stars](https://img.shields.io/github/stars/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor?color=yellow) ![GitHub forks](https://img.shields.io/github/forks/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor?color=lightgrey) ![GitHub last commit](https://img.shields.io/github/last-commit/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor?color=red) ![GitHub language count](https://img.shields.io/github/languages/count/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor?color=purple) ![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)

---

## [Facebook 專頁](https://www.facebook.com/talksometingshit/) | 中文說明

最新消息與教學更新請見 [Facebook](https://www.facebook.com/talksometingshit/)

---

## 使用方法：下載綠色版壓縮包，解壓後雙擊 GameTools_HealthMonitor.exe

• [GitHub下載](https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/releases), 免費網頁直鏈, 不要點擊下載 Source Code, 點擊下載壓縮包
• 可窗口化，可全屏，無需額外依賴

---

## ✨ 功能總覽

- 🩸 **血量 / 魔力監控**：可視化百分比 + 多閾值自動觸發
- ⚡ **技能連段**：自訂觸發鍵，順序與延遲全可調
- 🎒 **一鍵清包**：記錄背包佈局與顏色後自動清理
- 📦 **一鍵取物**：設定 5 個取物座標後按 F6 依序拾取
- 🖱️ **自動連點**：Ctrl + 左鍵啟動 / 停止
- 🧪 **即時預覽**：監控區域、狀態標記
- ⏸️ **全域暫停**：F9 立即停用所有熱鍵邏輯

---

## 📦 下載與使用

- 一般使用者：到 [Releases](https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/releases) 下載壓縮包並執行 `GameTools_HealthMonitor.exe`
- 開發者：直接使用原始碼（見下方「本機開發快速入口」）

## 🧭 本機開發快速入口

- 安裝依賴：`scripts/install_dependencies.bat`
- 直接跑 Python：`scripts/run_monitor.bat`
- 一鍵打包 EXE：`scripts/build_exe.bat`
- 打包後測試 EXE：`scripts/test_built_exe.bat`
- 檔案用途說明：`docs/檔案用途與建議流程.md`

---

| 熱鍵 | 功能 |
|------|------|
| F3 | 一鍵清包 |
| F5 | 快速回到藏身處 (回程邏輯) |
| F6 | 一鍵取物 (需先設定 5 點) |
| F9 | 全域暫停 / 解除 |
| F10 | 啟動 / 停止血魔監控 |
| F12 | 關閉工具 |
| Ctrl + 左鍵 | 自動連點切換 |

---

## 🚀 安裝與啟動

### 選項 1: 完整獨立 EXE 版本 (推薦)

1. 前往 [Releases 頁面](https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/releases) 下載最新版本的壓縮檔
2. 解壓縮到任意資料夾
3. 直接執行 `GameTools_HealthMonitor.exe`

**注意**: EXE 版本包含所有依賴項，文件較大 (~50MB+)

### 選項 2: 原始碼版本 (開發與自訂)

1. 下載源代碼: `git clone` 或下載 ZIP
2. 查看 `src/demo_health_monitor.py` (示範版本)
3. 執行 `scripts/run_monitor.bat` 或直接啟動 `src/health_monitor.py`

**說明**: 目前倉庫已包含主程式原始碼，可直接開發、除錯與自行打包。

---

## 📹 教學與更新

[![Facebook 專頁](https://img.shields.io/badge/Facebook-專頁-blue)](https://www.facebook.com/talksometingshit/)

> 📺 **建議先看 Facebook 專頁置頂貼文**，快速了解最新功能與設定方式。

---

## 🧪 初次設定建議

| 項目 | 操作 |
|------|------|
| 血/魔監控 | 框選區域 → 設百分比 → 開啟監控 |
| 取物座標 | 進入設定 → 按提示依序移動滑鼠 + Enter 確認 |
| 一鍵清包 | 截取背包 UI → 記錄淨空顏色 → 測試 F3 |
| 技能連段 | 定義觸發鍵 → 輸入技能序列 → 設定延遲 → 啟用 |
| 自動連點 | 按住 Ctrl+左鍵 切換狀態 |

---

## 🧠 功能摘要

### 血魔監控

- 每次擷取指定區域影像並估算百分比
- 多段觸發 (例如 80% / 50% / 30%)
- 觸發冷卻避免過度輸出按鍵

### 技能連段

- 最多多組獨立配置
- 每步自訂延遲，適配技能、網路延遲

### 一鍵清包 / 取物

- 透過顏色差異判斷有效格子
- 取物依序點擊既定 5 點，適合固定擺放流程

### 自動連點

- 高頻點擊 (固定短間隔)，保護滑鼠按鍵壽命，提高操作舒適度

---

## ❓ FAQ (精簡)

**Q: 為什麼熱鍵沒反應?** 可能曾經全域暫停 (F9)，再按一次恢復。

**Q: 清包沒有作用?** 確認已截取 UI 並記錄淨空顏色，且背包視窗已開。

**Q: 取物功能沒執行?** 確認已設定完 5 個座標，並位於正確場景。

**Q: 監控數值不準?** 重新框選，確保選的是純色區段，避免透明與動態特效。

**Q: 防毒誤報?** 將 EXE 加入白名單，因為有螢幕擷取與鍵盤監聽行為。

---

## 🗂️ 版本與更新

- 最新發布說明：[`RELEASE_NOTES.md`](RELEASE_NOTES.md)
- 最新版本請前往：[Releases 頁面](https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/releases)

---

## ⚠️ 免責聲明

本軟體是一個外部工具，專為教育和學習目的而開發。它僅通過螢幕截圖和模擬鍵盤輸入與遊戲交互，不會修改任何遊戲文件或代碼，也不會讀取遊戲記憶體。

本軟體僅供個人學習交流使用，僅限於個人遊戲帳號，不得用於任何商業或營利性目的。開發者團隊擁有本項目的最終解釋權。使用本軟體產生的所有問題與本項目及開發者團隊無關。若您發現商家使用本軟體進行代練並收費，這是商家的個人行為，本軟體不授權用於代練服務，產生的問題及後果與本軟體無關。本軟體不授權任何人進行售賣，售賣的軟體可能被加入惡意代碼，導致遊戲帳號或電腦資料被盜，與本軟體無關。

**重要提醒**：根據 Grinding Gear Games 的《Path of Exile》服務條款，遊戲可能禁止使用任何第三方自動化工具。使用此工具存在帳號風險，請謹慎評估。

### 風險警告

1. **帳號風險**：使用本工具可能導致帳號被封。請在了解風險後再使用。
2. **個人責任**：任何因使用本工具導致的帳號問題，均由使用者自行承擔。
3. **合規使用**：請確保在當地法律允許的範圍內使用本工具。

---

## 🤝 支持與社群

### 聯繫方式

- **GitHub Issues**：[回報問題與建議](https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/issues)
- **GitHub 官方倉庫**：[https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor](https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor)
- **Discord**：(暫無連結)

---

## 📂 專案結構

- `src/`: 主程式與語言包（主要開發目錄）
- `src for DEVELOPER/`: 舊版相容目錄（供既有流程 fallback）
- `scripts/`: 一鍵安裝、運行、打包、測試腳本
- `tools/`: 打包流程與工具
- `docs/`: 使用指南與技術文檔

---

## 致謝

- [OpenCV](https://opencv.org/) - 圖像處理核心技術
- [Python Keyboard](https://github.com/boppreh/keyboard) - 全域熱鍵監聽
- [PyAutoGUI](https://pyautogui.readthedocs.io/) - 滑鼠鍵盤自動化
- [PyGetWindow](https://github.com/asweigart/PyGetWindow) - 視窗管理

---

## ⭐ 支持

如果覺得有幫助，可以：

- Star 專案
- 回報 Issue
- 分享給朋友

---

> 簡潔版 README，完整教學請參考 `docs/使用指南.md` 與 `docs/運作原理.md`。





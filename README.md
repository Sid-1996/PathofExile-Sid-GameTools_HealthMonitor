# ![Health Monitor Icon](github/assets/GameTools_HealthMonitor.ico) Path of Exile Sid遊戲工具

## 基於圖像識別的 Path of Exile 自動化, 使用 Windows 接口模擬用戶點擊, 無讀取遊戲內存或侵入修改遊戲文件/數據

![Windows](https://img.shields.io/badge/platform-Windows-blue?color=blue) ![GitHub release](https://img.shields.io/github/v/release/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor?color=green) ![GitHub downloads](https://img.shields.io/github/downloads/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/total?color=orange) ![GitHub stars](https://img.shields.io/github/stars/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor?color=yellow) ![GitHub forks](https://img.shields.io/github/forks/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor?color=lightgrey) ![GitHub last commit](https://img.shields.io/github/last-commit/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor?color=red) ![GitHub language count](https://img.shields.io/github/languages/count/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor?color=purple) ![Milestone: 1000⭐=Open Source](https://img.shields.io/badge/Milestone-1000⭐=Open_Source-gold?style=flat-square) ![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)

---

## [教學影片](https://www.youtube.com/watch?v=qRe8GODRx98) | 中文說明

演示和教程 [YouTube](https://www.youtube.com/watch?v=qRe8GODRx98)

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

## 🎯 開源里程碑目標

### 🌟 **1000 星星 = 完整開源主工具源代碼！**

我們承諾：當這個專案獲得 **1000 個 GitHub 星星** ⭐ 時，將會：

- 🔓 **開放主工具完整源代碼** (`src/health_monitor.py` 等核心文件)
- 📚 **提供詳細的技術文檔** 和開發指南
- 🛠️ **分享編譯和打包腳本**
- 🤝 **歡迎社群貢獻和改進**

**目前進度：**

![GitHub stars](https://img.shields.io/github/stars/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor?color=yellow&style=for-the-badge) / 1000 ⭐

**加入我們一起達成目標！**

- ⭐ **給專案一個星星** 來支持我們
- 🔄 **分享給朋友** 讓更多人知道
- 💬 **在 Issues 中提供建議** 幫助改進

> 💡 **為什麼設定這個目標？** 我們相信開源能帶來更好的工具和更強大的社群。您的支持將幫助我們邁向完全透明的開發！

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

### 選項 1: 輕量級版本 (推薦用於 GitHub 分發)

1. 確保已安裝 Python 3.8+
2. 下載源代碼: `git clone` 或下載 ZIP
3. 雙擊 `scripts/install_dependencies.bat` 安裝依賴項
4. 雙擊 `scripts/run_monitor.bat` 或執行 `python src/health_monitor.py`

**優點**: 文件小 (僅 ~360KB)，適合 GitHub 分發

### 選項 2: 輕量級啟動器 (最小化)

1. 下載源代碼和 `scripts/GameTools_HealthMonitor_Light.bat`
2. 雙擊 `scripts/GameTools_HealthMonitor_Light.bat`
3. 腳本會檢查 Python 和依賴項，然後啟動程序

**優點**: 極輕量 (僅 766KB)，但需要安裝依賴項

### 選項 3: 完整獨立 EXE 版本 (v1.0.3)

1. 從 Releases 下載壓縮檔 `GameTools_HealthMonitor_v1.0.3.zip`
2. 解壓縮到任意資料夾
3. 直接執行 `GameTools_HealthMonitor.exe`

**注意**: EXE 版本包含所有依賴項，文件較大 (~50MB+)

---

## 📹 工具教學影片

[![YouTube 教學影片](https://img.shields.io/badge/YouTube-教學影片-red)](https://www.youtube.com/watch?v=qRe8GODRx98)

> 📺 **推薦先觀看教學影片**，快速了解工具功能與設定方法！

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

- 最新發布說明：`RELEASE_NOTES.md`
- 當前版本：v1.0.3（雙重按鍵發送機制優化 / GUI 凍結與熱鍵恢復修復 / 完整打包 / 零依賴 / 分頁美化優化 / 功能修復完善）

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

本專案是完全開源的 Path of Exile 輔助工具：

### 🔧 技術分享特性

- ✅ 提供開源源代碼，供學習參考
- ✅ 無功能限制，所有功能永久免費
- ✅ 歡迎技術交流和學習討論

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





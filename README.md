# Path of Exile Sid 輔助工具 / GameTools Health Monitor
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0) ![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/total) [![GitHub Pages](https://img.shields.io/badge/Web-GitHub%20Pages-58a6ff?style=flat-square&logo=github)](https://sid-1996.github.io/PathofExile-Sid-GameTools_HealthMonitor/)

> 以影像辨識與輸入模擬為核心的 Windows 工具  
> External automation research toolkit for Path of Exile  
> 🌐 <a href="https://sid-1996.github.io/PathofExile-Sid-GameTools_HealthMonitor/">GitHub Pages 介紹頁 / Project Site</a>

基於 Python + AutoHotkey + OCR / Image Recognition 所打造的 UI 自動化研究工具。

Built with Python + AutoHotkey + OCR / Image Recognition.

---

## 🌐 Language / 語言

This README uses both Traditional Chinese and English.

本 README 使用中英雙語撰寫。


---

# 📹 Demo Showcase / 示範影片

Dailymotion:

https://www.dailymotion.com/video/xa9cau2

---

# 📦 Download / 下載

GitHub Releases:

https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/releases

下載後解壓即可執行：

```txt
GameTools_HealthMonitor.exe
```

No additional dependencies required.

---

# ✨ Features / 功能總覽

## 🩸 Health / Mana Monitoring  
血量 / 魔力監控

- Real-time percentage detection  
- Multi-threshold trigger system  
- Cooldown protection  

- 即時百分比判定
- 多閾值觸發
- 觸發冷卻保護

---

## ⚡ Skill Automation  
技能連段

- Custom skill sequence
- Adjustable delays
- Multiple profiles

- 自訂技能序列
- 自訂延遲
- 多組配置

---

## 🎒 Inventory Automation  
背包自動化

- One-key inventory cleanup
- Fixed-point pickup
- UI color recognition

- 一鍵清包
- 固定點取物
- UI 顏色辨識

---

## 🖱️ Auto Clicker  
自動連點

```txt
Ctrl + Left Click Toggle
```

---

## ⏱️ Skill Timer  
技能計時器

- Custom skill slot configuration
- Millisecond-precision intervals
- Single key and modifier+key support

- 自訂技能槽位配置
- 毫秒級精度間隔
- 支援單鍵與組合鍵

---

## ⏸️ Global Controls / 全域控制

```txt
F9  = Pause / Resume
F12 = Exit
```

---

# ⌨️ Hotkeys / 熱鍵

| Key | Action |
|---|---|
| F3 | Clear Inventory / 一鍵清包 |
| F5 | Return Hideout / 回藏身處 |
| F6 | Pickup Sequence / 一鍵取物 |
| F9 | Pause / Resume |
| F10 | Health Monitor Toggle |
| F12 | Exit |
| Ctrl + Left Click | Auto Click |

---

# 🚀 Development / 開發

## Install Dependencies / 安裝依賴

```bat
scripts\install_dependencies.bat
```

---

## Run / 執行

```bat
scripts\run_monitor.bat
```

---

## Build EXE / 打包 EXE

```bat
scripts\build_exe.bat
```

---

## Test Built EXE / 測試 EXE

```bat
scripts\launch_built_exe.bat
```

---

# 📂 Project Structure / 專案結構

```txt
src/
  health_monitor.py      # Main application
  config_manager.py      # Config load/save
  language_system.py     # Translation system
  custom_dialogs.py      # Shared dialogs
  utils.py               # Runtime utilities
  skill_timer.py         # Skill timer module
  language_packs.json    # UI strings
scripts/                 # One-click workflows
tools/                   # Build pipeline
docs/                    # User/developer docs
```

---

# 🧠 Tech Stack / 技術使用

- OpenCV
- PyAutoGUI
- keyboard
- PyGetWindow
- AutoHotkey

---

# 🤝 Community / 社群

## Facebook Page

https://www.facebook.com/talksometingshit/

---

## GitHub Issues

https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/issues

---

# ⚠️ Disclaimer / 免責聲明

This software is provided for:

- educational research
- automation study
- image recognition experimentation

本軟體僅供：

- 教育研究
- 自動化學習
- 圖像辨識實驗

使用。

---

This software does NOT:

- modify game files
- inject code
- access game memory

本工具不會：

- 修改遊戲檔案
- 注入程式
- 讀取遊戲記憶體

---

Usage may violate the Terms of Service of Grinding Gear Games.

Use at your own risk.

使用本工具可能違反 Grinding Gear Games 的服務條款。

請自行承擔使用風險。

---

# 📜 License / 授權

AGPL-3.0

---

# ⭐ Support / 支持

If this project helped you:

- Star the repository
- Report issues
- Submit improvements

如果這個專案有幫助到你：

- 歡迎 Star
- 回報 Issue
- 提交改進

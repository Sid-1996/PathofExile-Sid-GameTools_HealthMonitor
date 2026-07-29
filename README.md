<p align="center">
  <img src="assets/GameTools_HealthMonitor.ico" width="100" alt="Logo">
</p>

<h1 align="center">GameTools Health Monitor</h1>

<p align="center">
  <i>Path of Exile Sid 輔助工具</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Version-1.2.1-3fb950?style=flat-square" />
  <img src="https://img.shields.io/badge/License-AGPL%20v3-blue?style=flat-square" />
  <img src="https://img.shields.io/github/downloads/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/total?style=flat-square" />
  <a href="https://sid-1996.github.io/PathofExile-Sid-GameTools_HealthMonitor/"><img src="https://img.shields.io/badge/Web-GitHub%20Pages-58a6ff?style=flat-square&logo=github" /></a>
</p>

<p align="center">
  以影像辨識與輸入模擬為核心的 Windows 自動化研究工具<br>
  <sub>External automation research toolkit for Path of Exile</sub>
</p>

---

## 📹 Demo / 示範影片

<p align="center">
  <a href="https://www.dailymotion.com/video/xa9cau2">
    <img src="https://www.dailymotion.com/img/video/thumb.png" width="480" alt="Demo Video" />
  </a>
</p>

<p align="center">
  <a href="https://www.dailymotion.com/video/xa9cau2">▶️ 在 Dailymotion 觀看完整示範</a>
</p>

---

## ✨ Features / 功能總覽

<table>
  <tr>
    <td><b>🩸 血量/魔力監控</b><br>即時百分比判定 · 多閾值觸發 · 冷卻保護</td>
    <td><b>⚡ 技能連段</b><br>自訂序列 · 可調延遲 · 多組配置</td>
  </tr>
  <tr>
    <td><b>🎒 背包自動化</b><br>一鍵清包 · 固定點取物 · UI 顏色辨識</td>
    <td><b>🖱️ 自動連點</b><br>Ctrl + 左鍵切換</td>
  </tr>
  <tr>
    <td><b>⏱️ 技能計時器</b><br>毫秒級精度 · 支援組合鍵</td>
    <td><b>⏸️ 全域控制</b><br>F9 暫停 · F12 離開</td>
  </tr>
</table>

---

## ⌨️ Hotkeys / 熱鍵

| Key | Action / 操作 |
|:---:|:---|
| `F3` | 一鍵清包 / Clear Inventory |
| `F5` | 回藏身處 / Return Hideout |
| `F6` | 一鍵取物 / Pickup Sequence |
| `F9` | 暫停 / Resume |
| `F10` | 血量監控開關 / Health Monitor Toggle |
| `F12` | 離開 / Exit |
| `Ctrl + Click` | 自動連點 / Auto Click |

---

## 📦 Download / 下載

<p align="center">
  <a class="btn" href="https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/releases">
    <img src="https://img.shields.io/badge/⬇️_下載_v1.2.1-3fb950?style=for-the-badge" alt="Download" />
  </a>
</p>

<p align="center">
  <sub>下載後解壓即可執行，無需額外安裝依賴 · Windows 10 / 11</sub>
</p>

---

## 🚀 Quick Start / 快速開始

### 從原始碼執行
```bat
scripts\install_dependencies.bat
Run.bat
```

### 打包 EXE
```bat
scripts\build_exe.bat
```

### 測試打包結果
```bat
Run.bat
```

---

## 📂 Project Structure / 專案結構

<details>
<summary>展開查看完整結構</summary>

```
src/
  health_monitor.py          # Main application
  tab_monitor.py             # Health/mana monitor tab
  tab_inventory.py           # Inventory clear + pickup tab
  tab_combo.py               # Skill combo tab
  tab_version.py             # Version check + auto-update
  tab_about.py               # About tab
  config_manager.py          # Config load/save
  language_system.py         # Translation system
  custom_dialogs.py          # Shared dialogs
  skill_timer.py             # Skill timer module
  app_state.py               # Shared state container
  utils.py                   # Runtime utilities
  updater_core.py            # Update engine
  language_packs.json        # UI strings
scripts/                     # One-click workflows
tools/build.py               # Build pipeline
docs/                        # User/developer docs
updater_main.py              # Standalone updater
release.ps1                  # One-click publish script
```

</details>

---

## 🧠 Tech Stack / 技術使用

<p>
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/OpenCV-5C3EE8?style=flat&logo=opencv&logoColor=white" />
  <img src="https://img.shields.io/badge/AutoHotkey-334455?style=flat&logo=autohotkey&logoColor=white" />
  <img src="https://img.shields.io/badge/PyInstaller-FDAD04?style=flat&logo=pyinstaller&logoColor=black" />
  <img src="https://img.shields.io/badge/tkinter-0-9CA3AF?style=flat&logo=python&logoColor=white" />
</p>

---

## 🤝 Community / 社群

<p>
  <a href="https://www.facebook.com/talksometingshit/"><img src="https://img.shields.io/badge/Facebook-1877F2?style=flat&logo=facebook&logoColor=white" /></a>
  <a href="https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/issues"><img src="https://img.shields.io/badge/GitHub%20Issues-1a1a1a?style=flat&logo=github&logoColor=white" /></a>
  <a href="https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor"><img src="https://img.shields.io/badge/⭐_Star-3fb950?style=flat&logo=github&logoColor=white" /></a>
</p>

---

## ☕ Support / 贊助

如果我的工具對你有幫助，歡迎用你喜歡的方式支持我。

If my tools help you, feel free to support me in your own way.

[![Ko-fi](https://img.shields.io/badge/Ko--fi-FF5E5B?style=flat&logo=kofi&logoColor=white)](https://ko-fi.com/K3K11KMXOL)
[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=flat&logo=paypal&logoColor=white)](https://www.paypal.com/ncp/payment/GJS4D5VTSVWG4)
[![ECPay](https://img.shields.io/badge/ECPay-8A2BE2?style=flat&logo=amazonpay&logoColor=white)](https://p.ecpay.com.tw/E0E3A)
[![愛發電](https://img.shields.io/badge/愛發電-946CE6?style=flat&logo=afdian&logoColor=white)](https://afdian.com/a/sid-1996)

---

## ⚠️ Disclaimer / 免責聲明

<details>
<summary>點擊查看完整免責聲明</summary>

本軟體僅供教育研究、自動化學習與圖像辨識實驗使用。

This software is provided for educational research, automation study, and image recognition experimentation.

本工具不會修改遊戲檔案、不會注入程式碼、不會讀取遊戲記憶體。

This software does NOT modify game files, inject code, or access game memory.

使用本工具可能違反 Grinding Gear Games 的服務條款，請自行承擔使用風險。

Usage may violate the Terms of Service of Grinding Gear Games. Use at your own risk.

</details>

---

<p align="center">
  <sub>License: <a href="https://www.gnu.org/licenses/agpl-3.0">AGPL-3.0</a> · Built with ❤️ by Sid-1996</sub>
</p>

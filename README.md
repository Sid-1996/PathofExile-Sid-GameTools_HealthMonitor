<p align="center">
  <img src="assets/GameTools_HealthMonitor.ico" width="100" alt="Logo">
</p>

<h1 align="center">GameTools Health Monitor</h1>

<p align="center">
  <i>Path of Exile Sid 輔助工具</i>
</p>

<p align="center">
  <img src="https://img.shields.io/github/v/release/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor?style=flat-square&label=Version" />
  <img src="https://img.shields.io/badge/License-AGPL%20v3-blue?style=flat-square" />
  <img src="https://img.shields.io/github/downloads/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/total?style=flat-square" />
  <a href="https://sid-1996.github.io/PathofExile-Sid-GameTools_HealthMonitor/"><img src="https://img.shields.io/badge/Web-GitHub%20Pages-58a6ff?style=flat-square&logo=github" /></a>
</p>

<p align="center">
  以影像辨識與輸入模擬為核心的 Windows 自動化研究工具<br>
  <sub>External automation research toolkit for Path of Exile</sub>
</p>

<p align="center">
  <img src="https://github-view-counter.vercel.app/api?username=PathofExile-Sid-GameTools_HealthMonitor&label=Repo+views&color=%23f85149&style=square" alt="Repo Views" />
</p>

---

## 📹 Demo / 示範影片

<p align="center">
  <a href="https://www.dailymotion.com/video/xa9cau2">
    <img src="https://img.shields.io/badge/▶️_觀看完整示範-0066DC?style=for-the-badge&logo=dailymotion&logoColor=white" alt="Watch on Dailymotion" />
  </a>
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
    <img src="https://img.shields.io/badge/⬇️_下載_Setup.exe-3fb950?style=for-the-badge" alt="Download Setup.exe" />
  </a>
</p>

<p align="center">
  <sub>⚠️ <b>v1.2.1（含更早）請務必手動重裝</b>：自動更新會在下載階段失敗，請下載 <code>Sid.GameToolsHealthMonitor-win-Setup.exe</code> 覆蓋安裝（設定保留）· Windows 10 / 11<br>新用戶亦請下載 <code>Setup.exe</code>（推薦） — Users on v1.2.1 or earlier must reinstall manually with <code>Setup.exe</code></sub>
</p>

---

## 🚀 Quick Start / 快速開始

> ⚠️ **遊戲視窗設定**：請將 Path of Exile 設為「視窗全螢幕」或「視窗模式」，工具才能正確背景截圖與顯示提示浮層。

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

### 資料與重設 / Data

- 設定檔：`%LOCALAPPDATA%\GameTools_HealthMonitor\health_monitor_config.json`（`*.backup` 自動備份、`screenshots\` 截圖）
- 工具內 `工具設置 > 資料與重設` 可 `開啟資料夾 / 複製路徑 / 重設為預設`（截圖預設保留，勾選才一併刪除）

### 移除 / Uninstall

- **Setup.exe 安裝**：`Windows 設定 > 應用程式 > 已安裝應用程式 > Sid.GameToolsHealthMonitor > 解除安裝`，再手動刪 `%LOCALAPPDATA%\GameTools_HealthMonitor`（如需清截圖/設定）
- **ZIP 可攜**：刪解壓目錄 + 上述資料夾

---

## 📂 Project Structure / 專案結構

<details>
<summary>展開查看完整結構</summary>

```
src/
  app.py                     # Qt (PySide6) entry point
  qt/                        # Qt GUI layer (main_window + 7 tabs)
  monitor_analyzer.py        # Health/mana HSV analysis + triggers
  capture_utils.py           # Screenshot + mss singleton
  image_utils.py             # Image drawing/resize/preview
  inventory_utils.py         # Inventory slot analysis
  config_manager.py          # Config load/save + backup
  language_system.py         # Translation system
  utils.py                   # Runtime utilities + get_user_data_dir + F12 emergency close
  auto_click_manager.py      # Auto-click (AHK) manager
  usage_tracker.py           # Usage time tracking
  window_key_sender.py       # Window-focus key sending
  auto_update.py             # Velopack GithubSource 更新引擎（主鏈，≥ v1.2.4-test）
  updater_core.py            # Legacy update engine（過渡期保留，v1.4+ 刪除）
  language_packs.json        # UI strings
scripts/                     # One-click workflows
tools/build.py               # Build pipeline (PyInstaller onedir + 旁置資源)
docs/                        # User/developer docs
updater_main.py              # Standalone updater (Legacy, 過渡期保留)
release.ps1                  # One-click publish (stable / -Preview / -TestRepo)
```

</details>

---

## 🧠 Tech Stack / 技術使用

<p>
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/OpenCV-5C3EE8?style=flat&logo=opencv&logoColor=white" />
  <img src="https://img.shields.io/badge/PySide6-41CD52?style=flat&logo=qt&logoColor=white" />
  <img src="https://img.shields.io/badge/Velopack-00A6ED?style=flat&logo=windows&logoColor=white" />
  <img src="https://img.shields.io/badge/Windows.Graphics.Capture-0078D4?style=flat&logo=windows&logoColor=white" />
  <img src="https://img.shields.io/badge/AutoHotkey-334455?style=flat&logo=autohotkey&logoColor=white" />
  <img src="https://img.shields.io/badge/PyInstaller-FDAD04?style=flat&logo=pyinstaller&logoColor=black" />
  <img src="https://img.shields.io/badge/tkinter-0-9CA3AF?style=flat&logo=python&logoColor=white" />
</p>

---

## 🙏 Acknowledgements / 致謝

感謝以下開源專案，讓這個小工具得以專注在 PoE 自動化本質，而無需重造輪子。

Thanks to the open source projects that let this small toolkit focus on the task itself.

- Velopack — 安裝與更新
- PySide6 / qfluentwidgets — 介面
- OpenCV — 影像辨識
- Windows.Graphics.Capture — 視窗擷取
- AutoHotkey / PyInstaller — 連點與打包

如有遺漏，歡迎提醒。

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

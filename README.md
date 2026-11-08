<p align="center">
  <img src="assets/GameTools_HealthMonitor.ico" width="100" alt="Logo">
</p>

<h1 align="center">GameTools Health Monitor</h1>

<p align="center">
  <i>Path of Exile Sid 輔助工具</i>
</p>

<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/English-Current-2ea44f?style=flat-square" alt="English" /></a>
  <a href="README.zh-TW.md"><img src="https://img.shields.io/badge/%E7%B9%81%E9%AB%94%E4%B8%AD%E6%96%87-0969da?style=flat-square" alt="繁體中文" /></a>
  <a href="README.zh-CN.md"><img src="https://img.shields.io/badge/%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87-0969da?style=flat-square" alt="简体中文" /></a>
</p>

<p align="center">
  <img src="https://img.shields.io/github/v/release/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor?style=flat-square&label=Version" />
  <img src="https://img.shields.io/badge/License-AGPL%20v3-blue?style=flat-square" />
  <img src="https://img.shields.io/github/downloads/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/total?style=flat-square" />
  <a href="https://sid-1996.github.io/PathofExile-Sid-GameTools_HealthMonitor/"><img src="https://img.shields.io/badge/Web-GitHub%20Pages-58a6ff?style=flat-square&logo=github" /></a>
</p>

<p align="center">
  A Windows automation research toolkit built on image recognition and input simulation<br>
  <sub>External automation research toolkit for Path of Exile</sub>
</p>

<p align="center">
  <img src="https://github-view-counter.vercel.app/api?username=PathofExile-Sid-GameTools_HealthMonitor&label=Repo+views&color=%23f85149&style=square" alt="Repo Views" />
</p>

---

## 📹 Demo

<p align="center">
  <a href="https://www.dailymotion.com/video/xa9cau2">
    <img src="https://img.shields.io/badge/▶️_Watch_Full_Demo-0066DC?style=for-the-badge&logo=dailymotion&logoColor=white" alt="Watch on Dailymotion" />
  </a>
</p>

---

## ✨ Features

<table>
  <tr>
    <td><b>🩸 Health / Mana Monitor</b><br>Real-time percent detection · Multi-threshold triggers · Cooldown protection</td>
    <td><b>⚡ Skill Combos</b><br>Custom sequences · Adjustable delays · Multiple profiles</td>
  </tr>
  <tr>
    <td><b>🎒 Inventory Automation</b><br>One-click clear · Fixed-point pickup · UI color recognition</td>
    <td><b>🖱️ Auto Click</b><br>Toggle with Ctrl + Left Click</td>
  </tr>
  <tr>
    <td><b>⏱️ Skill Timers</b><br>Millisecond precision · Supports key combinations</td>
    <td><b>⏸️ Global Control</b><br>F9 Pause · F12 Exit</td>
  </tr>
</table>

---

## 🖼️ Screenshots

<p align="center">
  <b>Health Monitor</b><br>
  <img src="assets/screenshots/01-health-monitor.png" width="800" alt="Health Monitor">
</p>

<p align="center">
  <b>Inventory Automation</b> · <b>Skill Combos</b><br>
  <img src="assets/screenshots/02-inventory.png" width="800" alt="Inventory Automation"><br>
  <img src="assets/screenshots/03-combo.png" width="800" alt="Skill Combos">
</p>

<p align="center">
  <b>Status · Help · Version</b><br>
  <img src="assets/screenshots/04-status.png" width="800" alt="Status">
  <img src="assets/screenshots/05-help.png" width="800" alt="Help">
  <img src="assets/screenshots/06-version.png" width="800" alt="Version">
</p>

<p align="center">
  <b>About · Settings</b><br>
  <img src="assets/screenshots/07-about.png" width="800" alt="About"><br>
  <img src="assets/screenshots/08-settings.png" width="800" alt="Settings">
</p>

---

## ⌨️ Hotkeys

| Key | Action |
|:---:|:---|
| `F3` | Clear Inventory |
| `F5` | Return to Hideout |
| `F6` | Pickup Sequence |
| `F9` | Pause / Resume |
| `F10` | Health Monitor Toggle |
| `F12` | Exit |
| `Ctrl + Click` | Auto Click |

---

## 📦 Download

<p align="center">
  <a class="btn" href="https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/releases">
    <img src="https://img.shields.io/badge/⬇️_Download_Setup.exe-3fb950?style=for-the-badge" alt="Download Setup.exe" />
  </a>
</p>

<p align="center">
  <sub>⚠️ <b>Users on v1.2.1 or earlier must reinstall manually</b>: auto-update will fail during download. Please download <code>Sid.GameToolsHealthMonitor-win-Setup.exe</code> and install over the old version (settings are preserved) · Windows 10 / 11<br>New users: download <code>Setup.exe</code> (recommended)</sub>
</p>

---

## 🚀 Quick Start

> ⚠️ **Game window setup**: Set Path of Exile to **Windowed Fullscreen** or **Windowed** mode so background capture and overlay notices work correctly.

### Secure self-build (read first)

> With AI-driven attacks and lookalike download sites on the rise, only trust this official entry point: **https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/releases**. Full guide for the three paths (source / self-built EXE / official package) is in [`docs/安全自建.md`](docs/安全自建.md) —— pick any one of them; this section only shows commands.

### Path A — Run from source

```powershell
git clone https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor.git
cd PathofExile-Sid-GameTools_HealthMonitor
uv sync --locked
Run.bat
```

(The legacy `scripts\install_dependencies.bat` still works, falling back to a global install.)

### Path B — Build your own EXE

```powershell
uv sync --locked
scripts\build_exe.bat
Run.bat
```

### Path C — Official package

Go to [Releases](https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/releases) above and download `Setup.exe` (see Download section).

### Data & Reset

- Config file: `%LOCALAPPDATA%\GameTools_HealthMonitor\health_monitor_config.json` (`*.backup` auto-backup, `screenshots\` captures)
- In-app `Settings > Data & Reset` can `Open Folder / Copy Path / Reset to Default` (screenshots are kept unless you also check the delete option)

### Uninstall

- **Setup.exe install**: `Windows Settings > Apps > Installed Apps > Sid.GameToolsHealthMonitor > Uninstall`, then manually delete `%LOCALAPPDATA%\GameTools_HealthMonitor` if you want to clear screenshots/settings
- **ZIP portable**: delete the extracted folder + the data folder above

---

## 📂 Project Structure

<details>
<summary>View full structure</summary>

```
src/
  app.py                     # Qt (PySide6) entry point
  qt/                        # Qt GUI layer (main_window + 7 tabs)
  monitor_analyzer.py        # Health/mana HSV analysis + triggers
  capture_utils.py           # Screenshot + mss singleton
  image_utils.py             # Image drawing/resize/preview
  inventory_utils.py         # Inventory slot analysis
  config_manager.py          # Config load/save + backup
  language_system.py         # Translation system (zh-tw / zh-cn / en)
  utils.py                   # Runtime utilities + get_user_data_dir + F12 emergency close
  auto_click_manager.py      # Auto-click (AHK) manager
  usage_tracker.py           # Usage time tracking
  window_key_sender.py       # Window-focus key sending
  auto_update.py             # Velopack GithubSource update engine (main, >= v1.2.4-test)
  updater_core.py            # Legacy update engine (transitional, removed in v1.4+)
  language_packs.json        # UI strings
scripts/                     # One-click workflows
tools/build.py               # Build pipeline (PyInstaller onedir + sidecar resources)
docs/                        # User/developer docs
updater_main.py              # Standalone updater (Legacy, transitional)
release.ps1                  # One-click publish (stable / -Preview / -TestRepo)
```

</details>

---

## 🧠 Tech Stack

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

## 🙏 Acknowledgements

Thanks to the open source projects that let this small toolkit focus on the task itself.

- Velopack — install & update
- PySide6 / qfluentwidgets — UI
- OpenCV — image recognition
- Windows.Graphics.Capture — window capture
- AutoHotkey / PyInstaller — auto-click & packaging

Please let me know if anyone is missing.

---

## 🤝 Community

<p>
  <a href="https://www.facebook.com/talksometingshit/"><img src="https://img.shields.io/badge/Facebook-1877F2?style=flat&logo=facebook&logoColor=white" /></a>
  <a href="https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/issues"><img src="https://img.shields.io/badge/GitHub%20Issues-1a1a1a?style=flat&logo=github&logoColor=white" /></a>
  <a href="https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor"><img src="https://img.shields.io/badge/⭐_Star-3fb950?style=flat&logo=github&logoColor=white" /></a>
</p>

---

## ☕ Support

If my tools help you, feel free to support me in your own way.

[![Ko-fi](https://img.shields.io/badge/Ko--fi-FF5E5B?style=flat&logo=kofi&logoColor=white)](https://ko-fi.com/K3K11KMXOL)
[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=flat&logo=paypal&logoColor=white)](https://www.paypal.com/ncp/payment/GJS4D5VTSVWG4)
[![ECPay](https://img.shields.io/badge/ECPay-8A2BE2?style=flat&logo=amazonpay&logoColor=white)](https://p.ecpay.com.tw/E0E3A)
[![愛發電](https://img.shields.io/badge/愛發電-946CE6?style=flat&logo=afdian&logoColor=white)](https://afdian.com/a/sid-1996)

---

## ⚠️ Disclaimer

<details>
<summary>Click to view full disclaimer</summary>

This software is provided for educational research, automation study, and image recognition experimentation.

This software does NOT modify game files, inject code, or access game memory.

Usage may violate the Terms of Service of Grinding Gear Games. Use at your own risk.

</details>

---

<p align="center">
  <sub>License: <a href="https://www.gnu.org/licenses/agpl-3.0">AGPL-3.0</a> · Built with ❤️ by Sid-1996</sub>
</p>

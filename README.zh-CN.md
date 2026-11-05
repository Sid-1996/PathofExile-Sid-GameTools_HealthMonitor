<p align="center">
  <img src="assets/GameTools_HealthMonitor.ico" width="100" alt="Logo">
</p>

<h1 align="center">GameTools Health Monitor</h1>

<p align="center">
  <i>Path of Exile Sid 辅助工具</i>
</p>

<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/English-2ea44f?style=flat-square" alt="English" /></a>
  <a href="README.zh-TW.md"><img src="https://img.shields.io/badge/%E7%B9%A1%E9%AB%94%E4%B8%AD%E6%96%87-0969da?style=flat-square" alt="繁体中文" /></a>
  <a href="README.zh-CN.md"><img src="https://img.shields.io/badge/%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87-Current-0969da?style=flat-square" alt="简体中文" /></a>
</p>



<p align="center">
  <img src="https://img.shields.io/github/v/release/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor?style=flat-square&label=Version" />
  <img src="https://img.shields.io/badge/License-AGPL%20v3-blue?style=flat-square" />
  <img src="https://img.shields.io/github/downloads/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/total?style=flat-square" />
  <a href="https://sid-1996.github.io/PathofExile-Sid-GameTools_HealthMonitor/"><img src="https://img.shields.io/badge/Web-GitHub%20Pages-58a6ff?style=flat-square&logo=github" /></a>
</p>

<p align="center">
  以影像辨识与输入模拟为核心的 Windows 自动化研究工具<br>
  <sub>External automation research toolkit for Path of Exile</sub>
</p>

<p align="center">
  <img src="https://github-view-counter.vercel.app/api?username=PathofExile-Sid-GameTools_HealthMonitor&label=Repo+views&color=%23f85149&style=square" alt="Repo Views" />
</p>

---

## 📹 Demo / 示范影片

<p align="center">
  <a href="https://www.dailymotion.com/video/xa9cau2">
    <img src="https://img.shields.io/badge/▶️_观看完整示范-0066DC?style=for-the-badge&logo=dailymotion&logoColor=white" alt="Watch on Dailymotion" />
  </a>
</p>

---

## ✨ Features / 功能总览

<table>
  <tr>
    <td><b>🩸 血量/魔力监控</b><br>即时百分比判定 · 多阈值触发 · 冷却保护</td>
    <td><b>⚡ 技能连段</b><br>自订序列 · 可调延迟 · 多组配置</td>
  </tr>
  <tr>
    <td><b>🎒 背包自动化</b><br>一键清包 · 固定点取物 · UI 颜色辨识</td>
    <td><b>🖱️ 自动连点</b><br>Ctrl + 左键切换</td>
  </tr>
  <tr>
    <td><b>⏱️ 技能计时器</b><br>毫秒级精度 · 支援组合键</td>
    <td><b>⏸️ 全域控制</b><br>F9 暂停 · F12 离开</td>
  </tr>
</table>

---

## ⌨️ Hotkeys / 热键

| Key | Action / 操作 |
|:---:|:---|
| `F3` | 一键清包 / Clear Inventory |
| `F5` | 回藏身处 / Return Hideout |
| `F6` | 一键取物 / Pickup Sequence |
| `F9` | 暂停 / Resume |
| `F10` | 血量监控开关 / Health Monitor Toggle |
| `F12` | 离开 / Exit |
| `Ctrl + Click` | 自动连点 / Auto Click |

---

## 📦 Download / 下载

<p align="center">
  <a class="btn" href="https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/releases">
    <img src="https://img.shields.io/badge/⬇️_下载_Setup.exe-3fb950?style=for-the-badge" alt="Download Setup.exe" />
  </a>
</p>

<p align="center">
  <sub>⚠️ <b>v1.2.1（含更早）请务必手动重装</b>：自动更新会在下载阶段失败，请下载 <code>Sid.GameToolsHealthMonitor-win-Setup.exe</code> 覆盖安装（设定保留）· Windows 10 / 11<br>新用户亦请下载 <code>Setup.exe</code>（推荐） — Users on v1.2.1 or earlier must reinstall manually with <code>Setup.exe</code></sub>
</p>

---

## 🚀 Quick Start / 快速开始

> ⚠️ **游戏视窗设定**：请将 Path of Exile 设为「视窗全萤幕」或「视窗模式」，工具才能正确背景截图与显示提示浮层。

### 安全自建（推荐先看）

> 近期 AI 攻击与仿冒下载站频传，先认唯一可信入口：**仅 https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/releases**。完整三条路（源码直跑 / 自建 EXE / 官方套件）见 [`docs/安全自建.md`](docs/安全自建.md) —— 选一条做就可以，本节只给指令。

### 路径 A — 源码直跑

```powershell
git clone https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor.git
cd PathofExile-Sid-GameTools_HealthMonitor
uv sync --locked
Run.bat
```

（旧命令 `scripts\install_dependencies.bat` 仍可用，会 fallback 至全域安装。）

### 路径 B — 自建 EXE

```powershell
uv sync --locked
scripts\build_exe.bat
Run.bat
```

### 路径 C — 官方套件

直接到上方 [Releases](https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/releases) 下载 `Setup.exe`（见 Download 区段）。

### 资料与重设 / Data

- 设定档：`%LOCALAPPDATA%\GameTools_HealthMonitor\health_monitor_config.json`（`*.backup` 自动备份、`screenshots\` 截图）
- 工具内 `工具设置 > 资料与重设` 可 `开启资料夹 / 复制路径 / 重设为预设`（截图预设保留，勾选才一并删除）

### 移除 / Uninstall

- **Setup.exe 安装**：`Windows 设定 > 应用程式 > 已安装应用程式 > Sid.GameToolsHealthMonitor > 解除安装`，再手动删 `%LOCALAPPDATA%\GameTools_HealthMonitor`（如需清截图/设定）
- **ZIP 可携**：删解压目录 + 上述资料夹

---

## 📂 Project Structure / 专案结构

<details>
<summary>展开查看完整结构</summary>

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
  auto_update.py             # Velopack GithubSource 更新引擎（主链，≥ v1.2.4-test）
  updater_core.py            # Legacy update engine（过渡期保留，v1.4+ 删除）
  language_packs.json        # UI strings
scripts/                     # One-click workflows
tools/build.py               # Build pipeline (PyInstaller onedir + 旁置资源)
docs/                        # User/developer docs
updater_main.py              # Standalone updater (Legacy, 过渡期保留)
release.ps1                  # One-click publish (stable / -Preview / -TestRepo)
```

</details>

---

## 🧠 Tech Stack / 技术使用

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

## 🙏 Acknowledgements / 致谢

感谢以下开源专案，让这个小工具得以专注在 PoE 自动化本质，而无需重造轮子。

Thanks to the open source projects that let this small toolkit focus on the task itself.

- Velopack — 安装与更新
- PySide6 / qfluentwidgets — 介面
- OpenCV — 影像辨识
- Windows.Graphics.Capture — 视窗撷取
- AutoHotkey / PyInstaller — 连点与打包

如有遗漏，欢迎提醒。

---

## 🤝 Community / 社群

<p>
  <a href="https://www.facebook.com/talksometingshit/"><img src="https://img.shields.io/badge/Facebook-1877F2?style=flat&logo=facebook&logoColor=white" /></a>
  <a href="https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/issues"><img src="https://img.shields.io/badge/GitHub%20Issues-1a1a1a?style=flat&logo=github&logoColor=white" /></a>
  <a href="https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor"><img src="https://img.shields.io/badge/⭐_Star-3fb950?style=flat&logo=github&logoColor=white" /></a>
</p>

---

## ☕ Support / 赞助

如果我的工具对你有帮助，欢迎用你喜欢的方式支持我。

If my tools help you, feel free to support me in your own way.

[![Ko-fi](https://img.shields.io/badge/Ko--fi-FF5E5B?style=flat&logo=kofi&logoColor=white)](https://ko-fi.com/K3K11KMXOL)
[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=flat&logo=paypal&logoColor=white)](https://www.paypal.com/ncp/payment/GJS4D5VTSVWG4)
[![ECPay](https://img.shields.io/badge/ECPay-8A2BE2?style=flat&logo=amazonpay&logoColor=white)](https://p.ecpay.com.tw/E0E3A)
[![爱发电](https://img.shields.io/badge/爱发电-946CE6?style=flat&logo=afdian&logoColor=white)](https://afdian.com/a/sid-1996)

---

## ⚠️ Disclaimer / 免责声明

<details>
<summary>点击查看完整免责声明</summary>

本软体仅供教育研究、自动化学习与图像辨识实验使用。

This software is provided for educational research, automation study, and image recognition experimentation.

本工具不会修改游戏档案、不会注入程式码、不会读取游戏记忆体。

This software does NOT modify game files, inject code, or access game memory.

使用本工具可能违反 Grinding Gear Games 的服务条款，请自行承担使用风险。

Usage may violate the Terms of Service of Grinding Gear Games. Use at your own risk.

</details>

---

<p align="center">
  <sub>License: <a href="https://www.gnu.org/licenses/agpl-3.0">AGPL-3.0</a> · Built with ❤️ by Sid-1996</sub>
</p>

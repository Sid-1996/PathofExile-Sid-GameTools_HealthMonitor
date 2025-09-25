# ![Health Monitor Icon](/assets/GameTools_HealthMonitor.ico) Path of Exile Sid Game Tools

## Image Recognition Based Path of Exile Automation Tool, Uses Windows Interface to Simulate User Clicks, No Game Memory Reading or File Modification

> 🌐 **Language / 語言**: [English](README_EN.md) | [中文](README.md)

![Windows](https://img.shields.io/badge/platform-Windows-blue?color=blue) ![GitHub release](https://img.shields.io/github/v/release/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor?color=green) ![GitHub downloads](https://img.shields.io/github/downloads/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/total?color=orange) ![GitHub stars](https://img.shields.io/github/stars/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor?color=yellow) ![GitHub forks](https://img.shields.io/github/forks/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor?color=lightgrey) ![GitHub last commit](https://img.shields.io/github/last-commit/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor?color=red) ![GitHub language count](https://img.shields.io/github/languages/count/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor?color=purple) ![Milestone: 500⭐=Open Source](https://img.shields.io/badge/Milestone-500⭐=Open_Source-gold?style=flat-square) ![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)

---

## [Tutorial Video](https://www.youtube.com/watch?v=qRe8GODRx98) | English Instructions

Demo and tutorial [YouTube](https://www.youtube.com/watch?v=qRe8GODRx98)

---

## How to Use: Download the Green Portable Version, Extract and Double-click GameTools_HealthMonitor.exe

• [GitHub Download](https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/releases), Free direct download, Don't click "Download Source Code", click the compressed package
• Works in windowed and fullscreen mode, no additional dependencies required

---

## ✨ Feature Overview

- 🩸 **Health / Mana Monitor**: Visual percentage + multi-threshold auto-trigger
- ⚡ **Skill Combo**: Custom trigger keys, fully adjustable sequence and delays
- 🎒 **One-Click Inventory Clear**: Record inventory layout and colors for automatic cleanup
- 📦 **One-Click Item Pickup**: Set 5 pickup coordinates and press F6 to pick up sequentially
- 🖱️ **Auto Clicker**: Ctrl + Left Click to start/stop
- 🧪 **Live Preview**: Monitor areas, status indicators
- ⏸️ **Global Pause**: F9 to immediately disable all hotkey logic

---

## 🎯 Open Source Milestone Goal

### 🌟 **500 Stars = Complete Open Source Main Tool Source Code!**

We have already shared the complete packaged tool archive for download!

When this project gets **500 GitHub stars** ⭐, we will additionally open:

- 🔓 **Open complete main tool source code** (`src/health_monitor.py` and other core files)
- 📚 **Provide detailed technical documentation** and development guides
- 🤝 **Welcome community contributions and improvements**

**Current Progress:**

![GitHub stars](https://img.shields.io/github/stars/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor?color=yellow&style=for-the-badge) / 500 ⭐

**Join us in achieving this goal!**

- ⭐ **Give the project a star** to support us
- 🔄 **Share with friends** to let more people know
- 💬 **Provide suggestions in Issues** to help improve

> 💡 **Why set this goal?** We believe open source brings better tools and stronger communities. Your support will help us move towards completely transparent development!

---

| Hotkey | Function |
|--------|----------|
| F3 | One-click inventory clear |
| F5 | Quick hideout return (return logic) |
| F6 | One-click item pickup (need to set 5 points first) |
| F9 | Global pause / resume |
| F10 | Start / stop health monitor |
| F12 | Close tool |
| Ctrl + Left Click | Auto clicker toggle |

---

## 🚀 Installation & Startup

### Option 1: Complete Standalone EXE Version (Recommended)

1. Go to [Releases page](https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/releases) to download the latest version archive
2. Extract to any folder
3. Run `GameTools_HealthMonitor.exe` directly

**Note**: EXE version includes all dependencies, larger file size (~50MB+)

### Option 2: Demo Source Code Version (Learning & Preview)

1. Download source code: `git clone` or download ZIP
2. Check `src/demo_health_monitor.py` (demo version)
3. Check `src/health_monitor.py` (full version placeholder)

**Note**: Demo version includes GUI interface and feature preview, complete source code requires **500 GitHub stars** ⭐ to unlock!

---

## 📹 Tool Tutorial Video

[![YouTube Tutorial Video](https://img.shields.io/badge/YouTube-Tutorial_Video-red)](https://www.youtube.com/watch?v=qRe8GODRx98)

> 📺 **Recommended to watch the tutorial video first** to quickly understand tool functions and settings!

---

## 🧪 Initial Setup Recommendations

| Item | Operation |
|------|-----------|
| Health/Mana Monitor | Select area → Set percentage → Enable monitoring |
| Pickup Coordinates | Enter settings → Follow prompts to move mouse sequentially + Enter to confirm |
| One-click Clear | Capture inventory UI → Record empty color → Test F3 |
| Skill Combo | Define trigger key → Input skill sequence → Set delays → Enable |
| Auto Clicker | Hold Ctrl+Left Click to toggle state |

---

## 🧠 Feature Summary

### Health Monitor

- Captures specified area image each time and estimates percentage
- Multi-stage triggering (e.g., 80% / 50% / 30%)
- Trigger cooldown to avoid excessive key output

### Skill Combo

- Up to multiple independent configurations
- Each step has custom delay, adapts to skills and network latency

### One-click Clear / Pickup

- Determines valid slots through color differences
- Pickup clicks predetermined 5 points in sequence, suitable for fixed placement processes

### Auto Clicker

- High-frequency clicking (fixed short intervals), protects mouse button life, improves operation comfort

---

## ❓ FAQ (Concise)

**Q: Why don't hotkeys respond?** May have been globally paused (F9), press again to resume.

**Q: Clear doesn't work?** Confirm UI has been captured and empty color recorded, and inventory window is open.

**Q: Pickup function not executing?** Confirm all 5 coordinates have been set and you're in the correct scene.

**Q: Monitor values inaccurate?** Reselect area, ensure pure color sections are selected, avoid transparency and dynamic effects.

**Q: Antivirus false positive?** Add EXE to whitelist, as it has screen capture and keyboard monitoring behavior.

---

## 🗂️ Versions & Updates

- Latest release notes: [`RELEASE_NOTES.md`](RELEASE_NOTES.md)
- Latest version available at: [Releases page](https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/releases)

---

## ⚠️ Disclaimer

This software is an external tool developed for educational and learning purposes. It only interacts with the game through screenshots and simulated keyboard input, and does not modify any game files or code, nor does it read game memory.

This software is for personal learning and communication only, limited to personal game accounts, and may not be used for any commercial or profit-making purposes. The development team has the final interpretation rights of this project. All problems arising from the use of this software are unrelated to this project and development team. If you find merchants using this software for leveling services and charging fees, this is the merchant's personal behavior, this software does not authorize use for leveling services, and the resulting problems and consequences are unrelated to this software. This software does not authorize anyone to sell it, sold software may have malicious code added, leading to game accounts or computer data being stolen, unrelated to this software.

**Important Reminder**: According to Grinding Gear Games' Path of Exile Terms of Service, the game may prohibit the use of any third-party automation tools. Using this tool carries account risks, please evaluate carefully.

### Risk Warning

1. **Account Risk**: Using this tool may result in account bans. Please use after understanding the risks.
2. **Personal Responsibility**: Any account issues caused by using this tool are the user's own responsibility.
3. **Compliant Use**: Please ensure use within legally allowed scope in your area.

---

## 🤝 Support & Community

### Contact Information

- **GitHub Issues**: [Report Issues & Suggestions](https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/issues)
- **GitHub Official Repository**: [https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor](https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor)
- **Discord**: (No link yet)

---

## 📂 Project Structure

This project adopts a progressive open source strategy:

### 🔧 Currently Provided Content

- ✅ **Demo Source Code** (`src/demo_health_monitor.py`) - Includes GUI interface and feature preview
- ✅ **Helper Scripts** (`scripts/auto_click.ahk`) - AutoHotkey auto clicker tool
- ✅ **Documentation and Resources** (`docs/`, `assets/`) - User guides and image resources
- ✅ **Build Scripts** (`tools/`) - Packaging and build tools

### 🎯 Complete Open Source Goal

- 🔒 **Complete Main Tool Source Code** (`src/health_monitor.py`) - Requires **500 GitHub stars** ⭐ to unlock
- 🔒 **Core Algorithm Implementation** - Image recognition and automation logic
- 🔒 **Detailed Technical Documentation** - Development guides and API documentation

### 🌟 Join Us to Unlock

When star count reaches 500, all source code will be open, welcome community participation in development and improvement!

---

## Acknowledgments

- [OpenCV](https://opencv.org/) - Core image processing technology
- [Python Keyboard](https://github.com/boppreh/keyboard) - Global hotkey monitoring
- [PyAutoGUI](https://pyautogui.readthedocs.io/) - Mouse keyboard automation
- [PyGetWindow](https://github.com/asweigart/PyGetWindow) - Window management

---

## ⭐ Support

If you find it helpful, you can:

- Star the project
- Report issues
- Share with friends

---

> Concise README, for complete tutorial please refer to `docs/使用指南.md` and `docs/運作原理.md`.

---
description: Quick AI agent handover guide for Path of Exile automation tool project
---

# 🤖 AI Agent 快速交接指南

## 🎯 交接目標
讓新的 AI Agent 在 5 分鐘內快速掌握專案全貌，能立即進行有效開發和維護。

## 📋 核心資訊清單

### 🏗️ 專案基礎資訊
- **專案名稱**: Path of Exile Sid 輔助工具
- **GitHub**: Sid-1996/PathofExile-Sid-GameTools_HealthMonitor
- **主要語言**: Python 3.12
- **目標平台**: Windows
- **開發模式**: src/ (主源碼) + src for DEVELOPER/ (兼容層)

### 📁 核心檔案結構
```
PathofExile-Sid-GameTools_HealthMonitor/
├── src/                          # 主源碼目錄
│   ├── health_monitor.py       # 主程式 (10,554 行)
│   └── language_packs.json    # 多語言包
├── tools/                        # 建構工具
│   └── build.py              # PyInstaller 打包腳本
├── scripts/                       # 自動化腳本
│   ├── cleanup.bat            # 清理工具
│   ├── release.bat            # 快速發布
│   ├── secure-release.bat      # 安全發布
│   ├── pre-push-check.bat     # 推送前審核
│   └── push-with-review.bat  # 安全推送
├── docs/                         # 文檔目錄
│   ├── 使用指南.md
│   ├── 使用說明.md
│   └── 運作原理.md
└── .windsurf/workflows/           # AI 技能文檔
    ├── project-understanding.md
    ├── ai-work-summary.md
    ├── github-release-guide.md
    └── ai-agent-handover.md
```

### 🎮 核心功能模組
1. **血魔監控** (`HealthMonitor` 類)
   - 圖像辨識血量/魔力條
   - 自動使用藥水邏輯
   - MSS 螢幕截取 + OpenCV 處理

2. **背包管理** (`InventoryManager` 類)
   - 一鍵清包 (F3)
   - 自動拾取物品
   - 座標設定和預覽

3. **技能連段** (`ComboSystem` 類)
   - 自動技能組合
   - 時序控制
   - 鍵盤/滑鼠模擬

4. **自動點擊** (`auto_click.exe`)
   - AutoHotkey 腳本編譯
   - CTRL+左鍵連點
   - 進程監控自動關閉

### 🔧 技術架構
- **GUI 框架**: Tkinter + ttk
- **圖像處理**: OpenCV + NumPy + PIL
- **螢幕截取**: MSS
- **輸入模擬**: PyAutoGUI + Keyboard
- **視窗管理**: PyGetWindow
- **系統資訊**: psutil + winreg
- **網路請求**: requests
- **建構工具**: PyInstaller

## 🚀 快速上手流程

### 1. 環境設置 (5 分鐘)
```bash
# 安裝依賴
scripts\install_dependencies.bat

# 或手動安裝
pip install -r scripts\requirements.txt
```

### 2. 本地開發 (10 分鐘)
```bash
# 運行主程式
scripts\run_monitor.bat

# 或直接運行
python src\health_monitor.py
```

### 3. 建構測試 (10 分鐘)
```bash
# 建構 EXE
scripts\build_exe.bat

# 測試建構版本
scripts\test_built_exe.bat
```

### 4. 發布流程 (10 分鐘)
```bash
# 安全發布
scripts\push-with-review.bat

# 或手動發布
# 1. 清理
scripts\cleanup.bat
# 2. 建構
python tools/build.py
# 3. 上傳到 GitHub Release
```

## 🔒 安全注意事項

### 推送前必檢查
- ✅ Git 狀態乾淨
- ✅ 無敏感資訊洩漏
- ✅ 檔案大小正常 (<100MB)
- ✅ 開源文檔完整

### 依賴完整性
- **核心依賴**: opencv-python, numpy, pillow, mss, keyboard, pygetwindow, pyautogui, psutil, requests
- **隱藏依賴**: webbrowser, win32gui, traceback, pywin32
- **數據檔案**: language_packs.json, auto_click.ahk

## 🐛 常見問題與解決

### 建構問題
- **PyInstaller 快取鎖定**: 刪除 `build/GameTools_HealthMonitor`
- **依賴缺失**: 確保所有依賴在 `tools/build.py` 中聲明
- **版本顯示錯誤**: 檢查 `src/language_packs.json` 中的 `window_title`

### 運行問題
- **權限不足**: 以管理員身份運行
- **遊戲視窗找不到**: 檢查視窗標題設定
- **圖像辨識失敗**: 確保遊戲視窗可見

## 📚 重要文檔索引

### 🎯 必讀文檔
1. **`AGENTS.md`** - AI 貢獻者快速指南
2. **`DEVELOPER_HANDBOOK.md`** - 詳細技術手冊 (908 行)
3. **`PROJECT_STRUCTURE.md`** - 專案結構說明
4. **`LOCAL_DEVELOPMENT.md`** - 本地開發便利工具指南
5. **`SECURITY_GUIDELINES.md`** - 安全發布指南
6. **`CHANGELOG.md`** - 版本更新記錄

### 🔧 技能文檔
- **`.windsurf/workflows/project-understanding.md`** - 專案理解指南
- **`.windsurf/workflows/github-release-guide.md`** - 發布流程指南
- **`.windsurf/workflows/ai-work-summary.md`** - AI 工作報告

## 🎯 開發任務類型

### 🔧 維護任務
- 修復 BUG
- 更新依賴
- 優化性能
- 改進用戶體驗

### 🚀 新功能開發
- 新增監控功能
- 擴展自動化操作
- 改進 GUI 介面
- 增加語言支持

### 📦 發布任務
- 版本號更新
- 建構 EXE
- 發布 GitHub Release
- 更新文檔

## 🔄 工作流程建議

### 日常開發
1. **使用便利腳本**: `scripts/release.bat` 快速測試
2. **本地化開發**: 使用 `LOCAL_DEVELOPMENT.md` 中的工具
3. **定期清理**: `scripts/cleanup.bat` 保持環境乾淨

### 發布前
1. **安全推送**: 使用 `scripts/push-with-review.bat`
2. **版本同步**: 確保 `tools/build.py` 和 `src/language_packs.json` 版本一致
3. **文檔更新**: 更新 `CHANGELOG.md`

### 問題排查
1. **檢查日誌**: 查看 `dist/` 建構日誌
2. **參考手冊**: `DEVELOPER_HANDBOOK.md` 詳細說明
3. **查看 Issues**: GitHub Issues 歷史記錄

## 🎯 30 分鐘快速檢查清單

### ✅ 環境檢查
- [ ] Python 3.12 可用
- [ ] 依賴已安裝
- [ ] Git 狀態乾淨
- [ ] 權限足夠

### ✅ 專案理解
- [ ] 知道主要功能模組
- [ ] 了解檔案結構
- [ ] 明白建構流程
- [ ] 知道安全要求

### ✅ 工具熟悉
- [ ] 會使用自動化腳本
- [ ] 知道如何發布
- [ ] 會處理常見問題
- [ ] 知道文檔位置

## 🚀 緊急聯絡方式

### 專案問題
- **GitHub Issues**: 創建新 Issue
- **文檔查詢**: 在相關文檔中留言

### 技術支援
- **開發者手冊**: 詳細技術文檔
- **AI 技能文檔**: `.windsurf/workflows/` 目錄

---

**🎯 目標**: 新的 AI Agent 能在 30 分鐘內掌握專案，1 小時內開始有效工作！**

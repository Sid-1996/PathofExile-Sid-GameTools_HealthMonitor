# 📦 Release 建立指南

## GitHub Release 準備清單

### 1. 準備發布檔案

#### 完整版發布包
**檔案名稱**: `GameTools_HealthMonitor_v1.0.0_Complete.zip`

**包含內容**:
```
GameTools_HealthMonitor_v1.0.0_Complete/
├── HealthMonitor.exe              # 主程式執行檔
├── auto_click.ahk.exe             # AutoHotkey 觸發程式
├── install_improved.bat           # 環境安裝腳本
├── 使用說明.md                    # 完整使用說明
├── config.json                    # 預設配置檔案
└── README.txt                     # 快速入門說明
```

#### 開發者參考包
**檔案名稱**: `GameTools_HealthMonitor_v1.0.0_Developer.zip`

**包含內容**:
```
GameTools_HealthMonitor_v1.0.0_Developer/
├── docs/
│   ├── 技術架構.md
│   ├── API參考.md
│   └── 使用說明.md
├── examples/
│   ├── color_detection_demo.py
│   ├── screen_monitoring_demo.py
│   └── README.md
└── requirements.txt
```

### 2. GitHub Release 建立步驟

#### 步驟 1: 建立新 Release
1. 進入 GitHub 專案頁面
2. 點擊 "Releases" 標籤
3. 點擊 "Create a new release" 按鈕

#### 步驟 2: 設定 Release 資訊
```
Tag version: v1.0.0
Release title: PathofExile Sid GameTools_HealthMonitor v1.0.0 - 正式發布版
Target: main branch
```

#### 步驟 3: 編寫 Release 說明
複製 `RELEASE_NOTES_v1.0.0.md` 內容到描述欄位

#### 步驟 4: 上傳檔案
- 上傳 `GameTools_HealthMonitor_v1.0.0_Complete.zip`
- 上傳 `GameTools_HealthMonitor_v1.0.0_Developer.zip`

#### 步驟 5: 發布設定
- ✅ Set as the latest release
- ✅ Create a discussion for this release
- ❌ Set as a pre-release (這是正式版)

### 3. Release 描述模板

```markdown
## 🎮 PathofExile Sid GameTools_HealthMonitor v1.0.0

**智能血量魔力監控工具正式發布！**

### ✨ 主要特色
- 🎯 雙重監控：血量 + 魔力同時檢測
- ⚡ 即時響應：毫秒級檢測速度
- 🖼️ 視覺預覽：所見即所得的設定界面
- �️ 完整功能：提供完整的遊戲輔助體驗

### 📥 下載選項

#### 🎮 完整版 (一般使用者)
[📦 下載 GameTools_HealthMonitor_v1.0.0_Complete.zip](link)
- 包含可執行檔和完整使用說明
- 一鍵安裝環境設定
- 適合直接使用

#### 💻 開發者版 (技術參考)
[📦 下載 GameTools_HealthMonitor_v1.0.0_Developer.zip](link)
- 技術文檔和示例代碼
- API 參考說明
- 適合學習和研究

### 🚀 快速開始
1. 下載完整版壓縮檔
2. 解壓縮並執行 `install_improved.bat`
3. 啟動 `HealthMonitor.exe`
4. 享受智能監控體驗！

### 🔧 系統需求
- Windows 10/11 (64位元)
- Python 3.10+ (自動安裝)
- 512MB+ 可用記憶體

### �️ 功能特色
- **完整監控**: 血量魔力即時監控
- **智能觸發**: 自動響應系統
- **視覺介面**: 直觀的操作體驗

### 📞 技術支援
遇到問題？歡迎在 Issues 區域回報或討論！

---
**免責聲明**: 僅供個人學習使用，請遵守遊戲官方規定。
```

### 4. 發布前檢查清單

#### 檔案檢查
- [ ] 執行檔是否正常運作
- [ ] 安裝腳本是否完整
- [ ] 說明文件是否清楚
- [ ] 範例檔案是否有效

#### 內容檢查
- [ ] 無敏感的技術實現細節
- [ ] 無開發者工具相關內容
- [ ] 版本號是否一致
- [ ] 連結是否正確

#### 法律檢查
- [ ] 開源授權條款是否明確
- [ ] 免責聲明是否完整
- [ ] 使用限制是否說明

### 5. 發布後作業

#### 立即作業
1. 檢查 Release 頁面顯示是否正常
2. 測試下載連結是否有效
3. 確認檔案大小和內容正確

#### 推廣作業
1. 更新專案 README.md
2. 在相關社群分享
3. 回應使用者反饋

#### 監控作業
1. 關注下載統計
2. 收集使用者回饋
3. 準備後續更新

### 6. 版本管理

#### 標籤命名規則
- 主要版本: `v1.0.0`
- 次要更新: `v1.1.0`
- 修復版本: `v1.0.1`
- 測試版本: `v1.0.0-beta.1`

#### 分支策略
- `main`: 穩定發布版本
- `develop`: 開發中功能
- `hotfix`: 緊急修復

### 7. 備份和歸檔

#### 發布檔案備份
- 本地保存所有發布檔案
- 雲端儲存備份
- 版本歷史記錄

#### 文檔歸檔
- 保存 Release Notes
- 記錄使用者反饋
- 建立版本對照表

---

**提醒**: 發布前務必仔細檢查所有內容，確保無敏感資訊洩露！
# PathofExile Sid GameTools_HealthMonitor

🎮 **專為 Path of Exile（流亡黯道）設計的智能血量魔力監控工具**

[![License](https://img.shields.io/badge/License-Custom-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

## 🚀 項目簡介

PathofExile Sid GameTools_HealthMonitor 是一款高效的遊戲輔助工具，專為提升 Path of Exile 遊戲體驗而設計。通過實時監控角色血量和魔力狀態，自動觸發對應的回復動作，讓玩家能夠專注於戰鬥策略而非手動操作。

### ✨ 核心特色

- 🔍 **智能檢測**：先進的顏色識別算法，精確檢測血量魔力狀態
- ⚡ **即時響應**：毫秒級響應時間，關鍵時刻不延遲
- 🎯 **多重觸發**：支援多個觸發點設定，靈活應對不同情況
- ️ **視覺預覽**：即時預覽監控區域，所見即所得
- ⚙️ **高度客製化**：豐富的設定選項，滿足不同玩家需求
- 🛠️ **完整功能**：提供完整的遊戲輔助體驗

## 📸 功能展示

### 主界面
- 即時血量魔力百分比顯示
- 觸發狀態和冷卻時間監控
- 視覺化預覽界面

### 設定介面
- 直觀的區域選擇工具
- 靈活的觸發條件設定
- 專業的顏色檢測調整

## 🛠️ 技術規格

### 系統需求
- **操作系統**：Windows 10/11
- **Python版本**：3.10 或更高
- **內存需求**：最少 512MB 可用內存
- **權限要求**：管理員權限（推薦）

### 技術架構
```
📦 PathofExile-Sid-GameTools_HealthMonitor
├── 🎮 核心功能
│   ├── 即時螢幕截圖分析
│   ├── HSV色彩空間檢測
│   ├── 多線程監控系統
│   └── 智能觸發算法
├── 🔧 工具集成
│   ├── AutoHotkey腳本支援
│   ├── 系統托盤集成
│   └── 熱鍵管理系統
└── 🎨 用戶體驗
    ├── 直觀的操作介面
    ├── 即時狀態顯示
    └── 靈活的配置管理
```

## 📦 快速安裝

### 方法一：一鍵安裝（推薦）
1. 下載 [最新版本](releases/latest)
2. 解壓到任意目錄
3. 運行 `環境安裝.bat` 自動配置環境
4. 運行 `啟動工具.bat` 開始使用

### 方法二：開發環境設定
```bash
# 克隆倉庫
git clone https://github.com/YourUsername/PathofExile-Sid-GameTools_HealthMonitor.git
cd PathofExile-Sid-GameTools_HealthMonitor

# 安裝依賴
pip install -r requirements.txt

# 運行示例代碼
python examples/color_detection_demo.py
python examples/screen_monitoring_demo.py
```

## 🎯 使用指南

### 基礎設定
1. **區域設定**：選擇血量和魔力條區域
2. **觸發設定**：配置觸發百分比和對應按鍵
3. **啟動監控**：點擊開始監控按鈕

### 進階設定
- **顏色調整**：調整HSV參數以適應不同顯示設備
- **性能優化**：調整更新頻率和預覽設定
- **多配置管理**：為不同角色創建專屬配置

詳細使用說明請參考：[使用說明文檔](docs/使用說明.md)

## � 技術展示

本專案提供完整的技術示例和文檔，展示遊戲輔助工具的核心技術：

### 🔬 示例代碼
- **色彩檢測演示**：HSV色彩空間的檢測技術
- **螢幕監控演示**：高效能即時監控實現
- **技術架構說明**：完整的系統設計文檔

### 📚 學習資源
- 詳細的API參考文檔
- 完整的技術架構說明
- 可運行的示例代碼

這些資源非常適合：
- 學習遊戲輔助工具開發
- 了解電腦視覺應用
- 研究自動化系統設計

## 🔧 技術資源

### 範例代碼執行
```bash
# 色彩檢測展示
python examples/color_detection_demo.py

# 螢幕監控展示  
python examples/screen_monitoring_demo.py
```

### 項目結構
```
📁 docs/             # 技術文檔
├── 技術架構.md       # 系統架構說明
├── API參考.md        # API 接口文檔
└── 使用說明.md       # 完整使用手冊

📁 examples/         # 示例代碼
├── color_detection_demo.py    # 色彩檢測展示
├── screen_monitoring_demo.py  # 螢幕監控展示
└── README.md        # 示例說明

📁 releases/         # 發布文件
├── RELEASE_NOTES_v1.0.0.md   # 版本說明
├── RELEASE_GUIDE.md           # 發布指南
└── BUILD_STATUS.md            # 構建狀態
```

## 🤝 貢獻指南

我們歡迎社區貢獻！請遵循以下步驟：

1. **Fork** 本倉庫
2. 創建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟 **Pull Request**

### 開發規範
- 遵循 PEP 8 編碼規範
- 添加適當的註釋和文檔
- 確保代碼通過所有測試
- 更新相關文檔

## 📋 更新日誌

### v1.0.0 (2025-09-15)
- ✨ 首次公開發布
- 🎮 完整血量魔力監控功能
- 🚀 優化檢測算法效能
- 🎨 改善用戶界面設計
- 🔧 重構系統架構
- 📚 提供完整技術文檔

### v0.x 開發版本
- 🎯 核心功能開發
- ⚡ 效能優化測試
- 🐛 問題修復和改進

[查看完整更新日誌](CHANGELOG.md)

## ⚠️ 重要聲明

- **遊戲政策**：使用前請確認符合遊戲服務條款
- **安全性**：僅從官方渠道下載，避免使用非官方版本
- **責任限制**：本工具僅供學習和個人使用
- **支援範圍**：主要支援繁體中文環境

## 📞 聯繫我們

### 開發者
- **作者**：PathofExile Sid
- **項目狀態**：積極維護中
- **技術支援**：通過 Issues 回報問題

### 社群
- **討論區**：[GitHub Discussions](../../discussions)
- **問題回報**：[GitHub Issues](../../issues)
- **功能建議**：[Feature Requests](../../issues/new?template=feature_request.md)

## 📄 授權條款

本項目採用自定義授權條款。詳細信息請參考 [LICENSE](LICENSE) 文件。

主要要點：
- ✅ 個人使用和學習
- ✅ 技術研究和改進
- ✅ 開源社群貢獻
- ❌ 商業用途（需要許可）
- ❌ 未經授權的分發

## 🙏 致謝

特別感謝：
- Path of Exile 社群的支持與回饋
- 開源社群提供的優秀工具和庫
- 所有測試用戶的寶貴建議

---

<div align="center">

**⭐ 如果這個項目對您有幫助，請給個 Star！**

[下載最新版本](../../releases/latest) · [查看文檔](docs/) · [回報問題](../../issues) · [功能建議](../../issues/new)

</div>
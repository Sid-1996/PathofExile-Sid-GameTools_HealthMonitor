# GameTools Health Monitor - 項目結構說明

## 📁 項目結構 (v1.0.7)

```
GameTools_HealthMonitor/
├── .github/                    # GitHub 配置和文檔
│   ├── FUNDING.yml            # 贊助配置
│   └── workflows/             # GitHub Actions 工作流
├── assets/                     # 資源文件
│   ├── GameTools_HealthMonitor.ico    # 應用圖標
│   └── 免責聲明.txt              # 免責聲明
├── docs/                       # 詳細文檔
│   ├── LICENSE.txt             # 授權文件
│   ├── RELEASE_NOTES.md        # 發佈說明
│   ├── 使用指南.md              # 使用指南
│   ├── 使用說明.md              # 使用說明
│   └── 運作原理.md              # 運作原理
├── scripts/                    # 腳本和工具
│   ├── auto_click.ahk          # AutoHotkey 腳本源碼
│   ├── GameTools_HealthMonitor_Light.bat    # 輕量版啟動腳本
│   ├── install_dependencies.bat              # 依賴項安裝腳本
│   ├── requirements.txt                      # Python 依賴項列表
│   └── run_monitor.bat                       # 運行腳本
├── src/                        # 源代碼
│   ├── health_monitor.py       # 主程序
│   ├── health_monitor_config.json    # 配置文件(工具儲存時自動產生)
│   ├── language_packs.json     # 多語言支援檔案
│   └── screenshots/            # 截圖資源(設置框選時自動產生)
│       ├── health_monitor_mana_preview.png
│       ├── health_monitor_preview.png
│       ├── interface_ui.png
│       └── inventory_ui.png
├── tools/                      # 開發工具
│   └── build.py               # 打包腳本
├── .gitignore                  # Git 忽略文件
├── LICENSE                     # 授權文件
├── PROJECT_STRUCTURE.md        # 項目結構說明
├── README.md                   # 項目說明（中文）
└── README_EN.md                # 項目說明（英文）
```

## 📊 文件大小統計 (v1.0.7)

- **總大小**: ~2.1 MB
- **GitHub 友好**: 適合直接上傳到 GitHub
- **結構清晰**: 文件分類明確，易於維護和開發

## 🚀 快速開始

### 開發環境設置

1. **克隆項目**:
   ```bash
   git clone <repository-url>
   cd GameTools_HealthMonitor
   ```

2. **安裝依賴**:
   ```bash
   # Windows: 雙擊 scripts/install_dependencies.bat
   # 或手動執行:
   pip install -r scripts/requirements.txt
   ```

3. **運行程序**:
   ```bash
   python src/health_monitor.py
   ```

### 打包發佈

```bash
python tools/build.py
```

## 🔧 開發規範

### 版本控制
- 使用 [Semantic Versioning](https://semver.org/) (v1.0.7)
- 主版本號用於重大功能更新
- 次版本號用於功能增強
- 修訂號用於錯誤修復和性能優化

### 代碼風格
- 遵循 PEP 8 Python 代碼規範
- 使用有意義的變數和函數名稱
- 添加適當的註釋和文檔字符串
- 保持代碼簡潔和可讀性

### Git 提交規範
```
feat: 新功能
fix: 錯誤修復
docs: 文檔更新
style: 代碼格式調整
refactor: 代碼重構
perf: 性能優化
test: 測試相關
chore: 構建過程或工具配置更新
```

## 📈 版本歷史

- **v1.0.7** (2026-04-29): 性能優化與穩定性提升版
- **v1.0.6** (2025-10-01): 雙語言支援完善版
- **v1.0.5** (2025-09-25): 一鍵清包系統重大優化版
- **v1.0.4** (2025-09-23): 多語言支援完善版
- **v1.0.3** (2025-09-20): 技能連段系統完善版
- **v1.0.2** (2025-09-18): 介面UI檢測系統完善版
- **v1.0.1** (2025-09-15): 背包UI檢測系統完善版
- **v1.0.0** (2025-09-10): 初始穩定版本

## 🤝 貢獻指南

歡迎提交 Issue 和 Pull Request！請確保：

1. 遵循現有的代碼風格
2. 添加適當的測試
3. 更新相關文檔
4. 提交前進行代碼檢查

## 📄 授權

本項目採用 AGPL v3 授權 - 查看 [LICENSE](LICENSE) 文件了解詳情
3. **運行程序**: 雙擊 `scripts/run_monitor.bat`

## 📂 目錄說明

- **assets/**: 存放圖標、聲明等資源文件
- **docs/**: 所有文檔，包括授權、使用指南等
- **scripts/**: 所有腳本文件和配置文件
- **src/**: 源代碼和資源文件
- **.github/**: GitHub 相關配置

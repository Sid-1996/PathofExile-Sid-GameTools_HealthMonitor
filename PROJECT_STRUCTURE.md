# GameTools Health Monitor - 項目結構說明

## 📁 項目結構 (v1.0.7)

```
GameTools_HealthMonitor/
├── .github/                    # GitHub 配置
├── assets/                     # 圖標與資源
├── docs/                       # 使用與技術文檔
├── scripts/                    # 一鍵流程腳本
│   ├── install_dependencies.bat
│   ├── run_monitor.bat
│   ├── build_exe.bat
│   └── test_built_exe.bat
├── src/                        # 主開發目錄（source of truth）
│   ├── health_monitor.py
│   ├── demo_health_monitor.py
│   ├── language_packs.json
│   └── screenshots/
├── src for DEVELOPER/          # 相容層（舊流程 fallback）
├── tools/                      # 打包工具
│   └── build.py
├── AGENTS.md                   # 給下一個 AI 的快速工作流
├── .gitignore
├── LICENSE
├── PROJECT_STRUCTURE.md
├── README.md
└── README_EN.md
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

## 🤖 AI 協作入口

- 請先閱讀 `AGENTS.md`
- 主要修改目錄：`src/`、`scripts/`、`tools/`
- 打包前後流程：`scripts/build_exe.bat` → `scripts/test_built_exe.bat`

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

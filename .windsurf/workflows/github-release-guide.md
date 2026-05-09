---
description: Guide to release v1.0.7 to GitHub
---

# GitHub v1.0.7 發布指南

## 當前狀態
- **本地版本**: 1.0.7
- **GitHub 最新 release**: v1.0.6
- **當前分支**: `codex/gui-dialog-responsiveness`
- **主分支**: `master`

## 發布步驟

### 1. 檢查當前狀態
```batch
cd "c:\Code play first\Python POE"
git status
git log --oneline -5
```

### 2. 切換到 master 分支
```batch
git checkout master
git pull origin master
```

### 3. 合併功能分支
```batch
git merge codex/gui-dialog-responsiveness
```

如果有衝突，解決衝突後：
```batch
git add .
git commit -m "Merge codex/gui-dialog-responsiveness into master"
```

### 4. 推送到 GitHub
```batch
git push origin master
```

### 5. 建構 EXE
```batch
cd "c:\Code play first\Python POE"
scripts\build_exe.bat
```

### 6. 測試建構的 EXE
```batch
scripts\test_built_exe.bat
```

### 7. 創建 GitHub Release

#### 方式 A: 使用 GitHub 網頁界面
1. 前往 https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor/releases/new
2. 輸入標籤: `v1.0.7`
3. 輸入標題: `GameTools_HealthMonitor_v1.0.7`
4. 上傳 `dist/GameTools_Package/GameTools_HealthMonitor_v1.0.7_*.zip`
5. 撰寫發布說明（參考下方範本）
6. 點擊 "Publish release"

#### 方式 B: 使用 GitHub CLI (gh)
```batch
gh release create v1.0.7 dist/GameTools_Package/GameTools_HealthMonitor_v1.0.7_*.zip --title "GameTools_HealthMonitor_v1.0.7" --notes "版本 v1.0.7 發布"
```

### 8. 驗證發布
1. 檢查 GitHub Releases 頁面確認 v1.0.7 已發布
2. 下載並測試發布的 ZIP 檔案
3. 確認版本號正確顯示

## 發布說明範本

```markdown
## 版本 v1.0.7 (2026-05-09)

#### 🎯 更新與修正

- **GUI 對話框響應性改進**: 改進對話框的響應性和用戶體驗
- **專案結構優化**: 創建 AI 技能文檔供未來維護
- **開發文檔完善**: 新增專案理解和開發者習慣文檔

#### 🔧 系統穩定性改進

- **雙源目錄管理**: 改進 src/ 和 src for DEVELOPER/ 的同步機制
- **建構流程優化**: 改進 PyInstaller 打包流程

#### 📚 文檔更新

- 新增 `.windsurf/workflows/project-understanding.md` - AI 技能文檔
- 新增 `.windsurf/workflows/ai-work-summary.md` - AI 工作報告
- 更新開發者手冊和專案結構文檔
```

## 注意事項

1. **版本同步**: 確保 `tools/build.py` 和 `src/health_monitor.py` 的版本號一致
2. **雙語文檔**: 更新時同時更新 `README.md` 和 `README_EN.md`
3. **建構測試**: 發布前務必測試建構的 EXE
4. **備份**: 發布前建議備份當前工作目錄

## 發布後清理

發布完成後，可以選擇：
- 刪除或歸檔功能分支 `codex/gui-dialog-responsiveness`
- 清理建構目錄 `build/` 和 `dist/` 的舊檔案

```batch
git branch -d codex/gui-dialog-responsiveness
rmdir /s /q build
rmdir /s /q dist
```

# 貢獻指南

感謝您對 PathofExile Sid GameTools_HealthMonitor 項目的關注！我們歡迎社區的貢獻，無論是錯誤報告、功能建議還是程式碼改進。

## 🤝 如何貢獻

### 回報問題 🐛

如果您發現了錯誤，請按照以下步驟報告：

1. **檢查現有問題**：首先查看 [Issues](https://github.com/YourUsername/PathofExile-Sid-GameTools_HealthMonitor/issues) 確認問題是否已經被報告
2. **使用問題範本**：使用提供的 Bug Report 範本
3. **提供詳細資訊**：
   - 作業系統版本
   - Python版本
   - 軟體版本
   - 重現步驟
   - 預期行為
   - 實際行為
   - 錯誤截圖（如適用）

### 建議功能 💡

我們樂於接受新功能建議：

1. **檢查現有建議**：查看現有的 Feature Requests
2. **使用功能請求範本**：描述您的想法
3. **說明用例**：解釋為什麼這個功能有用
4. **考慮實現方式**：如果可能，提供實現思路

### 貢獻程式碼 💻

#### 開發環境設置

1. **Fork 專案**：點擊 GitHub 上的 Fork 按鈕
2. **克隆倉庫**：
   ```bash
   git clone https://github.com/YourUsername/PathofExile-Sid-GameTools_HealthMonitor.git
   cd PathofExile-Sid-GameTools_HealthMonitor
   ```
3. **設置虛擬環境**：
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # 或 source venv/bin/activate  # macOS/Linux
   ```
4. **安裝依賴**：
   ```bash
   pip install -r requirements.txt
   ```

#### 開發流程

1. **創建分支**：
   ```bash
   git checkout -b feature/your-feature-name
   # 或
   git checkout -b bugfix/your-bugfix-name
   ```

2. **編寫程式碼**：
   - 遵循現有程式碼風格
   - 添加適當的註釋
   - 確保程式碼清晰易懂

3. **測試更改**：
   - 確保所有現有功能正常運作
   - 測試您的新功能或修復
   - 在不同場景下測試

4. **提交更改**：
   ```bash
   git add .
   git commit -m "feat: 添加新功能描述"
   # 或
   git commit -m "fix: 修復特定問題描述"
   ```

5. **推送分支**：
   ```bash
   git push origin feature/your-feature-name
   ```

6. **創建 Pull Request**：
   - 提供清晰的標題和描述
   - 說明更改的原因和影響
   - 參考相關的 Issues

## 📝 編碼規範

### Python 代碼風格

遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 規範：

```python
# 好的例子
def calculate_health_percentage(current_health, max_health):
    """計算血量百分比
    
    Args:
        current_health (int): 當前血量
        max_health (int): 最大血量
        
    Returns:
        float: 血量百分比 (0.0-1.0)
    """
    if max_health <= 0:
        return 0.0
    return current_health / max_health

# 避免
def calc_hp_pct(ch,mh):
    return ch/mh if mh>0 else 0
```

### 命名規範

- **變數和函數**：使用 snake_case
- **類別**：使用 PascalCase
- **常數**：使用 UPPER_SNAKE_CASE
- **私有成員**：以下劃線開頭

```python
# 變數和函數
health_percentage = 0.8
def get_window_title():
    pass

# 類別
class HealthMonitor:
    pass

# 常數
MAX_RETRY_COUNT = 3

# 私有成員
def _internal_method(self):
    pass
```

### 註釋規範

- 使用中文註釋
- 為複雜邏輯添加說明
- 使用 docstring 描述函數和類別

```python
def analyze_health_color(self, image):
    """分析圖像中的血量顏色
    
    使用 HSV 色彩空間檢測紅色像素，計算血量百分比。
    
    Args:
        image (numpy.ndarray): 要分析的圖像
        
    Returns:
        int: 血量百分比 (0-100)
        
    Raises:
        ValueError: 當圖像格式不正確時
    """
    # 轉換到 HSV 色彩空間以便更好地檢測顏色
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # ... 實現細節
```

## 🧪 測試指南

### 測試策略

1. **單元測試**：測試個別函數和方法
2. **整合測試**：測試模組間的互動
3. **使用者介面測試**：測試 GUI 功能
4. **效能測試**：確保效能符合要求

### 測試檢查清單

在提交前請確認：
- [ ] 所有現有功能正常運作
- [ ] 新功能按預期工作
- [ ] 沒有明顯的效能問題
- [ ] UI 響應正常
- [ ] 錯誤處理正確
- [ ] 在不同解析度下測試（如適用）

## 📋 Pull Request 指南

### PR 標題格式

使用清晰描述性的標題：
- `feat: 新增魔力監控功能`
- `fix: 修復血量檢測在高DPI下的問題`
- `docs: 更新安裝說明文件`
- `refactor: 重構觸發系統架構`
- `style: 修正程式碼格式`
- `test: 添加血量檢測單元測試`

### PR 描述範本

```markdown
## 更改描述
簡要描述此 PR 的更改內容

## 更改類型
- [ ] Bug fix (修復問題)
- [ ] New feature (新功能)
- [ ] Breaking change (重大變更)
- [ ] Documentation update (文件更新)

## 測試
描述您如何測試了這些更改

## 檢查清單
- [ ] 我的程式碼遵循項目的編碼規範
- [ ] 我已經進行了自我檢查
- [ ] 我的更改不會產生新的警告
- [ ] 我已經添加了必要的註釋
- [ ] 相關文件已經更新

## 相關 Issues
修復 #(issue 編號)
```

## 🎯 優先級領域

我們特別歡迎以下領域的貢獻：

### 高優先級
- 🐛 **錯誤修復**：特別是穩定性和相容性問題
- 🚀 **效能優化**：減少 CPU 使用率和記憶體消耗
- 🔧 **使用者體驗改進**：讓工具更易於使用

### 中優先級
- ✨ **新功能**：有用的新特性
- 📚 **文件改進**：更清晰的說明和教學
- 🧪 **測試覆蓋**：增加測試覆蓋率

### 低優先級
- 🎨 **UI 美化**：視覺改進
- 🔧 **程式碼重構**：在不破壞功能的前提下改進程式碼結構

## 📞 社區支援

### 溝通管道
- **GitHub Issues**：錯誤報告和功能請求
- **GitHub Discussions**：一般討論和問答
- **Pull Requests**：程式碼貢獻討論

### 回應時間
- Issues 回應：通常 48 小時內
- PR 檢視：通常 1 週內
- 複雜問題：可能需要更長時間

## 🏆 貢獻者認可

我們重視每位貢獻者的努力：

### 貢獻類型
- **程式碼貢獻**：修復、功能、改進
- **文件貢獻**：撰寫、翻譯、改善文件
- **測試貢獻**：回報問題、測試功能
- **設計貢獻**：UI/UX 改進建議
- **社區貢獻**：幫助其他用戶、推廣項目

### 認可方式
- 貢獻者將在 README 中被提及
- 重大貢獻將在發布說明中特別感謝
- 活躍貢獻者可獲得項目維護者權限

## ❓ 需要幫助？

如果您在貢獻過程中遇到問題：

1. 查看現有的 Issues 和 Discussions
2. 創建新的 Discussion 提問
3. 聯繫項目維護者

記住，沒有愚蠢的問題！我們都是從學習開始的。

---

再次感謝您的貢獻意願！每個貢獻，無論大小，都讓這個項目變得更好。 🙏
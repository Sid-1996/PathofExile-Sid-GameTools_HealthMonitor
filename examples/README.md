# 📚 技術示例與學習資源

此目錄包含了工具的核心技術示例代碼，主要供開發者和技術愛好者學習參考。

## 🎯 適用對象

- **開發者**：想要了解遊戲輔助工具開發技術
- **技術愛好者**：對電腦視覺和自動化感興趣
- **學生**：學習Python在遊戲自動化中的應用

## 📁 示例內容

### 色彩檢測示例 (`color_detection_demo.py`)
展示如何使用HSV色彩空間進行精確的顏色檢測，這是血魔監控功能的核心技術。

### 螢幕監控示例 (`screen_monitoring_demo.py`)
展示高效能螢幕截圖和即時監控技術，這是整個工具的基礎架構。

## ⚠️ 重要提醒

**這些示例代碼僅供學習參考，不建議普通用戶運行。**

如果您是普通用戶，只想使用工具的功能，請：
1. 直接下載 [最新版本](../../releases/latest)
2. 按照 [使用說明](docs/使用說明.md) 進行安裝和使用

## 🔧 開發環境需求

如果您想運行這些示例，需要：
- Python 3.10+
- OpenCV, mss, pyautogui 等依賴包
- 開發環境知識

## � 相關文檔

- [完整使用說明](docs/使用說明.md) - 面向普通用戶
- [技術架構說明](docs/技術架構.md) - 面向開發者
- [API參考](docs/API參考.md) - 技術文檔
```
opencv-python>=4.5.0
mss>=6.1.0
numpy>=1.21.0
Pillow>=8.0.0
```

### 安裝依賴
```bash
pip install opencv-python mss numpy Pillow
```

## 🎯 技術要點

### HSV 色彩檢測
```python
# 核心檢測邏輯
hsv_image = cv2.cvtColor(screenshot, cv2.COLOR_RGB2HSV)
mask = cv2.inRange(hsv_image, lower_bound, upper_bound)
percentage = cv2.countNonZero(mask) / total_pixels * 100
```

### 高效能截圖
```python
# 使用 mss 進行快速截圖
with mss() as sct:
    screenshot = sct.grab(monitor_region)
    img_array = np.array(screenshot)
```

### 自適應監控
```python
# 根據性能動態調整監控頻率
processing_time = time.time() - start_time
adaptive_delay = calculate_optimal_delay(processing_time)
time.sleep(adaptive_delay)
```

## 📊 性能指標

### 預期性能表現
- **截圖速度**: 1000+ FPS (小區域)
- **處理延遲**: < 5ms (典型工作負載)
- **CPU 使用率**: < 10% (優化後)
- **記憶體佔用**: < 50MB (穩定狀態)

### 優化技巧
1. **區域限制**: 僅截取必要的螢幕區域
2. **多線程**: 分離截圖和處理邏輯
3. **緩存機制**: 重用計算結果
4. **自適應**: 根據系統性能動態調整

## 🔧 客製化指南

### 修改檢測顏色
```python
# 在 color_detection_demo.py 中調整
test_colors = [
    ("自訂顏色1", [H, S, V]),
    ("自訂顏色2", [H, S, V]),
]
```

### 調整監控區域
```python
# 在 screen_monitoring_demo.py 中修改
monitor_regions = {
    'custom_region': {
        'left': X, 'top': Y, 
        'width': W, 'height': H
    }
}
```

### 性能調優
```python
# 調整監控頻率
base_delay = 0.01  # 10ms = 100 FPS
max_delay = 0.1    # 100ms = 10 FPS
```

## 🚀 進階應用

### 擴展檢測算法
- 邊緣檢測結合色彩檢測
- 機器學習模型整合
- 多重檢測策略

### 系統整合
- 熱鍵系統集成
- 系統托盤功能
- 配置文件管理

### 跨遊戲適配
- 通用色彩檢測框架
- 可配置的界面元素
- 自動校準系統

## ⚠️ 注意事項

1. **系統權限**: 某些功能可能需要管理員權限
2. **防毒軟體**: 螢幕截圖功能可能觸發安全警告
3. **性能影響**: 高頻監控會增加 CPU 負載
4. **兼容性**: 不同系統的顏色顯示可能有差異

## 📞 技術支援

如果您在使用示例代碼時遇到問題：

1. 檢查 Python 版本是否符合要求 (3.10+)
2. 確認所有依賴項已正確安裝
3. 查看錯誤日誌獲取詳細信息
4. 參考主專案的說明文檔

---

**免責聲明**: 這些示例代碼僅供學習和技術研究使用，實際應用需要根據具體需求進行調整和優化。
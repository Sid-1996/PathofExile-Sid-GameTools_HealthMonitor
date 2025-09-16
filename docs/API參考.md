# 📖 API 參考文檔

## 配置 API

### ConfigManager 類別

用於管理應用程式配置的核心類別。

```python
class ConfigManager:
    def __init__(self, config_file="config.json"):
        """初始化配置管理器"""
        
    def load_config(self):
        """載入配置文件"""
        
    def save_config(self):
        """保存配置文件"""
        
    def get(self, key, default=None):
        """獲取配置值"""
        
    def set(self, key, value):
        """設置配置值"""
```

### 配置項目

| 配置鍵 | 類型 | 預設值 | 說明 |
|--------|------|--------|------|
| `monitor_enabled` | bool | false | 是否啟用監控 |
| `health_threshold` | int | 50 | 血量觸發閾值 (%) |
| `mana_threshold` | int | 30 | 魔力觸發閾值 (%) |
| `monitor_frequency` | int | 100 | 監控頻率 (ms) |
| `health_region` | dict | {} | 血量監控區域 |
| `mana_region` | dict | {} | 魔力監控區域 |

## 監控 API

### MonitorCore 類別

核心監控功能實現。

```python
class MonitorCore:
    def start_monitoring(self):
        """開始監控"""
        
    def stop_monitoring(self):
        """停止監控"""
        
    def get_health_percentage(self):
        """獲取當前血量百分比"""
        return: float
        
    def get_mana_percentage(self):
        """獲取當前魔力百分比"""
        return: float
```

## 影像處理 API

### ImageProcessor 類別

處理螢幕截圖和顏色檢測。

```python
class ImageProcessor:
    def capture_region(self, region):
        """截取指定區域"""
        
    def detect_bar_percentage(self, image, color_range):
        """檢測血條/魔力條百分比"""
        
    def calibrate_colors(self, sample_image):
        """校準顏色檢測參數"""
```

## 觸發系統 API

### TriggerSystem 類別

管理觸發條件和執行動作。

```python
class TriggerSystem:
    def add_trigger(self, name, condition, action):
        """添加觸發器"""
        
    def remove_trigger(self, name):
        """移除觸發器"""
        
    def check_triggers(self):
        """檢查所有觸發條件"""
```

## 事件處理

### 事件類型

```python
# 監控事件
MONITOR_STARTED = "monitor_started"
MONITOR_STOPPED = "monitor_stopped"
HEALTH_CHANGED = "health_changed"
MANA_CHANGED = "mana_changed"

# 觸發事件
HEALTH_TRIGGERED = "health_triggered"
MANA_TRIGGERED = "mana_triggered"
TRIGGER_COOLDOWN = "trigger_cooldown"
```

### 事件監聽

```python
def on_health_change(percentage):
    """血量變化事件處理"""
    print(f"Health: {percentage}%")

# 註冊事件監聽器
event_manager.subscribe(HEALTH_CHANGED, on_health_change)
```

## 工具函數

### 顏色檢測

```python
def rgb_to_hsv(r, g, b):
    """RGB 轉 HSV 色彩空間"""
    
def create_color_range(base_color, tolerance=10):
    """創建顏色檢測範圍"""
    
def optimize_detection_params(sample_images):
    """優化檢測參數"""
```

### 區域管理

```python
def validate_region(region):
    """驗證監控區域有效性"""
    
def calculate_relative_position(absolute_pos, window_rect):
    """計算相對位置"""
    
def auto_detect_bars(screenshot):
    """自動檢測血條魔力條位置"""
```

## 錯誤處理

### 異常類型

```python
class MonitorError(Exception):
    """監控相關錯誤"""
    
class ConfigError(Exception):
    """配置相關錯誤"""
    
class ImageProcessingError(Exception):
    """圖像處理錯誤"""
```

### 錯誤代碼

| 代碼 | 說明 |
|------|------|
| E001 | 螢幕截圖失敗 |
| E002 | 區域配置無效 |
| E003 | 顏色檢測失敗 |
| E004 | 觸發執行失敗 |

---

**免責聲明**: 此 API 文檔僅供技術參考，實際使用需要完整的應用程式環境。
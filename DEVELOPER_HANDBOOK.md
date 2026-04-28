# Health Monitor 開發者手冊

## 專案概述

這是一個專為 Path of Exile 遊戲設計的自動化工具，主要功能包括：

- 實時血量/魔力監控與自動補充
- 物品欄自動化管理
- 技能連擊系統
- 全域熱鍵處理
- 圖形用戶界面

## 架構總覽

### 主要組件

#### HealthMonitor 類

主應用類，負責整個應用的生命周期管理。

**關鍵屬性：**

- `root`: Tkinter 主窗口
- `monitor_thread`: 監控線程
- `combo_thread`: 連段系統線程
- `config_file`: 配置文件路徑
- `license_valid`: 授權狀態

**主要方法分類：**

1. 初始化與清理
2. GUI 創建與管理
3. 監控系統
4. 熱鍵處理
5. 連段系統
6. 配置管理
7. 版本更新

## 詳細功能邏輯說明

### 健康監控系統邏輯

#### 實時監控算法

**螢幕捕獲流程：**

1. 使用 MSS 庫捕獲指定區域的螢幕畫面
2. 將捕獲的圖像轉換為 NumPy 數組格式
3. 應用圖像預處理（降噪、銳化）

**精確健康分析算法：**

```python
def analyze_health(self, img):
    """分析血量條，使用18個等間隔位置檢測以提高精度"""
    # 定義18個等間隔檢測位置的百分比（從上到下：95%, 90%, 85%, ..., 5%）
    detection_positions = [0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 
                          0.55, 0.5, 0.45, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1]
    
    health_count = 0
    
    # 在每個檢測位置附近取樣檢測
    for i, pos_percent in enumerate(detection_positions):
        # 計算檢測位置的Y坐標
        y_center = int(height * (1 - pos_percent))
        
        # 在檢測位置附近取一個小的區域（垂直5像素，水平全寬）
        sample_height = 5
        y_start = max(0, y_center - sample_height // 2)
        y_end = min(height, y_center + sample_height // 2)
        
        segment = img[y_start:y_end, :]
        
        # 檢查是否為血量顏色
        if self.is_health_color(segment):
            health_count += 1
    
    # 多重條件判斷滿血狀態
    if health_count >= 16:
        # 檢查下半部分和核心區域的比例
        # 應用滿血修正邏輯
    
    return (health_count / 18) * 100  # 轉換為百分比
```

**HSV顏色檢測邏輯：**

```python
def is_health_color(self, segment):
    """檢查區段是否為血量顏色"""
    # 轉換為HSV
    hsv = cv2.cvtColor(segment, cv2.COLOR_BGR2HSV)
    
    # 紅色範圍 (考慮色環) - 提高飽和度和亮度閾值以排除生命藥劑特效
    lower_red1 = np.array([0, self.red_saturation_min, self.red_value_min])
    upper_red1 = np.array([self.red_h_range, 255, 255])
    lower_red2 = np.array([170, self.red_saturation_min, self.red_value_min])
    upper_red2 = np.array([180, 255, 255])
    
    # 綠色範圍 - 也提高品質要求
    lower_green = np.array([self.green_h_range, self.green_saturation_min, self.green_value_min])
    upper_green = np.array([self.green_h_range + 40, 255, 255])
    
    # 檢查像素比例
    red_mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    red_mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    green_mask = cv2.inRange(hsv, lower_green, upper_green)
    
    red_pixels = np.count_nonzero(red_mask1 | red_mask2)
    green_pixels = np.count_nonzero(green_mask)
    total_pixels = segment.shape[0] * segment.shape[1]
    
    health_ratio = (red_pixels + green_pixels) / total_pixels
    
    return health_ratio > self.health_threshold
```

**魔力分析算法：**

```python
def analyze_mana(self, img):
    """分析魔力條，使用18個等間隔位置檢測以提高精度"""
    # 使用與血量相同的18點檢測邏輯
    detection_positions = [0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 
                          0.55, 0.5, 0.45, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1]
    
    mana_count = 0
    
    for i, pos_percent in enumerate(detection_positions):
        y_center = int(height * (1 - pos_percent))
        y_start = max(0, y_center - sample_height // 2)
        y_end = min(height, y_center + sample_height // 2)
        
        segment = img[y_start:y_end, :]
        
        # 檢查是否為魔力顏色（藍色）
        if self.is_mana_color(segment):
            mana_count += 1
    
    return (mana_count / 18) * 100

def is_mana_color(self, segment):
    """檢查區段是否為魔力顏色（藍色）"""
    hsv = cv2.cvtColor(segment, cv2.COLOR_BGR2HSV)
    
    # 藍色範圍
    lower_blue = np.array([90, 50, 50])
    upper_blue = np.array([130, 255, 255])
    
    blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
    blue_pixels = np.count_nonzero(blue_mask)
    total_pixels = segment.shape[0] * segment.shape[1]
    
    return (blue_pixels / total_pixels) > self.health_threshold
```

**觸發機制：**

- 基於冷卻時間追蹤變數 `last_trigger_times`
- 支持血量和魔力分離監控
- 包含防抖機制避免誤觸發
- 動態調整監控頻率（預設100ms，可配置）

#### 區域選擇邏輯

**動態區域調整：**

- 支持鼠標拖拽選擇監控區域
- 自動保存區域坐標到配置文件
- 提供視覺化區域預覽功能

### 物品欄管理邏輯

#### 網格坐標計算系統

**坐標映射算法：**

```python
def calculate_grid_coordinates(start_x, start_y, cell_width, cell_height, rows, cols):
    """計算物品欄中每個格子的坐標"""
    coordinates = []
    for row in range(rows):
        for col in range(cols):
            x = start_x + (col * cell_width) + (cell_width // 2)
            y = start_y + (row * cell_height) + (cell_height // 2)
            coordinates.append((x, y))
    return coordinates
```

**顏色檢測邏輯：**

實際的物品檢測基於RGB顏色差異比較，而不是HSV物品品質識別：

- **基準顏色記錄**：記錄空背包時每個格子的RGB顏色值作為基準
- **動態顏色比較**：運行時比較當前格子顏色與基準顏色的差異
- **物品存在判定**：如果RGB顏色差異大於閾值(15)，則認為該格子有物品
- **清空操作**：對檢測到有物品的格子執行Ctrl+點擊操作

**實際實現邏輯：**

```python
def should_clear_inventory(self, img, skip_slots=None, current_slot=None):
    """判斷是否需要清空背包 - 基於RGB顏色差異檢測"""
    occupied_slots = []
    
    for i, (pos_x, pos_y) in enumerate(self.inventory_grid_positions):
        # 獲取格子區域的平均RGB顏色
        cell_pixels = img[y1:y2, x1:x2]
        avg_color = np.mean(cell_pixels, axis=(0, 1))
        current_rgb = (int(avg_color[2]), int(avg_color[1]), int(avg_color[0]))
        
        # 與基準顏色比較
        baseline_rgb = self.empty_inventory_colors[i]
        color_diff = sum(abs(a - b) for a, b in zip(current_rgb, baseline_rgb))
        
        # 顏色差異大於15則認為有物品
        if color_diff > 15:
            occupied_slots.append(i)
    
    return len(occupied_slots) > 0, occupied_slots
```

#### 自動操作流程

**物品掃描算法：**

1. **基準顏色記錄**：用戶點擊「記錄淨空顏色」按鈕，記錄60個格子的RGB基準顏色
2. **區域選擇**：用戶框選背包區域，系統計算網格坐標位置
3. **動態檢測**：運行時逐格比較當前顏色與基準顏色的差異
4. **智能清空**：對有物品的格子執行Ctrl+點擊操作，自動清空物品
5. **狀態追蹤**：記錄已處理格子，避免重複處理同一物品

**清空策略：**

- **動態清空模式**：持續按住Ctrl鍵，逐個處理檢測到的物品
- **安全防護**：每個位置最多點擊1次，防止誤操作
- **中斷支持**：用戶可隨時按ESC中斷清空操作
- **狀態驗證**：每次操作後重新檢測背包狀態

### 熱鍵處理系統邏輯

#### 全域熱鍵註冊機制

**實際熱鍵綁定實現：**

```python
def setup_hotkeys(self):
    """設置全域熱鍵，使用keyboard庫"""
    # 全域熱鍵，不受視窗焦點限制
    keyboard.add_hotkey('f3', self.quick_clear_inventory)  # F3: 一鍵清包
    keyboard.add_hotkey('f5', self.return_to_hideout)     # F5: 返回藏身
    keyboard.add_hotkey('f6', self.f6_pickup_items)       # F6: 一鍵取物
    keyboard.add_hotkey('f9', self.toggle_global_pause)   # F9: 全域暫停開關
    keyboard.add_hotkey('f10', self.toggle_monitoring)    # F10: 監控開關
    keyboard.add_hotkey('f12', self.close_app)            # F12: 關閉應用
    
    self.add_status_message("全域熱鍵註冊成功", "success")
```

**全域暫停機制實現：**

```python
def toggle_global_pause(self):
    """F9: 全域暫停開關 - 暫停/恢復所有熱鍵功能"""
    self.global_pause = not self.global_pause
    
    if self.global_pause:
        # 記錄並停止血魔監控
        if self.monitoring:
            self.monitoring_was_active = True
            self.stop_monitoring()
        
        # 記錄並停止技能連段
        if self.combo_running:
            self.combo_was_running = True
            self.stop_combo_system()
    else:
        # 自動恢復之前的功能
        if self.monitoring_was_active:
            self.restart_monitoring_silently()
        
        if self.combo_was_running:
            self.restart_combo_system_silently()
```

**熱鍵衝突處理：**

- 使用 keyboard 庫的全域熱鍵監聽
- 不依賴遊戲窗口焦點
- 支持運行時熱鍵重新綁定
- 無需管理員權限即可工作

### 連段系統邏輯

#### 技能序列執行算法

**實際連段執行流程：**

```python
def execute_combo(self, set_index):
    """執行指定的連段套組"""
    if not self.combo_running:
        return

    # 檢查遊戲視窗是否在前台
    if self.window_var.get():
        if not self.is_game_window_foreground(self.window_var.get()):
            print(f"遊戲視窗 '{self.window_var.get()}' 不在前台，跳過連段執行")
            return

    combo_set = self.combo_sets[set_index]
    combo_keys = combo_set['combo_keys']
    delays = combo_set['delays']
    trigger_delay = combo_set.get('trigger_delay', '')
    trigger_key = combo_set.get('trigger_key', '')

    # 處理觸發延遲
    if trigger_delay and trigger_delay != 'off' and trigger_delay != '':
        try:
            delay_ms = int(trigger_delay)
            if delay_ms > 0:
                delay = delay_ms / 1000.0
                time.sleep(delay)
        except (ValueError, TypeError):
            pass  # 延遲時間無效，跳過延遲

    # 執行連段
    for i, key in enumerate(combo_keys):
        if not key or key == 'off' or key == '':
            continue

        # 模擬按鍵
        try:
            pyautogui.press(key.lower())
        except Exception as e:
            print(f"按鍵模擬失敗 {key}: {e}")
            continue

        # 處理技能間延遲
        if i < len(combo_keys) - 1 and delays[i] and delays[i] != 'off':
            try:
                delay_ms = int(delays[i])
                if delay_ms > 0:
                    delay = delay_ms / 1000.0
                    time.sleep(delay)
            except (ValueError, TypeError):
                pass  # 延遲時間無效，跳過延遲
```

**連段系統線程管理：**

```python
def run_combo_system(self):
    """運行連段系統的主循環"""
    print("連段系統線程已啟動")
    
    # 註冊快捷鍵 - 使用functools.partial解決閉包問題
    for i, enabled in enumerate(self.combo_enabled):
        if enabled:
            trigger_key = self.combo_sets[i]['trigger_key'].lower()
            try:
                from functools import partial
                hotkey_id = keyboard.add_hotkey(trigger_key,
                                              partial(self.execute_combo, i))
                self.combo_hotkeys[f"combo_{i}"] = hotkey_id
                print(f"註冊快捷鍵: {trigger_key} -> 連段套組 {i+1}")
            except Exception as e:
                print(f"註冊快捷鍵失敗 {trigger_key}: {e}")
    
    # 保持線程運行
    while self.combo_running:
        time.sleep(0.1)
    
    print("連段系統線程已結束")
```

**多線程管理：**

- 連段系統運行在獨立守護線程中
- 支持多個連段套組同時運行
- 使用 `functools.partial` 解決閉包變數問題
- 線程安全的狀態同步

### 配置管理邏輯

#### JSON 配置結構

**配置驗證機制：**

```python
def validate_config(self, config):
    """驗證配置文件的完整性"""
    required_keys = ['health_region', 'mana_region', 'health_threshold']
    
    for key in required_keys:
        if key not in config:
            # 使用默認值補充缺失配置
            config[key] = self.get_default_value(key)
    
    return config
```

**配置熱重載：**

- 支持運行時配置更新
- 無需重啟應用即可應用新設置
- 配置變更的實時驗證

### 圖像處理優化邏輯

#### 性能優化策略

**圖像縮放處理：**

```python
def optimize_image_capture(self, image, target_size=(800, 600)):
    """優化圖像大小以提高處理速度"""
    height, width = image.shape[:2]
    
    # 計算縮放比例
    scale = min(target_size[0] / width, target_size[1] / height)
    
    if scale < 1.0:
        new_width = int(width * scale)
        new_height = int(height * scale)
        image = cv2.resize(image, (new_width, new_height))
    
    return image
```

**記憶體管理：**

- 及時釋放處理完畢的圖像資源
- 使用物件池重用常用資源
- 監控記憶體使用情況

### 錯誤處理邏輯

#### 異常恢復機制

**線程異常處理：**

```python
def monitor_thread_wrapper(self):
    """監控線程異常包裝器"""
    try:
        self.monitor_health()
    except Exception as e:
        self.add_status_message(f"監控線程異常: {e}", "error")
        # 自動重啟監控線程
        if self.monitoring_active:
            self.restart_monitoring()
```

**網路異常處理：**

- 版本檢查失敗時的降級處理
- 連接超時的重試機制
- 離線模式的備用方案

### 數據持久化邏輯

#### 配置保存策略

**原子性寫入：**

```python
def save_config_atomically(self, config, file_path):
    """原子性配置文件保存"""
    # 先寫入臨時文件
    temp_file = file_path + '.tmp'
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    
    # 原子性替換
    os.replace(temp_file, file_path)
```

**備份機制：**

- 自動創建配置備份
- 支持配置回滾功能
- 備份文件清理策略

### 初始化與清理

#### `__init__(self, root)`

初始化 HealthMonitor 實例

- 設置窗口屬性
- 初始化變數
- 載入配置
- 驗證授權
- 創建 GUI 組件

#### `on_closing(self)`

應用關閉處理

- 停止所有線程
- 保存配置
- 清理資源

### GUI 創建與管理

#### `create_widgets(self)`

創建所有 GUI 組件

- 創建標籤頁
- 設置菜單欄
- 初始化各標籤頁內容

#### `create_monitor_tab(self)`

創建監控標籤頁

- 區域選擇控件
- 閾值設置
- 監控狀態顯示

#### `create_inventory_tab(self)`

創建物品欄標籤頁

- 網格坐標設置
- 顏色檢測參數
- 操作按鈕

#### `create_hotkey_tab(self)`

創建熱鍵標籤頁

- 熱鍵綁定控件
- 功能設置

#### `create_combo_tab(self)`

創建連段標籤頁

- 多套組管理
- 技能序列設置
- 延遲控制

### 監控系統

#### `start_monitoring(self)`

啟動監控系統

- 創建監控線程
- 設置監控參數
- 更新 UI 狀態

#### `stop_monitoring(self)`

停止監控系統

- 終止監控線程
- 重置 UI 狀態

#### `monitor_health(self)`

健康監控主循環

- 捕獲遊戲畫面
- 分析血量/魔力區域
- 觸發自動補充

#### `analyze_health_region(self, screenshot, region)`

分析指定區域的健康狀態

- HSV 顏色空間轉換
- 閾值比較
- 狀態判斷

### 熱鍵處理

#### `setup_hotkeys(self)`

設置全域熱鍵

- 註冊熱鍵監聽器
- 綁定回調函數

#### `toggle_monitoring(self)`

切換監控狀態

- F5: 啟動/停止監控

#### `toggle_inventory_scan(self)`

切換物品欄掃描

- F6: 執行物品欄操作

#### `emergency_stop(self)`

緊急停止

- F12: 立即停止所有操作

### 連段系統

#### `start_combo_system(self)`

啟動連段系統

- 驗證配置
- 創建連段線程
- 註冊觸發熱鍵

#### `run_combo_system(self)`

連段系統主循環

- 監聽觸發熱鍵
- 執行技能序列

#### `execute_combo(self, set_index)`

執行指定連段套組

- 模擬按鍵序列
- 處理延遲
- 狀態記錄

### 配置管理

#### `save_config(self)`

保存配置到文件

- 序列化設置
- 寫入 JSON 文件

#### `load_config(self)`

從文件載入配置

- 解析 JSON 配置
- 更新實例變數

#### `save_combo_config(self)`

保存連段配置

- 專門處理連段設置

#### `load_combo_config(self)`

載入連段配置

- 向後相容性處理

### 版本更新

#### `check_for_updates(self)`

檢查 GitHub 最新版本

- API 請求
- 版本比較
- UI 更新

#### `compare_versions(self, current, latest)`

版本號比較

- 語義化版本處理

## 配置選項說明

### 監控配置

```json
{
  "window_title": "Path of Exile 2",
  "region": [103, 895, 33, 160],
  "mana_region": [1767, 894, 33, 159],
  "settings": [
    {
      "type": "health",
      "percent": 60,
      "key": "1",
      "cooldown": 1500
    },
    {
      "type": "mana",
      "percent": 10,
      "key": "2",
      "cooldown": 1500
    }
  ],
  "health_threshold": 0.8,
  "red_h_range": 5,
  "green_h_range": 40,
  "red_saturation_min": 50,
  "red_value_min": 50,
  "green_saturation_min": 50,
  "green_value_min": 50,
  "monitor_interval": 0.1,
  "multi_trigger": true,
  "always_on_top": true
}
```

### 物品欄配置

```json
{
  "inventory_region": [x, y, width, height],
  "inventory_ui_region": [x, y, width, height],
  "interface_ui_region": [x, y, width, height],
  "empty_inventory_colors": [
    [255, 255, 255],
    [254, 254, 254],
    // ... 其他58個格子的基準RGB顏色
  ],
  "inventory_grid_positions": [
    [x1, y1],
    [x2, y2],
    // ... 60個格子的坐標位置
  ],
  "grid_offset_x": 0,
  "grid_offset_y": 0,
  "interface_ui_mse_threshold": 800,
  "interface_ui_ssim_threshold": 0.6,
  "interface_ui_hist_threshold": 0.7,
  "interface_ui_color_threshold": 35
}
```

### 連段配置

```json
{
  "combo_sets": [
    {
      "trigger_key": "Q",
      "combo_keys": ["Q", "Q", "W", "E", "off"],
      "delays": [500, 500, 600, 500, 100],
      "enabled": false,
      "trigger_delay": 500
    },
    {
      "trigger_key": "W",
      "combo_keys": ["", "", "", "", ""],
      "delays": ["", "", "", "", ""],
      "enabled": false
    }
  ],
  "combo_enabled": [false, false, false]
}
```

### F6取物配置

```json
{
  "pickup_coordinates": [
    [0, 0],
    [0, 0],
    [0, 0],
    [0, 0],
    [0, 0]
  ]
}
```

## 維護指南

### 常見問題排查

#### 監控不準確

1. 檢查區域坐標設置
2. 調整 HSV 閾值
3. 確認遊戲分辨率

#### 熱鍵無響應

1. 檢查權限設置
2. 確認鍵盤佈局
3. 查看衝突程序

#### 連段執行異常

1. 驗證技能鍵設置
2. 檢查延遲參數
3. 確認遊戲窗口焦點

### 性能優化

#### 監控頻率調整

- 降低截圖頻率以減少 CPU 使用
- 優化圖像處理算法

#### 記憶體管理

- 及時釋放截圖資源
- 清理不再使用的配置

### 安全注意事項

#### 熱鍵衝突

- 避免與系統熱鍵衝突
- 提供熱鍵衝突檢測

#### 遊戲兼容性

- 定期測試新版本兼容性
- 監控遊戲更新影響

## 擴展指南

### 添加新功能

#### 1. 定義功能需求

- 確定功能範圍
- 設計用戶界面
- 規劃配置結構

#### 2. 實現核心邏輯

- 添加新方法到 HealthMonitor 類
- 實現數據處理邏輯
- 添加錯誤處理

#### 3. 集成到 GUI

- 在適當標籤頁添加控件
- 綁定事件處理器
- 更新狀態顯示

#### 4. 配置管理

- 擴展配置結構
- 添加保存/載入邏輯
- 提供默認值

### 代碼風格規範

#### 命名約定

- 類名: PascalCase
- 方法名: snake_case
- 變數名: snake_case
- 常量: UPPER_CASE

#### 文檔要求

- 每個公共方法添加 docstring
- 複雜邏輯添加註釋
- 保持代碼可讀性

### 測試建議

#### 單元測試

- 測試核心算法
- 驗證配置處理
- 檢查錯誤處理

#### 集成測試

- 測試完整功能流程
- 驗證用戶界面
- 檢查性能表現

## 版本歷史

### v2.0.0

- 重構代碼結構
- 添加連段系統
- 改進用戶界面
- 增強錯誤處理

### v1.5.0

- 添加物品欄管理
- 實現熱鍵系統
- 優化監控算法

### v1.0.0

- 初始版本
- 基本健康監控功能

## 聯繫與支持

如有開發相關問題，請參考：

- 項目文檔
- 源代碼註釋
- GitHub Issues

---

本文檔由 AI 助手根據源代碼分析自動生成，最後更新時間：2024年

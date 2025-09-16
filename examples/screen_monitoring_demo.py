"""
螢幕監控示例 - 展示高效能螢幕截圖和監控技術
此示例展示如何使用 mss 進行高效能的區域監控
"""

import time
import threading
from mss import mss
import numpy as np
from collections import deque

class ScreenMonitorDemo:
    """螢幕監控技術展示類別"""
    
    def __init__(self):
        self.monitoring = False
        self.monitor_thread = None
        self.fps_counter = deque(maxlen=100)  # FPS 計算
        self.sct = mss()
        
        # 監控區域 (示例)
        self.monitor_regions = {
            'health_bar': {'left': 100, 'top': 100, 'width': 200, 'height': 20},
            'mana_bar': {'left': 100, 'top': 130, 'width': 200, 'height': 20}
        }
        
    def start_monitoring(self):
        """開始監控"""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            print("✓ 開始螢幕監控")
            
    def stop_monitoring(self):
        """停止監控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        print("✓ 停止螢幕監控")
        
    def _monitor_loop(self):
        """監控主循環"""
        last_time = time.time()
        
        while self.monitoring:
            try:
                # 記錄開始時間
                start_time = time.time()
                
                # 截取螢幕區域
                self._capture_and_analyze()
                
                # 計算 FPS
                current_time = time.time()
                fps = 1.0 / (current_time - last_time) if current_time > last_time else 0
                self.fps_counter.append(fps)
                last_time = current_time
                
                # 顯示性能統計
                if len(self.fps_counter) % 30 == 0:  # 每30幀顯示一次
                    avg_fps = sum(self.fps_counter) / len(self.fps_counter)
                    print(f"平均 FPS: {avg_fps:.1f}")
                
                # 適應性延遲
                sleep_time = max(0.001, 0.01 - (time.time() - start_time))
                time.sleep(sleep_time)
                
            except Exception as e:
                print(f"監控錯誤: {e}")
                time.sleep(0.1)
                
    def _capture_and_analyze(self):
        """截取並分析螢幕內容"""
        for region_name, region in self.monitor_regions.items():
            try:
                # 高效能螢幕截圖
                screenshot = self._fast_screenshot(region)
                
                # 簡單的分析處理
                analysis_result = self._analyze_region(screenshot, region_name)
                
                # 模擬結果處理
                self._process_analysis_result(region_name, analysis_result)
                
            except Exception as e:
                print(f"區域 {region_name} 處理錯誤: {e}")
                
    def _fast_screenshot(self, region):
        """高效能螢幕截圖"""
        # 構建 mss 格式的區域參數
        monitor = {
            'left': region['left'],
            'top': region['top'],
            'width': region['width'],
            'height': region['height']
        }
        
        # 使用 mss 進行快速截圖
        screenshot = self.sct.grab(monitor)
        
        # 轉換為 numpy 陣列
        img_array = np.array(screenshot)
        
        return img_array
        
    def _analyze_region(self, image, region_name):
        """分析截圖區域"""
        # 模擬顏色檢測
        if region_name == 'health_bar':
            # 模擬紅色檢測
            red_pixels = self._count_color_pixels(image, 'red')
            total_pixels = image.shape[0] * image.shape[1]
            percentage = (red_pixels / total_pixels) * 100
            
        elif region_name == 'mana_bar':
            # 模擬藍色檢測
            blue_pixels = self._count_color_pixels(image, 'blue')
            total_pixels = image.shape[0] * image.shape[1]
            percentage = (blue_pixels / total_pixels) * 100
            
        else:
            percentage = 0
            
        return {
            'percentage': percentage,
            'timestamp': time.time(),
            'region': region_name
        }
        
    def _count_color_pixels(self, image, color):
        """模擬顏色像素計算"""
        # 這裡是簡化的模擬，實際應用會使用 HSV 檢測
        height, width = image.shape[:2]
        
        if color == 'red':
            # 模擬紅色像素檢測
            return int(width * height * 0.7)  # 假設70%是紅色
        elif color == 'blue':
            # 模擬藍色像素檢測
            return int(width * height * 0.8)  # 假設80%是藍色
        else:
            return 0
            
    def _process_analysis_result(self, region_name, result):
        """處理分析結果"""
        percentage = result['percentage']
        
        # 模擬觸發條件檢查
        if region_name == 'health_bar' and percentage < 50:
            print(f"⚠️ 血量低於 50%: {percentage:.1f}%")
            
        elif region_name == 'mana_bar' and percentage < 30:
            print(f"⚠️ 魔力低於 30%: {percentage:.1f}%")
            
    def get_performance_stats(self):
        """獲取性能統計"""
        if not self.fps_counter:
            return None
            
        fps_list = list(self.fps_counter)
        return {
            'avg_fps': sum(fps_list) / len(fps_list),
            'min_fps': min(fps_list),
            'max_fps': max(fps_list),
            'sample_count': len(fps_list)
        }

class AdaptiveMonitor:
    """自適應監控系統"""
    
    def __init__(self):
        self.base_delay = 0.01  # 基礎延遲 10ms
        self.max_delay = 0.1    # 最大延遲 100ms
        self.performance_history = deque(maxlen=50)
        
    def calculate_adaptive_delay(self, processing_time):
        """計算自適應延遲"""
        self.performance_history.append(processing_time)
        
        if len(self.performance_history) < 10:
            return self.base_delay
            
        # 計算平均處理時間
        avg_processing_time = sum(self.performance_history) / len(self.performance_history)
        
        # 根據處理時間調整延遲
        if avg_processing_time > 0.05:  # 處理時間超過50ms
            adaptive_delay = min(self.max_delay, avg_processing_time * 1.5)
        else:
            adaptive_delay = self.base_delay
            
        return adaptive_delay
        
    def optimize_region_size(self, region, performance_target=60):
        """根據性能目標優化監控區域大小"""
        current_fps = self._estimate_fps()
        
        if current_fps < performance_target:
            # 性能不足，縮小監控區域
            scale_factor = 0.9
            region['width'] = int(region['width'] * scale_factor)
            region['height'] = int(region['height'] * scale_factor)
            
        elif current_fps > performance_target * 1.2:
            # 性能充足，可以擴大監控區域
            scale_factor = 1.1
            region['width'] = int(region['width'] * scale_factor)
            region['height'] = int(region['height'] * scale_factor)
            
        return region
        
    def _estimate_fps(self):
        """估算當前 FPS"""
        if len(self.performance_history) < 5:
            return 60  # 預設值
            
        avg_time = sum(self.performance_history) / len(self.performance_history)
        estimated_fps = 1.0 / max(avg_time, 0.001)
        
        return min(120, max(10, estimated_fps))  # 限制在合理範圍內

def demo_screen_monitoring():
    """螢幕監控示例程式"""
    print("=== 螢幕監控技術展示 ===")
    
    # 創建監控實例
    monitor = ScreenMonitorDemo()
    
    # 開始監控
    monitor.start_monitoring()
    
    try:
        # 運行 10 秒
        time.sleep(10)
        
        # 顯示性能統計
        stats = monitor.get_performance_stats()
        if stats:
            print("\n=== 性能統計 ===")
            print(f"平均 FPS: {stats['avg_fps']:.1f}")
            print(f"最低 FPS: {stats['min_fps']:.1f}")
            print(f"最高 FPS: {stats['max_fps']:.1f}")
            print(f"採樣次數: {stats['sample_count']}")
            
    finally:
        # 停止監控
        monitor.stop_monitoring()

if __name__ == "__main__":
    demo_screen_monitoring()
"""
色彩檢測示例 - 展示 HSV 色彩空間檢測技術
此示例展示如何使用 OpenCV 進行遊戲界面元素的顏色檢測
"""

import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk

class ColorDetectionDemo:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("色彩檢測技術展示")
        self.root.geometry("800x600")
        
        self.setup_ui()
        
    def setup_ui(self):
        """設置用戶界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 標題
        title = ttk.Label(main_frame, text="HSV 色彩檢測技術展示", 
                         font=("Arial", 16, "bold"))
        title.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # HSV 參數調整
        self.create_hsv_controls(main_frame)
        
        # 檢測結果顯示
        self.create_result_display(main_frame)
        
    def create_hsv_controls(self, parent):
        """創建 HSV 參數控制組件"""
        control_frame = ttk.LabelFrame(parent, text="HSV 參數調整", padding="10")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # H (色相) 控制
        ttk.Label(control_frame, text="色相 (H):").grid(row=0, column=0, sticky=tk.W)
        self.h_var = tk.IntVar(value=0)
        h_scale = ttk.Scale(control_frame, from_=0, to=179, variable=self.h_var,
                           command=self.update_detection)
        h_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
        
        # S (飽和度) 控制
        ttk.Label(control_frame, text="飽和度 (S):").grid(row=1, column=0, sticky=tk.W)
        self.s_var = tk.IntVar(value=255)
        s_scale = ttk.Scale(control_frame, from_=0, to=255, variable=self.s_var,
                           command=self.update_detection)
        s_scale.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
        
        # V (明度) 控制
        ttk.Label(control_frame, text="明度 (V):").grid(row=2, column=0, sticky=tk.W)
        self.v_var = tk.IntVar(value=255)
        v_scale = ttk.Scale(control_frame, from_=0, to=255, variable=self.v_var,
                           command=self.update_detection)
        v_scale.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
        
        # 容錯範圍
        ttk.Label(control_frame, text="容錯範圍:").grid(row=3, column=0, sticky=tk.W)
        self.tolerance_var = tk.IntVar(value=10)
        tolerance_scale = ttk.Scale(control_frame, from_=1, to=50, variable=self.tolerance_var,
                                   command=self.update_detection)
        tolerance_scale.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
        
    def create_result_display(self, parent):
        """創建檢測結果顯示區域"""
        result_frame = ttk.LabelFrame(parent, text="檢測結果", padding="10")
        result_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 結果文本
        self.result_text = tk.Text(result_frame, height=15, width=40)
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 滾動條
        scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=self.result_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.result_text.configure(yscrollcommand=scrollbar.set)
        
    def update_detection(self, *args):
        """更新檢測參數並顯示結果"""
        h = self.h_var.get()
        s = self.s_var.get()
        v = self.v_var.get()
        tolerance = self.tolerance_var.get()
        
        # 計算 HSV 範圍
        lower_hsv, upper_hsv = self.calculate_hsv_range(h, s, v, tolerance)
        
        # 顯示檢測參數
        result = f"=== HSV 檢測參數 ===\n"
        result += f"目標 HSV: ({h}, {s}, {v})\n"
        result += f"容錯範圍: ±{tolerance}\n"
        result += f"下限: {lower_hsv}\n"
        result += f"上限: {upper_hsv}\n\n"
        
        # 模擬檢測結果
        result += self.simulate_detection(lower_hsv, upper_hsv)
        
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, result)
        
    def calculate_hsv_range(self, h, s, v, tolerance):
        """計算 HSV 檢測範圍"""
        # 處理色相的環形特性
        h_lower = max(0, h - tolerance)
        h_upper = min(179, h + tolerance)
        
        # 飽和度和明度範圍
        s_lower = max(0, s - tolerance * 2)
        s_upper = min(255, s + tolerance * 2)
        
        v_lower = max(0, v - tolerance * 3)
        v_upper = min(255, v + tolerance * 3)
        
        lower_hsv = np.array([h_lower, s_lower, v_lower])
        upper_hsv = np.array([h_upper, s_upper, v_upper])
        
        return lower_hsv, upper_hsv
        
    def simulate_detection(self, lower_hsv, upper_hsv):
        """模擬檢測過程和結果"""
        result = "=== 模擬檢測過程 ===\n"
        
        # 模擬不同色彩的檢測結果
        test_colors = [
            ("紅色血條", [0, 255, 255]),
            ("藍色魔力條", [120, 255, 255]),
            ("綠色背景", [60, 255, 255]),
            ("黃色警告", [30, 255, 255])
        ]
        
        for color_name, hsv_color in test_colors:
            hsv_array = np.array(hsv_color)
            
            # 檢查是否在範圍內
            in_range = np.all(hsv_array >= lower_hsv) and np.all(hsv_array <= upper_hsv)
            
            result += f"{color_name} {hsv_color}: "
            result += "✓ 匹配\n" if in_range else "✗ 不匹配\n"
            
        result += "\n=== 實際應用示例 ===\n"
        result += "1. 截取遊戲畫面\n"
        result += "2. 轉換至 HSV 色彩空間\n"
        result += "3. 套用色彩範圍遮罩\n"
        result += "4. 計算匹配像素比例\n"
        result += "5. 判斷血量/魔力百分比\n"
        
        return result
        
    def run(self):
        """運行示例程式"""
        # 初始化顯示
        self.update_detection()
        self.root.mainloop()

# 進階檢測算法示例
class AdvancedDetection:
    """進階檢測算法展示"""
    
    @staticmethod
    def adaptive_threshold(image, block_size=11, C=2):
        """自適應閾值處理"""
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        adaptive = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, block_size, C
        )
        return adaptive
    
    @staticmethod
    def morphological_operations(mask):
        """形態學操作優化遮罩"""
        kernel = np.ones((3, 3), np.uint8)
        
        # 開運算去除噪聲
        opening = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # 閉運算填補空洞
        closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)
        
        return closing
    
    @staticmethod
    def calculate_bar_percentage(mask, region):
        """計算血條百分比的優化算法"""
        # 提取指定區域
        roi = mask[region['y']:region['y']+region['height'],
                   region['x']:region['x']+region['width']]
        
        # 計算非零像素
        total_pixels = roi.shape[0] * roi.shape[1]
        non_zero_pixels = cv2.countNonZero(roi)
        
        # 計算百分比
        percentage = (non_zero_pixels / total_pixels) * 100
        
        return min(100, max(0, percentage))

if __name__ == "__main__":
    # 運行示例程式
    demo = ColorDetectionDemo()
    demo.run()
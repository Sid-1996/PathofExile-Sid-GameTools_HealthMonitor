import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import threading
import time
import mss
import cv2
import numpy as np
import keyboard
import pygetwindow as gw
from PIL import Image, ImageTk, ImageDraw
import sys
import pyautogui
import ctypes
import subprocess
from datetime import datetime
import psutil
import requests
import functools

# 版本資訊
CURRENT_VERSION = "v1.0.2"
GITHUB_REPO = "Sid-1996/PathofExile-Sid-GameTools_HealthMonitor"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# Windows API 常數和函數
user32 = ctypes.windll.user32
GetForegroundWindow = user32.GetForegroundWindow
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
SendMessageW = user32.SendMessageW
PostMessageW = user32.PostMessageW

# Windows 虛擬鍵碼常數
VK_RETURN = 0x0D
VK_ESCAPE = 0x1B
VK_SPACE = 0x20
VK_TAB = 0x09
VK_BACK = 0x08
VK_DELETE = 0x2E
VK_HOME = 0x24
VK_END = 0x23
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_F3 = 0x72
VK_F5 = 0x74
VK_F6 = 0x75
VK_F7 = 0x76
VK_F8 = 0x77
VK_F9 = 0x78
VK_F10 = 0x79
VK_F12 = 0x7B

# Windows 消息常數
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_CHAR = 0x0102

# 設定函數參數類型
GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
GetWindowTextLengthW.restype = ctypes.c_int
GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
GetWindowTextW.restype = ctypes.c_int
SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_long]
SendMessageW.restype = ctypes.c_long

def get_app_dir():
    """獲取應用程式目錄，適用於開發環境和打包後的exe"""
    if getattr(sys, 'frozen', False):
        # 如果是打包後的exe
        return os.path.dirname(sys.executable)
    else:
        # 如果是開發環境
        return os.path.dirname(__file__)

class HealthMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("遊戲輔助工具 v1.0.2 - 血魔監控 + 一鍵清包 + 自動化工具")
        # 初始設定為較小的視窗，讓智能自適應功能接管
        self.root.geometry("900x700")  
        self.root.minsize(800, 600)    # 設定最小尺寸防止內容被擠壓
        # 移除預設的 -topmost 設定，讓設定載入時決定
        self.root.attributes("-alpha", 1.0)  # 預設完全不透明

        # 設定檔案路徑 - 使用應用程式目錄確保在打包後也能正確存取
        self.config_file = os.path.join(get_app_dir(), "health_monitor_config.json")

        # 初始化基本設定變數（在載入設定之前）
        self.config = {}

        # GUI最上方設定變數
        self.always_on_top_var = tk.BooleanVar(value=True)  # 預設保持在最上方

        # 監控間隔設定（預設100ms）
        self.monitor_interval = 0.1

        # 框選相關變數
        self.selection_active = False
        self.selection_start = None
        self.selection_end = None
        self.selected_region = None
        self.selected_mana_region = None

        # 一鍵清包相關變數
        self.inventory_region = None
        self.empty_inventory_colors = []  # 60個格子的顏色
        self.inventory_grid_positions = []  # 60個格子的位置
        # 格子偏移調整變數
        self.grid_offset_x = 0  # 水平偏移
        self.grid_offset_y = 0  # 垂直偏移
        self.inventory_window_var = tk.StringVar(value='')
        self.inventory_selection_active = False
        self.inventory_selection_start = None
        self.inventory_selection_end = None

        # 背包UI安全檢查相關變數
        self.inventory_ui_screenshot = None  # 背包UI截圖
        self.inventory_ui_region = None  # 背包UI區域
        self.inventory_ui_selection_active = False
        self.inventory_ui_selection_start = None
        self.inventory_ui_selection_end = None

        # 介面UI戰鬥狀態檢查相關變數
        self.interface_ui_screenshot = None  # 介面UI截圖
        self.interface_ui_region = None  # 介面UI區域
        self.interface_ui_selection_active = False
        self.interface_ui_selection_start = None
        self.interface_ui_selection_end = None

        # UI預覽相關變數
        self.ui_preview_image = None  # 用於Canvas顯示的PhotoImage

        # F3清包中斷控制變數
        self.inventory_clear_interrupt = False  # 中斷標誌
        
        # GUI動態縮小相關變數
        self.gui_minimized_for_clear = False  # GUI是否因清包而縮小
        self.original_gui_geometry = None  # 原始GUI位置和大小
        self.original_gui_state = None  # 原始GUI狀態
        self.gui_was_foreground_before_minimize = True  # GUI縮小前是否在前台
        
        # F6一鍵取物功能變數
        self.pickup_coordinates = []  # 儲存5個取物座標 [x, y]

        # 全域暫停功能變數
        self.global_pause = False  # 全域暫停狀態
        self.pause_status_label = None  # 暫停狀態顯示標籤
        self.monitoring_was_active = False  # 記錄血魔監控在暫停前的狀態
        self.combo_was_running = False  # 記錄技能連段在暫停前的狀態

        # 狀態更新控制變數
        self.last_status_update = 0
        self.status_update_interval = 100  # 100ms更新一次狀態

        # 顏色檢測參數（可調整）
        self.health_threshold = 0.8  # 健康像素比例閾值 - 優化為0.8以提高檢測準確性
        self.red_h_range = 5  # 紅色H範圍上限 - 優化為5以提高紅色檢測精準度
        self.green_h_range = 40  # 綠色H範圍下限
        
        # 新增HSV顏色參數
        self.red_saturation_min = 50   # 紅色最小鮮豔度
        self.red_value_min = 50        # 紅色最小明亮度
        self.green_saturation_min = 50  # 綠色最小鮮豔度
        self.green_value_min = 50      # 綠色最小明亮度

        # 介面UI檢測參數（可調整）
        self.interface_ui_mse_threshold = 800  # MSE閾值
        self.interface_ui_ssim_threshold = 0.6  # SSIM閾值
        self.interface_ui_hist_threshold = 0.7  # 直方圖相似度閾值
        self.interface_ui_color_threshold = 35  # 顏色差異閾值

        # 冷卻時間追蹤變數
        self.last_trigger_times = {}  # key: health_percent, value: timestamp

        # 技能連段相關變數
        self.combo_sets = []  # 儲存3個連段套組的設定
        self.combo_enabled = [False, False, False]  # 每個套組的啟用狀態
        self.combo_thread = None  # 連段執行線程
        self.combo_running = False  # 連段執行狀態
        self.combo_hotkeys = {}  # 連段快捷鍵綁定
        
        # 連段UI元件引用
        self.combo_ui_refs = []  # 儲存UI元件引用用於設定載入

        # 滑鼠自動點擊相關變數 (使用AHK實現)
        self.auto_click_process = None  # AHK自動點擊進程
        self.auto_click_script_path = os.path.join(get_app_dir(), "auto_click.ahk")
        self.auto_click_exe_path = os.path.join(get_app_dir(), "auto_click.exe")  # EXE版本路徑

        # 執行狀態記錄相關變數
        self.status_log = []  # 儲存狀態訊息
        self.status_log_max_lines = 100  # 最大記錄行數
        self.last_status_message = ""  # 記錄上一條訊息，避免重複
        self.status_text_widget = None  # 狀態顯示文字區域

        # GUI 元件
        self.create_widgets()

        # 在UI元件創建後載入設定
        self.load_config()

        # 將窗口置中於螢幕（如果沒有儲存的位置）
        self.center_window()

        # 確保GUI最上方設定正確應用（無論設定載入是否成功）
        self.root.attributes("-topmost", self.always_on_top_var.get())

        # 設置全域滾輪支持
        self.setup_global_scroll()

        # 配置pyautogui
        pyautogui.FAILSAFE = False  # 禁用failsafe，因為我們需要精確控制
        pyautogui.PAUSE = 0  # 移除按鍵間的預設延遲

        # 如果有已儲存的設定，自動載入預覽
        self.auto_load_preview()

        # 監控狀態
        self.monitoring = False
        self.monitor_thread = None

        # 快捷鍵設定
        self.setup_hotkeys()

        # 設置GUI關閉事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 設置右鍵中斷功能
        self.setup_mouse_interrupt()
        
        # 應用程式啟動完成訊息
        self.add_status_message("遊戲輔助工具已啟動完成", "success")
        self.add_status_message("熱鍵: F3一鍵清包 | F5返回藏身 | F6一鍵取物 | F9全域暫停 | F10血魔監控開關", "info")

    def setup_mouse_interrupt(self):
        """設置滑鼠右鍵中斷功能"""
        # 啟動背景線程監聽右鍵事件
        self.mouse_interrupt_thread = threading.Thread(target=self.monitor_mouse_interrupt, daemon=True)
        self.mouse_interrupt_thread.start()

    def monitor_mouse_interrupt(self):
        """監聽滑鼠右鍵事件用於中斷F3清包"""
        self.add_status_message("滑鼠中斷監聽已啟動 - 按住右鍵2秒可中斷F3清包", "info")
        print("滑鼠中斷監聽已啟動 - 按住右鍵2秒可中斷F3清包")

        right_click_start = None
        interrupt_threshold = 2.0  # 2秒閾值
        last_right_button_state = False  # 記錄上一次的右鍵狀態

        while True:
            try:
                # 使用GetKeyState檢查右鍵狀態，適用於持續按下檢測
                VK_RBUTTON = 0x02  # 右鍵虛擬鍵碼
                current_right_button_state = (ctypes.windll.user32.GetKeyState(VK_RBUTTON) & 0x8000) != 0

                if current_right_button_state and not last_right_button_state:
                    # 右鍵剛剛被按下
                    right_click_start = time.time()
                    print("檢測到右鍵按下，開始計時...")
                elif not current_right_button_state and last_right_button_state:
                    # 右鍵剛剛被釋放
                    if right_click_start is not None:
                        duration = time.time() - right_click_start
                        if duration >= interrupt_threshold:
                            print(f"右鍵按住 {duration:.1f} 秒，觸發F3清包中斷")
                            self.inventory_clear_interrupt = True
                        right_click_start = None

                last_right_button_state = current_right_button_state
                time.sleep(0.1)  # 每100ms檢查一次

            except Exception as e:
                print(f"滑鼠中斷監聽錯誤: {e}")
                time.sleep(1)  # 錯誤時稍作延遲

    def center_window(self):
        """將窗口置中於螢幕，如果沒有儲存的位置"""
        try:
            # 檢查是否已經有儲存的窗口位置
            if hasattr(self, 'config') and 'window_geometry' in self.config:
                print("已有儲存的窗口位置，跳過置中")
                return
            
            # 更新窗口以獲取正確的尺寸
            self.root.update_idletasks()
            
            # 獲取螢幕尺寸
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # 獲取窗口尺寸
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()
            
            # 如果窗口還沒有正確的尺寸，使用預設尺寸
            if window_width <= 1:
                window_width = 900
            if window_height <= 1:
                window_height = 700
            
            # 計算置中位置
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            
            # 確保位置不超出螢幕邊界
            x = max(0, x)
            y = max(0, y)
            
            # 設置窗口位置和尺寸
            self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
            
            print(f"窗口已置中: 螢幕 {screen_width}x{screen_height}, 窗口 {window_width}x{window_height}, 位置 ({x}, {y})")
            
        except Exception as e:
            print(f"置中窗口時發生錯誤: {e}")
            # 出錯時設置一個預設位置
            self.root.geometry("900x700+100+100")

    def create_widgets(self):
        # 創建分頁容器
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 分頁排列順序說明：
        # 主要功能分頁（前置）：
        # 1. 血魔監控 - 核心監控功能
        # 2. 一鍵清包 - 自動清包功能
        # 3. 技能連段 - 連段設定功能
        # 4. 使用說明 - 幫助文檔
        #
        # 系統資訊分頁（後置）：
        # 5. 授權資訊 - 軟體授權資訊
        # 6. 版本檢查 - 版本更新檢查

        # 第一個分頁：血魔監控
        self.monitor_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.monitor_frame, text="血魔監控")

        # 第二個分頁：一鍵清包
        self.inventory_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.inventory_frame, text="一鍵清包")

        # 第三個分頁：技能連段（插入到一鍵清包和使用說明之間）
        self.combo_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.combo_frame, text="技能連段")

        # 第四個分頁：執行狀態（新增）
        self.status_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.status_frame, text="執行狀態")

        # 第五個分頁：使用說明（系統資訊分頁 - 擺在最後）
        self.help_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.help_frame, text="使用說明")

        # 第六個分頁：版本檢查（系統資訊分頁 - 擺在最後）
        self.version_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.version_frame, text="版本檢查")

        # 第七個分頁：關於（系統資訊分頁 - 擺在最後）
        self.about_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.about_frame, text="🚀 關於作者")

        # 綁定分頁切換事件來實現智能自適應視窗大小
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)
        
        # 初始化分頁最小尺寸字典
        self.tab_min_sizes = {
            "血魔監控": (1050, 750),  # 血魔監控：左右分欄+圖表，需要適中空間
            "一鍵清包": (1350, 850),  # 一鍵清包：控件最多，需要最大空間
            "技能連段": (1200, 800),  # 技能連段：F6取物功能，需要中等空間
            "執行狀態": (900, 700),   # 執行狀態：文字顯示區域
            "使用說明": (900, 700),   # 使用說明：主要是文字內容
            "版本檢查": (850, 650),   # 版本檢查：簡單狀態顯示
            "🚀 關於作者": (600, 500)       # 關於：按鈕和文字說明
        }

        # 創建各分頁內容
        self.create_monitor_tab()
        self.create_inventory_tab()
        self.create_combo_tab()
        self.create_status_tab()  # 新增執行狀態分頁
        self.create_help_tab()
        self.create_version_tab()
        self.create_about_tab()  # 新增關於分頁
        
        # 初始化：設定當前分頁的視窗大小
        self.root.after(100, self.adjust_window_for_current_tab)
        
        # 恢復上次選擇的分頁
        self.root.after(200, self.restore_last_selected_tab)

    def on_tab_change(self, event):
        """分頁切換事件處理 - 智能自適應視窗大小"""
        try:
            # 獲取當前選中的分頁
            current_tab = self.notebook.tab(self.notebook.select(), "text")
            
            # 調整視窗大小以適應當前分頁
            self.adjust_window_for_tab(current_tab)
            
            # 保存當前分頁到配置中
            self.config['last_selected_tab'] = current_tab
            
        except Exception as e:
            print(f"分頁切換調整視窗大小時發生錯誤: {e}")
    
    def adjust_window_for_tab(self, tab_name):
        """根據分頁名稱調整視窗大小"""
        if tab_name in self.tab_min_sizes:
            min_width, min_height = self.tab_min_sizes[tab_name]
            
            # 嘗試動態計算實際最小尺寸
            try:
                dynamic_size = self.calculate_dynamic_tab_size(tab_name)
                if dynamic_size:
                    dyn_width, dyn_height = dynamic_size
                    # 使用動態計算和預設值的較大者
                    min_width = max(min_width, dyn_width + 50)  # 添加50px緩衝
                    min_height = max(min_height, dyn_height + 100)  # 添加100px緩衝
            except Exception as e:
                print(f"動態計算分頁大小失敗，使用預設值: {e}")
            
            # 獲取當前視窗大小和位置
            current_geometry = self.root.geometry()
            current_parts = current_geometry.split('+')
            current_size = current_parts[0].split('x')
            current_width = int(current_size[0])
            current_height = int(current_size[1])
            
            # 智能調整：如果當前尺寸小於所需最小尺寸，則調整到最小尺寸
            # 如果當前尺寸已經足夠，則不縮小視窗
            new_width = max(current_width, min_width)
            new_height = max(current_height, min_height)
            
            # 只有在需要放大視窗時才調整
            if new_width > current_width or new_height > current_height:
                # 保持視窗位置不變，只調整大小
                if len(current_parts) >= 3:
                    x_pos = current_parts[1]
                    y_pos = current_parts[2]
                    new_geometry = f"{new_width}x{new_height}+{x_pos}+{y_pos}"
                else:
                    new_geometry = f"{new_width}x{new_height}"
                
                self.root.geometry(new_geometry)
                print(f"已擴大視窗以適應 '{tab_name}' 分頁: {new_width}x{new_height}")
            else:
                print(f"當前視窗大小已適合 '{tab_name}' 分頁，無需調整")
    
    def calculate_dynamic_tab_size(self, tab_name):
        """動態計算分頁內容的實際最小尺寸"""
        try:
            # 根據分頁名稱獲取對應的框架
            frame_map = {
                "血魔監控": self.monitor_frame,
                "一鍵清包": self.inventory_frame,
                "技能連段": self.combo_frame,
                "使用說明": self.help_frame,
                "版本檢查": self.version_frame,
                "🚀 關於作者": self.about_frame
            }
            
            if tab_name not in frame_map:
                return None
                
            frame = frame_map[tab_name]
            
            # 強制更新佈局
            frame.update_idletasks()
            
            # 獲取框架的實際所需尺寸
            req_width = frame.winfo_reqwidth()
            req_height = frame.winfo_reqheight()
            
            # 加上Notebook和其他元素的額外空間
            total_width = req_width + 40  # padding和borders
            total_height = req_height + 80  # 分頁標籤和padding
            
            return (total_width, total_height)
            
        except Exception as e:
            print(f"計算 '{tab_name}' 動態尺寸時發生錯誤: {e}")
            return None
    
    def adjust_window_for_current_tab(self):
        """調整視窗大小以適應當前分頁"""
        try:
            current_tab = self.notebook.tab(self.notebook.select(), "text")
            self.adjust_window_for_tab(current_tab)
        except Exception as e:
            print(f"初始化視窗大小調整時發生錯誤: {e}")
    
    def restore_last_selected_tab(self):
        """恢復上次選擇的分頁"""
        try:
            if 'last_selected_tab' in self.config:
                last_tab = self.config['last_selected_tab']
                
                # 尋找對應的分頁索引
                for i in range(self.notebook.index("end")):
                    tab_text = self.notebook.tab(i, "text")
                    if tab_text == last_tab:
                        self.notebook.select(i)
                        self.adjust_window_for_tab(last_tab)
                        print(f"已恢復到上次選擇的分頁: {last_tab}")
                        break
        except Exception as e:
            print(f"恢復上次分頁時發生錯誤: {e}")

    def create_monitor_tab(self):
        # 主框架
        main_frame = self.monitor_frame

        # 創建左右分欄佈局
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))

        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # 設定列寬
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=0)
        main_frame.rowconfigure(0, weight=1)

        # === 左側區域：控制面板 ===
        # 遊戲視窗選擇區域
        window_frame = ttk.LabelFrame(left_frame, text="遊戲視窗設定", padding="10")
        window_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(window_frame, text="遊戲視窗:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.window_var = tk.StringVar(value=self.config.get('window_title', ''))
        self.window_combo = ttk.Combobox(window_frame, textvariable=self.window_var, width=35)
        self.window_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        ttk.Button(window_frame, text="重新整理", command=self.refresh_windows).grid(row=0, column=2, padx=(5, 0))

        ttk.Label(window_frame, text="血量條區域:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.region_label = ttk.Label(window_frame, text=self.get_region_text(), background="lightgray", relief="sunken", padding=2)
        self.region_label.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))

        ttk.Label(window_frame, text="魔力條區域:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.mana_region_label = ttk.Label(window_frame, text=self.get_mana_region_text(), background="lightgray", relief="sunken", padding=2)
        self.mana_region_label.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))

        ttk.Label(window_frame, text="介面UI區域:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.interface_ui_label = ttk.Label(window_frame, text=self.get_interface_ui_region_text(), background="lightgray", relief="sunken", padding=2)
        self.interface_ui_label.grid(row=3, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))

        ttk.Button(window_frame, text="📦 框選血量區域", command=self.start_selection).grid(row=4, column=0, pady=(5, 0))
        ttk.Button(window_frame, text="🔵 框選魔力區域", command=self.start_mana_selection).grid(row=4, column=1, pady=(5, 0), padx=(5, 0))
        ttk.Button(window_frame, text="🖼️ 框選介面UI", command=self.select_interface_ui_region).grid(row=4, column=2, pady=(5, 0), padx=(5, 0))

        # 設定列寬
        window_frame.columnconfigure(1, weight=1)

        # 觸發設定區域
        settings_frame = ttk.LabelFrame(left_frame, text="觸發設定", padding="10")
        settings_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # 新增設定區域
        add_frame = ttk.Frame(settings_frame)
        add_frame.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(add_frame, text="類型:").grid(row=0, column=0, sticky=tk.W)
        self.type_var = tk.StringVar(value="health")
        type_combo = ttk.Combobox(add_frame, textvariable=self.type_var, 
                                 values=["health", "mana"], state="readonly", width=8)
        type_combo.grid(row=0, column=1, padx=(5, 0))
        type_combo.bind("<<ComboboxSelected>>", self.on_type_changed)

        ttk.Label(add_frame, text="百分比:").grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        self.percent_var = tk.StringVar(value="60")
        ttk.Entry(add_frame, textvariable=self.percent_var, width=8).grid(row=0, column=3, padx=(5, 0))

        ttk.Label(add_frame, text="快捷鍵:").grid(row=0, column=4, sticky=tk.W, padx=(10, 0))
        self.key_var = tk.StringVar(value="1")
        ttk.Entry(add_frame, textvariable=self.key_var, width=12).grid(row=0, column=5, padx=(5, 0))

        ttk.Label(add_frame, text="冷卻(ms):").grid(row=0, column=6, sticky=tk.W, padx=(10, 0))
        self.cooldown_var = tk.StringVar(value="1500")
        ttk.Entry(add_frame, textvariable=self.cooldown_var, width=8).grid(row=0, column=7, padx=(5, 0))

        ttk.Button(add_frame, text="➕ 新增", command=self.add_setting_new).grid(row=0, column=8, padx=(10, 0))

        # 觸發選項區域
        options_frame = ttk.Frame(settings_frame)
        options_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))

        ttk.Button(options_frame, text="🗑️ 移除選取", command=self.remove_setting).grid(row=0, column=0, padx=(0, 0))
        ttk.Button(options_frame, text="🎨 調整顏色", command=self.adjust_colors).grid(row=0, column=1, padx=(20, 0))
        ttk.Button(options_frame, text="🖼️ 調整介面UI", command=self.adjust_interface_ui_thresholds).grid(row=0, column=2, padx=(10, 0))

        # 多重觸發選項
        self.multi_trigger_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="多重觸發 (允許多個設定同時觸發)",
                        variable=self.multi_trigger_var).grid(row=0, column=3, columnspan=2, sticky=tk.W, pady=(0, 0), padx=(20, 0))

        # 配置列寬以防止重疊
        options_frame.columnconfigure(0, weight=0)
        options_frame.columnconfigure(1, weight=0)
        options_frame.columnconfigure(2, weight=0)
        options_frame.columnconfigure(3, weight=1)
        options_frame.columnconfigure(4, weight=0)

        # 設定列表
        list_frame = ttk.Frame(settings_frame)
        list_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))

        self.settings_tree = ttk.Treeview(list_frame, columns=("type", "percent", "key", "cooldown"), show="headings", height=4)
        self.settings_tree.heading("type", text="類型")
        self.settings_tree.heading("percent", text="百分比")
        self.settings_tree.heading("key", text="快捷鍵")
        self.settings_tree.heading("cooldown", text="冷卻(ms)")
        self.settings_tree.column("type", width=60, anchor="center")
        self.settings_tree.column("percent", width=60, anchor="center")
        self.settings_tree.column("key", width=100, anchor="center")
        self.settings_tree.column("cooldown", width=80, anchor="center")

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.settings_tree.yview)
        self.settings_tree.configure(yscrollcommand=scrollbar.set)

        self.settings_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # 設定列寬
        settings_frame.columnconfigure(3, weight=1)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # 載入現有設定
        self.load_settings_to_tree()

        # 控制按鈕區域
        control_frame = ttk.LabelFrame(left_frame, text="控制面板", padding="10")
        control_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        self.start_btn = ttk.Button(control_frame, text="▶️ 開始監控", command=self.start_monitoring)
        self.start_btn.grid(row=0, column=0, padx=(0, 5))

        self.stop_btn = ttk.Button(control_frame, text="⏹️ 停止監控", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=1, padx=(0, 5))

        ttk.Button(control_frame, text="💾 儲存設定", command=self.save_config).grid(row=0, column=2)

        # 檢查頻率設定
        ttk.Label(control_frame, text="檢查頻率:").grid(row=1, column=0, sticky=tk.W, pady=(15, 0))
        self.monitor_interval_var = tk.StringVar(value=str(int(self.monitor_interval * 1000)))  # 根據初始化值設定
        interval_combo = ttk.Combobox(control_frame, textvariable=self.monitor_interval_var,
                                     values=["25", "50", "100"], state="readonly", width=8)
        interval_combo.grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=(15, 0))
        ttk.Label(control_frame, text="ms").grid(row=1, column=2, sticky=tk.W, pady=(15, 0))

        # 重要提醒區域
        reminder_frame = ttk.LabelFrame(control_frame, text="⚠️ 重要提醒", padding="8")
        reminder_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(20, 5))

        reminder_text = """請在遊戲中開啟以下設定以確保程式正常運作：
設定 > 介面 > 隱藏生命/魔力保留 > ✓ 打勾"""

        reminder_label = ttk.Label(reminder_frame, text=reminder_text,
                                  font=("Arial", 9), foreground="red",
                                  justify=tk.LEFT, wraplength=400)
        reminder_label.grid(row=0, column=0, sticky=(tk.W, tk.E))

        # 預覽控制選項
        preview_control_frame = ttk.Frame(control_frame)
        preview_control_frame.grid(row=3, column=0, columnspan=3, pady=(10, 0))

        ttk.Label(preview_control_frame, text="即時預覽:").grid(row=0, column=0, sticky=tk.W)
        self.preview_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(preview_control_frame, text="啟用", variable=self.preview_enabled).grid(row=0, column=1, sticky=tk.W, padx=(5, 0))

        ttk.Label(preview_control_frame, text="更新間隔:").grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        self.preview_interval_var = tk.StringVar(value="250")
        ttk.Entry(preview_control_frame, textvariable=self.preview_interval_var, width=8).grid(row=0, column=3, padx=(5, 0))
        ttk.Label(preview_control_frame, text="ms").grid(row=0, column=4, sticky=tk.W)

        ttk.Button(preview_control_frame, text="🔄 測試預覽", command=self.test_preview).grid(row=0, column=5, padx=(20, 0))

        # GUI最上方設定選項
        gui_control_frame = ttk.Frame(control_frame)
        gui_control_frame.grid(row=4, column=0, columnspan=3, pady=(10, 0))

        ttk.Label(gui_control_frame, text="GUI設定:").grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(gui_control_frame, text="永遠保持在最上方", variable=self.always_on_top_var, 
                       command=self.toggle_always_on_top).grid(row=0, column=1, columnspan=2, sticky=tk.W, padx=(5, 0))

        # === 右側區域：狀態顯示和預覽 ===
        # 即時狀態區域
        status_frame = ttk.LabelFrame(right_frame, text="即時狀態", padding="10")
        status_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # 狀態資訊
        ttk.Label(status_frame, text="💓 當前血量:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.health_label = ttk.Label(status_frame, text="--", font=("Arial", 12, "bold"), foreground="red", width=8, anchor="w")
        self.health_label.grid(row=0, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        ttk.Label(status_frame, text="🔵 當前魔力:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky=tk.W, pady=2)
        self.mana_label = ttk.Label(status_frame, text="--", font=("Arial", 12, "bold"), foreground="blue", width=8, anchor="w")
        self.mana_label.grid(row=1, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        ttk.Label(status_frame, text="🎨 主要顏色:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.color_label = ttk.Label(status_frame, text="--", width=20, anchor="w")
        self.color_label.grid(row=2, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        ttk.Label(status_frame, text="⚡ 觸發狀態:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.trigger_label = ttk.Label(status_frame, text="--", width=35, anchor="w")
        self.trigger_label.grid(row=3, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        # 區域預覽
        preview_frame = ttk.LabelFrame(right_frame, text="區域預覽", padding="10")
        preview_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 創建預覽區域的左右分欄
        health_preview_frame = ttk.LabelFrame(preview_frame, text="血量預覽", padding="5")
        health_preview_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))

        self.preview_label = ttk.Label(health_preview_frame, text="請先框選血量條區域", relief="sunken", background="lightgray", width=45, anchor="center")
        self.preview_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        mana_preview_frame = ttk.LabelFrame(preview_frame, text="魔力預覽", padding="5")
        mana_preview_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))

        self.mana_preview_label = ttk.Label(mana_preview_frame, text="請先框選魔力條區域", relief="sunken", background="lightblue", width=45, anchor="center")
        self.mana_preview_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 設定預覽區域大小
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.columnconfigure(1, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        health_preview_frame.columnconfigure(0, weight=1)
        health_preview_frame.rowconfigure(0, weight=1)
        mana_preview_frame.columnconfigure(0, weight=1)
        mana_preview_frame.rowconfigure(0, weight=1)

        # 介面UI預覽區域
        interface_ui_preview_frame = ttk.LabelFrame(right_frame, text="介面UI預覽", padding="5")
        interface_ui_preview_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        # 創建一個Canvas來顯示介面UI截圖 (縮小尺寸)
        self.interface_ui_preview_canvas = tk.Canvas(interface_ui_preview_frame, width=150, height=100, bg='lightgray', relief='sunken')
        self.interface_ui_preview_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E))

        # 添加說明文字
        ttk.Label(interface_ui_preview_frame, text="當您框選介面UI後，截圖將顯示在上面",
                 font=("", 7), foreground="gray").grid(row=1, column=0, sticky=tk.W, pady=(3, 0))

        right_frame.rowconfigure(1, weight=1)

        # 設定預覽標籤的固定尺寸以保持一致性
        self.preview_size = (380, 280)  # 更大的預覽尺寸 (寬度, 高度)
        
        # 為預覽框架設定更大的最小高度
        health_preview_frame.config(height=300)
        mana_preview_frame.config(height=300)

        # 初始化視窗列表
        self.refresh_windows()

        # 初始化變數
        self.last_preview_update = 0
        self.preview_update_interval = 500  # 500ms更新一次預覽圖片
        self.last_health_percent = -1
        self.last_mana_percent = -1
        self.last_mana_preview_update = 0

    def on_type_changed(self, event=None):
        """當類型選擇改變時更新預設值"""
        if self.type_var.get() == "health":
            self.percent_var.set("60")
            self.key_var.set("1")
        else:  # mana
            self.percent_var.set("10")
            self.key_var.set("2")

    def test_preview(self):
        """手動測試預覽功能"""
        if not self.window_var.get():
            messagebox.showerror("錯誤", "請先選擇遊戲視窗")
            return

        try:
            # 獲取遊戲視窗
            windows = gw.getWindowsWithTitle(self.window_var.get())
            if not windows:
                messagebox.showerror("錯誤", f"找不到遊戲視窗: {self.window_var.get()}")
                return

            window = windows[0]

            # 激活遊戲視窗
            window.activate()
            time.sleep(0.1)  # 給一點時間讓視窗激活

            success_count = 0
            
            # 測試血量預覽
            if self.config.get('region'):
                try:
                    self.capture_preview()
                    success_count += 1
                    print("血量預覽測試完成")
                except Exception as e:
                    print(f"血量預覽測試失敗: {e}")

            # 測試魔力預覽
            if self.config.get('mana_region'):
                try:
                    self.capture_mana_preview()
                    success_count += 1
                    print("魔力預覽測試完成")
                except Exception as e:
                    print(f"魔力預覽測試失敗: {e}")
            
            if success_count > 0:
                messagebox.showinfo("成功", f"預覽測試完成！已更新 {success_count} 個預覽")
            else:
                messagebox.showwarning("警告", "沒有可測試的區域設定\n請先框選血量或魔力區域")

        except Exception as e:
            messagebox.showerror("錯誤", f"預覽測試失敗: {str(e)}")

    def toggle_always_on_top(self):
        """切換GUI是否保持在最上方"""
        try:
            is_topmost = self.always_on_top_var.get()
            self.root.attributes("-topmost", is_topmost)
            print(f"GUI最上方設定已{'啟用' if is_topmost else '停用'}")

            # 自動保存設定
            try:
                self.config['always_on_top'] = is_topmost
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=2, ensure_ascii=False)
                print("GUI最上方設定已自動保存")
            except Exception as save_error:
                print(f"自動保存設定失敗: {save_error}")

        except Exception as e:
            print(f"切換GUI最上方設定失敗: {e}")

    def should_keep_topmost(self):
        """檢查是否應該保持GUI在最上方（根據用戶設定）"""
        return self.always_on_top_var.get()

    def set_topmost_if_enabled(self):
        """如果用戶啟用了永遠在最上方，則設定為置頂"""
        if self.should_keep_topmost():
            self.root.attributes("-topmost", True)

    def manage_window_hierarchy(self, window, level="SETTINGS"):
        """
        管理視窗層級系統
        層級從高到低: CHILD > SETTINGS > MAIN
        - CHILD: 子視窗（提示視窗、測試視窗等）- 最高層級
        - SETTINGS: 設定視窗（顏色調整、背包設定等）- 中間層級
        - MAIN: 主介面 - 最低層級（根據用戶設定決定是否置頂）
        """
        try:
            # 首先取消所有視窗的置頂，然後按層級重新設置
            self.root.attributes("-topmost", False)

            # 關閉所有現有的子視窗置頂
            for child in self.root.winfo_children():
                if isinstance(child, tk.Toplevel):
                    try:
                        child.attributes("-topmost", False)
                    except:
                        pass

            # 根據層級設置置頂
            if level == "CHILD":
                # 子視窗最高層級
                window.attributes("-topmost", True)
                # 主介面根據用戶設定決定
                if self.should_keep_topmost():
                    self.root.attributes("-topmost", True)
            elif level == "SETTINGS":
                # 設定視窗中間層級
                if self.should_keep_topmost():
                    self.root.attributes("-topmost", True)
                window.attributes("-topmost", True)
            elif level == "MAIN":
                # 主介面層級
                if self.should_keep_topmost():
                    self.root.attributes("-topmost", True)

        except Exception as e:
            print(f"管理視窗層級時發生錯誤: {e}")

    def create_settings_window(self, title, geometry="800x600", parent=None):
        """創建設定視窗（中間層級）"""
        window = tk.Toplevel(parent or self.root)
        window.title(title)
        window.geometry(geometry)
        self.manage_window_hierarchy(window, "SETTINGS")
        return window

    def create_child_window(self, title, geometry="400x300", parent=None):
        """創建子視窗（最高層級）"""
        window = tk.Toplevel(parent or self.root)
        window.title(title)
        window.geometry(geometry)
        self.manage_window_hierarchy(window, "CHILD")
        return window

    def test_window_hierarchy(self):
        """測試視窗層級系統"""
        print("🧪 測試視窗層級系統...")

        # 創建一個測試設定視窗
        test_settings = self.create_settings_window("測試設定視窗", "300x200")
        test_label = ttk.Label(test_settings, text="這是設定視窗（中層級）")
        test_label.pack(pady=20)

        def test_reset_function():
            """測試重置功能是否會重新激活父視窗"""
            messagebox.showinfo("測試重置", "這是測試重置完成訊息")
            # 重新激活父視窗
            test_settings.lift()
            test_settings.focus_force()
            test_settings.attributes("-topmost", True)

        ttk.Button(test_settings, text="測試重置功能", command=test_reset_function).pack(pady=10)
        ttk.Button(test_settings, text="關閉設定視窗", command=test_settings.destroy).pack(pady=10)

        print("✅ 視窗層級測試完成 - 請測試重置功能是否會重新激活父視窗")

    def activate_game_window(self):
        """激活遊戲視窗"""
        try:
            if self.window_var.get():
                import pygetwindow as gw
                windows = gw.getWindowsWithTitle(self.window_var.get())
                if windows:
                    game_window = windows[0]
                    game_window.activate()
                    print(f"已激活遊戲視窗: {self.window_var.get()}")
                    time.sleep(0.5)  # 等待視窗激活
                else:
                    print("找不到指定的遊戲視窗")
            else:
                print("未設定遊戲視窗")
        except Exception as e:
            print(f"激活遊戲視窗時發生錯誤: {e}")

    def create_status_tab(self):
        """創建執行狀態分頁"""
        # 主框架
        main_frame = self.status_frame
        
        # 標題
        title_label = ttk.Label(main_frame, text="🔍 工具執行狀態", font=("Microsoft YaHei", 20, "bold"))
        title_label.pack(pady=(15, 35))
        
        # 控制按鈕框架
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill="x", pady=(0, 15))
        
        # 清除記錄按鈕
        clear_btn = ttk.Button(control_frame, text="🗑️ 清除記錄", command=self.clear_status_log)
        clear_btn.pack(side="left", padx=(0, 10))
        
        # 自動滾動開關
        self.auto_scroll_var = tk.BooleanVar(value=True)
        auto_scroll_cb = ttk.Checkbutton(control_frame, text="自動滾動到最新訊息", variable=self.auto_scroll_var)
        auto_scroll_cb.pack(side="left", padx=(0, 10))
        
        # 狀態統計標籤
        self.status_count_label = ttk.Label(control_frame, text="共 0 條記錄")
        self.status_count_label.pack(side="right")
        
        # 創建文字顯示區域（帶滾動條）
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill="both", expand=True, pady=(10, 0))
        
        # 文字區域
        self.status_text_widget = tk.Text(
            text_frame, 
            wrap=tk.WORD, 
            font=("Consolas", 10),
            bg="#1e1e1e",
            fg="#ffffff",
            insertbackground="#ffffff",
            selectbackground="#264f78"
        )
        
        # 滾動條
        status_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.status_text_widget.yview)
        self.status_text_widget.configure(yscrollcommand=status_scrollbar.set)
        
        # 配置文字區域的顏色標籤
        self.configure_status_text_tags()
        
        # 佈局
        self.status_text_widget.pack(side="left", fill="both", expand=True)
        status_scrollbar.pack(side="right", fill="y")
        
        # 設置為只讀
        self.status_text_widget.config(state=tk.DISABLED)
        
        # 添加啟動訊息
        self.add_status_message("工具啟動成功", "success")

    def configure_status_text_tags(self):
        """配置狀態文字區域的顏色標籤"""
        # 成功訊息 - 綠色
        self.status_text_widget.tag_config("success", foreground="#4CAF50")
        # 警告訊息 - 黃色
        self.status_text_widget.tag_config("warning", foreground="#FF9800")
        # 錯誤訊息 - 紅色
        self.status_text_widget.tag_config("error", foreground="#F44336")
        # 資訊訊息 - 藍色
        self.status_text_widget.tag_config("info", foreground="#2196F3")
        # 熱鍵訊息 - 紫色
        self.status_text_widget.tag_config("hotkey", foreground="#9C27B0")
        # 監控訊息 - 青色
        self.status_text_widget.tag_config("monitor", foreground="#00BCD4")

    def add_status_message(self, message, msg_type="info"):
        """添加狀態訊息到顯示區域"""
        # 檢查是否重複訊息（簡單的重複檢測）
        if message == self.last_status_message:
            return
        
        self.last_status_message = message
        
        # 獲取當前時間
        current_time = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{current_time}] {message}\n"
        
        # 添加到記錄列表
        self.status_log.append((current_time, message, msg_type))
        
        # 限制記錄數量
        if len(self.status_log) > self.status_log_max_lines:
            self.status_log = self.status_log[-self.status_log_max_lines:]
            # 清空文字區域並重新載入
            if self.status_text_widget:
                self.refresh_status_display()
                return
        
        # 如果文字區域存在，添加新訊息
        if self.status_text_widget:
            self.status_text_widget.config(state=tk.NORMAL)
            self.status_text_widget.insert(tk.END, formatted_message, msg_type)
            self.status_text_widget.config(state=tk.DISABLED)
            
            # 自動滾動到底部
            if self.auto_scroll_var.get():
                self.status_text_widget.see(tk.END)
            
            # 更新統計
            self.update_status_count()

    def refresh_status_display(self):
        """重新刷新狀態顯示區域"""
        if not self.status_text_widget:
            return
            
        self.status_text_widget.config(state=tk.NORMAL)
        self.status_text_widget.delete(1.0, tk.END)
        
        for time_str, message, msg_type in self.status_log:
            formatted_message = f"[{time_str}] {message}\n"
            self.status_text_widget.insert(tk.END, formatted_message, msg_type)
        
        self.status_text_widget.config(state=tk.DISABLED)
        
        if self.auto_scroll_var.get():
            self.status_text_widget.see(tk.END)
        
        self.update_status_count()

    def clear_status_log(self):
        """清除狀態記錄"""
        self.status_log.clear()
        self.last_status_message = ""
        
        if self.status_text_widget:
            self.status_text_widget.config(state=tk.NORMAL)
            self.status_text_widget.delete(1.0, tk.END)
            self.status_text_widget.config(state=tk.DISABLED)
        
        self.update_status_count()
        self.add_status_message("記錄已清除", "info")

    def update_status_count(self):
        """更新狀態記錄數量顯示"""
        if self.status_count_label:
            count = len(self.status_log)
            self.status_count_label.config(text=f"共 {count} 條記錄")

    def create_help_tab(self):
        """創建美觀的使用說明分頁"""
        # 創建滾動區域
        canvas = tk.Canvas(self.help_frame, bg='#f8f9fa')
        scrollbar = ttk.Scrollbar(self.help_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='Card.TFrame')

        # 儲存Canvas引用供滾輪使用
        self.help_canvas = canvas

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set, bg='#f8f9fa')

        # 佈局
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 主標題區域
        header_frame = ttk.Frame(scrollable_frame, style='Card.TFrame')
        header_frame.pack(fill="x", padx=20, pady=(20, 10))

        title_label = ttk.Label(header_frame, text="🎮 Path of Exile 遊戲輔助工具",
                               font=("Microsoft YaHei", 24, "bold"), foreground='#2c3e50')
        title_label.pack(pady=(10, 5))

        subtitle_label = ttk.Label(header_frame, text="完全開源免費版 | MIT License",
                                  font=("Microsoft YaHei", 12), foreground='#7f8c8d')
        subtitle_label.pack(pady=(0, 10))

        # 主要內容區域 - 使用網格佈局充分利用空間
        content_frame = ttk.Frame(scrollable_frame, style='Card.TFrame')
        content_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # 配置網格佈局
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        content_frame.columnconfigure(2, weight=1)
        content_frame.rowconfigure(0, weight=0)  # 快捷鍵區域
        content_frame.rowconfigure(1, weight=1)  # 功能說明區域
        content_frame.rowconfigure(2, weight=0)  # 設定流程區域

        # === 第一行：快捷鍵和基本資訊 ===
        # 快捷鍵卡片
        hotkey_card = self.create_info_card(content_frame, "🔥 全域快捷鍵", [
            ("F3", "一鍵清空背包", "#e74c3c"),
            ("F5", "返回藏身處", "#3498db"),
            ("F6", "一鍵取物", "#2ecc71"),
            ("F9", "全域暫停開關", "#f39c12"),
            ("F10", "血魔監控開關", "#9b59b6"),
            ("F12", "關閉程式", "#95a5a6"),
            ("CTRL+左鍵", "自動連點", "#1abc9c")
        ])
        hotkey_card.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10), pady=(0, 10))

        # 版本資訊卡片
        version_card = ttk.LabelFrame(content_frame, text="📊 版本資訊", padding="15")
        version_card.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10), pady=(0, 10))

        version_info = f"""
� 當前版本：{CURRENT_VERSION}
📅 更新日期：2025年9月
👨‍💻 開發者：Sid
📧 聯絡方式：GitHub Issues

✅ 所有功能完全免費
🔓 無任何使用限制
🛡️ 開源透明可信賴
        """
        ttk.Label(version_card, text=version_info, justify="left",
                 font=('Microsoft YaHei', 10)).pack(anchor="w")

        # 快速開始卡片
        quickstart_card = ttk.LabelFrame(content_frame, text="🚀 快速開始", padding="15")
        quickstart_card.grid(row=0, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 0), pady=(0, 10))

        quickstart_text = """
⚡ 3分鐘快速設定：

1️ 選擇遊戲視窗
2️ 框選血量條區域
3️ 設定觸發條件
4️ 啟動監控系統

�🎮 開始享受自動化遊戲體驗！
        """
        ttk.Label(quickstart_card, text=quickstart_text, justify="left",
                 font=('Microsoft YaHei', 10)).pack(anchor="w")

        # === 第二行：功能詳細說明 ===
        # 核心功能卡片
        features_card = ttk.LabelFrame(content_frame, text="⭐ 核心功能詳解", padding="15")
        features_card.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10), pady=(0, 10))

        # 使用子框架來組織功能說明
        features_container = ttk.Frame(features_card)
        features_container.pack(fill="both", expand=True)

        # 左側功能
        left_features = ttk.Frame(features_container)
        left_features.pack(side="left", fill="both", expand=True, padx=(0, 15))

        ttk.Label(left_features, text="❤️ 血魔監控系統", font=('Microsoft YaHei', 12, 'bold'),
                 foreground='#e74c3c').pack(anchor="w", pady=(0, 5))
        ttk.Label(left_features, text="• 即時監控血量和魔力條\n• 自訂觸發百分比閾值\n• 自動執行設定快捷鍵\n• 支援冷卻時間控制",
                 font=('Microsoft YaHei', 9), justify="left").pack(anchor="w", pady=(0, 15))

        ttk.Label(left_features, text="🎒 智慧清包系統", font=('Microsoft YaHei', 12, 'bold'),
                 foreground='#3498db').pack(anchor="w", pady=(0, 5))
        ttk.Label(left_features, text="• 一鍵清空背包所有物品\n• 記錄背包UI基準顏色\n• 右鍵2秒可緊急中斷\n• 支援任意背包大小",
                 font=('Microsoft YaHei', 9), justify="left").pack(anchor="w", pady=(0, 15))

        # 右側功能
        right_features = ttk.Frame(features_container)
        right_features.pack(side="right", fill="both", expand=True, padx=(15, 0))

        ttk.Label(right_features, text="⚡ 技能連段系統", font=('Microsoft YaHei', 12, 'bold'),
                 foreground='#2ecc71').pack(anchor="w", pady=(0, 5))
        ttk.Label(right_features, text="• 設定觸發鍵和技能序列\n• 支援1-5個技能連段\n• 可調節延遲時間\n• 同時啟用多個套組",
                 font=('Microsoft YaHei', 9), justify="left").pack(anchor="w", pady=(0, 15))

        ttk.Label(right_features, text="🎯 自動化工具", font=('Microsoft YaHei', 12, 'bold'),
                 foreground='#9b59b6').pack(anchor="w", pady=(0, 5))
        ttk.Label(right_features, text="• F6一鍵取物（5個座標）\n• CTRL+左鍵自動連點\n• F5快速返回藏身處\n• 全域暫停功能",
                 font=('Microsoft YaHei', 9), justify="left").pack(anchor="w")

        # 設定指南卡片
        setup_card = ttk.LabelFrame(content_frame, text="📋 詳細設定指南", padding="15")
        setup_card.grid(row=1, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 0), pady=(0, 10))

        setup_guide = """
🔧 血魔監控設定：
1. 選擇遊戲視窗
2. 點擊"框選血量條"
3. 拖拽選擇血量條區域
4. 設定觸發條件
5. 啟動監控

📦 清包功能設定：
1. 點擊"框選背包UI"
2. 選擇背包區域
3. 記錄淨空顏色基準
4. 使用F3開始清包

⚙️ 連段系統設定：
1. 選擇觸發鍵
2. 設定技能序列
3. 調整延遲時間
4. 啟用所需套組
        """
        ttk.Label(setup_card, text=setup_guide, justify="left",
                 font=('Microsoft YaHei', 9)).pack(anchor="w")

        # === 第三行：注意事項和開源資訊 ===
        # 注意事項卡片
        notes_card = ttk.LabelFrame(scrollable_frame, text="⚠️ 重要注意事項", padding="15")
        notes_card.pack(fill="x", padx=20, pady=(0, 10))

        notes_text = """
• 確保遊戲視窗處於前台時使用功能效果最佳
• 框選區域時請精確選擇，避免包含干擾元素
• 建議在安全環境下測試設定是否正確
• 技能連段延遲建議設定在100-500毫秒之間
• 所有設定會自動儲存，下次啟動時自動載入
• 本工具完全開源免費，如遇收費版本請勿購買
• 使用過程中如有問題，請前往GitHub提交Issue
        """
        ttk.Label(notes_card, text=notes_text, justify="left",
                 font=('Microsoft YaHei', 10)).pack(anchor="w")

        # 開源資訊卡片
        opensource_card = ttk.LabelFrame(scrollable_frame, text="🌟 開源專案資訊", padding="15")
        opensource_card.pack(fill="x", padx=20, pady=(0, 20))

        # 開源資訊使用網格佈局
        opensource_container = ttk.Frame(opensource_card)
        opensource_container.pack(fill="x")

        opensource_container.columnconfigure(0, weight=1)
        opensource_container.columnconfigure(1, weight=1)

        # 左側：專案資訊
        left_info = ttk.Frame(opensource_container)
        left_info.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 20))

        ttk.Label(left_info, text="📂 GitHub 倉庫：", font=('Microsoft YaHei', 11, 'bold')).pack(anchor="w")
        ttk.Label(left_info, text="https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor",
                 font=('Consolas', 9), foreground='#3498db').pack(anchor="w", pady=(0, 10))

        ttk.Label(left_info, text="📄 授權協議：", font=('Microsoft YaHei', 11, 'bold')).pack(anchor="w")
        ttk.Label(left_info, text="MIT License - 完全免費開源", font=('Microsoft YaHei', 10)).pack(anchor="w", pady=(0, 10))

        # 右側：功能狀態
        right_info = ttk.Frame(opensource_container)
        right_info.grid(row=0, column=1, sticky=(tk.W, tk.E))

        ttk.Label(right_info, text="✅ 免費功能清單：", font=('Microsoft YaHei', 11, 'bold')).pack(anchor="w", pady=(0, 5))

        free_features = [
            "• F3 一鍵清包",
            "• F5 返回藏身處",
            "• F6 一鍵取物",
            "• F9 全域暫停",
            "• F10 血魔監控",
            "• 技能連段系統",
            "• 自動連點功能"
        ]

        for feature in free_features:
            ttk.Label(right_info, text=feature, font=('Microsoft YaHei', 9)).pack(anchor="w")

    def create_info_card(self, parent, title, items):
        """創建資訊卡片"""
        card = ttk.LabelFrame(parent, text=title, padding="15")

        for item in items:
            # 創建項目框架
            item_frame = ttk.Frame(card)
            item_frame.pack(fill="x", pady=(0, 8))

            # 快捷鍵標籤
            key_label = ttk.Label(item_frame, text=f" {item[0]} ", font=('Consolas', 10, 'bold'),
                                 background=item[2], foreground='white', padding=(5, 2))
            key_label.pack(side="left")

            # 說明文字
            desc_label = ttk.Label(item_frame, text=f" {item[1]}", font=('Microsoft YaHei', 10))
            desc_label.pack(side="left", padx=(10, 0))

        return card

    def setup_global_scroll(self):
        """設置全域滾輪支持，讓整個視窗都能使用滾輪"""
        # 為主視窗綁定滾輪事件
        self.root.bind("<MouseWheel>", self.handle_mousewheel)
        
        # 為notebook綁定分頁切換事件，確保滾輪在分頁切換後仍能工作
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # 儲存可滾動組件的引用
        self.scrollable_widgets = {}
        if hasattr(self, 'settings_tree'):
            self.scrollable_widgets['settings_tree'] = self.settings_tree

    def on_tab_changed(self, event):
        """分頁切換時的處理"""
        # 確保滾輪事件仍然綁定
        self.root.focus_set()  # 確保主視窗有焦點

    def handle_mousewheel(self, event):
        """處理滾輪事件，轉發給當前可見的可滾動組件"""
        # 獲取當前選中的分頁
        current_tab = self.notebook.select()
        tab_text = self.notebook.tab(current_tab, "text")
        
        # 根據不同的分頁處理滾輪事件
        if tab_text == "血量監控":
            # 血量監控分頁：滾動Treeview
            self.settings_tree.yview_scroll(int(-1*(event.delta/120)), "units")
            return "break"
            
        elif tab_text == "使用說明":
            # 使用說明分頁：滾動Canvas
            if hasattr(self, 'help_canvas') and self.help_canvas:
                self.help_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                return "break"
                
        return "break"  # 阻止事件繼續傳播

    def auto_load_preview(self):
        """在程式啟動時自動載入預覽圖片"""
        # 檢查是否有已儲存的區域設定
        if self.config.get('region') and self.config.get('window_title'):
            try:
                # 檢查遊戲視窗是否存在
                windows = gw.getWindowsWithTitle(self.config['window_title'])
                if windows:
                    # 設定視窗選擇
                    self.window_var.set(self.config['window_title'])
                    
                    # 嘗試載入預覽圖片
                    health_loaded = self.load_preview_image()
                    mana_loaded = self.load_mana_preview_image()
                    
                    if health_loaded or mana_loaded:
                        print(f"已自動載入設定：視窗={self.config['window_title']}")
                    else:
                        print("設定已載入，但預覽圖片需要更新")
                        
                else:
                    print(f"遊戲視窗 '{self.config['window_title']}' 未找到")
                    # 即使視窗不存在，也設定視窗名稱，讓用戶知道之前選擇的是什麼
                    self.window_var.set(self.config['window_title'])
                    # 更新預覽標籤顯示合適的提示
                    if hasattr(self, 'preview_label') and self.config.get('region'):
                        self.preview_label.config(text=f"遊戲視窗未找到:\n{self.config['window_title']}\n請重新整理視窗列表", image="")
                    if hasattr(self, 'mana_preview_label') and self.config.get('mana_region'):
                        self.mana_preview_label.config(text=f"遊戲視窗未找到:\n{self.config['window_title']}\n請重新整理視窗列表", image="")
            except Exception as e:
                print(f"自動載入預覽失敗: {e}")
                if hasattr(self, 'preview_label'):
                    self.preview_label.config(text="載入設定失敗\n請重新設定", image="")
                if hasattr(self, 'mana_preview_label'):
                    self.mana_preview_label.config(text="載入設定失敗\n請重新設定", image="")
        else:
            # 沒有設定時顯示預設提示
            if hasattr(self, 'preview_label'):
                self.preview_label.config(text="請先框選血量條區域", image="")
            if hasattr(self, 'mana_preview_label'):
                self.mana_preview_label.config(text="請先框選魔力條區域", image="")
            print("沒有找到已儲存的設定")

    def refresh_windows(self):
        windows = [w.title for w in gw.getAllWindows() if w.title]
        if hasattr(self, 'window_combo'):
            self.window_combo['values'] = windows
        else:
            print("警告: window_combo 不存在")

    def start_selection(self):
        if not self.window_var.get():
            messagebox.showerror("錯誤", "請先選擇遊戲視窗")
            return

        # 如果當前正在監控，自動停止監控
        if self.monitoring:
            self.stop_monitoring()
            messagebox.showinfo("提示", "已自動停止監控以進行框選操作")

        try:
            window = gw.getWindowsWithTitle(self.window_var.get())[0]
            window.activate()
            time.sleep(0.1)  # 等待視窗激活

            self.selection_active = True

            # 框選時降低透明度
            self.root.attributes("-alpha", 0.6)  # 降低透明度
            self.root.lift()

            # 創建覆蓋遊戲視窗的選擇視窗（子視窗 - 最高層級）
            self.selection_window = self.create_child_window("", f"{window.width}x{window.height}")
            self.selection_window.geometry(f"+{window.left}+{window.top}")
            self.selection_window.attributes("-alpha", 0.3)
            self.selection_window.overrideredirect(True)  # 移除視窗邊框
            self.selection_window.configure(bg='gray')

            canvas = tk.Canvas(self.selection_window, bg='gray', highlightthickness=0)
            canvas.pack(fill=tk.BOTH, expand=True)

            canvas.bind("<ButtonPress-1>", self.on_selection_start)
            canvas.bind("<B1-Motion>", self.on_selection_drag)
            canvas.bind("<ButtonRelease-1>", self.on_selection_end)

            # 綁定右鍵取消
            canvas.bind("<Button-3>", self.cancel_selection)
            
            # 設置全局ESC監聽（不依賴窗口焦點）
            self.setup_global_esc_listener()

            # 繪製提示文字
            canvas.create_text(window.width//2, window.height//2,
                             text="請拖曳框選血量條區域\n右鍵或按ESC取消",
                             fill="white", font=("Arial", 14, "bold"),
                             anchor="center")

        except Exception as e:
            messagebox.showerror("錯誤", f"無法啟動框選: {str(e)}")

    def on_selection_start(self, event):
        self.selection_start = (event.x, event.y)

    def on_selection_drag(self, event):
        if self.selection_start:
            self.selection_end = (event.x, event.y)

            # 清除之前的繪圖
            canvas = self.selection_window.winfo_children()[0]
            canvas.delete("selection")

            # 繪製選擇矩形
            x1, y1 = self.selection_start
            x2, y2 = self.selection_end
            canvas.create_rectangle(x1, y1, x2, y2, outline="red", width=2, tags="selection")

            self.selection_window.update()

    def on_selection_end(self, event):
        if self.selection_start and self.selection_end:
            # 座標已經是相對於遊戲視窗的
            x1, y1 = self.selection_start
            x2, y2 = self.selection_end

            # 確保座標正確（左上到右下）
            left = min(x1, x2)
            top = min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)

            self.selected_region = (left, top, width, height)

            # 儲存區域
            self.config['region'] = self.selected_region
            self.region_label.config(text=self.get_region_text(), background="lightgreen")

            # 擷取預覽圖
            self.capture_preview()

        self.selection_active = False
        self.selection_window.destroy()

        # 重新激活主視窗並恢復正常狀態
        self.root.attributes("-alpha", 1.0)  # 恢復完全不透明
        self.manage_window_hierarchy(self.root, "MAIN")  # 恢復主視窗層級
        self.root.lift()
        self.root.focus_force()
        self.root.focus_force()

    def cancel_selection(self, event):
        self.selection_active = False
        self.selection_start = None
        self.selection_end = None
        
        # 移除全局ESC監聽
        self.remove_global_esc_listener()
        
        if hasattr(self, 'selection_window') and self.selection_window:
            self.selection_window.destroy()
        
        # 重新激活主視窗並恢復正常狀態
        self.root.attributes("-alpha", 1.0)  # 恢復完全不透明
        self.manage_window_hierarchy(self.root, "MAIN")  # 恢復主視窗層級
        self.root.lift()
        self.root.focus_force()

    def setup_global_esc_listener(self):
        """設置全局ESC鍵監聽，用於框選取消"""
        try:
            # 移除舊的監聽器（如果存在）
            self.remove_global_esc_listener()
            
            # 添加新的ESC監聽器
            keyboard.add_hotkey('esc', self.global_esc_handler, suppress=False)
            self.global_esc_active = True
        except Exception as e:
            print(f"設置全局ESC監聽失敗: {e}")

    def remove_global_esc_listener(self):
        """移除全局ESC鍵監聽"""
        try:
            if hasattr(self, 'global_esc_active') and self.global_esc_active:
                keyboard.remove_hotkey('esc')
                self.global_esc_active = False
        except Exception as e:
            print(f"移除全局ESC監聽失敗: {e}")

    def global_esc_handler(self):
        """全局ESC鍵處理函數"""
        try:
            if hasattr(self, 'selection_active') and self.selection_active:
                # 使用tkinter的after方法來確保在主線程中執行
                self.root.after(0, lambda: self.cancel_selection(None))
        except Exception as e:
            print(f"全局ESC處理失敗: {e}")

    def setup_global_esc_listener_for_inventory(self):
        """設置背包UI選擇的全局ESC鍵監聽"""
        try:
            if not hasattr(self, 'global_esc_active_inventory') or not self.global_esc_active_inventory:
                keyboard.add_hotkey('esc', self.global_esc_handler_for_inventory)
                self.global_esc_active_inventory = True
                print("已設置背包UI選擇的全局ESC監聽")
        except Exception as e:
            print(f"設置背包UI選擇的全局ESC監聽失敗: {e}")

    def remove_global_esc_listener_for_inventory(self):
        """移除背包UI選擇的全局ESC鍵監聽"""
        try:
            if hasattr(self, 'global_esc_active_inventory') and self.global_esc_active_inventory:
                keyboard.remove_hotkey('esc')
                self.global_esc_active_inventory = False
                print("已移除背包UI選擇的全局ESC監聽")
        except Exception as e:
            print(f"移除背包UI選擇的全局ESC監聽失敗: {e}")

    def global_esc_handler_for_inventory(self):
        """背包UI選擇的全局ESC鍵處理函數"""
        try:
            if hasattr(self, 'inventory_ui_selection_active') and self.inventory_ui_selection_active:
                # 使用tkinter的after方法來確保在主線程中執行
                self.root.after(0, lambda: self.cancel_inventory_ui_selection(None))
                print("檢測到ESC鍵，取消背包UI選擇")
        except Exception as e:
            print(f"背包UI選擇的全局ESC處理失敗: {e}")

    def setup_global_esc_listener_for_interface(self):
        """設置介面UI選擇的全局ESC鍵監聽"""
        try:
            if not hasattr(self, 'global_esc_active_interface') or not self.global_esc_active_interface:
                keyboard.add_hotkey('esc', self.global_esc_handler_for_interface)
                self.global_esc_active_interface = True
                print("已設置介面UI選擇的全局ESC監聽")
        except Exception as e:
            print(f"設置介面UI選擇的全局ESC監聽失敗: {e}")

    def remove_global_esc_listener_for_interface(self):
        """移除介面UI選擇的全局ESC鍵監聽"""
        try:
            if hasattr(self, 'global_esc_active_interface') and self.global_esc_active_interface:
                keyboard.remove_hotkey('esc')
                self.global_esc_active_interface = False
                print("已移除介面UI選擇的全局ESC監聽")
        except Exception as e:
            print(f"移除介面UI選擇的全局ESC監聽失敗: {e}")

    def global_esc_handler_for_interface(self):
        """介面UI選擇的全局ESC鍵處理函數"""
        try:
            if hasattr(self, 'interface_ui_selection_active') and self.interface_ui_selection_active:
                # 使用tkinter的after方法來確保在主線程中執行
                self.root.after(0, lambda: self.cancel_interface_ui_selection(None))
                print("檢測到ESC鍵，取消介面UI選擇")
        except Exception as e:
            print(f"介面UI選擇的全局ESC處理失敗: {e}")

    def start_mana_selection(self):
        if not self.window_var.get():
            messagebox.showerror("錯誤", "請先選擇遊戲視窗")
            return

        # 如果當前正在監控，自動停止監控
        if self.monitoring:
            self.stop_monitoring()
            messagebox.showinfo("提示", "已自動停止監控以進行框選操作")

        try:
            window = gw.getWindowsWithTitle(self.window_var.get())[0]
            window.activate()
            time.sleep(0.1)  # 等待視窗激活

            self.selection_active = True

            # 框選時降低透明度
            self.root.attributes("-alpha", 0.6)  # 降低透明度
            self.root.lift()

            # 創建覆蓋遊戲視窗的選擇視窗（子視窗 - 最高層級）
            self.selection_window = self.create_child_window("", f"{window.width}x{window.height}")
            self.selection_window.geometry(f"+{window.left}+{window.top}")
            self.selection_window.attributes("-alpha", 0.3)
            self.selection_window.overrideredirect(True)  # 移除視窗邊框
            self.selection_window.configure(bg='blue')

            canvas = tk.Canvas(self.selection_window, bg='blue', highlightthickness=0)
            canvas.pack(fill=tk.BOTH, expand=True)

            canvas.bind("<ButtonPress-1>", self.on_mana_selection_start)
            canvas.bind("<B1-Motion>", self.on_mana_selection_drag)
            canvas.bind("<ButtonRelease-1>", self.on_mana_selection_end)

            # 綁定右鍵取消
            canvas.bind("<Button-3>", self.cancel_selection)
            
            # 綁定ESC鍵取消（窗口級別）
            self.selection_window.bind("<Escape>", self.cancel_selection)
            self.selection_window.focus_set()  # 確保selection_window能接收鍵盤事件
            
            # 設置全局ESC監聽（不依賴窗口焦點）
            self.setup_global_esc_listener()

            # 繪製提示文字
            canvas.create_text(window.width//2, window.height//2,
                             text="請拖曳框選魔力條區域\n右鍵或按ESC取消",
                             fill="white", font=("Arial", 14, "bold"),
                             anchor="center")

        except Exception as e:
            messagebox.showerror("錯誤", f"無法啟動魔力框選: {str(e)}")

    def on_mana_selection_start(self, event):
        self.selection_start = (event.x, event.y)

    def on_mana_selection_drag(self, event):
        if self.selection_start:
            self.selection_end = (event.x, event.y)

            # 清除之前的繪圖
            canvas = self.selection_window.winfo_children()[0]
            canvas.delete("selection")

            # 繪製選擇矩形
            x1, y1 = self.selection_start
            x2, y2 = self.selection_end
            canvas.create_rectangle(x1, y1, x2, y2, outline="cyan", width=2, tags="selection")

            self.selection_window.update()

    def on_mana_selection_end(self, event):
        if self.selection_start and self.selection_end:
            # 座標已經是相對於遊戲視窗的
            x1, y1 = self.selection_start
            x2, y2 = self.selection_end

            # 確保座標正確（左上到右下）
            left = min(x1, x2)
            top = min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)

            self.selected_mana_region = (left, top, width, height)

            # 儲存區域
            self.config['mana_region'] = self.selected_mana_region
            self.mana_region_label.config(text=self.get_mana_region_text(), background="lightgreen")

            # 擷取魔力預覽圖
            self.capture_mana_preview()

        self.selection_active = False
        self.selection_window.destroy()

        # 重新激活主視窗並恢復正常狀態
        self.root.attributes("-alpha", 1.0)  # 恢復完全不透明
        self.manage_window_hierarchy(self.root, "MAIN")  # 恢復主視窗層級
        self.root.lift()
        self.root.focus_force()
        self.root.focus_force()

    def capture_mana_preview(self):
        if not self.selected_mana_region:
            return

        try:
            # 獲取遊戲視窗位置
            window = gw.getWindowsWithTitle(self.window_var.get())[0]
            x, y, w, h = self.selected_mana_region

            # 計算絕對螢幕座標
            abs_x = window.left + x
            abs_y = window.top + y

            with mss.mss() as sct:
                monitor = {"top": abs_y, "left": abs_x, "width": w, "height": h}
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                img.thumbnail((200, 200))

                # 儲存魔力預覽圖片
                mana_preview_path = os.path.join(get_app_dir(), "screenshots", "health_monitor_mana_preview.png")
                os.makedirs(os.path.dirname(mana_preview_path), exist_ok=True)
                img.save(mana_preview_path)

                # 繪製刻度線
                self.draw_scale_lines(img)

                # 等比例縮放圖片到合適尺寸
                resized_img = self.resize_and_center_image(img, self.preview_size)
                self.mana_preview_image = ImageTk.PhotoImage(resized_img)
                if hasattr(self, 'mana_preview_label'):
                    self.mana_preview_label.config(image=self.mana_preview_image, text="")
                print("魔力預覽更新成功")
        except Exception as e:
            print(f"魔力預覽擷取失敗: {e}")
            if hasattr(self, 'mana_preview_label'):
                self.mana_preview_label.config(text=f"魔力預覽擷取失敗\n{str(e)}", image="")

    def capture_preview(self):
        if not self.selected_region:
            return

        try:
            # 獲取遊戲視窗位置
            window = gw.getWindowsWithTitle(self.window_var.get())[0]
            x, y, w, h = self.selected_region

            # 計算絕對螢幕座標
            abs_x = window.left + x
            abs_y = window.top + y

            with mss.mss() as sct:
                monitor = {"top": abs_y, "left": abs_x, "width": w, "height": h}
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                img.thumbnail((200, 200))

                # 儲存預覽圖片到檔案
                preview_path = os.path.join(get_app_dir(), "screenshots", "health_monitor_preview.png")
                os.makedirs(os.path.dirname(preview_path), exist_ok=True)
                img.save(preview_path)

                # 繪製刻度線
                self.draw_scale_lines(img)

                # 等比例縮放圖片到合適尺寸
                resized_img = self.resize_and_center_image(img, self.preview_size)
                self.preview_image = ImageTk.PhotoImage(resized_img)
                if hasattr(self, 'preview_label'):
                    self.preview_label.config(image=self.preview_image, text="")
                print("血量預覽更新成功")
        except Exception as e:
            print(f"預覽擷取失敗: {e}")
            if hasattr(self, 'preview_label'):
                self.preview_label.config(text=f"預覽擷取失敗\n{str(e)}", image="")

    def load_preview_image(self):
        """載入儲存的預覽圖片"""
        preview_path = os.path.join(get_app_dir(), "screenshots", "health_monitor_preview.png")
        if os.path.exists(preview_path) and self.selected_region:
            try:
                img = Image.open(preview_path)
                # 在預覽圖上繪製10等分刻度線
                self.draw_scale_lines(img)
                # 等比例縮放圖片到合適尺寸
                resized_img = self.resize_and_center_image(img, self.preview_size)
                self.preview_image = ImageTk.PhotoImage(resized_img)
                if hasattr(self, 'preview_label'):
                    self.preview_label.config(image=self.preview_image, text="")
                print("預覽圖片載入成功")
                return True
            except Exception as e:
                print(f"載入預覽圖片失敗: {e}")
                if hasattr(self, 'preview_label'):
                    self.preview_label.config(text="載入預覽失敗", image="")
                return False
        else:
            # 如果沒有預覽檔案但有區域設定，嘗試即時擷取
            if self.selected_region and hasattr(self, 'preview_label'):
                # 嘗試即時擷取預覽
                try:
                    self.capture_preview()
                    return True
                except:
                    self.preview_label.config(text="血量區域已設定\n等待擷取預覽", image="")
                    return False
            elif hasattr(self, 'preview_label'):
                self.preview_label.config(text="請先框選血量條區域", image="")
                return False

    def load_mana_preview_image(self):
        """載入儲存的魔力預覽圖片"""
        mana_preview_path = os.path.join(get_app_dir(), "screenshots", "health_monitor_mana_preview.png")
        if os.path.exists(mana_preview_path) and self.selected_mana_region:
            try:
                img = Image.open(mana_preview_path)
                # 在預覽圖上繪製10等分刻度線
                self.draw_scale_lines(img)
                # 等比例縮放圖片到合適尺寸
                resized_img = self.resize_and_center_image(img, self.preview_size)
                self.mana_preview_image = ImageTk.PhotoImage(resized_img)
                if hasattr(self, 'mana_preview_label'):
                    self.mana_preview_label.config(image=self.mana_preview_image, text="")
                print("魔力預覽圖片載入成功")
                return True
            except Exception as e:
                print(f"載入魔力預覽圖片失敗: {e}")
                if hasattr(self, 'mana_preview_label'):
                    self.mana_preview_label.config(text="載入魔力預覽失敗", image="")
                return False
        else:
            # 如果沒有預覽檔案但有區域設定，嘗試即時擷取
            if self.selected_mana_region and hasattr(self, 'mana_preview_label'):
                # 嘗試即時擷取預覽
                try:
                    self.capture_mana_preview()
                    return True
                except:
                    self.mana_preview_label.config(text="魔力區域已設定\n等待擷取預覽", image="")
                    return False
            elif hasattr(self, 'mana_preview_label'):
                self.mana_preview_label.config(text="請先框選魔力條區域", image="")
                return False

    def draw_scale_lines(self, img):
        """在預覽圖上繪製10等分刻度線"""
        # 正確處理 PIL Image 對象的寬度和高度
        if hasattr(img, 'shape'):  # numpy array
            width, height = img.shape[1], img.shape[0]
        else:  # PIL Image
            width, height = img.width, img.height

        # 創建繪圖物件
        draw = ImageDraw.Draw(img)

        # 繪製水平刻度線（10等分）
        for i in range(1, 10):
            y = int(height * i / 10)
            # 繪製刻度線
            draw.line([(0, y), (width, y)], fill=(255, 0, 0), width=1)
            # 繪製百分比標籤
            percent = 100 - (i * 10)
            draw.text((5, y - 15), f"{percent}%", fill=(255, 0, 0), font=None)

    def get_region_text(self):
        if self.config.get('region'):
            x, y, w, h = self.config['region']
            return f"x={x}, y={y}, w={w}, h={h}"
        return "未設定"

    def get_mana_region_text(self):
        if self.config.get('mana_region'):
            x, y, w, h = self.config['mana_region']
            return f"x={x}, y={y}, w={w}, h={h}"
        return "未設定"

    def get_interface_ui_region_text(self):
        if self.interface_ui_region:
            x, y, w, h = self.interface_ui_region['x'], self.interface_ui_region['y'], self.interface_ui_region['width'], self.interface_ui_region['height']
            return f"x={x}, y={y}, w={w}, h={h}"
        return "尚未記錄"

    def add_setting(self):
        try:
            percent = int(self.percent_var.get())
            key = self.key_var.get().strip()
            cooldown = int(self.cooldown_var.get())

            if not (0 <= percent <= 100):
                raise ValueError("百分比必須在0-100之間")

            if not key:
                raise ValueError("請輸入快捷鍵")

            if cooldown < 0:
                raise ValueError("冷卻時間不能為負數")

            # 驗證鍵序列
            if not self.validate_key_sequence(key):
                raise ValueError("無效的快捷鍵格式。支援格式：單鍵（如 '5'）或多鍵序列（如 '1-5-esc'）")

            # 新增到設定
            if 'settings' not in self.config:
                self.config['settings'] = []
            self.config['settings'].append({'percent': percent, 'key': key, 'cooldown': cooldown})

            # 更新樹狀圖
            self.settings_tree.insert("", tk.END, values=(percent, key, cooldown))

            # 清空輸入
            self.percent_var.set("50")
            self.key_var.set("5")
            self.cooldown_var.set("1000")

        except ValueError as e:
            messagebox.showerror("錯誤", str(e))

    def add_setting_new(self):
        try:
            setting_type = self.type_var.get()
            percent = int(self.percent_var.get())
            key = self.key_var.get().strip()
            cooldown = int(self.cooldown_var.get())

            if not (0 <= percent <= 100):
                raise ValueError("百分比必須在0-100之間")

            if not key:
                raise ValueError("請輸入快捷鍵")

            if cooldown < 0:
                raise ValueError("冷卻時間不能為負數")

            # 驗證鍵序列
            if not self.validate_key_sequence(key):
                raise ValueError("無效的快捷鍵格式。支援格式：單鍵（如 '5'）或多鍵序列（如 '1-5-esc'）")

            # 新增到設定
            if 'settings' not in self.config:
                self.config['settings'] = []
            self.config['settings'].append({
                'type': setting_type,
                'percent': percent, 
                'key': key, 
                'cooldown': cooldown
            })

            # 更新樹狀圖
            type_display = "血量" if setting_type == "health" else "魔力"
            self.settings_tree.insert("", tk.END, values=(type_display, percent, key, cooldown))

            # 清空輸入
            self.on_type_changed()  # 重置為預設值

        except ValueError as e:
            messagebox.showerror("輸入錯誤", str(e))
        except Exception as e:
            messagebox.showerror("錯誤", f"新增設定失敗: {str(e)}")

    def validate_key_sequence(self, key_sequence):
        """驗證鍵序列格式"""
        if not key_sequence:
            return False

        # 解析鍵序列
        keys = [key.strip() for key in key_sequence.split('-')]

        # 檢查每個鍵是否有效
        valid_keys = [
            '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
            'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
            'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
            'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f12',
            'esc', 'escape', 'enter', 'return', 'space', 'tab', 'backspace',
            'delete', 'home', 'end', 'pageup', 'pagedown',
            'up', 'down', 'left', 'right', 'uparrow', 'downarrow', 'leftarrow', 'rightarrow',
            'ctrl', 'alt', 'shift', 'win', 'cmd', 'windows'
        ]

        for key in keys:
            if key.lower() not in valid_keys:
                return False

        return True

    def remove_setting(self):
        selected_item = self.settings_tree.selection()
        if not selected_item:
            messagebox.showwarning("警告", "請先選取要移除的設定")
            return

        # 確認刪除
        if not messagebox.askyesno("確認", "確定要移除選取的設定嗎？"):
            return

        # 從樹狀圖中移除
        item_values = self.settings_tree.item(selected_item[0], 'values')
        self.settings_tree.delete(selected_item[0])

        # 從設定中移除
        if 'settings' in self.config:
            type_map = {"血量": "health", "魔力": "mana"}
            setting_type = type_map.get(item_values[0], "health")
            self.config['settings'] = [
                setting for setting in self.config['settings']
                if not (setting.get('type', 'health') == setting_type and 
                       setting['percent'] == int(item_values[1]) and 
                       setting['key'] == item_values[2])
            ]

    def load_settings_to_tree(self):
        for item in self.settings_tree.get_children():
            self.settings_tree.delete(item)

        for setting in self.config.get('settings', []):
            cooldown = setting.get('cooldown', 1000)  # 預設1000ms冷卻時間
            setting_type = setting.get('type', 'health')  # 預設為血量
            type_display = "血量" if setting_type == "health" else "魔力"
            self.settings_tree.insert("", tk.END, values=(type_display, setting['percent'], setting['key'], cooldown))

    def start_monitoring(self):
        if not self.window_var.get():
            messagebox.showerror("錯誤", "請先選擇遊戲視窗")
            return

        if not self.config.get('region'):
            messagebox.showerror("錯誤", "請先框選血量條區域")
            return

        if not self.config.get('settings'):
            messagebox.showerror("錯誤", "請至少設定一個觸發條件")
            return

        # 激活遊戲視窗
        try:
            windows = gw.getWindowsWithTitle(self.window_var.get())
            if windows:
                window = windows[0]
                window.activate()
                time.sleep(0.1)  # 給一點時間讓視窗激活
        except Exception as e:
            print(f"激活遊戲視窗失敗: {e}")

        self.monitoring = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        # 添加狀態訊息
        self.add_status_message("血魔監控已啟動", "success")

        # 開始監控時設置為非干擾模式：降低不透明度但保持可見
        self.root.attributes("-alpha", 0.8)  # 輕微透明
        self.manage_window_hierarchy(self.root, "MAIN")  # 設置主視窗層級

        self.monitor_thread = threading.Thread(target=self.monitor_health)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_monitoring(self):
        self.monitoring = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

        # 添加狀態訊息
        self.add_status_message("血魔監控已停止", "info")

        # 停止監控時恢復正常狀態
        self.root.attributes("-alpha", 1.0)  # 恢復完全不透明
        self.manage_window_hierarchy(self.root, "MAIN")  # 恢復主視窗層級

    def restart_monitoring_silently(self):
        """靜默重新啟動血魔監控（用於全域暫停恢復）"""
        if self.monitoring:
            return  # 已經在監控中
        
        if not self.window_var.get():
            raise Exception("未選擇遊戲視窗")
        
        if not self.config.get('region'):
            raise Exception("未設定血量條區域")
        
        if not self.config.get('settings'):
            raise Exception("未設定觸發條件")
        
        # 激活遊戲視窗（靜默）
        try:
            windows = gw.getWindowsWithTitle(self.window_var.get())
            if windows:
                window = windows[0]
                window.activate()
                time.sleep(0.1)
        except Exception as e:
            print(f"激活遊戲視窗失敗: {e}")
        
        self.monitoring = True
        
        # 更新UI（如果元件存在）
        try:
            if hasattr(self, 'start_btn') and self.start_btn:
                self.start_btn.config(state=tk.DISABLED)
            if hasattr(self, 'stop_btn') and self.stop_btn:
                self.stop_btn.config(state=tk.NORMAL)
        except:
            pass  # UI 更新失敗不影響功能
        
        # 開始監控時設置為非干擾模式
        self.root.attributes("-alpha", 0.8)
        self.manage_window_hierarchy(self.root, "MAIN")
        
        self.monitor_thread = threading.Thread(target=self.monitor_health)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def monitor_health(self):
        with mss.mss() as sct:
            while self.monitoring:
                try:
                    # 獲取遊戲視窗位置
                    windows = gw.getWindowsWithTitle(self.window_var.get())
                    if not windows:
                        self.update_status("--", "--", "視窗未找到", "")
                        self.add_status_message("遊戲視窗已關閉或找不到", "warning")
                        time.sleep(1)
                        continue

                    window = windows[0]
                    if window.isMinimized:
                        self.update_status("--", "--", "視窗最小化", "")
                        self.add_status_message("遊戲視窗已最小化，暫停監控", "warning")
                        time.sleep(1)
                        continue

                    # 檢查遊戲視窗是否在前台（處於焦點）
                    if not window.isActive:
                        self.update_status("--", "--", "等待遊戲視窗激活", "")
                        self.add_status_message("遊戲視窗失去焦點，暫停監控", "warning")
                        # 等待遊戲視窗重新激活，每500ms檢查一次
                        while self.monitoring and not window.isActive:
                            time.sleep(0.5)
                            # 重新獲取視窗狀態（因為視窗可能已經關閉或改變）
                            windows = gw.getWindowsWithTitle(self.window_var.get())
                            if not windows:
                                break
                            window = windows[0]
                            if window.isMinimized:
                                break
                        # 如果監控被停止或視窗不存在，跳出循環
                        if not self.monitoring or not windows or window.isMinimized:
                            continue
                        # 遊戲視窗重新激活，繼續監控
                        print("遊戲視窗已激活，繼續血魔監控")
                        self.add_status_message("遊戲視窗重新獲得焦點，恢復監控", "success")

                    # 計算區域在螢幕上的絕對位置
                    x, y, w, h = self.config['region']
                    abs_x = window.left + x
                    abs_y = window.top + y

                    # 擷取區域
                    monitor = {"top": abs_y, "left": abs_x, "width": w, "height": h}
                    screenshot = sct.grab(monitor)
                    img = np.frombuffer(screenshot.bgra, dtype=np.uint8)
                    img = img.reshape((screenshot.height, screenshot.width, 4))
                    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

                    # 分析血量
                    health_percent = self.analyze_health(img)
                    main_color = self.get_main_color(img)

                    # 分析魔力（如果有設定魔力區域）
                    mana_percent = "--"
                    if self.config.get('mana_region'):
                        try:
                            # 計算魔力區域在螢幕上的絕對位置
                            mx, my, mw, mh = self.config['mana_region']
                            mana_abs_x = window.left + mx
                            mana_abs_y = window.top + my

                            # 擷取魔力區域
                            mana_monitor = {"top": mana_abs_y, "left": mana_abs_x, "width": mw, "height": mh}
                            mana_screenshot = sct.grab(mana_monitor)
                            mana_img = np.frombuffer(mana_screenshot.bgra, dtype=np.uint8)
                            mana_img = mana_img.reshape((mana_screenshot.height, mana_screenshot.width, 4))
                            mana_img = cv2.cvtColor(mana_img, cv2.COLOR_BGRA2BGR)

                            # 分析魔力
                            mana_percent = self.analyze_mana(mana_img)
                            
                            # 動態更新魔力預覽圖片
                            self.update_live_mana_preview(mana_img, mana_percent)
                        except Exception as e:
                            print(f"魔力分析錯誤: {e}")
                            mana_percent = "--"

                    # 更新狀態
                    mana_value = int(mana_percent) if mana_percent != "--" else None
                    self.update_status(f"{health_percent}%", f"{mana_percent}%", main_color, self.check_triggers(health_percent, mana_value))

                    # 動態更新血量預覽圖片
                    self.update_live_preview(img, health_percent)

                    # 觸發相應的動作
                    self.trigger_actions(health_percent, mana_value)

                    # 使用選擇的檢查頻率
                    try:
                        interval_ms = int(self.monitor_interval_var.get())
                        time.sleep(interval_ms / 1000.0)  # 轉換為秒
                    except (ValueError, AttributeError):
                        time.sleep(0.1)  # 預設100ms

                except Exception as e:
                    print(f"監控錯誤: {e}")
                    self.update_status("--", "--", "--", f"錯誤: {str(e)}")
                    time.sleep(1)

    def update_live_preview(self, img, health_percent):
        """動態更新預覽圖片，減少更新頻率以避免閃爍"""
        import time as time_module

        # 檢查預覽是否啟用
        if not self.preview_enabled.get():
            return

        current_time = time_module.time() * 1000  # 轉換為毫秒

        # 獲取用戶設置的更新間隔
        try:
            update_interval = int(self.preview_interval_var.get())
        except ValueError:
            update_interval = 250  # 預設250ms

        # 只在血量變化或達到更新間隔時才更新
        should_update = (
            abs(health_percent - self.last_health_percent) >= 5 or  # 血量變化超過5%
            (current_time - self.last_preview_update) >= update_interval  # 時間間隔
        )

        if not should_update:
            return

        try:
            # 使用tkinter的after方法來非同步更新，避免阻塞
            self.root.after(0, lambda: self._update_preview_image(img, health_percent))

            # 更新追蹤變數
            self.last_preview_update = current_time
            self.last_health_percent = health_percent

        except Exception as e:
            print(f"預覽更新失敗: {e}")

    def _update_preview_image(self, img, health_percent):
        """實際更新預覽圖片的私有方法"""
        try:
            # 創建PIL圖片
            pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

            # 在圖片上繪製當前血量指示器
            self.draw_health_indicator(pil_img, health_percent)

            # 在圖片上繪製刻度線
            self.draw_scale_lines(pil_img)

            # 等比例縮放圖片到合適尺寸
            resized_img = self.resize_and_center_image(pil_img, self.preview_size)

            # 更新預覽圖片
            self.preview_image = ImageTk.PhotoImage(resized_img)
            if hasattr(self, 'preview_label'):
                self.preview_label.config(image=self.preview_image)

        except Exception as e:
            print(f"更新預覽圖片失敗: {e}")

    def resize_and_center_image(self, pil_img, target_size):
        """將圖片等比例縮放到適合預覽標籤的尺寸，讓圖片更大更清楚"""
        # 獲取原始尺寸和目標尺寸
        original_width, original_height = pil_img.size
        target_width, target_height = target_size
        
        # 計算縮放比例，保持長寬比，但確保圖片有合適的大小
        scale_x = target_width / original_width
        scale_y = target_height / original_height
        
        # 使用較大的縮放比例讓圖片更清楚，但不超過目標尺寸
        scale = min(scale_x, scale_y)
        
        # 確保最小縮放比例不會讓圖片太小
        min_scale = 2.0  # 最小2倍放大
        scale = max(scale, min_scale)
        
        # 如果放大後超過目標尺寸，則使用適合的縮放比例
        if scale * original_width > target_width or scale * original_height > target_height:
            scale = min(scale_x, scale_y)
        
        # 計算縮放後的尺寸
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        
        # 縮放圖片，保持高質量
        resized_img = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return resized_img

    def draw_health_indicator(self, img, health_percent):
        """在預覽圖片上繪製當前血量指示器"""
        width, height = img.size

        # 計算血量對應的高度位置
        health_height = int(height * (100 - health_percent) / 100)

        # 繪製血量指示線（紅色粗線）
        draw = ImageDraw.Draw(img)
        draw.line([(0, health_height), (width, health_height)],
                 fill=(255, 0, 0), width=3)

        # 繪製血量百分比文字在指示線下方
        text = f"{health_percent:.1f}%"
        bbox = draw.textbbox((0, 0), text, font=None)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # 計算文字位置：指示線下方5像素，水平居中
        text_x = (width - text_width) // 2
        text_y = health_height + 5

        # 確保文字不會超出圖片邊界
        if text_y + text_height > height:
            text_y = health_height - text_height - 5  # 如果下方空間不夠，放在上方

        # 繪製文字背景（半透明黑色矩形）
        draw.rectangle([text_x - 2, text_y - 2, text_x + text_width + 2, text_y + text_height + 2],
                      fill=(0, 0, 0, 128))

        # 繪製白色文字
        draw.text((text_x, text_y), text, fill=(255, 255, 255), font=None)

        # 添加黑色邊框讓文字更清楚
        draw.text((text_x + 1, text_y), text, fill=(0, 0, 0), font=None)
        draw.text((text_x - 1, text_y), text, fill=(0, 0, 0), font=None)
        draw.text((text_x, text_y + 1), text, fill=(0, 0, 0), font=None)
        draw.text((text_x, text_y - 1), text, fill=(0, 0, 0), font=None)

    def analyze_health(self, img):
        """分析血量條，使用18個等間隔位置檢測以提高精度"""
        height = img.shape[0]
        width = img.shape[1]

        # 定義18個等間隔檢測位置的百分比（從上到下：95%, 90%, 85%, ..., 5%）
        detection_positions = [0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5, 0.45, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1]

        health_count = 0
        debug_info = []

        # 在每個檢測位置附近取樣檢測
        for i, pos_percent in enumerate(detection_positions):
            # 計算檢測位置的Y坐標
            y_center = int(height * (1 - pos_percent))  # 從上往下計算

            # 在檢測位置附近取一個小的區域（垂直5像素，水平全寬）
            sample_height = 5
            y_start = max(0, y_center - sample_height // 2)
            y_end = min(height, y_center + sample_height // 2)

            segment = img[y_start:y_end, :]

            # 檢查是否為血量顏色
            is_health = self.is_health_color(segment)

            debug_info.append(f"檢測點{i+1} ({int(pos_percent*100)}%): Y範圍[{y_start}-{y_end}], 有血量色彩: {is_health}")

            if is_health:
                health_count += 1

        # 改進滿血檢測邏輯
        if health_count >= 16:  # 至少16個檢測點有血量
            # 檢查下半部分區域的整體血量比例
            bottom_half_start = height // 2
            bottom_segment = img[bottom_half_start:height, :]
            bottom_ratio = self.get_health_color_ratio(bottom_segment)

            # 檢查核心區域（30%-70%）
            core_start = int(height * 0.3)
            core_end = int(height * 0.7)
            core_segment = img[core_start:core_end, :]
            core_ratio = self.get_health_color_ratio(core_segment)

            # 多重條件判斷滿血
            is_full_blood = False

            # 條件1：下半部分血量比例很高
            if bottom_ratio > (self.health_threshold * 0.6):
                is_full_blood = True
                debug_info.append(f"滿血檢測1：下半部血量比例 {bottom_ratio:.3f} > 0.6閾值")

            # 條件2：核心區域表現良好且檢測點很多
            elif core_ratio > (self.health_threshold * 0.5) and health_count >= 16:
                is_full_blood = True
                debug_info.append(f"滿血檢測2：核心區域 {core_ratio:.3f} > 0.5閾值，{health_count}個檢測點有血量")

            # 條件3：所有檢測點都有血量
            elif health_count == 18:
                is_full_blood = True
                debug_info.append(f"滿血檢測3：所有18個檢測點都有血量")

            # 應用滿血修正
            if is_full_blood:
                health_count = 18  # 18個檢測點都滿血

        result = (health_count / 18) * 100  # 轉換為百分比

        # 在控制台輸出調試信息
        if health_count >= 6:  # 只在血量較高時輸出調試信息
            print(f"血量分析結果: {result:.1f}%")
            for info in debug_info:
                print(info)

        return result

    def is_health_color(self, segment):
        # 轉換為HSV
        hsv = cv2.cvtColor(segment, cv2.COLOR_BGR2HSV)

        # 紅色範圍 (考慮色環) - 提高飽和度和亮度閾值以排除生命藥劑特效
        # 真實血量：高飽和度(120+)、高亮度(100+)的鮮豔紅色
        # 藥劑特效：低飽和度、低亮度的暗紅色，應被排除
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

    def get_health_color_ratio(self, segment):
        """獲取分段中血量顏色的比例，用於精確判斷"""
        # 轉換為HSV
        hsv = cv2.cvtColor(segment, cv2.COLOR_BGR2HSV)

        # 紅色範圍 (考慮色環) - 使用與is_health_color相同的高品質閾值
        lower_red1 = np.array([0, self.red_saturation_min, self.red_value_min])
        upper_red1 = np.array([self.red_h_range, 255, 255])
        lower_red2 = np.array([170, self.red_saturation_min, self.red_value_min])
        upper_red2 = np.array([180, 255, 255])

        # 綠色範圍 - 同樣提高品質要求
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
        return health_ratio

    def analyze_mana(self, img):
        """分析魔力條，使用18個等間隔位置檢測以提高精度"""
        height = img.shape[0]
        width = img.shape[1]

        # 定義18個等間隔檢測位置的百分比（從上到下：95%, 90%, 85%, ..., 5%）
        detection_positions = [0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5, 0.45, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1]

        mana_count = 0
        debug_info = []

        # 在每個檢測位置附近取樣檢測
        for i, pos_percent in enumerate(detection_positions):
            # 計算檢測位置的Y坐標
            y_center = int(height * (1 - pos_percent))  # 從上往下計算

            # 在檢測位置附近取一個小的區域（垂直5像素，水平全寬）
            sample_height = 5
            y_start = max(0, y_center - sample_height // 2)
            y_end = min(height, y_center + sample_height // 2)

            segment = img[y_start:y_end, :]

            # 檢查是否為魔力顏色
            is_mana = self.is_mana_color(segment)

            debug_info.append(f"魔力檢測點{i+1} ({int(pos_percent*100)}%): Y範圍[{y_start}-{y_end}], 有魔力色彩: {is_mana}")

            if is_mana:
                mana_count += 1

        # 改進滿魔力檢測邏輯
        if mana_count >= 16:  # 至少16個檢測點有魔力
            # 檢查下半部分區域的整體魔力比例
            bottom_half_start = height // 2
            bottom_segment = img[bottom_half_start:height, :]
            bottom_ratio = self.get_mana_color_ratio(bottom_segment)

            # 檢查核心區域（30%-70%）
            core_start = int(height * 0.3)
            core_end = int(height * 0.7)
            core_segment = img[core_start:core_end, :]
            core_ratio = self.get_mana_color_ratio(core_segment)

            # 多重條件判斷滿魔力
            is_full_mana = False

            # 條件1：下半部分魔力比例很高
            if bottom_ratio > 0.4:  # 魔力閾值可能與血量不同
                is_full_mana = True
                debug_info.append(f"滿魔力檢測1：下半部魔力比例 {bottom_ratio:.3f} > 0.4閾值")

            # 條件2：核心區域表現良好且檢測點很多
            elif core_ratio > 0.3 and mana_count >= 16:
                is_full_mana = True
                debug_info.append(f"滿魔力檢測2：核心區域 {core_ratio:.3f} > 0.3閾值，{mana_count}個檢測點有魔力")

            # 條件3：所有檢測點都有魔力
            elif mana_count == 18:
                is_full_mana = True
                debug_info.append(f"滿魔力檢測3：所有18個檢測點都有魔力")

            # 應用滿魔力修正
            if is_full_mana:
                mana_count = 18  # 18個檢測點都滿魔力

        result = (mana_count / 18) * 100  # 轉換為百分比

        # 在控制台輸出調試信息
        if mana_count >= 6:  # 只在魔力較高時輸出調試信息
            print(f"魔力分析結果: {result:.1f}%")
            for info in debug_info:
                print(info)

        return result

    def is_mana_color(self, segment):
        """檢查區段是否為魔力顏色（藍色）"""
        # 轉換為HSV
        hsv = cv2.cvtColor(segment, cv2.COLOR_BGR2HSV)

        # 藍色範圍
        lower_blue = np.array([90, 50, 50])
        upper_blue = np.array([130, 255, 255])

        # 檢查像素比例
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
        blue_pixels = np.count_nonzero(blue_mask)
        total_pixels = segment.shape[0] * segment.shape[1]

        mana_ratio = blue_pixels / total_pixels
        return mana_ratio > 0.3  # 30%以上的像素為魔力顏色

    def get_mana_color_ratio(self, segment):
        """獲取分段中魔力顏色的比例，用於精確判斷"""
        # 轉換為HSV
        hsv = cv2.cvtColor(segment, cv2.COLOR_BGR2HSV)

        # 藍色範圍
        lower_blue = np.array([90, 50, 50])
        upper_blue = np.array([130, 255, 255])

        # 檢查像素比例
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
        blue_pixels = np.count_nonzero(blue_mask)
        total_pixels = segment.shape[0] * segment.shape[1]

        mana_ratio = blue_pixels / total_pixels
        return mana_ratio

    def get_main_color(self, img):
        # 獲取主要顏色
        pixels = img.reshape(-1, 3)
        pixels = np.float32(pixels)

        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        K = 3
        _, labels, centers = cv2.kmeans(pixels, K, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

        # 轉換為RGB
        centers = np.uint8(centers)
        dominant_color = centers[np.argmax(np.bincount(labels.flatten()))]

        return f"RGB({dominant_color[2]}, {dominant_color[1]}, {dominant_color[0]})"

    def check_triggers(self, health_percent, mana_percent=None):
        """檢查當前應該觸發哪個設定（優先顯示最低百分比的設定）"""
        # === 介面UI戰鬥狀態檢查 ===
        # 如果設定了介面UI區域，檢查是否在戰鬥狀態
        if hasattr(self, 'interface_ui_region') and self.interface_ui_region and hasattr(self, 'interface_ui_screenshot') and self.interface_ui_screenshot is not None:
            try:
                # 獲取遊戲視窗
                windows = gw.getWindowsWithTitle(self.window_var.get())
                if windows:
                    game_window = windows[0]
                    # 檢查介面UI是否可見（是否在戰鬥狀態）
                    if not self.is_interface_ui_visible(game_window):
                        return "未檢測到介面UI，跳過執行動作"
                else:
                    return "找不到遊戲視窗，無法檢查介面UI"
            except Exception as e:
                return f"介面UI檢查失敗: {str(e)}"

        # 分離血量和魔力設定
        health_settings = []
        mana_settings = []

        for setting in self.config.get('settings', []):
            setting_type = setting.get('type', 'health')
            if setting_type == 'health':
                health_settings.append(setting)
            else:
                mana_settings.append(setting)

        # 按照百分比從低到高排序（低百分比優先）
        health_settings.sort(key=lambda x: x['percent'])
        mana_settings.sort(key=lambda x: x['percent'])

        # 檢查血量設定
        if health_settings:
            for setting in health_settings:
                if health_percent <= setting['percent']:
                    # 檢查冷卻狀態
                    cooldown = setting.get('cooldown', 500)
                    last_trigger = self.last_trigger_times.get(setting['percent'], 0)
                    current_time = time.time()

                    if current_time - last_trigger >= cooldown / 1000:
                        return f"觸發 血量{setting['percent']}% ({setting['key']})"
                    else:
                        remaining = cooldown - (current_time - last_trigger) * 1000
                        return f"冷卻中 血量{setting['percent']}% ({setting['key']}) - 剩餘 {remaining:.0f}ms"

        # 檢查魔力設定
        if mana_percent is not None and mana_settings:
            for setting in mana_settings:
                if mana_percent <= setting['percent']:
                    # 檢查冷卻狀態
                    cooldown = setting.get('cooldown', 500)
                    last_trigger = self.last_trigger_times.get(setting['percent'], 0)
                    current_time = time.time()

                    if current_time - last_trigger >= cooldown / 1000:
                        return f"觸發 魔力{setting['percent']}% ({setting['key']})"
                    else:
                        remaining = cooldown - (current_time - last_trigger) * 1000
                        return f"冷卻中 魔力{setting['percent']}% ({setting['key']}) - 剩餘 {remaining:.0f}ms"

        return "正常"

    def trigger_actions(self, health_percent, mana_percent=None):
        """根據血量/魔力百分比觸發對應的快捷鍵動作，優先處理低百分比設定"""

        # === 介面UI戰鬥狀態檢查 ===
        # 如果設定了介面UI區域，檢查是否在戰鬥狀態
        if hasattr(self, 'interface_ui_region') and self.interface_ui_region and hasattr(self, 'interface_ui_screenshot') and self.interface_ui_screenshot is not None:
            try:
                # 獲取遊戲視窗
                windows = gw.getWindowsWithTitle(self.window_var.get())
                if windows:
                    game_window = windows[0]
                    # 檢查介面UI是否可見（是否在戰鬥狀態）
                    if not self.is_interface_ui_visible(game_window):
                        print(f"血魔檢查: 介面UI不存在，不在戰鬥狀態，跳過治療動作 (血量:{health_percent}%, 魔力:{mana_percent}%)")
                        return  # 不執行任何治療動作
                    else:
                        print(f"血魔檢查: 介面UI存在，正在戰鬥狀態，繼續執行治療動作")
                else:
                    print("血魔檢查: 找不到遊戲視窗，跳過介面UI檢查")
            except Exception as e:
                print(f"血魔檢查: 介面UI檢查失敗: {e}，繼續執行治療動作")
        else:
            print("血魔檢查: 未設定介面UI區域，跳過戰鬥狀態檢查")

        # 分離血量和魔力設定
        health_settings = []
        mana_settings = []

        for setting in self.config.get('settings', []):
            setting_type = setting.get('type', 'health')
            if setting_type == 'health':
                health_settings.append(setting)
            else:
                mana_settings.append(setting)

        # 按照百分比從低到高排序（低百分比優先）
        health_settings.sort(key=lambda x: x['percent'])
        mana_settings.sort(key=lambda x: x['percent'])

        # 處理血量設定
        if health_settings:
            for setting in health_settings:
                if health_percent <= setting['percent']:
                    # 檢查冷卻時間
                    cooldown = setting.get('cooldown', 500)  # 預設500ms
                    last_trigger = self.last_trigger_times.get(setting['percent'], 0)
                    current_time = time.time()
                    time_diff = current_time - last_trigger

                    print(f"🎯 血量觸發檢查: {health_percent}% <= {setting['percent']}% (設定閾值)")
                    print(f"🕐 冷卻檢查: 上次觸發時間 {time_diff:.3f}秒前, 需要冷卻 {cooldown/1000:.1f}秒")

                    if time_diff >= cooldown / 1000:  # 轉換為秒
                        try:
                            print(f"✅ 準備觸發: 血量{setting['percent']}%, 按鍵{setting['key']}")
                            # 添加狀態訊息
                            self.add_status_message(f"偵測到血量不足 {setting['percent']}%，自動使用 {setting['key']} 鍵", "monitor")
                            self.press_key_sequence(setting['key'], setting['percent'])
                            print(f"🎮 已完成按鍵序列: {setting['key']}")
                        except Exception as e:
                            print(f"❌ 按鍵觸發失敗: {e}")
                            pass
                    else:
                        remaining = cooldown - (time_diff) * 1000
                        print(f"⏳ 冷卻中: 還需等待 {remaining:.0f}ms")

                    # 找到第一個匹配的設定後就停止，避免執行更高百分比的設定
                    # 但是如果啟用了多重觸發，則繼續檢查其他設定
                    if not self.multi_trigger_var.get():
                        print(f"🚫 單一觸發模式: 停止檢查其他設定")
                        break
                    else:
                        print(f"🔄 多重觸發模式: 繼續檢查其他設定")
                        pass
                else:
                    print(f"⚪ 血量未達觸發條件: {health_percent}% > {setting['percent']}%")
                    pass

        # 處理魔力設定
        if mana_percent is not None and mana_settings:
            triggered = False
            for setting in mana_settings:
                if mana_percent <= setting['percent']:
                    # 檢查冷卻時間
                    cooldown = setting.get('cooldown', 500)  # 預設500ms
                    last_trigger = self.last_trigger_times.get(f"mana_{setting['percent']}", 0)
                    current_time = time.time()

                    if current_time - last_trigger >= cooldown / 1000:  # 轉換為秒
                        try:
                            # 添加狀態訊息
                            self.add_status_message(f"偵測到魔力不足 {setting['percent']}%，自動使用 {setting['key']} 鍵", "monitor")
                            self.press_key_sequence(setting['key'], f"mana_{setting['percent']}")
                            triggered = True
                        except Exception as e:
                            pass
                    else:
                        remaining = cooldown - (current_time - last_trigger) * 1000
                        triggered = True  # 即使在冷卻中，也標記為已處理

                    # 找到第一個匹配的設定後就停止，避免執行更高百分比的設定
                    # 但是如果啟用了多重觸發，則繼續檢查其他設定
                    if not self.multi_trigger_var.get():
                        break
                    else:
                        pass
                else:
                    pass

    def press_key_sequence(self, key_sequence, health_percent=None):
        """處理多鍵序列，按順序按下每個鍵 - 血魔監控專用"""
        print(f"🩸 血魔監控開始執行按鍵序列: {key_sequence}")
        
        # 解析鍵序列（用 - 分隔）
        keys = [key.strip() for key in key_sequence.split('-')]
        print(f"🩸 血魔監控解析後的按鍵列表: {keys}")

        # 獲取遊戲窗口句柄
        game_hwnd = self.get_game_window_handle()
        if game_hwnd:
            print(f"🩸 血魔監控使用全局發送到遊戲窗口: {game_hwnd}")
            # 使用修復版本的按鍵發送（keyboard庫 + 防重複）
            for i, key in enumerate(keys):
                vk_code = self.map_key_to_vk_code(key)
                if vk_code:
                    print(f"🩸 血魔按鍵 {i+1}/{len(keys)}: {key} -> VK_{vk_code}")
                    self.send_key_to_window(game_hwnd, vk_code)  # 使用修復版本
                else:
                    print(f"🩸 血魔按鍵 {i+1}/{len(keys)}: {key} -> 無法映射鍵碼")

                # 如果不是最後一個鍵，添加延遲
                if i < len(keys) - 1:
                    print(f"🩸 血魔按鍵間延遲: 25ms")
                    time.sleep(0.025)  # 25毫秒延遲
        else:
            print("使用全域鍵盤事件（無法獲取遊戲窗口）")
            # 回退到全局鍵盤事件
            for i, key in enumerate(keys):
                # 處理特殊鍵名映射
                mapped_key = self.map_key_name(key)
                print(f"按鍵 {i+1}/{len(keys)}: {key} -> {mapped_key}")
                # 按下並釋放鍵
                keyboard.press_and_release(mapped_key)

                # 如果不是最後一個鍵，添加延遲
                if i < len(keys) - 1:
                    print(f"按鍵間延遲: 25ms")
                    time.sleep(0.025)  # 25毫秒延遲

        print(f"按鍵序列執行完成: {key_sequence}")
        
        # 記錄觸發時間（用於冷卻計算）
        if health_percent is not None:
            # 處理魔力設定的特殊鍵
            if isinstance(health_percent, str) and health_percent.startswith('mana_'):
                # 對於魔力設定，使用原始百分比作為鍵
                mana_percent = int(health_percent.split('_')[1])
                self.last_trigger_times[f"mana_{mana_percent}"] = time.time()
                print(f"記錄魔力觸發時間: mana_{mana_percent}")
            else:
                # 對於血量設定，直接使用百分比
                self.last_trigger_times[health_percent] = time.time()
                print(f"記錄血量觸發時間: {health_percent}")


    def get_game_window_handle(self):
        """獲取遊戲窗口的句柄"""
        try:
            if not self.window_var.get():
                return None

            windows = gw.getWindowsWithTitle(self.window_var.get())
            if windows:
                return windows[0]._hWnd
            return None
        except Exception as e:
            return None

    def map_key_to_vk_code(self, key):
        """將鍵名映射到Windows虛擬鍵碼"""
        key = key.lower()

        # 數字鍵
        if key.isdigit():
            return ord(key)

        # 字母鍵
        if len(key) == 1 and key.isalpha():
            return ord(key.upper())

        # 特殊鍵映射
        key_mapping = {
            'esc': VK_ESCAPE,
            'escape': VK_ESCAPE,
            'enter': VK_RETURN,
            'return': VK_RETURN,
            'space': VK_SPACE,
            'tab': VK_TAB,
            'backspace': VK_BACK,
            'delete': VK_DELETE,
            'home': VK_HOME,
            'end': VK_END,
            'left': VK_LEFT,
            'up': VK_UP,
            'right': VK_RIGHT,
            'down': VK_DOWN,
            'f3': VK_F3,
            'f5': VK_F5,
            'f6': VK_F6,
            'f7': VK_F7,
            'f8': VK_F8,
            'f9': VK_F9,
            'f10': VK_F10,
            'f12': VK_F12,
        }

        return key_mapping.get(key)

    def send_key_to_window(self, hwnd, vk_code):
        """發送鍵盤事件到指定窗口 - 血魔監控專用（修復版本）"""
        try:
            # 增加防重複機制 - 檢查是否剛剛發送過相同的鍵
            current_time = time.time()
            key_id = f"{hwnd}_{vk_code}"
            
            # 檢查是否在200毫秒內發送過相同的鍵（增加到200ms防重複）
            if hasattr(self, '_last_key_send_times'):
                last_send_time = self._last_key_send_times.get(key_id, 0)
                if current_time - last_send_time < 0.2:  # 200毫秒防重複
                    print(f"🚫 血魔防重複: 跳過重複按鍵 {vk_code} (間隔 {(current_time - last_send_time)*1000:.1f}ms)")
                    return
            else:
                self._last_key_send_times = {}
            
            # 記錄發送時間
            self._last_key_send_times[key_id] = current_time
            
            print(f"🩸 血魔監控發送按鍵: VK_{vk_code} 到窗口 {hwnd}")
            
            # 🔄 使用最穩定的方法: keyboard庫全局按鍵 + 激活窗口
            try:
                import keyboard
                import pygetwindow as gw
                
                # 首先激活遊戲窗口
                windows = gw.getWindowsWithTitle(self.window_var.get())
                if windows:
                    windows[0].activate()
                    time.sleep(0.05)  # 等待窗口激活
                
                # 使用keyboard庫發送按鍵 - 最穩定的方法
                key_name = self.vk_to_key_name(vk_code)
                if key_name:
                    print(f"🎯 血魔使用keyboard庫發送: {key_name}")
                    keyboard.press_and_release(key_name)
                    print(f"✅ 血魔keyboard庫發送成功: {key_name}")
                else:
                    # 回退到PostMessage方法
                    self._send_with_postmessage(hwnd, vk_code)
                    
            except ImportError:
                print("⚠️ keyboard庫未安裝，血魔使用PostMessage方法")
                self._send_with_postmessage(hwnd, vk_code)
            except Exception as keyboard_error:
                print(f"⚠️ keyboard庫發送失敗，血魔回退到PostMessage: {keyboard_error}")
                self._send_with_postmessage(hwnd, vk_code)
                
        except Exception as e:
            print(f"❌ 血魔按鍵發送失敗: {e}")
            pass

    def send_key_to_window_combo(self, hwnd, vk_code):
        """發送鍵盤事件到指定窗口 - 技能連段專用（原始版本）"""
        try:
            print(f"⚔️ 技能連段發送按鍵: VK_{vk_code} 到窗口 {hwnd}")
            
            # 使用原始的SendMessage方法 - 針對特定窗口，不會干擾聊天
            SendMessageW(hwnd, WM_KEYDOWN, vk_code, 0)
            time.sleep(0.01)  # 原始的10毫秒延遲
            SendMessageW(hwnd, WM_KEYUP, vk_code, 0)
            
            print(f"✅ 技能連段SendMessage發送成功: VK_{vk_code}")
                
        except Exception as e:
            print(f"❌ 技能連段按鍵發送失敗: {e}")
            pass

    def _send_with_postmessage(self, hwnd, vk_code):
        """使用PostMessage發送按鍵的備用方法"""
        try:
            from ctypes import windll
            PostMessageW = windll.user32.PostMessageW
            
            print(f"🔄 使用PostMessage備用方法: VK_{vk_code}")
            # 使用PostMessage (異步)
            result1 = PostMessageW(hwnd, WM_KEYDOWN, vk_code, 0)
            time.sleep(0.1)  # 增加到100毫秒延遲
            result2 = PostMessageW(hwnd, WM_KEYUP, vk_code, 0)
            
            print(f"✅ PostMessage發送成功: VK_{vk_code} (down:{result1}, up:{result2})")
        except Exception as e:
            print(f"❌ PostMessage發送失敗: {e}")

    def vk_to_key_name(self, vk_code):
        """將虛擬鍵碼轉換為keyboard庫能識別的鍵名"""
        vk_mapping = {
            0x1B: 'esc',  # ESC
            0x31: '1', 0x32: '2', 0x33: '3', 0x34: '4', 0x35: '5',
            0x36: '6', 0x37: '7', 0x38: '8', 0x39: '9', 0x30: '0',
            0x41: 'a', 0x42: 'b', 0x43: 'c', 0x44: 'd', 0x45: 'e',
            0x46: 'f', 0x47: 'g', 0x48: 'h', 0x49: 'i', 0x4A: 'j',
            0x4B: 'k', 0x4C: 'l', 0x4D: 'm', 0x4E: 'n', 0x4F: 'o',
            0x50: 'p', 0x51: 'q', 0x52: 'r', 0x53: 's', 0x54: 't',
            0x55: 'u', 0x56: 'v', 0x57: 'w', 0x58: 'x', 0x59: 'y',
            0x5A: 'z',
            0x70: 'f1', 0x71: 'f2', 0x72: 'f3', 0x73: 'f4', 0x74: 'f5',
            0x75: 'f6', 0x76: 'f7', 0x77: 'f8', 0x78: 'f9', 0x79: 'f10',
            0x7A: 'f11', 0x7B: 'f12',
            0x20: 'space', 0x0D: 'enter', 0x09: 'tab',
        }
        return vk_mapping.get(vk_code, None)

    def map_key_name(self, key):
        """映射鍵名到 keyboard 模組能識別的格式"""
        key = key.lower()

        # 特殊鍵映射
        key_mapping = {
            'esc': 'esc',
            'escape': 'esc',
            'enter': 'enter',
            'return': 'enter',
            'space': 'space',
            'tab': 'tab',
            'backspace': 'backspace',
            'delete': 'delete',
            'home': 'home',
            'end': 'end',
            'pageup': 'page up',
            'pagedown': 'page down',
            'uparrow': 'up',
            'downarrow': 'down',
            'leftarrow': 'left',
            'rightarrow': 'right',
            'ctrl': 'ctrl',
            'alt': 'alt',
            'shift': 'shift',
            'win': 'windows',
            'cmd': 'windows',  # mac 兼容
        }

        return key_mapping.get(key, key)

    def update_status(self, health, mana, color, trigger):
        """平滑更新狀態顯示，避免頻繁更新導致閃爍"""
        import time as time_module

        current_time = time_module.time() * 1000  # 轉換為毫秒

        # 檢查是否需要更新（時間間隔控制）
        if (current_time - self.last_status_update) < self.status_update_interval:
            return

        # 使用tkinter的after方法非同步更新
        self.root.after(0, lambda: self._update_status_labels(health, mana, color, trigger))

        # 更新時間戳
        self.last_status_update = current_time

    def _update_status_labels(self, health, mana, color, trigger):
        """實際更新狀態標籤的私有方法"""
        try:
            self.health_label.config(text=health)
            self.mana_label.config(text=mana)
            self.color_label.config(text=color)
            self.trigger_label.config(text=trigger)
        except Exception as e:
            print(f"更新狀態標籤失敗: {e}")

    def is_game_window_foreground(self, window_title):
        """檢查遊戲視窗是否處於前台（活躍狀態）"""
        try:
            # 獲取當前前台視窗的句柄
            foreground_hwnd = GetForegroundWindow()

            # 獲取前台視窗標題的長度
            length = GetWindowTextLengthW(foreground_hwnd)
            if length > 0:
                # 創建緩衝區來存儲視窗標題
                buffer = ctypes.create_unicode_buffer(length + 1)
                GetWindowTextW(foreground_hwnd, buffer, length + 1)
                foreground_title = buffer.value

                # 檢查前台視窗標題是否包含遊戲視窗標題
                return window_title.lower() in foreground_title.lower()
            else:
                return False

        except Exception as e:
            print(f"檢查前台視窗失敗: {e}")
            return False

    def is_gui_foreground(self):
        """檢查GUI視窗是否處於前台（活躍狀態）"""
        try:
            # 獲取當前前台視窗的句柄
            foreground_hwnd = GetForegroundWindow()

            # 獲取前台視窗標題的長度
            length = GetWindowTextLengthW(foreground_hwnd)
            if length > 0:
                # 創建緩衝區來存儲視窗標題
                buffer = ctypes.create_unicode_buffer(length + 1)
                GetWindowTextW(foreground_hwnd, buffer, length + 1)
                foreground_title = buffer.value

                # 檢查前台視窗標題是否包含GUI標題
                gui_title = "遊戲輔助工具 v1.0.2 - 血魔監控 + 一鍵清包 + 自動化工具"
                return gui_title.lower() in foreground_title.lower()
            else:
                return False

        except Exception as e:
            print(f"檢查GUI前台狀態失敗: {e}")
            return False

    def adjust_colors(self):
        """調整顏色檢測參數"""
        adjust_window = self.create_settings_window("🎨 調整顏色檢測參數", "750x700")
        adjust_window.resizable(False, False)
        adjust_window.focus_force()

        # 主標題
        title_label = ttk.Label(adjust_window, text="調整血量顏色檢測參數",
                               font=("Arial", 12, "bold"))
        title_label.pack(pady=(20, 15))

        # 創建滾動區域
        # 主容器框架
        container = ttk.Frame(adjust_window)
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 20))

        # 創建Canvas和滾動條
        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 滾動事件綁定
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        def _bind_to_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_from_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind('<Enter>', _bind_to_mousewheel)
        canvas.bind('<Leave>', _unbind_from_mousewheel)

        # 佈局Canvas和滾動條
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 按鈕區域 - 放在滾動區域外面，始終可見
        button_frame = ttk.Frame(adjust_window)
        button_frame.pack(pady=(10, 20))  # 在滾動區域下方

        # 創建主框架 (在可滾動區域內)
        main_frame = ttk.Frame(scrollable_frame)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 健康比例閾值區域
        health_frame = ttk.LabelFrame(main_frame, text="健康像素比例門檻值", padding="10")
        health_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(health_frame, text="當前值:").grid(row=0, column=0, sticky=tk.W, pady=2)
        current_health_label = ttk.Label(health_frame, text=f"{self.health_threshold}",
                                        font=("Arial", 9, "bold"), foreground="blue")
        current_health_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(health_frame, text="新值 (0.0-1.0):").grid(row=1, column=0, sticky=tk.W, pady=(10, 2))
        health_threshold_var = tk.StringVar(value=str(self.health_threshold))
        health_entry = ttk.Entry(health_frame, textvariable=health_threshold_var, width=12)
        health_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 2))

        # 健康比例閾值詳細說明
        health_explanation = """🏥 健康像素比例門檻值 決定區域血量顏色檢測的敏感度
• 值越接近1.0 = 檢測越嚴格 (區域需有更多血量顏色才算"有血量")
• 值越接近0.0 = 檢測越寬鬆 (區域只需少量血量顏色就算"有血量")
• 建議範圍: 0.2-0.5 (依據血量條設計和遊戲調整)
• 適用於: 判斷血量條的每個小區域是否包含血量顏色"""
        ttk.Label(health_frame, text=health_explanation, font=("", 9),
                 foreground="gray", justify=tk.LEFT, wraplength=500).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        # 顏色範圍區域
        color_frame = ttk.LabelFrame(main_frame, text="顏色範圍設定", padding="10")
        color_frame.pack(fill=tk.X, pady=(0, 10))

        # 紅色H範圍
        ttk.Label(color_frame, text="紅色H範圍:").grid(row=0, column=0, sticky=tk.W, pady=2)
        current_red_label = ttk.Label(color_frame, text=f"{self.red_h_range}",
                                     font=("Arial", 9, "bold"), foreground="red")
        current_red_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(color_frame, text="新值 (0-20):").grid(row=1, column=0, sticky=tk.W, pady=(5, 2))
        red_h_var = tk.StringVar(value=str(self.red_h_range))
        red_entry = ttk.Entry(color_frame, textvariable=red_h_var, width=12)
        red_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(5, 2))

        # 紅色H範圍詳細說明
        red_explanation = """🔴 紅色H範圍 (顏色種類) 定義紅色顏色的最大範圍上限
• 值越小 = 紅色顏色範圍較窄 (只檢測特定紅色)，檢測更精確
• 值越大 = 紅色顏色範圍較寬，包含更多種紅色變化
• 建議範圍: 0-20 (標準紅色範圍)
• 適用於: 低血量時的紅色血量條檢測"""
        ttk.Label(color_frame, text=red_explanation, font=("", 9),
                 foreground="gray", justify=tk.LEFT, wraplength=500).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        # 綠色H範圍
        ttk.Label(color_frame, text="綠色H範圍:").grid(row=3, column=0, sticky=tk.W, pady=(15, 2))
        current_green_label = ttk.Label(color_frame, text=f"{self.green_h_range}",
                                       font=("Arial", 9, "bold"), foreground="green")
        current_green_label.grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=(15, 2))

        ttk.Label(color_frame, text="新值 (30-90):").grid(row=4, column=0, sticky=tk.W, pady=(5, 2))
        green_h_var = tk.StringVar(value=str(self.green_h_range))
        green_entry = ttk.Entry(color_frame, textvariable=green_h_var, width=12)
        green_entry.grid(row=4, column=1, sticky=tk.W, padx=(10, 0), pady=(5, 2))

        # 綠色H範圍詳細說明
        green_explanation = """🟢 綠色H範圍 (顏色種類) 定義血量條健康時的綠色顏色範圍
• 值越小 = 檢測偏黃的綠色調
• 值越大 = 檢測偏藍的綠色調
• 建議範圍: 30-90 (標準綠色範圍)
• 適用於: 健康狀態時的綠色血量條檢測"""
        ttk.Label(color_frame, text=green_explanation, font=("", 9),
                 foreground="gray", justify=tk.LEFT, wraplength=500).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        # HSV精細調整區域
        hsv_frame = ttk.LabelFrame(main_frame, text="HSV精細調整", padding="10")
        hsv_frame.pack(fill=tk.X, pady=(0, 10))

        # 紅色飽和度
        ttk.Label(hsv_frame, text="紅色最小鮮豔度:").grid(row=0, column=0, sticky=tk.W, pady=2)
        current_red_sat_label = ttk.Label(hsv_frame, text=f"{self.red_saturation_min}",
                                         font=("Arial", 9, "bold"), foreground="red")
        current_red_sat_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(hsv_frame, text="新值 (50-255):").grid(row=1, column=0, sticky=tk.W, pady=(5, 2))
        red_sat_var = tk.StringVar(value=str(self.red_saturation_min))
        red_sat_entry = ttk.Entry(hsv_frame, textvariable=red_sat_var, width=12)
        red_sat_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(5, 2))

        # 紅色亮度
        ttk.Label(hsv_frame, text="紅色最小明亮度:").grid(row=2, column=0, sticky=tk.W, pady=(10, 2))
        current_red_val_label = ttk.Label(hsv_frame, text=f"{self.red_value_min}",
                                         font=("Arial", 9, "bold"), foreground="red")
        current_red_val_label.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 2))

        ttk.Label(hsv_frame, text="新值 (50-255):").grid(row=3, column=0, sticky=tk.W, pady=(5, 2))
        red_val_var = tk.StringVar(value=str(self.red_value_min))
        red_val_entry = ttk.Entry(hsv_frame, textvariable=red_val_var, width=12)
        red_val_entry.grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=(5, 2))

        # 紅色HSV參數說明
        red_hsv_explanation = """🔴 紅色HSV參數 控制低血量紅色像素的檢測靈敏度
• 顏色鮮豔度: 值越低 = 檢測更暗淡的紅色，越高 = 只檢測鮮豔紅色
• 顏色明亮度: 值越低 = 檢測更暗的紅色，越高 = 只檢測明亮的紅色
• 建議範圍: 鮮豔度50-150，明亮度50-150
• 適用於: 適應不同遊戲畫面亮度和對比度"""
        ttk.Label(hsv_frame, text=red_hsv_explanation, font=("", 9),
                 foreground="gray", justify=tk.LEFT, wraplength=500).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        # 綠色飽和度
        ttk.Label(hsv_frame, text="綠色最小鮮豔度:").grid(row=0, column=2, sticky=tk.W, padx=(30, 0), pady=2)
        current_green_sat_label = ttk.Label(hsv_frame, text=f"{self.green_saturation_min}",
                                           font=("Arial", 9, "bold"), foreground="green")
        current_green_sat_label.grid(row=0, column=3, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(hsv_frame, text="新值 (50-255):").grid(row=1, column=2, sticky=tk.W, padx=(30, 0), pady=(5, 2))
        green_sat_var = tk.StringVar(value=str(self.green_saturation_min))
        green_sat_entry = ttk.Entry(hsv_frame, textvariable=green_sat_var, width=12)
        green_sat_entry.grid(row=1, column=3, sticky=tk.W, padx=(10, 0), pady=(5, 2))

        # 綠色亮度
        ttk.Label(hsv_frame, text="綠色最小明亮度:").grid(row=2, column=2, sticky=tk.W, padx=(30, 0), pady=(10, 2))
        current_green_val_label = ttk.Label(hsv_frame, text=f"{self.green_value_min}",
                                           font=("Arial", 9, "bold"), foreground="green")
        current_green_val_label.grid(row=2, column=3, sticky=tk.W, padx=(10, 0), pady=(10, 2))

        ttk.Label(hsv_frame, text="新值 (50-255):").grid(row=3, column=2, sticky=tk.W, padx=(30, 0), pady=(5, 2))
        green_val_var = tk.StringVar(value=str(self.green_value_min))
        green_val_entry = ttk.Entry(hsv_frame, textvariable=green_val_var, width=12)
        green_val_entry.grid(row=3, column=3, sticky=tk.W, padx=(10, 0), pady=(5, 2))

        # 綠色HSV參數說明
        green_hsv_explanation = """🟢 綠色HSV參數 控制健康狀態綠色像素的檢測靈敏度
• 顏色鮮豔度: 值越低 = 檢測更暗淡的綠色，越高 = 只檢測鮮豔綠色
• 顏色明亮度: 值越低 = 檢測更暗的綠色，越高 = 只檢測明亮的綠色
• 建議範圍: 鮮豔度50-150，明亮度50-150
• 適用於: 適應不同遊戲畫面亮度和對比度"""
        ttk.Label(hsv_frame, text=green_hsv_explanation, font=("", 9),
                 foreground="gray", justify=tk.LEFT, wraplength=500).grid(row=4, column=2, columnspan=2, sticky=tk.W, pady=(5, 0))

        # 設置輸入驗證 - 改進版，更寬鬆的驗證
        def validate_float_input(P):
            """寬鬆的浮點數驗證，允許數字、小數點、負號"""
            if P == "" or P == "-" or P == ".":
                return True
            # 允許以數字開頭後跟小數點，或以小數點開頭後跟數字
            if P.replace(".", "").replace("-", "").isdigit():
                # 檢查小數點數量（最多一個）
                if P.count(".") <= 1:
                    # 檢查負號位置（只能在開頭）
                    if P.count("-") <= 1 and (P.find("-") == 0 or P.find("-") == -1):
                        return True
            return False

        def validate_int_input(P):
            """寬鬆的整數驗證，允許數字和負號"""
            if P == "" or P == "-":
                return True
            # 允許負號只在開頭，且後面都是數字
            if P.replace("-", "").isdigit():
                if P.count("-") <= 1 and (P.find("-") == 0 or P.find("-") == -1):
                    return True
            return False

        vcmd_float = (adjust_window.register(validate_float_input), '%P')
        vcmd_int = (adjust_window.register(validate_int_input), '%P')

        health_entry.config(validate='key', validatecommand=vcmd_float)
        red_entry.config(validate='key', validatecommand=vcmd_int)
        green_entry.config(validate='key', validatecommand=vcmd_int)
        red_sat_entry.config(validate='key', validatecommand=vcmd_int)
        red_val_entry.config(validate='key', validatecommand=vcmd_int)
        green_sat_entry.config(validate='key', validatecommand=vcmd_int)
        green_val_entry.config(validate='key', validatecommand=vcmd_int)

        def apply_settings():
            try:
                new_health_threshold = float(health_threshold_var.get())
                new_red_h_range = int(red_h_var.get())
                new_green_h_range = int(green_h_var.get())
                new_red_sat_min = int(red_sat_var.get())
                new_red_val_min = int(red_val_var.get())
                new_green_sat_min = int(green_sat_var.get())
                new_green_val_min = int(green_val_var.get())

                # 驗證輸入範圍
                if not (0.0 <= new_health_threshold <= 1.0):
                    messagebox.showerror("輸入錯誤", "健康比例門檻值必須在 0.0-1.0 之間")
                    return

                if not (0 <= new_red_h_range <= 20):
                    messagebox.showerror("輸入錯誤", "紅色H範圍必須在 0-20 之間")
                    return

                if not (30 <= new_green_h_range <= 90):
                    messagebox.showerror("輸入錯誤", "綠色H範圍必須在 30-90 之間")
                    return

                if not (50 <= new_red_sat_min <= 255):
                    messagebox.showerror("輸入錯誤", "紅色最小鮮豔度必須在 50-255 之間")
                    return

                if not (50 <= new_red_val_min <= 255):
                    messagebox.showerror("輸入錯誤", "紅色最小明亮度必須在 50-255 之間")
                    return

                if not (50 <= new_green_sat_min <= 255):
                    messagebox.showerror("輸入錯誤", "綠色最小鮮豔度必須在 50-255 之間")
                    return

                if not (50 <= new_green_val_min <= 255):
                    messagebox.showerror("輸入錯誤", "綠色最小明亮度必須在 50-255 之間")
                    return

                # 應用設定
                self.health_threshold = new_health_threshold
                self.red_h_range = new_red_h_range
                self.green_h_range = new_green_h_range
                self.red_saturation_min = new_red_sat_min
                self.red_value_min = new_red_val_min
                self.green_saturation_min = new_green_sat_min
                self.green_value_min = new_green_val_min

                # 保存到配置文件
                self.config['health_threshold'] = self.health_threshold
                self.config['red_h_range'] = self.red_h_range
                self.config['green_h_range'] = self.green_h_range
                self.config['red_saturation_min'] = self.red_saturation_min
                self.config['red_value_min'] = self.red_value_min
                self.config['green_saturation_min'] = self.green_saturation_min
                self.config['green_value_min'] = self.green_value_min
                self.save_config()

                # 更新顯示的當前值
                current_health_label.config(text=f"{self.health_threshold}")
                current_red_label.config(text=f"{self.red_h_range}")
                current_green_label.config(text=f"{self.green_h_range}")
                current_red_sat_label.config(text=f"{self.red_saturation_min}")
                current_red_val_label.config(text=f"{self.red_value_min}")
                current_green_sat_label.config(text=f"{self.green_saturation_min}")
                current_green_val_label.config(text=f"{self.green_value_min}")

                messagebox.showinfo("設定已應用",
                                  f"✅ 顏色參數已成功更新並儲存！\n\n"
                                  f"🏥 健康閾值: {self.health_threshold}\n"
                                  f"🔴 紅色H範圍: {self.red_h_range}\n"
                                  f"🟢 綠色H範圍: {self.green_h_range}\n"
                                  f"📊 紅色飽和度: {self.red_saturation_min}\n"
                                  f"💡 紅色亮度: {self.red_value_min}\n"
                                  f"📊 綠色飽和度: {self.green_saturation_min}\n"
                                  f"💡 綠色亮度: {self.green_value_min}")
                
                # 關閉視窗
                adjust_window.destroy()

            except ValueError:
                messagebox.showerror("輸入錯誤", "請輸入有效的數字")

        def reset_to_defaults():
            """重置為預設值"""
            health_threshold_var.set("0.3")
            red_h_var.set("10")
            green_h_var.set("40")
            red_sat_var.set("50")
            red_val_var.set("50")
            green_sat_var.set("50")
            green_val_var.set("50")
            messagebox.showinfo("重置完成", "已重置為預設值，請點擊「應用設定」來儲存")
            # 重新激活父視窗
            adjust_window.lift()
            adjust_window.focus_force()
            adjust_window.attributes("-topmost", True)

        # 按鈕 - 放在所有函數定義之後
        ttk.Button(button_frame, text="✅ 應用設定", command=apply_settings,
                  style="Accent.TButton").grid(row=0, column=0, padx=(0, 10))
        ttk.Button(button_frame, text="🔄 重置預設值", command=reset_to_defaults).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(button_frame, text="❌ 取消", command=adjust_window.destroy).grid(row=0, column=2)

    def adjust_interface_ui_thresholds(self):
        """調整介面UI檢測參數"""
        adjust_window = self.create_settings_window("🖼️ 調整介面UI檢測參數", "420x700")
        adjust_window.resizable(False, False)
        adjust_window.focus_force()

        # 主標題
        title_label = ttk.Label(adjust_window, text="調整介面UI檢測參數",
                               font=("Arial", 12, "bold"))
        title_label.pack(pady=(20, 15))

        # 創建滾動區域
        # 主容器框架
        container = ttk.Frame(adjust_window)
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 20))

        # 創建Canvas和滾動條
        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 滾動事件綁定
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        def _bind_to_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_from_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind('<Enter>', _bind_to_mousewheel)
        canvas.bind('<Leave>', _unbind_from_mousewheel)

        # 佈局Canvas和滾動條
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 按鈕區域 - 放在滾動區域外面，始終可見
        button_frame = ttk.Frame(adjust_window)
        button_frame.pack(pady=(10, 20))  # 在滾動區域下方

        # 創建主框架 (在可滾動區域內)
        main_frame = ttk.Frame(scrollable_frame)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # MSE閾值區域
        mse_frame = ttk.LabelFrame(main_frame, text="MSE門檻值 (像素差異)", padding="10")
        mse_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(mse_frame, text="當前值:").grid(row=0, column=0, sticky=tk.W, pady=2)
        current_mse_label = ttk.Label(mse_frame, text=f"{self.interface_ui_mse_threshold}",
                                     font=("Arial", 9, "bold"), foreground="blue")
        current_mse_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(mse_frame, text="新值 (建議: 500-1500):").grid(row=1, column=0, sticky=tk.W, pady=(10, 2))
        mse_var = tk.StringVar(value=str(int(self.interface_ui_mse_threshold)))
        mse_entry = ttk.Entry(mse_frame, textvariable=mse_var, width=12)
        mse_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 2))

        # MSE詳細說明
        mse_explanation = """📊 MSE (像素差異) 用於比較圖片的像素差異
• 值越小 = 檢測越嚴格 (只接受像素差異很小的圖片)
• 值越大 = 檢測越寬鬆 (允許較大像素差異的圖片)
• 建議範圍: 降低值可避免誤判，升高值可適應動態UI"""
        ttk.Label(mse_frame, text=mse_explanation, font=("", 9),
                 foreground="gray", justify=tk.LEFT, wraplength=320).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        # SSIM閾值區域
        ssim_frame = ttk.LabelFrame(main_frame, text="SSIM門檻值 (圖片相似度)", padding="10")
        ssim_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(ssim_frame, text="當前值:").grid(row=0, column=0, sticky=tk.W, pady=2)
        current_ssim_label = ttk.Label(ssim_frame, text=f"{self.interface_ui_ssim_threshold}",
                                      font=("Arial", 9, "bold"), foreground="green")
        current_ssim_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(ssim_frame, text="新值 (0.0-1.0):").grid(row=1, column=0, sticky=tk.W, pady=(10, 2))
        ssim_var = tk.StringVar(value=str(self.interface_ui_ssim_threshold))
        ssim_entry = ttk.Entry(ssim_frame, textvariable=ssim_var, width=12)
        ssim_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 2))

        # SSIM參數說明
        ttk.Label(ssim_frame, text="📊 SSIM (圖片相似度) 評估圖片的整體結構相似度\n"
                                  "• 值越接近1.0 = 檢測越嚴格 (只接受高度相似的圖片)\n"
                                  "• 值越接近0.0 = 檢測越寬鬆 (允許更多結構變化)\n"
                                  "• 推薦範圍: 0.85-0.95 (平衡靈活性和準確性)\n"
                                  "• 適用於: 檢測UI元素位置和佈局變化",
                 font=("Arial", 9), foreground="#666666", wraplength=320).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        # 直方圖閾值區域
        hist_frame = ttk.LabelFrame(main_frame, text="顏色分布相似度門檻值", padding="10")
        hist_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(hist_frame, text="當前值:").grid(row=0, column=0, sticky=tk.W, pady=2)
        current_hist_label = ttk.Label(hist_frame, text=f"{self.interface_ui_hist_threshold}",
                                      font=("Arial", 9, "bold"), foreground="orange")
        current_hist_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(hist_frame, text="新值 (0.0-1.0):").grid(row=1, column=0, sticky=tk.W, pady=(10, 2))
        hist_var = tk.StringVar(value=str(self.interface_ui_hist_threshold))
        hist_entry = ttk.Entry(hist_frame, textvariable=hist_var, width=12)
        hist_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 2))

        # 直方圖參數說明
        ttk.Label(hist_frame, text="📈 顏色分布相似度 比較圖片的顏色分佈特徵\n"
                                  "• 值越接近1.0 = 檢測越嚴格 (要求顏色分佈高度相似)\n"
                                  "• 值越接近0.0 = 檢測越寬鬆 (允許顏色分佈較大差異)\n"
                                  "• 推薦範圍: 0.90-0.98 (適合大多數UI檢測場景)\n"
                                  "• 適用於: 檢測整體色彩風格和亮度變化",
                 font=("Arial", 9), foreground="#666666", wraplength=320).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        # 顏色差異閾值區域
        color_frame = ttk.LabelFrame(main_frame, text="顏色差異門檻值", padding="10")
        color_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(color_frame, text="當前值:").grid(row=0, column=0, sticky=tk.W, pady=2)
        current_color_label = ttk.Label(color_frame, text=f"{self.interface_ui_color_threshold}",
                                       font=("Arial", 9, "bold"), foreground="red")
        current_color_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(color_frame, text="新值 (建議: 20-60):").grid(row=1, column=0, sticky=tk.W, pady=(10, 2))
        color_var = tk.StringVar(value=str(int(self.interface_ui_color_threshold)))
        color_entry = ttk.Entry(color_frame, textvariable=color_var, width=12)
        color_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 2))

        # 顏色差異參數說明
        ttk.Label(color_frame, text="🎨 顏色差異 測量RGB顏色通道的平均差異值\n"
                                  "• 值越小 = 檢測越嚴格 (要求顏色高度相似)\n"
                                  "• 值越大 = 檢測越寬鬆 (允許較大顏色變化)\n"
                                  "• 推薦範圍: 20-60 (依據圖片品質和照明條件調整)\n"
                                  "• 適用於: 檢測細微的顏色變化或照明差異",
                 font=("Arial", 9), foreground="#666666", wraplength=320).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        def apply_settings():
            try:
                # 獲取輸入值並檢查是否為空
                mse_str = mse_var.get().strip()
                ssim_str = ssim_var.get().strip()
                hist_str = hist_var.get().strip()
                color_str = color_var.get().strip()

                # 檢查是否為空
                if not mse_str:
                    messagebox.showerror("輸入錯誤", "MSE閾值不能為空")
                    return
                if not ssim_str:
                    messagebox.showerror("輸入錯誤", "SSIM閾值不能為空")
                    return
                if not hist_str:
                    messagebox.showerror("輸入錯誤", "直方圖閾值不能為空")
                    return
                if not color_str:
                    messagebox.showerror("輸入錯誤", "顏色差異閾值不能為空")
                    return

                # 嘗試轉換為數字
                try:
                    # MSE允許浮點數輸入，但最終轉換為整數
                    new_mse = int(float(mse_str))
                except ValueError:
                    messagebox.showerror("輸入錯誤", "MSE閾值必須是有效的數字")
                    return

                try:
                    new_ssim = float(ssim_str)
                except ValueError:
                    messagebox.showerror("輸入錯誤", "SSIM閾值必須是有效的數字")
                    return

                try:
                    new_hist = float(hist_str)
                except ValueError:
                    messagebox.showerror("輸入錯誤", "直方圖閾值必須是有效的數字")
                    return

                try:
                    # 顏色差異允許浮點數輸入，但最終轉換為整數
                    new_color = int(float(color_str))
                except ValueError:
                    messagebox.showerror("輸入錯誤", "顏色差異閾值必須是有效的數字")
                    return

                # 驗證輸入範圍
                if not (100 <= new_mse <= 2000):
                    messagebox.showerror("輸入錯誤", "MSE閾值必須在 100-2000 之間")
                    return

                if not (0.0 <= new_ssim <= 1.0):
                    messagebox.showerror("輸入錯誤", "SSIM閾值必須在 0.0-1.0 之間")
                    return

                if not (0.0 <= new_hist <= 1.0):
                    messagebox.showerror("輸入錯誤", "直方圖閾值必須在 0.0-1.0 之間")
                    return

                if not (5 <= new_color <= 100):
                    messagebox.showerror("輸入錯誤", "顏色差異閾值必須在 5-100 之間")
                    return

                # 應用設定
                self.interface_ui_mse_threshold = new_mse
                self.interface_ui_ssim_threshold = new_ssim
                self.interface_ui_hist_threshold = new_hist
                self.interface_ui_color_threshold = new_color

                # 保存到配置文件
                self.config['interface_ui_mse_threshold'] = self.interface_ui_mse_threshold
                self.config['interface_ui_ssim_threshold'] = self.interface_ui_ssim_threshold
                self.config['interface_ui_hist_threshold'] = self.interface_ui_hist_threshold
                self.config['interface_ui_color_threshold'] = self.interface_ui_color_threshold
                self.save_config()

                # 更新顯示的當前值
                current_mse_label.config(text=f"{self.interface_ui_mse_threshold}")
                current_ssim_label.config(text=f"{self.interface_ui_ssim_threshold}")
                current_hist_label.config(text=f"{self.interface_ui_hist_threshold}")
                current_color_label.config(text=f"{self.interface_ui_color_threshold}")

                messagebox.showinfo("設定已應用",
                                  f"✅ 介面UI檢測參數已成功更新並儲存！\n\n"
                                  f"📊 MSE閾值: {self.interface_ui_mse_threshold}\n"
                                  f"🔍 SSIM閾值: {self.interface_ui_ssim_threshold}\n"
                                  f"📈 直方圖閾值: {self.interface_ui_hist_threshold}\n"
                                  f"🎨 顏色差異閾值: {self.interface_ui_color_threshold}")

                # 關閉視窗
                adjust_window.destroy()

            except Exception as e:
                messagebox.showerror("錯誤", f"應用設定時發生未知錯誤: {str(e)}")

        def reset_to_defaults():
            """重置為預設值"""
            mse_var.set("800")
            ssim_var.set("0.6")
            hist_var.set("0.7")
            color_var.set("35")
            messagebox.showinfo("重置完成", "已重置為預設值，請點擊「應用設定」來儲存")
            # 重新激活父視窗
            adjust_window.lift()
            adjust_window.focus_force()
            adjust_window.attributes("-topmost", True)

        # 設置輸入驗證 - 改進版，更寬鬆的驗證
        def validate_float_input(P):
            """寬鬆的浮點數驗證，允許數字、小數點、負號"""
            if P == "" or P == "-" or P == ".":
                return True
            # 允許以數字開頭後跟小數點，或以小數點開頭後跟數字
            if P.replace(".", "").replace("-", "").isdigit():
                # 檢查小數點數量（最多一個）
                if P.count(".") <= 1:
                    # 檢查負號位置（只能在開頭）
                    if P.count("-") <= 1 and (P.find("-") == 0 or P.find("-") == -1):
                        return True
            return False

        def validate_int_input(P):
            """寬鬆的整數驗證，允許數字和負號"""
            if P == "" or P == "-":
                return True
            # 允許負號只在開頭，且後面都是數字
            if P.replace("-", "").isdigit():
                if P.count("-") <= 1 and (P.find("-") == 0 or P.find("-") == -1):
                    return True
            return False

        vcmd_float = (adjust_window.register(validate_float_input), '%P')
        vcmd_int = (adjust_window.register(validate_int_input), '%P')

        mse_entry.config(validate='key', validatecommand=vcmd_int)
        ssim_entry.config(validate='key', validatecommand=vcmd_float)
        hist_entry.config(validate='key', validatecommand=vcmd_float)
        color_entry.config(validate='key', validatecommand=vcmd_int)

        # 按鈕 - 放在所有函數定義之後
        ttk.Button(button_frame, text="✅ 應用設定", command=apply_settings,
                  style="Accent.TButton").grid(row=0, column=0, padx=(0, 10))
        ttk.Button(button_frame, text="🔄 重置預設值", command=reset_to_defaults).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(button_frame, text="❌ 取消", command=adjust_window.destroy).grid(row=0, column=2)

    def setup_hotkeys(self):
        # 全域熱鍵，不受視窗焦點限制
        keyboard.add_hotkey('f3', self.quick_clear_inventory)  # F3: 一鍵清包（免費）
        keyboard.add_hotkey('f5', self.return_to_hideout)    # F5: 返回藏身（免費）
        keyboard.add_hotkey('f6', self.f6_pickup_items)      # F6: 一鍵取物（免費）
        keyboard.add_hotkey('f9', self.toggle_global_pause)  # F9: 全域暫停開關（免費）
        keyboard.add_hotkey('f10', self.toggle_monitoring)   # F10: 監控開關
        keyboard.add_hotkey('f12', self.close_app)
        
        self.add_status_message("全域熱鍵註冊成功", "success")
        
        # 設定 CTRL+左鍵自動點擊監聽器
        self.setup_auto_click_listener()
    
    def toggle_global_pause(self):
        """F9: 全域暫停開關 - 暫停/恢復所有熱鍵功能"""
        self.global_pause = not self.global_pause
        
        if self.global_pause:
            print("🔴 全域暫停已啟用 - 所有熱鍵功能已暫停")
            print("💬 現在可以安全聊天，不會誤觸任何熱鍵")
            print("🔄 再次按F9可恢復所有功能")
            
            # 添加狀態訊息
            self.add_status_message("按下 F9 - 全域暫停已啟用，所有熱鍵功能已停用", "warning")
            
            # 記錄並停止血魔監控（如果正在運行）
            if self.monitoring:
                self.monitoring_was_active = True
                self.stop_monitoring()
                print("🛑 血魔監控已自動停止")
                self.add_status_message("血魔監控已自動停止（暫停模式）", "info")
            else:
                self.monitoring_was_active = False
            
            # 記錄並停止技能連段（如果正在運行）
            if self.combo_running:
                self.combo_was_running = True
                self.stop_combo_system()
                print("🛑 技能連段已自動停止")
                self.add_status_message("技能連段已自動停止（暫停模式）", "info")
            else:
                self.combo_was_running = False
                
        else:
            print("🟢 全域暫停已解除 - 自動恢復之前的功能")
            
            # 添加狀態訊息
            self.add_status_message("按下 F9 - 全域暫停已解除，正在恢復功能", "success")
            
            # 自動恢復血魔監控（如果之前處於活躍狀態）
            if self.monitoring_was_active:
                try:
                    # 靜默重新啟動血魔監控
                    self.restart_monitoring_silently()
                    print("▶️ 血魔監控已自動重新啟動")
                    self.add_status_message("血魔監控已自動重新啟動", "success")
                except Exception as e:
                    print(f"⚠️ 血魔監控自動重新啟動失敗: {e}")
                    print("💡 請手動重新啟動血魔監控")
                    self.add_status_message(f"血魔監控自動重啟失敗: {str(e)}", "error")
            
            # 自動恢復技能連段（如果之前處於運行狀態）
            if self.combo_was_running:
                try:
                    # 靜默重新啟動技能連段系統
                    self.restart_combo_system_silently()
                    print("▶️ 技能連段已自動重新啟動")
                    self.add_status_message("技能連段已自動重新啟動", "success")
                except Exception as e:
                    print(f"⚠️ 技能連段自動重新啟動失敗: {e}")
                    print("💡 請手動重新啟動技能連段系統")
                    self.add_status_message(f"技能連段自動重啟失敗: {str(e)}", "error")
            
            print("⚡ 所有功能已完全恢復正常")
        
        # 更新UI顯示（如果有狀態標籤）
        self.update_pause_status_display()
    
    def update_pause_status_display(self):
        """更新暫停狀態顯示"""
        if self.pause_status_label:
            if self.global_pause:
                self.pause_status_label.config(
                    text="🔴 全域暫停中 - 所有熱鍵已停用",
                    foreground="red",
                    font=("Microsoft YaHei", 10, "bold")
                )
            else:
                self.pause_status_label.config(
                    text="🟢 正常運行",
                    foreground="green",
                    font=("Microsoft YaHei", 10, "normal")
                )
    
    def toggle_monitoring(self):
        """F10: 血魔監控開關"""
        # 全域暫停檢查
        if self.global_pause:
            print("🔴 全域暫停中，跳過F10熱鍵")
            self.add_status_message("按下 F10 - 因全域暫停模式而跳過執行", "warning")
            return

        if self.monitoring:
            self.add_status_message("按下 F10 - 停止血魔監控", "hotkey")
            self.stop_monitoring()
        else:
            self.add_status_message("按下 F10 - 啟動血魔監控", "hotkey")
            self.start_monitoring()

    def quick_clear_inventory(self):
        """F3快速清包功能"""
        # 全域暫停檢查
        if self.global_pause:
            print("🔴 全域暫停中，跳過F3熱鍵")
            self.add_status_message("按下 F3 - 因全域暫停模式而跳過執行", "warning")
            return
            
        self.add_status_message("按下 F3 - 開始執行一鍵清包", "hotkey")
        
        # 重置中斷標誌
        self.inventory_clear_interrupt = False

        if not self.inventory_region or not self.empty_inventory_colors:
            self.add_status_message("F3 執行失敗 - 背包設定不完整", "error")
            messagebox.showwarning("F3 清包提醒", "背包設定不完整！\n\n請先完成以下設定：\n1. 框選背包區域\n2. 記錄淨空顏色")
            return

        # 檢查背包UI是否已設定
        if not self.inventory_ui_region or self.inventory_ui_screenshot is None:
            self.add_status_message("F3 執行失敗 - 背包UI未設定", "error")
            messagebox.showwarning("F3 清包提醒", "背包UI截圖未設定！\n\n請先點擊「框選背包UI」按鈕框選背包區域，\n這樣程式才能判斷背包是否開啟。")
            return

        # 使用血魔監控的遊戲視窗
        window_title = self.window_var.get()
        if not window_title:
            self.add_status_message("F3 執行失敗 - 未設定遊戲視窗", "error")
            messagebox.showwarning("F3 清包提醒", "未設定遊戲視窗！\n\n請先在「血量監控」分頁選擇遊戲視窗。")
            return

        # 檢查遊戲視窗是否處於前台
        if not self.is_game_window_foreground(window_title):
            self.add_status_message("F3 執行取消 - 遊戲視窗不在前台", "warning")
            print(f"F3: 遊戲視窗 '{window_title}' 不在前台，跳過清包操作")
            return

        try:
            # 獲取遊戲視窗
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                self.add_status_message("F3 執行失敗 - 找不到遊戲視窗", "error")
                print("找不到遊戲視窗")
                return

            game_window = windows[0]
            self.add_status_message("F3 執行中 - 已找到遊戲視窗", "info")

            # 首先檢查GUI是否會遮擋背包UI檢測區域或背包區域，如果會則縮小GUI
            gui_minimized_for_ui_check = False
            needs_gui_minimize = False
            
            # 只有在啟用"永遠保持在最上方"時才需要檢查GUI遮擋問題
            if self.always_on_top_var.get():
                # 檢查是否需要縮小GUI（同時檢查背包UI檢測區域和背包區域）
                if hasattr(self, 'inventory_ui_region') and self.inventory_ui_region:
                    if self.check_gui_overlap_with_inventory_ui(game_window):
                        needs_gui_minimize = True
                        print("F3: 檢測到GUI可能遮擋背包UI檢測區域")
                
                if self.check_gui_overlap_with_inventory(game_window):
                    needs_gui_minimize = True
                    print("F3: 檢測到GUI可能遮擋背包區域")
            else:
                print("F3: GUI未設定為永遠保持在最上方，跳過遮擋檢查")
            
            # 如果需要縮小GUI，一次性處理
            if needs_gui_minimize:
                self.add_status_message("F3 執行中 - 縮小GUI避免遮擋", "info")
                print("F3: 正在縮小GUI以避免遮擋...")
                original_state_for_ui_check = self.root.state()
                original_geometry_for_ui_check = self.root.geometry()
                self.root.iconify()
                time.sleep(0.2)
                gui_minimized_for_ui_check = True
                print("F3: GUI已縮小")

            # 確保遊戲視窗在前台（無論是否啟用永遠保持在最上方，都需要激活遊戲視窗）
            try:
                game_window.activate()
                time.sleep(0.2)
                self.add_status_message("F3 執行中 - 遊戲視窗已激活", "info")
                print("F3: 遊戲視窗已激活")
            except Exception as e:
                print(f"F3: 激活遊戲視窗失敗: {e}")
                # 如果激活失敗，嘗試點擊視窗
                try:
                    pyautogui.click(game_window.left + game_window.width // 2, 
                                  game_window.top + game_window.height // 2)
                    time.sleep(0.2)
                    self.add_status_message("F3 執行中 - 嘗試點擊激活遊戲視窗", "info")
                    print("F3: 已嘗試點擊遊戲視窗")
                except Exception as e2:
                    self.add_status_message("F3 執行警告 - 無法激活遊戲視窗", "warning")
                    print(f"F3: 點擊遊戲視窗也失敗: {e2}")

            # 檢查背包UI是否可見（GUI已縮小或遊戲視窗已激活，不會被遮擋）
            if not self.is_inventory_ui_visible(game_window):
                print("F3: 背包UI未開啟，跳過清包操作")
                self.add_status_message("F3 執行取消 - 背包UI未開啟", "warning")
                # 如果之前縮小了GUI，需要恢復
                if gui_minimized_for_ui_check:
                    self.root.deiconify()
                    if original_state_for_ui_check == 'zoomed':
                        self.root.state('zoomed')
                    else:
                        self.root.geometry(original_geometry_for_ui_check)
                    time.sleep(0.2)
                    print("F3: GUI已恢復")
                return

            # 如果之前為UI檢測而縮小了GUI，現在恢復它（因為接下來要縮小GUI進行清包）
            if gui_minimized_for_ui_check:
                self.root.deiconify()
                if original_state_for_ui_check == 'zoomed':
                    self.root.state('zoomed')
                else:
                    self.root.geometry(original_geometry_for_ui_check)
                time.sleep(0.2)
                gui_minimized_for_ui_check = False
                print("F3: GUI已恢復以進行背包區域擷取")

            # 檢查GUI是否會遮擋背包區域，如果會則縮小GUI
            if self.check_gui_overlap_with_inventory(game_window):
                print("檢測到GUI可能遮擋背包區域，正在縮小GUI...")
                self.minimize_gui_for_clear(game_window)

            # 擷取背包區域
            with mss.mss() as sct:
                monitor = {
                    "top": game_window.top + self.inventory_region['y'],
                    "left": game_window.left + self.inventory_region['x'],
                    "width": self.inventory_region['width'],
                    "height": self.inventory_region['height']
                }

                screenshot = sct.grab(monitor)
                img = np.array(screenshot)
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

                # 檢查是否需要清空
                needs_clearing, occupied_slots = self.should_clear_inventory(img)
                if needs_clearing:
                    self.add_status_message(f"F3 執行中 - 檢測到 {len(occupied_slots)} 個物品格子", "info")
                    print(f"F3: 檢測到 {len(occupied_slots)} 個格子有物品，正在清空...")
                    self.clear_inventory_item(game_window, img)
                    if self.inventory_clear_interrupt:
                        self.add_status_message("F3 執行取消 - 清包被用戶中斷", "warning")
                        print("F3: 清包被中斷")
                    else:
                        self.add_status_message("F3 執行完成 - 背包已清空", "success")
                        print("F3: 已清空背包物品")
                else:
                    self.add_status_message("F3 執行完成 - 背包已為空狀態", "success")
                    print("F3: 背包已淨空，無需操作")

        except Exception as e:
            self.add_status_message(f"F3 執行失敗 - 發生錯誤: {str(e)}", "error")
            print(f"F3清包錯誤: {e}")
        finally:
            # 確保中斷標誌被重置
            self.inventory_clear_interrupt = False
            # 恢復GUI狀態
            self.restore_gui_after_clear()

    def check_gui_overlap_with_inventory(self, game_window):
        """檢查GUI是否會遮擋背包區域"""
        try:
            if not self.inventory_region:
                return False
            
            # 檢查GUI是否已經最小化，如果最小化則不會遮擋
            if self.root.state() == "iconic":
                return False
            
            # 獲取GUI當前位置和大小
            gui_x = self.root.winfo_x()
            gui_y = self.root.winfo_y()
            gui_width = self.root.winfo_width()
            gui_height = self.root.winfo_height()
            
            # 如果GUI尺寸為0或很小，認為不會遮擋
            if gui_width <= 1 or gui_height <= 1:
                return False
            
            # 計算背包區域在螢幕上的絕對位置
            inventory_left = game_window.left + self.inventory_region['x']
            inventory_top = game_window.top + self.inventory_region['y']
            inventory_right = inventory_left + self.inventory_region['width']
            inventory_bottom = inventory_top + self.inventory_region['height']
            
            # 計算GUI區域
            gui_right = gui_x + gui_width
            gui_bottom = gui_y + gui_height
            
            # 檢查是否有重疊
            overlap_x = max(0, min(gui_right, inventory_right) - max(gui_x, inventory_left))
            overlap_y = max(0, min(gui_bottom, inventory_bottom) - max(gui_y, inventory_top))
            
            # 如果重疊面積超過背包區域的10%，則認為會造成干擾
            overlap_area = overlap_x * overlap_y
            inventory_area = self.inventory_region['width'] * self.inventory_region['height']
            
            overlap_ratio = overlap_area / inventory_area if inventory_area > 0 else 0
            
            return overlap_ratio > 0.1  # 10%重疊閾值
            
        except Exception as e:
            print(f"檢查GUI重疊時發生錯誤: {e}")
            return False

    def check_gui_overlap_with_inventory_ui(self, game_window):
        """檢查GUI是否會遮擋背包UI檢測區域"""
        try:
            if not hasattr(self, 'inventory_ui_region') or not self.inventory_ui_region:
                return False
            
            # 檢查GUI是否已經最小化，如果最小化則不會遮擋
            if self.root.state() == "iconic":
                return False
            
            # 獲取GUI當前位置和大小
            gui_x = self.root.winfo_x()
            gui_y = self.root.winfo_y()
            gui_width = self.root.winfo_width()
            gui_height = self.root.winfo_height()
            
            # 如果GUI尺寸為0或很小，認為不會遮擋
            if gui_width <= 1 or gui_height <= 1:
                return False
            
            # 計算背包UI檢測區域在螢幕上的絕對位置
            ui_left = game_window.left + self.inventory_ui_region['x']
            ui_top = game_window.top + self.inventory_ui_region['y']
            ui_right = ui_left + self.inventory_ui_region['width']
            ui_bottom = ui_top + self.inventory_ui_region['height']
            
            # 計算GUI區域
            gui_right = gui_x + gui_width
            gui_bottom = gui_y + gui_height
            
            # 檢查是否有重疊
            overlap_x = max(0, min(gui_right, ui_right) - max(gui_x, ui_left))
            overlap_y = max(0, min(gui_bottom, ui_bottom) - max(gui_y, ui_top))
            
            # 如果重疊面積超過背包UI區域的5%，則認為會造成干擾
            overlap_area = overlap_x * overlap_y
            ui_area = self.inventory_ui_region['width'] * self.inventory_ui_region['height']
            
            overlap_ratio = overlap_area / ui_area if ui_area > 0 else 0
            
            return overlap_ratio > 0.05  # 5%重疊閾值（比背包區域更敏感）
            
        except Exception as e:
            print(f"檢查GUI與背包UI重疊時發生錯誤: {e}")
            return False

    def minimize_gui_for_clear(self, game_window=None):
        """縮小GUI以避免干擾清包操作"""
        try:
            if self.gui_minimized_for_clear:
                return  # 已經縮小了
            
            # 記錄GUI當前狀態
            self.original_gui_geometry = self.root.geometry()
            self.original_gui_state = self.root.state()
            
            # 臨時移除最小尺寸限制，允許GUI縮小
            self.original_min_size = self.root.minsize()
            self.root.minsize(400, 350)  # 設置允許縮小到500x450的最小尺寸
            
            # 檢查GUI當前是否在前台
            try:
                import win32gui
                
                # 獲取當前前台視窗
                foreground_hwnd = win32gui.GetForegroundWindow()
                current_process_hwnd = win32gui.FindWindow(None, self.root.title())
                
                self.gui_was_foreground_before_minimize = (foreground_hwnd == current_process_hwnd)
                print(f"GUI縮小前是否在前台: {self.gui_was_foreground_before_minimize}")
            except ImportError:
                # 如果沒有win32gui，假設GUI在前台
                self.gui_was_foreground_before_minimize = True
                print("無法檢查GUI前台狀態，假設在前台")
            except Exception as e:
                print(f"檢查GUI前台狀態失敗: {e}")
                self.gui_was_foreground_before_minimize = True
            
            # 獲取螢幕尺寸
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # 計算縮小後的大小 - 確保背包預覽的60格清晰可見
            # 背包預覽需要足夠的空間來顯示10x6的格子佈局
            preview_min_width = 600   # 確保10列格子有足夠寬度
            preview_min_height = 400  # 確保6行格子有足夠高度
            
            # 加上GUI其他控件的空間
            minimized_width = max(preview_min_width, 650)   # 增加寬度確保預覽完整
            minimized_height = max(preview_min_height, 500) # 增加高度確保預覽和控件都可見
            
            # 智能計算位置，避免覆蓋背包區域，並確保背包預覽區域可見
            minimized_x, minimized_y = self.calculate_safe_gui_position_with_preview(
                game_window, minimized_width, minimized_height, screen_width, screen_height)
            
            # 應用新的幾何位置
            new_geometry = f"{minimized_width}x{minimized_height}+{minimized_x}+{minimized_y}"
            self.root.geometry(new_geometry)
            
            # 只有在用戶啟用了永遠在最上方時，才確保視窗在前台
            if self.should_keep_topmost():
                self.root.lift()
                self.root.focus_force()
                print("縮小GUI時保持前台狀態")
            else:
                print("縮小GUI時保持後台狀態")
            
            self.gui_minimized_for_clear = True
            print(f"GUI已縮小到左上角以避免干擾清包操作: {new_geometry}")
            print("背包預覽的60格清晰可見，用戶可以觀察清包進度")
            
        except Exception as e:
            print(f"縮小GUI時發生錯誤: {e}")

    def calculate_safe_gui_position(self, game_window, gui_width, gui_height, screen_width, screen_height):
        """計算GUI的安全位置，避免覆蓋背包區域"""
        try:
            # 如果沒有遊戲視窗或背包區域資訊，使用預設位置
            if not game_window or not hasattr(self, 'inventory_region') or not self.inventory_region:
                return 10, 10
            
            # 計算背包區域在螢幕上的絕對位置
            inventory_left = game_window.left + self.inventory_region['x']
            inventory_top = game_window.top + self.inventory_region['y']
            inventory_right = inventory_left + self.inventory_region['width']
            inventory_bottom = inventory_top + self.inventory_region['height']
            
            # 候選位置：優先順序從高到低
            candidate_positions = [
                (10, 10),  # 左上角
                (screen_width - gui_width - 10, 10),  # 右上角
                (10, screen_height - gui_height - 10),  # 左下角
                (screen_width - gui_width - 10, screen_height - gui_height - 10),  # 右下角
            ]
            
            # 檢查每個候選位置是否會覆蓋背包區域
            for x, y in candidate_positions:
                gui_right = x + gui_width
                gui_bottom = y + gui_height
                
                # 檢查是否有重疊
                overlap_x = max(0, min(gui_right, inventory_right) - max(x, inventory_left))
                overlap_y = max(0, min(gui_bottom, inventory_bottom) - max(y, inventory_top))
                
                # 如果重疊面積很小（小於5%），則認為這個位置是安全的
                overlap_area = overlap_x * overlap_y
                inventory_area = self.inventory_region['width'] * self.inventory_region['height']
                overlap_ratio = overlap_area / inventory_area if inventory_area > 0 else 0
                
                if overlap_ratio < 0.05:  # 5%重疊閾值
                    print(f"選擇安全位置: ({x}, {y})，與背包重疊率: {overlap_ratio:.1%}")
                    return x, y
            
            # 如果所有位置都會嚴重重疊，使用最不重疊的位置
            best_position = (10, 10)
            min_overlap = float('inf')
            
            for x, y in candidate_positions:
                gui_right = x + gui_width
                gui_bottom = y + gui_height
                
                overlap_x = max(0, min(gui_right, inventory_right) - max(x, inventory_left))
                overlap_y = max(0, min(gui_bottom, inventory_bottom) - max(y, inventory_top))
                overlap_area = overlap_x * overlap_y
                
                if overlap_area < min_overlap:
                    min_overlap = overlap_area
                    best_position = (x, y)
            
            print(f"所有位置都會重疊，使用重疊最小的位置: {best_position}")
            return best_position
            
        except Exception as e:
            print(f"計算安全位置時發生錯誤: {e}")
            return 10, 10  # 返回預設位置

    def calculate_safe_gui_position_with_preview(self, game_window, gui_width, gui_height, screen_width, screen_height):
        """計算GUI的安全位置，避免覆蓋背包區域，並確保背包預覽區域可見"""
        try:
            # 如果沒有遊戲視窗或背包區域資訊，使用預設位置
            if not game_window or not hasattr(self, 'inventory_region') or not self.inventory_region:
                return 10, 10
            
            # 計算背包區域在螢幕上的絕對位置
            inventory_left = game_window.left + self.inventory_region['x']
            inventory_top = game_window.top + self.inventory_region['y']
            inventory_right = inventory_left + self.inventory_region['width']
            inventory_bottom = inventory_top + self.inventory_region['height']
            
            # 嘗試找到一個位置，既不覆蓋背包區域，又能讓背包預覽區域可見
            # 優先考慮左上角，因為用戶要求GUI縮小到左上角
            candidate_positions = [
                (10, 10),  # 左上角 - 優先（用戶要求）
                (screen_width - gui_width - 10, 10),  # 右上角
                (10, screen_height - gui_height - 10),  # 左下角
                (screen_width - gui_width - 10, screen_height - gui_height - 10),  # 右下角
            ]
            
            # 檢查每個候選位置
            for x, y in candidate_positions:
                gui_right = x + gui_width
                gui_bottom = y + gui_height
                
                # 檢查是否有重疊
                overlap_x = max(0, min(gui_right, inventory_right) - max(x, inventory_left))
                overlap_y = max(0, min(gui_bottom, inventory_bottom) - max(y, inventory_top))
                
                # 如果重疊面積很小（小於5%），則認為這個位置是安全的
                overlap_area = overlap_x * overlap_y
                inventory_area = self.inventory_region['width'] * self.inventory_region['height']
                overlap_ratio = overlap_area / inventory_area if inventory_area > 0 else 0
                
                if overlap_ratio < 0.08:  # 放寬到8%重疊閾值，確保左上角優先選擇
                    print(f"選擇安全位置（考慮預覽）: ({x}, {y})，與背包重疊率: {overlap_ratio:.1%}")
                    return x, y
            
            # 如果所有位置都會嚴重重疊，使用最不重疊的位置（優先左上角）
            best_position = (10, 10)  # 預設為左上角
            min_overlap = float('inf')
            
            for x, y in candidate_positions:
                gui_right = x + gui_width
                gui_bottom = y + gui_height
                
                overlap_x = max(0, min(gui_right, inventory_right) - max(x, inventory_left))
                overlap_y = max(0, min(gui_bottom, inventory_bottom) - max(y, inventory_top))
                overlap_area = overlap_x * overlap_y
                
                if overlap_area < min_overlap:
                    min_overlap = overlap_area
                    best_position = (x, y)
            
            print(f"所有位置都會重疊，使用重疊最小的位置（考慮預覽）: {best_position}")
            return best_position
            
        except Exception as e:
            print(f"計算考慮預覽的安全位置時發生錯誤: {e}")
            return 10, 10  # 返回左上角作為預設位置

    def restore_gui_after_clear(self):
        """恢復GUI到原始狀態"""
        try:
            if not self.gui_minimized_for_clear:
                return  # 沒有被縮小
            
            if self.original_gui_geometry:
                self.root.geometry(self.original_gui_geometry)
            
            if self.original_gui_state:
                self.root.state(self.original_gui_state)
            
            # 恢復原始的最小尺寸限制
            if hasattr(self, 'original_min_size') and self.original_min_size:
                self.root.minsize(self.original_min_size[0], self.original_min_size[1])
            
            # 只有在用戶啟用了永遠在最上方且GUI縮小前就在前台的情況下，才重新激活GUI
            if self.should_keep_topmost() and self.gui_was_foreground_before_minimize:
                self.root.lift()
                self.root.focus_force()
                print("GUI已恢復到原始狀態並重新激活")
            else:
                print("GUI已恢復到原始狀態，保持後台狀態")
            
            self.gui_minimized_for_clear = False
            self.original_gui_geometry = None
            self.original_gui_state = None
            self.gui_was_foreground_before_minimize = True  # 重置為預設值
            
        except Exception as e:
            print(f"恢復GUI時發生錯誤: {e}")

    def minimize_all_guis(self):
        """縮小所有GUI以避免干擾螢幕截圖操作"""
        try:
            # 簡單地將主GUI最小化
            self.root.iconify()
            print("GUI已縮小以避免干擾螢幕截圖")
        except Exception as e:
            print(f"縮小GUI時發生錯誤: {e}")

    def restore_all_guis(self):
        """恢復所有GUI到正常狀態"""
        try:
            # 恢復主GUI
            self.root.deiconify()
            print("GUI已恢復")
        except Exception as e:
            print(f"恢復GUI時發生錯誤: {e}")

    def create_inventory_tab(self):
        """創建一鍵清包分頁"""
        # 主框架
        main_frame = self.inventory_frame

        # 創建左右分欄佈局
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))

        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # 設定列寬 - 調整左右比例，讓右側預覽區域更大
        main_frame.columnconfigure(0, weight=1)  # 左側控制面板
        main_frame.columnconfigure(1, weight=2)  # 右側預覽區域 (更大的權重)
        main_frame.rowconfigure(0, weight=1)

        # === 左側區域：控制面板 ===
        # 背包設定區域
        inventory_frame = ttk.LabelFrame(left_frame, text="背包設定", padding="15")
        inventory_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))

        # 框選背包區域
        ttk.Button(inventory_frame, text="📦 框選背包區域", command=self.select_inventory_region).grid(row=0, column=0, pady=2)
        ttk.Button(inventory_frame, text="🎨 記錄淨空顏色", command=self.record_empty_inventory_color).grid(row=0, column=1, padx=(10, 0), pady=2)
        ttk.Button(inventory_frame, text="🖼️ 框選背包UI", command=self.select_inventory_ui_region).grid(row=0, column=2, padx=(10, 0), pady=2)

        # 顏色顯示
        ttk.Label(inventory_frame, text="記錄狀態:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.empty_color_label = ttk.Label(inventory_frame, text="尚未記錄", background="lightgray", relief="sunken")
        self.empty_color_label.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 0))

        # 背包UI顯示
        ttk.Label(inventory_frame, text="背包UI狀態:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.inventory_ui_label = ttk.Label(inventory_frame, text="尚未記錄", background="lightgray", relief="sunken")
        self.inventory_ui_label.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 0))

        # 控制按鈕
        control_frame = ttk.LabelFrame(left_frame, text="控制面板", padding="15")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))

        ttk.Button(control_frame, text="🔄 測試清包", command=self.test_inventory_clearing).grid(row=0, column=0, pady=2)
        ttk.Button(control_frame, text="💾 儲存設定", command=self.save_inventory_config).grid(row=0, column=1, padx=(10, 0), pady=2)

        # GUI設定選項
        gui_control_frame = ttk.Frame(control_frame)
        gui_control_frame.grid(row=1, column=0, columnspan=2, pady=(10, 0))

        ttk.Label(gui_control_frame, text="GUI設定:").grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(gui_control_frame, text="永遠保持在最上方", variable=self.always_on_top_var, 
                       command=self.toggle_always_on_top).grid(row=0, column=1, columnspan=2, sticky=tk.W, padx=(5, 0))

        # 狀態顯示
        status_frame = ttk.LabelFrame(left_frame, text="狀態", padding="15")
        status_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))

        ttk.Label(status_frame, text="F3熱鍵:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.inventory_status_label = ttk.Label(status_frame, text="就緒", foreground="green")
        self.inventory_status_label.grid(row=0, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        ttk.Label(status_frame, text="全域暫停:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.pause_status_label = ttk.Label(status_frame, text="🟢 正常運行", foreground="green")
        self.pause_status_label.grid(row=1, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        # F6取物座標設定
        pickup_frame = ttk.LabelFrame(left_frame, text="F6取物座標", padding="10")
        pickup_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        # 座標設定按鈕
        ttk.Button(pickup_frame, text="⚙️ 設定取物座標", command=self.setup_pickup_coordinates).grid(row=0, column=0, pady=2)
        ttk.Button(pickup_frame, text="💾 儲存座標", command=self.save_pickup_coordinates).grid(row=0, column=1, padx=(10, 0), pady=2)

        # 座標狀態顯示
        ttk.Label(pickup_frame, text="已設定座標:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.pickup_coords_label = ttk.Label(pickup_frame, text="0/5", foreground="gray")
        self.pickup_coords_label.grid(row=1, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        # F6狀態顯示
        ttk.Label(pickup_frame, text="F6熱鍵:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.pickup_status_label = ttk.Label(pickup_frame, text="就緒", foreground="green")
        self.pickup_status_label.grid(row=2, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        # UI截圖顯示區域
        ui_preview_frame = ttk.LabelFrame(left_frame, text="背包UI截圖", padding="10")
        ui_preview_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        # 創建一個Canvas來顯示UI截圖
        self.ui_preview_canvas = tk.Canvas(ui_preview_frame, width=200, height=150, bg='lightgray', relief='sunken')
        self.ui_preview_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E))

        # 添加說明文字
        ttk.Label(ui_preview_frame, text="當您框選背包UI後，截圖將顯示在上面", 
                 font=("", 8), foreground="gray").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))

        # === 右側區域：背包預覽 ===
        # 背包預覽區域
        preview_frame = ttk.LabelFrame(right_frame, text="背包預覽", padding="10")
        preview_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 統計資訊區域
        stats_frame = ttk.Frame(preview_frame)
        stats_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))

        ttk.Label(stats_frame, text="占用格子:").grid(row=0, column=0, sticky=tk.W)
        self.occupied_label = ttk.Label(stats_frame, text="0/60", foreground="blue", font=("", 10, "bold"))
        self.occupied_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        # 偏移調整區域
        offset_frame = ttk.Frame(preview_frame)
        offset_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))

        ttk.Label(offset_frame, text="格子對齊調整:").grid(row=0, column=0, sticky=tk.W, pady=(0, 2))

        # 水平偏移調整
        ttk.Label(offset_frame, text="水平:").grid(row=1, column=0, sticky=tk.W)
        ttk.Button(offset_frame, text="◀", width=3, command=lambda: self.adjust_grid_offset(-1, 0)).grid(row=1, column=1, padx=(5, 2))
        self.offset_x_label = ttk.Label(offset_frame, text="0", width=4, relief="sunken")
        self.offset_x_label.grid(row=1, column=2, padx=(2, 2))
        ttk.Button(offset_frame, text="▶", width=3, command=lambda: self.adjust_grid_offset(1, 0)).grid(row=1, column=3, padx=(2, 10))

        # 垂直偏移調整
        ttk.Label(offset_frame, text="垂直:").grid(row=1, column=4, sticky=tk.W)
        ttk.Button(offset_frame, text="▲", width=3, command=lambda: self.adjust_grid_offset(0, -1)).grid(row=1, column=5, padx=(5, 2))
        self.offset_y_label = ttk.Label(offset_frame, text="0", width=4, relief="sunken")
        self.offset_y_label.grid(row=1, column=6, padx=(2, 2))
        ttk.Button(offset_frame, text="▼", width=3, command=lambda: self.adjust_grid_offset(0, 1)).grid(row=1, column=7, padx=(2, 5))

        ttk.Button(offset_frame, text="重置", command=self.reset_grid_offset).grid(row=1, column=8, padx=(10, 0))

        self.inventory_preview_label = ttk.Label(preview_frame, text="請先框選背包區域", relief="sunken", background="lightgray")
        self.inventory_preview_label.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))

        # 設定預覽區域大小
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(2, weight=1)  # 預覽圖片區域
        right_frame.rowconfigure(0, weight=1)

        # 初始化偏移標籤
        self.update_offset_labels()

        # 初始化變數
        self.last_inventory_update = 0

    def adjust_grid_offset(self, delta_x, delta_y):
        """調整格子偏移"""
        self.grid_offset_x += delta_x
        self.grid_offset_y += delta_y

        # 限制偏移範圍
        max_offset = 20
        self.grid_offset_x = max(-max_offset, min(max_offset, self.grid_offset_x))
        self.grid_offset_y = max(-max_offset, min(max_offset, self.grid_offset_y))

        # 更新標籤顯示
        self.update_offset_labels()

        # 重新計算格子位置
        if self.inventory_region:
            self.inventory_grid_positions = self.calculate_inventory_grid_positions()

        # 如果有預覽圖片，立即更新
        if hasattr(self, 'inventory_preview_label') and self.inventory_preview_label.cget('text') != "請先框選背包區域":
            # 重新獲取當前背包圖片並更新預覽
            self.update_inventory_preview_from_current()

        # 初始化UI預覽
        self.update_ui_preview()

    def reset_grid_offset(self):
        """重置格子偏移"""
        self.grid_offset_x = 0
        self.grid_offset_y = 0
        self.update_offset_labels()

        # 重新計算格子位置
        if self.inventory_region:
            self.inventory_grid_positions = self.calculate_inventory_grid_positions()

        # 如果有預覽圖片，立即更新
        if hasattr(self, 'inventory_preview_label') and self.inventory_preview_label.cget('text') != "請先框選背包區域":
            self.update_inventory_preview_from_current()

    def update_offset_labels(self):
        """更新偏移標籤顯示"""
        if hasattr(self, 'offset_x_label'):
            self.offset_x_label.config(text=str(self.grid_offset_x))
        if hasattr(self, 'offset_y_label'):
            self.offset_y_label.config(text=str(self.grid_offset_y))

    def calculate_inventory_grid_positions(self):
        """計算背包格子位置 (5x12 布局，總共60個格子)"""
        if not self.inventory_region:
            return []

        # 背包區域的尺寸
        region_width = self.inventory_region['width']
        region_height = self.inventory_region['height']
        region_x = self.inventory_region['x']
        region_y = self.inventory_region['y']

        # 5x12 布局的格子數量 (5行12列)
        cols = 12  # 12列
        rows = 5   # 5行

        # 計算每個格子的寬度和高度
        cell_width = region_width / cols
        cell_height = region_height / rows

        # 計算格子位置
        positions = []
        for row in range(rows):
            for col in range(cols):
                # 計算格子中心點的相對位置
                center_x = (col + 0.5) * cell_width + self.grid_offset_x
                center_y = (row + 0.5) * cell_height + self.grid_offset_y

                # 轉換為絕對座標（遊戲視窗內的座標）
                abs_x = int(region_x + center_x)
                abs_y = int(region_y + center_y)

                positions.append((abs_x, abs_y))

        return positions

    def update_inventory_preview_from_current(self):
        """從當前背包區域重新獲取圖片並更新預覽"""
        try:
            # 使用血魔監控的遊戲視窗
            window_title = self.window_var.get()
            if not window_title:
                return

            # 獲取遊戲視窗
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                return

            game_window = windows[0]

            # 擷取背包區域
            with mss.mss() as sct:
                monitor = {
                    "top": game_window.top + self.inventory_region['y'],
                    "left": game_window.left + self.inventory_region['x'],
                    "width": self.inventory_region['width'],
                    "height": self.inventory_region['height']
                }

                screenshot = sct.grab(monitor)
                img = np.array(screenshot)
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

                # 分析背包狀態
                should_clear, occupied_slots = self.should_clear_inventory(img)

                # 更新預覽
                self.update_inventory_preview_with_items(img, occupied_slots)

        except Exception as e:
            print(f"重新獲取預覽失敗: {e}")

    def select_inventory_region(self):
        """框選背包區域"""
        # 使用血魔監控的遊戲視窗
        window_title = self.window_var.get()
        if not window_title:
            messagebox.showwarning("警告", "請先在血魔監控分頁設定遊戲視窗")
            return

        try:
            # 獲取遊戲視窗
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                messagebox.showerror("錯誤", "找不到指定的遊戲視窗")
                return

            game_window = windows[0]

            # 自動激活遊戲視窗（參考血魔監控的邏輯）
            game_window.activate()
            time.sleep(0.1)  # 等待視窗激活

            # 框選時降低透明度但保持置頂，讓用戶能看到GUI但遊戲視窗可以操作
            self.root.attributes("-alpha", 0.6)  # 降低透明度
            self.root.attributes("-topmost", True)  # 保持置頂但不搶焦點
            self.root.lift()

            # 創建覆蓋遊戲視窗的選擇視窗（參考血魔監控的邏輯）
            self.create_inventory_selection_window(game_window)

        except Exception as e:
            messagebox.showerror("錯誤", f"框選失敗: {str(e)}")
            self.root.deiconify()

    def create_inventory_selection_window(self, game_window):
        """創建背包區域選擇視窗（參考血魔監控邏輯）"""
        # 創建覆蓋遊戲視窗的選擇視窗（參考血魔監控的邏輯）（子視窗 - 最高層級）
        self.inventory_selection_window = self.create_child_window("", f"{game_window.width}x{game_window.height}")
        self.inventory_selection_window.geometry(f"+{game_window.left}+{game_window.top}")
        self.inventory_selection_window.attributes("-alpha", 0.3)
        self.inventory_selection_window.overrideredirect(True)  # 移除視窗邊框
        self.inventory_selection_window.configure(bg='gray')

        # 繪製遊戲視窗邊框
        canvas = tk.Canvas(self.inventory_selection_window, bg='gray', highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        # 繪製說明文字
        self.selection_text_id = canvas.create_text(game_window.width//2, game_window.height//2,
                          text="請拖曳框選背包區域\n右鍵或按ESC取消",
                          fill="white", font=("Arial", 14, "bold"),
                          anchor="center")

        # 綁定事件
        canvas.bind("<ButtonPress-1>", self.start_inventory_selection)
        canvas.bind("<B1-Motion>", self.update_inventory_selection)
        canvas.bind("<ButtonRelease-1>", self.end_inventory_selection)

        # 綁定右鍵取消
        canvas.bind("<Button-3>", self.cancel_inventory_selection)

        # 綁定ESC鍵取消
        self.inventory_selection_window.bind("<Escape>", self.cancel_inventory_selection)
        self.inventory_selection_window.focus_set()  # 確保selection_window能接收鍵盤事件

        # 確保canvas可以接收滑鼠事件
        canvas.focus_set()

    def start_inventory_selection(self, event):
        """開始背包區域選擇"""
        self.inventory_selection_active = True
        self.inventory_selection_start = (event.x, event.y)
        self.inventory_selection_end = (event.x, event.y)

        # 清除之前的選擇區域和隱藏說明文字
        canvas = event.widget
        canvas.delete("selection")
        if hasattr(self, 'selection_text_id'):
            canvas.itemconfig(self.selection_text_id, state='hidden')

    def update_inventory_selection(self, event):
        """更新背包區域選擇"""
        if self.inventory_selection_active:
            self.inventory_selection_end = (event.x, event.y)
            # 重新繪製選擇區域
            try:
                canvas = event.widget
                canvas.delete("selection")
                x1, y1 = self.inventory_selection_start
                x2, y2 = self.inventory_selection_end
                canvas.create_rectangle(x1, y1, x2, y2, outline='yellow', width=2, tags="selection")
            except Exception as e:
                print(f"更新選擇區域失敗: {e}")

    def end_inventory_selection(self, event):
        """結束背包區域選擇（參考血魔監控邏輯）"""
        if self.inventory_selection_active and self.inventory_selection_start and self.inventory_selection_end:
            self.inventory_selection_active = False

            # 獲取遊戲視窗資訊
            window_title = self.window_var.get()
            windows = gw.getWindowsWithTitle(window_title)
            if windows:
                game_window = windows[0]

                x1, y1 = self.inventory_selection_start
                x2, y2 = self.inventory_selection_end

                # 確保選擇區域有足夠的大小
                if abs(x2 - x1) < 10 or abs(y2 - y1) < 10:
                    messagebox.showwarning("警告", "選擇區域太小，請重新選擇")
                    self.cancel_inventory_selection()
                    return

                # 轉換為遊戲視窗內的相對座標
                rel_x1 = max(0, x1)
                rel_y1 = max(0, y1)
                rel_x2 = max(0, x2)
                rel_y2 = max(0, y2)

                # 確保在遊戲視窗範圍內
                rel_x2 = min(rel_x2, game_window.width)
                rel_y2 = min(rel_y2, game_window.height)

                self.inventory_region = {
                    'x': min(rel_x1, rel_x2),
                    'y': min(rel_y1, rel_y2),
                    'width': abs(rel_x2 - rel_x1),
                    'height': abs(rel_y2 - rel_y1)
                }

                messagebox.showinfo("成功", f"背包區域已設定:\n座標: ({self.inventory_region['x']}, {self.inventory_region['y']})\n大小: {self.inventory_region['width']}x{self.inventory_region['height']}")

            self.inventory_selection_window.destroy()

            # 重新激活主視窗並恢復正常狀態（參考血魔監控邏輯）
            self.root.attributes("-alpha", 1.0)  # 恢復完全不透明
            self.root.attributes("-topmost", True)  # 恢復置頂
            self.root.lift()
            self.root.focus_force()
        else:
            # 如果沒有有效的選擇，取消選擇
            self.cancel_inventory_selection()

    def cancel_inventory_selection(self, event=None):
        """取消背包區域選擇（參考血魔監控邏輯）"""
        # 重置選擇狀態
        self.inventory_selection_active = False
        self.inventory_selection_start = None
        self.inventory_selection_end = None

        if hasattr(self, 'inventory_selection_window'):
            self.inventory_selection_window.destroy()

        # 重新激活主視窗並恢復正常狀態（參考血魔監控邏輯）
        self.root.attributes("-alpha", 1.0)  # 恢復完全不透明
        self.root.attributes("-topmost", True)  # 恢復置頂
        self.root.lift()
        self.root.focus_force()

    def record_empty_inventory_color(self):
        """記錄淨空背包的60個格子顏色"""
        if not self.inventory_region:
            messagebox.showwarning("警告", "請先框選背包區域")
            return

        # 使用血魔監控的遊戲視窗
        window_title = self.window_var.get()
        if not window_title:
            messagebox.showwarning("警告", "請先在血魔監控分頁設定遊戲視窗")
            return

        try:
            # 縮小GUI並激活遊戲視窗，避免GUI遮擋
            self.minimize_all_guis()
            time.sleep(0.5)  # 等待GUI縮小

            # 獲取遊戲視窗
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                messagebox.showerror("錯誤", "找不到指定的遊戲視窗")
                return

            game_window = windows[0]
            
            # 激活遊戲視窗
            game_window.activate()
            time.sleep(0.5)  # 等待視窗激活
            print("已縮小GUI並激活遊戲視窗，準備記錄顏色")

            # 計算格子位置
            self.inventory_grid_positions = self.calculate_inventory_grid_positions()
            if not self.inventory_grid_positions:
                messagebox.showerror("錯誤", "無法計算格子位置")
                return

            # 擷取整個背包區域
            with mss.mss() as sct:
                monitor = {
                    "top": game_window.top + self.inventory_region['y'],
                    "left": game_window.left + self.inventory_region['x'],
                    "width": self.inventory_region['width'],
                    "height": self.inventory_region['height']
                }

                screenshot = sct.grab(monitor)
                img = np.array(screenshot)
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

                # 記錄60個格子的顏色
                self.empty_inventory_colors = []
                for pos_x, pos_y in self.inventory_grid_positions:
                    # 確保座標在圖片範圍內
                    img_x = pos_x - self.inventory_region['x']
                    img_y = pos_y - self.inventory_region['y']

                    if 0 <= img_x < img.shape[1] and 0 <= img_y < img.shape[0]:
                        # 獲取5x5區域的平均顏色以獲得更穩定的結果（從3x3增加到5x5）
                        x1 = max(0, img_x - 2)
                        y1 = max(0, img_y - 2)
                        x2 = min(img.shape[1], img_x + 3)
                        y2 = min(img.shape[0], img_y + 3)

                        cell_pixels = img[y1:y2, x1:x2]
                        if cell_pixels.size > 0:
                            avg_color = np.mean(cell_pixels, axis=(0, 1))
                            rgb_color = (int(avg_color[2]), int(avg_color[1]), int(avg_color[0]))  # BGR to RGB
                            self.empty_inventory_colors.append(rgb_color)
                        else:
                            self.empty_inventory_colors.append((0, 0, 0))  # 預設黑色
                    else:
                        self.empty_inventory_colors.append((0, 0, 0))  # 預設黑色

                # 更新顯示
                recorded_count = len([c for c in self.empty_inventory_colors if c != (0, 0, 0)])
                self.empty_color_label.config(text=f"已記錄 {recorded_count}/60 格顏色", background="lightgreen")

                # 恢復主GUI視窗
                self.restore_all_guis()
                print("顏色記錄完成，已恢復GUI視窗")

                messagebox.showinfo("成功", f"淨空顏色已記錄，共 {recorded_count} 個格子")

        except Exception as e:
            # 如果發生錯誤，也要恢復GUI視窗
            self.restore_all_guis()
            messagebox.showerror("錯誤", f"記錄顏色失敗: {str(e)}")

    def select_inventory_ui_region(self):
        """框選背包UI區域"""
        # 使用血魔監控的遊戲視窗
        window_title = self.window_var.get()
        if not window_title:
            messagebox.showwarning("警告", "請先在血魔監控分頁設定遊戲視窗")
            return

        try:
            # 獲取遊戲視窗
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                messagebox.showerror("錯誤", "找不到指定的遊戲視窗")
                return

            game_window = windows[0]

            # 設置選擇狀態
            self.inventory_ui_selection_active = True
            
            # 設置全局ESC監聽
            self.setup_global_esc_listener_for_inventory()

            # 自動激活遊戲視窗
            game_window.activate()
            time.sleep(0.1)  # 等待視窗激活

            # 框選時降低透明度但保持置頂，讓用戶能看到GUI但遊戲視窗可以操作
            self.root.attributes("-alpha", 0.6)  # 降低透明度
            self.root.attributes("-topmost", True)  # 保持置頂但不搶焦點
            self.root.lift()

            # 創建覆蓋遊戲視窗的選擇視窗
            self.create_inventory_ui_selection_window(game_window)

        except Exception as e:
            messagebox.showerror("錯誤", f"框選失敗: {str(e)}")
            self.root.deiconify()

    def select_interface_ui_region(self):
        """框選介面UI區域"""
        # 使用血魔監控的遊戲視窗
        window_title = self.window_var.get()
        if not window_title:
            messagebox.showwarning("警告", "請先在血魔監控分頁設定遊戲視窗")
            return

        try:
            # 獲取遊戲視窗
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                messagebox.showerror("錯誤", "找不到指定的遊戲視窗")
                return

            game_window = windows[0]

            # 設置選擇狀態
            self.interface_ui_selection_active = True
            
            # 設置全局ESC監聽
            self.setup_global_esc_listener_for_interface()

            # 自動激活遊戲視窗
            game_window.activate()
            time.sleep(0.1)  # 等待視窗激活

            # 框選時降低透明度但保持置頂，讓用戶能看到GUI但遊戲視窗可以操作
            self.root.attributes("-alpha", 0.6)  # 降低透明度
            self.root.attributes("-topmost", True)  # 保持置頂但不搶焦點
            self.root.lift()

            # 創建覆蓋遊戲視窗的選擇視窗
            self.create_interface_ui_selection_window(game_window)

        except Exception as e:
            messagebox.showerror("錯誤", f"框選失敗: {str(e)}")
            self.root.deiconify()

    def create_inventory_ui_selection_window(self, game_window):
        """創建背包UI區域選擇視窗"""
        # 創建覆蓋遊戲視窗的選擇視窗（子視窗 - 最高層級）
        self.inventory_ui_selection_window = self.create_child_window("", f"{game_window.width}x{game_window.height}")
        self.inventory_ui_selection_window.geometry(f"+{game_window.left}+{game_window.top}")
        self.inventory_ui_selection_window.attributes("-alpha", 0.3)
        self.inventory_ui_selection_window.overrideredirect(True)  # 移除視窗邊框
        self.inventory_ui_selection_window.configure(bg='gray')

        # 繪製遊戲視窗邊框
        canvas = tk.Canvas(self.inventory_ui_selection_window, bg='gray', highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        # 繪製說明文字
        self.ui_selection_text_id = canvas.create_text(game_window.width//2, game_window.height//2,
                          text="請拖曳框選背包UI區域\n右鍵或按ESC取消",
                          fill="white", font=("Arial", 14, "bold"),
                          anchor="center")

        # 綁定事件
        canvas.bind("<ButtonPress-1>", self.start_inventory_ui_selection)
        canvas.bind("<B1-Motion>", self.update_inventory_ui_selection)
        canvas.bind("<ButtonRelease-1>", self.end_inventory_ui_selection)

        # 綁定右鍵取消
        canvas.bind("<Button-3>", self.cancel_inventory_ui_selection)

        # 全局ESC監聽已在select_inventory_ui_region中設置，這裡不需要重複設置

        # 確保canvas可以接收滑鼠事件
        canvas.focus_set()

    def create_interface_ui_selection_window(self, game_window):
        """創建介面UI區域選擇視窗"""
        # 創建覆蓋遊戲視窗的選擇視窗（子視窗 - 最高層級）
        self.interface_ui_selection_window = self.create_child_window("", f"{game_window.width}x{game_window.height}")
        self.interface_ui_selection_window.geometry(f"+{game_window.left}+{game_window.top}")
        self.interface_ui_selection_window.attributes("-alpha", 0.3)
        self.interface_ui_selection_window.overrideredirect(True)  # 移除視窗邊框
        self.interface_ui_selection_window.configure(bg='gray')

        # 繪製遊戲視窗邊框
        canvas = tk.Canvas(self.interface_ui_selection_window, bg='gray', highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        # 繪製說明文字
        self.interface_ui_selection_text_id = canvas.create_text(game_window.width//2, game_window.height//2,
                          text="請拖曳框選介面UI區域\n右鍵或按ESC取消",
                          fill="white", font=("Arial", 14, "bold"),
                          anchor="center")

        # 綁定事件
        canvas.bind("<ButtonPress-1>", self.start_interface_ui_selection)
        canvas.bind("<B1-Motion>", self.update_interface_ui_selection)
        canvas.bind("<ButtonRelease-1>", self.end_interface_ui_selection)

        # 綁定右鍵取消
        canvas.bind("<Button-3>", self.cancel_interface_ui_selection)

        # 全局ESC監聽已在select_interface_ui_region中設置，這裡不需要重複設置

        # 確保canvas可以接收滑鼠事件
        canvas.focus_set()

    def start_inventory_ui_selection(self, event):
        """開始背包UI區域選擇"""
        self.inventory_ui_selection_active = True
        self.inventory_ui_selection_start = (event.x, event.y)
        self.inventory_ui_selection_end = (event.x, event.y)

        # 清除之前的選擇區域和隱藏說明文字
        canvas = event.widget
        canvas.delete("selection")
        if hasattr(self, 'ui_selection_text_id'):
            canvas.itemconfig(self.ui_selection_text_id, state='hidden')

    def update_inventory_ui_selection(self, event):
        """更新背包UI區域選擇"""
        if self.inventory_ui_selection_active:
            self.inventory_ui_selection_end = (event.x, event.y)
            # 重新繪製選擇區域
            try:
                canvas = event.widget
                canvas.delete("selection")
                x1, y1 = self.inventory_ui_selection_start
                x2, y2 = self.inventory_ui_selection_end
                canvas.create_rectangle(x1, y1, x2, y2, outline='yellow', width=2, tags="selection")
            except Exception as e:
                print(f"更新選擇區域失敗: {e}")

    def end_inventory_ui_selection(self, event):
        """結束背包UI區域選擇"""
        if self.inventory_ui_selection_active and self.inventory_ui_selection_start and self.inventory_ui_selection_end:
            self.inventory_ui_selection_active = False

            # 獲取遊戲視窗資訊
            window_title = self.window_var.get()
            windows = gw.getWindowsWithTitle(window_title)
            if windows:
                game_window = windows[0]

                x1, y1 = self.inventory_ui_selection_start
                x2, y2 = self.inventory_ui_selection_end

                # 確保選擇區域有足夠的大小
                if abs(x2 - x1) < 10 or abs(y2 - y1) < 10:
                    messagebox.showwarning("警告", "選擇區域太小，請重新選擇")
                    self.cancel_inventory_ui_selection()
                    return

                # 轉換為遊戲視窗內的相對座標
                rel_x1 = max(0, x1)
                rel_y1 = max(0, y1)
                rel_x2 = max(0, x2)
                rel_y2 = max(0, y2)

                # 確保在遊戲視窗範圍內
                rel_x2 = min(rel_x2, game_window.width)
                rel_y2 = min(rel_y2, game_window.height)

                self.inventory_ui_region = {
                    'x': min(rel_x1, rel_x2),
                    'y': min(rel_y1, rel_y2),
                    'width': abs(rel_x2 - rel_x1),
                    'height': abs(rel_y2 - rel_y1)
                }

                # 截取背包UI區域的圖片 - 使用血魔檢測的方式
                try:
                    # 計算絕對螢幕座標
                    abs_x = game_window.left + self.inventory_ui_region['x']
                    abs_y = game_window.top + self.inventory_ui_region['y']

                    with mss.mss() as sct:
                        monitor = {
                            "top": abs_y,
                            "left": abs_x,
                            "width": self.inventory_ui_region['width'],
                            "height": self.inventory_ui_region['height']
                        }

                        screenshot = sct.grab(monitor)
                        # 使用PIL Image方式，如同血魔檢測
                        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

                        # 創建screenshots目錄（如果不存在）
                        screenshot_dir = os.path.join(get_app_dir(), "screenshots")
                        os.makedirs(screenshot_dir, exist_ok=True)

                        # 直接保存PIL圖片為PNG
                        ui_screenshot_path = os.path.join(screenshot_dir, "inventory_ui.png")
                        img.save(ui_screenshot_path)
                        print(f"UI截圖已保存到: {ui_screenshot_path}")

                        # 將PIL圖片轉換為OpenCV格式用於後續處理
                        self.inventory_ui_screenshot = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

                        # 更新UI顯示
                        self.inventory_ui_label.config(text="已記錄背包UI", background="lightgreen")

                        # 更新UI預覽
                        self.update_ui_preview()

                        messagebox.showinfo("成功", f"背包UI區域已設定並截圖:\n座標: ({self.inventory_ui_region['x']}, {self.inventory_ui_region['y']})\n大小: {self.inventory_ui_region['width']}x{self.inventory_ui_region['height']}")

                except Exception as e:
                    messagebox.showerror("錯誤", f"截圖失敗: {str(e)}")
                    print(f"詳細錯誤: {e}")
                    import traceback
                    traceback.print_exc()

            self.inventory_ui_selection_window.destroy()

            # 重新激活主視窗並恢復正常狀態
            self.root.attributes("-alpha", 1.0)  # 恢復完全不透明
            self.root.attributes("-topmost", True)  # 恢復置頂
            self.root.lift()
            self.root.focus_force()
        else:
            # 如果沒有有效的選擇，取消選擇
            self.cancel_inventory_ui_selection()

    def cancel_inventory_ui_selection(self, event=None):
        """取消背包UI區域選擇"""
        # 重置選擇狀態
        self.inventory_ui_selection_active = False
        self.inventory_ui_selection_start = None
        self.inventory_ui_selection_end = None

        # 移除全局ESC監聽
        self.remove_global_esc_listener_for_inventory()

        if hasattr(self, 'inventory_ui_selection_window'):
            self.inventory_ui_selection_window.destroy()

        # 重新激活主視窗並恢復正常狀態
        self.root.attributes("-alpha", 1.0)  # 恢復完全不透明
        self.root.attributes("-topmost", True)  # 恢復置頂
        self.root.lift()
        self.root.focus_force()

    def start_interface_ui_selection(self, event):
        """開始介面UI區域選擇"""
        self.interface_ui_selection_active = True
        self.interface_ui_selection_start = (event.x, event.y)
        self.interface_ui_selection_end = (event.x, event.y)

        # 清除之前的選擇區域和隱藏說明文字
        canvas = event.widget
        canvas.delete("selection")
        if hasattr(self, 'interface_ui_selection_text_id'):
            canvas.itemconfig(self.interface_ui_selection_text_id, state='hidden')

    def update_interface_ui_selection(self, event):
        """更新介面UI區域選擇"""
        if self.interface_ui_selection_active:
            self.interface_ui_selection_end = (event.x, event.y)
            # 重新繪製選擇區域
            try:
                canvas = event.widget
                canvas.delete("selection")
                x1, y1 = self.interface_ui_selection_start
                x2, y2 = self.interface_ui_selection_end
                canvas.create_rectangle(x1, y1, x2, y2, outline='yellow', width=2, tags="selection")
            except Exception as e:
                print(f"更新選擇區域失敗: {e}")

    def end_interface_ui_selection(self, event):
        """結束介面UI區域選擇"""
        if self.interface_ui_selection_active and self.interface_ui_selection_start and self.interface_ui_selection_end:
            self.interface_ui_selection_active = False

            # 獲取遊戲視窗資訊
            window_title = self.window_var.get()
            windows = gw.getWindowsWithTitle(window_title)
            if windows:
                game_window = windows[0]

                x1, y1 = self.interface_ui_selection_start
                x2, y2 = self.interface_ui_selection_end

                # 確保選擇區域有足夠的大小
                if abs(x2 - x1) < 10 or abs(y2 - y1) < 10:
                    messagebox.showwarning("警告", "選擇區域太小，請重新選擇")
                    self.cancel_interface_ui_selection()
                    return

                # 轉換為遊戲視窗內的相對座標
                rel_x1 = max(0, x1)
                rel_y1 = max(0, y1)
                rel_x2 = max(0, x2)
                rel_y2 = max(0, y2)

                # 確保在遊戲視窗範圍內
                rel_x2 = min(rel_x2, game_window.width)
                rel_y2 = min(rel_y2, game_window.height)

                self.interface_ui_region = {
                    'x': min(rel_x1, rel_x2),
                    'y': min(rel_y1, rel_y2),
                    'width': abs(rel_x2 - rel_x1),
                    'height': abs(rel_y2 - rel_y1)
                }

                # 截取介面UI區域的圖片
                try:
                    # 計算絕對螢幕座標
                    abs_x = game_window.left + self.interface_ui_region['x']
                    abs_y = game_window.top + self.interface_ui_region['y']

                    with mss.mss() as sct:
                        monitor = {
                            "top": abs_y,
                            "left": abs_x,
                            "width": self.interface_ui_region['width'],
                            "height": self.interface_ui_region['height']
                        }

                        screenshot = sct.grab(monitor)
                        # 使用PIL Image方式
                        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

                        # 創建screenshots目錄（如果不存在）
                        screenshot_dir = os.path.join(get_app_dir(), "screenshots")
                        os.makedirs(screenshot_dir, exist_ok=True)

                        # 保存PIL圖片為PNG
                        interface_screenshot_path = os.path.join(screenshot_dir, "interface_ui.png")
                        img.save(interface_screenshot_path)
                        print(f"介面UI截圖已保存到: {interface_screenshot_path}")

                        # 將PIL圖片轉換為OpenCV格式用於後續處理
                        self.interface_ui_screenshot = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

                        # 更新UI顯示
                        self.interface_ui_label.config(text=self.get_interface_ui_region_text(), background="lightgreen")

                        # 更新介面UI預覽
                        self.update_interface_ui_preview()

                        messagebox.showinfo("成功", f"介面UI區域已設定並截圖:\n座標: ({self.interface_ui_region['x']}, {self.interface_ui_region['y']})\n大小: {self.interface_ui_region['width']}x{self.interface_ui_region['height']}")

                except Exception as e:
                    messagebox.showerror("錯誤", f"截圖失敗: {str(e)}")
                    print(f"詳細錯誤: {e}")
                    import traceback
                    traceback.print_exc()

            self.interface_ui_selection_window.destroy()

            # 重新激活主視窗並恢復正常狀態
            self.root.attributes("-alpha", 1.0)  # 恢復完全不透明
            self.root.attributes("-topmost", True)  # 恢復置頂
            self.root.lift()
            self.root.focus_force()
        else:
            # 如果沒有有效的選擇，取消選擇
            self.cancel_interface_ui_selection()

    def cancel_interface_ui_selection(self, event=None):
        """取消介面UI區域選擇"""
        # 重置選擇狀態
        self.interface_ui_selection_active = False
        self.interface_ui_selection_start = None
        self.interface_ui_selection_end = None

        # 移除全局ESC監聽
        self.remove_global_esc_listener_for_interface()

        if hasattr(self, 'interface_ui_selection_window'):
            self.interface_ui_selection_window.destroy()

        # 重新激活主視窗並恢復正常狀態
        self.root.attributes("-alpha", 1.0)  # 恢復完全不透明
        self.root.attributes("-topmost", True)  # 恢復置頂
        self.root.lift()
        self.root.focus_force()

    def save_ui_screenshot_to_file(self):
        """將UI截圖保存為PNG文件 - 此函數現在不再需要，因為已在截圖時直接保存"""
        # 這個函數現在不需要了，因為我們在 end_inventory_ui_selection 中直接保存
        pass

    def load_ui_screenshot_from_file(self):
        """從PNG文件載入UI截圖 - 使用血魔檢測的方式"""
        try:
            screenshot_dir = os.path.join(get_app_dir(), "screenshots")
            ui_screenshot_path = os.path.join(screenshot_dir, "inventory_ui.png")

            if os.path.exists(ui_screenshot_path):
                # 使用PIL載入圖片，如同血魔檢測
                img = Image.open(ui_screenshot_path)
                # 轉換為OpenCV格式
                self.inventory_ui_screenshot = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                print(f"UI截圖已從檔案載入: {ui_screenshot_path}")
                
                # 更新UI標籤狀態
                if hasattr(self, 'inventory_ui_label'):
                    self.inventory_ui_label.config(text="已記錄背包UI", background="lightgreen")
                
                # 更新UI預覽
                if hasattr(self, 'ui_preview_canvas'):
                    self.update_ui_preview()
                
                return True
            else:
                print("UI截圖檔案不存在")
                return False

        except Exception as e:
            print(f"載入UI截圖時發生錯誤: {e}")
            import traceback
            traceback.print_exc()
            return False

    def load_interface_ui_screenshot_from_file(self):
        """從PNG文件載入介面UI截圖"""
        try:
            screenshot_dir = os.path.join(get_app_dir(), "screenshots")
            interface_screenshot_path = os.path.join(screenshot_dir, "interface_ui.png")

            if os.path.exists(interface_screenshot_path):
                # 使用PIL載入圖片
                img = Image.open(interface_screenshot_path)
                # 轉換為OpenCV格式
                self.interface_ui_screenshot = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                print(f"介面UI截圖已從檔案載入: {interface_screenshot_path}")

                # 更新UI標籤狀態
                if hasattr(self, 'interface_ui_label'):
                    self.interface_ui_label.config(text=self.get_interface_ui_region_text(), background="lightgreen")

                # 更新介面UI預覽
                if hasattr(self, 'interface_ui_preview_canvas'):
                    self.update_interface_ui_preview()

                return True
            else:
                print("介面UI截圖檔案不存在")
                return False

        except Exception as e:
            print(f"載入介面UI截圖時發生錯誤: {e}")
            import traceback
            traceback.print_exc()
            return False

    def update_ui_preview(self):
        """更新UI預覽Canvas顯示截圖"""
        try:
            if self.inventory_ui_screenshot is None:
                # 如果沒有截圖，顯示預設文字
                if hasattr(self, 'ui_preview_canvas'):
                    self.ui_preview_canvas.delete("all")
                    self.ui_preview_canvas.create_text(100, 75, text="尚未截取UI", 
                                                     fill="gray", font=("Arial", 10))
                return

            # 將OpenCV BGR格式轉換為PIL RGB格式
            # inventory_ui_screenshot 是 BGR 格式，需要轉換為 RGB
            rgb_image = cv2.cvtColor(self.inventory_ui_screenshot, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_image)

            # 調整圖片大小以適應Canvas (200x150)
            canvas_width = 200
            canvas_height = 150

            # 計算縮放比例，保持寬高比
            img_width, img_height = pil_image.size
            scale = min(canvas_width / img_width, canvas_height / img_height)

            new_width = int(img_width * scale)
            new_height = int(img_height * scale)

            # 調整圖片大小
            pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # 轉換為PhotoImage
            self.ui_preview_image = ImageTk.PhotoImage(pil_image)

            # 在Canvas上顯示圖片
            if hasattr(self, 'ui_preview_canvas'):
                self.ui_preview_canvas.delete("all")
                # 計算居中位置
                x = (canvas_width - new_width) // 2
                y = (canvas_height - new_height) // 2
                self.ui_preview_canvas.create_image(x, y, anchor=tk.NW, image=self.ui_preview_image)

        except Exception as e:
            print(f"更新UI預覽失敗: {e}")
            if hasattr(self, 'ui_preview_canvas'):
                self.ui_preview_canvas.delete("all")
                self.ui_preview_canvas.create_text(100, 75, text="預覽載入失敗", 
                                                 fill="red", font=("Arial", 10))

    def is_inventory_ui_visible(self, game_window):
        """檢查背包UI是否可見"""
        if not self.inventory_ui_region or self.inventory_ui_screenshot is None:
            print("F3 UI檢查: 背包UI截圖不存在，無法執行清包")
            return False

        try:
            # 擷取當前背包UI區域
            with mss.mss() as sct:
                monitor = {
                    "top": game_window.top + self.inventory_ui_region['y'],
                    "left": game_window.left + self.inventory_ui_region['x'],
                    "width": self.inventory_ui_region['width'],
                    "height": self.inventory_ui_region['height']
                }

                screenshot = sct.grab(monitor)
                current_img = np.array(screenshot)
                current_img = cv2.cvtColor(current_img, cv2.COLOR_BGRA2BGR)

                # 比較兩張圖片的相似度
                if current_img.shape == self.inventory_ui_screenshot.shape:
                    # 使用均方誤差 (MSE) 來比較
                    mse = np.mean((current_img - self.inventory_ui_screenshot) ** 2)

                    # 使用更嚴格的MSE閾值以提高準確性
                    mse_threshold = 150  # 非常嚴格的閾值

                    # 計算額外的相似度指標
                    # 比較主要顏色
                    current_main_color = np.mean(current_img, axis=(0, 1))
                    recorded_main_color = np.mean(self.inventory_ui_screenshot, axis=(0, 1))
                    color_diff = np.mean(np.abs(current_main_color - recorded_main_color))

                    color_threshold = 10  # 顏色差異閾值

                    is_visible = (mse < mse_threshold) and (color_diff < color_threshold)

                    # 添加詳細調試信息
                    print(f"F3 UI檢查: MSE={mse:.2f} (閾值:{mse_threshold}), 顏色差={color_diff:.2f} (閾值:{color_threshold}), UI可見={is_visible}")

                    return is_visible
                else:
                    print(f"F3 UI檢查: 圖片尺寸不匹配 - 當前{current_img.shape}, 記錄{self.inventory_ui_screenshot.shape}")
                    return False

        except Exception as e:
            print(f"檢查背包UI可見性失敗: {e}")
            return False

    def is_interface_ui_visible(self, game_window):
        """檢查介面UI是否可見（用於判定是否在戰鬥狀態）- 改進版比較邏輯"""
        if not self.interface_ui_region or self.interface_ui_screenshot is None:
            print("血魔檢查: 介面UI截圖不存在，無法判定戰鬥狀態")
            return False

        try:
            # 擷取當前介面UI區域
            with mss.mss() as sct:
                monitor = {
                    "top": game_window.top + self.interface_ui_region['y'],
                    "left": game_window.left + self.interface_ui_region['x'],
                    "width": self.interface_ui_region['width'],
                    "height": self.interface_ui_region['height']
                }

                screenshot = sct.grab(monitor)
                current_img = np.array(screenshot)
                current_img = cv2.cvtColor(current_img, cv2.COLOR_BGRA2BGR)

                # 比較兩張圖片的相似度
                if current_img.shape == self.interface_ui_screenshot.shape:
                    # === 多重比較方法 ===

                    # 1. 均方誤差 (MSE) - 使用可調節閾值
                    mse = np.mean((current_img - self.interface_ui_screenshot) ** 2)
                    mse_threshold = self.interface_ui_mse_threshold

                    # 2. 結構相似性比較 (SSIM) - 如果可用
                    ssim_score = 0.5  # 預設值
                    try:
                        from skimage.metrics import structural_similarity as ssim
                        # 轉換為灰階進行SSIM比較
                        gray_current = cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY)
                        gray_recorded = cv2.cvtColor(self.interface_ui_screenshot, cv2.COLOR_BGR2GRAY)
                        ssim_score = ssim(gray_current, gray_recorded)
                    except ImportError:
                        print("血魔檢查: SSIM不可用，使用MSE比較")
                        ssim_score = 0.8  # 如果沒有SSIM，給予較高分數

                    ssim_threshold = self.interface_ui_ssim_threshold

                    # 3. 顏色直方圖比較
                    hist_current = cv2.calcHist([current_img], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
                    hist_recorded = cv2.calcHist([self.interface_ui_screenshot], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])

                    # 正規化直方圖
                    hist_current = cv2.normalize(hist_current, hist_current).flatten()
                    hist_recorded = cv2.normalize(hist_recorded, hist_recorded).flatten()

                    # 計算直方圖相似度
                    hist_similarity = cv2.compareHist(hist_current, hist_recorded, cv2.HISTCMP_CORREL)
                    hist_threshold = self.interface_ui_hist_threshold

                    # 4. 主要顏色比較（使用可調節閾值）
                    current_main_color = np.mean(current_img, axis=(0, 1))
                    recorded_main_color = np.mean(self.interface_ui_screenshot, axis=(0, 1))
                    color_diff = np.mean(np.abs(current_main_color - recorded_main_color))
                    color_threshold = self.interface_ui_color_threshold

                    # === 綜合判定邏輯 ===
                    # 使用多重條件，只要滿足大部分條件就認為相似
                    mse_pass = mse < mse_threshold
                    ssim_pass = ssim_score > ssim_threshold
                    hist_pass = hist_similarity > hist_threshold
                    color_pass = color_diff < color_threshold

                    # 計算通過的條件數量
                    pass_count = sum([mse_pass, ssim_pass, hist_pass, color_pass])

                    # 如果至少3個條件通過，或者MSE和顏色都通過，則認為相似
                    is_visible = (pass_count >= 3) or (mse_pass and color_pass) or (ssim_pass and hist_pass)

                    # 添加詳細調試信息
                    print(f"血魔UI檢查詳細:")
                    print(f"  MSE: {mse:.2f} < {mse_threshold} = {mse_pass}")
                    print(f"  SSIM: {ssim_score:.3f} > {ssim_threshold} = {ssim_pass}")
                    print(f"  直方圖: {hist_similarity:.3f} > {hist_threshold} = {hist_pass}")
                    print(f"  顏色差: {color_diff:.2f} < {color_threshold} = {color_pass}")
                    print(f"  通過條件: {pass_count}/4, 最終結果: {is_visible}")

                    return is_visible
                else:
                    print(f"血魔UI檢查: 圖片尺寸不匹配 - 當前{current_img.shape}, 記錄{self.interface_ui_screenshot.shape}")
                    return False

        except Exception as e:
            print(f"檢查介面UI可見性失敗: {e}")
            import traceback
            traceback.print_exc()
            return False

    def update_interface_ui_preview(self):
        """更新介面UI預覽Canvas顯示截圖"""
        try:
            if self.interface_ui_screenshot is None:
                # 如果沒有截圖，顯示預設文字
                if hasattr(self, 'interface_ui_preview_canvas'):
                    self.interface_ui_preview_canvas.delete("all")
                    self.interface_ui_preview_canvas.create_text(75, 50, text="尚未截取介面UI",
                                                               fill="gray", font=("Arial", 8))
                return

            # 將OpenCV BGR格式轉換為PIL RGB格式
            # interface_ui_screenshot 是 BGR 格式，需要轉換為 RGB
            rgb_image = cv2.cvtColor(self.interface_ui_screenshot, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_image)

            # 調整圖片大小以適應Canvas (150x100)
            canvas_width = 150
            canvas_height = 100

            # 計算縮放比例，保持寬高比
            img_width, img_height = pil_image.size
            scale = min(canvas_width / img_width, canvas_height / img_height)

            new_width = int(img_width * scale)
            new_height = int(img_height * scale)

            # 調整圖片大小
            pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # 轉換為PhotoImage
            self.interface_ui_preview_image = ImageTk.PhotoImage(pil_image)

            # 在Canvas上顯示圖片
            if hasattr(self, 'interface_ui_preview_canvas'):
                self.interface_ui_preview_canvas.delete("all")
                # 計算居中位置
                x = (canvas_width - new_width) // 2
                y = (canvas_height - new_height) // 2
                self.interface_ui_preview_canvas.create_image(x, y, anchor=tk.NW, image=self.interface_ui_preview_image)

        except Exception as e:
            print(f"更新介面UI預覽失敗: {e}")
            if hasattr(self, 'interface_ui_preview_canvas'):
                self.interface_ui_preview_canvas.delete("all")
                self.interface_ui_preview_canvas.create_text(75, 50, text="預覽載入失敗",
                                                           fill="red", font=("Arial", 8))

    def get_inventory_main_color(self, img):
        """獲取背包區域的主要顏色"""
        pixels = img.reshape(-1, 3)
        pixels = np.float32(pixels)

        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        K = 1  # 只取一個主要顏色
        _, labels, centers = cv2.kmeans(pixels, K, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

        # 轉換為RGB
        center = centers[0]
        return (int(center[2]), int(center[1]), int(center[0]))  # BGR to RGB

    def should_clear_inventory(self, img, skip_slots=None, current_slot=None):
        """判斷是否需要清空背包 - 檢查60個格子，可選擇跳過指定格子和之前的格子"""
        if not self.empty_inventory_colors or not self.inventory_grid_positions:
            return False, []

        # 檢查是否有任何格子的顏色不符合基準
        occupied_slots = []
        for i, (pos_x, pos_y) in enumerate(self.inventory_grid_positions):
            # 如果指定了最後處理過的格子，跳過所有索引小於等於該格子的格子
            # 這樣可以避免文字視窗被誤識別為道具
            if current_slot is not None and i <= current_slot:
                continue
                
            if i >= len(self.empty_inventory_colors):
                continue

            # 確保座標在圖片範圍內
            img_x = pos_x - self.inventory_region['x']
            img_y = pos_y - self.inventory_region['y']

            if 0 <= img_x < img.shape[1] and 0 <= img_y < img.shape[0]:
                # 獲取5x5區域的平均顏色（與記錄時保持一致）
                x1 = max(0, img_x - 2)
                y1 = max(0, img_y - 2)
                x2 = min(img.shape[1], img_x + 3)
                y2 = min(img.shape[0], img_y + 3)

                cell_pixels = img[y1:y2, x1:x2]
                if cell_pixels.size > 0:
                    avg_color = np.mean(cell_pixels, axis=(0, 1))
                    current_rgb = (int(avg_color[2]), int(avg_color[1]), int(avg_color[0]))  # BGR to RGB

                    # 比較顏色差異 - 降低閾值以提高靈敏度，特別針對黑色道具
                    baseline_rgb = self.empty_inventory_colors[i]
                    color_diff = sum(abs(a - b) for a, b in zip(current_rgb, baseline_rgb))

                    # 調試信息：記錄顏色差異
                    if i < 5:  # 只記錄前5個格子的信息
                        print(f"格子{i}: 當前顏色{current_rgb}, 基準顏色{baseline_rgb}, 差異{color_diff}")

                    # 如果顏色差異大於閾值，說明這個格子有物品
                    # 降低閾值從30到15，提高檢測靈敏度
                    if color_diff > 15:  # 進一步降低閾值
                        occupied_slots.append(i)  # 返回格子索引而不是座標

        return len(occupied_slots) > 0, occupied_slots

    def clear_inventory_item(self, game_window, img):
        """清空背包物品 - 分析圖片並點擊有物品的位置 (優化版)"""
        try:
            # 初始化變數
            last_processed_slot = -1  # 最後處理過的格子索引，初始化為-1
            
            # 分析背包圖片，找到有物品的位置
            item_positions = self.find_inventory_items(img, None, last_processed_slot)

            if not item_positions:
                print("沒有找到需要清空的物品")
                return

            print(f"找到 {len(item_positions)} 個物品位置")

            # 採用動態檢測方式：持續按住Ctrl，每次只處理一個確實有道具的位置
            print("開始動態清包模式 - 持續按住 Ctrl 鍵")
            pyautogui.keyDown('ctrl')
            time.sleep(0.025)  # CTRL按壓後等待25ms，符合操作時序要求

            total_processed = 0
            max_iterations = 60  # 防止無限循環的安全限制
            # 記錄每個座標被點擊的次數，用於智能跳過邏輯
            position_click_count = {}  # key: (x, y), value: click_count
            max_clicks_per_position = 1  # 同個座標最多點擊1次
            
            # 優化：預先計算monitor配置，避免重複計算
            monitor = {
                "top": game_window.top + self.inventory_region['y'],
                "left": game_window.left + self.inventory_region['x'],
                "width": self.inventory_region['width'],
                "height": self.inventory_region['height']
            }

            while total_processed < max_iterations:
                # 檢查中斷標誌
                if self.inventory_clear_interrupt:
                    print("F3清包被用戶中斷")
                    break

                try:
                    # 重新擷取並分析背包狀態
                    with mss.mss() as sct:
                        screenshot = sct.grab(monitor)
                        # 優化：直接轉換為numpy陣列，減少一次轉換
                        img = np.frombuffer(screenshot.rgb, dtype=np.uint8).reshape(screenshot.height, screenshot.width, 3)
                        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

                    # 重新分析背包狀態，跳過最後處理格子之前的所有格子
                    should_clear, current_occupied = self.should_clear_inventory(img, None, last_processed_slot)

                    if not should_clear:
                        print(f"背包已清空，動態清包結束 (總共處理了 {total_processed} 個道具)")
                        break

                    # 即時更新預覽：顯示當前背包狀態
                    try:
                        progress_text = f"清包進度: {total_processed} 個道具"
                        self.root.after(0, lambda: self.update_inventory_preview_with_progress(img, current_occupied, progress_text))
                        print(f"已更新背包預覽 (剩餘: {len(current_occupied)} 個道具)")
                    except Exception as e:
                        print(f"更新預覽時發生錯誤: {e}")

                    # 獲取當前確實有道具的位置，並過濾掉已經點擊過多的位置
                    current_positions = self.find_inventory_items(img, None, last_processed_slot)
                    
                    # 過濾掉已經點擊過多的位置（智能跳過邏輯）
                    filtered_positions = []
                    for pos in current_positions:
                        pos_key = (pos[0], pos[1])
                        click_count = position_click_count.get(pos_key, 0)
                        if click_count < max_clicks_per_position:
                            filtered_positions.append(pos)
                        else:
                            print(f"跳過座標 ({pos[0]}, {pos[1]}) - 已點擊 {click_count} 次，超過上限 {max_clicks_per_position}")
                    
                    current_positions = filtered_positions

                    if not current_positions:
                        print(f"沒有找到有效道具位置，動態清包結束 (總共處理了 {total_processed} 個道具)")
                        break

                    # 點擊第一個有效位置
                    pos = current_positions[0]
                    screen_x = game_window.left + pos[0]
                    screen_y = game_window.top + pos[1]

                    # 找到對應的格子索引並加入已處理集合
                    slot_index = None
                    for idx, grid_pos in enumerate(self.inventory_grid_positions):
                        if grid_pos == (pos[0], pos[1]):
                            slot_index = idx
                            break
                    
                    if slot_index is not None:
                        last_processed_slot = max(last_processed_slot, slot_index)  # 更新最後處理過的格子索引
                        print(f"格子索引 {slot_index} 已處理，最後處理格子更新為 {last_processed_slot}")

                    # 更新該位置的點擊計數
                    pos_key = (pos[0], pos[1])
                    position_click_count[pos_key] = position_click_count.get(pos_key, 0) + 1
                    click_count = position_click_count[pos_key]

                    print(f"處理第 {total_processed + 1} 個道具，位置: ({pos[0]}, {pos[1]})，螢幕座標: ({screen_x}, {screen_y})，點擊次數: {click_count}，格子索引: {slot_index}")

                    # 正確的滑鼠操作時序：
                    # 1. 滑鼠移動到道具上
                    pyautogui.moveTo(screen_x, screen_y, duration=0.015)
                    # 2. 移動後等待25ms
                    time.sleep(0.025)

                    # 3. 執行右鍵點擊
                    pyautogui.rightClick(screen_x, screen_y)
                    # 4. 點擊後等待25ms
                    time.sleep(0.025)

                    print(f"已執行右鍵點擊第 {total_processed + 1} 個道具 (包含正確的25ms延遲)")
                    total_processed += 1

                    # 優化：減少即時預覽更新頻率，避免過度截圖造成停頓
                    # 只在每5個道具或背包可能清空時才更新預覽
                    if total_processed % 5 == 0 or total_processed >= len(current_positions):
                        try:
                            # 重新擷取最新的背包狀態進行預覽更新
                            with mss.mss() as sct:
                                latest_screenshot = sct.grab(monitor)
                                latest_img = np.frombuffer(latest_screenshot.rgb, dtype=np.uint8).reshape(latest_screenshot.height, latest_screenshot.width, 3)
                                latest_img = cv2.cvtColor(latest_img, cv2.COLOR_RGB2BGR)

                            # 分析最新背包狀態
                            latest_should_clear, latest_occupied = self.should_clear_inventory(latest_img, None, last_processed_slot)
                            
                            progress_text = f"清包進度: {total_processed} 個道具"
                            self.root.after(0, lambda: self.update_inventory_preview_with_progress(latest_img, latest_occupied, progress_text))
                            print(f"已更新背包預覽 (處理進度: {total_processed} 個道具，剩餘: {len(latest_occupied)} 個)")
                            
                            # 如果背包已清空，提前結束
                            if not latest_should_clear:
                                print(f"背包已清空，提前結束動態清包 (總共處理了 {total_processed} 個道具)")
                                break
                                
                        except Exception as e:
                            print(f"更新預覽時發生錯誤: {e}")

                    # 優化：保持25ms延遲，確保操作流暢性
                    time.sleep(0.025)  # 25ms延遲，保持操作節奏

                except Exception as e:
                    print(f"動態清包過程中發生錯誤: {e}")
                    break

            if total_processed >= max_iterations:
                print(f"達到最大處理次數限制 ({max_iterations})，強制結束動態清包")

            # 釋放CTRL鍵
            print("釋放 Ctrl 鍵")
            pyautogui.keyUp('ctrl')
            time.sleep(0.025)  # CTRL釋放後等待25ms，保持一致的時序

            # 清包完成後最終更新預覽，顯示完成狀態
            try:
                # 重新擷取最終的背包狀態
                with mss.mss() as sct:
                    final_screenshot = sct.grab(monitor)
                    final_img = np.frombuffer(final_screenshot.rgb, dtype=np.uint8).reshape(final_screenshot.height, final_screenshot.width, 3)
                    final_img = cv2.cvtColor(final_img, cv2.COLOR_RGB2BGR)

                # 分析最終背包狀態，跳過最後處理格子之前的所有格子
                final_should_clear, final_occupied = self.should_clear_inventory(final_img, None, last_processed_slot)

                # 在主線程中最終更新預覽
                final_progress_text = f"清包完成: {total_processed} 個道具"
                self.root.after(0, lambda: self.update_inventory_preview_with_progress(final_img, final_occupied, final_progress_text))

                # 更新統計標籤為完成狀態
                self.root.after(0, lambda: self.occupied_label.config(text=f"{len(final_occupied)}/60") if hasattr(self, 'occupied_label') else None)

                print(f"已最終更新背包預覽 (清包完成: {total_processed} 個道具，剩餘: {len(final_occupied)} 個)")

            except Exception as e:
                print(f"最終更新預覽時發生錯誤: {e}")

            print(f"F3: 動態清包完成，已清空 {total_processed} 個背包物品")

        except Exception as e:
            print(f"清空物品失敗: {e}")
        finally:
            # 確保CTRL鍵被釋放
            try:
                pyautogui.keyUp('ctrl')
                print("確保CTRL鍵已釋放")
            except Exception as e:
                print(f"釋放CTRL鍵時發生錯誤: {e}")

    def find_inventory_items(self, img, skip_slots=None, current_slot=None):
        """分析圖片並找到有物品的格子位置"""
        _, occupied_indices = self.should_clear_inventory(img, None, current_slot)
        # 將索引轉換為座標
        occupied_positions = []
        for index in occupied_indices:
            if index < len(self.inventory_grid_positions):
                occupied_positions.append(self.inventory_grid_positions[index])
        return occupied_positions

    def update_inventory_preview_with_items(self, img, occupied_slots):
        """更新背包預覽，顯示60個格子的狀態"""
        try:
            # 創建副本以避免修改原始圖片
            display_img = img.copy()

            # 繪製網格線和檢查每個格子的狀態
            height, width = display_img.shape[:2]
            rows, cols = 5, 12  # 修正為5行x12列的正確排列

            # 計算網格大小
            cell_width = width // cols
            cell_height = height // rows

            # 繪製網格線
            for i in range(1, rows):
                y = i * cell_height
                cv2.line(display_img, (0, y), (width, y), (128, 128, 128), 1)

            for i in range(1, cols):
                x = i * cell_width
                cv2.line(display_img, (x, 0), (x, height), (128, 128, 128), 1)

            # 檢查並標記每個格子的狀態
            occupied_count = 0
            for row in range(5):  # 5行
                for col in range(12):  # 12列
                    # 計算格子中心點
                    center_x = col * cell_width + cell_width // 2
                    center_y = row * cell_height + cell_height // 2

                    # 計算這個格子在60個位置陣列中的索引
                    grid_index = row * cols + col

                    # 檢查這個格子是否有物品
                    has_item = False
                    if grid_index in occupied_slots:  # 直接檢查索引是否在佔用的格子列表中
                        has_item = True
                        occupied_count += 1
                        print(f"檢測到物品在格子 {grid_index} (行{row}, 列{col})")  # 調試信息

                    if has_item:
                        # 繪製紅色叉號表示有物品
                        size = 6
                        cv2.line(display_img, (center_x - size, center_y - size), (center_x + size, center_y + size), (0, 0, 255), 2)
                        cv2.line(display_img, (center_x + size, center_y - size), (center_x - size, center_y + size), (0, 0, 255), 2)
                    else:
                        # 繪製綠色圓點表示空置
                        cv2.circle(display_img, (center_x, center_y), 2, (0, 255, 0), -1)

            # 移除圖片上的統計文字（移到外面顯示）
            # cv2.putText(display_img, f"Occupied: {occupied_count}/60", (10, 20),
            #            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            # cv2.putText(display_img, f"Occupied: {occupied_count}/60", (10, 20),
            #            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)

            # 調整圖片大小 - 根據當前GUI尺寸動態調整
            # 獲取當前GUI尺寸來計算合適的最大尺寸
            try:
                current_gui_width = self.root.winfo_width()
                current_gui_height = self.root.winfo_height()
                
                # 根據GUI尺寸計算背包預覽的最大可用空間
                # 考慮到padding、統計資訊區域等UI元素，預留空間
                if current_gui_width < 600:  # GUI被縮小
                    max_width = max(300, current_gui_width - 100)  # 為側邊欄預留空間
                    max_height = max(200, current_gui_height - 200)  # 為統計和控制區域預留空間
                else:  # 正常GUI尺寸
                    max_width = 500
                    max_height = 400
            except:
                # 如果獲取GUI尺寸失敗，使用預設值
                max_width = 500
                max_height = 400

            # 計算縮放比例，保持長寬比
            scale = min(max_width / width, max_height / height, 1.0)  # 不超過1.0（不放大）

            if scale < 1.0:  # 只在需要縮小時調整
                new_width = int(width * scale)
                new_height = int(height * scale)
                display_img = cv2.resize(display_img, (new_width, new_height))
                print(f"背包預覽已縮放: {width}x{height} -> {new_width}x{new_height} (縮放比例: {scale:.2f})")

            # 轉換為PIL圖片
            display_img_rgb = cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(display_img_rgb)
            tk_img = ImageTk.PhotoImage(pil_img)

            # 更新預覽
            self.inventory_preview_label.config(image=tk_img, text="")
            self.inventory_preview_label.image = tk_img

            # 更新統計資訊標籤
            if hasattr(self, 'occupied_label'):
                self.occupied_label.config(text=f"{occupied_count}/60")

        except Exception as e:
            print(f"更新預覽失敗: {e}")
            # 如果標記失敗，至少顯示原始圖片
            self.update_inventory_preview(img)

    def update_inventory_preview_with_progress(self, img, occupied_slots, progress_text):
        """更新背包預覽，顯示60個格子的狀態和處理進度 - 優化版本"""
        try:
            # 創建副本以避免修改原始圖片
            display_img = img.copy()

            # 繪製網格線和檢查每個格子的狀態
            height, width = display_img.shape[:2]
            rows, cols = 5, 12  # 修正為5行x12列的正確排列

            # 計算網格大小
            cell_width = width // cols
            cell_height = height // rows

            # 繪製網格線 - 優化：使用更細的線條提高性能
            for i in range(1, rows):
                y = i * cell_height
                cv2.line(display_img, (0, y), (width, y), (128, 128, 128), 1)

            for i in range(1, cols):
                x = i * cell_width
                cv2.line(display_img, (x, 0), (x, height), (128, 128, 128), 1)

            # 檢查並標記每個格子的狀態 - 優化：使用更高效的標記方式
            occupied_count = len(occupied_slots)  # 直接使用長度，避免重複計算

            for grid_index in occupied_slots:
                # 計算格子位置
                row = grid_index // cols
                col = grid_index % cols
                
                # 計算格子中心點
                center_x = col * cell_width + cell_width // 2
                center_y = row * cell_height + cell_height // 2

                # 繪製紅色叉號表示有物品 - 優化：使用更小的標記提高性能
                size = 4  # 從6縮小到4
                cv2.line(display_img, (center_x - size, center_y - size), (center_x + size, center_y + size), (0, 0, 255), 1)
                cv2.line(display_img, (center_x + size, center_y - size), (center_x - size, center_y + size), (0, 0, 255), 1)

            # 調整圖片大小 - 根據當前GUI尺寸動態調整（與update_inventory_preview保持一致）
            try:
                current_gui_width = self.root.winfo_width()
                current_gui_height = self.root.winfo_height()
                
                # 根據GUI尺寸計算背包預覽的最大可用空間
                if current_gui_width < 600:  # GUI被縮小
                    max_width = max(300, current_gui_width - 100)  # 為側邊欄預留空間
                    max_height = max(200, current_gui_height - 200)  # 為統計和控制區域預留空間
                else:  # 正常GUI尺寸
                    max_width = 500
                    max_height = 400
            except:
                # 如果獲取GUI尺寸失敗，使用預設值
                max_width = 500
                max_height = 400

            # 計算縮放比例，保持長寬比
            scale = min(max_width / width, max_height / height, 1.0)  # 不超過1.0（不放大）

            if scale < 1.0:  # 只在需要縮小時調整
                new_width = int(width * scale)
                new_height = int(height * scale)
                display_img = cv2.resize(display_img, (new_width, new_height))
                print(f"背包進度預覽已縮放: {width}x{height} -> {new_width}x{new_height} (縮放比例: {scale:.2f})")

            # 轉換為PIL圖片 - 優化：直接使用現有的轉換邏輯
            display_img_rgb = cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(display_img_rgb)
            tk_img = ImageTk.PhotoImage(pil_img)

            # 更新預覽 - 優化：批量更新以提高性能
            self.inventory_preview_label.config(image=tk_img, text="")
            self.inventory_preview_label.image = tk_img

            # 更新統計資訊標籤 - 優化：只在需要時更新
            if hasattr(self, 'occupied_label'):
                self.occupied_label.config(text=f"{occupied_count}/60")

        except Exception as e:
            print(f"更新進度預覽失敗: {e}")
            # 如果標記失敗，至少顯示原始圖片
            self.update_inventory_preview(img)

    def test_inventory_clearing(self):
        """測試背包清空功能 - 增強版本，自動檢測並開啟背包"""
        if not self.inventory_region:
            messagebox.showwarning("警告", "請先框選背包區域")
            return

        if not self.empty_inventory_colors:
            messagebox.showwarning("警告", "請先記錄淨空顏色")
            return

        # 檢查背包UI區域是否已設定
        if not hasattr(self, 'inventory_ui_region') or not self.inventory_ui_region:
            messagebox.showwarning("警告", "請先框選背包UI區域")
            return

        # 使用血魔監控的遊戲視窗
        window_title = self.window_var.get()
        if not window_title:
            messagebox.showwarning("警告", "請先在血魔監控分頁設定遊戲視窗")
            return

        try:
            # 1. 檢測遊戲視窗是否存在
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                messagebox.showerror("錯誤", "找不到指定的遊戲視窗")
                return

            game_window = windows[0]
            print(f"找到遊戲視窗: {game_window.title}")

            # 2. 檢查GUI是否會遮擋背包UI檢測區域或背包區域，如果會則縮小GUI
            gui_minimized_for_test = False
            needs_gui_minimize = False
            
            # 只有在啟用"永遠保持在最上方"時才需要檢查GUI遮擋問題
            if self.always_on_top_var.get():
                # 檢查是否需要縮小GUI（同時檢查背包UI檢測區域和背包區域）
                if hasattr(self, 'inventory_ui_region') and self.inventory_ui_region:
                    if self.check_gui_overlap_with_inventory_ui(game_window):
                        needs_gui_minimize = True
                        print("檢測到GUI可能遮擋背包UI檢測區域")
                
                if self.check_gui_overlap_with_inventory(game_window):
                    needs_gui_minimize = True
                    print("檢測到GUI可能遮擋背包區域")
            else:
                print("GUI未設定為永遠保持在最上方，跳過遮擋檢查")
            
            # 如果需要縮小GUI，一次性處理
            if needs_gui_minimize:
                print("正在縮小GUI以避免遮擋...")
                original_state = self.root.state()
                original_geometry = self.root.geometry()
                self.root.iconify()
                time.sleep(0.2)
                gui_minimized_for_test = True
                print("GUI已縮小")

            # 3. 確保遊戲視窗在前台（無論是否啟用永遠保持在最上方，都需要激活遊戲視窗）
            try:
                game_window.activate()
                time.sleep(0.2)
                print("遊戲視窗已激活")
            except Exception as e:
                print(f"激活遊戲視窗失敗: {e}")
                # 如果激活失敗，嘗試點擊視窗
                try:
                    pyautogui.click(game_window.left + game_window.width // 2, 
                                  game_window.top + game_window.height // 2)
                    time.sleep(0.2)
                    print("已嘗試點擊遊戲視窗")
                except Exception as e2:
                    print(f"點擊遊戲視窗也失敗: {e2}")

            # 4. 檢測背包UI是否存在（GUI已縮小或遊戲視窗已激活，不會被遮擋）
            inventory_ui_exists = self.check_inventory_ui_exists(game_window)
            print(f"背包UI狀態: {'存在' if inventory_ui_exists else '不存在'}")

            # 5. 如果背包UI不存在，自動開啟背包
            if not inventory_ui_exists:
                print("背包未開啟，正在自動開啟...")
                # 確保遊戲視窗在前台
                try:
                    game_window.activate()
                    time.sleep(0.2)
                except:
                    # 如果 activate 失敗，嘗試點擊視窗
                    pyautogui.click(game_window.left + game_window.width // 2, 
                                  game_window.top + game_window.height // 2)
                    time.sleep(0.2)

                # 發送 I 鍵開啟背包
                pyautogui.press('i')
                time.sleep(0.8)  # 增加等待時間確保背包完全開啟
                print("已發送 I 鍵開啟背包")
                
                # 再次檢測背包是否已開啟（如果有設定UI檢測）
                if hasattr(self, 'inventory_ui_region') and self.inventory_ui_region:
                    inventory_ui_exists = self.check_inventory_ui_exists(game_window)
                    print(f"開啟後背包UI狀態: {'存在' if inventory_ui_exists else '不存在'}")
                    if not inventory_ui_exists:
                        print("警告: 背包可能未正確開啟，但繼續執行")

            # 4. 擷取並分析背包區域（GUI已經在需要時縮小了）
            with mss.mss() as sct:
                monitor = {
                    "top": game_window.top + self.inventory_region['y'],
                    "left": game_window.left + self.inventory_region['x'],
                    "width": self.inventory_region['width'],
                    "height": self.inventory_region['height']
                }

                screenshot = sct.grab(monitor)
                img = np.array(screenshot)
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

                # 分析背包狀態
                should_clear, occupied_slots = self.should_clear_inventory(img)

            # 5. 恢復GUI面板（如果之前縮小了）
            if gui_minimized_for_test:
                self.root.deiconify()
                if original_state == 'zoomed':
                    self.root.state('zoomed')
                else:
                    self.root.geometry(original_geometry)
                time.sleep(0.2)
                print("GUI已恢復")

            # 7. 更新背包預覽（包含物品標記）
            self.update_inventory_preview_with_items(img, occupied_slots)

            # 8. 如果沒有啟用"永遠保持在最上方"且沒有縮小GUI，重新激活GUI讓用戶能看到背包預覽
            if not self.always_on_top_var.get() and not gui_minimized_for_test:
                try:
                    # 重新激活GUI視窗，讓用戶能看到背包預覽
                    self.root.lift()
                    self.root.focus_force()
                    print("已重新激活GUI視窗，用戶可以查看背包預覽")
                except Exception as e:
                    print(f"重新激活GUI視窗失敗: {e}")

            # 9. 顯示測試結果（已移除對話框，改為控制台輸出）
            status = "需要清空" if should_clear else "背包淨空"
            result_msg = f"背包狀態: {status}\n"
            result_msg += f"占用格子: {len(occupied_slots)}/60\n"

            if occupied_slots:
                result_msg += "\n占用格子位置:\n"
                for i, index in enumerate(occupied_slots[:10]):  # 只顯示前10個
                    if index < len(self.inventory_grid_positions):
                        x, y = self.inventory_grid_positions[index]
                        result_msg += f"  {i+1}. 格子{index} ({x}, {y})\n"
                    else:
                        result_msg += f"  {i+1}. 格子{index} (無效位置)\n"
                if len(occupied_slots) > 10:
                    result_msg += f"  ...還有{len(occupied_slots)-10}個\n"

            print(f"測試清包結果:\n{result_msg}")
            # messagebox.showinfo("測試結果", result_msg)  # 已移除對話框

        except Exception as e:
            messagebox.showerror("錯誤", f"測試失敗: {str(e)}")
            # 確保GUI恢復正常
            try:
                self.root.deiconify()
            except:
                pass

    def save_inventory_config(self, parent_window=None):
        """儲存背包設定"""
        try:
            self.config['inventory_region'] = self.inventory_region
            self.config['empty_inventory_colors'] = self.empty_inventory_colors
            self.config['inventory_grid_positions'] = self.inventory_grid_positions
            self.config['grid_offset_x'] = self.grid_offset_x
            self.config['grid_offset_y'] = self.grid_offset_y
            # 儲存血魔監控的遊戲視窗標題
            self.config['inventory_window_title'] = self.window_var.get()

            # 儲存背包UI設定
            self.config['inventory_ui_region'] = self.inventory_ui_region
            # 注意：inventory_ui_screenshot是numpy array，不能直接序列化為JSON
            # 我們只儲存區域資訊，截圖會在下次啟動時重新截取

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)

            messagebox.showinfo("成功", "背包設定已儲存")
            
            # 重新激活主視窗而不是設定視窗
            if parent_window:
                self.root.lift()
                self.root.focus_force()
                # 根據用戶設定決定是否置頂主視窗
                if self.should_keep_topmost():
                    self.root.attributes("-topmost", True)
                
        except Exception as e:
            messagebox.showerror("錯誤", f"儲存失敗: {str(e)}")

    def return_to_hideout(self):
        """F5 返回藏身功能"""
        # 全域暫停檢查
        if self.global_pause:
            print("🔴 全域暫停中，跳過F5熱鍵")
            self.add_status_message("按下 F5 - 因全域暫停模式而跳過執行", "warning")
            return
            
        self.add_status_message("按下 F5 - 執行返回藏身", "hotkey")
        
        try:
            # 檢查是否有設定遊戲視窗
            window_title = self.window_var.get()
            if not window_title:
                print("F5: 未設定遊戲視窗，無法使用返回藏身功能")
                self.add_status_message("F5 執行失敗 - 未設定遊戲視窗", "error")
                return
            
            # 檢查遊戲視窗是否在前台
            if not self.is_game_window_foreground(window_title):
                print(f"F5: 遊戲視窗 '{window_title}' 不在前台，跳過返回藏身操作")
                self.add_status_message("F5 執行取消 - 遊戲視窗不在前台", "warning")
                return
            
            self.add_status_message("F5 執行中 - 發送返回藏身指令", "info")
            print("F5: 執行返回藏身")
            
            # 暫時阻止輸入，防止按鍵衝突
            import time
            
            # 按下 Enter 鍵開啟聊天框
            pyautogui.press('enter')
            time.sleep(0.025)
            
            # 使用 pyperclip 直接設定剪貼簿內容（更高效）
            import pyperclip
            pyperclip.copy("/hideout")
            
            # 貼上指令
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.025)
            
            # 按下 Enter 鍵執行指令
            pyautogui.press('enter')
            
            print("F5: 返回藏身指令已執行")
            self.add_status_message("F5 執行成功 - 返回藏身指令已發送", "success")
            
        except Exception as e:
            print(f"F5: 返回藏身失敗: {str(e)}")
            self.add_status_message(f"F5 執行失敗 - {str(e)}", "error")

    def f6_pickup_items(self):
        """F6 一鍵取物功能 - 優化版本（平衡速度和成功率）"""
        # 全域暫停檢查
        if self.global_pause:
            print("🔴 全域暫停中，跳過F6熱鍵")
            self.add_status_message("按下 F6 - 因全域暫停模式而跳過執行", "warning")
            return
            
        self.add_status_message("按下 F6 - 開始執行一鍵取物", "hotkey")
        
        print("=== F6取物功能被調用 ===")  # 添加調試訊息
        try:
            # 檢查是否有設定遊戲視窗
            window_title = self.window_var.get()
            if not window_title:
                print("F6: 未設定遊戲視窗，無法使用一鍵取物功能")
                self.add_status_message("F6 執行失敗 - 未設定遊戲視窗", "error")
                return
            
            print(f"F6: 遊戲視窗已設定為: {window_title}")
            
            # 檢查遊戲視窗是否在前台
            if not self.is_game_window_foreground(window_title):
                print(f"F6: 遊戲視窗 '{window_title}' 不在前台，跳過取物操作")
                self.add_status_message("F6 執行取消 - 遊戲視窗不在前台", "warning")
                return
            
            print("F6: 遊戲視窗在前台，繼續檢查...")
            self.add_status_message("F6 執行中 - 驗證遊戲視窗狀態", "info")
            
            # 如果遊戲視窗活躍，則最小化GUI視窗
            try:
                self.root.iconify()  # 最小化GUI視窗
                print("F6: GUI視窗已最小化")
            except Exception as e:
                print(f"F6: 最小化GUI視窗失敗: {e}")
            
            # 檢查背包UI設定是否完整（類似F3清包的檢查）
            if not hasattr(self, 'inventory_ui_region') or not self.inventory_ui_region or not hasattr(self, 'inventory_ui_screenshot') or self.inventory_ui_screenshot is None:
                print("F6: 背包UI截圖未設定，但仍然繼續執行（用戶可能未設定）")
                # 不強制要求背包UI設定，繼續執行
            else:
                print("F6: 背包UI設定檢查通過")
            
            # 檢查是否有設定取物座標
            if not hasattr(self, 'pickup_coordinates') or not self.pickup_coordinates or len(self.pickup_coordinates) == 0:
                print("F6: 尚未設定取物座標，請先設定座標")
                return
                
            print(f"F6: 取物座標已設定，共 {len(self.pickup_coordinates)} 個座標")
            
            # 檢查有效座標數量，並去除重複
            valid_coords = []
            seen_coords = set()
            for x, y in self.pickup_coordinates:
                if x != 0 or y != 0:  # 過濾無效座標
                    coord_tuple = (x, y)
                    if coord_tuple not in seen_coords:  # 去除重複
                        valid_coords.append((x, y))
                        seen_coords.add(coord_tuple)
            
            if not valid_coords:
                print("F6: 沒有有效的取物座標")
                return
            
            print(f"F6: 有效座標數量: {len(valid_coords)}")
            
            # 獲取遊戲視窗並檢查背包UI是否可見
            try:
                windows = gw.getWindowsWithTitle(window_title)
                if not windows:
                    print("F6: 找不到遊戲視窗")
                    return
                
                game_window = windows[0]
                print(f"F6: 找到遊戲視窗: {game_window.title}")
                
                # 簡化邏輯：跳過複雜的GUI檢查，直接執行取物
                print("F6: 跳過GUI遮擋檢查，直接執行取物")
                
                # 確保遊戲視窗在前台
                try:
                    game_window.activate()
                    time.sleep(0.2)
                    print("F6: 遊戲視窗已激活")
                except Exception as e:
                    print(f"F6: 激活遊戲視窗失敗: {e}")
                    print("F6: 視窗激活失敗，但仍然嘗試執行取物")

                # 檢查背包UI是否可見 - 確保背包已打開才執行取物
                if not self.is_inventory_ui_visible(game_window):
                    print("F6: 背包UI未打開，無法執行取物功能")
                    self.add_status_message("F6 執行取消 - 背包UI未開啟", "warning")
                    return
                
                self.add_status_message("F6 執行中 - 背包UI檢查通過", "info")
                print("F6: 背包UI檢查通過，開始執行取物")
                    
            except Exception as e:
                print(f"F6: 檢查遊戲視窗失敗: {e}")
                return
            
            print(f"F6: 開始穩定一鍵取物，共 {len(valid_coords)} 個座標")
            
            import time
            
            # 記錄原始滑鼠位置
            original_pos = pyautogui.position()
            print(f"F6: 原始滑鼠位置: {original_pos}")
            
            # 一次性按住 Ctrl 鍵
            pyautogui.keyDown('ctrl')
            time.sleep(0.05)  # 調整為50ms
            print("F6: Ctrl鍵已按下")
            
            try:
                # 優化版本：逐個座標進行 移動->等待->點擊 的序列，放慢速度讓遊戲有足夠響應時間
                for i, (x, y) in enumerate(valid_coords):
                    print(f"F6: 處理座標 {i+1}/{len(valid_coords)}: ({x}, {y})")
                    
                    # 步驟1: 移動滑鼠到目標位置 - 增加移動時間讓遊戲有足夠響應時間
                    pyautogui.moveTo(x, y, duration=0.05)  # 從15ms增加到50ms
                    
                    # 步驟2: 移動後等待，確保滑鼠到位並給遊戲響應時間
                    time.sleep(0.05)  # 從25ms增加到50ms
                    
                    # 步驟3: 點擊
                    pyautogui.click()
                    
                    # 步驟4: 點擊後等待，給遊戲足夠的處理時間
                    time.sleep(0.05)  # 從25ms增加到50ms，確保遊戲有足夠響應時間
                
                print("F6: 優化一鍵取物完成")
                print(f"調試信息 - 成功處理 {len(valid_coords)} 個座標")
                self.add_status_message(f"F6 執行完成 - 處理了 {len(valid_coords)} 個取物座標", "success")
                
                # 恢復原始滑鼠位置 - 使用較慢的移動速度
                pyautogui.moveTo(original_pos.x, original_pos.y, duration=0.05)  # 增加到50ms
                
            finally:
                # 確保 Ctrl 鍵被釋放
                pyautogui.keyUp('ctrl')
                time.sleep(0.05)  # 調整為50ms，確保按鍵釋放完成
                print("F6: Ctrl鍵已釋放")
            
        except Exception as e:
            print(f"F6: 一鍵取物失敗: {str(e)}")
            self.add_status_message(f"F6 執行失敗 - {str(e)}", "error")
            # 確保 Ctrl 鍵被釋放
            try:
                pyautogui.keyUp('ctrl')
                print("F6: 異常處理 - Ctrl鍵已釋放")
            except:
                pass

    def load_pickup_coordinates(self):
        """載入取物座標設定"""
        try:
            if 'pickup_coordinates' in self.config:
                self.pickup_coordinates = self.config['pickup_coordinates']
                print(f"載入取物座標: {len(self.pickup_coordinates)} 個座標")
        except Exception as e:
            print(f"載入取物座標失敗: {str(e)}")
            self.pickup_coordinates = []

    def save_pickup_coordinates(self, parent_window=None):
        """儲存取物座標設定"""
        try:
            self.config['pickup_coordinates'] = self.pickup_coordinates
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print("取物座標已儲存")
            messagebox.showinfo("成功", "取物座標已儲存")
            
            # 重新激活主視窗而不是設定視窗
            if parent_window:
                self.root.lift()
                self.root.focus_force()
                # 根據用戶設定決定是否置頂主視窗
                if self.should_keep_topmost():
                    self.root.attributes("-topmost", True)
                
        except Exception as e:
            print(f"儲存取物座標失敗: {str(e)}")
            messagebox.showerror("錯誤", f"儲存失敗: {str(e)}")

    def setup_pickup_coordinates(self):
        """設定取物座標 - 一次性連續設定5個座標"""
        # 創建設定視窗（設定視窗 - 中間層級）
        setup_window = self.create_settings_window("設定F6取物座標", "600x450")
        setup_window.resizable(False, False)
        
        # 置中顯示
        setup_window.transient(self.root)
        setup_window.grab_set()
        
        # 說明標籤
        info_label = ttk.Label(setup_window, text="一次性連續設定5個取物座標", font=("", 14, "bold"))
        info_label.pack(pady=10)
        
        instruction_text = """操作說明：
1. 點擊「開始連續設定」按鈕
2. 將滑鼠移動到第1個取物位置，按 Enter 確認
3. 依序設定第2、3、4、5個位置
4. 設定完畢後自動儲存並可測試"""
        
        instruction_label = ttk.Label(setup_window, text=instruction_text, 
                                     font=("", 10), justify='left')
        instruction_label.pack(pady=10)
        
        # 座標顯示區域
        coords_frame = ttk.LabelFrame(setup_window, text="座標狀態", padding="10")
        coords_frame.pack(fill='x', padx=20, pady=10)
        
        # 確保pickup_coordinates有5個位置
        while len(self.pickup_coordinates) < 5:
            self.pickup_coordinates.append([0, 0])
        
        # 創建座標顯示標籤
        self.coord_display_labels = []
        for i in range(5):
            frame = ttk.Frame(coords_frame)
            frame.pack(fill='x', pady=2)
            
            ttk.Label(frame, text=f"座標 {i+1}:", width=8).pack(side='left')
            
            coord_label = ttk.Label(frame, text=f"({self.pickup_coordinates[i][0]}, {self.pickup_coordinates[i][1]})", 
                                   width=15, relief='sunken')
            coord_label.pack(side='left', padx=(5, 10))
            self.coord_display_labels.append(coord_label)
            
            # 狀態指示器
            status_label = ttk.Label(frame, text="未設定", foreground="gray", width=10)
            status_label.pack(side='left', padx=5)
            self.coord_display_labels.append(status_label)  # 將狀態標籤也加入列表
        
        # 按鈕區域
        button_frame = ttk.Frame(setup_window)
        button_frame.pack(fill='x', padx=20, pady=20)
        
        ttk.Button(button_frame, text="🚀 開始連續設定", 
                  command=lambda: self.start_continuous_setup(setup_window)).pack(side='left', padx=5)
        ttk.Button(button_frame, text="🧪 測試F6取物", 
                  command=self.test_pickup).pack(side='left', padx=5)
        ttk.Button(button_frame, text="🗑️ 全部清除", 
                  command=self.clear_all_coordinates).pack(side='left', padx=5)
        ttk.Button(button_frame, text="💾 儲存", 
                  command=lambda: [self.save_pickup_coordinates(), setup_window.destroy()]).pack(side='right', padx=5)
        ttk.Button(button_frame, text="❌ 關閉", 
                  command=setup_window.destroy).pack(side='right', padx=5)
        
        # 初始化座標顯示
        self.update_coordinate_display()

    def start_continuous_setup(self, parent_window):
        """開始連續設定5個取物座標"""
        try:
            # 隱藏設定視窗和主視窗
            parent_window.withdraw()
            self.root.withdraw()
            
            # 等待視窗完全隱藏
            time.sleep(0.5)
            
            messagebox.showinfo("開始設定", 
                "即將開始連續設定5個取物座標\n\n" +
                "操作方式：\n" +
                "1. 將滑鼠移動到取物位置\n" +
                "2. 按 Enter 鍵確認該座標\n" +
                "3. 重複5次\n\n" +
                "💡 提示：隨時按 ESC 鍵可以取消設定\n\n" +
                "點擊確定開始...")
            
            import keyboard
            
            # 設定ESC鍵取消標記
            cancel_setup = False
            
            def on_esc_press():
                nonlocal cancel_setup
                cancel_setup = True
                print("❌ 用戶按下ESC，取消設定")
            
            # 註冊ESC鍵監聽
            keyboard.on_press_key('esc', lambda _: on_esc_press())
            
            try:
                for i in range(5):
                    if cancel_setup:
                        messagebox.showinfo("設定取消", "已取消座標設定")
                        break
                    
                    # 提示當前要設定的座標
                    try:
                        # 創建一個小的提示視窗（子視窗 - 最高層級）
                        hint_window = self.create_child_window(f"設定座標 {i+1}/5", "350x120")
                        hint_window.geometry("+100+100")
                        hint_window.attributes('-alpha', 0.9)
                        
                        hint_label = ttk.Label(hint_window, 
                            text=f"請將滑鼠移動到第 {i+1} 個取物位置\n然後按 Enter 鍵確認\n\n按 ESC 鍵取消設定", 
                            font=("", 11), justify='center')
                        hint_label.pack(expand=True)
                        
                        hint_window.update()
                        
                        # 等待 Enter 鍵或檢查取消標記
                        print(f"等待設定座標 {i+1}... (按ESC取消)")
                        
                        # 使用keyboard.wait，但同時檢查cancel_setup標記
                        enter_pressed = False
                        def on_enter_press():
                            nonlocal enter_pressed
                            enter_pressed = True
                        
                        keyboard.on_press_key('enter', lambda _: on_enter_press())
                        
                        # 等待Enter鍵或取消
                        while not enter_pressed and not cancel_setup:
                            time.sleep(0.1)  # 短暫延遲避免CPU占用過高
                        
                        if cancel_setup:
                            hint_window.destroy()
                            break
                        
                        # 獲取滑鼠位置
                        x, y = pyautogui.position()
                        self.pickup_coordinates[i] = [x, y]
                        
                        print(f"✅ 座標 {i+1} 已設定: ({x}, {y})")
                        
                        # 關閉提示視窗
                        hint_window.destroy()
                        
                        # 短暫延遲
                        time.sleep(0.3)
                        
                    except Exception as coord_error:
                        print(f"設定座標 {i+1} 失敗: {coord_error}")
                        try:
                            hint_window.destroy()
                        except:
                            pass
                        break
                
                # 取消鍵盤監聽
                keyboard.unhook_all()
                
                if not cancel_setup:
                    # 更新顯示
                    self.update_coordinate_display()
                    
                    # 自動儲存
                    self.save_pickup_coordinates(parent_window)
                    
                    messagebox.showinfo("設定完成", 
                        f"已成功設定 5 個取物座標！\n\n" +
                        "座標已自動儲存，現在可以使用 F6 鍵進行一鍵取物。")
                    # 重新激活主視窗而不是設定視窗
                    self.root.lift()
                    self.root.focus_force()
                    # 根據用戶設定決定是否置頂主視窗
                    if self.should_keep_topmost():
                        self.root.attributes("-topmost", True)
                else:
                    messagebox.showinfo("設定取消", "座標設定已取消")
                    
            except Exception as e:
                print(f"連續設定失敗: {str(e)}")
                messagebox.showerror("設定失敗", f"連續設定失敗: {str(e)}")
            finally:
                # 取消鍵盤監聽並重新設置全局熱鍵
                try:
                    keyboard.unhook_all()
                    # 重新設置全局熱鍵
                    self.setup_hotkeys()
                except:
                    pass
                    
        except Exception as e:
            print(f"連續設定失敗: {str(e)}")
            messagebox.showerror("設定失敗", f"連續設定失敗: {str(e)}")
        finally:
            # 恢復視窗顯示
            try:
                self.root.deiconify()
                parent_window.deiconify()
            except:
                pass

    def update_coordinate_display(self):
        """更新座標顯示"""
        if hasattr(self, 'coord_display_labels'):
            for i in range(5):
                if i * 2 < len(self.coord_display_labels):
                    # 更新座標顯示
                    coord_label = self.coord_display_labels[i * 2]
                    coord_label.config(text=f"({self.pickup_coordinates[i][0]}, {self.pickup_coordinates[i][1]})")
                    
                    # 更新狀態顯示
                    if (i * 2 + 1) < len(self.coord_display_labels):
                        status_label = self.coord_display_labels[i * 2 + 1]
                        if self.pickup_coordinates[i][0] != 0 or self.pickup_coordinates[i][1] != 0:
                            status_label.config(text="已設定", foreground="green")
                        else:
                            status_label.config(text="未設定", foreground="gray")
        
        # 更新主界面狀態
        self.update_pickup_status()

    def capture_pickup_coordinate(self, index, parent_window):
        """截取指定索引的取物座標"""
        try:
            # 隱藏設定視窗
            parent_window.withdraw()
            self.root.withdraw()
            
            # 等待一段時間讓視窗完全隱藏
            time.sleep(0.5)
            
            # 顯示提示對話框
            result = messagebox.askyesno("座標設定", 
                f"請將滑鼠移動到取物位置 {index+1}，\n然後點擊「確定」來記錄當前滑鼠位置。\n\n點擊「取消」可放棄設定。")
            
            if result:
                # 獲取滑鼠位置
                x, y = pyautogui.position()
                self.pickup_coordinates[index] = [x, y]
                
                print(f"設定取物座標 {index+1}: ({x}, {y})")
                
                # 更新標籤顯示
                if hasattr(self, 'coord_labels') and index < len(self.coord_labels):
                    self.coord_labels[index].config(text=f"({x}, {y})")
                
                # 更新設定視窗中的座標顯示
                self.update_coordinate_display()
                
                messagebox.showinfo("成功", f"取物座標 {index+1} 已設定為: ({x}, {y})")
            
        except Exception as e:
            print(f"截取座標失敗: {str(e)}")
            messagebox.showerror("錯誤", f"截取座標失敗: {str(e)}")
        finally:
            # 恢復視窗顯示
            self.root.deiconify()
            parent_window.deiconify()

    def clear_pickup_coordinate(self, index):
        """清除指定索引的取物座標"""
        if 0 <= index < len(self.pickup_coordinates):
            self.pickup_coordinates[index] = [0, 0]
            if hasattr(self, 'coord_labels') and index < len(self.coord_labels):
                self.coord_labels[index].config(text="(0, 0)")
            # 更新設定視窗中的座標顯示
            self.update_coordinate_display()
            print(f"已清除取物座標 {index+1}")

    def clear_all_coordinates(self):
        """清除所有取物座標"""
        if messagebox.askyesno("確認", "確定要清除所有取物座標嗎？"):
            self.pickup_coordinates = [[0, 0] for _ in range(5)]
            # 更新設定視窗中的座標顯示
            self.update_coordinate_display()
            print("已清除所有取物座標")

    def test_pickup(self):
        """測試F6取物功能"""
        print("=== 開始測試F6取物功能 ===")
        
        # 1. 檢查座標和遊戲視窗設定
        print("檢查座標和遊戲視窗設定...")
        
        # 檢查取物座標
        if not any(x != 0 or y != 0 for x, y in self.pickup_coordinates):
            messagebox.showerror("錯誤", "請先設定至少一個取物座標")
            return
        
        # 檢查遊戲視窗設定
        window_title = self.window_var.get()
        if not window_title:
            messagebox.showerror("錯誤", "請先選擇遊戲視窗")
            return
        
        # 檢查JSON配置是否正確寫入和讀取
        try:
            # 檢查當前配置
            if 'pickup_coordinates' not in self.config:
                messagebox.showerror("錯誤", "取物座標配置未找到，請重新設定")
                return
            
            # 驗證配置中的座標
            config_coords = self.config['pickup_coordinates']
            if len(config_coords) != 5:
                messagebox.showerror("錯誤", "取物座標配置不完整")
                return
            
            # 檢查配置與當前座標是否一致
            for i, (config_x, config_y) in enumerate(config_coords):
                current_x, current_y = self.pickup_coordinates[i]
                if config_x != current_x or config_y != current_y:
                    print(f"警告：座標{i+1}配置不一致 - 配置:({config_x},{config_y}) vs 當前:({current_x},{current_y})")
            
            print("✓ 座標和遊戲視窗設定檢查通過")
            
        except Exception as e:
            messagebox.showerror("錯誤", f"配置檢查失敗: {str(e)}")
            return
        
        try:
            # 獲取遊戲視窗
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                messagebox.showerror("錯誤", f"找不到遊戲視窗: {window_title}")
                return
            
            game_window = windows[0]
            print(f"✓ 找到遊戲視窗: {window_title}")
            
            # 2. 最小化主GUI視窗並激活遊戲視窗
            print("最小化主GUI視窗...")
            self.root.iconify()
            
            print("激活遊戲視窗...")
            game_window.activate()
            
            # 3. 等待1秒（確保遊戲視窗已活耀），不要有確認視窗
            print("等待1秒確保遊戲視窗已激活...")
            time.sleep(1)
            
            # 4. 調用f6_pickup_items()執行實際取物
            print("執行F6取物功能...")
            self.f6_pickup_items()
            
            # 5. 1秒後恢復GUI視窗
            print("等待1秒後恢復GUI視窗...")
            time.sleep(1)
            
            # 6. 測試完成
            self.root.deiconify()
            print("=== F6取物測試完成 ===")
            
        except Exception as e:
            print(f"測試取物功能失敗: {e}")
            # 確保GUI被恢復
            self.root.deiconify()
            messagebox.showerror("錯誤", f"測試取物功能失敗: {str(e)}")

    def update_pickup_status(self):
        """更新取物狀態顯示"""
        if hasattr(self, 'pickup_coords_label'):
            valid_coords = sum(1 for x, y in self.pickup_coordinates if x != 0 or y != 0)
            self.pickup_coords_label.config(text=f"{valid_coords}/5")
            
            if valid_coords > 0:
                self.pickup_coords_label.config(foreground="green")
            else:
                self.pickup_coords_label.config(foreground="gray")

    def on_closing(self):
        """處理GUI關閉事件，提供確認對話框"""
        # 創建自定義的確認對話框，支援Enter快速確認
        result = messagebox.askyesno(
            "確認關閉", 
            "確定要關閉遊戲輔助工具嗎？", 
            default=messagebox.YES  # 預設選擇YES，支援Enter快速確認
        )
        
        if result:
            self.close_app()

    def close_app(self):
        # 添加關閉訊息
        self.add_status_message("工具正在關閉，清理資源中...", "info")
        
        # 儲存設定
        try:
            self.save_config()
            print("設定已儲存")
        except Exception as e:
            print(f"儲存設定失敗: {e}")
        
        # 停止AHK自動點擊
        self.stop_auto_click_ahk()
        
        # 清理鍵盤監聽器
        try:
            keyboard.unhook_all()
        except:
            pass
        
        self.monitoring = False
        self.add_status_message("工具已成功關閉", "info")
        self.root.quit()

    def restart_app(self):
        """重新啟動應用程式"""
        self.monitoring = False
        self.save_config()
        
        try:
            if getattr(sys, 'frozen', False):
                # 如果是打包後的exe
                # 直接重新啟動exe，不依賴原始的啟動方式
                import subprocess
                subprocess.Popen([sys.executable], 
                               cwd=os.path.dirname(sys.executable),
                               creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                # 如果是開發環境(.py檔案)
                os.execv(sys.executable, ['python'] + sys.argv)
        except Exception as e:
            print(f"重啟失敗: {e}")
            messagebox.showerror("錯誤", f"無法重新啟動程式: {e}")
            return
        
        # 關閉當前程式
        self.root.quit()
        self.root.destroy()
        sys.exit(0)

    def update_live_mana_preview(self, img, mana_percent):
        """動態更新魔力預覽圖片，減少更新頻率以避免閃爍"""
        import time as time_module

        # 檢查預覽是否啟用
        if not self.preview_enabled.get():
            return

        current_time = time_module.time() * 1000  # 轉換為毫秒

        # 獲取用戶設置的更新間隔
        try:
            update_interval = int(self.preview_interval_var.get())
        except ValueError:
            update_interval = 250  # 預設250ms

        # 只在魔力變化或達到更新間隔時才更新
        should_update = (
            abs(mana_percent - self.last_mana_percent) >= 5 or  # 魔力變化超過5%
            (current_time - self.last_mana_preview_update) >= update_interval  # 時間間隔
        )

        if not should_update:
            return

        try:
            # 使用tkinter的after方法來非同步更新，避免阻塞
            self.root.after(0, lambda: self._update_mana_preview_image(img, mana_percent))

            # 更新追蹤變數
            self.last_mana_preview_update = current_time
            self.last_mana_percent = mana_percent

        except Exception as e:
            print(f"魔力預覽更新失敗: {e}")

    def _update_mana_preview_image(self, img, mana_percent):
        """實際更新魔力預覽圖片的私有方法"""
        try:
            # 創建PIL圖片
            pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

            # 在圖片上繪製當前魔力指示器
            self.draw_mana_indicator(pil_img, mana_percent)

            # 在圖片上繪製刻度線
            self.draw_scale_lines(pil_img)

            # 等比例縮放圖片到合適尺寸
            resized_img = self.resize_and_center_image(pil_img, self.preview_size)

            # 更新預覽圖片
            self.mana_preview_image = ImageTk.PhotoImage(resized_img)
            if hasattr(self, 'mana_preview_label'):
                self.mana_preview_label.config(image=self.mana_preview_image)

        except Exception as e:
            print(f"更新魔力預覽圖片失敗: {e}")

    def draw_mana_indicator(self, img, mana_percent):
        """在預覽圖片上繪製當前魔力指示器"""
        width, height = img.size

        # 計算魔力對應的高度位置
        mana_height = int(height * (100 - mana_percent) / 100)

        # 繪製魔力指示線（藍色粗線）
        draw = ImageDraw.Draw(img)
        draw.line([(0, mana_height), (width, mana_height)],
                 fill=(0, 0, 255), width=3)

        # 繪製魔力百分比文字在指示線下方
        text = f"{mana_percent:.1f}%"
        bbox = draw.textbbox((0, 0), text, font=None)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # 計算文字位置：指示線下方5像素，水平居中
        text_x = (width - text_width) // 2
        text_y = mana_height + 5

        # 確保文字不會超出圖片邊界
        if text_y + text_height > height:
            text_y = mana_height - text_height - 5  # 如果下方空間不夠，放在上方

        # 繪製文字背景（半透明黑色矩形）
        draw.rectangle([text_x - 2, text_y - 2, text_x + text_width + 2, text_y + text_height + 2],
                      fill=(0, 0, 0, 128))

        # 繪製白色文字
        draw.text((text_x, text_y), text, fill=(255, 255, 255), font=None)

        # 添加黑色邊框讓文字更清楚
        draw.text((text_x + 1, text_y), text, fill=(0, 0, 0), font=None)
        draw.text((text_x - 1, text_y), text, fill=(0, 0, 0), font=None)
        draw.text((text_x, text_y + 1), text, fill=(0, 0, 0), font=None)
        draw.text((text_x, text_y - 1), text, fill=(0, 0, 0), font=None)

    def load_config(self):
        """載入設定"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                self.add_status_message("設定檔案載入成功", "success")
            else:
                self.config = {}
                self.add_status_message("設定檔案不存在，使用預設設定", "info")

            # 載入區域設定
            self.selected_region = self.config.get('region')
            self.selected_mana_region = self.config.get('mana_region')
            self.inventory_region = self.config.get('inventory_region')
            self.empty_inventory_colors = self.config.get('empty_inventory_colors', [])
            self.inventory_grid_positions = self.config.get('inventory_grid_positions', [])
            self.grid_offset_x = self.config.get('grid_offset_x', 0)
            self.grid_offset_y = self.config.get('grid_offset_y', 0)

            # 載入背包UI設定
            self.inventory_ui_region = self.config.get('inventory_ui_region')

            # 如果有UI區域設定，嘗試從檔案載入UI截圖
            if self.inventory_ui_region:
                self.load_ui_screenshot_from_file()

            # 載入介面UI設定
            self.interface_ui_region = self.config.get('interface_ui_region')

            # 如果有介面UI區域設定，嘗試從檔案載入介面UI截圖
            if self.interface_ui_region:
                self.load_interface_ui_screenshot_from_file()

            # 更新背包顏色記錄狀態顯示
            if hasattr(self, 'empty_color_label') and self.empty_inventory_colors:
                recorded_count = len([c for c in self.empty_inventory_colors if c != (0, 0, 0)])
                self.empty_color_label.config(text=f"已記錄 {recorded_count}/60 格顏色", background="lightgreen")

            # 更新背包UI記錄狀態顯示
            if hasattr(self, 'inventory_ui_label') and self.inventory_ui_region:
                self.inventory_ui_label.config(text="已記錄背包UI", background="lightgreen")
                # 嘗試更新UI預覽（如果Canvas已創建）
                if hasattr(self, 'ui_preview_canvas'):
                    self.update_ui_preview()

            # 更新介面UI記錄狀態顯示
            if hasattr(self, 'interface_ui_label') and self.interface_ui_region:
                self.interface_ui_label.config(text=self.get_interface_ui_region_text(), background="lightgreen")
                # 嘗試更新介面UI預覽（如果Canvas已創建）
                if hasattr(self, 'interface_ui_preview_canvas'):
                    self.update_interface_ui_preview()

            # 載入遊戲視窗標題
            if 'inventory_window_title' in self.config:
                self.inventory_window_var.set(self.config['inventory_window_title'])
            elif 'window_title' in self.config:
                self.inventory_window_var.set(self.config['window_title'])

            # 同時設定血魔監控的視窗變數（如果UI已創建）
            if hasattr(self, 'window_var'):
                if 'window_title' in self.config:
                    self.window_var.set(self.config['window_title'])

            # 載入血魔監控設定
            self.blood_magic_enabled = self.config.get('blood_magic_enabled', False)
            self.blood_magic_region = self.config.get('blood_magic_region', None)
            self.blood_magic_threshold = self.config.get('blood_magic_threshold', 50)
            self.blood_magic_window_title = self.config.get('blood_magic_window_title', '')

            # 載入其他設定
            self.monitor_interval = self.config.get('monitor_interval', 0.1)  # 預設100ms
            self.auto_clear_enabled = self.config.get('auto_clear_enabled', False)
            self.clear_interval = self.config.get('clear_interval', 30)

            # 更新檢查頻率UI元件（如果UI已創建）
            if hasattr(self, 'monitor_interval_var'):
                interval_ms = int(self.monitor_interval * 1000)
                self.monitor_interval_var.set(str(interval_ms))

            # 載入預覽設定
            if hasattr(self, 'preview_enabled'):
                preview_enabled = self.config.get('preview_enabled', True)
                self.preview_enabled.set(preview_enabled)
            if hasattr(self, 'preview_interval_var'):
                preview_interval = self.config.get('preview_interval', 250)
                self.preview_interval_var.set(str(preview_interval))

            # 載入觸發設定
            if 'settings' in self.config:
                print(f"載入觸發設定: {len(self.config['settings'])} 個設定")
                for setting in self.config['settings']:
                    print(f"  - {setting.get('type', 'health')} {setting.get('percent', 0)}%: {setting.get('key', '')}")
            else:
                print("沒有找到觸發設定")

            # 載入顏色檢測參數 - 使用優化的預設值
            self.health_threshold = self.config.get('health_threshold', 0.8)  # 優化預設值: 0.8
            self.red_h_range = self.config.get('red_h_range', 5)  # 優化預設值: 5
            self.green_h_range = self.config.get('green_h_range', 40)
            
            # 載入新增的HSV參數
            self.red_saturation_min = self.config.get('red_saturation_min', 50)
            self.red_value_min = self.config.get('red_value_min', 50)
            self.green_saturation_min = self.config.get('green_saturation_min', 50)
            self.green_value_min = self.config.get('green_value_min', 50)

            # 載入介面UI檢測參數
            self.interface_ui_mse_threshold = int(self.config.get('interface_ui_mse_threshold', 800))
            self.interface_ui_ssim_threshold = float(self.config.get('interface_ui_ssim_threshold', 0.6))
            self.interface_ui_hist_threshold = float(self.config.get('interface_ui_hist_threshold', 0.7))
            self.interface_ui_color_threshold = int(self.config.get('interface_ui_color_threshold', 35))

            # 更新UI變數（如果UI已創建）
            if hasattr(self, 'mse_threshold_var'):
                self.mse_threshold_var.set(str(self.interface_ui_mse_threshold))
            if hasattr(self, 'ssim_threshold_var'):
                self.ssim_threshold_var.set(str(self.interface_ui_ssim_threshold))
            if hasattr(self, 'hist_threshold_var'):
                self.hist_threshold_var.set(str(self.interface_ui_hist_threshold))
            if hasattr(self, 'color_threshold_var'):
                self.color_threshold_var.set(str(self.interface_ui_color_threshold))

            # 載入觸發選項
            self.multi_trigger_var.set(self.config.get('multi_trigger', False))

            # 載入GUI最上方設定
            always_on_top = self.config.get('always_on_top', True)  # 預設為True
            self.always_on_top_var.set(always_on_top)
            self.root.attributes("-topmost", always_on_top)

            # 如果設定檔案中沒有always_on_top設定，保存預設值
            if 'always_on_top' not in self.config:
                self.config['always_on_top'] = always_on_top
                try:
                    with open(self.config_file, 'w', encoding='utf-8') as f:
                        json.dump(self.config, f, indent=2, ensure_ascii=False)
                    print("已保存預設的GUI最上方設定")
                except Exception as save_error:
                    print(f"保存預設設定失敗: {save_error}")

            # 載入窗口位置和大小
            if 'window_geometry' in self.config:
                try:
                    saved_geometry = self.config['window_geometry']
                    self.root.geometry(saved_geometry)
                    print(f"已恢復窗口位置: {saved_geometry}")
                except Exception as e:
                    print(f"恢復窗口位置失敗: {e}")

            # 載入F6一鍵取物座標
            self.pickup_coordinates = self.config.get('pickup_coordinates', [])
            print(f"載入F6取物座標: {len(self.pickup_coordinates)} 個座標")
            
            # 確保pickup_coordinates有5個位置
            while len(self.pickup_coordinates) < 5:
                self.pickup_coordinates.append([0, 0])
            
            # 更新取物狀態顯示
            if hasattr(self, 'pickup_coords_label'):
                self.update_pickup_status()

            # 載入連段設定
            if 'combo_sets' in self.config:
                self.combo_sets = self.config['combo_sets']
                # 確保向後相容性，為舊配置添加缺失的字段
                for combo_set in self.combo_sets:
                    if 'trigger_delay' not in combo_set:
                        combo_set['trigger_delay'] = ''
                    if 'stationary_attacks' not in combo_set:
                        combo_set['stationary_attacks'] = [False, False, False, False, False]
                
                # 確保combo_sets長度正確
                while len(self.combo_sets) < 3:
                    self.combo_sets.append({
                        'trigger_key': 'Q' if len(self.combo_sets) == 0 else 'W' if len(self.combo_sets) == 1 else 'E',
                        'trigger_delay': '',
                        'combo_keys': ['', '', '', '', ''],
                        'delays': ['', '', '', '', ''],
                        'stationary_attacks': [False, False, False, False, False]
                    })
                self.combo_sets = self.combo_sets[:3]  # 確保不超過3個
                
                print(f"載入連段設定: {len(self.combo_sets)} 個套組")
            if 'combo_enabled' in self.config:
                self.combo_enabled = self.config['combo_enabled']
                # 確保combo_enabled長度正確
                while len(self.combo_enabled) < 3:
                    self.combo_enabled.append(False)
                self.combo_enabled = self.combo_enabled[:3]  # 確保不超過3個
                print(f"載入連段啟用狀態: {self.combo_enabled}")
            else:
                # 如果配置文件中沒有combo_enabled，重置為預設值
                self.combo_enabled = [False, False, False]
            
            # 更新組合UI元件
            self.update_combo_ui_from_config()

            # 更新UI
            self.update_offset_labels()
            self.update_inventory_preview_from_current()

            # 更新區域顯示標籤
            if hasattr(self, 'region_label'):
                self.region_label.config(text=self.get_region_text(), 
                                       background="lightgreen" if self.config.get('region') else "lightgray")
            if hasattr(self, 'mana_region_label'):
                self.mana_region_label.config(text=self.get_mana_region_text(), 
                                            background="lightgreen" if self.config.get('mana_region') else "lightgray")

            # 更新觸發設定列表
            if hasattr(self, 'load_settings_to_tree'):
                self.load_settings_to_tree()

            # 確保UI預覽被正確更新
            if hasattr(self, 'ui_preview_canvas'):
                self.update_ui_preview()

        except Exception as e:
            self.add_status_message(f"設定檔案載入失敗 - {str(e)}", "error")
            print(f"載入設定時發生錯誤: {e}")
            # 使用預設值
            self.config = {}

    def save_config(self):
        """儲存血魔監控設定"""
        try:
            # 儲存遊戲視窗設定
            self.config['window_title'] = self.window_var.get()

            # 儲存區域設定
            if hasattr(self, 'selected_region') and self.selected_region:
                self.config['region'] = self.selected_region
            if hasattr(self, 'selected_mana_region') and self.selected_mana_region:
                self.config['mana_region'] = self.selected_mana_region
            
            # 儲存背包相關設定
            if hasattr(self, 'inventory_region') and self.inventory_region:
                self.config['inventory_region'] = self.inventory_region
            if hasattr(self, 'inventory_ui_region') and self.inventory_ui_region:
                self.config['inventory_ui_region'] = self.inventory_ui_region
            if hasattr(self, 'interface_ui_region') and self.interface_ui_region:
                self.config['interface_ui_region'] = self.interface_ui_region
            if hasattr(self, 'empty_inventory_colors') and self.empty_inventory_colors:
                self.config['empty_inventory_colors'] = self.empty_inventory_colors
            if hasattr(self, 'inventory_grid_positions') and self.inventory_grid_positions:
                self.config['inventory_grid_positions'] = self.inventory_grid_positions
            if hasattr(self, 'grid_offset_x'):
                self.config['grid_offset_x'] = self.grid_offset_x
            if hasattr(self, 'grid_offset_y'):
                self.config['grid_offset_y'] = self.grid_offset_y

            # 儲存觸發設定
            settings = []
            if hasattr(self, 'settings_tree'):
                for item in self.settings_tree.get_children():
                    values = self.settings_tree.item(item, 'values')
                    if len(values) >= 4:
                        setting_type = "health" if values[0] == "血量" else "mana"
                        settings.append({
                            'type': setting_type,
                            'percent': int(values[1]),
                            'key': values[2],
                            'cooldown': int(values[3])
                        })
            if settings:
                self.config['settings'] = settings

            # 儲存預覽設定
            if hasattr(self, 'preview_enabled'):
                self.config['preview_enabled'] = self.preview_enabled.get()
            if hasattr(self, 'preview_interval_var'):
                self.config['preview_interval'] = int(self.preview_interval_var.get())

            # 儲存顏色檢測參數
            self.config['health_threshold'] = self.health_threshold
            self.config['red_h_range'] = self.red_h_range
            self.config['green_h_range'] = self.green_h_range
            
            # 儲存新增的HSV參數
            self.config['red_saturation_min'] = self.red_saturation_min
            self.config['red_value_min'] = self.red_value_min
            self.config['green_saturation_min'] = self.green_saturation_min
            self.config['green_value_min'] = self.green_value_min

            # 儲存介面UI檢測參數
            self.config['interface_ui_mse_threshold'] = self.interface_ui_mse_threshold
            self.config['interface_ui_ssim_threshold'] = self.interface_ui_ssim_threshold
            self.config['interface_ui_hist_threshold'] = self.interface_ui_hist_threshold
            self.config['interface_ui_color_threshold'] = self.interface_ui_color_threshold

            # 儲存觸發選項
            self.config['multi_trigger'] = self.multi_trigger_var.get()

            # 儲存GUI最上方設定
            self.config['always_on_top'] = self.always_on_top_var.get()

            # 儲存窗口位置和大小
            try:
                current_geometry = self.root.geometry()
                self.config['window_geometry'] = current_geometry
                print(f"已儲存窗口位置: {current_geometry}")
            except Exception as e:
                print(f"儲存窗口位置失敗: {e}")

            # 儲存連段設定
            if hasattr(self, 'combo_sets') and self.combo_sets:
                self.config['combo_sets'] = self.combo_sets
            if hasattr(self, 'combo_enabled') and self.combo_enabled:
                self.config['combo_enabled'] = self.combo_enabled

            # 儲存監控間隔
            if hasattr(self, 'monitor_interval'):
                self.config['monitor_interval'] = self.monitor_interval
            # 儲存檢查頻率設定
            if hasattr(self, 'monitor_interval_var'):
                try:
                    interval_ms = int(self.monitor_interval_var.get())
                    self.config['monitor_interval'] = interval_ms / 1000.0  # 轉換為秒儲存
                except (ValueError, AttributeError):
                    self.config['monitor_interval'] = 0.1  # 預設100ms

            # 儲存到檔案
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)

            self.add_status_message("設定檔案儲存成功", "success")
            messagebox.showinfo("成功", "所有紀錄都已儲存")
        except Exception as e:
            self.add_status_message(f"設定檔案儲存失敗 - {str(e)}", "error")
            messagebox.showerror("錯誤", f"儲存失敗: {str(e)}")

    def setup_auto_click_listener(self):
        """設定自動點擊功能 - 自動啟動AHK腳本"""
        try:
            print("設定自動點擊功能...")
            
            # 自動啟動AHK腳本
            self.start_auto_click_ahk()
                
        except Exception as e:
            print(f"設定自動點擊功能失敗: {e}")

    def start_auto_click_ahk(self):
        """啟動AHK自動點擊腳本 - 支援EXE版本優先"""
        try:
            # 檢查是否已經有進程在運行
            if self.auto_click_process and self.auto_click_process.poll() is None:
                print("AHK自動點擊已經在運行中")
                return
            
            # 獲取當前進程名稱，支援編譯前後
            if getattr(sys, 'frozen', False):
                # 如果是打包後的exe
                process_name = "GameTools_HealthMonitor.exe"
            else:
                # 如果是開發環境，獲取實際的Python可執行文件名稱
                actual_executable = os.path.basename(sys.executable)
                print(f"實際Python可執行文件: {actual_executable}")
                print(f"完整路徑: {sys.executable}")
                
                # 檢查所有可能的Python進程名稱
                current_pid = os.getpid()
                current_process = psutil.Process(current_pid)
                actual_process_name = current_process.name()
                print(f"當前進程PID: {current_pid}")
                print(f"當前進程名稱: {actual_process_name}")
                
                # 使用實際的進程名稱
                process_name = actual_process_name
            
            print(f"將傳遞給AHK的進程名稱: {process_name}")
            
            # 優先檢查EXE版本
            if os.path.exists(self.auto_click_exe_path):
                print(f"找到EXE版本: {self.auto_click_exe_path}")
                # 以管理員權限直接執行EXE，傳遞Python進程名稱作為參數
                import ctypes
                try:
                    # 嘗試以管理員權限啟動
                    ctypes.windll.shell32.ShellExecuteW(
                        None, 
                        "runas", 
                        self.auto_click_exe_path, 
                        process_name, 
                        None, 
                        1
                    )
                    print("🟢 AHK自動點擊(EXE版)已以管理員權限啟動")
                    print("💡 現在可以直接使用 CTRL+左鍵 進行自動連點")
                    print("💡 當主程式退出時，AHK腳本會自動關閉")
                except Exception as admin_error:
                    print(f"管理員權限啟動失敗，嘗試普通啟動: {admin_error}")
                    # 如果管理員權限啟動失敗，則使用普通方式
                    self.auto_click_process = subprocess.Popen([
                        self.auto_click_exe_path,
                        process_name
                    ], creationflags=subprocess.CREATE_NO_WINDOW)
                    print("🟢 AHK自動點擊(EXE版)已啟動")
                return
            
            # 如果沒有EXE版本，檢查AHK腳本
            elif os.path.exists(self.auto_click_script_path):
                print(f"找到AHK腳本: {self.auto_click_script_path}")
                
                # 尋找AutoHotkey可執行文件
                ahk_paths = [
                    r"C:\Program Files\AutoHotkey\v2\AutoHotkey64.exe",
                    r"C:\Program Files\AutoHotkey\v2\AutoHotkey32.exe", 
                    r"C:\Program Files\AutoHotkey\AutoHotkey.exe",
                    r"C:\Program Files (x86)\AutoHotkey\AutoHotkey.exe"
                ]
                
                ahk_exe = None
                for path in ahk_paths:
                    if os.path.exists(path):
                        ahk_exe = path
                        break
                
                if not ahk_exe:
                    print("❌ 未找到AutoHotkey程式，請確保已安裝AutoHotkey或使用EXE版本")
                    return
                
                # 啟動AHK腳本，傳遞Python進程名稱作為參數
                self.auto_click_process = subprocess.Popen([
                    ahk_exe, 
                    self.auto_click_script_path,
                    process_name
                ], creationflags=subprocess.CREATE_NO_WINDOW)
                
                print("🟢 AHK自動點擊已啟動")
                print("💡 現在可以直接使用 CTRL+左鍵 進行自動連點")
                print("💡 當主程式退出時，AHK腳本會自動關閉")
                
            else:
                print("❌ 未找到AHK腳本或EXE文件")
                print(f"請確保存在以下文件之一：")
                print(f"  - {self.auto_click_exe_path}")
                print(f"  - {self.auto_click_script_path}")
                
        except Exception as e:
            print(f"❌ 啟動AHK自動點擊失敗: {e}")

    def stop_auto_click_ahk(self):
        """停止AHK自動點擊腳本"""
        try:
            if self.auto_click_process and self.auto_click_process.poll() is None:
                self.auto_click_process.terminate()
                self.auto_click_process.wait(timeout=3)
                print("🔴 AHK自動點擊已停止")
            else:
                print("AHK自動點擊未運行")
        except subprocess.TimeoutExpired:
            # 如果無法正常終止，強制結束
            self.auto_click_process.kill()
            print("🔴 AHK自動點擊已強制停止")
        except Exception as e:
            print(f"停止AHK自動點擊時發生錯誤: {e}")
        finally:
            self.auto_click_process = None

    def on_mouse_click(self, x, y, button, pressed):
        """滑鼠點擊事件處理"""
        try:
            from pynput import mouse
            
            # 添加調試輸出
            if button == mouse.Button.left:
                self.left_button_pressed = pressed
                print(f"滑鼠左鍵事件: pressed={pressed}, ctrl_pressed={self.ctrl_pressed}")
                
                # 檢查是否滿足CTRL+左鍵條件
                if self.ctrl_pressed and self.left_button_pressed:
                    if not self.auto_click_active:
                        print("檢測到 CTRL+左鍵組合，開始自動點擊")
                        self.start_auto_click()
                else:
                    # 任一鍵釋放都停止自動點擊
                    if self.auto_click_active:
                        print("CTRL+左鍵組合中斷，停止自動點擊")
                        self.stop_auto_click()
                    
        except Exception as e:
            print(f"滑鼠點擊事件處理錯誤: {e}")

    def toggle_auto_click_mode(self):
        """切換自動點擊模式（主要方案）"""
        if self.auto_click_active:
            self.stop_auto_click()
            print("🔴 自動點擊已停止（Ctrl+Shift+X）")
        else:
            self.start_auto_click()
            print("🟢 自動點擊已啟動（Ctrl+Shift+X再次按下可停止）")

    def toggle_auto_click(self):
        """切換自動點擊狀態（備用方案）"""
        if self.auto_click_active:
            self.stop_auto_click()
            print("🔴 自動點擊已停止（Ctrl+Shift+Z）")
        else:
            self.start_auto_click()
            print("🟢 自動點擊已啟動（Ctrl+Shift+Z再次按下可停止）")

    def on_ctrl_press(self, event=None):
        """CTRL鍵按下事件（保留作為備用）"""
        pass

    def on_ctrl_release(self, event=None):
        """CTRL鍵釋放事件（保留作為備用）"""
        pass

    def start_auto_click(self):
        """開始自動點擊"""
        if not self.auto_click_active:
            print("啟動自動點擊...")
            self.auto_click_active = True
            self.auto_click_running = True
            # 在新執行緒中執行自動點擊
            self.auto_click_thread = threading.Thread(target=self.auto_click_loop, daemon=True)
            self.auto_click_thread.start()
            print("自動點擊執行緒已啟動")
        else:
            print("自動點擊已經在運行中")

    def stop_auto_click(self):
        """停止自動點擊"""
        if self.auto_click_active:
            print("停止自動點擊...")
            self.auto_click_active = False
            self.auto_click_running = False
            print("自動點擊已停止")
        else:
            print("自動點擊已經是停止狀態")
        self.auto_click_running = False

    def auto_click_loop(self):
        """自動點擊循環 - 模擬AHK的while循環行為"""
        print("進入自動點擊循環")
        click_count = 0
        
        # 類似AHK的 while (GetKeyState("MButton", "P") && !clickStop)
        while self.auto_click_running and self.auto_click_active:
            try:
                # 檢查CTRL和左鍵是否仍然按下 (類似AHK的GetKeyState檢查)
                if not (self.ctrl_pressed and self.left_button_pressed):
                    print("按鍵狀態改變，結束自動點擊循環")
                    break
                
                # 獲取當前滑鼠位置
                current_x, current_y = pyautogui.position()
                
                # 執行點擊 (類似AHK的Click())
                pyautogui.leftClick(current_x, current_y)
                click_count += 1
                
                if click_count % 20 == 0:  # 每20次點擊輸出一次狀態
                    print(f"已點擊 {click_count} 次，位置: ({current_x}, {current_y})")
                
                # 等待指定間隔 (類似AHK的Sleep(滑鼠連點速度))
                time.sleep(self.click_interval)
                    
            except Exception as e:
                print(f"自動點擊錯誤: {e}")
                break
                
        # 清理狀態
        print(f"自動點擊循環結束，總共點擊 {click_count} 次")
        self.auto_click_active = False
        self.auto_click_running = False









    def check_inventory_ui_exists(self, game_window):
        """檢測背包UI是否存在（簡化版本）"""
        if not self.inventory_ui_region:
            return False
            
        try:
            # 擷取當前背包UI區域
            with mss.mss() as sct:
                monitor = {
                    "top": game_window.top + self.inventory_ui_region['y'],
                    "left": game_window.left + self.inventory_ui_region['x'],
                    "width": self.inventory_ui_region['width'],
                    "height": self.inventory_ui_region['height']
                }

                screenshot = sct.grab(monitor)
                current_img = np.array(screenshot)
                current_img = cv2.cvtColor(current_img, cv2.COLOR_BGRA2BGR)

                # 如果有參考截圖，進行比較
                if hasattr(self, 'inventory_ui_screenshot') and self.inventory_ui_screenshot is not None:
                    if current_img.shape == self.inventory_ui_screenshot.shape:
                        # 使用更寬鬆的閾值用於檢測（因為只是檢測是否存在）
                        mse = np.mean((current_img - self.inventory_ui_screenshot) ** 2)
                        mse_threshold = 500  # 比較寬鬆的閾值
                        
                        current_main_color = np.mean(current_img, axis=(0, 1))
                        recorded_main_color = np.mean(self.inventory_ui_screenshot, axis=(0, 1))
                        color_diff = np.mean(np.abs(current_main_color - recorded_main_color))
                        color_threshold = 30  # 較寬鬆的顏色閾值
                        
                        is_visible = (mse < mse_threshold) and (color_diff < color_threshold)
                        print(f"背包UI檢測: MSE={mse:.2f}, 顏色差={color_diff:.2f}, 存在={is_visible}")
                        return is_visible
                    else:
                        print(f"背包UI檢測: 圖片尺寸不匹配")
                        return False
                else:
                    # 如果沒有參考截圖，使用簡單的像素檢測
                    # 檢查是否有足夠的非黑色像素（假設背包UI有內容）
                    gray = cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY)
                    non_black_pixels = np.sum(gray > 50)  # 計算非黑色像素
                    total_pixels = gray.shape[0] * gray.shape[1]
                    ratio = non_black_pixels / total_pixels
                    
                    # 如果非黑色像素比例超過30%，認為UI存在
                    ui_exists = ratio > 0.3
                    print(f"背包UI檢測: 非黑色像素比例={ratio:.2f}, 存在={ui_exists}")
                    return ui_exists
                    
        except Exception as e:
            print(f"檢測背包UI存在性失敗: {e}")
            return False

    def create_version_tab(self):
        """創建版本檢查分頁"""
        main_frame = self.version_frame
        
        # 標題
        title_label = ttk.Label(main_frame, text="🔄 版本檢查與更新", font=('Microsoft YaHei', 18, 'bold'))
        title_label.pack(pady=(15, 35))
        
        # 當前版本資訊框架
        current_frame = ttk.LabelFrame(main_frame, text="當前版本資訊", padding="20")
        current_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(current_frame, text="目前版本:", font=('Microsoft YaHei', 12, 'bold')).pack(anchor=tk.W)
        current_version_label = ttk.Label(current_frame, text=CURRENT_VERSION, 
                                        font=('Microsoft YaHei', 14, 'bold'), foreground='blue')
        current_version_label.pack(anchor=tk.W, pady=(5, 0))
        
        # 遠端版本資訊框架
        remote_frame = ttk.LabelFrame(main_frame, text="最新版本資訊", padding="20")
        remote_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.latest_version_var = tk.StringVar(value="檢查中...")
        ttk.Label(remote_frame, text="最新版本:", font=('Microsoft YaHei', 12, 'bold')).pack(anchor=tk.W)
        self.latest_version_label = ttk.Label(remote_frame, textvariable=self.latest_version_var,
                                            font=('Microsoft YaHei', 14, 'bold'), foreground='green')
        self.latest_version_label.pack(anchor=tk.W, pady=(5, 10))
        
        # 版本狀態顯示
        self.version_status_var = tk.StringVar(value="正在檢查版本...")
        self.version_status_label = ttk.Label(remote_frame, textvariable=self.version_status_var,
                                            font=('Microsoft YaHei', 11))
        self.version_status_label.pack(anchor=tk.W, pady=(0, 10))
        
        # 更新說明
        self.release_notes_var = tk.StringVar(value="")
        self.release_notes_label = ttk.Label(remote_frame, textvariable=self.release_notes_var,
                                           wraplength=500, font=('Microsoft YaHei', 10), foreground='gray')
        self.release_notes_label.pack(anchor=tk.W, pady=(0, 10))
        
        # 按鈕框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(25, 0))
        
        # 檢查更新按鈕
        self.check_update_btn = ttk.Button(button_frame, text="🔍 檢查更新", 
                                         command=self.check_for_updates)
        self.check_update_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 前往下載按鈕
        self.download_btn = ttk.Button(button_frame, text="⬇️ 前往下載頁面", 
                                     command=self.open_download_page, state='disabled')
        self.download_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 檢查GitHub連接按鈕
        self.test_connection_btn = ttk.Button(button_frame, text="🔗 測試連接", 
                                            command=self.test_github_connection)
        self.test_connection_btn.pack(side=tk.LEFT)
        
        # 自動靜默檢查版本（只在有新版本時彈出提醒）
        self.root.after(2000, self.silent_version_check)

    def create_combo_tab(self):
        """創建技能連段分頁 - 橫向寬敞佈局"""
        main_frame = self.combo_frame
        
        # 標題
        title_label = ttk.Label(main_frame, text="⚡ 技能連段系統", font=('Microsoft YaHei', 20, 'bold'))
        title_label.pack(pady=(15, 35))
        
        # 創建橫向佈局的主框架
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 初始化連段套組設定
        self.initialize_combo_sets()
        
        # 創建3個連段套組的橫向佈局
        for i in range(3):
            self.create_combo_set_frame_horizontal(content_frame, i)
        
        # 全域控制區域 - 橫向佈局
        control_frame = ttk.LabelFrame(content_frame, text="全域控制", padding="20")
        control_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(25, 0))
        
        # 控制按鈕區域
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.combo_start_btn = ttk.Button(button_frame, text="▶️ 啟動連段系統", 
                                        command=self.start_combo_system, width=15)
        self.combo_start_btn.pack(side=tk.LEFT, padx=(0, 15))
        
        self.combo_stop_btn = ttk.Button(button_frame, text="⏹️ 停止連段系統", 
                                       command=self.stop_combo_system, state=tk.DISABLED, width=15)
        self.combo_stop_btn.pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Button(button_frame, text="💾 儲存設定", command=self.save_combo_config, width=12).pack(side=tk.LEFT)
        
        # 狀態顯示區域
        status_frame = ttk.Frame(control_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(status_frame, text="系統狀態:", font=('Microsoft YaHei', 13, 'bold')).pack(side=tk.LEFT)
        self.combo_status_label = ttk.Label(status_frame, text="未啟動", foreground="red", font=('Microsoft YaHei', 13))
        self.combo_status_label.pack(side=tk.LEFT, padx=(8, 0))
        
        # 設定content_frame的網格佈局
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        content_frame.columnconfigure(2, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # 使用說明區域
        help_frame = ttk.LabelFrame(main_frame, text="使用說明", padding="20")
        help_frame.pack(fill=tk.X, pady=(25, 0))
        
        help_text = """🎯 技能連段使用說明：

1. 設定觸發技能：選擇一個按鍵作為連段的觸發鍵
2. 設定連段技能：選擇1-5個技能按鍵作為連段序列
3. 設定延遲時間：每個連段之間的延遲時間（毫秒）
4. 啟用套組：勾選要使用的連段套組
5. 啟動系統：點擊"啟動連段系統"開始監聽觸發鍵

💡 提示：
• 支援的按鍵：QWERTYUIOPASDFGHJKLZXCVBNM1234567890
• 延遲時間建議：100-500毫秒
• 可以同時啟用多個套組
• 系統會在背景運行，不影響其他操作

⚠️ 重要提醒：
• 觸發鍵會同時發送到遊戲和觸發連段功能
• 如果勾選"原地攻擊"，技能將以 Shift+技能鍵 的方式執行
• 在遊戲聊天時使用觸發鍵會輸入英文字，這是無法避免的
• 建議在聊天時使用 F9 暫停功能避免意外觸發"""
        
        help_label = ttk.Label(help_frame, text=help_text, justify=tk.LEFT, 
                             font=('Arial', 9), foreground="gray")
        help_label.pack(anchor=tk.W)

    def initialize_combo_sets(self):
        """初始化連段套組設定"""
        if not self.combo_sets:
            # 預設設定
            for i in range(3):
                combo_set = {
                    'trigger_key': 'Q' if i == 0 else 'W' if i == 1 else 'E',
                    'trigger_delay': '',  # 觸發按鍵後的初始延遲時間
                    'combo_keys': ['', '', '', '', ''],  # 5個連段技能
                    'delays': ['', '', '', '', ''],  # 對應的延遲時間，預設為空
                    'stationary_attacks': [False, False, False, False, False],  # 原地攻擊設定
                }
                self.combo_sets.append(combo_set)

    def create_combo_set_frame_horizontal(self, parent, set_index):
        """創建單個連段套組的橫向框架"""
        set_frame = ttk.LabelFrame(parent, text=f"連段套組 {set_index + 1}", padding="15")
        set_frame.grid(row=0, column=set_index, sticky=(tk.N, tk.S, tk.W, tk.E), padx=(0, 15) if set_index < 2 else (0, 0))
        
        # 初始化UI元件引用存儲
        if len(self.combo_ui_refs) <= set_index:
            self.combo_ui_refs.extend([{}] * (set_index + 1 - len(self.combo_ui_refs)))
        
        # 啟用勾選框
        enabled_var = tk.BooleanVar(value=self.combo_enabled[set_index])
        enabled_check = ttk.Checkbutton(set_frame, text="啟用此套組", 
                                      variable=enabled_var,
                                      command=functools.partial(self.toggle_combo_set, set_index, enabled_var))
        enabled_check.grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(0, 15))
        self.combo_ui_refs[set_index]['enabled_var'] = enabled_var        # 觸發技能設定
        trigger_frame = ttk.Frame(set_frame)
        trigger_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 15))

        ttk.Label(trigger_frame, text="觸發技能:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W)
        trigger_var = tk.StringVar(value=self.combo_sets[set_index]['trigger_key'])
        trigger_combo = ttk.Combobox(trigger_frame, textvariable=trigger_var,
                                   values=['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P',
                                          'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L',
                                          'Z', 'X', 'C', 'V', 'B', 'N', 'M',
                                          '1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
                                   state="readonly", width=10, font=('Arial', 10))
        trigger_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        trigger_combo.bind("<<ComboboxSelected>>",
                         functools.partial(self.update_trigger_key, set_index, trigger_var))
        self.combo_ui_refs[set_index]['trigger_var'] = trigger_var

        # 觸發延遲設定
        ttk.Label(trigger_frame, text="初始延遲(ms):", font=('Arial', 10, 'bold')).grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        trigger_delay_var = tk.StringVar(value=self.combo_sets[set_index]['trigger_delay'])
        trigger_delay_entry = ttk.Entry(trigger_frame, textvariable=trigger_delay_var, width=8, font=('Arial', 10))
        trigger_delay_entry.grid(row=0, column=3, sticky=tk.W, padx=(10, 0))
        trigger_delay_entry.bind("<KeyRelease>",
                               functools.partial(self.update_trigger_delay, set_index, trigger_delay_var))
        self.combo_ui_refs[set_index]['trigger_delay_var'] = trigger_delay_var

        # 連段技能設定區域
        skills_frame = ttk.LabelFrame(set_frame, text="連段技能設定", padding="10")
        skills_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 10))

        # 創建技能設定區域的網格佈局
        for i in range(5):
            # 行標籤
            row_label = f"技能{i+1}:"
            ttk.Label(skills_frame, text=row_label, font=('Arial', 9, 'bold')).grid(row=i, column=0, sticky=tk.W, pady=3)

            # 技能按鍵
            key_var = tk.StringVar(value=self.combo_sets[set_index]['combo_keys'][i] if self.combo_sets[set_index]['combo_keys'][i] else 'off')
            key_combo = ttk.Combobox(skills_frame, textvariable=key_var,
                                   values=['off', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P',
                                          'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L',
                                          'Z', 'X', 'C', 'V', 'B', 'N', 'M',
                                          '1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
                                   state="readonly", width=6, font=('Arial', 9))
            key_combo.grid(row=i, column=1, sticky=tk.W, padx=(5, 0), pady=3)
            key_combo.bind("<<ComboboxSelected>>",
                         functools.partial(self.update_combo_key, set_index, i, key_var))
            
            # 延遲時間標籤
            ttk.Label(skills_frame, text="延遲(ms):", font=('Arial', 9)).grid(row=i, column=2, sticky=tk.W, padx=(15, 0), pady=3)

            # 延遲時間輸入框
            delay_var = tk.StringVar(value=self.combo_sets[set_index]['delays'][i] if self.combo_sets[set_index]['delays'][i] else '')
            delay_entry = ttk.Entry(skills_frame, textvariable=delay_var, width=8, font=('Arial', 9))
            delay_entry.grid(row=i, column=3, sticky=tk.W, padx=(5, 0), pady=3)
            delay_entry.bind("<KeyRelease>",
                           functools.partial(self.update_combo_delay, set_index, i, delay_var))
            
            # 原地攻擊checkbox
            stationary_var = tk.BooleanVar(value=self.combo_sets[set_index]['stationary_attacks'][i])
            stationary_check = ttk.Checkbutton(skills_frame, text="原地攻擊", variable=stationary_var,
                                             command=functools.partial(self.update_stationary_attack, set_index, i, stationary_var))
            stationary_check.grid(row=i, column=4, sticky=tk.W, padx=(15, 0), pady=3)
            
            # 原地攻擊說明標籤
            ttk.Label(skills_frame, text="(Shift+技能)", font=('Arial', 8), foreground="gray").grid(
                row=i, column=5, sticky=tk.W, padx=(5, 0), pady=3)
            
            # 存儲UI元件引用
            if 'key_vars' not in self.combo_ui_refs[set_index]:
                self.combo_ui_refs[set_index]['key_vars'] = []
                self.combo_ui_refs[set_index]['delay_vars'] = []
                self.combo_ui_refs[set_index]['stationary_vars'] = []
            
            if len(self.combo_ui_refs[set_index]['key_vars']) <= i:
                self.combo_ui_refs[set_index]['key_vars'].extend([''] * (i + 1 - len(self.combo_ui_refs[set_index]['key_vars'])))
                self.combo_ui_refs[set_index]['delay_vars'].extend([''] * (i + 1 - len(self.combo_ui_refs[set_index]['delay_vars'])))
                self.combo_ui_refs[set_index]['stationary_vars'].extend([None] * (i + 1 - len(self.combo_ui_refs[set_index]['stationary_vars'])))
            
            self.combo_ui_refs[set_index]['key_vars'][i] = key_var
            self.combo_ui_refs[set_index]['delay_vars'][i] = delay_var
            self.combo_ui_refs[set_index]['stationary_vars'][i] = stationary_var        # 設定框架寬度
        set_frame.columnconfigure(0, weight=1)
        set_frame.columnconfigure(1, weight=1)
        set_frame.columnconfigure(2, weight=1)
        set_frame.columnconfigure(3, weight=1)
        set_frame.columnconfigure(4, weight=1)
        set_frame.columnconfigure(5, weight=1)

        # 設定skills_frame的網格佈局
        skills_frame.columnconfigure(0, weight=0)
        skills_frame.columnconfigure(1, weight=0)
        skills_frame.columnconfigure(2, weight=0)
        skills_frame.columnconfigure(3, weight=0)
        skills_frame.columnconfigure(4, weight=0)
        skills_frame.columnconfigure(5, weight=1)

    def toggle_combo_set(self, set_index, enabled_var, event=None):
        """切換連段套組的啟用狀態"""
        self.combo_enabled[set_index] = enabled_var.get()
        print(f"連段套組 {set_index + 1} {'啟用' if enabled_var.get() else '停用'}")

    def update_trigger_key(self, set_index, trigger_var, event=None):
        """更新觸發鍵"""
        self.combo_sets[set_index]['trigger_key'] = trigger_var.get()
        print(f"連段套組 {set_index + 1} 觸發鍵更新為: {trigger_var.get()}")

    def update_trigger_delay(self, set_index, trigger_delay_var, event=None):
        """更新觸發延遲時間"""
        delay_text = trigger_delay_var.get().strip()
        if delay_text == '':
            # 允許空值
            self.combo_sets[set_index]['trigger_delay'] = ''
            return

        try:
            delay = int(delay_text)
            if delay < 0:
                delay = 0
            elif delay > 5000:
                delay = 5000
            self.combo_sets[set_index]['trigger_delay'] = delay
            trigger_delay_var.set(str(delay))
        except ValueError:
            # 如果輸入無效，保持原值
            trigger_delay_var.set(str(self.combo_sets[set_index]['trigger_delay']) if self.combo_sets[set_index]['trigger_delay'] else '')

    def update_combo_key(self, set_index, key_index, key_var, event=None):
        """更新連段技能按鍵"""
        self.combo_sets[set_index]['combo_keys'][key_index] = key_var.get()
        print(f"連段套組 {set_index + 1} 技能{key_index + 1} 更新為: {key_var.get()}")

    def update_combo_delay(self, set_index, delay_index, delay_var, event=None):
        """更新連段延遲時間"""
        delay_text = delay_var.get().strip()
        if delay_text == '':
            # 允許空值
            self.combo_sets[set_index]['delays'][delay_index] = ''
            return

        try:
            delay = int(delay_text)
            if delay < 0:
                delay = 0
            elif delay > 5000:
                delay = 5000
            self.combo_sets[set_index]['delays'][delay_index] = delay
            delay_var.set(str(delay))
        except ValueError:
            # 如果輸入無效，保持原值
            delay_var.set(str(self.combo_sets[set_index]['delays'][delay_index]) if self.combo_sets[set_index]['delays'][delay_index] else '')

    def update_stationary_attack(self, set_index, skill_index, stationary_var):
        """更新原地攻擊設定"""
        self.combo_sets[set_index]['stationary_attacks'][skill_index] = stationary_var.get()
        status = "啟用" if stationary_var.get() else "停用"
        print(f"連段套組 {set_index + 1} 技能{skill_index + 1} 原地攻擊: {status}")

    def update_combo_ui_from_config(self):
        """從載入的設定更新組合UI元件"""
        try:
            # 確保combo_ui_refs長度正確
            while len(self.combo_ui_refs) < len(self.combo_sets):
                self.combo_ui_refs.append({})
            
            for set_index in range(len(self.combo_sets)):
                if set_index < len(self.combo_ui_refs):
                    ui_refs = self.combo_ui_refs[set_index]
                    
                    # 更新啟用狀態
                    if 'enabled_var' in ui_refs and set_index < len(self.combo_enabled):
                        ui_refs['enabled_var'].set(self.combo_enabled[set_index])
                    
                    # 更新觸發鍵
                    if 'trigger_var' in ui_refs:
                        ui_refs['trigger_var'].set(self.combo_sets[set_index]['trigger_key'])
                    
                    # 更新觸發延遲
                    if 'trigger_delay_var' in ui_refs:
                        ui_refs['trigger_delay_var'].set(str(self.combo_sets[set_index]['trigger_delay']) if self.combo_sets[set_index]['trigger_delay'] else '')
                    
                    # 更新技能按鍵、延遲和原地攻擊設定
                    if 'key_vars' in ui_refs and 'delay_vars' in ui_refs and 'stationary_vars' in ui_refs:
                        for i in range(len(self.combo_sets[set_index]['combo_keys'])):
                            if i < len(ui_refs['key_vars']):
                                ui_refs['key_vars'][i].set(self.combo_sets[set_index]['combo_keys'][i] if self.combo_sets[set_index]['combo_keys'][i] else 'off')
                            if i < len(ui_refs['delay_vars']):
                                ui_refs['delay_vars'][i].set(str(self.combo_sets[set_index]['delays'][i]) if self.combo_sets[set_index]['delays'][i] else '')
                            if i < len(ui_refs['stationary_vars']) and i < len(self.combo_sets[set_index]['stationary_attacks']):
                                ui_refs['stationary_vars'][i].set(self.combo_sets[set_index]['stationary_attacks'][i])
            
            print("組合UI元件已從設定更新")
        except Exception as e:
            print(f"更新組合UI元件時發生錯誤: {e}")

    def start_combo_system(self):
        """啟動連段系統"""
        if self.combo_running:
            messagebox.showwarning("警告", "連段系統已經在運行中")
            return
        
        # 檢查是否有啟用的套組
        enabled_sets = [i for i, enabled in enumerate(self.combo_enabled) if enabled]
        if not enabled_sets:
            messagebox.showwarning("警告", "請至少啟用一個連段套組")
            return
        
        # 檢查設定是否完整
        for i in enabled_sets:
            combo_set = self.combo_sets[i]
            if not combo_set['trigger_key']:
                messagebox.showerror("錯誤", f"連段套組 {i+1} 的觸發技能未設定")
                return
            # 檢查是否有至少一個連段技能
            has_combo = any(key for key in combo_set['combo_keys'] if key and key != 'off' and key != '')
            if not has_combo:
                messagebox.showerror("錯誤", f"連段套組 {i+1} 沒有設定任何連段技能")
                return
        
        # 啟動連段系統
        self.combo_running = True
        self.combo_thread = threading.Thread(target=self.run_combo_system, daemon=True)
        self.combo_thread.start()
        
        # 更新UI
        self.combo_start_btn.config(state=tk.DISABLED)
        self.combo_stop_btn.config(state=tk.NORMAL)
        self.combo_status_label.config(text="運行中", foreground="green")
        
        enabled_count = len(enabled_sets)
        self.add_status_message(f"技能連擊系統已啟動 - {enabled_count} 個套組運行中", "success")
        print("技能連段系統已啟動")

    def stop_combo_system(self):
        """停止連段系統"""
        if not self.combo_running:
            return
        
        self.combo_running = False
        if self.combo_thread and self.combo_thread.is_alive():
            self.combo_thread.join(timeout=1.0)
        
        # 取消所有快捷鍵綁定
        for hotkey in self.combo_hotkeys.values():
            try:
                keyboard.remove_hotkey(hotkey)
            except:
                pass
        self.combo_hotkeys.clear()
        
        # 更新UI
        self.combo_start_btn.config(state=tk.NORMAL)
        self.combo_stop_btn.config(state=tk.DISABLED)
        self.combo_status_label.config(text="已停止", foreground="red")
        
        self.add_status_message("技能連擊系統已停止", "info")
        print("技能連段系統已停止")

    def restart_combo_system_silently(self):
        """靜默重新啟動連段系統（用於全域暫停恢復）"""
        if self.combo_running:
            return  # 已經在運行中
        
        # 檢查是否有啟用的套組
        enabled_sets = [i for i, enabled in enumerate(self.combo_enabled) if enabled]
        if not enabled_sets:
            raise Exception("沒有啟用的連段套組")
        
        # 檢查設定是否完整（靜默檢查）
        for i in enabled_sets:
            combo_set = self.combo_sets[i]
            if not combo_set['trigger_key']:
                raise Exception(f"連段套組 {i+1} 的觸發技能未設定")
            # 檢查是否有至少一個連段技能
            has_combo = any(key for key in combo_set['combo_keys'] if key and key != 'off' and key != '')
            if not has_combo:
                raise Exception(f"連段套組 {i+1} 沒有設定任何連段技能")
        
        # 啟動連段系統
        self.combo_running = True
        self.combo_thread = threading.Thread(target=self.run_combo_system, daemon=True)
        self.combo_thread.start()
        
        # 更新UI（如果元件存在）
        try:
            if hasattr(self, 'combo_start_btn') and self.combo_start_btn:
                self.combo_start_btn.config(state=tk.DISABLED)
            if hasattr(self, 'combo_stop_btn') and self.combo_stop_btn:
                self.combo_stop_btn.config(state=tk.NORMAL)
            if hasattr(self, 'combo_status_label') and self.combo_status_label:
                self.combo_status_label.config(text="運行中", foreground="green")
        except:
            pass  # UI 更新失敗不影響功能

    def run_combo_system(self):
        """運行連段系統的主循環"""
        print("連段系統線程已啟動")
        
        # 註冊快捷鍵
        for i, enabled in enumerate(self.combo_enabled):
            if enabled:
                trigger_key = self.combo_sets[i]['trigger_key'].lower()
                try:
                    # 使用partial來避免閉包問題
                    from functools import partial
                    hotkey_id = keyboard.add_hotkey(trigger_key,
                                                  partial(self.execute_combo, i),
                                                  suppress=False)  # 不阻止按鍵傳遞到遊戲
                    self.combo_hotkeys[f"combo_{i}"] = hotkey_id
                    print(f"註冊快捷鍵: {trigger_key} -> 連段套組 {i+1}")
                except Exception as e:
                    print(f"註冊快捷鍵失敗 {trigger_key}: {e}")
        
        # 保持線程運行
        while self.combo_running:
            time.sleep(0.1)
        
        print("連段系統線程已結束")

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

        # 計算有效技能數量
        valid_keys = [key for key in combo_keys if key and key != 'off' and key != '']
        
        # 詳細的連段資訊
        combo_info = f"🎯 觸發連擊套組 {set_index + 1}"
        if trigger_key:
            combo_info += f" (觸發鍵: {trigger_key})"
        combo_info += f" - {len(valid_keys)} 個有效技能"
        
        # 添加技能序列資訊
        if valid_keys:
            skills_text = " | ".join([f"{i+1}:{key}" for i, key in enumerate(valid_keys)])
            combo_info += f"\n📋 技能序列: {skills_text}"
        
        self.add_status_message(combo_info, "monitor")
        print(f"執行連段套組 {set_index + 1}: {valid_keys}")
        
        # 處理觸發延遲（如果有設定）
        if trigger_delay and trigger_delay != 'off' and trigger_delay != '':
            try:
                delay_ms = int(trigger_delay)
                if delay_ms > 0:
                    delay = delay_ms / 1000.0  # 轉換為秒
                    self.add_status_message(f"⏱️ 觸發延遲: {delay_ms}ms", "info")
                    print(f"  觸發延遲: {delay_ms}ms")
                    time.sleep(delay)
            except (ValueError, TypeError):
                # 如果延遲時間無效，跳過延遲
                pass
        
        # 執行連段
        for i, key in enumerate(combo_keys):
            # 跳過off或空值的技能
            if not key or key == 'off' or key == '' or not self.combo_running:
                if not self.combo_running:
                    self.add_status_message(f"⏹️ 連擊套組 {set_index + 1} 被中斷", "warning")
                    print(f"連段套組 {set_index + 1} 被中斷")
                    return
                continue

            # 模擬按鍵 - 使用選擇性按鍵發送，避免影響其他應用程序
            try:
                # 檢查是否啟用原地攻擊
                is_stationary = combo_set.get('stationary_attacks', [False] * 5)[i]
                
                # 嘗試獲取遊戲窗口句柄進行選擇性按鍵發送
                game_hwnd = self.get_game_window_handle()
                if game_hwnd:
                    if is_stationary:
                        # 原地攻擊：先按下Shift，然後按技能鍵，最後釋放Shift
                        shift_vk = self.map_key_to_vk_code('shift')
                        skill_vk = self.map_key_to_vk_code(key.lower())
                        
                        if shift_vk and skill_vk:
                            # 按下Shift
                            SendMessageW(game_hwnd, WM_KEYDOWN, shift_vk, 0)
                            time.sleep(0.01)
                            
                            # 按下技能鍵
                            SendMessageW(game_hwnd, WM_KEYDOWN, skill_vk, 0)
                            time.sleep(0.01)
                            
                            # 釋放技能鍵
                            SendMessageW(game_hwnd, WM_KEYUP, skill_vk, 0)
                            time.sleep(0.01)
                            
                            # 釋放Shift
                            SendMessageW(game_hwnd, WM_KEYUP, shift_vk, 0)
                            
                            self.add_status_message(f"⚔️ 技能 {i+1}: Shift+{key} (原地攻擊 - 選擇性發送)", "success")
                            print(f"  原地攻擊模式: Shift+{key} (發送到遊戲窗口)")
                        else:
                            # 如果無法映射鍵碼，回退到全局按鍵
                            pyautogui.keyDown('shift')
                            pyautogui.press(key.lower())
                            pyautogui.keyUp('shift')
                            self.add_status_message(f"⚔️ 技能 {i+1}: Shift+{key} (原地攻擊 - 全局發送)", "warning")
                            print(f"  原地攻擊模式: Shift+{key} (全局按鍵)")
                    else:
                        # 普通攻擊：直接按技能鍵
                        vk_code = self.map_key_to_vk_code(key.lower())
                        if vk_code:
                            self.send_key_to_window_combo(game_hwnd, vk_code)  # 使用技能連段專用方法
                            self.add_status_message(f"⚔️ 技能 {i+1}: {key} (普通攻擊 - 選擇性發送)", "success")
                            print(f"  ⚔️ 技能連段選擇性按下技能鍵: {key} (發送到遊戲窗口)")
                        else:
                            # 如果無法映射鍵碼，回退到全局按鍵
                            pyautogui.press(key.lower())
                            self.add_status_message(f"⚔️ 技能 {i+1}: {key} (普通攻擊 - 全局發送)", "warning")
                            print(f"  ⚔️ 技能連段全局按下技能鍵: {key} (鍵碼映射失敗)")
                else:
                    # 如果無法獲取窗口句柄，回退到全局按鍵
                    if is_stationary:
                        pyautogui.keyDown('shift')
                        pyautogui.press(key.lower())
                        pyautogui.keyUp('shift')
                        self.add_status_message(f"⚔️ 技能 {i+1}: Shift+{key} (原地攻擊 - 全局發送)", "warning")
                        print(f"  原地攻擊模式: Shift+{key} (全局按鍵)")
                    else:
                        pyautogui.press(key.lower())
                        self.add_status_message(f"⚔️ 技能 {i+1}: {key} (普通攻擊 - 全局發送)", "warning")
                        print(f"  全局按下技能鍵: {key} (無法獲取窗口句柄)")
            except Exception as e:
                self.add_status_message(f"❌ 技能 {i+1}: {key} 執行失敗 - {str(e)}", "error")
                print(f"  按鍵模擬失敗 {key}: {e}")
                continue

            # 延遲（如果有設定且大於0）
            if i < len(combo_keys) - 1 and delays[i] and delays[i] != 'off':
                try:
                    delay_ms = int(delays[i])
                    if delay_ms > 0:
                        delay = delay_ms / 1000.0  # 轉換為秒
                        self.add_status_message(f"⏱️ 技能間延遲: {delay_ms}ms", "info")
                        time.sleep(delay)
                        print(f"  延遲: {delay_ms}ms")
                except (ValueError, TypeError):
                    # 如果延遲時間無效，跳過延遲
                    pass

        print(f"連段套組 {set_index + 1} 執行完成")
        
        # 詳細的完成訊息
        completion_info = f"✅ 連擊套組 {set_index + 1} 執行完成"
        if trigger_key:
            completion_info += f" (觸發鍵: {trigger_key})"
        completion_info += f" - 成功執行 {len(valid_keys)} 個技能"
        
        self.add_status_message(completion_info, "success")

    def save_combo_config(self):
        """儲存連段設定"""
        try:
            config = {
                'combo_sets': self.combo_sets,
                'combo_enabled': self.combo_enabled
            }
            
            # 載入現有設定
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    existing_config = json.load(f)
            else:
                existing_config = {}
            
            # 更新連段設定
            existing_config.update(config)
            
            # 儲存設定
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(existing_config, f, indent=4, ensure_ascii=False)
            
            messagebox.showinfo("成功", "連段設定已儲存")
            print("連段設定已儲存")
            
        except Exception as e:
            messagebox.showerror("錯誤", f"儲存連段設定失敗: {str(e)}")
            print(f"儲存連段設定失敗: {e}")

    def load_combo_config(self):
        """載入連段設定"""
        try:
            if not os.path.exists(self.config_file):
                messagebox.showinfo("提示", "沒有找到設定檔案，使用預設設定")
                return
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 載入連段設定
            if 'combo_sets' in config:
                self.combo_sets = config['combo_sets']
                # 確保向後相容性，為舊配置添加缺失的字段
                for combo_set in self.combo_sets:
                    if 'trigger_delay' not in combo_set:
                        combo_set['trigger_delay'] = ''
                    if 'stationary_attacks' not in combo_set:
                        combo_set['stationary_attacks'] = [False, False, False, False, False]
                
                # 確保combo_sets長度正確
                while len(self.combo_sets) < 3:
                    self.combo_sets.append({
                        'trigger_key': 'Q' if len(self.combo_sets) == 0 else 'W' if len(self.combo_sets) == 1 else 'E',
                        'trigger_delay': '',
                        'combo_keys': ['', '', '', '', ''],
                        'delays': ['', '', '', '', ''],
                        'stationary_attacks': [False, False, False, False, False]
                    })
                self.combo_sets = self.combo_sets[:3]  # 確保不超過3個
            if 'combo_enabled' in config:
                self.combo_enabled = config['combo_enabled']
                # 確保combo_enabled長度正確
                while len(self.combo_enabled) < 3:
                    self.combo_enabled.append(False)
                self.combo_enabled = self.combo_enabled[:3]  # 確保不超過3個
            else:
                # 如果配置文件中沒有combo_enabled，重置為預設值
                self.combo_enabled = [False, False, False]
            
            # 更新UI以反映載入的設定
            self.update_combo_ui_from_config()
            
            messagebox.showinfo("成功", "連段設定已載入")
            print("連段設定已載入")
            
        except Exception as e:
            messagebox.showerror("錯誤", f"載入連段設定失敗: {str(e)}")
            print(f"載入連段設定失敗: {e}")

    def check_for_updates(self):
        """檢查GitHub上的最新版本"""
        def _check():
            try:
                self.latest_version_var.set("檢查中...")
                self.version_status_var.set("正在連接GitHub...")
                self.release_notes_var.set("")
                
                # 發送請求到GitHub API
                response = requests.get(GITHUB_API_URL, timeout=10)
                
                if response.status_code == 200:
                    release_data = response.json()
                    latest_version = release_data.get('tag_name', 'unknown')
                    release_body = release_data.get('body', '無更新說明')
                    download_url = release_data.get('html_url', '')
                    
                    # 更新UI顯示
                    self.latest_version_var.set(latest_version)
                    self.download_url = download_url
                    
                    # 版本比較
                    if self.compare_versions(CURRENT_VERSION, latest_version):
                        self.version_status_var.set("🆕 發現新版本！建議更新")
                        self.latest_version_label.config(foreground='red')
                        self.download_btn.config(state='normal')
                    else:
                        self.version_status_var.set("✅ 您使用的是最新版本")
                        self.latest_version_label.config(foreground='green')
                        self.download_btn.config(state='disabled')
                    
                    # 顯示更新說明（截取前200字符）
                    if release_body and release_body != '無更新說明':
                        notes = release_body[:200] + "..." if len(release_body) > 200 else release_body
                        self.release_notes_var.set(f"更新說明: {notes}")
                    
                else:
                    self.latest_version_var.set("檢查失敗")
                    self.version_status_var.set(f"❌ 檢查失敗 (HTTP {response.status_code})")
                    self.latest_version_label.config(foreground='red')
                    
            except requests.exceptions.Timeout:
                self.latest_version_var.set("連接超時")
                self.version_status_var.set("❌ 連接GitHub超時，請檢查網路連接")
                self.latest_version_label.config(foreground='red')
            except requests.exceptions.ConnectionError:
                self.latest_version_var.set("連接失敗")
                self.version_status_var.set("❌ 無法連接到GitHub，請檢查網路連接")
                self.latest_version_label.config(foreground='red')
            except Exception as e:
                self.latest_version_var.set("檢查錯誤")
                self.version_status_var.set(f"❌ 檢查時發生錯誤: {str(e)}")
                self.latest_version_label.config(foreground='red')
        
        # 在後台線程中執行檢查
        threading.Thread(target=_check, daemon=True).start()

    def compare_versions(self, current, latest):
        """比較版本號，返回True如果latest > current"""
        try:
            # 移除 'v' 前綴並分割版本號
            current_clean = current.lstrip('v').split('.')
            latest_clean = latest.lstrip('v').split('.')
            
            # 確保版本號有3個部分
            while len(current_clean) < 3:
                current_clean.append('0')
            while len(latest_clean) < 3:
                latest_clean.append('0')
            
            # 逐一比較主版本、次版本、修訂版本
            for i in range(3):
                current_part = int(current_clean[i])
                latest_part = int(latest_clean[i])
                
                if latest_part > current_part:
                    return True
                elif latest_part < current_part:
                    return False
            
            return False  # 版本相同
        except Exception as e:
            print(f"版本比較錯誤: {e}")
            return False

    def open_download_page(self):
        """打開下載頁面"""
        try:
            if hasattr(self, 'download_url') and self.download_url:
                import webbrowser
                webbrowser.open(self.download_url)
            else:
                # 備用URL
                import webbrowser
                webbrowser.open(f"https://github.com/{GITHUB_REPO}/releases")
        except Exception as e:
            messagebox.showerror("錯誤", f"無法打開下載頁面: {e}")

    def test_github_connection(self):
        """測試GitHub連接"""
        def _test():
            try:
                self.version_status_var.set("正在測試連接...")
                response = requests.get("https://api.github.com", timeout=5)
                if response.status_code == 200:
                    self.version_status_var.set("✅ GitHub連接正常")
                else:
                    self.version_status_var.set(f"⚠️ GitHub連接異常 (HTTP {response.status_code})")
            except Exception as e:
                self.version_status_var.set(f"❌ 連接測試失敗: {str(e)}")
        
        threading.Thread(target=_test, daemon=True).start()

    def silent_version_check(self):
        """靜默檢查版本，只在有新版本時彈出提醒"""
        def _silent_check():
            try:
                # 發送請求到GitHub API
                response = requests.get(GITHUB_API_URL, timeout=10)
                
                if response.status_code == 200:
                    release_data = response.json()
                    latest_version = release_data.get('tag_name', 'unknown')
                    release_body = release_data.get('body', '無更新說明')
                    download_url = release_data.get('html_url', '')
                    
                    # 只在有新版本時彈出提醒
                    if self.compare_versions(CURRENT_VERSION, latest_version):
                        # 在主線程中顯示更新提醒
                        self.root.after(0, lambda: self.show_update_notification(latest_version, release_body, download_url))
                    
            except Exception as e:
                # 靜默處理錯誤，不影響用戶體驗
                print(f"靜默版本檢查失敗: {e}")
        
        # 在後台線程中執行檢查
        threading.Thread(target=_silent_check, daemon=True).start()

    def show_update_notification(self, latest_version, release_body, download_url):
        """顯示更新通知視窗"""
        # 創建更新通知視窗
        update_window = tk.Toplevel(self.root)
        update_window.title("🆕 發現新版本")
        update_window.geometry("500x350")
        update_window.resizable(False, False)
        update_window.transient(self.root)
        update_window.grab_set()
        
        # 讓視窗居中
        update_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 50,
            self.root.winfo_rooty() + 50
        ))
        
        # 標題
        title_frame = ttk.Frame(update_window)
        title_frame.pack(fill=tk.X, padx=20, pady=20)
        
        ttk.Label(title_frame, text="🎉 發現新版本！", 
                 font=('Arial', 16, 'bold'), foreground='green').pack()
        
        # 版本資訊
        info_frame = ttk.LabelFrame(update_window, text="版本資訊", padding="15")
        info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        ttk.Label(info_frame, text=f"目前版本: {CURRENT_VERSION}", 
                 font=('Arial', 10)).pack(anchor=tk.W, pady=(0, 5))
        ttk.Label(info_frame, text=f"最新版本: {latest_version}", 
                 font=('Arial', 10, 'bold'), foreground='red').pack(anchor=tk.W, pady=(0, 10))
        
        # 更新說明
        if release_body and release_body != '無更新說明':
            ttk.Label(info_frame, text="更新說明:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
            notes = release_body[:300] + "..." if len(release_body) > 300 else release_body
            notes_label = ttk.Label(info_frame, text=notes, wraplength=400, 
                                   font=('Arial', 9), justify=tk.LEFT)
            notes_label.pack(anchor=tk.W, pady=(5, 0))
        
        # 按鈕框架
        button_frame = ttk.Frame(update_window)
        button_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        def open_download():
            try:
                import webbrowser
                webbrowser.open(download_url)
                update_window.destroy()
            except Exception as e:
                messagebox.showerror("錯誤", f"無法打開下載頁面: {e}")
        
        def switch_to_version_tab():
            # 切換到版本檢查分頁並更新資訊
            self.notebook.select(self.version_frame)
            self.latest_version_var.set(latest_version)
            self.version_status_var.set("🆕 發現新版本！建議更新")
            self.release_notes_var.set(f"更新說明: {release_body[:200]}...")
            self.latest_version_label.config(foreground='red')
            self.download_btn.config(state='normal')
            self.download_url = download_url
            update_window.destroy()
        
        # 按鈕
        ttk.Button(button_frame, text="⬇️ 立即下載", 
                  command=open_download).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="📋 查看詳情", 
                  command=switch_to_version_tab).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="❌ 稍後提醒", 
                  command=update_window.destroy).pack(side=tk.RIGHT)

    def create_about_tab(self):
        """創建關於分頁"""
        main_frame = self.about_frame
        
        # 標題
        title_label = ttk.Label(main_frame, text="ℹ️ 關於 Path of Exile 遊戲輔助工具", 
                               font=('Microsoft YaHei', 22, 'bold'))
        title_label.pack(pady=(20, 40))
        
        # 版本和狀態資訊
        info_frame = ttk.LabelFrame(main_frame, text="軟體資訊", padding="25")
        info_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(info_frame, text=f"版本: {CURRENT_VERSION}", 
                 font=('Microsoft YaHei', 16, 'bold')).pack(anchor=tk.W, pady=(0, 10))
        ttk.Label(info_frame, text="狀態: 完全免費開源", 
                 font=('Microsoft YaHei', 14), foreground='green').pack(anchor=tk.W, pady=(0, 10))
        ttk.Label(info_frame, text="授權: MIT License", 
                 font=('Microsoft YaHei', 14)).pack(anchor=tk.W)
        
        # 連結按鈕框架
        links_frame = ttk.LabelFrame(main_frame, text="官方連結", padding="25")
        links_frame.pack(fill=tk.X, pady=(0, 20))
        
        # GitHub 按鈕
        def open_github():
            try:
                import webbrowser
                webbrowser.open("https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor")
            except Exception as e:
                messagebox.showerror("錯誤", f"無法打開 GitHub 頁面: {e}")
        
        github_btn = ttk.Button(links_frame, text="🌐 GitHub 官方倉庫", command=open_github)
        github_btn.configure(width=25)
        github_btn.pack(fill=tk.X, pady=(0, 8))
        
        # Discord 按鈕（暫無連結）
        def discord_placeholder():
            messagebox.showinfo("提示", "Discord 社群功能即將推出，敬請期待！\n您可以暫時通過 GitHub Issues 與我們聯繫。")
        
        discord_btn = ttk.Button(links_frame, text="💬 Discord 社群 (即將推出)", 
                                command=discord_placeholder, state='disabled')
        discord_btn.configure(width=25)
        discord_btn.pack(fill=tk.X)
        
        # 贊助支持框架
        sponsor_frame = ttk.LabelFrame(main_frame, text="💝 支持開發者", padding="25")
        sponsor_frame.pack(fill=tk.X, pady=(0, 20))
        
        sponsor_intro = ttk.Label(sponsor_frame, 
                                 text="如果這個工具對您有幫助，歡迎支持開發者繼續維護和改進 ❤️", 
                                 font=('Microsoft YaHei', 13), foreground='#2E7D32',
                                 wraplength=450)
        sponsor_intro.pack(anchor=tk.W, pady=(0, 20))
        
        # 創建按鈕網格
        button_frame = ttk.Frame(sponsor_frame)
        button_frame.pack(fill=tk.X)
        
        # 贊助按鈕行
        sponsor_buttons_frame = ttk.Frame(button_frame)
        sponsor_buttons_frame.pack(fill=tk.X)
        
        # ECPay 按鈕
        def open_ecpay():
            try:
                import webbrowser
                webbrowser.open("https://p.ecpay.com.tw/E0E3A")
            except Exception as e:
                messagebox.showerror("錯誤", f"無法打開ECPay頁面: {e}")
        
        ecpay_btn = ttk.Button(sponsor_buttons_frame, text="💳 ECPay", command=open_ecpay)
        ecpay_btn.pack(side=tk.LEFT, padx=(0, 8), expand=True, fill=tk.X)
        
        # PayPal 按鈕
        def open_paypal():
            try:
                import webbrowser
                webbrowser.open("https://www.paypal.com/ncp/payment/GJS4D5VTSVWG4")
            except Exception as e:
                messagebox.showerror("錯誤", f"無法打開PayPal頁面: {e}")
        
        paypal_btn = ttk.Button(sponsor_buttons_frame, text="🌍 PayPal", command=open_paypal)
        paypal_btn.pack(side=tk.LEFT, padx=(4, 0), expand=True, fill=tk.X)
        
        # 免責聲明
        disclaimer_frame = ttk.LabelFrame(main_frame, text="⚠️ 重要聲明", padding="20")
        disclaimer_frame.pack(fill=tk.BOTH, expand=True)
        
        disclaimer_text = """本軟體是免費開源的。如果你被收費，請立即退款。請造訪 GitHub 下載最新的官方版本。

本軟體僅供個人使用，用於學習 Python 程式設計、電腦視覺、UI 自動化等技術。請勿將其用於任何營利性或商業用途。

使用本軟體可能會導致帳號被封。請在了解風險後再使用。"""
        
        disclaimer_label = ttk.Label(disclaimer_frame, text=disclaimer_text, 
                                   wraplength=480, font=('Microsoft YaHei', 12), 
                                   justify=tk.LEFT, foreground='#D32F2F')
        disclaimer_label.pack(anchor=tk.W)

if __name__ == "__main__":
    root = tk.Tk()
    app = HealthMonitor(root)
    root.mainloop()

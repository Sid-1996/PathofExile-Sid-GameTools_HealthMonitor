import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font as tkfont
import json
import os
import threading
import time


try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError as e:
    print(f"警告: OpenCV不可用 - {e}")
    print("某些圖像處理功能可能無法正常工作")
    cv2 = None
    np = None
    OPENCV_AVAILABLE = False
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
# Import new modularized components
from skill_timer import SkillTimerModule
from language_system import get_language_manager, get_text as get_localized_text
from utils import set_app_instance, setup_signal_handlers, setup_exception_handler, format_usage_time, get_app_dir, global_f12_handler, Tooltip
from custom_dialogs import CustomMessageBox, setup_custom_messagebox
from config_manager import get_config_manager
from _version import __version__
from app_state import AppState
from auto_click_manager import AutoClickManager
from usage_tracker import UsageTracker
from window_key_sender import WindowKeySender
from tab_help import HelpTab
from tab_about import AboutTab
from tab_status import StatusTab
from tab_version import VersionTab
from tab_combo import ComboTab
from tab_inventory import InventoryTab
from tab_monitor import MonitorTab
from image_utils import draw_scale_lines, resize_and_center_image, draw_health_indicator, draw_mana_indicator, get_region_text, get_mana_region_text, get_interface_ui_region_text
from monitor_analyzer import (
    analyze_health,
    is_health_color,
    get_health_color_ratio,
    analyze_mana,
    is_mana_color,
    get_mana_color_ratio,
    get_main_color,
    check_triggers,
    trigger_actions,
    interruptible_sleep,
)
from capture_utils import _mss_singleton, capture_region_to_pil, capture_region_to_cv2
from capture_utils import build_game_window_monitor, save_screenshot, load_screenshot_from_file
from inventory_utils import should_clear_inventory, find_inventory_items, calculate_inventory_grid_positions

# 版本資訊
CURRENT_VERSION = f"v{__version__}"

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



class HealthMonitor:
    def get_text(self, key):
        """獲取本地化文字"""
        try:
            # 直接使用語言管理器，避免導入函數的問題
            result = self.language_manager.get_text(key)
            return result
        except Exception:
            # print(f"[DEBUG] 主程序 get_text('{key}') 異常: {e}")
            return f"[{key}]"

    def change_language_display(self, display_name):
        """處理顯示名稱的語言切換"""
        language_code = self.language_display_map.get(display_name, "zh-tw")
        self.change_language(language_code)

    def change_language(self, new_language):
        """切換語言"""
        if new_language == self.current_language:
            return  # 如果選擇的語言和當前語言相同，不做任何動作

        # 創建雙語確認訊息（已經包含重啟說明）
        bilingual_title = self.get_text("language_change_title")
        bilingual_message = self.get_text("language_change_message")

        # 顯示雙語確認視窗（訊息已包含重啟說明）
        result = CustomMessageBox.ask_yes_no(bilingual_title, bilingual_message, self.root)

        if result:
            # 保存語言設定並重新啟動應用程式
            self.language_manager.change_language(new_language)
            self.current_language = new_language  # 同步主程序的 current_language
            self.language_var.set(self.language_reverse_map.get(new_language, "繁體中文"))
            self.config['language'] = new_language

            # 立即更新UI語言（在重啟前）
            self.update_ui_language()

            # 保存設定，如果失敗則顯示錯誤訊息
            try:
                self.config_manager.save_config(self.config)
                print("語言設定已保存")
            except Exception as e:
                print(f"保存語言設定失敗: {e}")

            # 重新啟動應用程式
            try:
                import subprocess
                import sys
                script_path = os.path.abspath(__file__)
                current_dir = os.getcwd()

                print(f"重新啟動Python腳本: {sys.executable} {script_path}")

                # 啟動新實例
                subprocess.Popen([sys.executable, script_path], cwd=current_dir)

                # 關閉當前應用程式
                self.close_app()

            except Exception as e:
                print(f"Python腳本重新啟動失敗: {e}")
                CustomMessageBox.show_error("錯誤", f"無法重新啟動應用程式：{e}", self.root)
        else:
            # 使用者選擇取消，恢復語言選擇器到當前語言
            display_name = self.language_manager.get_current_display_name()
            self.language_var.set(display_name)
            print("使用者取消語言切換，保持原語言設定")

    def update_ui_text(self):
        """全面更新所有UI元件的文字"""
        try:
            # print(f"[DEBUG] update_ui_text() 開始執行，語言: {self.language_manager.current_language}")

            # 更新視窗標題
            self.root.title(self.get_text("window_title"))

            # 更新分頁標題
            self.notebook.tab(0, text=self.get_text("tab_health_monitor"))
            self.notebook.tab(1, text=self.get_text("tab_inventory_clear"))
            self.notebook.tab(2, text=self.get_text("tab_skill_combo"))
            self.notebook.tab(3, text=self.get_text("tab_status"))
            self.notebook.tab(4, text=self.get_text("tab_help"))
            self.notebook.tab(5, text=self.get_text("tab_version"))
            self.notebook.tab(6, text=self.get_text("tab_about"))

            # 更新控制面板的UI元素
            if hasattr(self, 'control_frame'):
                self.control_frame.config(text=self.get_text("control_panel"))
                if hasattr(self, 'start_btn'):
                    self.monitor_tab.start_btn.config(text=self.get_text("start_monitoring"))
                if hasattr(self, 'stop_btn'):
                    self.monitor_tab.stop_btn.config(text=self.get_text("stop_monitoring"))
                if hasattr(self, 'save_btn'):
                    self.monitor_tab.save_btn.config(text=self.get_text("save_settings"))
                if hasattr(self, 'test_preview_btn'):
                    self.monitor_tab.test_preview_btn.config(text=self.get_text("test_preview"))
                if hasattr(self, 'check_freq_label'):
                    self.monitor_tab.check_freq_label.config(text=self.get_text("check_frequency"))
                if hasattr(self, 'ms_label'):
                    self.monitor_tab.ms_label.config(text=self.get_text("ms"))
                if hasattr(self, 'reminder_frame'):
                    self.monitor_tab.reminder_frame.config(text=self.get_text("important_reminder"))
                if hasattr(self, 'reminder_label'):
                    self.monitor_tab.reminder_label.config(text=self.get_text("reminder_text"))
                if hasattr(self, 'language_label'):
                    self.monitor_tab.language_label.config(text=self.get_text("language"))
                if hasattr(self, 'gui_settings_label'):
                    self.monitor_tab.gui_settings_label.config(text=self.get_text("gui_settings"))
                if hasattr(self, 'always_on_top_check'):
                    self.monitor_tab.always_on_top_check.config(text=self.get_text("always_on_top"))
                if hasattr(self, 'preview_settings_label'):
                    self.monitor_tab.preview_settings_label.config(text=self.get_text("preview_settings"))
                if hasattr(self, 'enable_preview_check'):
                    self.monitor_tab.enable_preview_check.config(text=self.get_text("enable_preview"))
                if hasattr(self, 'preview_interval_label'):
                    self.monitor_tab.preview_interval_label.config(text=self.get_text("preview_interval"))
                if hasattr(self, 'preview_ms_label'):
                    self.monitor_tab.preview_ms_label.config(text=self.get_text("ms"))

            # 更新遊戲視窗設定區域
            if hasattr(self, 'window_frame'):
                self.window_frame.config(text=self.get_text("game_window_settings"))
                if hasattr(self, 'region_label'):
                    self.monitor_tab.region_label.config(text=get_region_text(self.config))
                if hasattr(self, 'mana_region_label'):
                    self.monitor_tab.mana_region_label.config(text=get_mana_region_text(self.config))
                if hasattr(self.monitor_tab, 'interface_ui_label'):
                    self.monitor_tab.interface_ui_label.config(text=get_interface_ui_region_text(self.interface_ui_region))
                if hasattr(self, 'select_health_btn'):
                    self.select_health_btn.config(text=self.get_text("select_health_region"))
                if hasattr(self, 'select_mana_btn'):
                    self.select_mana_btn.config(text=self.get_text("select_mana_region"))
                if hasattr(self, 'select_interface_ui_btn'):
                    self.select_interface_ui_btn.config(text=self.get_text("select_interface_ui"))

            # 更新觸發設定區域
            if hasattr(self, 'settings_frame'):
                self.settings_frame.config(text=self.get_text("trigger_settings"))
                if hasattr(self, 'remove_selected_btn'):
                    self.remove_selected_btn.config(text=self.get_text("remove_selected"))
                if hasattr(self, 'adjust_colors_btn'):
                    self.adjust_colors_btn.config(text=self.get_text("adjust_colors"))
                if hasattr(self, 'adjust_interface_ui_btn'):
                    self.adjust_interface_ui_btn.config(text=self.get_text("adjust_interface_ui"))
                if hasattr(self, 'multi_trigger_check'):
                    self.multi_trigger_check.config(text=self.get_text("multiple_triggers"))

            # 更新即時狀態區域
            if hasattr(self, 'real_time_status_frame'):
                self.monitor_tab.real_time_status_frame.config(text=self.get_text("real_time_status"))
                if hasattr(self, 'current_health_label'):
                    self.monitor_tab.current_health_label.config(text=self.get_text("current_health"))
                if hasattr(self, 'current_mana_label'):
                    self.monitor_tab.current_mana_label.config(text=self.get_text("current_mana"))
                if hasattr(self, 'main_color_label'):
                    self.monitor_tab.main_color_label.config(text=self.get_text("main_color"))
                if hasattr(self, 'trigger_status_label'):
                    self.monitor_tab.trigger_status_label.config(text=self.get_text("trigger_status"))

            # 更新預覽區域
            if hasattr(self, 'preview_frame'):
                self.monitor_tab.preview_frame.config(text=self.get_text("region_preview"))
                if hasattr(self, 'health_preview_frame'):
                    self.monitor_tab.health_preview_frame.config(text=self.get_text("health_preview"))
                if hasattr(self, 'preview_label'):
                    self.monitor_tab.preview_label.config(text=self.get_text("select_health_region_first"))
                if hasattr(self, 'mana_preview_frame'):
                    self.monitor_tab.mana_preview_frame.config(text=self.get_text("mana_preview"))
                if hasattr(self, 'mana_preview_label'):
                    self.monitor_tab.mana_preview_label.config(text=self.get_text("select_mana_region_first"))

            # print(f"[DEBUG] update_ui_text() 完成")

        except Exception:
            pass

    def update_ui_language(self):
        """更新UI語言（保持向後相容）"""
        self.update_ui_text()
        if hasattr(self, 'monitor_tab'):
            self.monitor_tab.update_monitor_tab_language()

    def update_status_tab_language(self):
        try:
            if hasattr(self, 'status_tab'):
                self.status_tab.update_language()
        except Exception as e:
            print(f"更新狀態分頁語言時發生錯誤: {e}")

    def update_help_tab_language(self):
        if hasattr(self, 'help_tab'):
            self.help_tab.update_language()

    def update_version_tab_language(self):
        try:
            if hasattr(self, 'version_tab'):
                self.version_tab.update_language()
        except Exception as e:
            print(f"更新版本分頁語言時發生錯誤: {e}")

    def update_about_tab_language(self):
        try:
            if hasattr(self, 'about_tab'):
                self.about_tab.update_language()
        except Exception as e:
            print(f"更新關於分頁語言時發生錯誤: {e}")

    def update_combo_tab_language(self):
        try:
            if hasattr(self, 'combo_tab'):
                self.combo_tab.update_language()
        except Exception as e:
            print(f"更新技能連段分頁語言時發生錯誤: {e}")

    def __init__(self, root):
        global _app_instance
        _app_instance = self  # 保存全局引用

        self.root = root
        self._startup_phase = True
        self._startup_visual_refresh_pending = False

        # 【核心修正 1】優先初始化配置管理器，從源頭取得保存的語言設定
        self.config_manager = get_config_manager()
        self.config_file = self.config_manager.config_file

        # 【核心修正 2】從配置或註冊表取得 saved_language，並初始化語言管理器
        self.language_manager = get_language_manager()

        # 臨時載入設定以獲取語言偏好
        success, message = self.config_manager.load_config()
        temp_config = self.config_manager.config

        # 嘗試從 config 讀取語言，若無則預設為 'zh-tw'
        saved_language = temp_config.get("language", "zh-tw")
        self.language_manager.change_language(saved_language)
        self.current_language = saved_language

        # print(f"[DEBUG] 語系初始化成功！當前設定語系為: {self.current_language}")

        # 【核心修正 3】這時候語言已經準備好了，才可以開始設定視窗標題與執行 get_text
        self.root.title(self.get_text("window_title"))

        # 初始化自訂對話框（替換 tkinter.messagebox）
        setup_custom_messagebox()

        # 初始設定為中等大小的視窗
        self.root.geometry("800x600")
        self.root.minsize(650, 500)
        self.root.attributes("-alpha", 1.0)

        # 記錄應用程式啟動時間
        self.start_time = datetime.now()
        print(f"{self.get_text('app_start_time')} {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # 初始化使用時間追蹤
        self.usage_tracker = UsageTracker(self)

        # 存儲原始 exe 路徑（用於 exe 重啟）
        self.original_exe_path = None
        if getattr(sys, 'frozen', False):
            # 在 PyInstaller --onefile 模式下，找到原始 exe 路徑
            try:
                import psutil
                current_process = psutil.Process()
                # 獲取當前進程的可執行文件路徑
                self.original_exe_path = current_process.exe()
                print(f"檢測到原始 exe 路徑: {self.original_exe_path}")
            except Exception as e:
                print(f"使用 psutil 獲取 exe 路徑失敗: {e}")
                # 備用方法：檢查常見位置
                try:
                    # 從命令行參數或環境變量中獲取
                    if len(sys.argv) > 0:
                        # 檢查第一個參數是否是 exe 路徑
                        potential_path = sys.argv[0]
                        if potential_path.endswith('.exe') and os.path.exists(potential_path):
                            self.original_exe_path = potential_path
                        else:
                            # 嘗試從應用程式目錄查找
                            app_dir = get_app_dir()
                            possible_exe_names = ['GameTools_HealthMonitor.exe', 'health_monitor.exe']
                            for exe_name in possible_exe_names:
                                exe_path = os.path.join(app_dir, exe_name)
                                if os.path.exists(exe_path):
                                    self.original_exe_path = exe_path
                                    break
                except Exception as e2:
                    print(f"備用方法也失敗: {e2}")

        # 獲取語言映射
        self.config = {}
        self.state = AppState(self)
        self.language_display_map = self.language_manager.get_language_display_map()
        self.language_reverse_map = self.language_manager.get_language_reverse_map()

        # 設置語言變數為顯示名稱
        display_name = self.language_manager.get_current_display_name()
        self.language_var = tk.StringVar(value=display_name)

        # 創建載入提示視窗（在語言設定之後）
        self.show_loading_window()

        # GUI最上方設定變數
        self.always_on_top_var = tk.BooleanVar(value=False)  # 預設不在最上方，避免影響彈出視窗操作

        # 框選相關變數
        self.selection_active = False
        self.selection_start = None
        self.selection_end = None
        self.selected_region = None
        self.selected_mana_region = None

        # InventoryTab 相關變數（由 InventoryTab.__init__ 自行初始化）
        self.inventory_grid_positions = []  # 60個格子的位置
        self.inventory_selection_active = False
        self.inventory_selection_start = None
        self.inventory_selection_end = None
        self.inventory_ui_selection_active = False
        self.inventory_ui_selection_start = None
        self.inventory_ui_selection_end = None
        self.interface_ui_region = None  # 介面UI區域
        self.ui_preview_image = None  # 用於Canvas顯示的PhotoImage
        self.pickup_coordinates = []  # 儲存5個取物座標 [x, y]
        self.pause_status_label = None  # 暫停狀態顯示標籤

        # 線程鎖（定義在 AppState 中）

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


        # 滑鼠自動點擊管理器
        self.auto_click_manager = AutoClickManager(self)

        # 預覽控制變數
        self.preview_enabled = tk.BooleanVar(value=True)
        self.preview_interval_var = tk.StringVar(value="250")

        # GUI 元件
        self.update_loading_status("正在創建介面元件...")
        self.create_widgets()

        # 在UI元件創建後載入設定
        self.update_loading_status("正在載入設定...")
        success, message = self.config_manager.load_config()
        self.config = self.config_manager.config

        # 載入配置到各個變數
        self.load_config()

        # 將窗口置中於螢幕（如果沒有儲存的位置）
        self.update_loading_status("正在初始化視窗...")
        self.center_window()

        # 確保GUI最上方設定正確應用（無論設定載入是否成功）
        # 移除預設置頂，讓用戶手動控制
        # self.root.attributes("-topmost", self.always_on_top_var.get())

        # 設置全域滾輪支持
        self.update_loading_status("正在設置功能...")
        self.setup_global_scroll()

        # 配置pyautogui
        pyautogui.FAILSAFE = False  # 禁用failsafe，因為我們需要精確控制
        pyautogui.PAUSE = 0  # 移除按鍵間的預設延遲

        # 如果有已儲存的設定，自動載入預覽

        # GUI ??關閉協議
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # ????????
        self.close_loading_window()
        self._startup_phase = False
        self.root.after(10, self.finish_startup_tasks)

    def finish_startup_tasks(self):
        """Run non-critical startup tasks after the main window is already visible."""
        try:
            # print(f"[DEBUG] finish_startup_tasks 開始執行")
            # 確保UI語言正確更新 - 使用新的 update_ui_text() 方法
            # print(f"[DEBUG] 調用 update_ui_text()")
            self.update_ui_text()
            self.monitor_tab.update_monitor_tab_language()

            self.monitor_tab.auto_load_preview()
        except Exception as e:
            print(f": {e}")

        if self._startup_visual_refresh_pending:
            self._startup_visual_refresh_pending = False
            try:
                self.refresh_visual_previews_after_load()
            except Exception as e:
                print(f": {e}")

        try:
            self.setup_hotkeys()
        except Exception as e:
            print(f": {e}")

        try:
            self.setup_mouse_interrupt()
        except Exception as e:
            print(f": {e}")

        self.window_key_sender = WindowKeySender(self)
        self.root.after(500, self.window_key_sender._start_window_focus_watcher)

        self.status_tab.add_status_message(self.get_text("tool_started_successfully"), "success")
        self.status_tab.add_status_message(self.get_text("hotkey_info"), "info")
        self.usage_tracker.start_periodic_update()

    def refresh_visual_previews_after_load(self):
        """Refresh heavier previews after startup so the main window appears sooner."""
        if hasattr(self, 'ui_preview_canvas') and hasattr(self, 'inventory_tab') and self.inventory_tab.inventory_ui_region:
            self.inventory_tab.update_ui_preview()

        if hasattr(self.monitor_tab, 'interface_ui_preview_canvas') and self.interface_ui_region:
            self.inventory_tab.update_interface_ui_preview()

        if hasattr(self, 'inventory_tab') and self.inventory_tab.inventory_region:
            self.inventory_tab.update_inventory_preview_from_current()

    def setup_mouse_interrupt(self):
        """設置滑鼠右鍵中斷功能"""
        # 啟動背景線程監聽右鍵事件
        self.mouse_interrupt_thread = threading.Thread(target=self.monitor_mouse_interrupt, daemon=True)
        self.mouse_interrupt_thread.start()

    def monitor_mouse_interrupt(self):
        """監聽滑鼠右鍵事件用於中斷F3清包"""
        if self.state._is_closing:
            return
        self.status_tab.add_status_message(self.get_text("mouse_interrupt_started"), "info")
        print(self.get_text("mouse_interrupt_started"))

        right_click_start = None
        interrupt_threshold = 2.0  # 2秒閾值
        last_right_button_state = False  # 記錄上一次的右鍵狀態

        while not self.state._is_closing:
            try:
                # 使用GetKeyState檢查右鍵狀態，適用於持續按下檢測
                VK_RBUTTON = 0x02  # 右鍵虛擬鍵碼
                current_right_button_state = (ctypes.windll.user32.GetKeyState(VK_RBUTTON) & 0x8000) != 0

                if current_right_button_state and not last_right_button_state:
                    # 右鍵剛剛被按下
                    right_click_start = time.time()
                    print(self.get_text("right_click_detected"))
                elif not current_right_button_state and last_right_button_state:
                    # 右鍵剛剛被釋放
                    if right_click_start is not None:
                        duration = time.time() - right_click_start
                        if duration >= interrupt_threshold:
                            print(self.get_text("right_click_interrupt").format(duration=duration))
                            self.state.inventory_clear_interrupt = True
                        right_click_start = None

                last_right_button_state = current_right_button_state
                time.sleep(0.1)  # 每100ms檢查一次

            except Exception as e:
                if self.state._is_closing:
                    break
                print(f"{self.get_text('mouse_interrupt_error')} {e}")
                time.sleep(1)  # 錯誤時稍作延遲

    def center_window(self):
        """將窗口置中於螢幕，如果沒有儲存的位置"""
        try:
            # 檢查是否已經有儲存的窗口位置
            if hasattr(self, 'config') and 'window_geometry' in self.config:
                print(self.get_text("skip_center_window"))
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

            print(self.get_text("window_centered").format(screen_width=screen_width, screen_height=screen_height, window_width=window_width, window_height=window_height, x=x, y=y))

        except Exception as e:
            print(f"{self.get_text('center_window_error')} {e}")
            # 出錯時設置一個預設位置，使用較小的初始尺寸
            self.root.geometry("800x600+100+100")

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
        # print(f"[DEBUG] 準備調用 self.get_text('tab_health_monitor')")
        tab_health_text = self.get_text("tab_health_monitor")
        # print(f"[DEBUG] 創建分頁1標題: '{tab_health_text}' (語言: {self.language_manager.current_language})")
        self.notebook.add(self.monitor_frame, text=tab_health_text)

        # 第二個分頁：一鍵清包
        self.inventory_frame = ttk.Frame(self.notebook, padding="10")
        # print(f"[DEBUG] 準備調用 self.get_text('tab_inventory_clear')")
        tab_inventory_text = self.get_text("tab_inventory_clear")
        # print(f"[DEBUG] 創建分頁2標題: '{tab_inventory_text}'")
        self.notebook.add(self.inventory_frame, text=tab_inventory_text)

        # 第三個分頁：技能連段（插入到一鍵清包和使用說明之間）
        self.combo_frame = ttk.Frame(self.notebook, padding="10")
        # print(f"[DEBUG] 準備調用 self.get_text('tab_skill_combo')")
        tab_combo_text = self.get_text("tab_skill_combo")
        # print(f"[DEBUG] 創建分頁3標題: '{tab_combo_text}'")
        self.notebook.add(self.combo_frame, text=tab_combo_text)

        # 第四個分頁：執行狀態（新增）
        self.status_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.status_frame, text=self.get_text("tab_status"))

        # 第五個分頁：使用說明（系統資訊分頁 - 擺在最後）
        self.help_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.help_frame, text=self.get_text("tab_help"))

        # 第六個分頁：版本檢查（系統資訊分頁 - 擺在最後）
        self.version_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.version_frame, text=self.get_text("tab_version"))

        # 第七個分頁：關於（系統資訊分頁 - 擺在最後）
        self.about_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.about_frame, text=self.get_text("tab_about"))

        # 綁定分頁切換事件來實現智能自適應視窗大小
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        # 初始化分頁最小尺寸字典 - 根據實際內容需求優化
        self.tab_min_sizes = {
            "血魔監控": (1000, 700),  # 血魔監控：左右分欄+設定區域，需要適中空間
            "一鍵清包": (1200, 800),  # 一鍵清包：左側控制+右側預覽，需要較大空間
            "技能連段": (1100, 650),  # 技能連段：3個連段區域橫向排列，需要寬度
            "執行狀態": (800, 600),   # 執行狀態：主要是文字顯示區域，較緊湊
            "使用說明": (900, 650),   # 使用說明：卡片式佈局，中等空間
            "版本檢查": (750, 550),   # 版本檢查：簡單的版本資訊顯示，較小空間
            "🚀 關於作者": (650, 500)       # 關於：卡片式按鈕佈局，緊湊空間
        }

        # 創建各分頁內容
        self.monitor_tab = MonitorTab(self, self.state, self.monitor_frame, self.notebook)
        self.inventory_tab = InventoryTab(self, self.state, self.inventory_frame)
        self.status_tab = StatusTab(self, self.state, self.status_frame)
        self.combo_tab = ComboTab(self, self.state, self.combo_frame)
        self.help_tab = HelpTab(self, self.state, self.help_frame)
        self.version_tab = VersionTab(self, self.state, self.version_frame)
        self.about_tab = AboutTab(self, self.state, self.about_frame)

        # 初始化：設定當前分頁的視窗大小
        self.root.after(100, self.adjust_window_for_current_tab)

        # 恢復上次選擇的分頁
        self.root.after(200, self.restore_last_selected_tab)

        # 更新UI語言
        self.update_ui_language()

    def on_tab_change(self, event):
        """分頁切換事件處理 - 智能自適應視窗大小"""
        try:
            # 獲取當前選中的分頁
            current_tab = self.notebook.tab(self.notebook.select(), "text")

            # 調整視窗大小以適應當前分頁
            self.adjust_window_for_tab(current_tab)

            # 保存當前分頁到配置中
            self.config['last_selected_tab'] = current_tab

            try:
                tab_index = self.notebook.index(self.notebook.select())
                if tab_index == 1:
                    self.window_key_sender._focus_watcher_interval = 200
                    if self.window_key_sender._is_game_window_visible() and hasattr(self, 'inventory_tab') and self.inventory_tab.inventory_region:
                        self.root.after(0, self.inventory_tab.update_inventory_preview_from_current)
                else:
                    self.window_key_sender._focus_watcher_interval = 1000
            except Exception:
                pass

        except Exception as e:
            print(f"{self.get_text('tab_switch_resize_error')} {e}")

    def adjust_window_for_tab(self, tab_name):
        """根據分頁名稱調整視窗大小 - 支持智能縮放"""
        if tab_name in self.tab_min_sizes:
            target_width, target_height = self.tab_min_sizes[tab_name]

            # 嘗試動態計算實際最小尺寸
            try:
                dynamic_size = self.calculate_dynamic_tab_size(tab_name)
                if dynamic_size:
                    dyn_width, dyn_height = dynamic_size
                    # 使用動態計算和預設值的較大者
                    target_width = max(target_width, dyn_width + 50)  # 添加50px緩衝
                    target_height = max(target_height, dyn_height + 100)  # 添加100px緩衝
            except Exception as e:
                print(f"{self.get_text('dynamic_size_calc_failed')} {e}")

            # 獲取當前視窗大小和位置
            current_geometry = self.root.geometry()
            current_parts = current_geometry.split('+')
            current_size = current_parts[0].split('x')
            current_width = int(current_size[0])
            current_height = int(current_size[1])

            # 智能調整策略：
            # 1. 如果目標尺寸大於當前尺寸，放大到目標尺寸
            # 2. 如果目標尺寸小於當前尺寸且差距較大(>100px)，適度縮小
            # 3. 保證不小於應用程式的最小尺寸

            min_app_width, min_app_height = 650, 500  # 應用程式絕對最小尺寸

            # 計算新尺寸
            if target_width > current_width:
                new_width = target_width  # 需要放大
            elif current_width - target_width > 150:  # 當前尺寸比目標大很多時才縮小
                new_width = max(target_width + 50, min_app_width)  # 適度縮小，保留50px緩衝
            else:
                new_width = current_width  # 保持不變

            if target_height > current_height:
                new_height = target_height  # 需要放大
            elif current_height - target_height > 100:  # 當前尺寸比目標大很多時才縮小
                new_height = max(target_height + 50, min_app_height)  # 適度縮小，保留50px緩衝
            else:
                new_height = current_height  # 保持不變

            # 確保不小於最小尺寸
            new_width = max(new_width, min_app_width)
            new_height = max(new_height, min_app_height)

            # 只有在需要調整時才改變視窗大小
            if new_width != current_width or new_height != current_height:
                # 保持視窗位置不變，只調整大小
                if len(current_parts) >= 3:
                    x_pos = current_parts[1]
                    y_pos = current_parts[2]
                    new_geometry = f"{new_width}x{new_height}+{x_pos}+{y_pos}"
                else:
                    new_geometry = f"{new_width}x{new_height}"

                self.root.geometry(new_geometry)

                # 輸出調整信息
                if new_width > current_width or new_height > current_height:
                    print(self.get_text("window_enlarged").format(tab_name=tab_name, new_width=new_width, new_height=new_height))
                elif new_width < current_width or new_height < current_height:
                    print(self.get_text("window_shrunk").format(tab_name=tab_name, new_width=new_width, new_height=new_height))
            else:
                print(self.get_text("window_size_suitable").format(tab_name=tab_name))

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
            print(f"{self.get_text('calc_dynamic_size_error').format(tab_name=tab_name)} {e}")
            return None

    def adjust_window_for_current_tab(self):
        """調整視窗大小以適應當前分頁"""
        try:
            current_tab = self.notebook.tab(self.notebook.select(), "text")
            self.adjust_window_for_tab(current_tab)
        except Exception as e:
            print(f"{self.get_text('init_window_resize_error')} {e}")

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
                        print(self.get_text("restored_last_tab").format(last_tab=last_tab))
                        # 同步更新 focus watcher 間隔
                        if hasattr(self, 'window_key_sender'):
                            if i == 1:
                                self.window_key_sender._focus_watcher_interval = 200
                            else:
                                self.window_key_sender._focus_watcher_interval = 1000
                        break
        except Exception as e:
            print(f"{self.get_text('restore_tab_error')} {e}")

    def toggle_always_on_top(self):
        """切換GUI是否保持在最上方"""
        try:
            is_topmost = self.always_on_top_var.get()
            self.root.attributes("-topmost", is_topmost)
            print(f"GUI最上方設定已{'啟用' if is_topmost else '停用'}")

            # 自動保存設定
            try:
                self.config['always_on_top'] = is_topmost
                self.config_manager.save_config(self.config)
                print("GUI最上方設定已自動保存")
            except Exception as save_error:
                print(f"自動保存設定失敗: {save_error}")

        except Exception as e:
            print(f"切換GUI最上方設定失敗: {e}")

    def should_keep_topmost(self):
        """檢查是否應該保持GUI在最上方（根據用戶設定）"""
        return self.always_on_top_var.get()

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
                    except Exception:
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
        print(" 測試視窗層級系統...")

        # 創建一個測試設定視窗
        test_settings = self.create_settings_window("測試設定視窗", "300x200")
        test_label = ttk.Label(test_settings, text=self.get_text("test_window_title"))
        test_label.pack(pady=20)

        def test_reset_function():
            """測試重置功能是否會重新激活父視窗"""
            CustomMessageBox.show_info(self.get_text("test_reset"), self.get_text("test_reset_completed_message"), self.root)
            # 重新激活父視窗
            test_settings.lift()
            test_settings.focus_force()
            test_settings.attributes("-topmost", True)

    def setup_global_scroll(self):
        """設置全域滾輪支持，讓整個視窗都能使用滾輪"""
        # 為主視窗綁定滾輪事件
        self.root.bind("<MouseWheel>", self.handle_mousewheel)

        # 為notebook綁定分頁切換事件，確保滾輪在分頁切換後仍能工作
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # 儲存可滾動組件的引用
        self.scrollable_widgets = {}
        if hasattr(self, 'settings_tree'):
            self.scrollable_widgets['settings_tree'] = self.monitor_tab.settings_tree

    def on_tab_changed(self, event):
        """分頁切換時的處理"""
        # 確保滾輪事件仍然綁定
        self.root.focus_set()  # 確保主視窗有焦點
        # 同步觸發分頁切換的其他邏輯（視窗大小、interval 等）
        self.on_tab_change(event)

    def handle_mousewheel(self, event):
        """處理滾輪事件，轉發給當前可見的可滾動組件"""
        # 獲取當前選中的分頁索引
        current_tab_index = self.notebook.index(self.notebook.select())

        # 根據不同的分頁處理滾輪事件
        if current_tab_index == 0:  # 血量監控分頁
            # 血量監控分頁：滾動Treeview
            self.monitor_tab.settings_tree.yview_scroll(int(-1*(event.delta/120)), "units")
            return "break"

        elif current_tab_index == 2:  # 技能組合分頁
            if hasattr(self, 'combo_tab') and self.combo_tab.combo_canvas:
                self.combo_tab.combo_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                return "break"

        elif current_tab_index == 4:  # 使用說明分頁
            help_canvas = self.help_tab.help_canvas if hasattr(self, 'help_tab') else None
            if help_canvas:
                help_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                return "break"

        elif current_tab_index == 6:  # 關於作者分頁
            if hasattr(self, 'about_tab') and self.about_tab.about_canvas:
                self.about_tab.about_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                return "break"

        return "break"  # 阻止事件繼續傳播

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
        """移除背包相關選擇的全局ESC鍵監聽"""
        try:
            if hasattr(self, 'global_esc_active_inventory') and self.global_esc_active_inventory:
                # 檢查是否還有其他背包相關的選擇在進行中
                inventory_ui_active = getattr(self, 'inventory_ui_selection_active', False)
                inventory_active = getattr(self, 'inventory_selection_active', False)

                # 只有在沒有任何背包相關選擇活動時才移除監聽
                if not inventory_ui_active and not inventory_active:
                    keyboard.remove_hotkey('esc')
                    self.global_esc_active_inventory = False
                    print("已移除背包相關選擇的全局ESC監聽")
                else:
                    print("還有其他背包相關選擇在進行中，保持ESC監聽")
        except Exception as e:
            print(f"移除背包相關選擇的全局ESC監聽失敗: {e}")

    def global_esc_handler_for_inventory(self):
        """背包相關選擇的全局ESC鍵處理函數"""
        try:
            # 檢查背包UI選擇
            if hasattr(self, 'inventory_ui_selection_active') and self.inventory_ui_selection_active:
                # 使用tkinter的after方法來確保在主線程中執行
                self.root.after(0, lambda: self.inventory_tab.cancel_inventory_ui_selection(None))
                print("檢測到ESC鍵，取消背包UI選擇")
                return

            # 檢查背包區域選擇
            if hasattr(self, 'inventory_selection_active') and self.inventory_selection_active:
                # 使用tkinter的after方法來確保在主線程中執行
                self.root.after(0, lambda: self.inventory_tab.cancel_inventory_selection(None))
                print("檢測到ESC鍵，取消背包區域選擇")
                return
        except Exception as e:
            print(f"背包相關選擇的全局ESC處理失敗: {e}")

    def check_game_window_minimized(self, window_title):
        """檢查遊戲視窗是否最小化，如果最小化則顯示提醒視窗"""
        try:
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                return False  # 視窗不存在，不處理

            game_window = windows[0]
            if game_window.isMinimized:
                messagebox.showwarning(
                    self.get_text("warning"),
                    self.get_text("game_window_minimized_warning")
                )
                return True  # 已顯示提醒
            return False  # 未最小化
        except Exception as e:
            print(f"[WARN] 檢查遊戲視窗狀態失敗: {e}")
            return False

    # ========== 線程安全的監控狀態管理 ==========
    def is_monitoring(self):
        """線程安全地檢查監控狀態"""
        with self.state.monitoring_lock:
            return self.state.monitoring

    def set_monitoring(self, state):
        """線程安全地設置監控狀態"""
        with self.state.monitoring_lock:
            self.state.monitoring = state

    def wait_monitoring_stopped(self, timeout=2.0):
        """等待監控線程停止"""
        start_time = time.time()
        while self.is_monitoring() and (time.time() - start_time) < timeout:
            time.sleep(0.05)

        # 等待線程完全結束
        if self.state.monitor_thread and self.state.monitor_thread.is_alive():
            self.state.monitor_thread.join(timeout=max(0.1, timeout - (time.time() - start_time)))

    # ========== 線程安全的連段狀態管理 ==========
    def is_combo_running(self):
        """線程安全地檢查連段狀態"""
        with self.state.combo_lock:
            return self.state.combo_running

    def set_combo_running(self, state):
        """線程安全地設置連段狀態"""
        with self.state.combo_lock:
            self.state.combo_running = state

    def wait_combo_stopped(self, timeout=2.0):
        """等待連段線程停止"""
        start_time = time.time()
        while self.is_combo_running() and (time.time() - start_time) < timeout:
            time.sleep(0.05)

        # 等待線程完全結束
        if self.state.combo_thread and self.state.combo_thread.is_alive():
            self.state.combo_thread.join(timeout=max(0.1, timeout - (time.time() - start_time)))

    # ========== 線程安全的全域暫停管理 ==========
    def is_global_pause(self):
        """線程安全地檢查全域暫停狀態"""
        with self.state.global_pause_lock:
            return self.state.global_pause

    def set_global_pause(self, state):
        """線程安全地設置全域暫停狀態"""
        with self.state.global_pause_lock:
            self.state.global_pause = state

    def start_monitoring(self):
        # 檢查是否已在監控中
        if self.is_monitoring():
            print("[WARN] 監控已在運行中，跳過重複啟動")
            return

        # 檢查OpenCV是否可用
        if not OPENCV_AVAILABLE:
            messagebox.showerror(self.get_text("error"), "OpenCV不可用，無法啟動監控功能。請重新安裝應用程式。")
            return

        if not self.monitor_tab.window_var.get():
            messagebox.showerror(self.get_text("error"), self.get_text("select_game_window_first"))
            return

        # 檢查遊戲視窗是否最小化
        if self.check_game_window_minimized(self.monitor_tab.window_var.get()):
            return

        if not self.config.get('region'):
            messagebox.showerror(self.get_text("error"), self.get_text("select_health_bar_region_first"))
            return

        if not self.config.get('settings'):
            messagebox.showerror(self.get_text("error"), self.get_text("set_at_least_one_trigger"))
            return

        # 激活遊戲視窗
        try:
            windows = gw.getWindowsWithTitle(self.monitor_tab.window_var.get())
            if windows:
                window = windows[0]
                window.activate()
                time.sleep(0.1)  # 給一點時間讓視窗激活
        except Exception as e:
            print(f"激活遊戲視窗失敗: {e}")

        # 線程安全地設置監控狀態
        self.set_monitoring(True)
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        # 添加狀態訊息
        self.status_tab.add_status_message(self.get_text("health_monitor_started"), "success")

        # 開始監控時設置為非干擾模式：降低不透明度但保持可見
        self.root.attributes("-alpha", 0.8)  # 輕微透明
        self.manage_window_hierarchy(self.root, "MAIN")  # 設置主視窗層級

        self.state.monitor_thread = threading.Thread(target=self.monitor_health)
        self.state.monitor_thread.daemon = True
        self.state.monitor_thread.start()

    def stop_monitoring(self):
        """Stop monitoring without blocking the Tk main thread."""
        if not self.is_monitoring():
            return

        print("[STOP] ...")
        self.set_monitoring(False)

        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_tab.add_status_message(self.get_text("health_monitor_stopped"), "info")

        self.root.attributes("-alpha", 1.0)
        self.manage_window_hierarchy(self.root, "MAIN")
        self.root.after(10, self._wait_for_monitoring_stop_async)

    def _wait_for_monitoring_stop_async(self, deadline=None):
        """Wait for monitor thread exit without freezing the GUI."""
        if deadline is None:
            deadline = time.time() + 2.0

        thread = self.state.monitor_thread
        if not thread or not thread.is_alive():
            self.state.monitor_thread = None
            print("[STOP] ")
            return

        if time.time() >= deadline:
            print("[STOP] ")
            return

        self.root.after(25, lambda: self._wait_for_monitoring_stop_async(deadline))

    def restart_monitoring_silently(self):
        """靜默重新啟動血魔監控（用於全域暫停恢復）"""
        if self.is_monitoring():
            return  # 已經在監控中

        if not self.monitor_tab.window_var.get():
            raise Exception("未選擇遊戲視窗")

        if not self.config.get('region'):
            raise Exception("未設定血量條區域")

        if not self.config.get('settings'):
            raise Exception("未設定觸發條件")

        # 激活遊戲視窗（靜默）
        try:
            windows = gw.getWindowsWithTitle(self.monitor_tab.window_var.get())
            if windows:
                window = windows[0]
                window.activate()
                time.sleep(0.1)
        except Exception as e:
            print(f"激活遊戲視窗失敗: {e}")

        # 線程安全地設置監控狀態
        self.set_monitoring(True)

        # 更新UI（如果元件存在）
        try:
            if hasattr(self, 'start_btn') and self.start_btn:
                self.start_btn.config(state=tk.DISABLED)
            if hasattr(self, 'stop_btn') and self.stop_btn:
                self.stop_btn.config(state=tk.NORMAL)
        except Exception:
            pass  # UI 更新失敗不影響功能

        # 開始監控時設置為非干擾模式
        self.root.attributes("-alpha", 0.8)
        self.manage_window_hierarchy(self.root, "MAIN")

        self.state.monitor_thread = threading.Thread(target=self.monitor_health)
        self.state.monitor_thread.daemon = True
        self.state.monitor_thread.start()

    def monitor_health(self):
        with _mss_singleton:
            while self.is_monitoring():
                # 提前檢查監控狀態，避免不必要的處理
                if not self.is_monitoring():
                    break

                try:
                    # 獲取遊戲視窗位置
                    windows = gw.getWindowsWithTitle(self.monitor_tab.window_var.get())
                    if not windows:
                        self.monitor_tab.update_status("--", "--", "視窗未找到", "")
                        self.status_tab.add_status_message(self.get_text("game_window_closed"), "warning")
                        interruptible_sleep(1.0, self.is_monitoring)
                        continue

                    window = windows[0]

                    # 檢查遊戲視窗是否在前台且非最小化
                    if window.isMinimized or not window.isActive:
                        if window.isMinimized:
                            self.monitor_tab.update_status("--", "--", self.get_text("game_window_minimized"), "")
                        else:
                            self.monitor_tab.update_status("--", "--", self.get_text("waiting_for_game_window"), "")
                        if not self.monitor_tab._preview_placeholder_shown:
                            self.monitor_tab._preview_placeholder_shown = True
                            msg_key = "game_window_minimized" if window.isMinimized else "game_window_lost_focus"
                            self.status_tab.add_status_message(self.get_text(msg_key), "warning")
                            self.root.after(0, self.monitor_tab._show_health_preview_placeholder)
                            self.root.after(0, self.monitor_tab._show_mana_preview_placeholder)
                        interruptible_sleep(0.5, self.is_monitoring)
                        continue
                    if self.monitor_tab._preview_placeholder_shown:
                        self.monitor_tab._preview_placeholder_shown = False
                        self.status_tab.add_status_message(self.get_text("game_window_regained_focus"), "success")

                    # 計算區域在螢幕上的絕對位置
                    x, y, w, h = self.config['region']
                    abs_x = window.left + x
                    abs_y = window.top + y

                    monitor = {"top": abs_y, "left": abs_x, "width": w, "height": h}
                    img = capture_region_to_cv2(monitor)

                    # 分析血量
                    health_percent = analyze_health(
                        img,
                        lambda seg: is_health_color(seg, self.red_saturation_min, self.red_value_min, self.red_h_range, self.green_h_range, self.green_saturation_min, self.green_value_min, self.health_threshold),
                        lambda seg: get_health_color_ratio(seg, self.red_saturation_min, self.red_value_min, self.red_h_range, self.green_h_range, self.green_saturation_min, self.green_value_min),
                        self.health_threshold,
                    )
                    main_color = get_main_color(img)

                    # 分析魔力（如果有設定魔力區域）
                    mana_percent = "--"
                    if self.config.get('mana_region'):
                        try:
                            # 計算魔力區域在螢幕上的絕對位置
                            mx, my, mw, mh = self.config['mana_region']
                            mana_abs_x = window.left + mx
                            mana_abs_y = window.top + my

                            mana_monitor = {"top": mana_abs_y, "left": mana_abs_x, "width": mw, "height": mh}
                            mana_img = capture_region_to_cv2(mana_monitor)

                            # 分析魔力
                            mana_percent = analyze_mana(mana_img, is_mana_color, get_mana_color_ratio)

                            # 動態更新魔力預覽圖片
                            self.monitor_tab.update_live_mana_preview(mana_img, mana_percent)
                        except Exception as e:
                            print(f"魔力分析錯誤: {e}")
                            mana_percent = "--"

                    # 更新狀態
                    mana_value = int(mana_percent) if mana_percent != "--" else None
                    self.monitor_tab.update_status(
                        f"{health_percent}%",
                        f"{mana_percent}%",
                        main_color,
                        check_triggers(
                            health_percent, mana_value,
                            self.config, self.state.last_trigger_times,
                            self.get_text, self.is_interface_ui_visible,
                            self.monitor_tab.window_var.get(),
                            getattr(self, 'interface_ui_region', None),
                            getattr(self, 'interface_ui_screenshot', None),
                        ),
                    )

                    # 動態更新血量預覽圖片
                    self.monitor_tab.update_live_preview(img, health_percent)

                    # 觸發相應的動作
                    trigger_actions(
                        health_percent, mana_value,
                        self.config, self.state.last_trigger_times,
                        self.monitor_tab.multi_trigger_var.get(),
                        self.add_status_message, self.get_text,
                        self.is_interface_ui_visible, self.press_key_sequence,
                        self.monitor_tab.window_var.get(),
                        getattr(self, 'interface_ui_region', None),
                        getattr(self, 'interface_ui_screenshot', None),
                    )

                    # 使用選擇的檢查頻率
                    try:
                        interval_ms = int(self.monitor_tab.monitor_interval_var.get())
                        interruptible_sleep(interval_ms / 1000.0, self.is_monitoring)  # 轉換為秒
                    except (ValueError, AttributeError):
                        interruptible_sleep(0.1, self.is_monitoring)  # 預設100ms

                except Exception as e:
                    print(f"監控錯誤: {e}")
                    self.monitor_tab.update_status("--", "--", "--", f"錯誤: {str(e)}")
                    interruptible_sleep(1, self.is_monitoring)

    def press_key_sequence(self, key_sequence, health_percent=None):
        """處理多鍵序列，按順序按下每個鍵 - 血魔監控專用"""
        print(f" 血魔監控開始執行按鍵序列: {key_sequence}")

        # 解析鍵序列（用 - 分隔）
        keys = [key.strip() for key in key_sequence.split('-')]
        print(f" 血魔監控解析後的按鍵列表: {keys}")

        # 獲取遊戲窗口句柄
        game_hwnd = self.window_key_sender.get_game_window_handle()
        if game_hwnd:
            print(f" 血魔監控使用全局發送到遊戲窗口: {game_hwnd}")
            # 使用修復版本的按鍵發送（keyboard庫 + 防重複）
            for i, key in enumerate(keys):
                vk_code = self.window_key_sender.map_key_to_vk_code(key)
                if vk_code:
                    print(f" 血魔按鍵 {i+1}/{len(keys)}: {key} -> VK_{vk_code}")
                    self.window_key_sender.send_key_to_window(game_hwnd, vk_code)  # 使用修復版本
                else:
                    print(f" 血魔按鍵 {i+1}/{len(keys)}: {key} -> 無法映射鍵碼")

                # 如果不是最後一個鍵，添加延遲
                if i < len(keys) - 1:
                    print(" 血魔按鍵間延遲: 25ms")
                    time.sleep(0.025)  # 25毫秒延遲
        else:
            print("使用全域鍵盤事件（無法獲取遊戲窗口）")
            # 回退到全局鍵盤事件
            for i, key in enumerate(keys):
                # 處理特殊鍵名映射
                mapped_key = self.window_key_sender.map_key_name(key)
                print(f"按鍵 {i+1}/{len(keys)}: {key} -> {mapped_key}")
                # 按下並釋放鍵
                keyboard.press_and_release(mapped_key)

                # 如果不是最後一個鍵，添加延遲
                if i < len(keys) - 1:
                    print("按鍵間延遲: 25ms")
                    time.sleep(0.025)  # 25毫秒延遲

        print(f"按鍵序列執行完成: {key_sequence}")

        # 記錄觸發時間（用於冷卻計算）
        if health_percent is not None:
            # 處理魔力設定的特殊鍵
            if isinstance(health_percent, str) and health_percent.startswith('mana_'):
                # 對於魔力設定，使用原始百分比作為鍵
                mana_percent = int(health_percent.split('_')[1])
                self.state.last_trigger_times[f"mana_{mana_percent}"] = time.time()
                print(f"記錄魔力觸發時間: mana_{mana_percent}")
            else:
                # 對於血量設定，直接使用百分比
                self.state.last_trigger_times[health_percent] = time.time()
                print(f"記錄血量觸發時間: {health_percent}")


    def open_video_link(self, url):
        """打開影片連結"""
        import webbrowser
        try:
            webbrowser.open(url)
        except Exception as e:
            messagebox.showerror(self.get_text("error"), self.get_text("browser_open_failed").format(error=e))

    def select_interface_ui_region(self):
        """Delegate to inventory_tab - wrapper for backward compatibility."""
        if hasattr(self, 'inventory_tab'):
            self.inventory_tab.select_interface_ui_region()

    def setup_hotkeys(self):
        # 全域熱鍵，不受視窗焦點限制
        keyboard.add_hotkey('f3', self.inventory_tab.quick_clear_inventory)  # F3: 一鍵清包
        keyboard.add_hotkey('f5', self.inventory_tab.return_to_hideout)    # F5: 返回藏身
        keyboard.add_hotkey('f6', self.inventory_tab.f6_pickup_items)      # F6: 一鍵取物
        keyboard.add_hotkey('f9', self.toggle_global_pause)  # F9: 全域暫停開關
        keyboard.add_hotkey('f10', self.toggle_monitoring)   # F10: 監控開關
        keyboard.add_hotkey('f12', global_f12_handler)       # F12: 緊急關閉（使用全局處理器）

        self.status_tab.add_status_message(self.get_text("global_hotkeys_registered"), "success")

        # 設定 CTRL+左鍵自動點擊監聽器
        self.auto_click_manager.setup_auto_click_listener()

    def toggle_global_pause(self):
        """F9: 全域暫停開關 - 暫停/恢復所有熱鍵功能（線程安全）"""
        # 使用鎖保護全域暫停狀態的修改
        with self.state.global_pause_lock:
            self.state.global_pause = not self.state.global_pause
            is_pausing = self.state.global_pause

        if is_pausing:
            print("[STOP] 全域暫停已啟用 - 所有熱鍵功能已暫停")
            print(" 現在可以安全聊天，不會誤觸任何熱鍵")
            print(" 再次按F9可恢復所有功能")

            # 添加狀態訊息
            self.status_tab.add_status_message(self.get_text("global_pause_activated"), "warning")

            # 記錄並停止血魔監控（如果正在運行）
            if self.is_monitoring():
                self.state.monitoring_was_active = True
                self.stop_monitoring()
                print(" 血魔監控已自動停止")
                self.status_tab.add_status_message(self.get_text("health_monitor_auto_stopped"), "info")
            else:
                self.state.monitoring_was_active = False

            # 記錄並停止技能連段（如果正在運行）
            if self.is_combo_running():
                self.state.combo_was_running = True
                self.combo_tab.stop_combo_system()
                print(" 技能連段已自動停止")
                self.status_tab.add_status_message(self.get_text("combo_system_auto_stopped"), "info")
            else:
                self.state.combo_was_running = False

        else:
            print(" 全域暫停已解除 - 自動恢復之前的功能")

            # 添加狀態訊息
            self.status_tab.add_status_message(self.get_text("global_pause_deactivated"), "success")

            # 自動恢復血魔監控（如果之前處於活躍狀態）
            if self.state.monitoring_was_active:
                try:
                    # 靜默重新啟動血魔監控
                    self.restart_monitoring_silently()
                    print("[START] 血魔監控已自動重新啟動")
                    self.status_tab.add_status_message(self.get_text("health_monitor_auto_restarted"), "success")
                except Exception as e:
                    print(f"[WARN] 血魔監控自動重新啟動失敗: {e}")
                    print(" 請手動重新啟動血魔監控")
                    self.status_tab.add_status_message(self.get_text("health_monitor_restart_failed").format(error=str(e)), "error")

            # 自動恢復技能連段（如果之前處於運行狀態）
            if self.state.combo_was_running:
                try:
                    # 靜默重新啟動技能連段系統
                    self.combo_tab.restart_combo_system_silently()
                    print("[START] 技能連段已自動重新啟動")
                    self.status_tab.add_status_message("技能連段已自動重新啟動", "success")
                except Exception as e:
                    print(f"[WARN] 技能連段自動重新啟動失敗: {e}")
                    print(" 請手動重新啟動技能連段系統")
                    self.status_tab.add_status_message(f"技能連段自動重啟失敗: {str(e)}", "error")

            print(" 所有功能已完全恢復正常")

        # 更新UI顯示（如果有狀態標籤）
        self.update_pause_status_display()

    def update_pause_status_display(self):
        """更新暫停狀態顯示"""
        if self.pause_status_label:
            if self.is_global_pause():
                self.pause_status_label.config(
                    text="[STOP] 全域暫停中 - 所有熱鍵已停用",
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
        """F10: 血魔監控開關（線程安全）"""
        # 全域暫停檢查
        if self.is_global_pause():
            print("[STOP] 全域暫停中，跳過F10熱鍵")
            self.status_tab.add_status_message("按下 F10 - 因全域暫停模式而跳過執行", "warning")
            return

        if self.is_monitoring():
            self.status_tab.add_status_message("按下 F10 - 停止血魔監控", "hotkey")
            self.stop_monitoring()
        else:
            self.status_tab.add_status_message("按下 F10 - 啟動血魔監控", "hotkey")
            self.start_monitoring()

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

    def close_app(self):
        if self.state._is_closing:
            return

        self.state._is_closing = True

        if hasattr(self, 'version_tab') and self.version_tab._silent_version_check_after_id:
            try:
                self.root.after_cancel(self.version_tab._silent_version_check_after_id)
            except Exception:
                pass
            self.version_tab._silent_version_check_after_id = None

        if hasattr(self, 'usage_tracker'):
            self.usage_tracker.stop()

        # 計算並記錄運行時間
        end_time = datetime.now()
        runtime = end_time - self.start_time
        runtime_str = f"{runtime.days}天 {runtime.seconds//3600}小時 {(runtime.seconds%3600)//60}分鐘 {runtime.seconds%60}秒"
        print(f"應用程式運行時間: {runtime_str}")
        self.status_tab.add_status_message(f"應用程式運行時間: {runtime_str}", "info")

        # 添加關閉訊息
        self.status_tab.add_status_message("工具正在關閉，清理資源中...", "info")

        # 儲存設定
        try:
            self.save_config(show_message=False)
            print("設定已儲存")
        except Exception as e:
            print(f"儲存設定失敗: {e}")

        # 停止AHK自動點擊
        self.auto_click_manager.stop_auto_click_ahk()

        mouse_interrupt_thread = getattr(self, 'mouse_interrupt_thread', None)
        if mouse_interrupt_thread and mouse_interrupt_thread.is_alive():
            try:
                mouse_interrupt_thread.join(timeout=0.3)
            except Exception:
                pass

        # 清理鍵盤監聽器
        try:
            keyboard.unhook_all()
        except Exception:
            pass

        self.state.monitoring = False
        self.status_tab.add_status_message(self.get_text("tool_closed_successfully"), "info")

        # 清理全局引用
        global _app_instance
        _app_instance = None

        try:
            self.root.quit()
        finally:
            try:
                self.root.destroy()
            except Exception:
                pass

    def restart_app(self):
        """重新啟動應用程式"""
        self.state.monitoring = False
        self.save_config()

        try:
            if getattr(sys, 'frozen', False):
                # 如果是打包後的EXE，直接重新啟動EXE
                exe_path = sys.executable
                print(f"重新啟動EXE應用程式: {exe_path}")
                import subprocess
                subprocess.Popen([exe_path],
                               cwd=os.path.dirname(exe_path),
                               creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                # 如果是Python腳本，智能選擇重新啟動方式
                script_path = os.path.abspath(__file__)

                # 嘗試找到最簡單的相對路徑
                current_dir = os.getcwd()
                os.path.dirname(script_path)

                try:
                    # 計算相對路徑
                    relative_path = os.path.relpath(script_path, current_dir)
                    # 如果相對路徑太複雜、包含太多..或包含空格，就使用絕對路徑
                    if (relative_path.count('..') > 2 or
                        len(relative_path) > len(script_path) * 0.7 or
                        ' ' in relative_path):
                        relative_path = script_path
                except ValueError:
                    # 如果無法計算相對路徑，使用絕對路徑
                    relative_path = script_path

                print(f"重新啟動Python腳本: {sys.executable} {relative_path}")
                # 使用subprocess正確處理包含空格的路徑
                import subprocess
                subprocess.Popen([sys.executable, relative_path],
                               cwd=current_dir,
                               creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            print(f"重啟失敗: {e}")
            messagebox.showerror("錯誤", f"無法重新啟動程式: {e}")
            return

        # 關閉當前程式
        self.root.quit()
        self.root.destroy()
        sys.exit(0)

    def load_config(self):
        """????"""
        print("[DEBUG] load_config ")
        try:
            success, message = self.config_manager.load_config()
            self.config = self.config_manager.config

            if success:
                self.status_tab.add_status_message(self.get_text("config_loaded_successfully"), "success")
            else:
                self.status_tab.add_status_message(self.get_text("config_file_not_found"), "info")

            self.monitor_tab.selected_region = self.config.get('region')
            self.monitor_tab.selected_mana_region = self.config.get('mana_region')
            self.inventory_tab.inventory_region = self.config.get('inventory_region')
            self.inventory_tab.empty_inventory_colors = self.config.get('empty_inventory_colors', [])
            self.inventory_grid_positions = [tuple(pos) for pos in self.config.get('inventory_grid_positions', [])]
            self.inventory_tab.grid_offset_x = self.config.get('grid_offset_x', 0)
            self.inventory_tab.grid_offset_y = self.config.get('grid_offset_y', 0)
            self.inventory_tab.excluded_inventory_slots = set(self.config.get('excluded_inventory_slots', []))

            click_mode = self.config.get('inventory_clear_click_mode', 'left')
            if hasattr(self, 'inventory_clear_click_mode'):
                self.inventory_tab.inventory_clear_click_mode.set(click_mode)

            self.inventory_tab.inventory_ui_region = self.config.get('inventory_ui_region')
            if self.inventory_tab.inventory_ui_region:
                self.inventory_tab.load_ui_screenshot_from_file()

            self.interface_ui_region = self.config.get('interface_ui_region')
            if self.interface_ui_region:
                self.inventory_tab.load_interface_ui_screenshot_from_file()

            if hasattr(self, 'empty_color_label') and self.empty_inventory_colors:
                recorded_count = len([c for c in self.inventory_tab.empty_inventory_colors if c != (0, 0, 0)])
                self.empty_color_label.config(
                    text=self.get_text("recorded_colors_template").format(count=recorded_count),
                    background="lightgreen",
                )

            if hasattr(self, 'inventory_tab') and hasattr(self.inventory_tab, 'inventory_ui_label') and self.inventory_tab.inventory_ui_region:
                self.inventory_tab.inventory_ui_label.config(text=self.get_text("inventory_ui_recorded"), background="lightgreen")
                if hasattr(self, 'ui_preview_canvas'):
                    if self._startup_phase:
                        self._startup_visual_refresh_pending = True
                    else:
                        self.inventory_tab.update_ui_preview()

            if hasattr(self.monitor_tab, 'interface_ui_label') and self.interface_ui_region:
                self.monitor_tab.interface_ui_label.config(text=get_interface_ui_region_text(self.interface_ui_region), background="lightgreen")
                if hasattr(self.monitor_tab, 'interface_ui_preview_canvas'):
                    if self._startup_phase:
                        self._startup_visual_refresh_pending = True
                    else:
                        self.inventory_tab.update_interface_ui_preview()

            if 'inventory_window_title' in self.config:
                self.inventory_tab.inventory_window_var.set(self.config['inventory_window_title'])
            elif 'window_title' in self.config:
                self.inventory_tab.inventory_window_var.set(self.config['window_title'])

            if hasattr(self.monitor_tab, 'window_var') and 'window_title' in self.config:
                self.monitor_tab.window_var.set(self.config['window_title'])

            self.blood_magic_enabled = self.config.get('blood_magic_enabled', False)
            self.blood_magic_region = self.config.get('blood_magic_region', None)
            self.blood_magic_threshold = self.config.get('blood_magic_threshold', 50)
            self.blood_magic_window_title = self.config.get('blood_magic_window_title', '')

            self.state.monitor_interval = self.config.get('monitor_interval', 0.1)
            self.auto_clear_enabled = self.config.get('auto_clear_enabled', False)
            self.clear_interval = self.config.get('clear_interval', 30)

            if hasattr(self, 'monitor_interval_var'):
                interval_ms = int(self.state.monitor_interval * 1000)
                self.monitor_tab.monitor_interval_var.set(str(interval_ms))

            if hasattr(self, 'preview_enabled'):
                preview_enabled = self.config.get('preview_enabled', True)
                self.preview_enabled.set(preview_enabled)
            if hasattr(self, 'preview_interval_var'):
                preview_interval = self.config.get('preview_interval', 250)
                self.preview_interval_var.set(str(preview_interval))

            if 'settings' in self.config:
                print(f": {len(self.config['settings'])} ")
                migrated = False
                for setting in self.config['settings']:
                    old_type = setting.get('type', 'HP')
                    if old_type in ['health', 'mana']:
                        new_type = 'HP' if old_type == 'health' else 'MP'
                        setting['type'] = new_type
                        migrated = True
                        print(f"  : {old_type} -> {new_type}")

                if migrated:
                    self.save_config(show_message=False)
                    print("")

                for setting in self.config['settings']:
                    print(f"  - {setting.get('type', 'HP')} {setting.get('percent', 0)}%: {setting.get('key', '')}")
            else:
                print("")

            self.health_threshold = self.config.get('health_threshold', 0.8)
            self.red_h_range = self.config.get('red_h_range', 5)
            self.green_h_range = self.config.get('green_h_range', 40)
            self.red_saturation_min = self.config.get('red_saturation_min', 50)
            self.red_value_min = self.config.get('red_value_min', 50)
            self.green_saturation_min = self.config.get('green_saturation_min', 50)
            self.green_value_min = self.config.get('green_value_min', 50)

            self.interface_ui_mse_threshold = int(self.config.get('interface_ui_mse_threshold', 800))
            self.interface_ui_ssim_threshold = float(self.config.get('interface_ui_ssim_threshold', 0.6))
            self.interface_ui_hist_threshold = float(self.config.get('interface_ui_hist_threshold', 0.7))
            self.interface_ui_color_threshold = int(self.config.get('interface_ui_color_threshold', 35))

            if hasattr(self, 'mse_threshold_var'):
                self.inventory_tab.mse_threshold_var.set(str(self.interface_ui_mse_threshold))
            if hasattr(self, 'ssim_threshold_var'):
                self.inventory_tab.ssim_threshold_var.set(str(self.interface_ui_ssim_threshold))
            if hasattr(self, 'hist_threshold_var'):
                self.inventory_tab.hist_threshold_var.set(str(self.interface_ui_hist_threshold))
            if hasattr(self, 'color_threshold_var'):
                self.inventory_tab.color_threshold_var.set(str(self.interface_ui_color_threshold))

            self.monitor_tab.multi_trigger_var.set(self.config.get('multi_trigger', False))

            always_on_top = self.config.get('always_on_top', False)
            self.always_on_top_var.set(always_on_top)

            if 'always_on_top' not in self.config:
                self.config['always_on_top'] = always_on_top
                try:
                    with open(self.config_file, 'w', encoding='utf-8') as f:
                        json.dump(self.config, f, indent=2, ensure_ascii=False)
                    print("GUI")
                except Exception as save_error:
                    print(f": {save_error}")

            if 'window_geometry' in self.config:
                try:
                    saved_geometry = self.config['window_geometry']
                    self.root.geometry(saved_geometry)
                    print(f": {saved_geometry}")
                except Exception as e:
                    print(f": {e}")

            self.pickup_coordinates = self.config.get('pickup_coordinates', [])
            print(f"F6: {len(self.pickup_coordinates)} ")
            while len(self.pickup_coordinates) < 5:
                self.pickup_coordinates.append([0, 0])
            if hasattr(self, 'pickup_coords_label'):
                self.inventory_tab.update_pickup_status()

            if 'combo_sets' in self.config:
                self.state.combo_sets = self.config['combo_sets']
                for combo_set in self.state.combo_sets:
                    if 'trigger_delay' not in combo_set:
                        combo_set['trigger_delay'] = ''
                    if 'stationary_attacks' not in combo_set:
                        combo_set['stationary_attacks'] = [False, False, False, False, False]

                while len(self.state.combo_sets) < 3:
                    self.state.combo_sets.append({
                        'trigger_key': 'Q' if len(self.state.combo_sets) == 0 else 'W' if len(self.state.combo_sets) == 1 else 'E',
                        'trigger_delay': '',
                        'combo_keys': ['', '', '', '', ''],
                        'delays': ['', '', '', '', ''],
                        'stationary_attacks': [False, False, False, False, False],
                    })
                self.state.combo_sets = self.state.combo_sets[:3]
                print(f": {len(self.state.combo_sets)} ")

            if 'combo_enabled' in self.config:
                self.state.combo_enabled = self.config['combo_enabled']
                while len(self.state.combo_enabled) < 3:
                    self.state.combo_enabled.append(False)
                self.state.combo_enabled = self.state.combo_enabled[:3]
                print(f": {self.state.combo_enabled}")
            else:
                self.state.combo_enabled = [False, False, False]

            self.combo_tab.update_combo_ui_from_config()
            self.inventory_tab.update_offset_labels()
            if self._startup_phase:
                self._startup_visual_refresh_pending = True
            else:
                self.inventory_tab.update_inventory_preview_from_current()

            if hasattr(self.monitor_tab, 'region_label'):
                self.monitor_tab.region_label.config(
                    text=get_region_text(self.config),
                    background="lightgreen" if self.config.get('region') else "lightgray",
                )
            if hasattr(self.monitor_tab, 'mana_region_label'):
                self.monitor_tab.mana_region_label.config(
                    text=get_mana_region_text(self.config),
                    background="lightgreen" if self.config.get('mana_region') else "lightgray",
                )

            if hasattr(self.monitor_tab, 'load_settings_to_tree'):
                self.monitor_tab.load_settings_to_tree()

            if hasattr(self, 'ui_preview_canvas'):
                self.inventory_tab.update_ui_preview()

            if hasattr(self, 'update_pickup_coordinates_display'):
                self.monitor_tab.update_pickup_coordinates_display()

            loaded_language = self.config.get('language', 'zh-tw')
            # print(f"[DEBUG] load_config : {loaded_language}")
            # print(f"[DEBUG] load_config : {self.language_manager.current_language}")

            if loaded_language != self.language_manager.current_language:
                # print(f"[DEBUG]  {self.language_manager.current_language} -> {loaded_language}")
                self.language_manager.change_language(loaded_language)
                self.current_language = loaded_language
            else:
                pass

            display_name = self.language_reverse_map.get(self.current_language, '????')
            self.language_var.set(display_name)

            self.update_ui_language()

        except Exception as e:
            error_msg = f"?????????: {e}"
            print(f"[ERROR] {error_msg}")
            self.status_tab.add_status_message(f"??????- {str(e)}", "error")
            self.config = {}

    def save_config(self, show_message=True):
        """儲存血魔監控設定"""
        try:
            # 儲存遊戲視窗設定
            self.config['window_title'] = self.monitor_tab.window_var.get()

            # 儲存區域設定
            if hasattr(self.monitor_tab, 'selected_region') and self.monitor_tab.selected_region:
                self.config['region'] = self.monitor_tab.selected_region
            if hasattr(self.monitor_tab, 'selected_mana_region') and self.monitor_tab.selected_mana_region:
                self.config['mana_region'] = self.monitor_tab.selected_mana_region

            # 儲存背包相關設定
            if hasattr(self, 'inventory_tab') and self.inventory_tab.inventory_region:
                self.config['inventory_region'] = self.inventory_tab.inventory_region
            if hasattr(self, 'inventory_tab') and self.inventory_tab.inventory_ui_region:
                self.config['inventory_ui_region'] = self.inventory_tab.inventory_ui_region
            if self.interface_ui_region:
                self.config['interface_ui_region'] = self.interface_ui_region
            if hasattr(self, 'inventory_tab') and self.inventory_tab.empty_inventory_colors:
                self.config['empty_inventory_colors'] = self.inventory_tab.empty_inventory_colors
            if self.inventory_grid_positions:
                self.config['inventory_grid_positions'] = self.inventory_grid_positions
            if hasattr(self, 'inventory_tab'):
                self.config['grid_offset_x'] = self.inventory_tab.grid_offset_x
                self.config['grid_offset_y'] = self.inventory_tab.grid_offset_y
                self.config['excluded_inventory_slots'] = sorted(self.inventory_tab.excluded_inventory_slots)

            # 儲存觸發設定
            settings = []
            if hasattr(self.monitor_tab, 'settings_tree'):
                for item in self.monitor_tab.settings_tree.get_children():
                    values = self.monitor_tab.settings_tree.item(item, 'values')
                    if len(values) >= 4:
                        setting_type = "HP" if values[0] == "HP" else "MP"
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
            self.config['multi_trigger'] = self.monitor_tab.multi_trigger_var.get()

            # 儲存GUI最上方設定
            self.config['always_on_top'] = self.always_on_top_var.get()

            # 儲存語言設定
            self.config['language'] = self.current_language

            # 儲存窗口位置和大小
            try:
                current_geometry = self.root.geometry()
                self.config['window_geometry'] = current_geometry
                print(f"已儲存窗口位置: {current_geometry}")
            except Exception as e:
                print(f"儲存窗口位置失敗: {e}")

            # 儲存連段設定
            if hasattr(self, 'combo_sets'):
                self.config['combo_sets'] = self.state.combo_sets
            if hasattr(self, 'combo_enabled'):
                self.config['combo_enabled'] = self.state.combo_enabled

            # 儲存血魔監控設定
            if hasattr(self, 'blood_magic_enabled'):
                self.config['blood_magic_enabled'] = self.blood_magic_enabled
            if hasattr(self, 'blood_magic_region') and self.blood_magic_region:
                self.config['blood_magic_region'] = self.blood_magic_region
            if hasattr(self, 'blood_magic_threshold'):
                self.config['blood_magic_threshold'] = self.blood_magic_threshold
            if hasattr(self, 'blood_magic_window_title'):
                self.config['blood_magic_window_title'] = self.blood_magic_window_title

            # 儲存自動清包設定
            if hasattr(self, 'auto_clear_enabled'):
                self.config['auto_clear_enabled'] = self.auto_clear_enabled
            if hasattr(self, 'clear_interval'):
                self.config['clear_interval'] = self.clear_interval
            if hasattr(self, 'inventory_clear_click_mode'):
                self.config['inventory_clear_click_mode'] = self.inventory_tab.inventory_clear_click_mode.get()

            # 儲存取物座標設定
            if hasattr(self, 'pickup_coordinates') and self.pickup_coordinates:
                self.config['pickup_coordinates'] = self.pickup_coordinates

            # 儲存背包視窗標題（區分於血魔監控視窗）
            if hasattr(self, 'inventory_window_var'):
                self.config['inventory_window_title'] = self.inventory_tab.inventory_window_var.get()

            # 儲存監控間隔
            if hasattr(self, 'monitor_interval'):
                self.config['monitor_interval'] = self.state.monitor_interval
            # 儲存檢查頻率設定
            if hasattr(self, 'monitor_interval_var'):
                try:
                    interval_ms = int(self.monitor_tab.monitor_interval_var.get())
                    self.config['monitor_interval'] = interval_ms / 1000.0  # 轉換為秒儲存
                except (ValueError, AttributeError):
                    self.config['monitor_interval'] = 0.1  # 預設100ms

            # 儲存到檔案
            self.config_manager.save_config(self.config)

            self.status_tab.add_status_message("設定檔案儲存成功", "success")
            if show_message:
                messagebox.showinfo("成功", "所有紀錄都已儲存")
        except Exception as e:
            self.status_tab.add_status_message(f"設定檔案儲存失敗 - {str(e)}", "error")
            messagebox.showerror("錯誤", f"儲存失敗: {str(e)}")

    def on_closing(self):
        """應用程式關閉時的處理函數"""
        result = messagebox.askyesno(
            "確認關閉",
            self.get_text("confirm_close_app"),
            default=messagebox.YES
        )

        if not result:
            return

        try:
            self.usage_tracker.track_usage_time()
        except Exception as e:
            print(f"保存使用時間時發生錯誤: {e}")

        # 停止技能計時器
        if hasattr(self, 'skill_timer'):
            self.skill_timer.stop_all()

        self.close_app()

    def show_loading_window(self):
        """顯示工具載入中的提示視窗"""
        try:
            # 創建載入提示視窗
            self.loading_window = tk.Toplevel(self.root)
            self.loading_window.title("載入中")
            self.loading_window.geometry("300x150")
            self.loading_window.resizable(False, False)
            self.loading_window.attributes("-topmost", True)
            self.loading_window.attributes("-alpha", 0.95)

            # 置中於螢幕
            self.loading_window.transient(self.root)
            self.loading_window.grab_set()

            # 將載入窗口置中於螢幕
            self.loading_window.update_idletasks()
            screen_width = self.loading_window.winfo_screenwidth()
            screen_height = self.loading_window.winfo_screenheight()
            window_width = 300
            window_height = 150
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            self.loading_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

            # 創建內容框架
            frame = ttk.Frame(self.loading_window, padding="20")
            frame.pack(fill=tk.BOTH, expand=True)

            # 載入圖標和文字
            loading_label = ttk.Label(frame, text="🔄", font=("Arial", 24))
            loading_label.pack(pady=(0, 10))

            title_label = ttk.Label(frame, text=self.get_text("tool_starting"), font=("Arial", 14, "bold"))
            title_label.pack(pady=(0, 5))

            subtitle_label = ttk.Label(frame, text=self.get_text("please_wait_initializing"), font=("Arial", 10))
            subtitle_label.pack(pady=(0, 10))

            # 進度條
            self.progress_var = tk.DoubleVar()
            progress_bar = ttk.Progressbar(frame, variable=self.progress_var, maximum=100, mode='indeterminate')
            progress_bar.pack(fill=tk.X, pady=(0, 10))
            progress_bar.start(10)  # 開始動畫

            # 狀態文字
            self.loading_status_label = ttk.Label(frame, text=self.get_text("loading_settings"), font=("Arial", 9))
            self.loading_status_label.pack()

            # 強制更新視窗
            self.loading_window.update()

        except Exception as e:
            print(f"創建載入提示視窗失敗: {e}")

    def close_loading_window(self):
        """關閉載入提示視窗"""
        try:
            if hasattr(self, 'loading_window') and self.loading_window:
                self.loading_window.destroy()
                self.loading_window = None
        except Exception as e:
            print(f"關閉載入提示視窗失敗: {e}")

    def update_loading_status(self, status_text):
        """更新載入狀態文字"""
        try:
            if hasattr(self, 'loading_status_label') and self.loading_status_label:
                self.loading_status_label.config(text=status_text)
                self.loading_window.update()
        except Exception as e:
            print(f"更新載入狀態失敗: {e}")

    def add_status_message(self, message, msg_type="info"):
        self.status_tab.add_status_message(message, msg_type)

if __name__ == "__main__":
    def emergency_exit_handler(signum=None, frame=None):
        """緊急退出處理器 - 確保在任何異常情況下都能關閉應用程序"""
        print("\n[STOP] 收到緊急退出信號，正在強制關閉應用程序...")
        try:
            # 嘗試正常關閉
            if 'app' in globals() and hasattr(app, 'close_app'):
                app.close_app()
            elif 'root' in globals() and root:
                root.quit()
                root.destroy()
        except Exception:
            pass
        # 強制退出
        os._exit(1)

    # 設置信號處理器（適用於Unix-like系統）
    try:
        import signal
        signal.signal(signal.SIGTERM, emergency_exit_handler)
        signal.signal(signal.SIGINT, emergency_exit_handler)
    except (ImportError, AttributeError):
        # Windows不支援這些信號，忽略
        pass

    # 設置全局異常處理器
    def global_exception_handler(exc_type, exc_value, exc_traceback):
        """全局異常處理器 - 捕獲所有未處理的異常"""
        import traceback
        print(f"\n[ERROR] 發生未捕獲的異常: {exc_type.__name__}: {exc_value}")
        print("[TRACEBACK]")
        traceback.print_exception(exc_type, exc_value, exc_traceback)

        # 嘗試緊急關閉應用程序
        try:
            emergency_exit_handler()
        except Exception:
            os._exit(1)

    # 安裝全局異常處理器
    import sys
    sys.excepthook = global_exception_handler

    try:
        root = tk.Tk()
        app = HealthMonitor(root)
        root.mainloop()
    except KeyboardInterrupt:
        print("\n[INTERRUPT] 收到鍵盤中斷信號，正在關閉...")
        emergency_exit_handler()
    except Exception as e:
        print(f"\n[FATAL] 主程序發生異常: {e}")
        import traceback
        traceback.print_exc()
        emergency_exit_handler()

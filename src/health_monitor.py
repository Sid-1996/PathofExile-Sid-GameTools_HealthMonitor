import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font as tkfont
import json
import os
import threading
import time
import mss
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
import winreg

# Import new modularized components
from skill_timer import SkillTimerModule
from language_system import get_language_manager, get_text as get_localized_text
from utils import set_app_instance, setup_signal_handlers, setup_exception_handler, format_usage_time, get_app_dir, global_f12_handler
from custom_dialogs import setup_custom_messagebox
from config_manager import get_config_manager

# 版本資訊
CURRENT_VERSION = "v1.0.9"
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

# ========== 自訂對話框類 ==========
class CustomMessageBox:
    """Shared modal dialogs with dynamic sizing for long localized text."""
    result = None

    MIN_WIDTH = 420
    MAX_WIDTH = 760
    MIN_HEIGHT = 180
    MAX_HEIGHT = 560
    MESSAGE_WRAP = 520

    @staticmethod
    def _resolve_parent(parent=None):
        candidate = parent or tk._default_root
        if candidate is None:
            return None

        try:
            if not candidate.winfo_exists():
                return None
            if candidate.state() == 'withdrawn':
                return None
        except Exception:
            return None

        return candidate

    @staticmethod
    def _build_dialog(title, message, buttons, parent=None, accent=None, close_result=False):
        CustomMessageBox.result = None
        parent = CustomMessageBox._resolve_parent(parent)

        window = tk.Toplevel(parent)
        window.title(title or 'Message')
        window.resizable(False, False)
        window.minsize(CustomMessageBox.MIN_WIDTH, CustomMessageBox.MIN_HEIGHT)

        if parent is not None:
            window.transient(parent)
        window.grab_set()

        container = ttk.Frame(window, padding=(20, 18, 20, 14))
        container.pack(fill=tk.BOTH, expand=True)

        message_font = tkfont.nametofont('TkDefaultFont')
        message_widget = tk.Message(
            container,
            text=message or '',
            width=CustomMessageBox.MESSAGE_WRAP,
            justify=tk.LEFT,
            anchor='w',
            font=message_font,
            foreground=accent or 'black',
            padx=0,
            pady=0,
        )
        message_widget.pack(fill=tk.BOTH, expand=True)

        button_frame = ttk.Frame(container)
        button_frame.pack(fill=tk.X, pady=(18, 0))

        focus_button = None
        for button in reversed(buttons):
            btn = ttk.Button(
                button_frame,
                text=button['text'],
                command=lambda value=button['result']: CustomMessageBox._close(window, value),
                width=max(12, len(button['text']) + 2),
            )
            btn.pack(side=tk.RIGHT, padx=(8, 0))
            if button.get('default') and focus_button is None:
                btn.configure(default=tk.ACTIVE)
                focus_button = btn

        if focus_button is not None:
            focus_button.focus_set()

        default_result = next((button['result'] for button in buttons if button.get('default')), True)
        window.bind('<Return>', lambda e: CustomMessageBox._close(window, default_result))
        window.bind('<KP_Enter>', lambda e: CustomMessageBox._close(window, default_result))
        window.bind('<Escape>', lambda e: CustomMessageBox._close(window, close_result))
        window.protocol('WM_DELETE_WINDOW', lambda: CustomMessageBox._close(window, close_result))

        window.update_idletasks()

        width = min(max(container.winfo_reqwidth() + 8, CustomMessageBox.MIN_WIDTH), CustomMessageBox.MAX_WIDTH)
        if width != CustomMessageBox.MIN_WIDTH:
            message_widget.configure(width=max(320, width - 70))
            window.update_idletasks()

        height = min(max(container.winfo_reqheight() + 8, CustomMessageBox.MIN_HEIGHT), CustomMessageBox.MAX_HEIGHT)

        if parent is not None and parent.winfo_exists():
            parent.update_idletasks()
            parent_x = parent.winfo_rootx()
            parent_y = parent.winfo_rooty()
            parent_width = parent.winfo_width()
            parent_height = parent.winfo_height()
            x = parent_x + max(0, (parent_width - width) // 2)
            y = parent_y + max(0, (parent_height - height) // 2)
        else:
            screen_width = window.winfo_screenwidth()
            screen_height = window.winfo_screenheight()
            x = max(0, (screen_width - width) // 2)
            y = max(0, (screen_height - height) // 2)

        window.geometry(f'{width}x{height}+{x}+{y}')
        window.wait_window()
        return CustomMessageBox.result

    @staticmethod
    def show_info(title, message, parent=None):
        CustomMessageBox._build_dialog(
            title,
            message,
            buttons=[{'text': 'OK (Enter)', 'result': True, 'default': True}],
            parent=parent,
            close_result=True,
        )
        return True

    @staticmethod
    def show_warning(title, message, parent=None):
        CustomMessageBox._build_dialog(
            title,
            message,
            buttons=[{'text': 'OK (Enter)', 'result': True, 'default': True}],
            parent=parent,
            accent='#8a6d00',
            close_result=True,
        )
        return True

    @staticmethod
    def show_error(title, message, parent=None):
        CustomMessageBox._build_dialog(
            title,
            message,
            buttons=[{'text': 'OK (Enter)', 'result': True, 'default': True}],
            parent=parent,
            accent='#b00020',
            close_result=True,
        )
        return True

    @staticmethod
    def ask_yes_no(title, message, parent=None):
        return CustomMessageBox._build_dialog(
            title,
            message,
            buttons=[
                {'text': 'No (Esc)', 'result': False},
                {'text': 'Yes (Enter)', 'result': True, 'default': True},
            ],
            parent=parent,
            close_result=False,
        )

    @staticmethod
    def _close(window, result):
        CustomMessageBox.result = result
        window.destroy()


def _custom_messagebox_info(title=None, message=None, **options):
    return CustomMessageBox.show_info(title or 'Info', message or '', parent=options.get('parent'))


def _custom_messagebox_warning(title=None, message=None, **options):
    return CustomMessageBox.show_warning(title or 'Warning', message or '', parent=options.get('parent'))


def _custom_messagebox_error(title=None, message=None, **options):
    return CustomMessageBox.show_error(title or 'Error', message or '', parent=options.get('parent'))


def _custom_messagebox_askyesno(title=None, message=None, **options):
    return CustomMessageBox.ask_yes_no(title or 'Confirm', message or '', parent=options.get('parent'))


messagebox.showinfo = _custom_messagebox_info
messagebox.showwarning = _custom_messagebox_warning
messagebox.showerror = _custom_messagebox_error
messagebox.askyesno = _custom_messagebox_askyesno

class HealthMonitor:
    def get_text(self, key):
        """獲取本地化文字"""
        try:
            # 直接使用語言管理器，避免導入函數的問題
            result = self.language_manager.get_text(key)
            return result
        except Exception as e:
            # print(f"[DEBUG] 主程序 get_text('{key}') 異常: {e}")
            return f"[{key}]"

    def load_usage_time_from_registry(self):
        """從註冊表載入總使用時間"""
        try:
            # 開啟註冊表鍵
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r"Software\SidGameTools\HealthMonitor",
                               0, winreg.KEY_READ)
            # 讀取使用時間值
            value, _ = winreg.QueryValueEx(key, "TotalUsageTime")
            winreg.CloseKey(key)
            return int(value)
        except FileNotFoundError:
            # 如果鍵不存在，返回0
            return 0
        except Exception as e:
            print(f"載入使用時間失敗: {e}")
            return 0

    def save_usage_time_to_registry(self, total_seconds):
        """保存總使用時間到註冊表"""
        try:
            # 創建或開啟註冊表鍵
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\SidGameTools\HealthMonitor")
            # 保存使用時間值
            winreg.SetValueEx(key, "TotalUsageTime", 0, winreg.REG_DWORD, total_seconds)
            winreg.CloseKey(key)
            print(f"已保存總使用時間: {format_usage_time(total_seconds)}")
        except Exception as e:
            print(f"保存使用時間失敗: {e}")

    
    def track_usage_time(self):
        """追蹤並保存使用時間"""
        try:
            # 計算本次使用時間
            end_time = datetime.now()
            session_duration = int((end_time - self.start_time).total_seconds())

            # 累加到總時間
            self.total_usage_time += session_duration

            # 保存到註冊表
            self.save_usage_time_to_registry(self.total_usage_time)

            print(f"本次使用時間: {format_usage_time(session_duration)}")
            print(f"累計總使用時間: {format_usage_time(self.total_usage_time)}")

        except Exception as e:
            print(f"追蹤使用時間失敗: {e}")

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
                    self.start_btn.config(text=self.get_text("start_monitoring"))
                if hasattr(self, 'stop_btn'):
                    self.stop_btn.config(text=self.get_text("stop_monitoring"))
                if hasattr(self, 'save_btn'):
                    self.save_btn.config(text=self.get_text("save_settings"))
                if hasattr(self, 'test_preview_btn'):
                    self.test_preview_btn.config(text=self.get_text("test_preview"))
                if hasattr(self, 'check_freq_label'):
                    self.check_freq_label.config(text=self.get_text("check_frequency"))
                if hasattr(self, 'ms_label'):
                    self.ms_label.config(text=self.get_text("ms"))
                if hasattr(self, 'reminder_frame'):
                    self.reminder_frame.config(text=self.get_text("important_reminder"))
                if hasattr(self, 'reminder_label'):
                    self.reminder_label.config(text=self.get_text("reminder_text"))
                if hasattr(self, 'language_label'):
                    self.language_label.config(text=self.get_text("language"))
                if hasattr(self, 'gui_settings_label'):
                    self.gui_settings_label.config(text=self.get_text("gui_settings"))
                if hasattr(self, 'always_on_top_check'):
                    self.always_on_top_check.config(text=self.get_text("always_on_top"))
                if hasattr(self, 'preview_settings_label'):
                    self.preview_settings_label.config(text=self.get_text("preview_settings"))
                if hasattr(self, 'enable_preview_check'):
                    self.enable_preview_check.config(text=self.get_text("enable_preview"))
                if hasattr(self, 'preview_interval_label'):
                    self.preview_interval_label.config(text=self.get_text("preview_interval"))
                if hasattr(self, 'preview_ms_label'):
                    self.preview_ms_label.config(text=self.get_text("ms"))
            
            # 更新遊戲視窗設定區域
            if hasattr(self, 'window_frame'):
                self.window_frame.config(text=self.get_text("game_window_settings"))
                if hasattr(self, 'region_label'):
                    self.region_label.config(text=self.get_region_text())
                if hasattr(self, 'mana_region_label'):
                    self.mana_region_label.config(text=self.get_mana_region_text())
                if hasattr(self, 'interface_ui_label'):
                    self.interface_ui_label.config(text=self.get_interface_ui_region_text())
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
                self.real_time_status_frame.config(text=self.get_text("real_time_status"))
                if hasattr(self, 'current_health_label'):
                    self.current_health_label.config(text=self.get_text("current_health"))
                if hasattr(self, 'current_mana_label'):
                    self.current_mana_label.config(text=self.get_text("current_mana"))
                if hasattr(self, 'main_color_label'):
                    self.main_color_label.config(text=self.get_text("main_color"))
                if hasattr(self, 'trigger_status_label'):
                    self.trigger_status_label.config(text=self.get_text("trigger_status"))
            
            # 更新預覽區域
            if hasattr(self, 'preview_frame'):
                self.preview_frame.config(text=self.get_text("region_preview"))
                if hasattr(self, 'health_preview_frame'):
                    self.health_preview_frame.config(text=self.get_text("health_preview"))
                if hasattr(self, 'preview_label'):
                    self.preview_label.config(text=self.get_text("select_health_region_first"))
                if hasattr(self, 'mana_preview_frame'):
                    self.mana_preview_frame.config(text=self.get_text("mana_preview"))
                if hasattr(self, 'mana_preview_label'):
                    self.mana_preview_label.config(text=self.get_text("select_mana_region_first"))
            
            # print(f"[DEBUG] update_ui_text() 完成")
            
        except Exception as e:
            pass

    def update_ui_language(self):
        """更新UI語言（保持向後相容）"""
        self.update_ui_text()

    def update_status_tab_language(self):
        """更新狀態分頁的語言"""
        try:
            # 更新狀態分頁的標籤和按鈕
            if hasattr(self, 'status_count_label'):
                count = len(getattr(self, 'status_log', []))
                self.status_count_label.config(text=self.get_text("total_records").format(count=count))
            
            if hasattr(self, 'clear_records_btn'):
                self.clear_records_btn.config(text=self.get_text("clear_records"))
                
            if hasattr(self, 'auto_scroll_var') and hasattr(self, 'auto_scroll_check'):
                self.auto_scroll_check.config(text=self.get_text("auto_scroll_to_latest"))
                
        except Exception as e:
            print(f"更新狀態分頁語言時發生錯誤: {e}")

    def update_help_tab_language(self):
        """更新幫助分頁的語言"""
        try:
            # 重新創建幫助分頁內容以應用新語言
            if hasattr(self, 'help_frame'):
                # 清除現有內容
                for widget in self.help_frame.winfo_children():
                    widget.destroy()

                # 重新創建幫助分頁
                self.create_help_tab()
        except Exception as e:
            print(f"更新幫助分頁語言時發生錯誤: {e}")

    def update_version_tab_language(self):
        """更新版本分頁的語言"""
        try:
            # 重新創建版本分頁內容以應用新語言
            if hasattr(self, 'version_frame'):
                # 清除現有內容
                for widget in self.version_frame.winfo_children():
                    widget.destroy()

                # 重新創建版本分頁
                self.create_version_tab()
        except Exception as e:
            print(f"更新版本分頁語言時發生錯誤: {e}")

    def update_about_tab_language(self):
        """更新關於分頁的語言"""
        try:
            # 重新創建關於分頁內容以應用新語言
            if hasattr(self, 'about_frame'):
                # 清除現有內容
                for widget in self.about_frame.winfo_children():
                    widget.destroy()

                # 重新創建關於分頁
                self.create_about_tab()
        except Exception as e:
            print(f"更新關於分頁語言時發生錯誤: {e}")

    def update_inventory_tab_language(self):
        """更新一鍵清包分頁的語言"""
        try:
            # 更新LabelFrame標題
            if hasattr(self, 'inventory_frame'):
                for child in self.inventory_frame.winfo_children():
                    if isinstance(child, ttk.LabelFrame):
                        text = child.cget('text')
                        if text == "背包設定" or text == "Inventory Settings":
                            child.config(text=self.get_text("inventory_settings"))
                        elif text == "控制面板" or text == "Control Panel":
                            child.config(text=self.get_text("control_panel"))
                        elif text == "狀態" or text == "Status":
                            child.config(text=self.get_text("status"))
                        elif text == "F6取物座標" or text == "F6 Pickup Coordinates":
                            child.config(text=self.get_text("pickup_coordinates"))
                        elif text == "背包UI截圖" or text == "Inventory UI Screenshot":
                            child.config(text=self.get_text("inventory_ui_screenshot"))
                        elif text == "背包預覽" or text == "Inventory Preview":
                            child.config(text=self.get_text("inventory_preview"))
            
            # 更新按鈕文字
            if hasattr(self, 'select_inventory_region_btn'):
                self.select_inventory_region_btn.config(text=self.get_text("select_inventory_region"))
            if hasattr(self, 'record_empty_color_btn'):
                self.record_empty_color_btn.config(text=self.get_text("record_empty_color"))
            if hasattr(self, 'select_inventory_ui_btn'):
                self.select_inventory_ui_btn.config(text=self.get_text("select_inventory_ui"))
            if hasattr(self, 'test_clear_inventory_btn'):
                self.test_clear_inventory_btn.config(text=self.get_text("test_clear_inventory"))
            if hasattr(self, 'save_inventory_settings_btn'):
                self.save_inventory_settings_btn.config(text=self.get_text("save_inventory_settings"))
            if hasattr(self, 'setup_pickup_coordinates_btn'):
                self.setup_pickup_coordinates_btn.config(text=self.get_text("setup_pickup_coordinates"))
            if hasattr(self, 'save_pickup_coordinates_btn'):
                self.save_pickup_coordinates_btn.config(text=self.get_text("save_coordinates"))
            
            # 更新標籤文字
            if hasattr(self, 'record_status_label'):
                self.record_status_label.config(text=self.get_text("record_status"))
            if hasattr(self, 'inventory_ui_status_label'):
                self.inventory_ui_status_label.config(text=self.get_text("inventory_ui_status"))
            if hasattr(self, 'inventory_f3_label'):
                self.inventory_f3_label.config(text=self.get_text("f3_hotkey"))
            if hasattr(self, 'pause_status_label_title'):
                self.pause_status_label_title.config(text=self.get_text("global_pause"))
            if hasattr(self, 'coordinates_set_label'):
                self.coordinates_set_label.config(text=self.get_text("coordinates_set"))
            if hasattr(self, 'pickup_f6_label'):
                self.pickup_f6_label.config(text=self.get_text("f6_hotkey"))
            if hasattr(self, 'occupied_label_title'):
                self.occupied_label_title.config(text=self.get_text("occupied_slots"))
            if hasattr(self, 'grid_adjustment_label'):
                self.grid_adjustment_label.config(text=self.get_text("grid_alignment_adjustment"))
            if hasattr(self, 'horizontal_label'):
                self.horizontal_label.config(text=self.get_text("horizontal"))
            if hasattr(self, 'vertical_label'):
                self.vertical_label.config(text=self.get_text("vertical"))
            
            # 更新重置按鈕
            if hasattr(self, 'reset_offset_btn'):
                self.reset_offset_btn.config(text=self.get_text("reset"))
            
            # 更新說明文字
            if hasattr(self, 'ui_preview_hint_label'):
                self.ui_preview_hint_label.config(text=self.get_text("inventory_ui_screenshot_hint"))
            
            # 更新預覽標籤的初始文字
            if hasattr(self, 'inventory_preview_label') and not getattr(self, '_preview_has_image', False):
                self.inventory_preview_label.itemconfig(self._preview_placeholder, text=self.get_text("select_inventory_region_first"))
            
            # 更新舊的按鈕引用（向後相容）
            if hasattr(self, 'inventory_clear_btn'):
                self.inventory_clear_btn.config(text=self.get_text("clear_inventory"))
            if hasattr(self, 'pickup_items_btn'):
                self.pickup_items_btn.config(text=self.get_text("pickup_items"))
                
        except Exception as e:
            print(f"更新一鍵清包分頁語言時發生錯誤: {e}")

    def update_combo_tab_language(self):
        """更新技能連段分頁的語言"""
        try:
            # 更新技能計時器按鈕文字
            if hasattr(self, 'skill_timer'):
                self.skill_timer.refresh_language()
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
        
        # 初始設定為中等大小的視窗
        self.root.geometry("800x600")
        self.root.minsize(650, 500)    
        self.root.attributes("-alpha", 1.0)  

        # 記錄應用程式啟動時間
        self.start_time = datetime.now()
        print(f"{self.get_text('app_start_time')} {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # 初始化使用時間追蹤
        self.total_usage_time = self.load_usage_time_from_registry()
        print(f"載入總使用時間: {format_usage_time(self.total_usage_time)}")

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
        self._is_closing = False
        self._silent_version_check_after_id = None
        self._usage_time_after_id = None
        self.language_display_map = self.language_manager.get_language_display_map()
        self.language_reverse_map = self.language_manager.get_language_reverse_map()
        
        # 設置語言變數為顯示名稱
        display_name = self.language_manager.get_current_display_name()
        self.language_var = tk.StringVar(value=display_name)

        # 創建載入提示視窗（在語言設定之後）
        self.show_loading_window()

        # GUI最上方設定變數
        self.always_on_top_var = tk.BooleanVar(value=False)  # 預設不在最上方，避免影響彈出視窗操作

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
        self.excluded_inventory_slots = set()  # 被排除的格子索引（清包時跳過）

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

        # ========== 線程同步機制 ==========
        # 使用 RLock 允許同一線程多次獲取鎖
        self.monitoring_lock = threading.RLock()  # 監控狀態的鎖
        self.combo_lock = threading.RLock()  # 連段狀態的鎖
        self.global_pause_lock = threading.RLock()  # 全域暫停狀態的鎖

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

        # 預覽控制變數
        self.preview_enabled = tk.BooleanVar(value=True)
        self.preview_interval_var = tk.StringVar(value="250")

        # 執行狀態記錄相關變數
        self.status_log = []  # 儲存狀態訊息
        self.status_log_max_lines = 100  # 最大記錄行數
        self.last_status_message = ""  # 記錄上一條訊息，避免重複
        self.status_text_widget = None  # 狀態顯示文字區域

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

        # 監控狀態
        self.monitoring = False
        self.monitor_thread = None

        # ??GUI????
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
            # print(f"[DEBUG] update_ui_text() 完成")
            
            self.auto_load_preview()
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

        self.add_status_message(self.get_text("tool_started_successfully"), "success")
        self.add_status_message(self.get_text("hotkey_info"), "info")
        self._usage_time_after_id = self.root.after(60000, self.update_usage_time_periodically)

    def refresh_visual_previews_after_load(self):
        """Refresh heavier previews after startup so the main window appears sooner."""
        if hasattr(self, 'ui_preview_canvas') and self.inventory_ui_region:
            self.update_ui_preview()

        if hasattr(self, 'interface_ui_preview_canvas') and self.interface_ui_region:
            self.update_interface_ui_preview()

        if self.inventory_region:
            self.update_inventory_preview_from_current()

    def setup_mouse_interrupt(self):
        """設置滑鼠右鍵中斷功能"""
        # 啟動背景線程監聽右鍵事件
        self.mouse_interrupt_thread = threading.Thread(target=self.monitor_mouse_interrupt, daemon=True)
        self.mouse_interrupt_thread.start()

    def monitor_mouse_interrupt(self):
        """監聽滑鼠右鍵事件用於中斷F3清包"""
        if self._is_closing:
            return
        self.add_status_message(self.get_text("mouse_interrupt_started"), "info")
        print(self.get_text("mouse_interrupt_started"))

        right_click_start = None
        interrupt_threshold = 2.0  # 2秒閾值
        last_right_button_state = False  # 記錄上一次的右鍵狀態

        while not self._is_closing:
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
                            self.inventory_clear_interrupt = True
                        right_click_start = None

                last_right_button_state = current_right_button_state
                time.sleep(0.1)  # 每100ms檢查一次

            except Exception as e:
                if self._is_closing:
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
                        break
        except Exception as e:
            print(f"{self.get_text('restore_tab_error')} {e}")

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
        window_frame = ttk.LabelFrame(left_frame, text=self.get_text("game_window_settings"), padding="10")
        window_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(window_frame, text=self.get_text("game_window")).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.window_var = tk.StringVar(value='')
        self.window_combo = ttk.Combobox(window_frame, textvariable=self.window_var, width=35)
        self.window_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        ttk.Button(window_frame, text=self.get_text("refresh"), command=self.refresh_windows).grid(row=0, column=2, padx=(5, 0))

        ttk.Label(window_frame, text=self.get_text("health_bar_region")).grid(row=1, column=0, sticky=tk.W, pady=2)
        self.region_label = ttk.Label(window_frame, text=self.get_region_text(), background="lightgray", relief="sunken", padding=2)
        self.region_label.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))

        ttk.Label(window_frame, text=self.get_text("mana_bar_region")).grid(row=2, column=0, sticky=tk.W, pady=2)
        self.mana_region_label = ttk.Label(window_frame, text=self.get_mana_region_text(), background="lightgray", relief="sunken", padding=2)
        self.mana_region_label.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))

        ttk.Label(window_frame, text=self.get_text("interface_ui_region")).grid(row=3, column=0, sticky=tk.W, pady=2)
        self.interface_ui_label = ttk.Label(window_frame, text=self.get_interface_ui_region_text(), background="lightgray", relief="sunken", padding=2)
        self.interface_ui_label.grid(row=3, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))

        ttk.Button(window_frame, text=self.get_text("select_health_region"), command=self.start_selection).grid(row=4, column=0, pady=(5, 0))
        ttk.Button(window_frame, text=self.get_text("select_mana_region"), command=self.start_mana_selection).grid(row=4, column=1, pady=(5, 0), padx=(5, 0))
        ttk.Button(window_frame, text=self.get_text("select_interface_ui"), command=self.select_interface_ui_region).grid(row=4, column=2, pady=(5, 0), padx=(5, 0))

        # 設定列寬
        window_frame.columnconfigure(1, weight=1)

        # 觸發設定區域
        settings_frame = ttk.LabelFrame(left_frame, text=self.get_text("trigger_settings"), padding="10")
        settings_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # 新增設定區域
        add_frame = ttk.Frame(settings_frame)
        add_frame.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(add_frame, text=self.get_text("type")).grid(row=0, column=0, sticky=tk.W)
        self.type_var = tk.StringVar(value="HP")
        type_combo = ttk.Combobox(add_frame, textvariable=self.type_var, 
                                 values=["HP", "MP"], state="readonly", width=8)
        type_combo.grid(row=0, column=1, padx=(5, 0))
        type_combo.bind("<<ComboboxSelected>>", self.on_type_changed)

        ttk.Label(add_frame, text=self.get_text("percentage")).grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        self.percent_var = tk.StringVar(value="60")
        ttk.Entry(add_frame, textvariable=self.percent_var, width=8).grid(row=0, column=3, padx=(5, 0))

        ttk.Label(add_frame, text=self.get_text("hotkey")).grid(row=0, column=4, sticky=tk.W, padx=(10, 0))
        self.key_var = tk.StringVar(value="1")
        ttk.Entry(add_frame, textvariable=self.key_var, width=12).grid(row=0, column=5, padx=(5, 0))

        ttk.Label(add_frame, text=self.get_text("cooldown_ms")).grid(row=0, column=6, sticky=tk.W, padx=(10, 0))
        self.cooldown_var = tk.StringVar(value="1500")
        ttk.Entry(add_frame, textvariable=self.cooldown_var, width=8).grid(row=0, column=7, padx=(5, 0))

        ttk.Button(add_frame, text=self.get_text("add_trigger"), command=self.add_setting_new).grid(row=0, column=8, padx=(10, 0))

        # 觸發選項區域
        options_frame = ttk.Frame(settings_frame)
        options_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))

        ttk.Button(options_frame, text=self.get_text("remove_selected"), command=self.remove_setting).grid(row=0, column=0, padx=(0, 0))
        ttk.Button(options_frame, text=self.get_text("adjust_colors"), command=self.adjust_colors).grid(row=0, column=1, padx=(20, 0))
        ttk.Button(options_frame, text=self.get_text("adjust_interface_ui"), command=self.adjust_interface_ui_thresholds).grid(row=0, column=2, padx=(10, 0))

        # 多重觸發選項
        self.multi_trigger_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text=self.get_text("multiple_triggers"),
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
        self.settings_tree.heading("type", text=self.get_text("type"))
        self.settings_tree.heading("percent", text=self.get_text("percentage"))
        self.settings_tree.heading("key", text=self.get_text("hotkey"))
        self.settings_tree.heading("cooldown", text=self.get_text("cooldown_ms"))
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
        self.control_frame = ttk.LabelFrame(left_frame, text=self.get_text("control_panel"), padding="10")
        self.control_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        self.start_btn = ttk.Button(self.control_frame, text=self.get_text("start_monitoring"), command=self.start_monitoring)
        self.start_btn.grid(row=0, column=0, padx=(0, 5))

        self.stop_btn = ttk.Button(self.control_frame, text=self.get_text("stop_monitoring"), command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=1, padx=(0, 5))

        self.save_btn = ttk.Button(self.control_frame, text=self.get_text("save_settings"), command=self.save_config)
        self.save_btn.grid(row=0, column=2)

        self.test_preview_btn = ttk.Button(self.control_frame, text=self.get_text("test_preview"), command=self.test_preview)
        self.test_preview_btn.grid(row=0, column=3, padx=(5, 0))

        # 檢查頻率設定
        self.check_freq_label = ttk.Label(self.control_frame, text=self.get_text("check_frequency"))
        self.check_freq_label.grid(row=1, column=0, sticky=tk.W, pady=(15, 0))
        self.monitor_interval_var = tk.StringVar(value=str(int(self.monitor_interval * 1000)))  # 根據初始化值設定
        interval_combo = ttk.Combobox(self.control_frame, textvariable=self.monitor_interval_var,
                                     values=["25", "50", "100"], state="readonly", width=8)
        interval_combo.grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=(15, 0))
        self.ms_label = ttk.Label(self.control_frame, text=self.get_text("ms"))
        self.ms_label.grid(row=1, column=2, sticky=tk.W, pady=(15, 0))

        # 重要提醒區域
        self.reminder_frame = ttk.LabelFrame(self.control_frame, text=self.get_text("important_reminder"), padding="8")
        self.reminder_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(20, 5))

        reminder_text = self.get_text("reminder_text")

        self.reminder_label = ttk.Label(self.reminder_frame, text=reminder_text,
                                  font=("Arial", 9), foreground="red",
                                  justify=tk.LEFT, wraplength=400)
        self.reminder_label.grid(row=0, column=0, sticky=(tk.W, tk.E))

        # 語言選擇
        language_text = self.get_text("language")
        self.language_label = ttk.Label(self.control_frame, text=language_text)
        self.language_label.grid(row=4, column=0, sticky=tk.W, pady=(10, 0))
        # print(f"[DEBUG] 語言標籤文字: '{language_text}'")
        
        # 語言顯示名稱映射
        self.language_display_map = {
            "繁體中文": "zh-tw",
            "English": "en"
        }
        self.language_reverse_map = {v: k for k, v in self.language_display_map.items()}

        # 設置下拉選單的顯示值
        display_values = list(self.language_display_map.keys())
        current_display = self.language_reverse_map.get(self.current_language, "繁體中文")
        self.language_var.set(current_display)
        # print(f"[DEBUG] 語言選擇器當前顯示: '{current_display}'")
        # print(f"[DEBUG] 可用語言選項: {display_values}")
        
        language_combo = ttk.Combobox(self.control_frame, textvariable=self.language_var,
                                     values=display_values, state="readonly", width=12)
        language_combo.grid(row=4, column=1, sticky=tk.W, padx=(5, 0), pady=(10, 0))
        language_combo.bind("<<ComboboxSelected>>", lambda e: self.change_language_display(self.language_var.get()))

        # GUI最上方設定選項
        gui_control_frame = ttk.Frame(self.control_frame)
        gui_control_frame.grid(row=5, column=0, columnspan=3, pady=(10, 0))

        self.gui_settings_label = ttk.Label(gui_control_frame, text=self.get_text("gui_settings"))
        self.gui_settings_label.grid(row=0, column=0, sticky=tk.W)
        self.always_on_top_check = ttk.Checkbutton(gui_control_frame, text=self.get_text("always_on_top"), variable=self.always_on_top_var, 
                       command=self.toggle_always_on_top)
        self.always_on_top_check.grid(row=0, column=1, columnspan=2, sticky=tk.W, padx=(5, 0))

        # 預覽控制選項
        self.preview_control_frame = ttk.Frame(self.control_frame)
        self.preview_control_frame.grid(row=6, column=0, columnspan=3, pady=(10, 0))

        self.preview_settings_label = ttk.Label(self.preview_control_frame, text=self.get_text("preview_settings"))
        self.preview_settings_label.grid(row=0, column=0, sticky=tk.W)
        self.enable_preview_check = ttk.Checkbutton(self.preview_control_frame, text=self.get_text("enable_preview"), variable=self.preview_enabled)
        self.enable_preview_check.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))

        self.preview_interval_label = ttk.Label(self.preview_control_frame, text=self.get_text("preview_interval"))
        self.preview_interval_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        ttk.Entry(self.preview_control_frame, textvariable=self.preview_interval_var, width=8).grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=(5, 0))
        self.preview_ms_label = ttk.Label(self.preview_control_frame, text=self.get_text("ms"))
        self.preview_ms_label.grid(row=1, column=2, sticky=tk.W, pady=(5, 0))

        # 即時狀態區域
        self.real_time_status_frame = ttk.LabelFrame(right_frame, text=self.get_text("real_time_status"), padding="10")
        self.real_time_status_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # 狀態資訊
        self.current_health_label = ttk.Label(self.real_time_status_frame, text=self.get_text("current_health"), font=("Arial", 10, "bold"))
        self.current_health_label.grid(row=0, column=0, sticky=tk.W, pady=2)
        self.health_label = ttk.Label(self.real_time_status_frame, text="--", font=("Arial", 12, "bold"), foreground="red", width=8, anchor="w")
        self.health_label.grid(row=0, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        self.current_mana_label = ttk.Label(self.real_time_status_frame, text=self.get_text("current_mana"), font=("Arial", 10, "bold"))
        self.current_mana_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        self.mana_label = ttk.Label(self.real_time_status_frame, text="--", font=("Arial", 12, "bold"), foreground="blue", width=8, anchor="w")
        self.mana_label.grid(row=1, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        self.main_color_label = ttk.Label(self.real_time_status_frame, text=self.get_text("main_color"))
        self.main_color_label.grid(row=2, column=0, sticky=tk.W, pady=2)
        self.color_label = ttk.Label(self.real_time_status_frame, text="--", width=20, anchor="w")
        self.color_label.grid(row=2, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        self.trigger_status_label = ttk.Label(self.real_time_status_frame, text=self.get_text("trigger_status"))
        self.trigger_status_label.grid(row=3, column=0, sticky=tk.W, pady=2)
        self.trigger_label = ttk.Label(self.real_time_status_frame, text="--", width=35, anchor="w")
        self.trigger_label.grid(row=3, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        # 區域預覽
        self.preview_frame = ttk.LabelFrame(right_frame, text=self.get_text("region_preview"), padding="10")
        self.preview_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 創建預覽區域的左右分欄
        self.health_preview_frame = ttk.LabelFrame(self.preview_frame, text=self.get_text("health_preview"), padding="5")
        self.health_preview_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))

        self.preview_label = ttk.Label(self.health_preview_frame, text=self.get_text("select_health_region_first"), relief="sunken", background="lightgray", width=45, anchor="center")
        self.preview_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.mana_preview_frame = ttk.LabelFrame(self.preview_frame, text=self.get_text("mana_preview"), padding="5")
        self.mana_preview_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))

        self.mana_preview_label = ttk.Label(self.mana_preview_frame, text=self.get_text("select_mana_region_first"), relief="sunken", background="lightblue", width=45, anchor="center")
        self.mana_preview_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 設定預覽區域大小
        self.preview_frame.columnconfigure(0, weight=1)
        self.preview_frame.columnconfigure(1, weight=1)
        self.preview_frame.rowconfigure(0, weight=1)
        self.health_preview_frame.columnconfigure(0, weight=1)
        self.health_preview_frame.rowconfigure(0, weight=1)
        self.mana_preview_frame.columnconfigure(0, weight=1)
        self.mana_preview_frame.rowconfigure(0, weight=1)

        # 介面UI預覽區域
        interface_ui_preview_frame = ttk.LabelFrame(right_frame, text=self.get_text("interface_ui_preview"), padding="5")
        interface_ui_preview_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        # 創建一個Canvas來顯示介面UI截圖 (縮小尺寸)
        self.interface_ui_preview_canvas = tk.Canvas(interface_ui_preview_frame, width=150, height=100, bg='lightgray', relief='sunken')
        self.interface_ui_preview_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E))

        # 添加說明文字
        ttk.Label(interface_ui_preview_frame, text=self.get_text("interface_ui_preview_hint"),
                 font=("", 7), foreground="gray").grid(row=1, column=0, sticky=tk.W, pady=(3, 0))

        right_frame.rowconfigure(1, weight=1)

        # 設定預覽標籤的固定尺寸以保持一致性
        self.preview_size = (380, 280)  # 更大的預覽尺寸 (寬度, 高度)
        
        # 為預覽框架設定更大的最小高度
        self.health_preview_frame.config(height=300)
        self.mana_preview_frame.config(height=300)

        # 初始化視窗列表
        self.refresh_windows()

        # 初始化變數
        self.last_preview_update = 0
        self.preview_update_interval = 500  # 500ms更新一次預覽圖片
        self.last_health_percent = -1
        self.last_mana_percent = -1
        self.last_mana_preview_update = 0
        self._preview_placeholder_shown = False

    def on_type_changed(self, event=None):
        """當類型選擇改變時更新預設值"""
        if self.type_var.get() == "HP":
            self.percent_var.set("60")
            self.key_var.set("1")
        else:  # MP
            self.percent_var.set("10")
            self.key_var.set("2")

    def test_preview(self):
        """手動測試預覽功能"""
        if not self.window_var.get():
            messagebox.showerror(self.get_text("error"), self.get_text("select_game_window_first"))
            return

        # 檢查遊戲視窗是否最小化
        if self.check_game_window_minimized(self.window_var.get()):
            return

        try:
            # 獲取遊戲視窗
            windows = gw.getWindowsWithTitle(self.window_var.get())
            if not windows:
                CustomMessageBox.show_error(self.get_text("error"), self.get_text("game_window_not_found_with_title").format(window_title=self.window_var.get()), self.root)
                return

            window = windows[0]

            # 先隱藏主介面，避免遮擋遊戲視窗
            self.root.iconify()

            def _perform_preview_test():
                success_count = 0
                error_messages = []

                try:
                    window.activate()
                    # 給遊戲視窗時間激活，但避免長時間阻塞 UI
                    time.sleep(0.2)

                    if self.config.get('region'):
                        try:
                            self.capture_preview_async()
                            success_count += 1
                            print(self.get_text("health_preview_test_complete"))
                        except Exception as e:
                            error_messages.append(f"{self.get_text('health_preview_test_failed')} {e}")

                    if self.config.get('mana_region'):
                        try:
                            self.capture_mana_preview_async()
                            success_count += 1
                            print(self.get_text("mana_preview_test_complete"))
                        except Exception as e:
                            error_messages.append(f"魔力預覽測試失敗: {e}")

                except Exception as e:
                    error_messages.append(self.get_text("preview_test_failed").format(error=str(e)))

                finally:
                    self.root.after(0, self.root.deiconify)

                    def _show_result():
                        if success_count > 0:
                            CustomMessageBox.show_info(self.get_text("settings_applied"), self.get_text("preview_test_completed").format(success_count=success_count), self.root)
                        else:
                            CustomMessageBox.show_warning(self.get_text("important_reminder"), self.get_text("no_testable_regions"), self.root)

                        for msg in error_messages:
                            print(msg)

                    self.root.after(0, _show_result)

            thread = threading.Thread(target=_perform_preview_test, daemon=True)
            thread.start()

        except Exception as e:
            CustomMessageBox.show_error(self.get_text("error"), self.get_text("preview_test_failed").format(error=str(e)), self.root)

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
        title_label = ttk.Label(main_frame, text=self.get_text("tool_execution_status"), font=("Microsoft YaHei", 20, "bold"))
        title_label.pack(pady=(15, 35))
        
        # 控制按鈕框架
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill="x", pady=(0, 15))
        
        # 清除記錄按鈕
        clear_btn = ttk.Button(control_frame, text=self.get_text("clear_records"), command=self.clear_status_log)
        clear_btn.pack(side="left", padx=(0, 10))
        
        # 自動滾動開關
        self.auto_scroll_var = tk.BooleanVar(value=True)
        auto_scroll_cb = ttk.Checkbutton(control_frame, text=self.get_text("auto_scroll_to_latest"), variable=self.auto_scroll_var)
        auto_scroll_cb.pack(side="left", padx=(0, 10))
        
        # 狀態統計標籤
        self.status_count_label = ttk.Label(control_frame, text=self.get_text("total_records"))
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
        self.add_status_message(self.get_text("tool_started_successfully"), "success")

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
        if self._is_closing:
            return

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
            try:
                if self.status_text_widget and self.status_text_widget.winfo_exists():
                    self.refresh_status_display()
                    return
            except (RuntimeError, tk.TclError):
                return
        
        # 如果文字區域存在，添加新訊息
        try:
            widget_exists = bool(self.status_text_widget and self.status_text_widget.winfo_exists())
        except (RuntimeError, tk.TclError):
            return

        if widget_exists:
            try:
                self.status_text_widget.config(state=tk.NORMAL)
                self.status_text_widget.insert(tk.END, formatted_message, msg_type)
                self.status_text_widget.config(state=tk.DISABLED)
            except (RuntimeError, tk.TclError):
                return
            
            # 自動滾動到底部
            try:
                if self.auto_scroll_var.get():
                    self.status_text_widget.see(tk.END)
            except (RuntimeError, tk.TclError):
                return
            
            # 更新統計
            try:
                self.update_status_count()
            except (RuntimeError, tk.TclError):
                return

    def schedule_ui_callback(self, callback, delay=0):
        if self._is_closing:
            return None

        try:
            if not self.root.winfo_exists():
                return None
        except (RuntimeError, tk.TclError):
            return None

        def guarded_callback():
            if self._is_closing:
                return

            try:
                if not self.root.winfo_exists():
                    return
            except (RuntimeError, tk.TclError):
                return

            try:
                callback()
            except (RuntimeError, tk.TclError):
                return

        try:
            return self.root.after(delay, guarded_callback)
        except (RuntimeError, tk.TclError):
            return None

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
        self.add_status_message(self.get_text("records_cleared"), "info")

    def update_status_count(self):
        """更新狀態記錄數量顯示"""
        if self.status_count_label:
            count = len(self.status_log)
            self.status_count_label.config(text=self.get_text("total_records").format(count=count))

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

        title_label = ttk.Label(header_frame, text=self.get_text("poe_sid_tools_title"),
                               font=("Microsoft YaHei", 24, "bold"), foreground='#2c3e50')
        title_label.pack(pady=(10, 5))

        subtitle_label = ttk.Label(header_frame, text=self.get_text("opensource_subtitle"),
                                  font=("Microsoft YaHei", 12), foreground='#7f8c8d')
        subtitle_label.pack(pady=(0, 10))

        # 影片連結按鈕
        video_frame = ttk.Frame(header_frame)
        video_frame.pack(pady=(0, 10))

        video_button = ttk.Button(video_frame, text=self.get_text("watch_demo_video"),
                                 command=lambda: self.open_video_link("https://dai.ly/xa9cau2"))
        video_button.pack()

        video_note_label = ttk.Label(video_frame, text=self.get_text("video_recommendation"),
                                    font=("Microsoft YaHei", 9), foreground='#e74c3c')
        video_note_label.pack(pady=(5, 0))

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
        hotkey_card = self.create_info_card(content_frame, self.get_text("global_hotkeys_title"), [
            ("F3", self.get_text("hotkey_f3_desc"), "#e74c3c"),
            ("F5", self.get_text("hotkey_f5_desc"), "#3498db"),
            ("F6", self.get_text("hotkey_f6_desc"), "#2ecc71"),
            ("F9", self.get_text("hotkey_f9_desc"), "#f39c12"),
            ("F10", self.get_text("hotkey_f10_desc"), "#9b59b6"),
            ("F12", self.get_text("hotkey_f12_desc"), "#95a5a6"),
            ("CTRL+Click", self.get_text("hotkey_ctrl_click_desc"), "#1abc9c")
        ])
        hotkey_card.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10), pady=(0, 10))

        # 版本資訊卡片
        version_card = ttk.LabelFrame(content_frame, text=self.get_text("version_info"), padding="15")
        version_card.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10), pady=(0, 10))

        version_info = self.get_text("version_info_text").format(version=CURRENT_VERSION)
        ttk.Label(version_card, text=version_info, justify="left",
                 font=('Microsoft YaHei', 10)).pack(anchor="w")

        # 快速開始卡片
        quickstart_card = ttk.LabelFrame(content_frame, text=self.get_text("quick_start"), padding="15")
        quickstart_card.grid(row=0, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 0), pady=(0, 10))

        quickstart_text = self.get_text("quickstart_text")
        ttk.Label(quickstart_card, text=quickstart_text, justify="left",
                 font=('Microsoft YaHei', 10)).pack(anchor="w")

        # === 第二行：功能詳細說明 ===
        # 核心功能卡片
        features_card = ttk.LabelFrame(content_frame, text=self.get_text("core_features"), padding="15")
        features_card.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10), pady=(0, 10))

        # 使用子框架來組織功能說明
        features_container = ttk.Frame(features_card)
        features_container.pack(fill="both", expand=True)

        # 左側功能
        left_features = ttk.Frame(features_container)
        left_features.pack(side="left", fill="both", expand=True, padx=(0, 15))

        ttk.Label(left_features, text=self.get_text("health_monitor_system"), font=('Microsoft YaHei', 12, 'bold'),
                 foreground='#e74c3c').pack(anchor="w", pady=(0, 5))
        ttk.Label(left_features, text=self.get_text("health_monitor_desc"),
                 font=('Microsoft YaHei', 9), justify="left").pack(anchor="w", pady=(0, 15))

        ttk.Label(left_features, text=self.get_text("smart_inventory_system"), font=('Microsoft YaHei', 12, 'bold'),
                 foreground='#3498db').pack(anchor="w", pady=(0, 5))
        ttk.Label(left_features, text=self.get_text("smart_inventory_desc"),
                 font=('Microsoft YaHei', 9), justify="left").pack(anchor="w", pady=(0, 15))

        # 右側功能
        right_features = ttk.Frame(features_container)
        right_features.pack(side="right", fill="both", expand=True, padx=(15, 0))

        ttk.Label(right_features, text=self.get_text("skill_combo_system"), font=('Microsoft YaHei', 12, 'bold'),
                 foreground='#2ecc71').pack(anchor="w", pady=(0, 5))
        ttk.Label(right_features, text=self.get_text("skill_combo_desc"),
                 font=('Microsoft YaHei', 9), justify="left").pack(anchor="w", pady=(0, 15))

        ttk.Label(right_features, text=self.get_text("automation_tools"), font=('Microsoft YaHei', 12, 'bold'),
                 foreground='#9b59b6').pack(anchor="w", pady=(0, 5))
        ttk.Label(right_features, text=self.get_text("automation_tools_desc"),
                 font=('Microsoft YaHei', 9), justify="left").pack(anchor="w")

        # 設定指南卡片
        setup_card = ttk.LabelFrame(content_frame, text=self.get_text("detailed_setup_guide"), padding="15")
        setup_card.grid(row=1, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 0), pady=(0, 10))

        setup_guide = self.get_text("setup_guide_text")
        ttk.Label(setup_card, text=setup_guide, justify="left",
                 font=('Microsoft YaHei', 9)).pack(anchor="w")

        # === 第三行：注意事項和開源資訊 ===
        # 注意事項卡片
        notes_card = ttk.LabelFrame(scrollable_frame, text=self.get_text("important_notes"), padding="15")
        notes_card.pack(fill="x", padx=20, pady=(0, 10))

        notes_text = self.get_text("notes_text")
        ttk.Label(notes_card, text=notes_text, justify="left",
                 font=('Microsoft YaHei', 10)).pack(anchor="w")

        # 開源資訊卡片
        opensource_card = ttk.LabelFrame(scrollable_frame, text=self.get_text("opensource_info"), padding="15")
        opensource_card.pack(fill="x", padx=20, pady=(0, 20))

        # 開源資訊使用網格佈局
        opensource_container = ttk.Frame(opensource_card)
        opensource_container.pack(fill="x")

        opensource_container.columnconfigure(0, weight=1)
        opensource_container.columnconfigure(1, weight=1)

        # 左側：專案資訊
        left_info = ttk.Frame(opensource_container)
        left_info.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 20))

        ttk.Label(left_info, text=self.get_text("github_repo_label"), font=('Microsoft YaHei', 11, 'bold')).pack(anchor="w")
        ttk.Label(left_info, text="https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor",
                 font=('Consolas', 9), foreground='#3498db').pack(anchor="w", pady=(0, 5))

        # GitHub倉庫訪問按鈕
        github_button = ttk.Button(left_info, text=self.get_text("visit_github_button"),
                                  command=lambda: self.open_video_link("https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor"))
        github_button.pack(anchor="w", pady=(0, 10))

        ttk.Label(left_info, text=self.get_text("license_label"), font=('Microsoft YaHei', 11, 'bold')).pack(anchor="w")
        ttk.Label(left_info, text=self.get_text("license_text"), font=('Microsoft YaHei', 10)).pack(anchor="w", pady=(0, 10))

        # 右側：功能狀態
        right_info = ttk.Frame(opensource_container)
        right_info.grid(row=0, column=1, sticky=(tk.W, tk.E))

        ttk.Label(right_info, text=self.get_text("features_list_label"), font=('Microsoft YaHei', 11, 'bold')).pack(anchor="w", pady=(0, 5))

        free_features = [
            self.get_text("feature_f3"),
            self.get_text("feature_f5"),
            self.get_text("feature_f6"),
            self.get_text("feature_f9"),
            self.get_text("feature_f10"),
            self.get_text("feature_skill_combo"),
            self.get_text("feature_auto_click")
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
        # 獲取當前選中的分頁索引
        current_tab_index = self.notebook.index(self.notebook.select())

        # 根據不同的分頁處理滾輪事件
        if current_tab_index == 0:  # 血量監控分頁
            # 血量監控分頁：滾動Treeview
            self.settings_tree.yview_scroll(int(-1*(event.delta/120)), "units")
            return "break"

        elif current_tab_index == 4:  # 使用說明分頁
            # 使用說明分頁：滾動Canvas
            if hasattr(self, 'help_canvas') and self.help_canvas:
                self.help_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                return "break"

        return "break"  # 阻止事件繼續傳播

    def auto_load_preview(self):
        """在程式啟動時自動載入預覽圖片（僅載入已保存的圖片，避免耗時的即時截圖）"""
        # 檢查是否有已儲存的區域設定
        if self.config.get('region') and self.config.get('window_title'):
            try:
                # 檢查遊戲視窗是否存在
                windows = gw.getWindowsWithTitle(self.config['window_title'])
                if windows:
                    # 設定視窗選擇
                    self.window_var.set(self.config['window_title'])
                    
                    # 只載入已保存的預覽圖片，不進行即時截圖以加快啟動速度
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
                        self.preview_label.config(text=self.get_text("game_window_not_found").format(window_title=self.config['window_title']), image="")
                    if hasattr(self, 'mana_preview_label') and self.config.get('mana_region'):
                        self.mana_preview_label.config(text=self.get_text("game_window_not_found").format(window_title=self.config['window_title']), image="")
            except Exception as e:
                print(f"自動載入預覽失敗: {e}")
                if hasattr(self, 'preview_label'):
                    self.preview_label.config(text=self.get_text("settings_load_failed"), image="")
                if hasattr(self, 'mana_preview_label'):
                    self.mana_preview_label.config(text=self.get_text("settings_load_failed"), image="")
        else:
            # 沒有設定時顯示預設提示
            if hasattr(self, 'preview_label'):
                self.preview_label.config(text=self.get_text("select_health_bar_first"), image="")
            if hasattr(self, 'mana_preview_label'):
                self.mana_preview_label.config(text=self.get_text("select_mana_bar_first"), image="")
            print("沒有找到已儲存的設定")

    def refresh_windows(self):
        windows = [w.title for w in gw.getAllWindows() if w.title]
        if hasattr(self, 'window_combo'):
            self.window_combo['values'] = windows
        else:
            print("警告: window_combo 不存在")

    def start_selection(self):
        if not self.window_var.get():
            CustomMessageBox.show_error(self.get_text("error"), self.get_text("select_game_window_first"), self.root)
            return

        # 檢查遊戲視窗是否最小化
        if self.check_game_window_minimized(self.window_var.get()):
            return

        # 如果當前正在監控，自動停止監控
        if self.monitoring:
            self.stop_monitoring()
            CustomMessageBox.show_info(self.get_text("important_reminder"), self.get_text("monitoring_auto_stopped_for_selection"), self.root)

        try:
            window = gw.getWindowsWithTitle(self.window_var.get())[0]
            window.activate()
            time.sleep(0.1)  # 等待視窗激活

            self.selection_active = True

            # 框選時最小化主視窗以便清楚看到遊戲視窗
            self.root.iconify()  # 最小化主視窗

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
                             text=self.get_text("select_health_bar_instruction"),
                             fill="white", font=("Arial", 14, "bold"),
                             anchor="center")

        except Exception as e:
            CustomMessageBox.show_error(self.get_text("error"), self.get_text("selection_start_failed").format(error=str(e)), self.root)

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

            # 非同步擷取預覽圖，避免阻塞UI線程
            self.root.after(100, self.capture_preview_async)

        self.selection_active = False
        self.remove_global_esc_listener()
        if hasattr(self, 'selection_window') and self.selection_window:
            self.selection_window.destroy()
            self.selection_window = None

        # 統一的GUI恢復
        self.finalize_selection_restore_gui()

    def cancel_selection(self, event):
        self.selection_active = False
        self.selection_start = None
        self.selection_end = None
        
        # 移除全局ESC監聽
        self.remove_global_esc_listener()
        
        if hasattr(self, 'selection_window') and self.selection_window:
            self.selection_window.destroy()
        
        # 統一的GUI恢復
        self.finalize_selection_restore_gui()

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

    def finalize_selection_restore_gui(self, success_message_key=None, message_params=None):
        """統一的選擇完成後GUI恢復和訊息顯示helper函數"""
        # 重新激活主視窗並恢復正常狀態
        self.root.deiconify()
        self.root.attributes("-topmost", self.always_on_top_var.get())  # 恢復置頂（根據用戶設定）
        self.root.lift()
        self.root.focus_force()

        # 如果有成功訊息，顯示確認對話框
        if success_message_key:
            message = self.get_text(success_message_key)
            if message_params:
                message = message.format(**message_params)
            CustomMessageBox.show_info(self.get_text("success"), message, self.root)

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
                self.root.after(0, lambda: self.cancel_inventory_ui_selection(None))
                print("檢測到ESC鍵，取消背包UI選擇")
                return
            
            # 檢查背包區域選擇
            if hasattr(self, 'inventory_selection_active') and self.inventory_selection_active:
                # 使用tkinter的after方法來確保在主線程中執行
                self.root.after(0, lambda: self.cancel_inventory_selection(None))
                print("檢測到ESC鍵，取消背包區域選擇")
                return
        except Exception as e:
            print(f"背包相關選擇的全局ESC處理失敗: {e}")

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
            CustomMessageBox.show_error(self.get_text("error"), self.get_text("select_game_window_first"), self.root)
            return

        # 檢查遊戲視窗是否最小化
        if self.check_game_window_minimized(self.window_var.get()):
            return

        # 如果當前正在監控，自動停止監控
        if self.monitoring:
            self.stop_monitoring()
            CustomMessageBox.show_info(self.get_text("important_reminder"), self.get_text("monitoring_auto_stopped_for_selection"), self.root)

        try:
            window = gw.getWindowsWithTitle(self.window_var.get())[0]
            window.activate()
            time.sleep(0.1)  # 等待視窗激活

            self.selection_active = True

            # 框選時最小化主視窗以便清楚看到遊戲視窗
            self.root.iconify()  # 最小化主視窗

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
                             text=self.get_text("select_mana_bar_instruction"),
                             fill="white", font=("Arial", 14, "bold"),
                             anchor="center")

        except Exception as e:
            CustomMessageBox.show_error(self.get_text("error"), self.get_text("mana_selection_start_failed").format(error=str(e)), self.root)

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

            # 非同步擷取魔力預覽圖，避免阻塞UI線程
            self.root.after(100, self.capture_mana_preview_async)

        self.selection_active = False
        self.remove_global_esc_listener()
        if hasattr(self, 'selection_window') and self.selection_window:
            self.selection_window.destroy()
            self.selection_window = None

        # 統一的GUI恢復
        self.finalize_selection_restore_gui()

    def capture_mana_preview(self):
        if not self.selected_mana_region:
            return

        if not self._is_game_window_active():
            if hasattr(self, 'mana_preview_label'):
                self.mana_preview_label.config(text=self.get_text("waiting_for_game_window"), image="")
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

        if not self._is_game_window_active():
            if hasattr(self, 'preview_label'):
                self.preview_label.config(text=self.get_text("waiting_for_game_window"), image="")
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

    def capture_preview_async(self):
        """非同步擷取預覽圖，避免阻塞UI線程"""
        if not self._is_game_window_active():
            self.root.after(0, lambda: hasattr(self, 'preview_label') and self.preview_label.config(text=self.get_text("waiting_for_game_window"), image=""))
            return

        def _capture():
            if not self.selected_region:
                return

            try:
                window = gw.getWindowsWithTitle(self.window_var.get())[0]
                x, y, w, h = self.selected_region
                abs_x = window.left + x
                abs_y = window.top + y

                with mss.mss() as sct:
                    monitor = {"top": abs_y, "left": abs_x, "width": w, "height": h}
                    screenshot = sct.grab(monitor)
                    img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                    img.thumbnail((200, 200))

                    preview_path = os.path.join(get_app_dir(), "screenshots", "health_monitor_preview.png")
                    os.makedirs(os.path.dirname(preview_path), exist_ok=True)
                    img.save(preview_path)

                    self.draw_scale_lines(img)
                    resized_img = self.resize_and_center_image(img, self.preview_size)

                    def _update_preview():
                        try:
                            self.preview_image = ImageTk.PhotoImage(resized_img)
                            if hasattr(self, 'preview_label'):
                                self.preview_label.config(image=self.preview_image, text="")
                            print("血量預覽更新成功")
                        except Exception as e:
                            print(f"血量預覽更新失敗: {e}")
                            if hasattr(self, 'preview_label'):
                                self.preview_label.config(text=f"預覽擷取失敗\n{str(e)}", image="")

                    self.root.after(0, _update_preview)
            except Exception as e:
                print(f"預覽擷取失敗: {e}")
                _err_msg = str(e)
                def _update_error():
                    if hasattr(self, 'preview_label'):
                        self.preview_label.config(text=f"預覽擷取失敗\n{_err_msg}", image="")
                self.root.after(0, _update_error)

        thread = threading.Thread(target=_capture, daemon=True)
        thread.start()

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
            # 如果沒有預覽檔案且有區域設定，顯示等待預覽的提示
            if self.selected_region and hasattr(self, 'preview_label'):
                self.preview_label.config(text=self.get_text("health_region_set_waiting_preview"), image="")
                return False
            elif hasattr(self, 'preview_label'):
                self.preview_label.config(text=self.get_text("select_health_bar_first"), image="")
                return False

    def capture_mana_preview_async(self):
        """非同步擷取魔力預覽圖片，避免阻塞UI"""
        if not self._is_game_window_active():
            self.root.after(0, lambda: hasattr(self, 'mana_preview_label') and self.mana_preview_label.config(text=self.get_text("waiting_for_game_window"), image=""))
            return

        def _capture():
            if not self.selected_mana_region:
                return

            try:
                window = gw.getWindowsWithTitle(self.window_var.get())[0]
                x, y, w, h = self.selected_mana_region
                abs_x = window.left + x
                abs_y = window.top + y

                with mss.mss() as sct:
                    monitor = {"top": abs_y, "left": abs_x, "width": w, "height": h}
                    screenshot = sct.grab(monitor)
                    img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                    img.thumbnail((200, 200))

                    mana_preview_path = os.path.join(get_app_dir(), "screenshots", "health_monitor_mana_preview.png")
                    os.makedirs(os.path.dirname(mana_preview_path), exist_ok=True)
                    img.save(mana_preview_path)

                    self.draw_scale_lines(img)
                    resized_img = self.resize_and_center_image(img, self.preview_size)

                    def _update_preview():
                        try:
                            self.mana_preview_image = ImageTk.PhotoImage(resized_img)
                            if hasattr(self, 'mana_preview_label'):
                                self.mana_preview_label.config(image=self.mana_preview_image, text="")
                            print("魔力預覽更新成功")
                        except Exception as e:
                            print(f"魔力預覽更新失敗: {e}")
                            if hasattr(self, 'mana_preview_label'):
                                self.mana_preview_label.config(text=f"魔力預覽擷取失敗\n{str(e)}", image="")

                    self.root.after(0, _update_preview)
            except Exception as e:
                print(f"魔力預覽擷取失敗: {e}")
                _err_msg = str(e)
                def _update_error():
                    if hasattr(self, 'mana_preview_label'):
                        self.mana_preview_label.config(text=f"魔力預覽擷取失敗\n{_err_msg}", image="")
                self.root.after(0, _update_error)

        import threading
        thread = threading.Thread(target=_capture, daemon=True)
        thread.start()

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
                    self.mana_preview_label.config(text=self.get_text("mana_preview_load_failed"), image="")
                return False
        else:
            # 如果沒有預覽檔案但有區域設定，嘗試即時擷取
            if self.selected_mana_region and hasattr(self, 'mana_preview_label'):
                # 嘗試即時擷取預覽
                try:
                    self.capture_mana_preview_async()
                    return True
                except:
                    self.mana_preview_label.config(text=self.get_text("mana_region_set_waiting_preview"), image="")
                    return False
            elif hasattr(self, 'mana_preview_label'):
                self.mana_preview_label.config(text=self.get_text("select_mana_bar_first"), image="")
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
            CustomMessageBox.show_error(self.get_text("error"), str(e), self.root)

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
            type_display = "HP" if setting_type == "HP" else "MP"
            self.settings_tree.insert("", tk.END, values=(type_display, percent, key, cooldown))

            # 清空輸入
            self.on_type_changed()  # 重置為預設值

        except ValueError as e:
            CustomMessageBox.show_error(self.get_text("input_error"), str(e), self.root)
        except Exception as e:
            CustomMessageBox.show_error(self.get_text("error"), self.get_text("add_setting_failed").format(error=str(e)), self.root)

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
            CustomMessageBox.show_warning(self.get_text("important_reminder"), self.get_text("select_setting_to_remove_first"), self.root)
            return

        # 確認刪除
        if not CustomMessageBox.ask_yes_no(self.get_text("confirm"), self.get_text("confirm_remove_setting"), self.root):
            return

        # 從樹狀圖中移除
        item_values = self.settings_tree.item(selected_item[0], 'values')
        self.settings_tree.delete(selected_item[0])

        # 從設定中移除
        if 'settings' in self.config:
            setting_type = item_values[0]  # 直接使用UI顯示的值
            self.config['settings'] = [
                setting for setting in self.config['settings']
                if not (setting.get('type', 'HP') == setting_type and 
                       setting['percent'] == int(item_values[1]) and 
                       setting['key'] == item_values[2])
            ]

    def load_settings_to_tree(self):
        for item in self.settings_tree.get_children():
            self.settings_tree.delete(item)

        for setting in self.config.get('settings', []):
            cooldown = setting.get('cooldown', 1000)  # 預設1000ms冷卻時間
            setting_type = setting.get('type', 'HP')  # 預設為HP
            type_display = "HP" if setting_type == "HP" else "MP"
            self.settings_tree.insert("", tk.END, values=(type_display, setting['percent'], setting['key'], cooldown))

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
        with self.monitoring_lock:
            return self.monitoring
    
    def set_monitoring(self, state):
        """線程安全地設置監控狀態"""
        with self.monitoring_lock:
            self.monitoring = state
    
    def wait_monitoring_stopped(self, timeout=2.0):
        """等待監控線程停止"""
        start_time = time.time()
        while self.is_monitoring() and (time.time() - start_time) < timeout:
            time.sleep(0.05)
        
        # 等待線程完全結束
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=max(0.1, timeout - (time.time() - start_time)))

    # ========== 線程安全的連段狀態管理 ==========
    def is_combo_running(self):
        """線程安全地檢查連段狀態"""
        with self.combo_lock:
            return self.combo_running
    
    def set_combo_running(self, state):
        """線程安全地設置連段狀態"""
        with self.combo_lock:
            self.combo_running = state
    
    def wait_combo_stopped(self, timeout=2.0):
        """等待連段線程停止"""
        start_time = time.time()
        while self.is_combo_running() and (time.time() - start_time) < timeout:
            time.sleep(0.05)
        
        # 等待線程完全結束
        if self.combo_thread and self.combo_thread.is_alive():
            self.combo_thread.join(timeout=max(0.1, timeout - (time.time() - start_time)))

    # ========== 線程安全的全域暫停管理 ==========
    def is_global_pause(self):
        """線程安全地檢查全域暫停狀態"""
        with self.global_pause_lock:
            return self.global_pause
    
    def set_global_pause(self, state):
        """線程安全地設置全域暫停狀態"""
        with self.global_pause_lock:
            self.global_pause = state

    def start_monitoring(self):
        # 檢查是否已在監控中
        if self.is_monitoring():
            print("[WARN] 監控已在運行中，跳過重複啟動")
            return

        # 檢查OpenCV是否可用
        if not OPENCV_AVAILABLE:
            messagebox.showerror(self.get_text("error"), "OpenCV不可用，無法啟動監控功能。請重新安裝應用程式。")
            return

        if not self.window_var.get():
            messagebox.showerror(self.get_text("error"), self.get_text("select_game_window_first"))
            return

        # 檢查遊戲視窗是否最小化
        if self.check_game_window_minimized(self.window_var.get()):
            return

        if not self.config.get('region'):
            messagebox.showerror(self.get_text("error"), self.get_text("select_health_bar_region_first"))
            return

        if not self.config.get('settings'):
            messagebox.showerror(self.get_text("error"), self.get_text("set_at_least_one_trigger"))
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

        # 線程安全地設置監控狀態
        self.set_monitoring(True)
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        # 添加狀態訊息
        self.add_status_message(self.get_text("health_monitor_started"), "success")

        # 開始監控時設置為非干擾模式：降低不透明度但保持可見
        self.root.attributes("-alpha", 0.8)  # 輕微透明
        self.manage_window_hierarchy(self.root, "MAIN")  # 設置主視窗層級

        self.monitor_thread = threading.Thread(target=self.monitor_health)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop monitoring without blocking the Tk main thread."""
        if not self.is_monitoring():
            return

        print("[STOP] ...")
        self.set_monitoring(False)

        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.add_status_message(self.get_text("health_monitor_stopped"), "info")

        self.root.attributes("-alpha", 1.0)
        self.manage_window_hierarchy(self.root, "MAIN")
        self.root.after(10, self._wait_for_monitoring_stop_async)

    def _wait_for_monitoring_stop_async(self, deadline=None):
        """Wait for monitor thread exit without freezing the GUI."""
        if deadline is None:
            deadline = time.time() + 2.0

        thread = self.monitor_thread
        if not thread or not thread.is_alive():
            self.monitor_thread = None
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
        
        # 線程安全地設置監控狀態
        self.set_monitoring(True)
        
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

    def _interruptible_sleep(self, duration):
        """可中斷的睡眠函數，能夠快速響應停止信號"""
        start_time = time.time()
        while self.is_monitoring() and (time.time() - start_time) < duration:
            time.sleep(0.01)  # 10ms的小睡眠，允許快速響應停止

    def monitor_health(self):
        with mss.mss() as sct:
            while self.is_monitoring():
                # 提前檢查監控狀態，避免不必要的處理
                if not self.is_monitoring():
                    break
                    
                try:
                    # 獲取遊戲視窗位置
                    windows = gw.getWindowsWithTitle(self.window_var.get())
                    if not windows:
                        self.update_status("--", "--", "視窗未找到", "")
                        self.add_status_message(self.get_text("game_window_closed"), "warning")
                        self._interruptible_sleep(1.0)
                        continue

                    window = windows[0]

                    # 檢查遊戲視窗是否在前台且非最小化
                    if window.isMinimized or not window.isActive:
                        if window.isMinimized:
                            self.update_status("--", "--", self.get_text("game_window_minimized"), "")
                        else:
                            self.update_status("--", "--", self.get_text("waiting_for_game_window"), "")
                        if not self._preview_placeholder_shown:
                            self._preview_placeholder_shown = True
                            msg_key = "game_window_minimized" if window.isMinimized else "game_window_lost_focus"
                            self.add_status_message(self.get_text(msg_key), "warning")
                            self.root.after(0, self._show_health_preview_placeholder)
                            self.root.after(0, self._show_mana_preview_placeholder)
                        self._interruptible_sleep(0.5)
                        continue
                    if self._preview_placeholder_shown:
                        self._preview_placeholder_shown = False
                        self.add_status_message(self.get_text("game_window_regained_focus"), "success")

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
                        self._interruptible_sleep(interval_ms / 1000.0)  # 轉換為秒
                    except (ValueError, AttributeError):
                        self._interruptible_sleep(0.1)  # 預設100ms

                except Exception as e:
                    print(f"監控錯誤: {e}")
                    self.update_status("--", "--", "--", f"錯誤: {str(e)}")
                    self._interruptible_sleep(1)

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
                        return self.get_text("interface_ui_not_detected")
                else:
                    return self.get_text("game_window_not_found_for_ui_check")
            except Exception as e:
                return f"{self.get_text('interface_ui_check_failed')}: {str(e)}"

        # 分離HP和MP設定
        health_settings = []
        mana_settings = []

        for setting in self.config.get('settings', []):
            setting_type = setting.get('type', 'HP')
            if setting_type == 'HP':
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
                        return self.get_text("trigger_health").format(percent=setting['percent'], key=setting['key'])
                    else:
                        remaining = cooldown - (current_time - last_trigger) * 1000
                        return self.get_text("cooldown_health").format(percent=setting['percent'], key=setting['key'], remaining=f"{remaining:.0f}")

        # 檢查魔力設定
        if mana_percent is not None and mana_settings:
            for setting in mana_settings:
                if mana_percent <= setting['percent']:
                    # 檢查冷卻狀態
                    cooldown = setting.get('cooldown', 500)
                    last_trigger = self.last_trigger_times.get(f"mana_{setting['percent']}", 0)
                    current_time = time.time()

                    if current_time - last_trigger >= cooldown / 1000:
                        return self.get_text("trigger_mana").format(percent=setting['percent'], key=setting['key'])
                    else:
                        remaining = cooldown - (current_time - last_trigger) * 1000
                        return self.get_text("cooldown_mana").format(percent=setting['percent'], key=setting['key'], remaining=f"{remaining:.0f}")

        return self.get_text("normal")

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

        # 分離HP和MP設定
        health_settings = []
        mana_settings = []

        for setting in self.config.get('settings', []):
            setting_type = setting.get('type', 'HP')
            if setting_type == 'HP':
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

                    print(f" 血量觸發檢查: {health_percent}% <= {setting['percent']}% (設定閾值)")
                    print(f" 冷卻檢查: 上次觸發時間 {time_diff:.3f}秒前, 需要冷卻 {cooldown/1000:.1f}秒")

                    if time_diff >= cooldown / 1000:  # 轉換為秒
                        try:
                            print(f"[OK] 準備觸發: 血量{setting['percent']}%, 按鍵{setting['key']}")
                            # 添加狀態訊息
                            self.add_status_message(self.get_text("health_low_triggered").format(percent=setting['percent'], key=setting['key']), "monitor")
                            self.press_key_sequence(setting['key'], setting['percent'])
                            print(f" 已完成按鍵序列: {setting['key']}")
                        except Exception as e:
                            print(f"[ERROR] 按鍵觸發失敗: {e}")
                            pass
                    else:
                        remaining = cooldown - (time_diff) * 1000
                        print(f"冷卻中: 還需等待 {remaining:.0f}ms")

                    # 找到第一個匹配的設定後就停止，避免執行更高百分比的設定
                    # 但是如果啟用了多重觸發，則繼續檢查其他設定
                    if not self.multi_trigger_var.get():
                        print(f" 單一觸發模式: 停止檢查其他設定")
                        break
                    else:
                        print(f" 多重觸發模式: 繼續檢查其他設定")
                        pass
                else:
                    print(f" 血量未達觸發條件: {health_percent}% > {setting['percent']}%")
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
                            self.add_status_message(self.get_text("mana_low_triggered").format(percent=setting['percent'], key=setting['key']), "monitor")
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
        print(f" 血魔監控開始執行按鍵序列: {key_sequence}")
        
        # 解析鍵序列（用 - 分隔）
        keys = [key.strip() for key in key_sequence.split('-')]
        print(f" 血魔監控解析後的按鍵列表: {keys}")

        # 獲取遊戲窗口句柄
        game_hwnd = self.get_game_window_handle()
        if game_hwnd:
            print(f" 血魔監控使用全局發送到遊戲窗口: {game_hwnd}")
            # 使用修復版本的按鍵發送（keyboard庫 + 防重複）
            for i, key in enumerate(keys):
                vk_code = self.map_key_to_vk_code(key)
                if vk_code:
                    print(f" 血魔按鍵 {i+1}/{len(keys)}: {key} -> VK_{vk_code}")
                    self.send_key_to_window(game_hwnd, vk_code)  # 使用修復版本
                else:
                    print(f" 血魔按鍵 {i+1}/{len(keys)}: {key} -> 無法映射鍵碼")

                # 如果不是最後一個鍵，添加延遲
                if i < len(keys) - 1:
                    print(f" 血魔按鍵間延遲: 25ms")
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
                    print(f" 血魔防重複: 跳過重複按鍵 {vk_code} (間隔 {(current_time - last_send_time)*1000:.1f}ms)")
                    return
            else:
                self._last_key_send_times = {}
            
            # 記錄發送時間
            self._last_key_send_times[key_id] = current_time
            
            print(f" 血魔監控發送按鍵: VK_{vk_code} 到窗口 {hwnd}")
            
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
                    print(f" 血魔使用keyboard庫發送: {key_name}")
                    keyboard.press_and_release(key_name)
                    print(f"[OK] 血魔keyboard庫發送成功: {key_name}")
                else:
                    # 回退到PostMessage方法
                    self._send_with_postmessage(hwnd, vk_code)
                    
            except ImportError:
                print("[WARN] keyboard庫未安裝，血魔使用PostMessage方法")
                self._send_with_postmessage(hwnd, vk_code)
            except Exception as keyboard_error:
                print(f"[WARN] keyboard庫發送失敗，血魔回退到PostMessage: {keyboard_error}")
                self._send_with_postmessage(hwnd, vk_code)
                
        except Exception as e:
            print(f"[ERROR] 血魔按鍵發送失敗: {e}")
            pass

    def send_key_to_window_combo(self, hwnd, vk_code):
        """發送鍵盤事件到指定窗口 - 技能連段專用（原始版本）"""
        try:
            print(f"[SKILL] 技能連段發送按鍵: VK_{vk_code} 到窗口 {hwnd}")
            
            # 使用原始的SendMessage方法 - 針對特定窗口，不會干擾聊天
            SendMessageW(hwnd, WM_KEYDOWN, vk_code, 0)
            time.sleep(0.01)  # 原始的10毫秒延遲
            SendMessageW(hwnd, WM_KEYUP, vk_code, 0)
            
            print(f"[OK] 技能連段SendMessage發送成功: VK_{vk_code}")
                
        except Exception as e:
            print(f"[ERROR] 技能連段按鍵發送失敗: {e}")
            pass

    def _send_with_postmessage(self, hwnd, vk_code):
        """使用PostMessage發送按鍵的備用方法"""
        try:
            from ctypes import windll
            PostMessageW = windll.user32.PostMessageW
            
            print(f" 使用PostMessage備用方法: VK_{vk_code}")
            # 使用PostMessage (異步)
            result1 = PostMessageW(hwnd, WM_KEYDOWN, vk_code, 0)
            time.sleep(0.1)  # 增加到100毫秒延遲
            result2 = PostMessageW(hwnd, WM_KEYUP, vk_code, 0)
            
            print(f"[OK] PostMessage發送成功: VK_{vk_code} (down:{result1}, up:{result2})")
        except Exception as e:
            print(f"[ERROR] PostMessage發送失敗: {e}")

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

    def open_video_link(self, url):
        """打開影片連結"""
        import webbrowser
        try:
            webbrowser.open(url)
        except Exception as e:
            messagebox.showerror(self.get_text("error"), self.get_text("browser_open_failed").format(error=e))

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
                gui_title = f"Sid輔助工具 {CURRENT_VERSION} - 血魔監控 + 一鍵清包 + 自動化工具"
                return gui_title.lower() in foreground_title.lower()
            else:
                return False

        except Exception as e:
            print(f"檢查GUI前台狀態失敗: {e}")
            return False

    def _is_game_window_active(self):
        """檢查遊戲視窗是否在前台且可用（非最小化）"""
        try:
            windows = gw.getWindowsWithTitle(self.window_var.get())
            if not windows:
                return False
            w = windows[0]
            return not w.isMinimized and w.isActive
        except:
            return False

    def _show_health_preview_placeholder(self):
        """在血量預覽上顯示等待激活提示（主線程呼叫）"""
        if hasattr(self, 'preview_label'):
            self.preview_label.config(text=self.get_text("waiting_for_game_window"), image="")

    def _show_mana_preview_placeholder(self):
        """在魔力預覽上顯示等待激活提示（主線程呼叫）"""
        if hasattr(self, 'mana_preview_label'):
            self.mana_preview_label.config(text=self.get_text("waiting_for_game_window"), image="")

    def adjust_colors(self):
        """調整顏色檢測參數"""
        adjust_window = self.create_settings_window(self.get_text("adjust_colors_title"), "1000x700")
        adjust_window.resizable(False, False)
        adjust_window.focus_force()

        # 主標題
        title_label = ttk.Label(adjust_window, text=self.get_text("adjust_colors_main_title"),
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
        health_frame = ttk.LabelFrame(main_frame, text=self.get_text("health_pixel_ratio_threshold"), padding="10")
        health_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(health_frame, text=self.get_text("current_value")).grid(row=0, column=0, sticky=tk.W, pady=2)
        current_health_label = ttk.Label(health_frame, text=f"{self.health_threshold}",
                                        font=("Arial", 9, "bold"), foreground="blue")
        current_health_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(health_frame, text=self.get_text("new_value_0_1")).grid(row=1, column=0, sticky=tk.W, pady=(10, 2))
        health_threshold_var = tk.StringVar(value=str(self.health_threshold))
        health_entry = ttk.Entry(health_frame, textvariable=health_threshold_var, width=12)
        health_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 2))

        # 健康比例閾值詳細說明
        health_explanation = self.get_text("health_pixel_ratio_explanation")
        ttk.Label(health_frame, text=health_explanation, font=("", 9),
                 foreground="gray", justify=tk.LEFT, wraplength=700).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        # 顏色範圍區域
        color_frame = ttk.LabelFrame(main_frame, text=self.get_text("color_range_settings"), padding="10")
        color_frame.pack(fill=tk.X, pady=(0, 10))

        # 紅色H範圍
        ttk.Label(color_frame, text=self.get_text("red_h_range_label")).grid(row=0, column=0, sticky=tk.W, pady=2)
        current_red_label = ttk.Label(color_frame, text=f"{self.red_h_range}",
                                     font=("Arial", 9, "bold"), foreground="red")
        current_red_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(color_frame, text=self.get_text("new_value_0_20")).grid(row=1, column=0, sticky=tk.W, pady=(5, 2))
        red_h_var = tk.StringVar(value=str(self.red_h_range))
        red_entry = ttk.Entry(color_frame, textvariable=red_h_var, width=12)
        red_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(5, 2))

        # 紅色H範圍詳細說明
        red_explanation = self.get_text("red_h_range_explanation")
        ttk.Label(color_frame, text=red_explanation, font=("", 9),
                 foreground="gray", justify=tk.LEFT, wraplength=700).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        # 綠色H範圍
        ttk.Label(color_frame, text=self.get_text("green_h_range_label")).grid(row=3, column=0, sticky=tk.W, pady=(15, 2))
        current_green_label = ttk.Label(color_frame, text=f"{self.green_h_range}",
                                       font=("Arial", 9, "bold"), foreground="green")
        current_green_label.grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=(15, 2))

        ttk.Label(color_frame, text=self.get_text("new_value_30_90")).grid(row=4, column=0, sticky=tk.W, pady=(5, 2))
        green_h_var = tk.StringVar(value=str(self.green_h_range))
        green_entry = ttk.Entry(color_frame, textvariable=green_h_var, width=12)
        green_entry.grid(row=4, column=1, sticky=tk.W, padx=(10, 0), pady=(5, 2))

        # 綠色H範圍詳細說明
        green_explanation = self.get_text("green_h_range_explanation")
        ttk.Label(color_frame, text=green_explanation, font=("", 9),
                 foreground="gray", justify=tk.LEFT, wraplength=700).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        # HSV精細調整區域
        hsv_frame = ttk.LabelFrame(main_frame, text=self.get_text("hsv_fine_tuning"), padding="10")
        hsv_frame.pack(fill=tk.X, pady=(0, 10))

        # 紅色飽和度
        ttk.Label(hsv_frame, text=self.get_text("red_min_saturation")).grid(row=0, column=0, sticky=tk.W, pady=2)
        current_red_sat_label = ttk.Label(hsv_frame, text=f"{self.red_saturation_min}",
                                         font=("Arial", 9, "bold"), foreground="red")
        current_red_sat_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(hsv_frame, text=self.get_text("new_value_range")).grid(row=1, column=0, sticky=tk.W, pady=(5, 2))
        red_sat_var = tk.StringVar(value=str(self.red_saturation_min))
        red_sat_entry = ttk.Entry(hsv_frame, textvariable=red_sat_var, width=12)
        red_sat_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(5, 2))

        # 紅色亮度
        ttk.Label(hsv_frame, text=self.get_text("red_min_brightness")).grid(row=2, column=0, sticky=tk.W, pady=(10, 2))
        current_red_val_label = ttk.Label(hsv_frame, text=f"{self.red_value_min}",
                                         font=("Arial", 9, "bold"), foreground="red")
        current_red_val_label.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 2))

        ttk.Label(hsv_frame, text=self.get_text("new_value_range")).grid(row=3, column=0, sticky=tk.W, pady=(5, 2))
        red_val_var = tk.StringVar(value=str(self.red_value_min))
        red_val_entry = ttk.Entry(hsv_frame, textvariable=red_val_var, width=12)
        red_val_entry.grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=(5, 2))

        # 紅色HSV參數說明
        ttk.Label(hsv_frame, text=self.get_text("red_hsv_explanation"), font=("", 9),
                 foreground="gray", justify=tk.LEFT, wraplength=700).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        # 綠色飽和度
        ttk.Label(hsv_frame, text=self.get_text("green_min_saturation")).grid(row=0, column=2, sticky=tk.W, padx=(30, 0), pady=2)
        current_green_sat_label = ttk.Label(hsv_frame, text=f"{self.green_saturation_min}",
                                           font=("Arial", 9, "bold"), foreground="green")
        current_green_sat_label.grid(row=0, column=3, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(hsv_frame, text=self.get_text("new_value_range")).grid(row=1, column=2, sticky=tk.W, padx=(30, 0), pady=(5, 2))
        green_sat_var = tk.StringVar(value=str(self.green_saturation_min))
        green_sat_entry = ttk.Entry(hsv_frame, textvariable=green_sat_var, width=12)
        green_sat_entry.grid(row=1, column=3, sticky=tk.W, padx=(10, 0), pady=(5, 2))

        # 綠色亮度
        ttk.Label(hsv_frame, text=self.get_text("green_min_brightness")).grid(row=2, column=2, sticky=tk.W, padx=(30, 0), pady=(10, 2))
        current_green_val_label = ttk.Label(hsv_frame, text=f"{self.green_value_min}",
                                           font=("Arial", 9, "bold"), foreground="green")
        current_green_val_label.grid(row=2, column=3, sticky=tk.W, padx=(10, 0), pady=(10, 2))

        ttk.Label(hsv_frame, text=self.get_text("new_value_range")).grid(row=3, column=2, sticky=tk.W, padx=(30, 0), pady=(5, 2))
        green_val_var = tk.StringVar(value=str(self.green_value_min))
        green_val_entry = ttk.Entry(hsv_frame, textvariable=green_val_var, width=12)
        green_val_entry.grid(row=3, column=3, sticky=tk.W, padx=(10, 0), pady=(5, 2))

        # 綠色HSV參數說明
        ttk.Label(hsv_frame, text=self.get_text("green_hsv_explanation"), font=("", 9),
                 foreground="gray", justify=tk.LEFT, wraplength=700).grid(row=4, column=2, columnspan=2, sticky=tk.W, pady=(5, 0))

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
                    messagebox.showerror(self.get_text("input_error"), self.get_text("health_threshold_range_error"))
                    return

                if not (0 <= new_red_h_range <= 20):
                    messagebox.showerror(self.get_text("input_error"), self.get_text("red_h_range_error"))
                    return

                if not (30 <= new_green_h_range <= 90):
                    messagebox.showerror(self.get_text("input_error"), self.get_text("green_h_range_error"))
                    return

                if not (50 <= new_red_sat_min <= 255):
                    messagebox.showerror(self.get_text("input_error"), self.get_text("red_saturation_range_error"))
                    return

                if not (50 <= new_red_val_min <= 255):
                    messagebox.showerror(self.get_text("input_error"), self.get_text("red_value_range_error"))
                    return

                if not (50 <= new_green_sat_min <= 255):
                    messagebox.showerror(self.get_text("input_error"), self.get_text("green_saturation_range_error"))
                    return

                if not (50 <= new_green_val_min <= 255):
                    messagebox.showerror(self.get_text("input_error"), self.get_text("green_value_range_error"))
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

                messagebox.showinfo(self.get_text("settings_applied"),
                                  self.get_text("color_settings_updated").format(
                                      health_threshold=self.health_threshold,
                                      red_h_range=self.red_h_range,
                                      green_h_range=self.green_h_range,
                                      red_saturation_min=self.red_saturation_min,
                                      red_value_min=self.red_value_min,
                                      green_saturation_min=self.green_saturation_min,
                                      green_value_min=self.green_value_min))
                
                # 關閉視窗
                adjust_window.destroy()

            except ValueError:
                messagebox.showerror(self.get_text("input_error"), self.get_text("enter_valid_number"))

        def reset_to_defaults():
            """重置為預設值"""
            health_threshold_var.set("0.3")
            red_h_var.set("10")
            green_h_var.set("40")
            red_sat_var.set("50")
            red_val_var.set("50")
            green_sat_var.set("50")
            green_val_var.set("50")
            messagebox.showinfo(self.get_text("reset_completed"), self.get_text("reset_completed_message"))
            # 重新激活父視窗
            adjust_window.lift()
            adjust_window.focus_force()
            adjust_window.attributes("-topmost", True)

        # 按鈕 - 放在所有函數定義之後
        ttk.Button(button_frame, text=self.get_text("apply_settings"), command=apply_settings,
                  style="Accent.TButton", width=15).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(button_frame, text=self.get_text("reset_to_defaults"), command=reset_to_defaults, width=18).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(button_frame, text=self.get_text("cancel"), command=adjust_window.destroy, width=10).grid(row=0, column=2)

    def adjust_interface_ui_thresholds(self):
        """調整介面UI檢測參數"""
        adjust_window = self.create_settings_window(self.get_text("adjust_interface_ui_title"), "550x700")
        adjust_window.resizable(False, False)
        adjust_window.focus_force()

        # 主標題
        title_label = ttk.Label(adjust_window, text=self.get_text("adjust_interface_ui_main_title"),
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
        mse_frame = ttk.LabelFrame(main_frame, text=self.get_text("mse_threshold_title"), padding="10")
        mse_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(mse_frame, text=self.get_text("current_value")).grid(row=0, column=0, sticky=tk.W, pady=2)
        current_mse_label = ttk.Label(mse_frame, text=f"{self.interface_ui_mse_threshold}",
                                     font=("Arial", 9, "bold"), foreground="blue")
        current_mse_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(mse_frame, text=self.get_text("new_value_mse_suggested")).grid(row=1, column=0, sticky=tk.W, pady=(10, 2))
        mse_var = tk.StringVar(value=str(int(self.interface_ui_mse_threshold)))
        mse_entry = ttk.Entry(mse_frame, textvariable=mse_var, width=12)
        mse_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 2))

        # MSE詳細說明
        mse_explanation = self.get_text("mse_explanation")
        ttk.Label(mse_frame, text=mse_explanation, font=("", 9),
                 foreground="gray", justify=tk.LEFT, wraplength=320).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        # SSIM閾值區域
        ssim_frame = ttk.LabelFrame(main_frame, text=self.get_text("ssim_threshold_title"), padding="10")
        ssim_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(ssim_frame, text=self.get_text("current_value")).grid(row=0, column=0, sticky=tk.W, pady=2)
        current_ssim_label = ttk.Label(ssim_frame, text=f"{self.interface_ui_ssim_threshold}",
                                      font=("Arial", 9, "bold"), foreground="green")
        current_ssim_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(ssim_frame, text=self.get_text("new_value_range_0_1")).grid(row=1, column=0, sticky=tk.W, pady=(10, 2))
        ssim_var = tk.StringVar(value=str(self.interface_ui_ssim_threshold))
        ssim_entry = ttk.Entry(ssim_frame, textvariable=ssim_var, width=12)
        ssim_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 2))

        # SSIM參數說明
        ttk.Label(ssim_frame, text=self.get_text("ssim_explanation"),
                 font=("Arial", 9), foreground="#666666", wraplength=320).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        # 直方圖閾值區域
        hist_frame = ttk.LabelFrame(main_frame, text=self.get_text("histogram_threshold_title"), padding="10")
        hist_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(hist_frame, text=self.get_text("current_value")).grid(row=0, column=0, sticky=tk.W, pady=2)
        current_hist_label = ttk.Label(hist_frame, text=f"{self.interface_ui_hist_threshold}",
                                      font=("Arial", 9, "bold"), foreground="orange")
        current_hist_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(hist_frame, text=self.get_text("new_value_range_0_1")).grid(row=1, column=0, sticky=tk.W, pady=(10, 2))
        hist_var = tk.StringVar(value=str(self.interface_ui_hist_threshold))
        hist_entry = ttk.Entry(hist_frame, textvariable=hist_var, width=12)
        hist_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 2))

        # 直方圖參數說明
        ttk.Label(hist_frame, text=self.get_text("histogram_explanation"),
                 font=("Arial", 9), foreground="#666666", wraplength=320).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        # 顏色差異閾值區域
        color_frame = ttk.LabelFrame(main_frame, text=self.get_text("color_diff_threshold_title"), padding="10")
        color_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(color_frame, text=self.get_text("current_value")).grid(row=0, column=0, sticky=tk.W, pady=2)
        current_color_label = ttk.Label(color_frame, text=f"{self.interface_ui_color_threshold}",
                                       font=("Arial", 9, "bold"), foreground="red")
        current_color_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(color_frame, text=self.get_text("new_value_suggested")).grid(row=1, column=0, sticky=tk.W, pady=(10, 2))
        color_var = tk.StringVar(value=str(int(self.interface_ui_color_threshold)))
        color_entry = ttk.Entry(color_frame, textvariable=color_var, width=12)
        color_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 2))

        # 顏色差異參數說明
        ttk.Label(color_frame, text=self.get_text("color_diff_explanation"),
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
                    messagebox.showerror(self.get_text("input_error"), self.get_text("mse_threshold_empty"))
                    return
                if not ssim_str:
                    messagebox.showerror(self.get_text("input_error"), self.get_text("ssim_threshold_empty"))
                    return
                if not hist_str:
                    messagebox.showerror(self.get_text("input_error"), self.get_text("histogram_threshold_empty"))
                    return
                if not color_str:
                    messagebox.showerror(self.get_text("input_error"), self.get_text("color_threshold_empty"))
                    return

                # 嘗試轉換為數字
                try:
                    # MSE允許浮點數輸入，但最終轉換為整數
                    new_mse = int(float(mse_str))
                except ValueError:
                    messagebox.showerror(self.get_text("input_error"), self.get_text("mse_invalid_number"))
                    return

                try:
                    new_ssim = float(ssim_str)
                except ValueError:
                    messagebox.showerror(self.get_text("input_error"), self.get_text("ssim_invalid_number"))
                    return

                try:
                    new_hist = float(hist_str)
                except ValueError:
                    messagebox.showerror(self.get_text("input_error"), self.get_text("histogram_invalid_number"))
                    return

                try:
                    # 顏色差異允許浮點數輸入，但最終轉換為整數
                    new_color = int(float(color_str))
                except ValueError:
                    messagebox.showerror(self.get_text("input_error"), self.get_text("color_invalid_number"))
                    return

                # 驗證輸入範圍
                if not (100 <= new_mse <= 2000):
                    messagebox.showerror(self.get_text("input_error"), self.get_text("mse_range_error"))
                    return

                if not (0.0 <= new_ssim <= 1.0):
                    messagebox.showerror(self.get_text("input_error"), self.get_text("ssim_range_error"))
                    return

                if not (0.0 <= new_hist <= 1.0):
                    messagebox.showerror(self.get_text("input_error"), self.get_text("histogram_range_error"))
                    return

                if not (5 <= new_color <= 100):
                    messagebox.showerror(self.get_text("input_error"), self.get_text("color_range_error"))
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

                messagebox.showinfo(self.get_text("settings_applied"),
                                  self.get_text("interface_ui_settings_updated").format(
                                      mse_threshold=self.interface_ui_mse_threshold,
                                      ssim_threshold=self.interface_ui_ssim_threshold,
                                      hist_threshold=self.interface_ui_hist_threshold,
                                      color_threshold=self.interface_ui_color_threshold))

                # 關閉視窗
                adjust_window.destroy()

            except Exception as e:
                messagebox.showerror(self.get_text("error"), f"{self.get_text('settings_applied')}: {str(e)}")

        def reset_to_defaults():
            """重置為預設值"""
            mse_var.set("800")
            ssim_var.set("0.6")
            hist_var.set("0.7")
            color_var.set("35")
            messagebox.showinfo(self.get_text("reset_completed"), self.get_text("reset_completed_message"))
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
        ttk.Button(button_frame, text=self.get_text("apply_settings"), command=apply_settings,
                  style="Accent.TButton", width=15).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(button_frame, text=self.get_text("reset_to_defaults"), command=reset_to_defaults, width=18).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(button_frame, text=self.get_text("cancel"), command=adjust_window.destroy, width=10).grid(row=0, column=2)

    def setup_hotkeys(self):
        # 全域熱鍵，不受視窗焦點限制
        keyboard.add_hotkey('f3', self.quick_clear_inventory)  # F3: 一鍵清包
        keyboard.add_hotkey('f5', self.return_to_hideout)    # F5: 返回藏身
        keyboard.add_hotkey('f6', self.f6_pickup_items)      # F6: 一鍵取物
        keyboard.add_hotkey('f9', self.toggle_global_pause)  # F9: 全域暫停開關
        keyboard.add_hotkey('f10', self.toggle_monitoring)   # F10: 監控開關
        keyboard.add_hotkey('f12', global_f12_handler)       # F12: 緊急關閉（使用全局處理器）
        
        self.add_status_message(self.get_text("global_hotkeys_registered"), "success")
        
        # 設定 CTRL+左鍵自動點擊監聽器
        self.setup_auto_click_listener()
    
    def toggle_global_pause(self):
        """F9: 全域暫停開關 - 暫停/恢復所有熱鍵功能（線程安全）"""
        # 使用鎖保護全域暫停狀態的修改
        with self.global_pause_lock:
            self.global_pause = not self.global_pause
            is_pausing = self.global_pause
        
        if is_pausing:
            print("[STOP] 全域暫停已啟用 - 所有熱鍵功能已暫停")
            print(" 現在可以安全聊天，不會誤觸任何熱鍵")
            print(" 再次按F9可恢復所有功能")
            
            # 添加狀態訊息
            self.add_status_message(self.get_text("global_pause_activated"), "warning")
            
            # 記錄並停止血魔監控（如果正在運行）
            if self.is_monitoring():
                self.monitoring_was_active = True
                self.stop_monitoring()
                print(" 血魔監控已自動停止")
                self.add_status_message(self.get_text("health_monitor_auto_stopped"), "info")
            else:
                self.monitoring_was_active = False
            
            # 記錄並停止技能連段（如果正在運行）
            if self.is_combo_running():
                self.combo_was_running = True
                self.stop_combo_system()
                print(" 技能連段已自動停止")
                self.add_status_message(self.get_text("combo_system_auto_stopped"), "info")
            else:
                self.combo_was_running = False
                
        else:
            print(" 全域暫停已解除 - 自動恢復之前的功能")
            
            # 添加狀態訊息
            self.add_status_message(self.get_text("global_pause_deactivated"), "success")
            
            # 自動恢復血魔監控（如果之前處於活躍狀態）
            if self.monitoring_was_active:
                try:
                    # 靜默重新啟動血魔監控
                    self.restart_monitoring_silently()
                    print("[START] 血魔監控已自動重新啟動")
                    self.add_status_message(self.get_text("health_monitor_auto_restarted"), "success")
                except Exception as e:
                    print(f"[WARN] 血魔監控自動重新啟動失敗: {e}")
                    print(" 請手動重新啟動血魔監控")
                    self.add_status_message(self.get_text("health_monitor_restart_failed").format(error=str(e)), "error")
            
            # 自動恢復技能連段（如果之前處於運行狀態）
            if self.combo_was_running:
                try:
                    # 靜默重新啟動技能連段系統
                    self.restart_combo_system_silently()
                    print("[START] 技能連段已自動重新啟動")
                    self.add_status_message("技能連段已自動重新啟動", "success")
                except Exception as e:
                    print(f"[WARN] 技能連段自動重新啟動失敗: {e}")
                    print(" 請手動重新啟動技能連段系統")
                    self.add_status_message(f"技能連段自動重啟失敗: {str(e)}", "error")
            
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
            self.add_status_message("按下 F10 - 因全域暫停模式而跳過執行", "warning")
            return

        if self.is_monitoring():
            self.add_status_message("按下 F10 - 停止血魔監控", "hotkey")
            self.stop_monitoring()
        else:
            self.add_status_message("按下 F10 - 啟動血魔監控", "hotkey")
            self.start_monitoring()

    def quick_clear_inventory(self):
        """F3快速清包功能（線程安全）"""
        # 全域暫停檢查
        if self.is_global_pause():
            print("[STOP] 全域暫停中，跳過F3熱鍵")
            self.add_status_message("按下 F3 - 因全域暫停模式而跳過執行", "warning")
            return
            
        self.add_status_message(self.get_text("f3_hotkey_pressed"), "hotkey")
        
        # 重置中斷標誌
        self.inventory_clear_interrupt = False

        if not self.inventory_region or not self.empty_inventory_colors:
            self.add_status_message(self.get_text("f3_fail_inventory_incomplete"), "error")
            messagebox.showwarning(self.get_text("f3_inventory_reminder"), self.get_text("inventory_setup_incomplete"))
            return

        # 檢查背包UI是否已設定
        if not self.inventory_ui_region or self.inventory_ui_screenshot is None:
            self.add_status_message(self.get_text("f3_fail_inventory_ui_not_set"), "error")
            messagebox.showwarning(self.get_text("f3_inventory_reminder"), self.get_text("inventory_ui_screenshot_not_set"))
            return

        # 使用血魔監控的遊戲視窗
        window_title = self.window_var.get()
        if not window_title:
            self.add_status_message(self.get_text("f3_fail_game_window_not_set"), "error")
            messagebox.showwarning("F3 清包提醒", "未設定遊戲視窗！\n\n請先在「血量監控」分頁選擇遊戲視窗。")
            return

        # 檢查遊戲視窗是否處於前台
        if not self.is_game_window_foreground(window_title):
            self.add_status_message(self.get_text("f3_cancel_game_not_foreground"), "warning")
            print(f"F3: 遊戲視窗 '{window_title}' 不在前台，跳過清包操作")
            return

        try:
            # 獲取遊戲視窗
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                self.add_status_message(self.get_text("f3_fail_game_window_not_found"), "error")
                print("找不到遊戲視窗")
                return

            game_window = windows[0]
            self.add_status_message(self.get_text("f3_processing_game_window_found"), "info")

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
                self.add_status_message(self.get_text("f3_processing_gui_minimized"), "info")
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
                self.add_status_message(self.get_text("f3_processing_game_window_activated"), "info")
                print("F3: 遊戲視窗已激活")
            except Exception as e:
                print(f"F3: 激活遊戲視窗失敗: {e}")
                # 如果激活失敗，嘗試點擊視窗
                try:
                    pyautogui.click(game_window.left + game_window.width // 2, 
                                  game_window.top + game_window.height // 2)
                    time.sleep(0.2)
                    self.add_status_message(self.get_text("f3_processing_trying_activate"), "info")
                    print("F3: 已嘗試點擊遊戲視窗")
                except Exception as e2:
                    self.add_status_message(self.get_text("f3_warning_cannot_activate_game_window"), "warning")
                    print(f"F3: 點擊遊戲視窗也失敗: {e2}")

            # 檢查背包UI是否可見（GUI已縮小或遊戲視窗已激活，不會被遮擋）
            if not self.is_inventory_ui_visible(game_window):
                print("F3: 背包UI未開啟，跳過清包操作")
                self.add_status_message(self.get_text("f3_cancel_inventory_not_open"), "warning")
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
                needs_clearing, occupied_slots = self.should_clear_inventory(img, self.excluded_inventory_slots)
                if needs_clearing:
                    self.add_status_message(self.get_text("f3_processing_items_detected").format(count=len(occupied_slots)), "info")
                    print(f"F3: 檢測到 {len(occupied_slots)} 個格子有物品，正在清空...")
                    self.clear_inventory_item(game_window, img)
                    if self.inventory_clear_interrupt:
                        self.add_status_message(self.get_text("f3_cancel_user_interrupt"), "warning")
                        print("F3: 清包被中斷")
                    else:
                        self.add_status_message(self.get_text("f3_completed_inventory_cleared"), "success")
                        print("F3: 已清空背包物品")
                else:
                    self.add_status_message("F3 執行完成 - 背包已為空狀態", "success")
                    print("F3: 背包已淨空，無需操作")

        except Exception as e:
            self.add_status_message(self.get_text("f3_fail_error_occurred").format(error=str(e)), "error")
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
        inventory_frame = ttk.LabelFrame(left_frame, text=self.get_text("inventory_settings"), padding="15")
        inventory_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))

        # 框選背包區域
        self.select_inventory_region_btn = ttk.Button(inventory_frame, text=self.get_text("select_inventory_region"), command=self.select_inventory_region)
        self.select_inventory_region_btn.grid(row=0, column=0, pady=2)
        self.record_empty_color_btn = ttk.Button(inventory_frame, text=self.get_text("record_empty_color"), command=self.record_empty_inventory_color)
        self.record_empty_color_btn.grid(row=0, column=1, padx=(10, 0), pady=2)
        self.select_inventory_ui_btn = ttk.Button(inventory_frame, text=self.get_text("select_inventory_ui"), command=self.select_inventory_ui_region)
        self.select_inventory_ui_btn.grid(row=0, column=2, padx=(10, 0), pady=2)

        # 顏色顯示
        self.record_status_label = ttk.Label(inventory_frame, text=self.get_text("record_status"))
        self.record_status_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        self.empty_color_label = ttk.Label(inventory_frame, text=self.get_text("not_recorded"), background="lightgray", relief="sunken")
        self.empty_color_label.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 0))

        # 背包UI顯示
        self.inventory_ui_status_label = ttk.Label(inventory_frame, text=self.get_text("inventory_ui_status"))
        self.inventory_ui_status_label.grid(row=2, column=0, sticky=tk.W, pady=2)
        self.inventory_ui_label = ttk.Label(inventory_frame, text=self.get_text("not_recorded"), background="lightgray", relief="sunken")
        self.inventory_ui_label.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 0))

        # 控制按鈕
        control_frame = ttk.LabelFrame(left_frame, text=self.get_text("control_panel"), padding="15")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))

        self.test_clear_inventory_btn = ttk.Button(control_frame, text=self.get_text("test_clear_inventory"), command=self.test_inventory_clearing)
        self.test_clear_inventory_btn.grid(row=0, column=0, pady=2)
        self.save_inventory_settings_btn = ttk.Button(control_frame, text=self.get_text("save_inventory_settings"), command=self.save_inventory_config)
        self.save_inventory_settings_btn.grid(row=0, column=1, padx=(10, 0), pady=2)

        # GUI設定選項
        gui_control_frame = ttk.Frame(control_frame)
        gui_control_frame.grid(row=1, column=0, columnspan=2, pady=(10, 0))

        ttk.Label(gui_control_frame, text=self.get_text("gui_settings")).grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(gui_control_frame, text=self.get_text("always_on_top"), variable=self.always_on_top_var, 
                       command=self.toggle_always_on_top).grid(row=0, column=1, columnspan=2, sticky=tk.W, padx=(5, 0))

        # 狀態顯示
        status_frame = ttk.LabelFrame(left_frame, text=self.get_text("status"), padding="15")
        status_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))

        self.inventory_f3_label = ttk.Label(status_frame, text=self.get_text("f3_hotkey"))
        self.inventory_f3_label.grid(row=0, column=0, sticky=tk.W, pady=2)
        self.inventory_status_label = ttk.Label(status_frame, text=self.get_text("ready"), foreground="green")
        self.inventory_status_label.grid(row=0, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        self.pause_status_label_title = ttk.Label(status_frame, text=self.get_text("global_pause"))
        self.pause_status_label_title.grid(row=1, column=0, sticky=tk.W, pady=2)
        self.pause_status_label = ttk.Label(status_frame, text=self.get_text("normal_operation"), foreground="green")
        self.pause_status_label.grid(row=1, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        # F6取物座標設定
        pickup_frame = ttk.LabelFrame(left_frame, text=self.get_text("pickup_coordinates"), padding="10")
        pickup_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        # 座標設定按鈕
        self.setup_pickup_coordinates_btn = ttk.Button(pickup_frame, text=self.get_text("setup_pickup_coordinates"), command=self.setup_pickup_coordinates)
        self.setup_pickup_coordinates_btn.grid(row=0, column=0, pady=2)
        self.save_pickup_coordinates_btn = ttk.Button(pickup_frame, text=self.get_text("save_coordinates"), command=self.save_pickup_coordinates)
        self.save_pickup_coordinates_btn.grid(row=0, column=1, padx=(10, 0), pady=2)

        # 座標狀態顯示
        self.coordinates_set_label = ttk.Label(pickup_frame, text=self.get_text("coordinates_set"))
        self.coordinates_set_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        self.pickup_coords_label = ttk.Label(pickup_frame, text=self.get_text("coordinates_count"), foreground="gray")
        self.pickup_coords_label.grid(row=1, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        # F6狀態顯示
        self.pickup_f6_label = ttk.Label(pickup_frame, text=self.get_text("f6_hotkey"))
        self.pickup_f6_label.grid(row=2, column=0, sticky=tk.W, pady=2)
        self.pickup_status_label = ttk.Label(pickup_frame, text=self.get_text("ready"), foreground="green")
        self.pickup_status_label.grid(row=2, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        # UI截圖顯示區域
        ui_preview_frame = ttk.LabelFrame(left_frame, text=self.get_text("inventory_ui_screenshot"), padding="10")
        ui_preview_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        # 創建一個Canvas來顯示UI截圖
        self.ui_preview_canvas = tk.Canvas(ui_preview_frame, width=200, height=150, bg='lightgray', relief='sunken')
        self.ui_preview_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E))

        # 添加說明文字
        self.ui_preview_hint_label = ttk.Label(ui_preview_frame, text=self.get_text("inventory_ui_screenshot_hint"), 
                 font=("", 8), foreground="gray")
        self.ui_preview_hint_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))

        # === 右側區域：背包預覽 ===
        # 背包預覽區域
        preview_frame = ttk.LabelFrame(right_frame, text=self.get_text("inventory_preview"), padding="10")
        preview_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 統計資訊區域
        stats_frame = ttk.Frame(preview_frame)
        stats_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))

        self.occupied_label_title = ttk.Label(stats_frame, text=self.get_text("occupied_slots"))
        self.occupied_label_title.grid(row=0, column=0, sticky=tk.W)
        self.occupied_label = ttk.Label(stats_frame, text=self.get_text("slots_count"), foreground="blue", font=("", 10, "bold"))
        self.occupied_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        # 偏移調整區域
        offset_frame = ttk.Frame(preview_frame)
        offset_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))

        self.grid_adjustment_label = ttk.Label(offset_frame, text=self.get_text("grid_alignment_adjustment"))
        self.grid_adjustment_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 2))

        # 水平偏移調整
        self.horizontal_label = ttk.Label(offset_frame, text=self.get_text("horizontal"))
        self.horizontal_label.grid(row=1, column=0, sticky=tk.W)
        ttk.Button(offset_frame, text="◀", width=3, command=lambda: self.adjust_grid_offset(-1, 0)).grid(row=1, column=1, padx=(5, 2))
        self.offset_x_label = ttk.Label(offset_frame, text="0", width=4, relief="sunken")
        self.offset_x_label.grid(row=1, column=2, padx=(2, 2))
        ttk.Button(offset_frame, text="▶", width=3, command=lambda: self.adjust_grid_offset(1, 0)).grid(row=1, column=3, padx=(2, 10))

        # 垂直偏移調整
        self.vertical_label = ttk.Label(offset_frame, text=self.get_text("vertical"))
        self.vertical_label.grid(row=1, column=4, sticky=tk.W)
        ttk.Button(offset_frame, text="▲", width=3, command=lambda: self.adjust_grid_offset(0, -1)).grid(row=1, column=5, padx=(5, 2))
        self.offset_y_label = ttk.Label(offset_frame, text="0", width=4, relief="sunken")
        self.offset_y_label.grid(row=1, column=6, padx=(2, 2))
        ttk.Button(offset_frame, text="▼", width=3, command=lambda: self.adjust_grid_offset(0, 1)).grid(row=1, column=7, padx=(2, 5))

        self.reset_offset_btn = ttk.Button(offset_frame, text=self.get_text("reset"), command=self.reset_grid_offset)
        self.reset_offset_btn.grid(row=1, column=8, padx=(10, 0))

        self.inventory_preview_label = tk.Canvas(preview_frame, bg="lightgray", highlightthickness=0, relief="sunken", borderwidth=2, width=300, height=200)
        self.inventory_preview_label.grid(row=2, column=0, pady=(5, 0))
        self._preview_placeholder = self.inventory_preview_label.create_text(10, 10, text=self.get_text("select_inventory_region_first"), anchor='nw', fill='gray')
        self.inventory_preview_label.bind('<Button-1>', self._on_preview_click)
        self._preview_has_image = False

        self.inventory_exclude_hint = ttk.Label(preview_frame, text=self.get_text("inventory_exclude_hint"), foreground="gray")
        self.inventory_exclude_hint.grid(row=3, column=0, sticky=tk.W, pady=(2, 5))

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
        if hasattr(self, 'inventory_preview_label') and getattr(self, '_preview_has_image', False):
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
        if hasattr(self, 'inventory_preview_label') and getattr(self, '_preview_has_image', False):
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
            if not self._is_game_window_active():
                if hasattr(self, 'inventory_preview_label'):
                    self.inventory_preview_label.delete("all")
                    self._preview_placeholder = self.inventory_preview_label.create_text(10, 10, text=self.get_text("waiting_for_game_window"), anchor='nw', fill='gray')
                    self._preview_has_image = False
                return

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
                should_clear, occupied_slots = self.should_clear_inventory(img, self.excluded_inventory_slots)

                # 更新預覽
                self.update_inventory_preview_with_items(img, occupied_slots)

        except Exception as e:
            print(f"重新獲取預覽失敗: {e}")

    def select_inventory_region(self):
        """框選背包區域"""
        # 使用血魔監控的遊戲視窗
        window_title = self.window_var.get()
        if not window_title:
            messagebox.showwarning(self.get_text("warning"), self.get_text("set_game_window_first"))
            return

        # 檢查遊戲視窗是否最小化
        if self.check_game_window_minimized(window_title):
            return

        try:
            # 獲取遊戲視窗
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                messagebox.showerror(self.get_text("error"), self.get_text("game_window_not_found"))
                return

            game_window = windows[0]

            # 縮小GUI視窗以避免干擾
            self.root.iconify()
            print("GUI已縮小以進行背包區域框選")

            # 激活遊戲視窗並等待激活完成
            game_window.activate()
            time.sleep(0.3)  # 增加等待時間確保視窗完全激活
            print("遊戲視窗已激活")

            # 設置選擇狀態
            self.inventory_selection_active = True
            
            # 設置全局ESC監聽
            self.setup_global_esc_listener_for_inventory()

            # 創建覆蓋遊戲視窗的選擇視窗
            self.create_inventory_selection_window(game_window)

        except Exception as e:
            messagebox.showerror(self.get_text("error"), self.get_text("selection_failed").format(error=str(e)))
            # 確保GUI被恢復
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
                          text=self.get_text("drag_select_inventory_region"),
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
                    # 先清理選擇狀態，防止無限循環
                    self.inventory_selection_active = False
                    self.inventory_selection_start = None
                    self.inventory_selection_end = None

                    # 銷毀選擇視窗
                    if hasattr(self, 'inventory_selection_window'):
                        self.inventory_selection_window.destroy()

                    # 移除全局ESC監聽
                    self.remove_global_esc_listener_for_inventory()

                    # 先恢復主視窗，避免警告對話框被隱藏
                    self.root.deiconify()
                    self.root.attributes("-topmost", self.always_on_top_var.get())  # 恢復置頂（根據用戶設定）
                    self.root.lift()
                    self.root.focus_force()

                    # 顯示警告並恢復GUI
                    messagebox.showwarning(self.get_text("warning"), self.get_text("selection_too_small"))
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

                # 銷毀選擇視窗（在顯示對話框之前）
                if hasattr(self, 'inventory_selection_window'):
                    self.inventory_selection_window.destroy()

                # 移除全局ESC監聽
                self.remove_global_esc_listener_for_inventory()

                # 統一的GUI恢復和訊息顯示
                self.finalize_selection_restore_gui("inventory_region_set", {
                    'x': self.inventory_region['x'], 
                    'y': self.inventory_region['y'],
                    'width': self.inventory_region['width'], 
                    'height': self.inventory_region['height']
                })

            else:
                # 如果沒有找到遊戲視窗，銷毀選擇視窗
                if hasattr(self, 'inventory_selection_window'):
                    self.inventory_selection_window.destroy()
                self.remove_global_esc_listener_for_inventory()

            # 重新激活主視窗並恢復正常狀態
            self.root.deiconify()
            self.root.attributes("-topmost", self.always_on_top_var.get())  # 恢復置頂（根據用戶設定）
            self.root.lift()
            self.root.focus_force()
            print("GUI已恢復（背包區域選擇完成）")
        else:
            # 如果沒有有效的選擇，取消選擇
            self.cancel_inventory_selection()

    def cancel_inventory_selection(self, event=None):
        """取消背包區域選擇（參考血魔監控邏輯）"""
        # 重置選擇狀態
        self.inventory_selection_active = False
        self.inventory_selection_start = None
        self.inventory_selection_end = None

        # 移除全局ESC監聽
        self.remove_global_esc_listener_for_inventory()

        if hasattr(self, 'inventory_selection_window'):
            self.inventory_selection_window.destroy()

        # 統一的GUI恢復
        self.finalize_selection_restore_gui()

    def record_empty_inventory_color(self):
        """記錄淨空背包的60個格子顏色"""
        if not self.inventory_region:
            messagebox.showwarning(self.get_text("warning"), self.get_text("select_inventory_region_first"))
            return

        # 使用血魔監控的遊戲視窗
        window_title = self.window_var.get()
        if not window_title:
            messagebox.showwarning(self.get_text("warning"), self.get_text("set_game_window_first"))
            return

        # 檢查遊戲視窗是否最小化
        if self.check_game_window_minimized(window_title):
            return

        try:
            # 縮小GUI並激活遊戲視窗，避免GUI遮擋
            self.minimize_all_guis()
            time.sleep(0.5)  # 等待GUI縮小

            # 獲取遊戲視窗
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                messagebox.showerror(self.get_text("error"), self.get_text("game_window_not_found"))
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
                        # 獲取20x20區域的平均顏色以獲得更穩定的結果（從5x5增加到20x20）
                        x1 = max(0, img_x - 10)
                        y1 = max(0, img_y - 10)
                        x2 = min(img.shape[1], img_x + 10)
                        y2 = min(img.shape[0], img_y + 10)

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
                self.empty_color_label.config(text=self.get_text("recorded_colors_template").format(count=recorded_count), background="lightgreen")

                # 恢復主GUI視窗
                self.restore_all_guis()
                print("顏色記錄完成，已恢復GUI視窗")

                # 更新背包預覽畫面，讓使用者看到記錄效果
                self.update_inventory_preview_from_current()

                messagebox.showinfo(self.get_text("success"), self.get_text("empty_color_recorded_message").format(count=recorded_count))

        except Exception as e:
            # 如果發生錯誤，也要恢復GUI視窗
            self.restore_all_guis()
            messagebox.showerror("錯誤", f"記錄顏色失敗: {str(e)}")

    def select_inventory_ui_region(self):
        """框選背包UI區域"""
        # 使用血魔監控的遊戲視窗
        window_title = self.window_var.get()
        if not window_title:
            messagebox.showwarning(self.get_text("warning"), self.get_text("set_game_window_first"))
            return

        # 檢查遊戲視窗是否最小化
        if self.check_game_window_minimized(window_title):
            return

        try:
            # 獲取遊戲視窗
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                messagebox.showerror(self.get_text("error"), self.get_text("game_window_not_found"))
                return

            game_window = windows[0]

            # 縮小GUI視窗以避免干擾
            self.root.iconify()
            print("GUI已縮小以進行背包UI框選")

            # 激活遊戲視窗並等待激活完成
            game_window.activate()
            time.sleep(0.3)  # 增加等待時間確保視窗完全激活
            print("遊戲視窗已激活")

            # 設置選擇狀態
            self.inventory_ui_selection_active = True
            
            # 設置全局ESC監聽
            self.setup_global_esc_listener_for_inventory()

            # 創建覆蓋遊戲視窗的選擇視窗
            self.create_inventory_ui_selection_window(game_window)

        except Exception as e:
            messagebox.showerror("錯誤", f"框選失敗: {str(e)}")
            # 確保GUI被恢復
            self.root.deiconify()

    def select_interface_ui_region(self):
        """框選介面UI區域"""
        # 使用血魔監控的遊戲視窗
        window_title = self.window_var.get()
        if not window_title:
            messagebox.showwarning(self.get_text("warning"), self.get_text("set_game_window_first"))
            return

        # 檢查遊戲視窗是否最小化
        if self.check_game_window_minimized(window_title):
            return

        try:
            # 獲取遊戲視窗
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                messagebox.showerror(self.get_text("error"), self.get_text("game_window_not_found"))
                return

            game_window = windows[0]

            # 縮小GUI視窗以避免干擾
            self.root.iconify()
            print("GUI已縮小以進行介面UI框選")

            # 激活遊戲視窗並等待激活完成
            game_window.activate()
            time.sleep(0.3)  # 增加等待時間確保視窗完全激活
            print("遊戲視窗已激活")

            # 設置選擇狀態
            self.interface_ui_selection_active = True
            
            # 設置全局ESC監聽
            self.setup_global_esc_listener_for_interface()

            # 創建覆蓋遊戲視窗的選擇視窗
            self.create_interface_ui_selection_window(game_window)

        except Exception as e:
            messagebox.showerror("錯誤", f"框選失敗: {str(e)}")
            # 確保GUI被恢復
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
                          text=self.get_text("select_inventory_ui_instruction"),
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
                          text=self.get_text("select_interface_ui_instruction"),
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
                    # 先清理選擇狀態，防止無限循環
                    self.inventory_ui_selection_active = False
                    self.inventory_ui_selection_start = None
                    self.inventory_ui_selection_end = None

                    # 銷毀選擇視窗
                    if hasattr(self, 'inventory_ui_selection_window'):
                        self.inventory_ui_selection_window.destroy()

                    # 移除全局ESC監聽
                    self.remove_global_esc_listener_for_inventory_ui()

                    # 先恢復主視窗，避免警告對話框被隱藏
                    self.root.deiconify()
                    self.root.attributes("-topmost", self.always_on_top_var.get())  # 恢復置頂（根據用戶設定）
                    self.root.lift()
                    self.root.focus_force()

                    # 顯示警告並恢復GUI
                    messagebox.showwarning(self.get_text("warning"), self.get_text("selection_too_small"))
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
                        self.inventory_ui_label.config(text=self.get_text("inventory_ui_recorded"), background="lightgreen")

                        # 更新UI預覽
                        self.update_ui_preview()

                except Exception as e:
                    messagebox.showerror("錯誤", f"截圖失敗: {str(e)}")
                    print(f"詳細錯誤: {e}")
                    import traceback
                    traceback.print_exc()

                # 銷毀選擇視窗（在處理完成後）
                if hasattr(self, 'inventory_ui_selection_window'):
                    self.inventory_ui_selection_window.destroy()

                # 移除全局ESC監聽
                self.remove_global_esc_listener_for_inventory_ui()


                # 統一的GUI恢復和訊息顯示
                self.finalize_selection_restore_gui("inventory_ui_region_set", {
                    'x': self.inventory_ui_region['x'], 
                    'y': self.inventory_ui_region['y'],
                    'width': self.inventory_ui_region['width'], 
                    'height': self.inventory_ui_region['height']
                })

            else:
                # 如果沒有找到遊戲視窗，銷毀選擇視窗
                if hasattr(self, 'inventory_ui_selection_window'):
                    self.inventory_ui_selection_window.destroy()
                self.remove_global_esc_listener_for_inventory_ui()

            # 重新激活主視窗並恢復正常狀態
            self.root.deiconify()
            self.root.attributes("-topmost", self.always_on_top_var.get())  # 恢復置頂（根據用戶設定）
            self.root.lift()
            self.root.focus_force()
            print("GUI已恢復")
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
        self.remove_global_esc_listener_for_inventory_ui()

        if hasattr(self, 'inventory_ui_selection_window'):
            self.inventory_ui_selection_window.destroy()

        # 統一的GUI恢復
        self.finalize_selection_restore_gui()

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
                    # 先清理選擇狀態，防止無限循環
                    self.interface_ui_selection_active = False
                    self.interface_ui_selection_start = None
                    self.interface_ui_selection_end = None

                    # 銷毀選擇視窗
                    if hasattr(self, 'interface_ui_selection_window'):
                        self.interface_ui_selection_window.destroy()

                    # 移除全局ESC監聽
                    self.remove_global_esc_listener_for_interface()

                    # 先恢復主視窗，避免警告對話框被隱藏
                    self.root.deiconify()
                    self.root.attributes("-topmost", self.always_on_top_var.get())  # 恢復置頂（根據用戶設定）
                    self.root.lift()
                    self.root.focus_force()

                    # 顯示警告並恢復GUI
                    messagebox.showwarning(self.get_text("warning"), self.get_text("selection_too_small"))
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

                except Exception as e:
                    messagebox.showerror("錯誤", f"截圖失敗: {str(e)}")
                    print(f"詳細錯誤: {e}")
                    import traceback
                    traceback.print_exc()

                # 銷毀選擇視窗（在處理完成後）
                if hasattr(self, 'interface_ui_selection_window'):
                    self.interface_ui_selection_window.destroy()

                # 移除全局ESC監聽
                self.remove_global_esc_listener_for_interface()

                # 統一的GUI恢復和訊息顯示
                self.finalize_selection_restore_gui("interface_ui_region_set", {
                    'x': self.interface_ui_region['x'], 
                    'y': self.interface_ui_region['y'],
                    'width': self.interface_ui_region['width'], 
                    'height': self.interface_ui_region['height']
                })

            else:
                # 如果沒有找到遊戲視窗，銷毀選擇視窗
                if hasattr(self, 'interface_ui_selection_window'):
                    self.interface_ui_selection_window.destroy()
                self.remove_global_esc_listener_for_interface()

            # 重新激活主視窗並恢復正常狀態
            self.root.deiconify()
            self.root.attributes("-topmost", self.always_on_top_var.get())  # 恢復置頂（根據用戶設定）
            self.root.lift()
            self.root.focus_force()
            print("GUI已恢復（介面UI選擇完成）")
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

        # 統一的GUI恢復
        self.finalize_selection_restore_gui()

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
                    self.inventory_ui_label.config(text=self.get_text("inventory_ui_recorded"), background="lightgreen")
                
                # 更新UI預覽
                if hasattr(self, 'ui_preview_canvas'):
                    if self._startup_phase:
                        self._startup_visual_refresh_pending = True
                    else:
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
                    if self._startup_phase:
                        self._startup_visual_refresh_pending = True
                    else:
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

            # 跳過使用者排除的格子
            if skip_slots is not None and i in skip_slots:
                continue

            if i >= len(self.empty_inventory_colors):
                continue

            # 確保座標在圖片範圍內
            img_x = pos_x - self.inventory_region['x']
            img_y = pos_y - self.inventory_region['y']

            if 0 <= img_x < img.shape[1] and 0 <= img_y < img.shape[0]:
                # 獲取20x20區域的平均顏色（與記錄時保持一致）
                x1 = max(0, img_x - 10)
                y1 = max(0, img_y - 10)
                x2 = min(img.shape[1], img_x + 10)
                y2 = min(img.shape[0], img_y + 10)

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
        """清空背包物品 - 動態辨識版：每次點擊後重新辨識，適應大物品清空多格的情況

        包含智能跳過機制：當遇到無法存放進倉庫的物品時，自動跳過該物品，
        繼續清理其他可以存放的物品，大幅提升清包效率。
        """
        try:
            import math

            # === 階段1：初始識別一次，創建清包列表並計算辨識次數 ===
            print("階段1：開始初始識別，創建清包列表")
            initial_item_positions = self.find_inventory_items(img, self.excluded_inventory_slots, -1)

            if not initial_item_positions:
                print("沒有找到需要清空的物品")
                return

            print(f"找到 {len(initial_item_positions)} 個物品位置，開始動態清包")

            # === 階段2：動態清包循環（替換分組邏輯） ===
            print("階段2：開始動態清包循環")

            # 優化：預先計算monitor配置
            monitor = {
                "top": game_window.top + self.inventory_region['y'],
                "left": game_window.left + self.inventory_region['x'],
                "width": self.inventory_region['width'],
                "height": self.inventory_region['height']
            }

            total_processed = 0
            max_iterations = 40  # 最多處理40個物品（降低試錯次數）

            # 跳過無法清空的物品位置（倉庫滿載時使用）
            skipped_positions = set()  # 記錄跳過的位置

            # 開始動態清包模式：持續按住Ctrl
            print("開始動態清包模式 - 持續按住 Ctrl 鍵")
            pyautogui.keyDown('ctrl')
            time.sleep(0.025)  # CTRL按壓後等待25ms

            while total_processed < max_iterations:
                # 檢查中斷標誌
                if self.inventory_clear_interrupt:
                    print("F3清包被用戶中斷")
                    break

                # 每次循環都重新辨識當前背包狀態
                try:
                    # 辨識前先將滑鼠移動到遊戲視窗正中央，避免滑鼠停留在物品上影響辨識
                    center_x = game_window.left + game_window.width // 2
                    center_y = game_window.top + game_window.height // 2
                    pyautogui.moveTo(center_x, center_y, duration=0.015)
                    time.sleep(0.025)  # 等待滑鼠移動完成

                    with mss.mss() as sct:
                        current_screenshot = sct.grab(monitor)
                        current_img = np.frombuffer(current_screenshot.rgb, dtype=np.uint8).reshape(current_screenshot.height, current_screenshot.width, 3)
                        current_img = cv2.cvtColor(current_img, cv2.COLOR_RGB2BGR)

                    # 分析當前背包狀態
                    should_continue, current_occupied = self.should_clear_inventory(current_img, self.excluded_inventory_slots, -1)

                    # 更新預覽
                    progress_text = f"動態清包: {total_processed} 個道具已處理"
                    self.root.after(0, lambda: self.update_inventory_preview_with_progress(current_img, current_occupied, progress_text))
                    print(f"辨識結果：剩餘 {len(current_occupied)} 個物品需要清理")

                    # 如果背包已清空，結束
                    if not should_continue:
                        print(f"背包已清空，結束動態清包 (總共處理了 {total_processed} 個道具)")
                        break

                except Exception as e:
                    print(f"辨識過程發生錯誤: {e}")
                    break

                # 找到下一個要點擊的物品位置（跳過已標記無法清空的物品）
                current_item_positions = self.find_inventory_items(current_img, self.excluded_inventory_slots, -1)

                # 過濾掉已跳過的位置
                available_positions = [pos for pos in current_item_positions if pos not in skipped_positions]

                if not available_positions:
                    if skipped_positions:
                        print(f" 所有剩餘物品都無法存放進倉庫（已跳過 {len(skipped_positions)} 個位置）")
                        self.add_status_message(self.get_text("inventory_full_cannot_continue"), "warning")
                    else:
                        print("重新辨識發現沒有需要清理的物品，結束")
                    break

                # 選擇第一個可用的物品進行點擊
                next_pos = available_positions[0]
                screen_x = game_window.left + next_pos[0]
                screen_y = game_window.top + next_pos[1]

                # 找到對應的格子索引
                slot_index = None
                for idx, grid_pos in enumerate(self.inventory_grid_positions):
                    if grid_pos == next_pos:
                        slot_index = idx
                        break

                print(f"準備點擊第 {total_processed + 1} 個物品 - 格子索引 {slot_index}, 螢幕坐標 ({screen_x}, {screen_y})")

                # 滑鼠操作時序
                pyautogui.moveTo(screen_x, screen_y, duration=0.015)
                time.sleep(0.025)
                pyautogui.rightClick(screen_x, screen_y)
                time.sleep(0.025)

                print(f"[OK] 已完成右鍵點擊第 {total_processed + 1} 個道具")
                total_processed += 1

                # 點擊完成後，將滑鼠移動到遊戲視窗正中央，避免影響下次辨識
                center_x = game_window.left + game_window.width // 2
                center_y = game_window.top + game_window.height // 2
                pyautogui.moveTo(center_x, center_y, duration=0.015)
                print(f"滑鼠已移動到遊戲視窗正中央 ({center_x}, {center_y})")

                # 每次點擊後等待，讓遊戲有時間處理大物品
                time.sleep(0.015)

                # 檢查點擊的物品是否真的被清空了
                try:
                    # 檢查前先將滑鼠移動到遊戲視窗正中央，避免影響辨識
                    center_x = game_window.left + game_window.width // 2
                    center_y = game_window.top + game_window.height // 2
                    pyautogui.moveTo(center_x, center_y, duration=0.015)
                    time.sleep(0.025)  # 等待滑鼠移動完成

                    with mss.mss() as sct:
                        check_screenshot = sct.grab(monitor)
                        check_img = np.frombuffer(check_screenshot.rgb, dtype=np.uint8).reshape(check_screenshot.height, check_screenshot.width, 3)
                        check_img = cv2.cvtColor(check_img, cv2.COLOR_RGB2BGR)

                    # 檢查點擊的位置是否還有物品
                    check_item_positions = self.find_inventory_items(check_img, self.excluded_inventory_slots, -1)

                    # 如果點擊的位置還有物品，說明無法清空（倉庫滿了）
                    if next_pos in check_item_positions:
                        skipped_positions.add(next_pos)
                        print(f"[WARN] 物品位置 {next_pos} 無法清空，已加入跳過列表 (跳過總數: {len(skipped_positions)})")
                        # 不計入總處理數，因為這個物品沒有被成功清空
                        total_processed -= 1
                    else:
                        print(f"[OK] 物品位置 {next_pos} 已成功清空")

                except Exception as e:
                    print(f"檢查物品清空狀態時發生錯誤: {e}")
                    # 出錯時假設清空成功，繼續處理

            # 釋放CTRL鍵
            print("釋放 Ctrl 鍵")
            pyautogui.keyUp('ctrl')
            time.sleep(0.025)  # CTRL釋放後等待25ms

            # === 階段3：最終確認和重試邏輯 ===
            print("階段3：最終確認和重試邏輯")

            # 清包完成後最終更新預覽，顯示完成狀態
            try:
                # 最終確認前先將滑鼠移動到遊戲視窗正中央，避免影響辨識
                center_x = game_window.left + game_window.width // 2
                center_y = game_window.top + game_window.height // 2
                pyautogui.moveTo(center_x, center_y, duration=0.015)
                time.sleep(0.025)  # 等待滑鼠移動完成

                # 重新擷取最終的背包狀態
                with mss.mss() as sct:
                    final_screenshot = sct.grab(monitor)
                    final_img = np.frombuffer(final_screenshot.rgb, dtype=np.uint8).reshape(final_screenshot.height, final_screenshot.width, 3)
                    final_img = cv2.cvtColor(final_img, cv2.COLOR_RGB2BGR)

                # 分析最終背包狀態
                final_should_clear, final_occupied = self.should_clear_inventory(final_img, self.excluded_inventory_slots, -1)

                # 在主線程中最終更新預覽
                final_progress_text = f"清包完成: {total_processed} 個道具"
                self.root.after(0, lambda: self.update_inventory_preview_with_progress(final_img, final_occupied, final_progress_text))

                # 更新統計標籤為完成狀態
                self.root.after(0, lambda: self.occupied_label.config(text=f"{len(final_occupied)}/60") if hasattr(self, 'occupied_label') else None)

                print(f"最終確認：清包完成 {total_processed} 個道具，剩餘: {len(final_occupied)} 個")

                # 如果還有物品且未達到重試次數限制，執行一次重試
                if final_should_clear and total_processed < max_iterations:
                    print("檢測到還有剩餘物品，執行最終重試")
                    self.add_status_message(self.get_text("f3_retry_final"), "info")

                    # 重新擷取當前狀態作為重試的基礎
                    retry_item_positions = self.find_inventory_items(final_img, self.excluded_inventory_slots, -1)

                    if retry_item_positions:
                        print(f"重試：找到 {len(retry_item_positions)} 個剩餘物品")

                        # 創建重試任務列表
                        retry_tasks = []
                        for pos in retry_item_positions:
                            screen_x = game_window.left + pos[0]
                            screen_y = game_window.top + pos[1]

                            slot_index = None
                            for idx, grid_pos in enumerate(self.inventory_grid_positions):
                                if grid_pos == pos:  # 直接比較tuple
                                    slot_index = idx
                                    break

                            if slot_index is not None:
                                retry_tasks.append((screen_x, screen_y, slot_index))

                        print(f"重試：已創建重試任務列表，包含 {len(retry_tasks)} 個任務")

                        # 執行重試：持續按住Ctrl進行重試點擊
                        pyautogui.keyDown('ctrl')
                        time.sleep(0.025)

                        retry_processed = 0
                        for task in retry_tasks[:5]:  # 限制重試最多處理5個物品
                            if self.inventory_clear_interrupt:
                                break

                            screen_x, screen_y, slot_index = task

                            print(f"重試處理第 {retry_processed + 1} 個剩餘物品，位置: ({screen_x}, {screen_y})")

                            # 正確的滑鼠操作時序：
                            # 1. 滑鼠移動到道具上
                            print(f"重試滑鼠移動到: ({screen_x}, {screen_y})")
                            pyautogui.moveTo(screen_x, screen_y, duration=0.015)  # 恢復到0.015秒
                            # 2. 移動後等待25ms (恢復到25ms)
                            time.sleep(0.025)

                            # 3. 執行右鍵點擊
                            print(f"重試執行右鍵點擊: ({screen_x}, {screen_y})")
                            pyautogui.rightClick(screen_x, screen_y)
                            # 4. 點擊後等待25ms (恢復到25ms)
                            time.sleep(0.025)

                            print(f"已執行右鍵點擊重試第 {retry_processed + 1} 個道具 (包含正確的延遲)")
                            retry_processed += 1
                            total_processed += 1

                        pyautogui.keyUp('ctrl')
                        time.sleep(0.025)  # CTRL釋放後等待25ms，保持一致的時序

                        print(f"重試完成，已額外處理 {retry_processed} 個剩餘物品")

                        # 重試後最終更新前先將滑鼠移動到遊戲視窗正中央
                        center_x = game_window.left + game_window.width // 2
                        center_y = game_window.top + game_window.height // 2
                        pyautogui.moveTo(center_x, center_y, duration=0.015)
                        time.sleep(0.025)  # 等待滑鼠移動完成

                        # 重試後最終更新
                        with mss.mss() as sct:
                            retry_final_screenshot = sct.grab(monitor)
                            retry_final_img = np.frombuffer(retry_final_screenshot.rgb, dtype=np.uint8).reshape(retry_final_screenshot.height, retry_final_screenshot.width, 3)
                            retry_final_img = cv2.cvtColor(retry_final_img, cv2.COLOR_RGB2BGR)

                        _, retry_final_occupied = self.should_clear_inventory(retry_final_img, self.excluded_inventory_slots, -1)

                        final_progress_text = f"清包完成(包含重試): {total_processed} 個道具"
                        self.root.after(0, lambda: self.update_inventory_preview_with_progress(retry_final_img, retry_final_occupied, final_progress_text))

                        self.root.after(0, lambda: self.occupied_label.config(text=f"{len(retry_final_occupied)}/60") if hasattr(self, 'occupied_label') else None)

                        print(f"重試最終確認：總共處理 {total_processed} 個道具，剩餘: {len(retry_final_occupied)} 個")

            except Exception as e:
                print(f"最終確認過程發生錯誤: {e}")

            print(f"F3: 優化清包完成，已清空 {total_processed} 個背包物品")

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
        _, occupied_indices = self.should_clear_inventory(img, skip_slots, current_slot)
        # 將索引轉換為座標
        occupied_positions = []
        for index in occupied_indices:
            if index < len(self.inventory_grid_positions):
                occupied_positions.append(self.inventory_grid_positions[index])
        return occupied_positions

    def _draw_exclusion_overlay(self):
        """在 Canvas 上繪製排除格子的藍色疊加層（獨立於底圖，刷新後仍保留）"""
        if not getattr(self, '_preview_has_image', False) or not hasattr(self, '_preview_meta'):
            return
        canvas = self.inventory_preview_label
        canvas.delete('exclusion')
        meta = self._preview_meta
        cell_w, cell_h = meta['cell_w'], meta['cell_h']
        off_x, off_y = meta['offset_x'], meta['offset_y']
        for idx in self.excluded_inventory_slots:
            row = idx // 12
            col = idx % 12
            x1 = col * cell_w + off_x
            y1 = row * cell_h + off_y
            x2 = x1 + cell_w
            y2 = y1 + cell_h
            canvas.create_rectangle(x1, y1, x2, y2, outline='blue', width=2, tags='exclusion')
            canvas.create_line(x1, y1, x2, y2, fill='blue', width=1, tags='exclusion')
            canvas.create_line(x2, y1, x1, y2, fill='blue', width=1, tags='exclusion')

    def _on_preview_click(self, event):
        """點擊背包預覽切換格子的排除狀態"""
        if not getattr(self, '_preview_has_image', False) or not hasattr(self, '_preview_meta'):
            self.add_status_message("無法切換排除：請先完成背包設定（框選區域＋記錄空格顏色）", "warning")
            return
        meta = self._preview_meta
        click_x = event.x - meta['offset_x']
        click_y = event.y - meta['offset_y']
        if click_x < 0 or click_y >= meta['img_h'] or click_y < 0 or click_x >= meta['img_w']:
            return
        col = click_x // meta['cell_w']
        row = click_y // meta['cell_h']
        if col < 0 or col >= 12 or row < 0 or row >= 5:
            return
        idx = row * 12 + col
        if idx in self.excluded_inventory_slots:
            self.excluded_inventory_slots.discard(idx)
        else:
            self.excluded_inventory_slots.add(idx)
        self._draw_exclusion_overlay()
        self.add_status_message(f"格子 {idx} 已{'排除' if idx in self.excluded_inventory_slots else '取消排除'}", "info")
        self.save_config(show_message=False)

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

            # 考慮偏移來調整網格線位置
            offset_x = int(self.grid_offset_x)
            offset_y = int(self.grid_offset_y)

            # 繪製網格線（根據偏移調整）
            for i in range(1, rows):
                y = i * cell_height + offset_y
                # 確保線條在圖片範圍內
                if 0 <= y < height:
                    cv2.line(display_img, (0, y), (width, y), (128, 128, 128), 1)

            for i in range(1, cols):
                x = i * cell_width + offset_x
                # 確保線條在圖片範圍內
                if 0 <= x < width:
                    cv2.line(display_img, (x, 0), (x, height), (128, 128, 128), 1)

            # 檢查並標記每個格子的狀態
            occupied_count = 0
            for row in range(5):  # 5行
                for col in range(12):  # 12列
                    # 計算格子中心點（考慮偏移）
                    center_x = col * cell_width + cell_width // 2 + offset_x
                    center_y = row * cell_height + cell_height // 2 + offset_y

                    # 確保中心點在圖片範圍內
                    if not (0 <= center_x < width and 0 <= center_y < height):
                        continue

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

            # 排除標記改由 Canvas 疊加層處理（_draw_exclusion_overlay）
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
                    max_width = 700
                    max_height = 500
            except:
                # 如果獲取GUI尺寸失敗，使用預設值
                max_width = 700
                max_height = 500

            # 計算縮放比例，保持長寬比
            scale = min(max_width / width, max_height / height, 1.0)

            if scale < 1.0:
                new_width = int(width * scale)
                new_height = int(height * scale)
                display_img = cv2.resize(display_img, (new_width, new_height))

            # 轉換為PIL圖片
            display_img_rgb = cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(display_img_rgb)
            tk_img = ImageTk.PhotoImage(pil_img)

            # 儲存預覽元數據供點擊排除使用
            disp_w = new_width if scale < 1.0 else width
            disp_h = new_height if scale < 1.0 else height
            self._preview_meta = {
                'img_w': disp_w, 'img_h': disp_h,
                'cell_w': disp_w // 12, 'cell_h': disp_h // 5,
                'offset_x': int(offset_x * scale) if scale < 1.0 else offset_x,
                'offset_y': int(offset_y * scale) if scale < 1.0 else offset_y,
            }
            self._last_preview_img = img
            self._last_occupied_slots = occupied_slots

            # 更新預覽（Canvas，鎖定尺寸 = 圖片尺寸）+ 排除疊加層
            self.inventory_preview_label.delete("all")
            self.inventory_preview_label.create_image(0, 0, image=tk_img, anchor='nw')
            self.inventory_preview_label.image = tk_img
            self.inventory_preview_label.config(width=disp_w, height=disp_h)
            self._preview_has_image = True
            self._draw_exclusion_overlay()

            # 更新統計資訊標籤
            if hasattr(self, 'occupied_label'):
                self.occupied_label.config(text=f"{occupied_count}/60")

        except Exception as e:
            print(f"更新預覽失敗: {e}")
            try:
                display_img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(display_img_rgb)
                tk_img = ImageTk.PhotoImage(pil_img)
                if hasattr(self, 'inventory_preview_label'):
                    self.inventory_preview_label.delete("all")
                    self.inventory_preview_label.create_image(0, 0, image=tk_img, anchor='nw')
                    self.inventory_preview_label.image = tk_img
                    self._preview_has_image = True
                    self._draw_exclusion_overlay()
            except Exception as e2:
                print(f"顯示原始圖片也失敗: {e2}")

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
                # 將格子索引轉換為相對於預覽圖片的座標
                if grid_index < len(self.inventory_grid_positions):
                    abs_x, abs_y = self.inventory_grid_positions[grid_index]
                    # 轉換為相對於背包區域的座標
                    center_x = abs_x - self.inventory_region['x']
                    center_y = abs_y - self.inventory_region['y']

                    # 確保標記在圖片邊界內
                    if 0 <= center_x < width and 0 <= center_y < height:
                        # 繪製紅色叉號表示有物品 - 優化：使用更小的標記提高性能
                        size = 4  # 從6縮小到4
                        cv2.line(display_img, (center_x - size, center_y - size), (center_x + size, center_y + size), (0, 0, 255), 1)
                        cv2.line(display_img, (center_x + size, center_y - size), (center_x - size, center_y + size), (0, 0, 255), 1)

            # 排除標記改由 Canvas 疊加層處理（_draw_exclusion_overlay）
            # 調整圖片大小 - 根據當前GUI尺寸動態調整（與update_inventory_preview保持一致）
            try:
                current_gui_width = self.root.winfo_width()
                current_gui_height = self.root.winfo_height()
                
                # 根據GUI尺寸計算背包預覽的最大可用空間
                if current_gui_width < 600:  # GUI被縮小
                    max_width = max(300, current_gui_width - 100)  # 為側邊欄預留空間
                    max_height = max(200, current_gui_height - 200)  # 為統計和控制區域預留空間
                else:  # 正常GUI尺寸
                    max_width = 700
                    max_height = 500
            except:
                # 如果獲取GUI尺寸失敗，使用預設值
                max_width = 700
                max_height = 500

            # 計算縮放比例，保持長寬比
            scale = min(max_width / width, max_height / height, 1.0)

            if scale < 1.0:
                new_width = int(width * scale)
                new_height = int(height * scale)
                display_img = cv2.resize(display_img, (new_width, new_height))

            # 轉換為PIL圖片
            display_img_rgb = cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(display_img_rgb)
            tk_img = ImageTk.PhotoImage(pil_img)

            # 儲存預覽元數據供點擊排除使用
            disp_w = new_width if scale < 1.0 else width
            disp_h = new_height if scale < 1.0 else height
            self._preview_meta = {
                'img_w': disp_w, 'img_h': disp_h,
                'cell_w': disp_w // 12, 'cell_h': disp_h // 5,
                'offset_x': 0, 'offset_y': 0,
            }
            self._last_preview_img = img
            self._last_occupied_slots = occupied_slots

            # 更新預覽（Canvas，鎖定尺寸 = 圖片尺寸）+ 排除疊加層
            self.inventory_preview_label.delete("all")
            self.inventory_preview_label.create_image(0, 0, image=tk_img, anchor='nw')
            self.inventory_preview_label.image = tk_img
            self.inventory_preview_label.config(width=disp_w, height=disp_h)
            self._preview_has_image = True
            self._draw_exclusion_overlay()

            # 更新統計資訊標籤
            if hasattr(self, 'occupied_label'):
                self.occupied_label.config(text=f"{occupied_count}/60")

        except Exception as e:
            print(f"更新進度預覽失敗: {e}")
            try:
                display_img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(display_img_rgb)
                tk_img = ImageTk.PhotoImage(pil_img)
                if hasattr(self, 'inventory_preview_label'):
                    self.inventory_preview_label.delete("all")
                    self.inventory_preview_label.create_image(0, 0, image=tk_img, anchor='nw')
                    self.inventory_preview_label.image = tk_img
                    self.inventory_preview_label.config(width=disp_w, height=disp_h)
                    self._preview_has_image = True
                    self._draw_exclusion_overlay()
            except Exception as e2:
                print(f"顯示原始圖片也失敗: {e2}")

    def test_inventory_clearing(self):
        """測試背包清空功能 - 增強版本，自動檢測並開啟背包"""
        if not self.inventory_region:
            messagebox.showwarning(self.get_text("warning"), self.get_text("select_inventory_region_first"))
            return

        if not self.empty_inventory_colors:
            messagebox.showwarning(self.get_text("warning"), self.get_text("record_empty_color_first"))
            return

        # 檢查背包UI區域是否已設定
        if not hasattr(self, 'inventory_ui_region') or not self.inventory_ui_region:
            messagebox.showwarning(self.get_text("warning"), self.get_text("select_inventory_ui_region_first"))
            return

        # 使用血魔監控的遊戲視窗
        window_title = self.window_var.get()
        if not window_title:
            messagebox.showwarning(self.get_text("warning"), self.get_text("set_game_window_first"))
            return

        # 檢查遊戲視窗是否最小化
        if self.check_game_window_minimized(window_title):
            return

        try:
            # 1. 檢測遊戲視窗是否存在
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                messagebox.showerror(self.get_text("error"), self.get_text("game_window_not_found"))
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
                should_clear, occupied_slots = self.should_clear_inventory(img, self.excluded_inventory_slots)

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
            self.config['inventory_grid_positions'] = [list(pos) for pos in self.inventory_grid_positions]  # 保存為list格式
            self.config['grid_offset_x'] = self.grid_offset_x
            self.config['grid_offset_y'] = self.grid_offset_y
            self.config['excluded_inventory_slots'] = sorted(self.excluded_inventory_slots)
            # 儲存血魔監控的遊戲視窗標題
            self.config['inventory_window_title'] = self.window_var.get()

            # 儲存背包UI設定
            self.config['inventory_ui_region'] = self.inventory_ui_region
            # 注意：inventory_ui_screenshot是numpy array，不能直接序列化為JSON
            # 我們只儲存區域資訊，截圖會在下次啟動時重新截取

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)

            messagebox.showinfo(self.get_text("success"), self.get_text("inventory_settings_saved"))
            
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
            print("[STOP] 全域暫停中，跳過F5熱鍵")
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
            self.add_status_message(self.get_text("f5_success_hide_command_sent"), "success")
            
        except Exception as e:
            print(f"F5: 返回藏身失敗: {str(e)}")
            self.add_status_message(f"F5 執行失敗 - {str(e)}", "error")

    def f6_pickup_items(self):
        """F6 一鍵取物（非阻塞版）
        主線程做必要的檢查與安排 GUI 操作（使用 root.after），實際的滑鼠/視窗操作在背景執行緒中完成，
        避免阻塞 Tkinter 事件迴圈造成主 GUI 無法互動。"""
        # 全域暫停檢查（主線程）
        if self.global_pause:
            print("[STOP] 全域暫停中，跳過F6熱鍵")
            # 在主線程更新狀態訊息
            try:
                self.root.after(0, lambda: self.add_status_message(self.get_text("f6_skip_global_pause"), "warning"))
            except:
                pass
            return

        # 簡短回饋（主線程）
        try:
            self.root.after(0, lambda: self.add_status_message(self.get_text("f6_hotkey_pressed"), "hotkey"))
        except:
            pass

        print("=== F6取物功能被調用（非阻塞版） ===")

        # 在主線程進行輕量檢查與狀態擷取
        window_title = self.window_var.get()
        if not window_title:
            print("F6: 未設定遊戲視窗，無法使用一鍵取物功能")
            try:
                self.root.after(0, lambda: self.add_status_message(self.get_text("f6_fail_game_window_not_set"), "error"))
            except:
                pass
            return

        print(f"F6: 遊戲視窗已設定為: {window_title}")

        # 檢查 GUI 狀態（在主線程）
        gui_was_visible = (self.root.state() == 'normal')
        gui_was_foreground = False
        gui_was_topmost = self.should_keep_topmost()  # 檢查是否原本保持在最上方
        if gui_was_visible:
            try:
                foreground_hwnd = GetForegroundWindow()
                gui_hwnd = self.root.winfo_id()
                gui_was_foreground = (foreground_hwnd == gui_hwnd)
            except:
                gui_was_foreground = False

        print(f"F6: GUI視窗狀態 - 原本{'顯示' if gui_was_visible else '最小化'}，{'在前台' if gui_was_foreground else '在後台'}，{'保持在最上方' if gui_was_topmost else '不保持在最上方'}")

        # 如果 GUI 在前台或保持在最上方，安排把 GUI 移到後台（主線程）以免遮擋遊戲
        if gui_was_foreground or gui_was_topmost:
            def _prepare_gui_for_execution():
                try:
                    # 如果原本保持在最上方，先取消置頂
                    if gui_was_topmost:
                        self.root.attributes("-topmost", False)
                        print("F6: 已取消 GUI 置頂設定")
                    # 然後移到後台
                    getattr(self.root, 'lower', lambda: None)()
                    print("F6: 已安排將 GUI 移到後台")
                except Exception as e:
                    print(f"F6: 準備 GUI 失敗: {e}")
            try:
                self.root.after(0, _prepare_gui_for_execution)
            except Exception as e:
                print(f"F6: 安排準備 GUI 失敗: {e}")

        # 隱藏可能的設定視窗（主線程）
        def _hide_setting_windows():
            try:
                for w in self.root.winfo_children():
                    try:
                        if w.winfo_exists() and hasattr(w, 'title'):
                            t = str(w.title())
                            if ('F6' in t or '設定' in t or 'setup' in t.lower()) and w.winfo_ismapped():
                                try:
                                    # 先嘗試釋放該視窗的 modal grab（如果有的話），避免 withdraw 後仍保留 grab
                                    try:
                                        if hasattr(w, 'grab_release'):
                                            w.grab_release()
                                            print(f"F6: 已釋放設定視窗的 grab: {t}")
                                    except Exception:
                                        pass

                                    # 如仍有全域 grab，嘗試釋放 root 的 grab
                                    try:
                                        if hasattr(self.root, 'grab_release'):
                                            self.root.grab_release()
                                            print("F6: 已釋放 root 的 grab（備援）")
                                    except Exception:
                                        pass

                                    w.withdraw()
                                    print(f"F6: 隱藏設定視窗: {t}")
                                except Exception as e:
                                    print(f"F6: 隱藏設定視窗失敗 {t}: {e}")
                    except Exception:
                        pass
            except Exception as e:
                print(f"F6: 隱藏設定視窗時發生錯誤: {e}")

        try:
            self.root.after(0, _hide_setting_windows)
        except:
            pass

        # 現在啟動背景執行緒處理實際的取物工作
        def _worker(window_title_local, valid_coords_local, gui_was_foreground_local, gui_was_topmost_local):
            """背景執行緒：執行視窗激活、背包檢查與 pyautogui 點擊序列"""
            try:
                # 嘗試取得遊戲視窗
                windows = gw.getWindowsWithTitle(window_title_local)
                if not windows:
                    print("F6(worker): 找不到遊戲視窗")
                    try:
                        self.root.after(0, lambda: self.add_status_message(self.get_text("f6_fail_game_window_not_set"), "error"))
                    except:
                        pass
                    return

                game_window = windows[0]
                print(f"F6(worker): 找到遊戲視窗: {game_window.title}")

                # 激活遊戲視窗（在OS層面），不是 Tkinter
                try:
                    game_window.activate()
                    time.sleep(0.5)
                except Exception as e:
                    print(f"F6(worker): 激活遊戲視窗失敗: {e}")

                # 再次確認遊戲視窗在前台
                if not self.is_game_window_foreground(window_title_local):
                    print("F6(worker): 警告 - 遊戲視窗可能未在前台")

                # 檢查背包UI是否可見
                if not self.is_inventory_ui_visible(game_window):
                    print("F6(worker): 背包UI未打開，無法執行取物功能")
                    try:
                        self.root.after(0, lambda: self.add_status_message(self.get_text("f6_cancel_inventory_ui_not_open"), "warning"))
                    except:
                        pass
                    return

                try:
                    self.root.after(0, lambda: self.add_status_message(self.get_text("f6_processing_inventory_ui_check_passed"), "info"))
                except:
                    pass

                print(f"F6(worker): 開始執行取物，共 {len(valid_coords_local)} 個座標")

                # 記錄原始滑鼠位置
                try:
                    original_pos = pyautogui.position()
                except:
                    original_pos = None

                # 按住 Ctrl
                try:
                    pyautogui.keyDown('ctrl')
                    time.sleep(0.05)
                except Exception as e:
                    print(f"F6(worker): 按鍵Down失敗: {e}")

                try:
                    for i, (rel_x, rel_y) in enumerate(valid_coords_local):
                        abs_x = game_window.left + rel_x
                        abs_y = game_window.top + rel_y
                        print(f"F6(worker): 處理座標 {i+1}/{len(valid_coords_local)} -> ({abs_x},{abs_y})")
                        pyautogui.moveTo(abs_x, abs_y, duration=0.05)
                        time.sleep(0.05)
                        pyautogui.click()
                        time.sleep(0.05)

                    print("F6(worker): 取物完成")
                    try:
                        self.root.after(0, lambda: self.add_status_message(self.get_text("f6_completed_coordinates_processed").format(count=len(valid_coords_local)), "success"))
                    except:
                        pass

                    if original_pos:
                        try:
                            pyautogui.moveTo(original_pos.x, original_pos.y, duration=0.05)
                        except:
                            pass

                finally:
                    try:
                        pyautogui.keyUp('ctrl')
                    except:
                        pass

                # 執行完畢後：如果 GUI 原本在前台或保持在最上方，安排主線程恢復 GUI
                def _restore_gui():
                    try:
                        if gui_was_foreground_local or gui_was_topmost_local:
                            try:
                                # 先恢復到前台
                                self.root.lift()
                                self.root.focus_force()
                                # 如果原本保持在最上方，恢復置頂
                                if gui_was_topmost_local:
                                    self.root.attributes("-topmost", True)
                                    print("F6(worker): 已在主線程恢復 GUI 到前台並重新置頂")
                                else:
                                    print("F6(worker): 已在主線程恢復 GUI 到前台")
                            except Exception as e:
                                print(f"F6(worker): 恢復 GUI 失敗: {e}")
                        else:
                            print("F6(worker): GUI 保持在後台（原本在後台且不置頂）")
                    except Exception as e:
                        print(f"F6(worker): Restore callback 例外: {e}")

                try:
                    self.root.after(0, _restore_gui)
                except:
                    pass

            except Exception as e:
                print(f"F6(worker): 發生例外: {e}")
                _err_msg = str(e)
                try:
                    self.root.after(0, lambda: self.add_status_message(f"F6 執行失敗 - {_err_msg}", "error"))
                except:
                    pass
                # 確保 ctrl 被釋放
                try:
                    pyautogui.keyUp('ctrl')
                except:
                    pass

        # 組裝有效座標（主線程）
        valid_coords = []
        seen = set()
        if hasattr(self, 'pickup_coordinates') and self.pickup_coordinates:
            for x, y in self.pickup_coordinates:
                if x != 0 or y != 0:
                    t = (x, y)
                    if t not in seen:
                        valid_coords.append((x, y))
                        seen.add(t)

        if not valid_coords:
            print("F6: 沒有有效的取物座標")
            return

        # 背景執行緒啟動
        print(f"F6: 啟動背景執行緒執行取物，共 {len(valid_coords)} 個座標")
        t = threading.Thread(target=_worker, args=(window_title, valid_coords, gui_was_foreground, gui_was_topmost), daemon=True)
        t.start()

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
            messagebox.showinfo(self.get_text("success"), self.get_text("pickup_coordinates_saved"))
            self.root.lift()
            self.root.focus_force()
            
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
        setup_window = self.create_settings_window(self.get_text("setup_f6_pickup_coordinates_title"), "750x500")
        setup_window.resizable(False, False)
        
        # 置中顯示
        setup_window.transient(self.root)
        setup_window.grab_set()
        
        # 說明標籤
        info_label = ttk.Label(setup_window, text=self.get_text("setup_f6_pickup_coordinates_description"), font=("", 14, "bold"))
        info_label.pack(pady=10)
        
        instruction_text = self.get_text("setup_f6_pickup_instructions")
        
        instruction_label = ttk.Label(setup_window, text=instruction_text, 
                                     font=("", 10), justify='left')
        instruction_label.pack(pady=10)
        
        # 座標顯示區域
        coords_frame = ttk.LabelFrame(setup_window, text=self.get_text("coordinate_status"), padding="10")
        coords_frame.pack(fill='x', padx=20, pady=10)
        
        # 確保pickup_coordinates有5個位置
        while len(self.pickup_coordinates) < 5:
            self.pickup_coordinates.append([0, 0])
        
        # 創建座標顯示標籤
        self.coord_display_labels = []
        for i in range(5):
            frame = ttk.Frame(coords_frame)
            frame.pack(fill='x', pady=2)
            
            ttk.Label(frame, text=self.get_text("coordinate_template").format(number=i+1), width=8).pack(side='left')
            
            coord_label = ttk.Label(frame, text=f"({self.pickup_coordinates[i][0]}, {self.pickup_coordinates[i][1]})", 
                                   width=15, relief='sunken')
            coord_label.pack(side='left', padx=(5, 10))
            self.coord_display_labels.append(coord_label)
            
            # 狀態指示器
            status_label = ttk.Label(frame, text=self.get_text("coordinate_not_set"), foreground="gray", width=10)
            status_label.pack(side='left', padx=5)
            self.coord_display_labels.append(status_label)  # 將狀態標籤也加入列表
        
        # 按鈕區域
        button_frame = ttk.Frame(setup_window)
        button_frame.pack(fill='x', padx=20, pady=20)
        
        ttk.Button(button_frame, text=self.get_text("start_continuous_setup"), 
                  command=lambda: self.start_continuous_setup(setup_window), width=25).pack(side='left', padx=5)
        ttk.Button(button_frame, text=self.get_text("test_f6_pickup"), 
                  command=self.test_pickup, width=15).pack(side='left', padx=5)
        ttk.Button(button_frame, text=self.get_text("clear_all_coordinates"), 
                  command=self.clear_all_coordinates, width=12).pack(side='left', padx=5)
        ttk.Button(button_frame, text=self.get_text("save_coordinates"), 
                  command=lambda: [self.save_pickup_coordinates(), setup_window.destroy()], width=18).pack(side='right', padx=5)
        ttk.Button(button_frame, text=self.get_text("close"), 
                  command=setup_window.destroy, width=8).pack(side='right', padx=5)
        
        # 初始化座標顯示
        self.update_coordinate_display()

    def start_continuous_setup(self, parent_window):
        """開始連續設定5個取物座標"""
        # 檢查遊戲視窗是否最小化
        window_title = self.window_var.get()
        if window_title and self.check_game_window_minimized(window_title):
            return

        try:
            # 隱藏設定視窗和主視窗
            parent_window.withdraw()
            self.root.withdraw()
            
            # 等待視窗完全隱藏
            time.sleep(0.5)
            
            messagebox.showinfo(self.get_text("start_setup_title"), 
                self.get_text("start_setup_message"))
            
            import keyboard
            
            # 設定ESC鍵取消標記
            cancel_setup = False
            
            def on_esc_press():
                nonlocal cancel_setup
                cancel_setup = True
                print("[ERROR] 用戶按下ESC，取消設定")
            
            # 註冊ESC鍵監聽
            keyboard.on_press_key('esc', lambda _: on_esc_press())
            
            try:
                for i in range(5):
                    if cancel_setup:
                        messagebox.showinfo(self.get_text("setup_cancelled"), self.get_text("setup_cancelled_message"))
                        break
                    
                    # 提示當前要設定的座標
                    try:
                        # 創建一個小的提示視窗（子視窗 - 最高層級）
                        hint_window = self.create_child_window(self.get_text("setup_coordinate_title").format(current=i+1, total=5), "450x140")
                        hint_window.geometry("+100+100")
                        hint_window.attributes('-alpha', 0.9)
                        
                        hint_label = ttk.Label(hint_window, 
                            text=self.get_text("setup_coordinate_hint").format(number=i+1), 
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
                        
                        # 獲取滑鼠位置並轉換為相對於遊戲視窗的座標
                        abs_x, abs_y = pyautogui.position()
                        
                        # 獲取遊戲視窗位置
                        window_title = self.window_var.get()
                        if window_title:
                            windows = gw.getWindowsWithTitle(window_title)
                            if windows:
                                game_window = windows[0]
                                # 轉換為相對於遊戲視窗的座標
                                rel_x = abs_x - game_window.left
                                rel_y = abs_y - game_window.top
                                self.pickup_coordinates[i] = [rel_x, rel_y]
                                print(f"[OK] 座標 {i+1} 已設定: 絕對座標({abs_x}, {abs_y}) -> 相對座標({rel_x}, {rel_y})")
                            else:
                                # 如果找不到遊戲視窗，使用絕對座標（向後相容）
                                self.pickup_coordinates[i] = [abs_x, abs_y]
                                print(f"[WARN] 找不到遊戲視窗，使用絕對座標 {i+1}: ({abs_x}, {abs_y})")
                        else:
                            # 如果沒有設定遊戲視窗，使用絕對座標（向後相容）
                            self.pickup_coordinates[i] = [abs_x, abs_y]
                            print(f"[WARN] 未設定遊戲視窗，使用絕對座標 {i+1}: ({abs_x}, {abs_y})")
                        
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
                    
                    messagebox.showinfo(self.get_text("setup_completed_title"), 
                        self.get_text("setup_completed_message"))
                    # 重新激活主視窗而不是設定視窗
                    self.root.lift()
                    self.root.focus_force()
                    # 根據用戶設定決定是否置頂主視窗
                    if self.should_keep_topmost():
                        self.root.attributes("-topmost", True)
                else:
                    messagebox.showinfo(self.get_text("setup_cancelled"), self.get_text("setup_cancelled_message"))
                    
            except Exception as e:
                print(f"連續設定失敗: {str(e)}")
                messagebox.showerror(self.get_text("setup_failed"), f"{self.get_text('setup_failed')}: {str(e)}")
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
            messagebox.showerror(self.get_text("setup_failed"), f"{self.get_text('setup_failed')}: {str(e)}")
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
                            status_label.config(text=self.get_text("coordinate_set"), foreground="green")
                        else:
                            status_label.config(text=self.get_text("coordinate_not_set"), foreground="gray")
        
        # 更新主界面狀態
        self.update_pickup_status()

    def clear_all_coordinates(self):
        """清除所有取物座標"""
        if messagebox.askyesno(self.get_text("confirm"), self.get_text("confirm_clear_coordinates")):
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

        # 檢查遊戲視窗是否最小化
        if self.check_game_window_minimized(window_title):
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
            
            print("[OK] 座標和遊戲視窗設定檢查通過")
            
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
            print(f"[OK] 找到遊戲視窗: {window_title}")
            
            # 2. 激活遊戲視窗（讓f6_pickup_items函數自己處理GUI最小化）
            print("激活遊戲視窗...")
            game_window.activate()
            
            # 3. 等待1秒（確保遊戲視窗已活耀），不要有確認視窗
            print("等待1秒確保遊戲視窗已激活...")
            time.sleep(1)
            
            # 4. 調用f6_pickup_items()執行實際取物（該函數會自己處理GUI的最小化和恢復）
            print("執行F6取物功能...")
            self.f6_pickup_items()
            
            # 5. 測試完成（f6_pickup_items已經處理了GUI恢復）
            print("=== F6取物測試完成 ===")
            
        except Exception as e:
            print(f"測試取物功能失敗: {e}")
            # 測試模式：在異常情況下也不恢復GUI視窗
            print("F6: 測試模式 - 異常處理時不恢復GUI視窗")
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

    # Duplicate on_closing removed; actual on_closing is defined later.
    def close_app(self):
        if self._is_closing:
            return

        self._is_closing = True

        for after_attr in ("_silent_version_check_after_id", "_usage_time_after_id"):
            after_id = getattr(self, after_attr, None)
            if after_id:
                try:
                    self.root.after_cancel(after_id)
                except Exception:
                    pass
                setattr(self, after_attr, None)

        # 計算並記錄運行時間
        end_time = datetime.now()
        runtime = end_time - self.start_time
        runtime_str = f"{runtime.days}天 {runtime.seconds//3600}小時 {(runtime.seconds%3600)//60}分鐘 {runtime.seconds%60}秒"
        print(f"應用程式運行時間: {runtime_str}")
        self.add_status_message(f"應用程式運行時間: {runtime_str}", "info")
        
        # 添加關閉訊息
        self.add_status_message("工具正在關閉，清理資源中...", "info")
        
        # 儲存設定
        try:
            self.save_config(show_message=False)
            print("設定已儲存")
        except Exception as e:
            print(f"儲存設定失敗: {e}")
        
        # 停止AHK自動點擊
        self.stop_auto_click_ahk()

        mouse_interrupt_thread = getattr(self, 'mouse_interrupt_thread', None)
        if mouse_interrupt_thread and mouse_interrupt_thread.is_alive():
            try:
                mouse_interrupt_thread.join(timeout=0.3)
            except Exception:
                pass
        
        # 清理鍵盤監聽器
        try:
            keyboard.unhook_all()
        except:
            pass
        
        self.monitoring = False
        self.add_status_message(self.get_text("tool_closed_successfully"), "info")
        
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
        self.monitoring = False
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
                script_dir = os.path.dirname(script_path)
                
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
        """????"""
        print("[DEBUG] load_config ")
        try:
            success, message = self.config_manager.load_config()
            self.config = self.config_manager.config

            if success:
                self.add_status_message(self.get_text("config_loaded_successfully"), "success")
            else:
                self.add_status_message(self.get_text("config_file_not_found"), "info")

            self.selected_region = self.config.get('region')
            self.selected_mana_region = self.config.get('mana_region')
            self.inventory_region = self.config.get('inventory_region')
            self.empty_inventory_colors = self.config.get('empty_inventory_colors', [])
            self.inventory_grid_positions = [tuple(pos) for pos in self.config.get('inventory_grid_positions', [])]
            self.grid_offset_x = self.config.get('grid_offset_x', 0)
            self.grid_offset_y = self.config.get('grid_offset_y', 0)
            self.excluded_inventory_slots = set(self.config.get('excluded_inventory_slots', []))

            self.inventory_ui_region = self.config.get('inventory_ui_region')
            if self.inventory_ui_region:
                self.load_ui_screenshot_from_file()

            self.interface_ui_region = self.config.get('interface_ui_region')
            if self.interface_ui_region:
                self.load_interface_ui_screenshot_from_file()

            if hasattr(self, 'empty_color_label') and self.empty_inventory_colors:
                recorded_count = len([c for c in self.empty_inventory_colors if c != (0, 0, 0)])
                self.empty_color_label.config(
                    text=self.get_text("recorded_colors_template").format(count=recorded_count),
                    background="lightgreen",
                )

            if hasattr(self, 'inventory_ui_label') and self.inventory_ui_region:
                self.inventory_ui_label.config(text=self.get_text("inventory_ui_recorded"), background="lightgreen")
                if hasattr(self, 'ui_preview_canvas'):
                    if self._startup_phase:
                        self._startup_visual_refresh_pending = True
                    else:
                        self.update_ui_preview()

            if hasattr(self, 'interface_ui_label') and self.interface_ui_region:
                self.interface_ui_label.config(text=self.get_interface_ui_region_text(), background="lightgreen")
                if hasattr(self, 'interface_ui_preview_canvas'):
                    if self._startup_phase:
                        self._startup_visual_refresh_pending = True
                    else:
                        self.update_interface_ui_preview()

            if 'inventory_window_title' in self.config:
                self.inventory_window_var.set(self.config['inventory_window_title'])
            elif 'window_title' in self.config:
                self.inventory_window_var.set(self.config['window_title'])

            if hasattr(self, 'window_var') and 'window_title' in self.config:
                self.window_var.set(self.config['window_title'])

            self.blood_magic_enabled = self.config.get('blood_magic_enabled', False)
            self.blood_magic_region = self.config.get('blood_magic_region', None)
            self.blood_magic_threshold = self.config.get('blood_magic_threshold', 50)
            self.blood_magic_window_title = self.config.get('blood_magic_window_title', '')

            self.monitor_interval = self.config.get('monitor_interval', 0.1)
            self.auto_clear_enabled = self.config.get('auto_clear_enabled', False)
            self.clear_interval = self.config.get('clear_interval', 30)

            if hasattr(self, 'monitor_interval_var'):
                interval_ms = int(self.monitor_interval * 1000)
                self.monitor_interval_var.set(str(interval_ms))

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
                self.mse_threshold_var.set(str(self.interface_ui_mse_threshold))
            if hasattr(self, 'ssim_threshold_var'):
                self.ssim_threshold_var.set(str(self.interface_ui_ssim_threshold))
            if hasattr(self, 'hist_threshold_var'):
                self.hist_threshold_var.set(str(self.interface_ui_hist_threshold))
            if hasattr(self, 'color_threshold_var'):
                self.color_threshold_var.set(str(self.interface_ui_color_threshold))

            self.multi_trigger_var.set(self.config.get('multi_trigger', False))

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
                self.update_pickup_status()

            if 'combo_sets' in self.config:
                self.combo_sets = self.config['combo_sets']
                for combo_set in self.combo_sets:
                    if 'trigger_delay' not in combo_set:
                        combo_set['trigger_delay'] = ''
                    if 'stationary_attacks' not in combo_set:
                        combo_set['stationary_attacks'] = [False, False, False, False, False]

                while len(self.combo_sets) < 3:
                    self.combo_sets.append({
                        'trigger_key': 'Q' if len(self.combo_sets) == 0 else 'W' if len(self.combo_sets) == 1 else 'E',
                        'trigger_delay': '',
                        'combo_keys': ['', '', '', '', ''],
                        'delays': ['', '', '', '', ''],
                        'stationary_attacks': [False, False, False, False, False],
                    })
                self.combo_sets = self.combo_sets[:3]
                print(f": {len(self.combo_sets)} ")

            if 'combo_enabled' in self.config:
                self.combo_enabled = self.config['combo_enabled']
                while len(self.combo_enabled) < 3:
                    self.combo_enabled.append(False)
                self.combo_enabled = self.combo_enabled[:3]
                print(f": {self.combo_enabled}")
            else:
                self.combo_enabled = [False, False, False]

            self.update_combo_ui_from_config()
            self.update_offset_labels()
            if self._startup_phase:
                self._startup_visual_refresh_pending = True
            else:
                self.update_inventory_preview_from_current()

            if hasattr(self, 'region_label'):
                self.region_label.config(
                    text=self.get_region_text(),
                    background="lightgreen" if self.config.get('region') else "lightgray",
                )
            if hasattr(self, 'mana_region_label'):
                self.mana_region_label.config(
                    text=self.get_mana_region_text(),
                    background="lightgreen" if self.config.get('mana_region') else "lightgray",
                )

            if hasattr(self, 'load_settings_to_tree'):
                self.load_settings_to_tree()

            if hasattr(self, 'ui_preview_canvas'):
                self.update_ui_preview()

            if hasattr(self, 'update_pickup_coordinates_display'):
                self.update_pickup_coordinates_display()

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
            self.add_status_message(f"??????- {str(e)}", "error")
            self.config = {}

    def save_config(self, show_message=True):
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
            if hasattr(self, 'excluded_inventory_slots'):
                self.config['excluded_inventory_slots'] = sorted(self.excluded_inventory_slots)

            # 儲存觸發設定
            settings = []
            if hasattr(self, 'settings_tree'):
                for item in self.settings_tree.get_children():
                    values = self.settings_tree.item(item, 'values')
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
            self.config['multi_trigger'] = self.multi_trigger_var.get()

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
                self.config['combo_sets'] = self.combo_sets
            if hasattr(self, 'combo_enabled'):
                self.config['combo_enabled'] = self.combo_enabled

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

            # 儲存取物座標設定
            if hasattr(self, 'pickup_coordinates') and self.pickup_coordinates:
                self.config['pickup_coordinates'] = self.pickup_coordinates

            # 儲存背包視窗標題（區分於血魔監控視窗）
            if hasattr(self, 'inventory_window_var'):
                self.config['inventory_window_title'] = self.inventory_window_var.get()

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
            self.config_manager.save_config(self.config)

            self.add_status_message("設定檔案儲存成功", "success")
            if show_message:
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
                    print(" AHK自動點擊(EXE版)已以管理員權限啟動")
                    print(" 現在可以直接使用 CTRL+左鍵 進行自動連點")
                    print(" 當主程式退出時，AHK腳本會自動關閉")
                except Exception as admin_error:
                    print(f"管理員權限啟動失敗，嘗試普通啟動: {admin_error}")
                    # 如果管理員權限啟動失敗，則使用普通方式
                    self.auto_click_process = subprocess.Popen([
                        self.auto_click_exe_path,
                        process_name
                    ], creationflags=subprocess.CREATE_NO_WINDOW)
                    print(" AHK自動點擊(EXE版)已啟動")
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
                    print("[ERROR] 未找到AutoHotkey程式，請確保已安裝AutoHotkey或使用EXE版本")
                    return
                
                # 啟動AHK腳本，傳遞Python進程名稱作為參數
                self.auto_click_process = subprocess.Popen([
                    ahk_exe, 
                    self.auto_click_script_path,
                    process_name
                ], creationflags=subprocess.CREATE_NO_WINDOW)
                
                print(" AHK自動點擊已啟動")
                print(" 現在可以直接使用 CTRL+左鍵 進行自動連點")
                print(" 當主程式退出時，AHK腳本會自動關閉")
                
            else:
                print("[ERROR] 未找到AHK腳本或EXE文件")
                print(f"請確保存在以下文件之一：")
                print(f"  - {self.auto_click_exe_path}")
                print(f"  - {self.auto_click_script_path}")
                
        except Exception as e:
            print(f"[ERROR] 啟動AHK自動點擊失敗: {e}")

    def stop_auto_click_ahk(self):
        """停止AHK自動點擊腳本"""
        try:
            if self.auto_click_process and self.auto_click_process.poll() is None:
                self.auto_click_process.terminate()
                self.auto_click_process.wait(timeout=3)
                print("[STOP] AHK自動點擊已停止")
            else:
                print("AHK自動點擊未運行")
        except subprocess.TimeoutExpired:
            # 如果無法正常終止，強制結束
            self.auto_click_process.kill()
            print("[STOP] AHK自動點擊已強制停止")
        except Exception as e:
            print(f"停止AHK自動點擊時發生錯誤: {e}")
        finally:
            self.auto_click_process = None

    def toggle_auto_click(self):
        """切換自動點擊狀態（備用方案）"""
        if self.auto_click_active:
            self.stop_auto_click()
            print("[STOP] 自動點擊已停止（Ctrl+Shift+Z）")
        else:
            self.start_auto_click()
            print(" 自動點擊已啟動（Ctrl+Shift+Z再次按下可停止）")

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
        title_label = ttk.Label(main_frame, text=self.get_text("version_check_title"), font=('Microsoft YaHei', 18, 'bold'))
        title_label.pack(pady=(15, 35))
        
        # 當前版本資訊框架
        current_frame = ttk.LabelFrame(main_frame, text=self.get_text("current_version_info"), padding="20")
        current_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(current_frame, text=self.get_text("current_version_label"), font=('Microsoft YaHei', 12, 'bold')).pack(anchor=tk.W)
        current_version_label = ttk.Label(current_frame, text=CURRENT_VERSION, 
                                        font=('Microsoft YaHei', 14, 'bold'), foreground='blue')
        current_version_label.pack(anchor=tk.W, pady=(5, 0))
        
        # 遠端版本資訊框架
        remote_frame = ttk.LabelFrame(main_frame, text=self.get_text("latest_version_info"), padding="20")
        remote_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.latest_version_var = tk.StringVar(value=self.get_text("checking_version"))
        ttk.Label(remote_frame, text=self.get_text("latest_version_label"), font=('Microsoft YaHei', 12, 'bold')).pack(anchor=tk.W)
        self.latest_version_label = ttk.Label(remote_frame, textvariable=self.latest_version_var,
                                            font=('Microsoft YaHei', 14, 'bold'), foreground='green')
        self.latest_version_label.pack(anchor=tk.W, pady=(5, 10))
        
        # 版本狀態顯示
        self.version_status_var = tk.StringVar(value=self.get_text("checking_version_status"))
        self.version_status_label = ttk.Label(remote_frame, textvariable=self.version_status_var,
                                            font=('Microsoft YaHei', 11))
        self.version_status_label.pack(anchor=tk.W, pady=(0, 10))
        
        # 更新說明 - 使用Text widget以獲得更好的格式
        ttk.Label(remote_frame, text=self.get_text("update_notes_label"), font=('Microsoft YaHei', 11, 'bold')).pack(anchor=tk.W, pady=(5, 5))

        # 創建Text widget來顯示更新說明
        self.release_notes_text = tk.Text(remote_frame, height=6, wrap=tk.WORD,
                                        font=('Microsoft YaHei', 10), foreground='gray',
                                        bg=self.root.cget('bg'), relief='flat', borderwidth=0)
        self.release_notes_text.pack(fill=tk.X, pady=(0, 10))
        self.release_notes_text.insert(1.0, self.get_text("loading_text"))
        self.release_notes_text.config(state='disabled')  # 預設為只讀

        # 添加滾動條
        scrollbar = ttk.Scrollbar(remote_frame, orient="vertical", command=self.release_notes_text.yview)
        self.release_notes_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 10))
        self.release_notes_text.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=(0, 10))
        
        # 按鈕框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(25, 0))
        
        # 檢查更新按鈕
        self.check_update_btn = ttk.Button(button_frame, text=self.get_text("check_update_button"), 
                                         command=self.check_for_updates)
        self.check_update_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 前往下載按鈕
        self.download_btn = ttk.Button(button_frame, text=self.get_text("download_page_button"), 
                                     command=self.open_download_page, state='disabled')
        self.download_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 檢查GitHub連接按鈕
        self.test_connection_btn = ttk.Button(button_frame, text=self.get_text("test_connection_button"), 
                                            command=self.test_github_connection)
        self.test_connection_btn.pack(side=tk.LEFT)
        
        # 自動靜默檢查版本（只在有新版本時彈出提醒）
        self._silent_version_check_after_id = self.root.after(2000, self.silent_version_check)

    def create_combo_tab(self):
        """創建技能連段分頁 - 橫向寬敞佈局"""
        main_frame = self.combo_frame
        
        # 標題
        title_label = ttk.Label(main_frame, text=self.get_text("skill_combo_system_title"), font=('Microsoft YaHei', 20, 'bold'))
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
        control_frame = ttk.LabelFrame(content_frame, text=self.get_text("global_control"), padding="20")
        control_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(25, 0))
        
        # 控制按鈕區域
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.combo_start_btn = ttk.Button(button_frame, text=self.get_text("start_combo_system"), 
                                        command=self.start_combo_system, width=20)
        self.combo_start_btn.pack(side=tk.LEFT, padx=(0, 15))
        
        self.combo_stop_btn = ttk.Button(button_frame, text=self.get_text("stop_combo_system"), 
                                       command=self.stop_combo_system, state=tk.DISABLED, width=20)
        self.combo_stop_btn.pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Button(button_frame, text=self.get_text("save_combo_settings"), command=self.save_combo_config, width=15).pack(side=tk.LEFT)
        
        # 狀態顯示區域
        status_frame = ttk.Frame(control_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(status_frame, text=self.get_text("system_status"), font=('Microsoft YaHei', 13, 'bold')).pack(side=tk.LEFT)
        self.combo_status_label = ttk.Label(status_frame, text=self.get_text("not_started"), foreground="red", font=('Microsoft YaHei', 13))
        self.combo_status_label.pack(side=tk.LEFT, padx=(8, 0))
        
        # 設定content_frame的網格佈局
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        content_frame.columnconfigure(2, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # 使用說明區域
        help_frame = ttk.LabelFrame(main_frame, text=self.get_text("usage_instructions"), padding="20")
        help_frame.pack(fill=tk.X, pady=(25, 0))
        
        help_text = self.get_text("skill_combo_usage_title") + "\n\n" + self.get_text("skill_combo_usage_content")
        
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
        set_frame = ttk.LabelFrame(parent, text=self.get_text("combo_set_template").format(number=set_index + 1), padding="15")
        set_frame.grid(row=0, column=set_index, sticky=(tk.N, tk.S, tk.W, tk.E), padx=(0, 15) if set_index < 2 else (0, 0))
        
        # 初始化UI元件引用存儲
        if len(self.combo_ui_refs) <= set_index:
            self.combo_ui_refs.extend([{}] * (set_index + 1 - len(self.combo_ui_refs)))
        
        # 啟用勾選框
        enabled_var = tk.BooleanVar(value=self.combo_enabled[set_index])
        enabled_check = ttk.Checkbutton(set_frame, text=self.get_text("enable_this_set"), 
                                      variable=enabled_var,
                                      command=functools.partial(self.toggle_combo_set, set_index, enabled_var))
        enabled_check.grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(0, 15))
        self.combo_ui_refs[set_index]['enabled_var'] = enabled_var        # 觸發技能設定
        trigger_frame = ttk.Frame(set_frame)
        trigger_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 15))

        ttk.Label(trigger_frame, text=self.get_text("trigger_skill"), font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W)
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
        ttk.Label(trigger_frame, text=self.get_text("initial_delay_ms"), font=('Arial', 10, 'bold')).grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        trigger_delay_var = tk.StringVar(value=self.combo_sets[set_index]['trigger_delay'])
        trigger_delay_entry = ttk.Entry(trigger_frame, textvariable=trigger_delay_var, width=8, font=('Arial', 10))
        trigger_delay_entry.grid(row=0, column=3, sticky=tk.W, padx=(10, 0))
        trigger_delay_entry.bind("<KeyRelease>",
                               functools.partial(self.update_trigger_delay, set_index, trigger_delay_var))
        self.combo_ui_refs[set_index]['trigger_delay_var'] = trigger_delay_var

        # 連段技能設定區域
        skills_frame = ttk.LabelFrame(set_frame, text=self.get_text("combo_skill_settings"), padding="10")
        skills_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 10))

        # 創建技能設定區域的網格佈局
        for i in range(5):
            # 行標籤
            row_label = self.get_text("skill_template").format(number=i+1)
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
            ttk.Label(skills_frame, text=self.get_text("delay_ms"), font=('Arial', 9)).grid(row=i, column=2, sticky=tk.W, padx=(15, 0), pady=3)

            # 延遲時間輸入框
            delay_var = tk.StringVar(value=self.combo_sets[set_index]['delays'][i] if self.combo_sets[set_index]['delays'][i] else '')
            delay_entry = ttk.Entry(skills_frame, textvariable=delay_var, width=8, font=('Arial', 9))
            delay_entry.grid(row=i, column=3, sticky=tk.W, padx=(5, 0), pady=3)
            delay_entry.bind("<KeyRelease>",
                           functools.partial(self.update_combo_delay, set_index, i, delay_var))
            
            # 原地攻擊checkbox
            stationary_var = tk.BooleanVar(value=self.combo_sets[set_index]['stationary_attacks'][i])
            stationary_check = ttk.Checkbutton(skills_frame, text=self.get_text("stationary_attack"), variable=stationary_var,
                                             command=functools.partial(self.update_stationary_attack, set_index, i, stationary_var))
            stationary_check.grid(row=i, column=4, sticky=tk.W, padx=(15, 0), pady=3)
            
            # 原地攻擊說明標籤
            ttk.Label(skills_frame, text=self.get_text("shift_skill_note"), font=('Arial', 8), foreground="gray").grid(
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

        # ── 技能計時器模組（掛在 combo_frame 底部）──
        # 只在第一次建立時初始化，避免重複建立
        if not hasattr(self, 'skill_timer'):
            self.skill_timer = SkillTimerModule(
                parent=self.combo_frame,
                max_slots=4,
                on_log=self.add_status_message,
                get_text=self.get_text
            )
            self.skill_timer.frame.pack(fill="x", padx=5, pady=(10, 5))

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
        """啟動連段系統（線程安全）"""
        if self.is_combo_running():
            messagebox.showwarning(self.get_text("warning"), self.get_text("combo_system_already_running"))
            return
        
        # 檢查是否有啟用的套組
        enabled_sets = [i for i, enabled in enumerate(self.combo_enabled) if enabled]
        if not enabled_sets:
            messagebox.showwarning(self.get_text("warning"), self.get_text("enable_at_least_one_combo_set"))
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
        
        # 線程安全地設置連段狀態
        self.set_combo_running(True)
        self.combo_thread = threading.Thread(target=self.run_combo_system, daemon=True)
        self.combo_thread.start()
        
        # 更新UI
        self.combo_start_btn.config(state=tk.DISABLED)
        self.combo_stop_btn.config(state=tk.NORMAL)
        self.combo_status_label.config(text=self.get_text("combo_running"), foreground="green")
        
        enabled_count = len(enabled_sets)
        self.add_status_message(self.get_text("combo_system_started").format(count=enabled_count), "success")
        print("技能連段系統已啟動")

    def stop_combo_system(self):
        """停止連段系統（線程安全）"""
        if not self.is_combo_running():
            return
        
        print("[STOP] 正在停止連段系統...")
        # 線程安全地設置連段狀態
        self.set_combo_running(False)
        
        # 等待連段線程完全結束
        self.wait_combo_stopped(timeout=2.0)
        
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
        self.combo_status_label.config(text=self.get_text("combo_stopped"), foreground="red")
        
        self.add_status_message("技能連擊系統已停止", "info")
        print("[STOP] 連段系統已完全停止")

    def restart_combo_system_silently(self):
        """靜默重新啟動連段系統（用於全域暫停恢復，線程安全）"""
        if self.is_combo_running():
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
        
        # 線程安全地設置連段狀態
        self.set_combo_running(True)
        self.combo_thread = threading.Thread(target=self.run_combo_system, daemon=True)
        self.combo_thread.start()
        
        # 更新UI（如果元件存在）
        try:
            if hasattr(self, 'combo_start_btn') and self.combo_start_btn:
                self.combo_start_btn.config(state=tk.DISABLED)
            if hasattr(self, 'combo_stop_btn') and self.combo_stop_btn:
                self.combo_stop_btn.config(state=tk.NORMAL)
            if hasattr(self, 'combo_status_label') and self.combo_status_label:
                self.combo_status_label.config(text=self.get_text("combo_running"), foreground="green")
        except:
            pass  # UI 更新失敗不影響功能

    def run_combo_system(self):
        """運行連段系統的主循環（線程安全）"""
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
        while self.is_combo_running():
            time.sleep(0.1)
        
        print("連段系統線程已結束")

    def execute_combo(self, set_index):
        """執行指定的連段套組（線程安全）"""
        if not self.is_combo_running():
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
        self.add_status_message(self.get_text("combo_trigger_detected").format(
            set=set_index + 1, key=trigger_key, count=len(valid_keys)), "monitor")
        
        # 添加技能序列資訊
        if valid_keys:
            skills_text = " | ".join([f"{i+1}:{key}" for i, key in enumerate(valid_keys)])
            self.add_status_message(self.get_text("combo_skill_sequence").format(sequence=skills_text), "monitor")
        print(f"執行連段套組 {set_index + 1}: {valid_keys}")
        
        # 處理觸發延遲（如果有設定）
        if trigger_delay and trigger_delay != 'off' and trigger_delay != '':
            try:
                delay_ms = int(trigger_delay)
                if delay_ms > 0:
                    delay = delay_ms / 1000.0  # 轉換為秒
                    self.add_status_message(self.get_text("combo_trigger_delay").format(delay=delay_ms), "info")
                    print(f"  觸發延遲: {delay_ms}ms")
                    time.sleep(delay)
            except (ValueError, TypeError):
                # 如果延遲時間無效，跳過延遲
                pass
        
        # 執行連段
        for i, key in enumerate(combo_keys):
            # 跳過off或空值的技能
            if not key or key == 'off' or key == '' or not self.is_combo_running():
                if not self.is_combo_running():
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
                            
                            self.add_status_message(self.get_text("combo_skill_execution").format(
                                index=i+1, skill=f"Shift+{key}", type=self.get_text("stationary_attack"), method=self.get_text("selective_send")), "success")
                            print(f"  原地攻擊模式: Shift+{key} (發送到遊戲窗口)")
                        else:
                            # 如果無法映射鍵碼，回退到全局按鍵
                            pyautogui.keyDown('shift')
                            pyautogui.press(key.lower())
                            pyautogui.keyUp('shift')
                            self.add_status_message(self.get_text("combo_skill_execution").format(
                                index=i+1, skill=f"Shift+{key}", type=self.get_text("stationary_attack"), method=self.get_text("global_send")), "warning")
                            print(f"  原地攻擊模式: Shift+{key} (全局按鍵)")
                    else:
                        # 普通攻擊：直接按技能鍵
                        vk_code = self.map_key_to_vk_code(key.lower())
                        if vk_code:
                            self.send_key_to_window_combo(game_hwnd, vk_code)  # 使用技能連段專用方法
                            self.add_status_message(self.get_text("combo_skill_execution").format(
                                index=i+1, skill=key, type=self.get_text("normal_attack"), method=self.get_text("selective_send")), "success")
                            print(f"  [SKILL] 技能連段選擇性按下技能鍵: {key} (發送到遊戲窗口)")
                        else:
                            # 如果無法映射鍵碼，回退到全局按鍵
                            pyautogui.press(key.lower())
                            self.add_status_message(self.get_text("combo_skill_execution").format(
                                index=i+1, skill=key, type=self.get_text("normal_attack"), method=self.get_text("global_send")), "warning")
                            print(f"  [SKILL] 技能連段全局按下技能鍵: {key} (鍵碼映射失敗)")
                else:
                    # 如果無法獲取窗口句柄，回退到全局按鍵
                    if is_stationary:
                        pyautogui.keyDown('shift')
                        pyautogui.press(key.lower())
                        pyautogui.keyUp('shift')
                        self.add_status_message(self.get_text("combo_skill_execution").format(
                            index=i+1, skill=f"Shift+{key}", type=self.get_text("stationary_attack"), method=self.get_text("global_send")), "warning")
                        print(f"  原地攻擊模式: Shift+{key} (全局按鍵)")
                    else:
                        pyautogui.press(key.lower())
                        self.add_status_message(self.get_text("combo_skill_execution").format(
                            index=i+1, skill=key, type=self.get_text("normal_attack"), method=self.get_text("global_send")), "warning")
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
                        self.add_status_message(self.get_text("combo_skill_delay").format(delay=delay_ms), "info")
                        time.sleep(delay)
                        print(f"  延遲: {delay_ms}ms")
                except (ValueError, TypeError):
                    # 如果延遲時間無效，跳過延遲
                    pass

        print(f"連段套組 {set_index + 1} 執行完成")
        
        # 詳細的完成訊息
        self.add_status_message(self.get_text("combo_completed").format(
            set=set_index + 1, key=trigger_key, count=len(valid_keys)), "success")

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
            
            # 儲存技能計時器設定
            if hasattr(self, 'skill_timer'):
                existing_config['skill_timer'] = self.skill_timer.get_config()

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

            # 載入技能計時器設定
            if hasattr(self, 'skill_timer') and 'skill_timer' in config:
                self.skill_timer.load_config(config['skill_timer'])

            messagebox.showinfo("成功", "連段設定已載入")
            print("連段設定已載入")
            
        except Exception as e:
            messagebox.showerror("錯誤", f"載入連段設定失敗: {str(e)}")
            print(f"載入連段設定失敗: {e}")

    def check_for_updates(self):
        """檢查GitHub上的最新版本"""
        def _check():
            try:
                self.latest_version_var.set(self.get_text("checking_version"))
                self.version_status_var.set(self.get_text("connecting_github"))
                
                # 發送請求到GitHub API
                response = requests.get(GITHUB_API_URL, timeout=10)
                
                if response.status_code == 200:
                    release_data = response.json()
                    latest_version = release_data.get('tag_name', 'unknown')
                    release_body = release_data.get('body', self.get_text("no_update_notes"))
                    download_url = release_data.get('html_url', '')
                    
                    # 更新UI顯示
                    self.latest_version_var.set(latest_version)
                    self.download_url = download_url
                    
                    # 版本比較
                    if self.compare_versions(CURRENT_VERSION, latest_version):
                        self.version_status_var.set(self.get_text("new_version_found"))
                        self.latest_version_label.config(foreground='red')
                        self.download_btn.config(state='normal')
                    else:
                        self.version_status_var.set(self.get_text("using_latest_version"))
                        self.latest_version_label.config(foreground='green')
                        self.download_btn.config(state='disabled')
                    
                    # 顯示更新說明
                    if release_body and release_body != self.get_text("no_update_notes"):
                        self.update_release_notes_display(release_body)
                    
                else:
                    self.latest_version_var.set(self.get_text("check_failed"))
                    self.version_status_var.set(self.get_text("check_failed_http").format(status_code=response.status_code))
                    self.latest_version_label.config(foreground='red')
                    
            except requests.exceptions.Timeout:
                self.latest_version_var.set(self.get_text("connection_timeout"))
                self.version_status_var.set(self.get_text("github_timeout"))
                self.latest_version_label.config(foreground='red')
            except requests.exceptions.ConnectionError:
                self.latest_version_var.set(self.get_text("connection_failed"))
                self.version_status_var.set(self.get_text("github_connection_failed"))
                self.latest_version_label.config(foreground='red')
            except Exception as e:
                self.latest_version_var.set(self.get_text("check_error"))
                self.version_status_var.set(self.get_text("check_error_with_message").format(error=str(e)))
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
            messagebox.showerror(self.get_text("download_page_error_title"), 
                               self.get_text("download_page_error_message").format(error=e))

    def test_github_connection(self):
        """測試GitHub連接"""
        def _test():
            try:
                self.version_status_var.set(self.get_text("testing_connection"))
                response = requests.get("https://api.github.com", timeout=5)
                if response.status_code == 200:
                    self.version_status_var.set(self.get_text("github_connection_ok"))
                else:
                    self.version_status_var.set(self.get_text("github_connection_warning").format(status_code=response.status_code))
            except Exception as e:
                self.version_status_var.set(self.get_text("connection_test_failed").format(error=str(e)))
        
        threading.Thread(target=_test, daemon=True).start()

    def format_release_notes(self, markdown_text):
        """將Markdown格式的更新說明轉換為易讀的純文本格式"""
        if not markdown_text or markdown_text == self.get_text("no_update_notes"):
            return self.get_text("no_update_notes")

        import re

        # 移除代碼塊標記
        text = re.sub(r'```[\s\S]*?```', '', markdown_text)

        # 轉換標題
        text = re.sub(r'^### (.*)$', r'● \1', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.*)$', r'◆ \1', text, flags=re.MULTILINE)
        text = re.sub(r'^# (.*)$', r'■ \1', text, flags=re.MULTILINE)

        # 轉換列表項目
        text = re.sub(r'^\* (.*)$', r'• \1', text, flags=re.MULTILINE)
        text = re.sub(r'^- (.*)$', r'• \1', text, flags=re.MULTILINE)
        text = re.sub(r'^\d+\. (.*)$', r'➤ \1', text, flags=re.MULTILINE)

        # 移除連結語法，保留文字
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

        # 移除粗體和斜體標記
        text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^\*]+)\*', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)

        # 移除多餘的空行
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)

        # 限制長度，避免過長
        if len(text) > 800:
            text = text[:800] + "..."

        return text.strip()

    def update_release_notes_display(self, release_body):
        """更新更新說明的顯示"""
        formatted_notes = self.format_release_notes(release_body)

        # 啟用Text widget進行編輯
        self.release_notes_text.config(state='normal')
        self.release_notes_text.delete(1.0, tk.END)
        self.release_notes_text.insert(1.0, formatted_notes)
        self.release_notes_text.config(state='disabled')

    def silent_version_check(self):
        self._silent_version_check_after_id = None
        if self._is_closing:
            return

        """靜默檢查版本，更新UI顯示並在有新版本時彈出提醒"""
        def _silent_check():
            try:
                # 發送請求到GitHub API
                response = requests.get(GITHUB_API_URL, timeout=10)

                if response.status_code == 200:
                    release_data = response.json()
                    latest_version = release_data.get('tag_name', 'unknown')
                    release_body = release_data.get('body', self.get_text("no_update_notes"))
                    download_url = release_data.get('html_url', '')

                    # 在主線程中更新UI
                    def update_ui():
                        try:
                            self.latest_version_var.set(latest_version)
                            self.download_url = download_url

                            # 版本比較
                            if self.compare_versions(CURRENT_VERSION, latest_version):
                                self.version_status_var.set(self.get_text("new_version_found"))
                                self.latest_version_label.config(foreground='red')
                                self.download_btn.config(state='normal')
                                # 彈出更新提醒
                                self.show_update_notification(latest_version, release_body, download_url)
                            else:
                                self.version_status_var.set(self.get_text("using_latest_version"))
                                self.latest_version_label.config(foreground='green')
                                self.download_btn.config(state='disabled')

                            # 顯示更新說明
                            if release_body and release_body != self.get_text("no_update_notes"):
                                self.update_release_notes_display(release_body)

                        except Exception as e:
                            print(f"UI更新失敗: {e}")

                    self.schedule_ui_callback(update_ui)

                else:
                    # 連接失敗時的UI更新
                    def update_error_ui():
                        try:
                            self.latest_version_var.set(self.get_text("check_failed"))
                            self.version_status_var.set(self.get_text("check_failed_http").format(status_code=response.status_code))
                            self.latest_version_label.config(foreground='red')
                        except Exception as e:
                            print(f"錯誤UI更新失敗: {e}")

                    self.schedule_ui_callback(update_error_ui)

            except requests.exceptions.Timeout:
                def update_timeout_ui():
                    try:
                        self.latest_version_var.set(self.get_text("connection_timeout"))
                        self.version_status_var.set(self.get_text("github_timeout"))
                        self.latest_version_label.config(foreground='red')
                    except Exception as e:
                        print(f"超時UI更新失敗: {e}")

                self.schedule_ui_callback(update_timeout_ui)

            except requests.exceptions.ConnectionError:
                def update_connection_ui():
                    try:
                        self.latest_version_var.set(self.get_text("connection_failed"))
                        self.version_status_var.set(self.get_text("github_connection_failed"))
                        self.latest_version_label.config(foreground='red')
                    except Exception as e:
                        print(f"連接UI更新失敗: {e}")

                self.schedule_ui_callback(update_connection_ui)

            except Exception as e:
                _err_msg = str(e)
                def update_exception_ui():
                    try:
                        self.latest_version_var.set(self.get_text("check_error"))
                        self.version_status_var.set(self.get_text("check_error_with_message").format(error=_err_msg))
                        self.latest_version_label.config(foreground='red')
                    except Exception as e2:
                        print(f"異常UI更新失敗: {e2}")

                self.schedule_ui_callback(update_exception_ui)

        # 在後台線程中執行檢查
        threading.Thread(target=_silent_check, daemon=True).start()

    def show_update_notification(self, latest_version, release_body, download_url):
        """顯示更新通知視窗"""
        # 創建更新通知視窗
        update_window = tk.Toplevel(self.root)
        update_window.title(self.get_text("new_version_found_title"))
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
        
        ttk.Label(title_frame, text=self.get_text("new_version_found_title_2"), 
                 font=('Arial', 16, 'bold'), foreground='green').pack()
        
        # 版本資訊
        info_frame = ttk.LabelFrame(update_window, text=self.get_text("version_information"), padding="15")
        info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        ttk.Label(info_frame, text=self.get_text("current_version_display").format(version=CURRENT_VERSION), 
                 font=('Arial', 10)).pack(anchor=tk.W, pady=(0, 5))
        ttk.Label(info_frame, text=self.get_text("latest_version_display").format(version=latest_version), 
                 font=('Arial', 10, 'bold'), foreground='red').pack(anchor=tk.W, pady=(0, 10))
        
        # 更新說明
        if release_body and release_body != self.get_text("no_update_notes"):
            ttk.Label(info_frame, text=self.get_text("update_notes_label"), font=('Arial', 10, 'bold')).pack(anchor=tk.W)
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
                messagebox.showerror(self.get_text("download_page_error_title"), 
                                   self.get_text("download_page_error_message").format(error=e))
        
        def switch_to_version_tab():
            # 切換到版本檢查分頁並更新資訊
            self.notebook.select(self.version_frame)
            self.latest_version_var.set(latest_version)
            self.version_status_var.set(self.get_text("new_version_found"))
            self.update_release_notes_display(release_body)
            self.latest_version_label.config(foreground='red')
            self.download_btn.config(state='normal')
            self.download_url = download_url
            update_window.destroy()
        
        # 按鈕
        ttk.Button(button_frame, text=self.get_text("download_now_button"), 
                  command=open_download).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text=self.get_text("view_details_button"), 
                  command=switch_to_version_tab).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text=self.get_text("remind_later_button"), 
                  command=update_window.destroy).pack(side=tk.RIGHT)

    def create_about_tab(self):
        """創建關於分頁 - 現代化卡片式設計"""
        main_frame = self.about_frame

        # 創建可滾動框架
        canvas = tk.Canvas(main_frame, bg='#f8f9fa', highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='Card.TFrame')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 打包canvas和滾動條
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 主標題區域 - 現代化設計
        header_frame = ttk.Frame(scrollable_frame, style='Card.TFrame')
        header_frame.pack(fill="x", padx=20, pady=(20, 10))

        title_label = ttk.Label(header_frame, text=self.get_text("about_title"),
                               font=("Microsoft YaHei", 24, "bold"), foreground='#2c3e50')
        title_label.pack(pady=(10, 5))

        subtitle_label = ttk.Label(header_frame, text=self.get_text("about_subtitle"),
                                  font=("Microsoft YaHei", 12), foreground='#7f8c8d')
        subtitle_label.pack(pady=(0, 10))

        # 主要內容區域 - 使用網格佈局充分利用空間
        content_frame = ttk.Frame(scrollable_frame, style='Card.TFrame')
        content_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # 左側：軟體資訊
        left_frame = ttk.Frame(content_frame)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))

        # 軟體資訊卡片
        info_card = ttk.LabelFrame(left_frame, text=self.get_text("software_info"), padding="20")
        info_card.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(info_card, text=self.get_text("version_display").format(version=CURRENT_VERSION),
                 font=('Microsoft YaHei', 14, 'bold')).pack(anchor=tk.W, pady=(0, 8))
        ttk.Label(info_card, text=self.get_text("status_display"),
                 font=('Microsoft YaHei', 12), foreground='#27ae60').pack(anchor=tk.W, pady=(0, 8))
        
        # 使用時間顯示
        usage_time_text = format_usage_time(self.total_usage_time)
        self.usage_time_label = ttk.Label(info_card, text=self.get_text("total_usage_time").format(time=usage_time_text),
                                         font=('Microsoft YaHei', 12), foreground='#1976D2')
        self.usage_time_label.pack(anchor=tk.W, pady=(0, 8))
        
        ttk.Label(info_card, text=self.get_text("license_display"),
                 font=('Microsoft YaHei', 12)).pack(anchor=tk.W)

        # 官方連結卡片
        links_card = ttk.LabelFrame(left_frame, text=self.get_text("official_links"), padding="20")
        links_card.pack(fill=tk.X, pady=(10, 0))

        # 連結按鈕 - 2x2網格佈局
        links_grid = ttk.Frame(links_card)
        links_grid.pack(fill=tk.X)

        # 第一行：GitHub 和 Discord
        row1_frame = ttk.Frame(links_grid)
        row1_frame.pack(fill=tk.X, pady=(0, 8))

        # GitHub 按鈕
        def open_github():
            try:
                import webbrowser
                webbrowser.open("https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor")
            except Exception as e:
                messagebox.showerror("錯誤", f"無法打開 GitHub 頁面: {e}")

        github_btn = ttk.Button(row1_frame, text=self.get_text("github_button"), command=open_github, width=12)
        github_btn.pack(side=tk.LEFT, padx=(0, 8))

        # Discord 按鈕（暫無連結）
        def discord_placeholder():
            messagebox.showinfo("提示", self.get_text("discord_placeholder_message"))

        discord_btn = ttk.Button(row1_frame, text=self.get_text("discord_button"), command=discord_placeholder,
                                state='disabled', width=12)
        discord_btn.pack(side=tk.LEFT)

        # 第二行：Sid工具箱
        row2_frame = ttk.Frame(links_grid)
        row2_frame.pack(fill=tk.X)

        # Sid流亡工具箱按鈕
        def open_sid_toolbox():
            try:
                import webbrowser
                webbrowser.open("https://lelive.weebly.com/")
            except Exception as e:
                messagebox.showerror("錯誤", f"無法打開 Sid流亡工具箱 頁面: {e}")

        sid_btn = ttk.Button(row2_frame, text=self.get_text("sid_toolbox_button"), command=open_sid_toolbox, width=12)
        sid_btn.pack(side=tk.LEFT)

        # 右側：支持開發者
        right_frame = ttk.Frame(content_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))

        # 支持卡片
        support_card = ttk.LabelFrame(right_frame, text=self.get_text("support_developer"), padding="20")
        support_card.pack(fill=tk.BOTH, expand=True)

        support_text = ttk.Label(support_card,
                                text=self.get_text("support_text"),
                                font=('Microsoft YaHei', 12), foreground='#2E7D32',
                                justify=tk.CENTER)
        support_text.pack(pady=(0, 15))

        # 贊助按鈕 - 水平排列
        sponsor_frame = ttk.Frame(support_card)
        sponsor_frame.pack(fill=tk.X)

        # ECPay 按鈕
        def open_ecpay():
            try:
                import webbrowser
                webbrowser.open("https://p.ecpay.com.tw/E0E3A")
            except Exception as e:
                messagebox.showerror("錯誤", f"無法打開ECPay頁面: {e}")

        ecpay_btn = ttk.Button(sponsor_frame, text=self.get_text("ecpay_button"), command=open_ecpay)
        ecpay_btn.pack(side=tk.LEFT, padx=(0, 8), expand=True, fill=tk.X)

        # PayPal 按鈕
        def open_paypal():
            try:
                import webbrowser
                webbrowser.open("https://www.paypal.com/ncp/payment/GJS4D5VTSVWG4")
            except Exception as e:
                messagebox.showerror("錯誤", f"無法打開PayPal頁面: {e}")

        paypal_btn = ttk.Button(sponsor_frame, text=self.get_text("paypal_button"), command=open_paypal)
        paypal_btn.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # 底部免責聲明 - 全寬
        disclaimer_frame = ttk.LabelFrame(scrollable_frame, text=self.get_text("important_disclaimer"), padding="20")
        disclaimer_frame.pack(fill=tk.X, padx=20, pady=(0, 20))

        disclaimer_text = self.get_text("disclaimer_text")

        disclaimer_label = ttk.Label(disclaimer_frame, text=disclaimer_text,
                                   wraplength=800, font=('Microsoft YaHei', 11),
                                   justify=tk.LEFT, foreground='#d32f2f')
        disclaimer_label.pack(anchor=tk.W)

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
            print("應用程式正在關閉，保存使用時間...")
            self.track_usage_time()
            print("使用時間已保存")
        except Exception as e:
            print(f"保存使用時間時發生錯誤: {e}")

        # 停止技能計時器
        if hasattr(self, 'skill_timer'):
            self.skill_timer.stop_all()

        self.close_app()

    def update_usage_time_display(self):
        """更新使用時間顯示"""
        try:
            if hasattr(self, 'usage_time_label'):
                usage_time_text = format_usage_time(self.total_usage_time)
                self.usage_time_label.config(text=self.get_text("total_usage_time").format(time=usage_time_text))
        except Exception as e:
            print(f"更新使用時間顯示時發生錯誤: {e}")

    def update_usage_time_periodically(self):
        if self._is_closing:
            self._usage_time_after_id = None
            return

        """定期更新使用時間顯示"""
        try:
            # 更新顯示
            self.update_usage_time_display()

            # 每分鐘再次調度
            self._usage_time_after_id = self.root.after(60000, self.update_usage_time_periodically)
        except Exception as e:
            print(f"定期更新使用時間時發生錯誤: {e}")

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
        except:
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
        except:
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

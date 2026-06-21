import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import os
import json
import numpy as np
import pyautogui
from PIL import Image, ImageTk, ImageDraw
import cv2
import keyboard
import pygetwindow as gw
import win32gui
from utils import Tooltip, format_usage_time, get_app_dir
from image_utils import resize_and_center_image, get_interface_ui_region_text
from inventory_utils import calculate_inventory_grid_positions, should_clear_inventory, find_inventory_items
from capture_utils import _mss_singleton, capture_region_to_cv2
from custom_dialogs import CustomMessageBox


class InventoryTab:
    def __init__(self, app, state, inventory_frame=None):
        self._app = app
        self._state = state
        self._preview_has_image = False
        self._preview_meta = None
        self._preview_placeholder = None
        self._inventory_click_mode = "exclude"
        self.excluded_inventory_slots = set()
        self.grid_offset_x = 0
        self.grid_offset_y = 0
        self.inventory_region = None
        self.inventory_ui_region = None
        self.empty_inventory_colors = []
        self.occupied_threshold = 50
        self.last_inventory_window = None
        self.last_inventory_ui_window = None
        self.last_interface_ui_window = None
        self.pickup_coordinates = None
        self.continuous_setup_running = False
        self.occupied_slots_cache = set()
        self.original_min_size = (800, 600)
        self.inventory_window_var = tk.StringVar(value='')
        self.inventory_clear_click_mode = tk.StringVar(value="left")
        self.inventory_frame = inventory_frame
        self.inventory_clear_btn = None
        self.pickup_items_btn = None
        self.inventory_ui_screenshot = None
        self.interface_ui_screenshot = None
        self.create_inventory_tab()

    def update_inventory_tab_language(self):
        """更新一鍵清包分頁的語言"""
        try:
            # 更新LabelFrame標題
            if hasattr(self, 'inventory_frame'):
                for child in self.inventory_frame.winfo_children():
                    if isinstance(child, ttk.LabelFrame):
                        text = child.cget('text')
                        if text == "背包設定" or text == "Inventory Settings":
                            child.config(text=self._app.get_text("inventory_settings"))
                        elif text == "控制面板" or text == "Control Panel":
                            child.config(text=self._app.get_text("control_panel"))
                        elif text == "狀態" or text == "Status":
                            child.config(text=self._app.get_text("status"))
                        elif text == "F6取物座標" or text == "F6 Pickup Coordinates":
                            child.config(text=self._app.get_text("pickup_coordinates"))
                        elif text == "背包UI截圖" or text == "Inventory UI Screenshot":
                            child.config(text=self._app.get_text("inventory_ui_screenshot"))
                        elif text == "背包預覽" or text == "Inventory Preview":
                            child.config(text=self._app.get_text("inventory_preview"))

            # 更新按鈕文字
            if hasattr(self, 'select_inventory_region_btn'):
                self.select_inventory_region_btn.config(text=self._app.get_text("select_inventory_region"))
            if hasattr(self, 'record_empty_color_btn'):
                self.record_empty_color_btn.config(text=self._app.get_text("record_empty_color"))
            if hasattr(self, 'select_inventory_ui_btn'):
                self.select_inventory_ui_btn.config(text=self._app.get_text("select_inventory_ui"))
            if hasattr(self, 'test_clear_inventory_btn'):
                self.test_clear_inventory_btn.config(text=self._app.get_text("test_clear_inventory"))
            if hasattr(self, 'save_inventory_settings_btn'):
                self.save_inventory_settings_btn.config(text=self._app.get_text("save_inventory_settings"))
            if hasattr(self, 'setup_pickup_coordinates_btn'):
                self.setup_pickup_coordinates_btn.config(text=self._app.get_text("setup_pickup_coordinates"))
            if hasattr(self, 'save_pickup_coordinates_btn'):
                self.save_pickup_coordinates_btn.config(text=self._app.get_text("save_coordinates"))

            # 更新標籤文字
            if hasattr(self, 'record_status_label'):
                self.record_status_label.config(text=self._app.get_text("record_status"))
            if hasattr(self, 'inventory_ui_status_label'):
                self.inventory_ui_status_label.config(text=self._app.get_text("inventory_ui_status"))
            if hasattr(self, 'inventory_f3_label'):
                self.inventory_f3_label.config(text=self._app.get_text("f3_hotkey"))
            if hasattr(self, 'pause_status_label_title'):
                self.pause_status_label_title.config(text=self._app.get_text("global_pause"))
            if hasattr(self, 'coordinates_set_label'):
                self.coordinates_set_label.config(text=self._app.get_text("coordinates_set"))
            if hasattr(self, 'pickup_f6_label'):
                self.pickup_f6_label.config(text=self._app.get_text("f6_hotkey"))
            if hasattr(self, 'occupied_label_title'):
                self.occupied_label_title.config(text=self._app.get_text("occupied_slots"))
            if hasattr(self, 'grid_adjustment_label'):
                self.grid_adjustment_label.config(text=self._app.get_text("grid_alignment_adjustment"))
            if hasattr(self, 'horizontal_label'):
                self.horizontal_label.config(text=self._app.get_text("horizontal"))
            if hasattr(self, 'vertical_label'):
                self.vertical_label.config(text=self._app.get_text("vertical"))

            # 更新重置按鈕
            if hasattr(self, 'reset_offset_btn'):
                self.reset_offset_btn.config(text=self._app.get_text("reset"))

            # 更新說明文字
            if hasattr(self, 'ui_preview_hint_label'):
                self.ui_preview_hint_label.config(text=self._app.get_text("inventory_ui_screenshot_hint"))

            # 更新預覽標籤的初始文字
            if hasattr(self, 'inventory_preview_label') and not getattr(self, '_preview_has_image', False):
                self.inventory_preview_label.itemconfig(self._preview_placeholder, text=self._app.get_text("select_inventory_region_first"))

            # 更新舊的按鈕引用（向後相容）
            if hasattr(self, 'inventory_clear_btn'):
                self.inventory_clear_btn.config(text=self._app.get_text("clear_inventory"))
            if hasattr(self, 'pickup_items_btn'):
                self.pickup_items_btn.config(text=self._app.get_text("pickup_items"))

        except Exception as e:
            print(f"更新一鍵清包分頁語言時發生錯誤: {e}")

    def setup_global_esc_listener_for_inventory(self):
        """設置背包UI選擇的全局ESC鍵監聽"""
        try:
            if not hasattr(self._app, 'global_esc_active_inventory') or not self._app.global_esc_active_inventory:
                keyboard.add_hotkey('esc', self.global_esc_handler_for_inventory)
                self._app.global_esc_active_inventory = True
                print("已設置背包UI選擇的全局ESC監聽")
        except Exception as e:
            print(f"設置背包UI選擇的全局ESC監聽失敗: {e}")

    def remove_global_esc_listener_for_inventory(self):
        """移除背包相關選擇的全局ESC鍵監聽"""
        try:
            if hasattr(self._app, 'global_esc_active_inventory') and self._app.global_esc_active_inventory:
                # 檢查是否還有其他背包相關的選擇在進行中
                inventory_ui_active = getattr(self, 'inventory_ui_selection_active', False)
                inventory_active = getattr(self, 'inventory_selection_active', False)

                # 只有在沒有任何背包相關選擇活動時才移除監聽
                if not inventory_ui_active and not inventory_active:
                    keyboard.remove_hotkey('esc')
                    self._app.global_esc_active_inventory = False
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
                self._app.root.after(0, lambda: self.cancel_inventory_ui_selection(None))
                print("檢測到ESC鍵，取消背包UI選擇")
                return

            # 檢查背包區域選擇
            if hasattr(self, 'inventory_selection_active') and self.inventory_selection_active:
                # 使用tkinter的after方法來確保在主線程中執行
                self._app.root.after(0, lambda: self.cancel_inventory_selection(None))
                print("檢測到ESC鍵，取消背包區域選擇")
                return
        except Exception as e:
            print(f"背包相關選擇的全局ESC處理失敗: {e}")

    def setup_global_esc_listener_for_interface(self):
        """設置介面UI選擇的全局ESC鍵監聽"""
        try:
            if not hasattr(self._app, 'global_esc_active_interface') or not self._app.global_esc_active_interface:
                keyboard.add_hotkey('esc', self.global_esc_handler_for_interface)
                self._app.global_esc_active_interface = True
                print("已設置介面UI選擇的全局ESC監聽")
        except Exception as e:
            print(f"設置介面UI選擇的全局ESC監聽失敗: {e}")

    def remove_global_esc_listener_for_interface(self):
        """移除介面UI選擇的全局ESC鍵監聽"""
        try:
            if hasattr(self._app, 'global_esc_active_interface') and self._app.global_esc_active_interface:
                keyboard.remove_hotkey('esc')
                self._app.global_esc_active_interface = False
                print("已移除介面UI選擇的全局ESC監聽")
        except Exception as e:
            print(f"移除介面UI選擇的全局ESC監聽失敗: {e}")

    def global_esc_handler_for_interface(self):
        """介面UI選擇的全局ESC鍵處理函數"""
        try:
            if hasattr(self, 'interface_ui_selection_active') and self.interface_ui_selection_active:
                # 使用tkinter的after方法來確保在主線程中執行
                self._app.root.after(0, lambda: self.cancel_interface_ui_selection(None))
                print("檢測到ESC鍵，取消介面UI選擇")
        except Exception as e:
            print(f"介面UI選擇的全局ESC處理失敗: {e}")

    def quick_clear_inventory(self):
        """F3快速清包功能（非阻塞版）- 比照F6的視窗管理策略"""
        # 全域暫停檢查
        if self._state.global_pause:
            print("[STOP] 全域暫停中，跳過F3熱鍵")
            try:
                self._app.root.after(0, lambda: self._app.status_tab.add_status_message("按下 F3 - 因全域暫停模式而跳過執行", "warning"))
            except Exception:
                pass
            return

        # 重置中斷標誌
        self._state.inventory_clear_interrupt = False

        try:
            self._app.root.after(0, lambda: self._app.status_tab.add_status_message(self._app.get_text("f3_hotkey_pressed"), "hotkey"))
        except Exception:
            pass

        if not self.inventory_region or not self.empty_inventory_colors:
            try:
                self._app.root.after(0, lambda: self._app.status_tab.add_status_message(self._app.get_text("f3_fail_inventory_incomplete"), "error"))
                self._app.root.after(0, lambda: messagebox.showwarning(self._app.get_text("f3_inventory_reminder"), self._app.get_text("inventory_setup_incomplete")))
            except Exception:
                pass
            return

        if not self.inventory_ui_region or self.inventory_ui_screenshot is None:
            try:
                self._app.root.after(0, lambda: self._app.status_tab.add_status_message(self._app.get_text("f3_fail_inventory_ui_not_set"), "error"))
                self._app.root.after(0, lambda: messagebox.showwarning(self._app.get_text("f3_inventory_reminder"), self._app.get_text("inventory_ui_screenshot_not_set")))
            except Exception:
                pass
            return

        window_title = self._app.monitor_tab.window_var.get()
        if not window_title:
            try:
                self._app.root.after(0, lambda: self._app.status_tab.add_status_message(self._app.get_text("f3_fail_game_window_not_set"), "error"))
                self._app.root.after(0, lambda: messagebox.showwarning("F3 清包提醒", "未設定遊戲視窗！\n\n請先在「血量監控」分頁選擇遊戲視窗。"))
            except Exception:
                pass
            return

        # 前台檢查改為警告而非強制取消（與F6一致）
        if not self._app.window_key_sender.is_game_window_foreground(window_title):
            try:
                self._app.root.after(0, lambda: self._app.status_tab.add_status_message(self._app.get_text("f3_cancel_game_not_foreground"), "warning"))
            except Exception:
                pass
            print(f"F3: 遊戲視窗 '{window_title}' 不在前台，將嘗試激活")

        # 捕獲GUI狀態
        gui_was_visible = (self._app.root.state() == 'normal')
        gui_was_foreground = False
        gui_was_topmost = self._app.should_keep_topmost()
        if gui_was_visible:
            try:
                foreground_hwnd = win32gui.GetForegroundWindow()
                gui_hwnd = self._app.root.winfo_id()
                gui_was_foreground = (foreground_hwnd == gui_hwnd)
            except Exception:
                gui_was_foreground = False

        print(f"F3: GUI視窗狀態 - 原本{'顯示' if gui_was_visible else '最小化'}，{'在前台' if gui_was_foreground else '在後台'}，{'保持在最上方' if gui_was_topmost else '不保持在最上方'}")

        # 如果GUI在前台或保持在最上方，移到後台
        if gui_was_foreground or gui_was_topmost:
            def _prepare_gui():
                try:
                    if gui_was_topmost:
                        self._app.root.attributes("-topmost", False)
                        print("F3: 已取消 GUI 置頂設定")
                    getattr(self._app.root, 'lower', lambda: None)()
                    print("F3: 已將 GUI 移到後台")
                except Exception as e:
                    print(f"F3: 準備 GUI 失敗: {e}")
            try:
                self._app.root.after(0, _prepare_gui)
            except Exception as e:
                print(f"F3: 安排準備 GUI 失敗: {e}")

        # 隱藏設定視窗
        def _hide_setting_windows():
            try:
                for w in self._app.root.winfo_children():
                    try:
                        if w.winfo_exists() and hasattr(w, 'title'):
                            t = str(w.title())
                            if ('F3' in t or '清包' in t or '設定' in t or 'setup' in t.lower()) and w.winfo_ismapped():
                                try:
                                    try:
                                        if hasattr(w, 'grab_release'):
                                            w.grab_release()
                                            print(f"F3: 已釋放設定視窗的 grab: {t}")
                                    except Exception:
                                        pass
                                    try:
                                        if hasattr(self._app.root, 'grab_release'):
                                            self._app.root.grab_release()
                                            print("F3: 已釋放 root 的 grab（備援）")
                                    except Exception:
                                        pass
                                    w.withdraw()
                                    print(f"F3: 隱藏設定視窗: {t}")
                                except Exception as e:
                                    print(f"F3: 隱藏設定視窗失敗 {t}: {e}")
                    except Exception:
                        pass
            except Exception as e:
                print(f"F3: 隱藏設定視窗時發生錯誤: {e}")
        try:
            self._app.root.after(0, _hide_setting_windows)
        except Exception:
            pass

        # 啟動背景執行緒執行清包
        def _worker(window_title_local, gui_was_foreground_local, gui_was_topmost_local):
            try:
                windows = gw.getWindowsWithTitle(window_title_local)
                if not windows:
                    print("F3(worker): 找不到遊戲視窗")
                    try:
                        self._app.root.after(0, lambda: self._app.status_tab.add_status_message(self._app.get_text("f3_fail_game_window_not_found"), "error"))
                    except Exception:
                        pass
                    return

                game_window = windows[0]
                print(f"F3(worker): 找到遊戲視窗: {game_window.title}")

                # 激活遊戲視窗
                try:
                    game_window.activate()
                    time.sleep(0.5)
                except Exception as e:
                    print(f"F3(worker): 激活遊戲視窗失敗: {e}")

                if not self._app.window_key_sender.is_game_window_foreground(window_title_local):
                    print("F3(worker): 警告 - 遊戲視窗可能未在前台")
                    try:
                        pyautogui.click(game_window.left + game_window.width // 2,
                                      game_window.top + game_window.height // 2)
                        time.sleep(0.2)
                    except Exception:
                        pass

                # 檢查背包UI是否可見
                if not self.is_inventory_ui_visible(game_window):
                    print("F3(worker): 背包UI未開啟，跳過清包操作")
                    try:
                        self._app.root.after(0, lambda: self._app.status_tab.add_status_message(self._app.get_text("f3_cancel_inventory_not_open"), "warning"))
                    except Exception:
                        pass
                    return

                try:
                    self._app.root.after(0, lambda: self._app.status_tab.add_status_message(self._app.get_text("f3_processing_game_window_found"), "info"))
                except Exception:
                    pass

                # 擷取背包區域
                monitor = {
                    "top": game_window.top + self.inventory_region['y'],
                    "left": game_window.left + self.inventory_region['x'],
                    "width": self.inventory_region['width'],
                    "height": self.inventory_region['height']
                }
                img = capture_region_to_cv2(monitor)

                # 檢查是否需要清空
                needs_clearing, occupied_slots = should_clear_inventory(img, self.empty_inventory_colors, self.inventory_grid_positions, self.inventory_region, self.excluded_inventory_slots)
                if needs_clearing:
                    try:
                        self._app.root.after(0, lambda: self._app.status_tab.add_status_message(self._app.get_text("f3_processing_items_detected").format(count=len(occupied_slots)), "info"))
                    except Exception:
                        pass
                    print(f"F3(worker): 檢測到 {len(occupied_slots)} 個格子有物品，正在清空...")
                    self.clear_inventory_item(game_window, img)
                    if self._state.inventory_clear_interrupt:
                        try:
                            self._app.root.after(0, lambda: self._app.status_tab.add_status_message(self._app.get_text("f3_cancel_user_interrupt"), "warning"))
                        except Exception:
                            pass
                        print("F3(worker): 清包被中斷")
                    else:
                        try:
                            self._app.root.after(0, lambda: self._app.status_tab.add_status_message(self._app.get_text("f3_completed_inventory_cleared"), "success"))
                        except Exception:
                            pass
                        print("F3(worker): 已清空背包物品")
                else:
                    try:
                        self._app.root.after(0, lambda: self._app.status_tab.add_status_message("F3 執行完成 - 背包已為空狀態", "success"))
                    except Exception:
                        pass
                    print("F3(worker): 背包已淨空，無需操作")

            except Exception as e:
                _err_msg = str(e)
                print(f"F3(worker): 發生例外: {e}")
                try:
                    self._app.root.after(0, lambda: self._app.status_tab.add_status_message(f"F3 執行失敗 - {_err_msg}", "error"))
                except Exception:
                    pass
            finally:
                self._state.inventory_clear_interrupt = False
                def _restore_gui():
                    try:
                        if gui_was_foreground_local or gui_was_topmost_local:
                            try:
                                self._app.root.lift()
                                self._app.root.focus_force()
                                if gui_was_topmost_local:
                                    self._app.root.attributes("-topmost", True)
                                    print("F3(worker): 已恢復 GUI 到前台並重新置頂")
                                else:
                                    print("F3(worker): 已恢復 GUI 到前台")
                            except Exception as e:
                                print(f"F3(worker): 恢復 GUI 失敗: {e}")
                    except Exception as e:
                        print(f"F3(worker): Restore callback 例外: {e}")
                try:
                    self._app.root.after(0, _restore_gui)
                except Exception:
                    pass

        t = threading.Thread(target=_worker, args=(window_title, gui_was_foreground, gui_was_topmost), daemon=True)
        t.start()

    def check_gui_overlap_with_inventory(self, game_window):
        """檢查GUI是否會遮擋背包區域"""
        try:
            if not self.inventory_region:
                return False

            # 檢查GUI是否已經最小化，如果最小化則不會遮擋
            if self._app.root.state() == "iconic":
                return False

            # 獲取GUI當前位置和大小
            gui_x = self._app.root.winfo_x()
            gui_y = self._app.root.winfo_y()
            gui_width = self._app.root.winfo_width()
            gui_height = self._app.root.winfo_height()

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
            if self._app.root.state() == "iconic":
                return False

            # 獲取GUI當前位置和大小
            gui_x = self._app.root.winfo_x()
            gui_y = self._app.root.winfo_y()
            gui_width = self._app.root.winfo_width()
            gui_height = self._app.root.winfo_height()

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
            if self._state.gui_minimized_for_clear:
                return  # 已經縮小了

            # 記錄GUI當前狀態
            self._state.original_gui_geometry = self._app.root.geometry()
            self._state.original_gui_state = self._app.root.state()

            # 臨時移除最小尺寸限制，允許GUI縮小
            self.original_min_size = self._app.root.minsize()
            self._app.root.minsize(400, 350)  # 設置允許縮小到500x450的最小尺寸

            # 檢查GUI當前是否在前台
            try:
                import win32gui

                # 獲取當前前台視窗
                foreground_hwnd = win32gui.GetForegroundWindow()
                current_process_hwnd = win32gui.FindWindow(None, self._app.root.title())

                self._state.gui_was_foreground_before_minimize = (foreground_hwnd == current_process_hwnd)
                print(f"GUI縮小前是否在前台: {self._state.gui_was_foreground_before_minimize}")
            except ImportError:
                # 如果沒有win32gui，假設GUI在前台
                self._state.gui_was_foreground_before_minimize = True
                print("無法檢查GUI前台狀態，假設在前台")
            except Exception as e:
                print(f"檢查GUI前台狀態失敗: {e}")
                self._state.gui_was_foreground_before_minimize = True

            # 獲取螢幕尺寸
            screen_width = self._app.root.winfo_screenwidth()
            screen_height = self._app.root.winfo_screenheight()

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
            self._app.root.geometry(new_geometry)

            # 只有在用戶啟用了永遠在最上方時，才確保視窗在前台
            if self._app.should_keep_topmost():
                self._app.root.lift()
                self._app.root.focus_force()
                print("縮小GUI時保持前台狀態")
            else:
                print("縮小GUI時保持後台狀態")

            self._state.gui_minimized_for_clear = True
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
            if not self._state.gui_minimized_for_clear:
                return  # 沒有被縮小

            if self._state.original_gui_geometry:
                self._app.root.geometry(self._state.original_gui_geometry)

            if self._state.original_gui_state:
                self._app.root.state(self._state.original_gui_state)

            # 恢復原始的最小尺寸限制
            if hasattr(self, 'original_min_size') and self.original_min_size:
                self._app.root.minsize(self.original_min_size[0], self.original_min_size[1])

            # 只有在用戶啟用了永遠在最上方且GUI縮小前就在前台的情況下，才重新激活GUI
            if self._app.should_keep_topmost() and self._state.gui_was_foreground_before_minimize:
                self._app.root.lift()
                self._app.root.focus_force()
                print("GUI已恢復到原始狀態並重新激活")
            else:
                print("GUI已恢復到原始狀態，保持後台狀態")

            self._state.gui_minimized_for_clear = False
            self._state.original_gui_geometry = None
            self._state.original_gui_state = None
            self._state.gui_was_foreground_before_minimize = True  # 重置為預設值

        except Exception as e:
            print(f"恢復GUI時發生錯誤: {e}")

    def minimize_all_guis(self):
        """縮小所有GUI以避免干擾螢幕截圖操作"""
        try:
            # 簡單地將主GUI最小化
            self._app.root.iconify()
            print("GUI已縮小以避免干擾螢幕截圖")
        except Exception as e:
            print(f"縮小GUI時發生錯誤: {e}")

    def restore_all_guis(self):
        """恢復所有GUI到正常狀態"""
        try:
            # 恢復主GUI
            self._app.root.deiconify()
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
        inventory_frame = ttk.LabelFrame(left_frame, text=self._app.get_text("inventory_settings"), padding="15")
        inventory_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))

        # 框選背包區域
        self.select_inventory_region_btn = ttk.Button(inventory_frame, text=self._app.get_text("select_inventory_region"), command=self.select_inventory_region)
        self.select_inventory_region_btn.grid(row=0, column=0, pady=2)
        Tooltip(self.select_inventory_region_btn, self._app.get_text("select_inventory_region_tip"))
        self.record_empty_color_btn = ttk.Button(inventory_frame, text=self._app.get_text("record_empty_color"), command=self.record_empty_inventory_color)
        self.record_empty_color_btn.grid(row=0, column=1, padx=(10, 0), pady=2)
        Tooltip(self.record_empty_color_btn, self._app.get_text("record_empty_color_tip"))
        self.select_inventory_ui_btn = ttk.Button(inventory_frame, text=self._app.get_text("select_inventory_ui"), command=self.select_inventory_ui_region)
        self.select_inventory_ui_btn.grid(row=0, column=2, padx=(10, 0), pady=2)
        Tooltip(self.select_inventory_ui_btn, self._app.get_text("select_inventory_ui_tip"))

        # 顏色顯示
        self.record_status_label = ttk.Label(inventory_frame, text=self._app.get_text("record_status"))
        self.record_status_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        self.empty_color_label = ttk.Label(inventory_frame, text=self._app.get_text("not_recorded"), background="lightgray", relief="sunken")
        self.empty_color_label.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 0))

        # 背包UI顯示
        self.inventory_ui_status_label = ttk.Label(inventory_frame, text=self._app.get_text("inventory_ui_status"))
        self.inventory_ui_status_label.grid(row=2, column=0, sticky=tk.W, pady=2)
        self.inventory_ui_label = ttk.Label(inventory_frame, text=self._app.get_text("not_recorded"), background="lightgray", relief="sunken")
        self.inventory_ui_label.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 0))

        # 控制按鈕
        control_frame = ttk.LabelFrame(left_frame, text=self._app.get_text("control_panel"), padding="15")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))

        self.test_clear_inventory_btn = ttk.Button(control_frame, text=self._app.get_text("test_clear_inventory"), command=self.test_inventory_clearing)
        self.test_clear_inventory_btn.grid(row=0, column=0, pady=2)
        Tooltip(self.test_clear_inventory_btn, self._app.get_text("test_clear_inventory_tip"))
        self.save_inventory_settings_btn = ttk.Button(control_frame, text=self._app.get_text("save_inventory_settings"), command=self.save_inventory_config)
        self.save_inventory_settings_btn.grid(row=0, column=1, padx=(10, 0), pady=2)

        # 清包點擊模式選擇
        click_mode_frame = ttk.Frame(control_frame)
        click_mode_frame.grid(row=1, column=0, columnspan=2, pady=(5, 0), sticky=tk.W)

        ttk.Label(click_mode_frame, text=self._app.get_text("clear_click_mode")).grid(row=0, column=0, sticky=tk.W)
        self.inventory_clear_click_mode = tk.StringVar(value="left")

        left_rb = ttk.Radiobutton(click_mode_frame, text=self._app.get_text("clear_click_left"),
                                  variable=self.inventory_clear_click_mode, value="left",
                                  command=self._on_click_mode_changed)
        left_rb.grid(row=0, column=1, padx=(5, 10))
        Tooltip(left_rb, self._app.get_text("clear_click_left_tip"))

        right_rb = ttk.Radiobutton(click_mode_frame, text=self._app.get_text("clear_click_right"),
                                   variable=self.inventory_clear_click_mode, value="right",
                                   command=self._on_click_mode_changed)
        right_rb.grid(row=0, column=2, padx=(5, 10))
        Tooltip(right_rb, self._app.get_text("clear_click_right_tip"))

        # GUI設定選項
        gui_control_frame = ttk.Frame(control_frame)
        gui_control_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))

        ttk.Label(gui_control_frame, text=self._app.get_text("gui_settings")).grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(gui_control_frame, text=self._app.get_text("always_on_top"), variable=self._app.always_on_top_var,
                       command=self._app.toggle_always_on_top).grid(row=0, column=1, columnspan=2, sticky=tk.W, padx=(5, 0))

        # 狀態顯示
        status_frame = ttk.LabelFrame(left_frame, text=self._app.get_text("status"), padding="15")
        status_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))

        self.inventory_f3_label = ttk.Label(status_frame, text=self._app.get_text("f3_hotkey"))
        self.inventory_f3_label.grid(row=0, column=0, sticky=tk.W, pady=2)
        self.inventory_status_label = ttk.Label(status_frame, text=self._app.get_text("ready"), foreground="green")
        self.inventory_status_label.grid(row=0, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        self.pause_status_label_title = ttk.Label(status_frame, text=self._app.get_text("global_pause"))
        self.pause_status_label_title.grid(row=1, column=0, sticky=tk.W, pady=2)
        self.pause_status_label = ttk.Label(status_frame, text=self._app.get_text("normal_operation"), foreground="green")
        self.pause_status_label.grid(row=1, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        # F6取物座標設定
        pickup_frame = ttk.LabelFrame(left_frame, text=self._app.get_text("pickup_coordinates"), padding="10")
        pickup_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        # 座標設定按鈕
        self.setup_pickup_coordinates_btn = ttk.Button(pickup_frame, text=self._app.get_text("setup_pickup_coordinates"), command=self.setup_pickup_coordinates)
        self.setup_pickup_coordinates_btn.grid(row=0, column=0, pady=2)
        Tooltip(self.setup_pickup_coordinates_btn, self._app.get_text("setup_pickup_coordinates_tip"))
        self.save_pickup_coordinates_btn = ttk.Button(pickup_frame, text=self._app.get_text("save_coordinates"), command=self.save_pickup_coordinates)
        self.save_pickup_coordinates_btn.grid(row=0, column=1, padx=(10, 0), pady=2)

        # 座標狀態顯示
        self.coordinates_set_label = ttk.Label(pickup_frame, text=self._app.get_text("coordinates_set"))
        self.coordinates_set_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        self.pickup_coords_label = ttk.Label(pickup_frame, text=self._app.get_text("coordinates_count"), foreground="gray")
        self.pickup_coords_label.grid(row=1, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        # F6狀態顯示
        self.pickup_f6_label = ttk.Label(pickup_frame, text=self._app.get_text("f6_hotkey"))
        self.pickup_f6_label.grid(row=2, column=0, sticky=tk.W, pady=2)
        self.pickup_status_label = ttk.Label(pickup_frame, text=self._app.get_text("ready"), foreground="green")
        self.pickup_status_label.grid(row=2, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        # UI截圖顯示區域
        ui_preview_frame = ttk.LabelFrame(left_frame, text=self._app.get_text("inventory_ui_screenshot"), padding="10")
        ui_preview_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        # 創建一個Canvas來顯示UI截圖
        self.ui_preview_canvas = tk.Canvas(ui_preview_frame, width=200, height=150, bg='lightgray', relief='sunken')
        self.ui_preview_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E))

        # 添加說明文字
        self.ui_preview_hint_label = ttk.Label(ui_preview_frame, text=self._app.get_text("inventory_ui_screenshot_hint"),
                 font=("", 8), foreground="gray")
        self.ui_preview_hint_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))

        # === 右側區域：背包預覽 ===
        # 背包預覽區域
        preview_frame = ttk.LabelFrame(right_frame, text=self._app.get_text("inventory_preview"), padding="10")
        preview_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 統計資訊區域
        stats_frame = ttk.Frame(preview_frame)
        stats_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))

        self.occupied_label_title = ttk.Label(stats_frame, text=self._app.get_text("occupied_slots"))
        self.occupied_label_title.grid(row=0, column=0, sticky=tk.W)
        self.occupied_label = ttk.Label(stats_frame, text=self._app.get_text("slots_count"), foreground="blue", font=("", 10, "bold"))
        self.occupied_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        # 偏移調整區域
        offset_frame = ttk.Frame(preview_frame)
        offset_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))

        self.grid_adjustment_label = ttk.Label(offset_frame, text=self._app.get_text("grid_alignment_adjustment"))
        self.grid_adjustment_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 2))

        # 水平偏移調整
        self.horizontal_label = ttk.Label(offset_frame, text=self._app.get_text("horizontal"))
        self.horizontal_label.grid(row=1, column=0, sticky=tk.W)
        ttk.Button(offset_frame, text="◀", width=3, command=lambda: self.adjust_grid_offset(-1, 0)).grid(row=1, column=1, padx=(5, 2))
        self.offset_x_label = ttk.Label(offset_frame, text="0", width=4, relief="sunken")
        self.offset_x_label.grid(row=1, column=2, padx=(2, 2))
        ttk.Button(offset_frame, text="▶", width=3, command=lambda: self.adjust_grid_offset(1, 0)).grid(row=1, column=3, padx=(2, 10))

        # 垂直偏移調整
        self.vertical_label = ttk.Label(offset_frame, text=self._app.get_text("vertical"))
        self.vertical_label.grid(row=1, column=4, sticky=tk.W)
        ttk.Button(offset_frame, text="▲", width=3, command=lambda: self.adjust_grid_offset(0, -1)).grid(row=1, column=5, padx=(5, 2))
        self.offset_y_label = ttk.Label(offset_frame, text="0", width=4, relief="sunken")
        self.offset_y_label.grid(row=1, column=6, padx=(2, 2))
        ttk.Button(offset_frame, text="▼", width=3, command=lambda: self.adjust_grid_offset(0, 1)).grid(row=1, column=7, padx=(2, 5))

        self.reset_offset_btn = ttk.Button(offset_frame, text=self._app.get_text("reset"), command=self.reset_grid_offset)
        self.reset_offset_btn.grid(row=1, column=8, padx=(10, 0))

        self.inventory_preview_label = tk.Canvas(preview_frame, bg="lightgray", highlightthickness=0, relief="sunken", borderwidth=2, width=300, height=200)
        self.inventory_preview_label.grid(row=2, column=0, pady=(5, 0), sticky=(tk.N, tk.S, tk.W, tk.E))
        self._preview_placeholder = self.inventory_preview_label.create_text(10, 10, text=self._app.get_text("select_inventory_region_first"), anchor='nw', fill='gray')
        self.inventory_preview_label.bind('<Button-1>', self._on_preview_click)
        self.inventory_preview_label.bind('<Configure>', self._on_preview_resize)
        self._preview_has_image = False

        self.inventory_exclude_hint = ttk.Label(preview_frame, text=self._app.get_text("inventory_exclude_hint"), foreground="gray")
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
            self.inventory_grid_positions = calculate_inventory_grid_positions(self.inventory_region, self.grid_offset_x, self.grid_offset_y)

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
            self.inventory_grid_positions = calculate_inventory_grid_positions(self.inventory_region, self.grid_offset_x, self.grid_offset_y)

        # 如果有預覽圖片，立即更新
        if hasattr(self, 'inventory_preview_label') and getattr(self, '_preview_has_image', False):
            self.update_inventory_preview_from_current()

    def update_offset_labels(self):
        """更新偏移標籤顯示"""
        if hasattr(self, 'offset_x_label'):
            self.offset_x_label.config(text=str(self.grid_offset_x))
        if hasattr(self, 'offset_y_label'):
            self.offset_y_label.config(text=str(self.grid_offset_y))

    def update_inventory_preview_from_current(self):
        """從當前背包區域重新獲取圖片並更新預覽"""
        try:
            if not hasattr(self._app, 'window_key_sender') or not self._app.window_key_sender._is_game_window_visible():
                if hasattr(self, 'inventory_preview_label'):
                    self.inventory_preview_label.delete("all")
                    self._preview_placeholder = self.inventory_preview_label.create_text(10, 10, text=self._app.get_text("waiting_for_game_window"), anchor='nw', fill='gray')
                    self._preview_has_image = False
                return

            # 使用血魔監控的遊戲視窗
            window_title = self._app.monitor_tab.window_var.get()
            if not window_title:
                return

            # 獲取遊戲視窗
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                return

            game_window = windows[0]

            # 若已設定背包UI參考圖，檢查背包是否已開啟
            if self.inventory_ui_region and hasattr(self, 'inventory_ui_screenshot') and self.inventory_ui_screenshot is not None:
                if not self.check_inventory_ui_exists(game_window):
                    if hasattr(self, 'inventory_preview_label'):
                        self.inventory_preview_label.delete("all")
                        w = self.inventory_preview_label.winfo_width() or 300
                        h = self.inventory_preview_label.winfo_height() or 200
                        self.inventory_preview_label.create_text(
                            w // 2, h // 2,
                            text=self._app.get_text("waiting_inventory_open"),
                            anchor='center',
                            fill='gray',
                            font=('Microsoft JhengHei', 14)
                        )
                        self._preview_has_image = False
                    return
            elif self.inventory_ui_region and (not hasattr(self, 'inventory_ui_screenshot') or self.inventory_ui_screenshot is None):
                # 有設定區域但還沒截參考圖，提示使用者
                if hasattr(self, 'inventory_preview_label'):
                    self.inventory_preview_label.delete("all")
                    w = self.inventory_preview_label.winfo_width() or 300
                    h = self.inventory_preview_label.winfo_height() or 200
                    self.inventory_preview_label.create_text(
                        w // 2, h // 2,
                        text=self._app.get_text("inventory_ui_not_recorded"),
                        anchor='center',
                        fill='orange',
                        font=('Microsoft JhengHei', 14)
                    )
                    self._preview_has_image = False
                return

            monitor = {
                "top": game_window.top + self.inventory_region['y'],
                "left": game_window.left + self.inventory_region['x'],
                "width": self.inventory_region['width'],
                "height": self.inventory_region['height']
            }
            img = capture_region_to_cv2(monitor)

            # 分析背包狀態
            should_clear, occupied_slots = should_clear_inventory(img, self.empty_inventory_colors, self.inventory_grid_positions, self.inventory_region, self.excluded_inventory_slots)

            # 更新預覽
            self.update_inventory_preview_with_items(img, occupied_slots)

        except Exception as e:
            print(f"重新獲取預覽失敗: {e}")

    def select_inventory_region(self):
        """框選背包區域"""
        # 使用血魔監控的遊戲視窗
        window_title = self._app.monitor_tab.window_var.get()
        if not window_title:
            messagebox.showwarning(self._app.get_text("warning"), self._app.get_text("set_game_window_first"))
            return

        # 檢查遊戲視窗是否最小化
        if self._app.check_game_window_minimized(window_title):
            return

        try:
            # 獲取遊戲視窗
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                messagebox.showerror(self._app.get_text("error"), self._app.get_text("game_window_not_found"))
                return

            game_window = windows[0]

            # 縮小GUI視窗以避免干擾
            self._app.root.iconify()
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
            messagebox.showerror(self._app.get_text("error"), self._app.get_text("selection_failed").format(error=str(e)))
            # 確保GUI被恢復
            self._app.root.deiconify()

    def create_inventory_selection_window(self, game_window):
        """創建背包區域選擇視窗（參考血魔監控邏輯）"""
        # 創建覆蓋遊戲視窗的選擇視窗（參考血魔監控的邏輯）（子視窗 - 最高層級）
        self.inventory_selection_window = self._app.create_child_window("", f"{game_window.width}x{game_window.height}")
        self.inventory_selection_window.geometry(f"+{game_window.left}+{game_window.top}")
        self.inventory_selection_window.attributes("-alpha", 0.3)
        self.inventory_selection_window.overrideredirect(True)  # 移除視窗邊框
        self.inventory_selection_window.configure(bg='gray')

        # 繪製遊戲視窗邊框
        canvas = tk.Canvas(self.inventory_selection_window, bg='gray', highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        # 繪製說明文字
        self.selection_text_id = canvas.create_text(game_window.width//2, game_window.height//2,
                          text=self._app.get_text("drag_select_inventory_region"),
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
            window_title = self._app.monitor_tab.window_var.get()
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
                    self._app.root.deiconify()
                    self._app.root.attributes("-topmost", self._app.always_on_top_var.get())  # 恢復置頂（根據用戶設定）
                    self._app.root.lift()
                    self._app.root.focus_force()

                    # 顯示警告並恢復GUI
                    messagebox.showwarning(self._app.get_text("warning"), self._app.get_text("selection_too_small"))
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
                self._app.monitor_tab.finalize_selection_restore_gui("inventory_region_set", {
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
            self._app.root.deiconify()
            self._app.root.attributes("-topmost", self._app.always_on_top_var.get())  # 恢復置頂（根據用戶設定）
            self._app.root.lift()
            self._app.root.focus_force()
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
        self._app.monitor_tab.finalize_selection_restore_gui()

    def record_empty_inventory_color(self):
        """記錄淨空背包的60個格子顏色"""
        if not self.inventory_region:
            messagebox.showwarning(self._app.get_text("warning"), self._app.get_text("select_inventory_region_first"))
            return

        # 使用血魔監控的遊戲視窗
        window_title = self._app.monitor_tab.window_var.get()
        if not window_title:
            messagebox.showwarning(self._app.get_text("warning"), self._app.get_text("set_game_window_first"))
            return

        # 檢查遊戲視窗是否最小化
        if self._app.check_game_window_minimized(window_title):
            return

        try:
            # 縮小GUI並激活遊戲視窗，避免GUI遮擋
            self.minimize_all_guis()
            time.sleep(0.5)  # 等待GUI縮小

            # 獲取遊戲視窗
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                messagebox.showerror(self._app.get_text("error"), self._app.get_text("game_window_not_found"))
                return

            game_window = windows[0]

            # 激活遊戲視窗
            game_window.activate()
            time.sleep(0.5)  # 等待視窗激活
            print("已縮小GUI並激活遊戲視窗，準備記錄顏色")

            # 計算格子位置
            self.inventory_grid_positions = calculate_inventory_grid_positions(self.inventory_region, self.grid_offset_x, self.grid_offset_y)
            if not self.inventory_grid_positions:
                messagebox.showerror("錯誤", "無法計算格子位置")
                return

            # 擷取整個背包區域
            with _mss_singleton as sct:
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
                self.empty_color_label.config(text=self._app.get_text("recorded_colors_template").format(count=recorded_count), background="lightgreen")

                # 恢復主GUI視窗
                self.restore_all_guis()
                print("顏色記錄完成，已恢復GUI視窗")

                # 更新背包預覽畫面，讓使用者看到記錄效果
                self.update_inventory_preview_from_current()

                messagebox.showinfo(self._app.get_text("success"), self._app.get_text("empty_color_recorded_message").format(count=recorded_count))

        except Exception as e:
            # 如果發生錯誤，也要恢復GUI視窗
            self.restore_all_guis()
            messagebox.showerror("錯誤", f"記錄顏色失敗: {str(e)}")

    def select_inventory_ui_region(self):
        """框選背包UI區域"""
        # 使用血魔監控的遊戲視窗
        window_title = self._app.monitor_tab.window_var.get()
        if not window_title:
            messagebox.showwarning(self._app.get_text("warning"), self._app.get_text("set_game_window_first"))
            return

        # 檢查遊戲視窗是否最小化
        if self._app.check_game_window_minimized(window_title):
            return

        try:
            # 獲取遊戲視窗
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                messagebox.showerror(self._app.get_text("error"), self._app.get_text("game_window_not_found"))
                return

            game_window = windows[0]

            # 縮小GUI視窗以避免干擾
            self._app.root.iconify()
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
            self._app.root.deiconify()

    def select_interface_ui_region(self):
        """框選介面UI區域"""
        # 使用血魔監控的遊戲視窗
        window_title = self._app.monitor_tab.window_var.get()
        if not window_title:
            messagebox.showwarning(self._app.get_text("warning"), self._app.get_text("set_game_window_first"))
            return

        # 檢查遊戲視窗是否最小化
        if self._app.check_game_window_minimized(window_title):
            return

        try:
            # 獲取遊戲視窗
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                messagebox.showerror(self._app.get_text("error"), self._app.get_text("game_window_not_found"))
                return

            game_window = windows[0]

            # 縮小GUI視窗以避免干擾
            self._app.root.iconify()
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
            self._app.root.deiconify()

    def create_inventory_ui_selection_window(self, game_window):
        """創建背包UI區域選擇視窗"""
        # 創建覆蓋遊戲視窗的選擇視窗（子視窗 - 最高層級）
        self.inventory_ui_selection_window = self._app.create_child_window("", f"{game_window.width}x{game_window.height}")
        self.inventory_ui_selection_window.geometry(f"+{game_window.left}+{game_window.top}")
        self.inventory_ui_selection_window.attributes("-alpha", 0.3)
        self.inventory_ui_selection_window.overrideredirect(True)  # 移除視窗邊框
        self.inventory_ui_selection_window.configure(bg='gray')

        # 繪製遊戲視窗邊框
        canvas = tk.Canvas(self.inventory_ui_selection_window, bg='gray', highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        # 繪製說明文字
        self.ui_selection_text_id = canvas.create_text(game_window.width//2, game_window.height//2,
                          text=self._app.get_text("select_inventory_ui_instruction"),
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
        self.interface_ui_selection_window = self._app.create_child_window("", f"{game_window.width}x{game_window.height}")
        self.interface_ui_selection_window.geometry(f"+{game_window.left}+{game_window.top}")
        self.interface_ui_selection_window.attributes("-alpha", 0.3)
        self.interface_ui_selection_window.overrideredirect(True)  # 移除視窗邊框
        self.interface_ui_selection_window.configure(bg='gray')

        # 繪製遊戲視窗邊框
        canvas = tk.Canvas(self.interface_ui_selection_window, bg='gray', highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        # 繪製說明文字
        self.interface_ui_selection_text_id = canvas.create_text(game_window.width//2, game_window.height//2,
                          text=self._app.get_text("select_interface_ui_instruction"),
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
            window_title = self._app.monitor_tab.window_var.get()
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
                    self.remove_global_esc_listener_for_inventory()

                    # 先恢復主視窗，避免警告對話框被隱藏
                    self._app.root.deiconify()
                    self._app.root.attributes("-topmost", self._app.always_on_top_var.get())  # 恢復置頂（根據用戶設定）
                    self._app.root.lift()
                    self._app.root.focus_force()

                    # 顯示警告並恢復GUI
                    messagebox.showwarning(self._app.get_text("warning"), self._app.get_text("selection_too_small"))
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

                    with _mss_singleton as sct:
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
                        self.inventory_ui_label.config(text=self._app.get_text("inventory_ui_recorded"), background="lightgreen")

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
                self.remove_global_esc_listener_for_inventory()


                # 統一的GUI恢復和訊息顯示
                self._app.monitor_tab.finalize_selection_restore_gui("inventory_ui_region_set", {
                    'x': self.inventory_ui_region['x'],
                    'y': self.inventory_ui_region['y'],
                    'width': self.inventory_ui_region['width'],
                    'height': self.inventory_ui_region['height']
                })

            else:
                # 如果沒有找到遊戲視窗，銷毀選擇視窗
                if hasattr(self, 'inventory_ui_selection_window'):
                    self.inventory_ui_selection_window.destroy()
                self.remove_global_esc_listener_for_inventory()

            # 重新激活主視窗並恢復正常狀態
            self._app.root.deiconify()
            self._app.root.attributes("-topmost", self._app.always_on_top_var.get())  # 恢復置頂（根據用戶設定）
            self._app.root.lift()
            self._app.root.focus_force()
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
        self.remove_global_esc_listener_for_inventory()

        if hasattr(self, 'inventory_ui_selection_window'):
            self.inventory_ui_selection_window.destroy()

        # 統一的GUI恢復
        self._app.monitor_tab.finalize_selection_restore_gui()

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
            window_title = self._app.monitor_tab.window_var.get()
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
                    self._app.root.deiconify()
                    self._app.root.attributes("-topmost", self._app.always_on_top_var.get())  # 恢復置頂（根據用戶設定）
                    self._app.root.lift()
                    self._app.root.focus_force()

                    # 顯示警告並恢復GUI
                    messagebox.showwarning(self._app.get_text("warning"), self._app.get_text("selection_too_small"))
                    return

                # 轉換為遊戲視窗內的相對座標
                rel_x1 = max(0, x1)
                rel_y1 = max(0, y1)
                rel_x2 = max(0, x2)
                rel_y2 = max(0, y2)

                # 確保在遊戲視窗範圍內
                rel_x2 = min(rel_x2, game_window.width)
                rel_y2 = min(rel_y2, game_window.height)

                self._app.interface_ui_region = {
                    'x': min(rel_x1, rel_x2),
                    'y': min(rel_y1, rel_y2),
                    'width': abs(rel_x2 - rel_x1),
                    'height': abs(rel_y2 - rel_y1)
                }

                # 截取介面UI區域的圖片
                try:
                    # 計算絕對螢幕座標
                    abs_x = game_window.left + self._app.interface_ui_region['x']
                    abs_y = game_window.top + self._app.interface_ui_region['y']

                    with _mss_singleton as sct:
                        monitor = {
                            "top": abs_y,
                            "left": abs_x,
                            "width": self._app.interface_ui_region['width'],
                            "height": self._app.interface_ui_region['height']
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
                        self._app.monitor_tab.interface_ui_label.config(text=get_interface_ui_region_text(self._app.interface_ui_region), background="lightgreen")

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
                self._app.monitor_tab.finalize_selection_restore_gui("interface_ui_region_set", {
                    'x': self._app.interface_ui_region['x'],
                    'y': self._app.interface_ui_region['y'],
                    'width': self._app.interface_ui_region['width'],
                    'height': self._app.interface_ui_region['height']
                })

            else:
                # 如果沒有找到遊戲視窗，銷毀選擇視窗
                if hasattr(self, 'interface_ui_selection_window'):
                    self.interface_ui_selection_window.destroy()
                self.remove_global_esc_listener_for_interface()

            # 重新激活主視窗並恢復正常狀態
            self._app.root.deiconify()
            self._app.root.attributes("-topmost", self._app.always_on_top_var.get())  # 恢復置頂（根據用戶設定）
            self._app.root.lift()
            self._app.root.focus_force()
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
        self._app.monitor_tab.finalize_selection_restore_gui()

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
                    self.inventory_ui_label.config(text=self._app.get_text("inventory_ui_recorded"), background="lightgreen")

                # 更新UI預覽
                if hasattr(self, 'ui_preview_canvas'):
                    if self._app._startup_phase:
                        self._app._startup_visual_refresh_pending = True
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
                if hasattr(self._app.monitor_tab, 'interface_ui_label'):
                    self._app.monitor_tab.interface_ui_label.config(text=get_interface_ui_region_text(self._app.interface_ui_region), background="lightgreen")

                # 更新介面UI預覽
                if hasattr(self._app.monitor_tab, 'interface_ui_preview_canvas'):
                    if self._app._startup_phase:
                        self._app._startup_visual_refresh_pending = True
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
            with _mss_singleton as sct:
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
        if not self._app.interface_ui_region or self.interface_ui_screenshot is None:
            print("血魔檢查: 介面UI截圖不存在，無法判定戰鬥狀態")
            return False

        try:
            # 擷取當前介面UI區域
            with _mss_singleton as sct:
                monitor = {
                    "top": game_window.top + self._app.interface_ui_region['y'],
                    "left": game_window.left + self._app.interface_ui_region['x'],
                    "width": self._app.interface_ui_region['width'],
                    "height": self._app.interface_ui_region['height']
                }

                screenshot = sct.grab(monitor)
                current_img = np.array(screenshot)
                current_img = cv2.cvtColor(current_img, cv2.COLOR_BGRA2BGR)

                # 比較兩張圖片的相似度
                if current_img.shape == self.interface_ui_screenshot.shape:
                    # === 多重比較方法 ===

                    # 1. 均方誤差 (MSE) - 使用可調節閾值
                    mse = np.mean((current_img - self.interface_ui_screenshot) ** 2)
                    mse_threshold = self._app.interface_ui_mse_threshold

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

                    ssim_threshold = self._app.interface_ui_ssim_threshold

                    # 3. 顏色直方圖比較
                    hist_current = cv2.calcHist([current_img], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
                    hist_recorded = cv2.calcHist([self.interface_ui_screenshot], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])

                    # 正規化直方圖
                    hist_current = cv2.normalize(hist_current, hist_current).flatten()
                    hist_recorded = cv2.normalize(hist_recorded, hist_recorded).flatten()

                    # 計算直方圖相似度
                    hist_similarity = cv2.compareHist(hist_current, hist_recorded, cv2.HISTCMP_CORREL)
                    hist_threshold = self._app.interface_ui_hist_threshold

                    # 4. 主要顏色比較（使用可調節閾值）
                    current_main_color = np.mean(current_img, axis=(0, 1))
                    recorded_main_color = np.mean(self.interface_ui_screenshot, axis=(0, 1))
                    color_diff = np.mean(np.abs(current_main_color - recorded_main_color))
                    color_threshold = self._app.interface_ui_color_threshold

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
                    print("血魔UI檢查詳細:")
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
                if hasattr(self._app.monitor_tab, 'interface_ui_preview_canvas'):
                    self._app.monitor_tab.interface_ui_preview_canvas.delete("all")
                    self._app.monitor_tab.interface_ui_preview_canvas.create_text(75, 50, text="尚未截取介面UI",
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
            if hasattr(self._app.monitor_tab, 'interface_ui_preview_canvas'):
                self._app.monitor_tab.interface_ui_preview_canvas.delete("all")
                # 計算居中位置
                x = (canvas_width - new_width) // 2
                y = (canvas_height - new_height) // 2
                self._app.monitor_tab.interface_ui_preview_canvas.create_image(x, y, anchor=tk.NW, image=self.interface_ui_preview_image)

        except Exception as e:
            print(f"更新介面UI預覽失敗: {e}")
            if hasattr(self._app.monitor_tab, 'interface_ui_preview_canvas'):
                self._app.monitor_tab.interface_ui_preview_canvas.delete("all")
                self._app.monitor_tab.interface_ui_preview_canvas.create_text(75, 50, text="預覽載入失敗",
                                                           fill="red", font=("Arial", 8))

    def clear_inventory_item(self, game_window, img):
        """清空背包物品 - 動態辨識版：每次點擊後重新辨識，適應大物品清空多格的情況

        包含智能跳過機制：當遇到無法存放進倉庫的物品時，自動跳過該物品，
        繼續清理其他可以存放的物品，大幅提升清包效率。
        """
        try:
            import math

            # === 階段1：初始識別一次，創建清包列表並計算辨識次數 ===
            print("階段1：開始初始識別，創建清包列表")
            initial_item_positions = find_inventory_items(img, self.empty_inventory_colors, self.inventory_grid_positions, self.inventory_region, self.excluded_inventory_slots, -1)

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
                if self._state.inventory_clear_interrupt:
                    print("F3清包被用戶中斷")
                    break

                # 每次循環都重新辨識當前背包狀態
                try:
                    # 辨識前先將滑鼠移動到遊戲視窗正中央，避免滑鼠停留在物品上影響辨識
                    center_x = game_window.left + game_window.width // 2
                    center_y = game_window.top + game_window.height // 2
                    pyautogui.moveTo(center_x, center_y, duration=0.015)
                    time.sleep(0.025)  # 等待滑鼠移動完成

                    with _mss_singleton as sct:
                        current_screenshot = sct.grab(monitor)
                        current_img = np.frombuffer(current_screenshot.rgb, dtype=np.uint8).reshape(current_screenshot.height, current_screenshot.width, 3)
                        current_img = cv2.cvtColor(current_img, cv2.COLOR_RGB2BGR)

                    # 分析當前背包狀態
                    should_continue, current_occupied = should_clear_inventory(current_img, self.empty_inventory_colors, self.inventory_grid_positions, self.inventory_region, self.excluded_inventory_slots, -1)

                    # 更新預覽
                    progress_text = f"動態清包: {total_processed} 個道具已處理"
                    self._app.root.after(0, lambda: self.update_inventory_preview_with_progress(current_img, current_occupied, progress_text))
                    print(f"辨識結果：剩餘 {len(current_occupied)} 個物品需要清理")

                    # 如果背包已清空，結束
                    if not should_continue:
                        print(f"背包已清空，結束動態清包 (總共處理了 {total_processed} 個道具)")
                        break

                except Exception as e:
                    print(f"辨識過程發生錯誤: {e}")
                    break

                # 找到下一個要點擊的物品位置（跳過已標記無法清空的物品）
                current_item_positions = find_inventory_items(current_img, self.empty_inventory_colors, self.inventory_grid_positions, self.inventory_region, self.excluded_inventory_slots, -1)

                # 過濾掉已跳過的位置
                available_positions = [pos for pos in current_item_positions if pos not in skipped_positions]

                if not available_positions:
                    if skipped_positions:
                        print(f" 所有剩餘物品都無法存放進倉庫（已跳過 {len(skipped_positions)} 個位置）")
                        self._app.status_tab.add_status_message(self._app.get_text("inventory_full_cannot_continue"), "warning")
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
                if self.inventory_clear_click_mode.get() == "left":
                    pyautogui.click(screen_x, screen_y)
                    print(f"[OK] 已完成左鍵點擊第 {total_processed + 1} 個道具")
                else:
                    pyautogui.rightClick(screen_x, screen_y)
                    print(f"[OK] 已完成右鍵點擊第 {total_processed + 1} 個道具")
                time.sleep(0.025)
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

                    with _mss_singleton as sct:
                        check_screenshot = sct.grab(monitor)
                        check_img = np.frombuffer(check_screenshot.rgb, dtype=np.uint8).reshape(check_screenshot.height, check_screenshot.width, 3)
                        check_img = cv2.cvtColor(check_img, cv2.COLOR_RGB2BGR)

                    # 檢查點擊的位置是否還有物品
                    check_item_positions = find_inventory_items(check_img, self.empty_inventory_colors, self.inventory_grid_positions, self.inventory_region, self.excluded_inventory_slots, -1)

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
                with _mss_singleton as sct:
                    final_screenshot = sct.grab(monitor)
                    final_img = np.frombuffer(final_screenshot.rgb, dtype=np.uint8).reshape(final_screenshot.height, final_screenshot.width, 3)
                    final_img = cv2.cvtColor(final_img, cv2.COLOR_RGB2BGR)

                # 分析最終背包狀態
                final_should_clear, final_occupied = should_clear_inventory(final_img, self.empty_inventory_colors, self.inventory_grid_positions, self.inventory_region, self.excluded_inventory_slots, -1)

                # 在主線程中最終更新預覽
                final_progress_text = f"清包完成: {total_processed} 個道具"
                self._app.root.after(0, lambda: self.update_inventory_preview_with_progress(final_img, final_occupied, final_progress_text))

                # 更新統計標籤為完成狀態
                self._app.root.after(0, lambda: self.occupied_label.config(text=f"{len(final_occupied)}/60") if hasattr(self, 'occupied_label') else None)

                print(f"最終確認：清包完成 {total_processed} 個道具，剩餘: {len(final_occupied)} 個")

                # 如果還有物品且未達到重試次數限制，執行一次重試
                if final_should_clear and total_processed < max_iterations:
                    print("檢測到還有剩餘物品，執行最終重試")
                    self._app.status_tab.add_status_message(self._app.get_text("f3_retry_final"), "info")

                    # 重新擷取當前狀態作為重試的基礎
                    retry_item_positions = find_inventory_items(final_img, self.empty_inventory_colors, self.inventory_grid_positions, self.inventory_region, self.excluded_inventory_slots, -1)

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
                            if self._state.inventory_clear_interrupt:
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
                        with _mss_singleton as sct:
                            retry_final_screenshot = sct.grab(monitor)
                            retry_final_img = np.frombuffer(retry_final_screenshot.rgb, dtype=np.uint8).reshape(retry_final_screenshot.height, retry_final_screenshot.width, 3)
                            retry_final_img = cv2.cvtColor(retry_final_img, cv2.COLOR_RGB2BGR)

                        _, retry_final_occupied = should_clear_inventory(retry_final_img, self.empty_inventory_colors, self.inventory_grid_positions, self.inventory_region, self.excluded_inventory_slots, -1)

                        final_progress_text = f"清包完成(包含重試): {total_processed} 個道具"
                        self._app.root.after(0, lambda: self.update_inventory_preview_with_progress(retry_final_img, retry_final_occupied, final_progress_text))

                        self._app.root.after(0, lambda: self.occupied_label.config(text=f"{len(retry_final_occupied)}/60") if hasattr(self, 'occupied_label') else None)

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

    def _draw_exclusion_overlay(self):
        """在 Canvas 上繪製排除格子的藍色疊加層（獨立於底圖，刷新後仍保留）"""
        if not getattr(self, '_preview_has_image', False) or not hasattr(self, '_preview_meta'):
            return
        canvas = self.inventory_preview_label
        canvas.delete('exclusion')
        meta = self._preview_meta
        cell_w, cell_h = meta['cell_w'], meta['cell_h']
        off_x, off_y = meta['offset_x'], meta['offset_y']
        cx = meta.get('canvas_x', 0)
        cy = meta.get('canvas_y', 0)
        for idx in self.excluded_inventory_slots:
            row = idx // 12
            col = idx % 12
            x1 = col * cell_w + cx + off_x
            y1 = row * cell_h + cy + off_y
            x2 = x1 + cell_w
            y2 = y1 + cell_h
            canvas.create_rectangle(x1, y1, x2, y2, outline='blue', width=2, tags='exclusion')
            canvas.create_line(x1, y1, x2, y2, fill='blue', width=1, tags='exclusion')
            canvas.create_line(x2, y1, x1, y2, fill='blue', width=1, tags='exclusion')

    def _on_preview_click(self, event):
        """點擊背包預覽切換格子的排除狀態"""
        if not getattr(self, '_preview_has_image', False) or not hasattr(self, '_preview_meta'):
            self._app.status_tab.add_status_message("無法切換排除：請先完成背包設定（框選區域＋記錄空格顏色）", "warning")
            return
        meta = self._preview_meta
        click_x = event.x - meta.get('canvas_x', 0) - meta['offset_x']
        click_y = event.y - meta.get('canvas_y', 0) - meta['offset_y']
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
        self._app.status_tab.add_status_message(f"格子 {idx} 已{'排除' if idx in self.excluded_inventory_slots else '取消排除'}", "info")
        self._app.save_config(show_message=False)

    def _on_preview_resize(self, event=None):
        """Canvas 尺寸變更時重新縮放預覽"""
        if not getattr(self, '_preview_has_image', False) or not hasattr(self, '_last_preview_img'):
            return
        self.update_inventory_preview_with_items(self._last_preview_img, self._last_occupied_slots)

    def _on_click_mode_changed(self):
        self._app.save_config(show_message=False)

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

            # 調整圖片大小以適應 Canvas 可用空間，保持長寬比
            canvas = self.inventory_preview_label
            avail_w = canvas.winfo_width()
            avail_h = canvas.winfo_height()
            if avail_w < 50 or avail_h < 50:
                avail_w, avail_h = 300, 200

            scale = min(avail_w / width, avail_h / height, 1.0)

            if scale < 1.0:
                new_width = int(width * scale)
                new_height = int(height * scale)
                display_img = cv2.resize(display_img, (new_width, new_height))
            else:
                new_width, new_height = width, height

            # 轉換為PIL圖片
            display_img_rgb = cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(display_img_rgb)
            tk_img = ImageTk.PhotoImage(pil_img)

            # 計算置中偏移
            cx = (avail_w - new_width) // 2
            cy = (avail_h - new_height) // 2

            # 儲存預覽元數據供點擊排除使用
            self._preview_meta = {
                'img_w': new_width, 'img_h': new_height,
                'cell_w': new_width // 12, 'cell_h': new_height // 5,
                'offset_x': int(offset_x * scale) if scale < 1.0 else offset_x,
                'offset_y': int(offset_y * scale) if scale < 1.0 else offset_y,
                'canvas_x': cx, 'canvas_y': cy,
            }
            self._last_preview_img = img
            self._last_occupied_slots = occupied_slots

            # 更新預覽（Canvas 由 layout 管理尺寸）+ 排除疊加層
            self.inventory_preview_label.delete("all")
            self.inventory_preview_label.create_image(cx, cy, image=tk_img, anchor='nw')
            self.inventory_preview_label.image = tk_img
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
            # 調整圖片大小以適應 Canvas 可用空間，保持長寬比
            canvas = self.inventory_preview_label
            avail_w = canvas.winfo_width()
            avail_h = canvas.winfo_height()
            if avail_w < 50 or avail_h < 50:
                avail_w, avail_h = 300, 200

            scale = min(avail_w / width, avail_h / height, 1.0)

            if scale < 1.0:
                new_width = int(width * scale)
                new_height = int(height * scale)
                display_img = cv2.resize(display_img, (new_width, new_height))
            else:
                new_width, new_height = width, height

            # 轉換為PIL圖片
            display_img_rgb = cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(display_img_rgb)
            tk_img = ImageTk.PhotoImage(pil_img)

            # 計算置中偏移
            cx = (avail_w - new_width) // 2
            cy = (avail_h - new_height) // 2

            # 儲存預覽元數據供點擊排除使用
            self._preview_meta = {
                'img_w': new_width, 'img_h': new_height,
                'cell_w': new_width // 12, 'cell_h': new_height // 5,
                'offset_x': 0, 'offset_y': 0,
                'canvas_x': cx, 'canvas_y': cy,
            }
            self._last_preview_img = img
            self._last_occupied_slots = occupied_slots

            # 更新預覽（Canvas 由 layout 管理尺寸）+ 排除疊加層
            self.inventory_preview_label.delete("all")
            self.inventory_preview_label.create_image(cx, cy, image=tk_img, anchor='nw')
            self.inventory_preview_label.image = tk_img
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
                    self._preview_has_image = True
                    self._draw_exclusion_overlay()
            except Exception as e2:
                print(f"顯示原始圖片也失敗: {e2}")

    def test_inventory_clearing(self):
        """測試背包清空功能 - 增強版本，自動檢測並開啟背包"""
        if not self.inventory_region:
            messagebox.showwarning(self._app.get_text("warning"), self._app.get_text("select_inventory_region_first"))
            return

        if not self.empty_inventory_colors:
            messagebox.showwarning(self._app.get_text("warning"), self._app.get_text("record_empty_color_first"))
            return

        # 檢查背包UI區域是否已設定
        if not hasattr(self, 'inventory_ui_region') or not self.inventory_ui_region:
            messagebox.showwarning(self._app.get_text("warning"), self._app.get_text("select_inventory_ui_region_first"))
            return

        # 檢查格子位置是否已計算
        if not hasattr(self, 'inventory_grid_positions') or not self.inventory_grid_positions:
            messagebox.showwarning(self._app.get_text("warning"), self._app.get_text("please_adjust_inventory_region_first"))
            return

        # 使用血魔監控的遊戲視窗
        window_title = self._app.monitor_tab.window_var.get()
        if not window_title:
            messagebox.showwarning(self._app.get_text("warning"), self._app.get_text("set_game_window_first"))
            return

        # 檢查遊戲視窗是否最小化
        if self._app.check_game_window_minimized(window_title):
            return

        try:
            # 1. 檢測遊戲視窗是否存在
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                messagebox.showerror(self._app.get_text("error"), self._app.get_text("game_window_not_found"))
                return

            game_window = windows[0]
            print(f"找到遊戲視窗: {game_window.title}")

            # 2. 檢查GUI是否會遮擋背包UI檢測區域或背包區域，如果會則縮小GUI
            gui_minimized_for_test = False
            needs_gui_minimize = False

            # 只有在啟用"永遠保持在最上方"時才需要檢查GUI遮擋問題
            if self._app.always_on_top_var.get():
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
                original_state = self._app.root.state()
                original_geometry = self._app.root.geometry()
                self._app.root.iconify()
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
                except Exception:
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
            with _mss_singleton as sct:
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
                should_clear, occupied_slots = should_clear_inventory(img, self.empty_inventory_colors, self.inventory_grid_positions, self.inventory_region, self.excluded_inventory_slots)

            # 5. 恢復GUI面板（如果之前縮小了）
            if gui_minimized_for_test:
                self._app.root.deiconify()
                if original_state == 'zoomed':
                    self._app.root.state('zoomed')
                else:
                    self._app.root.geometry(original_geometry)
                time.sleep(0.2)
                print("GUI已恢復")

            # 7. 更新背包預覽（包含物品標記）
            self.update_inventory_preview_with_items(img, occupied_slots)

            # 8. 如果沒有啟用"永遠保持在最上方"且沒有縮小GUI，重新激活GUI讓用戶能看到背包預覽
            if not self._app.always_on_top_var.get() and not gui_minimized_for_test:
                try:
                    # 重新激活GUI視窗，讓用戶能看到背包預覽
                    self._app.root.lift()
                    self._app.root.focus_force()
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
                self._app.root.deiconify()
            except Exception:
                pass

    def save_inventory_config(self, parent_window=None):
        """儲存背包設定"""
        try:
            self._app.config['inventory_region'] = self.inventory_region
            self._app.config['empty_inventory_colors'] = self.empty_inventory_colors
            self._app.config['inventory_grid_positions'] = [list(pos) for pos in self.inventory_grid_positions]  # 保存為list格式
            self._app.config['grid_offset_x'] = self.grid_offset_x
            self._app.config['grid_offset_y'] = self.grid_offset_y
            self._app.config['excluded_inventory_slots'] = sorted(self.excluded_inventory_slots)
            # 儲存血魔監控的遊戲視窗標題
            self._app.config['inventory_window_title'] = self._app.monitor_tab.window_var.get()

            # 儲存背包UI設定
            self._app.config['inventory_ui_region'] = self.inventory_ui_region
            # 注意：inventory_ui_screenshot是numpy array，不能直接序列化為JSON
            # 我們只儲存區域資訊，截圖會在下次啟動時重新截取

            with open(self._app.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._app.config, f, indent=2, ensure_ascii=False)

            messagebox.showinfo(self._app.get_text("success"), self._app.get_text("inventory_settings_saved"))

            # 重新激活主視窗而不是設定視窗
            if parent_window:
                self._app.root.lift()
                self._app.root.focus_force()
                # 根據用戶設定決定是否置頂主視窗
                if self._app.should_keep_topmost():
                    self._app.root.attributes("-topmost", True)

        except Exception as e:
            messagebox.showerror("錯誤", f"儲存失敗: {str(e)}")

    def return_to_hideout(self):
        """F5 返回藏身功能"""
        # 全域暫停檢查
        if self._state.global_pause:
            print("[STOP] 全域暫停中，跳過F5熱鍵")
            self._app.status_tab.add_status_message("按下 F5 - 因全域暫停模式而跳過執行", "warning")
            return

        self._app.status_tab.add_status_message("按下 F5 - 執行返回藏身", "hotkey")

        try:
            # 檢查是否有設定遊戲視窗
            window_title = self._app.monitor_tab.window_var.get()
            if not window_title:
                print("F5: 未設定遊戲視窗，無法使用返回藏身功能")
                self._app.status_tab.add_status_message("F5 執行失敗 - 未設定遊戲視窗", "error")
                return

            # 檢查遊戲視窗是否在前台
            if not self._app.window_key_sender.is_game_window_foreground(window_title):
                print(f"F5: 遊戲視窗 '{window_title}' 不在前台，跳過返回藏身操作")
                self._app.status_tab.add_status_message("F5 執行取消 - 遊戲視窗不在前台", "warning")
                return

            self._app.status_tab.add_status_message("F5 執行中 - 發送返回藏身指令", "info")
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
            self._app.status_tab.add_status_message(self._app.get_text("f5_success_hide_command_sent"), "success")

        except Exception as e:
            print(f"F5: 返回藏身失敗: {str(e)}")
            self._app.status_tab.add_status_message(f"F5 執行失敗 - {str(e)}", "error")

    def f6_pickup_items(self):
        """F6 一鍵取物（非阻塞版）
        主線程做必要的檢查與安排 GUI 操作（使用 root.after），實際的滑鼠/視窗操作在背景執行緒中完成，
        避免阻塞 Tkinter 事件迴圈造成主 GUI 無法互動。"""
        # 全域暫停檢查（主線程）
        if self._state.global_pause:
            print("[STOP] 全域暫停中，跳過F6熱鍵")
            # 在主線程更新狀態訊息
            try:
                self._app.root.after(0, lambda: self._app.status_tab.add_status_message(self._app.get_text("f6_skip_global_pause"), "warning"))
            except Exception:
                pass
            return

        # 簡短回饋（主線程）
        try:
            self._app.root.after(0, lambda: self._app.status_tab.add_status_message(self._app.get_text("f6_hotkey_pressed"), "hotkey"))
        except Exception:
            pass

        print("=== F6取物功能被調用（非阻塞版） ===")

        # 在主線程進行輕量檢查與狀態擷取
        window_title = self._app.monitor_tab.window_var.get()
        if not window_title:
            print("F6: 未設定遊戲視窗，無法使用一鍵取物功能")
            try:
                self._app.root.after(0, lambda: self._app.status_tab.add_status_message(self._app.get_text("f6_fail_game_window_not_set"), "error"))
            except Exception:
                pass
            return

        print(f"F6: 遊戲視窗已設定為: {window_title}")

        # 檢查 GUI 狀態（在主線程）
        gui_was_visible = (self._app.root.state() == 'normal')
        gui_was_foreground = False
        gui_was_topmost = self._app.should_keep_topmost()  # 檢查是否原本保持在最上方
        if gui_was_visible:
            try:
                foreground_hwnd = win32gui.GetForegroundWindow()
                gui_hwnd = self._app.root.winfo_id()
                gui_was_foreground = (foreground_hwnd == gui_hwnd)
            except Exception:
                gui_was_foreground = False

        print(f"F6: GUI視窗狀態 - 原本{'顯示' if gui_was_visible else '最小化'}，{'在前台' if gui_was_foreground else '在後台'}，{'保持在最上方' if gui_was_topmost else '不保持在最上方'}")

        # 如果 GUI 在前台或保持在最上方，安排把 GUI 移到後台（主線程）以免遮擋遊戲
        if gui_was_foreground or gui_was_topmost:
            def _prepare_gui_for_execution():
                try:
                    # 如果原本保持在最上方，先取消置頂
                    if gui_was_topmost:
                        self._app.root.attributes("-topmost", False)
                        print("F6: 已取消 GUI 置頂設定")
                    # 然後移到後台
                    getattr(self._app.root, 'lower', lambda: None)()
                    print("F6: 已安排將 GUI 移到後台")
                except Exception as e:
                    print(f"F6: 準備 GUI 失敗: {e}")
            try:
                self._app.root.after(0, _prepare_gui_for_execution)
            except Exception as e:
                print(f"F6: 安排準備 GUI 失敗: {e}")

        # 隱藏可能的設定視窗（主線程）
        def _hide_setting_windows():
            try:
                for w in self._app.root.winfo_children():
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
                                        if hasattr(self._app.root, 'grab_release'):
                                            self._app.root.grab_release()
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
            self._app.root.after(0, _hide_setting_windows)
        except Exception:
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
                        self._app.root.after(0, lambda: self._app.status_tab.add_status_message(self._app.get_text("f6_fail_game_window_not_set"), "error"))
                    except Exception:
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
                if not self._app.window_key_sender.is_game_window_foreground(window_title_local):
                    print("F6(worker): 警告 - 遊戲視窗可能未在前台")

                # 檢查背包UI是否可見
                if not self.is_inventory_ui_visible(game_window):
                    print("F6(worker): 背包UI未打開，無法執行取物功能")
                    try:
                        self._app.root.after(0, lambda: self._app.status_tab.add_status_message(self._app.get_text("f6_cancel_inventory_ui_not_open"), "warning"))
                    except Exception:
                        pass
                    return

                try:
                    self._app.root.after(0, lambda: self._app.status_tab.add_status_message(self._app.get_text("f6_processing_inventory_ui_check_passed"), "info"))
                except Exception:
                    pass

                print(f"F6(worker): 開始執行取物，共 {len(valid_coords_local)} 個座標")

                # 記錄原始滑鼠位置
                try:
                    original_pos = pyautogui.position()
                except Exception:
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
                        self._app.root.after(0, lambda: self._app.status_tab.add_status_message(self._app.get_text("f6_completed_coordinates_processed").format(count=len(valid_coords_local)), "success"))
                    except Exception:
                        pass

                    if original_pos:
                        try:
                            pyautogui.moveTo(original_pos.x, original_pos.y, duration=0.05)
                        except Exception:
                            pass

                finally:
                    try:
                        pyautogui.keyUp('ctrl')
                    except Exception:
                        pass

                # 執行完畢後：如果 GUI 原本在前台或保持在最上方，安排主線程恢復 GUI
                def _restore_gui():
                    try:
                        if gui_was_foreground_local or gui_was_topmost_local:
                            try:
                                # 先恢復到前台
                                self._app.root.lift()
                                self._app.root.focus_force()
                                # 如果原本保持在最上方，恢復置頂
                                if gui_was_topmost_local:
                                    self._app.root.attributes("-topmost", True)
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
                    self._app.root.after(0, _restore_gui)
                except Exception:
                    pass

            except Exception as e:
                print(f"F6(worker): 發生例外: {e}")
                _err_msg = str(e)
                try:
                    self._app.root.after(0, lambda: self._app.status_tab.add_status_message(f"F6 執行失敗 - {_err_msg}", "error"))
                except Exception:
                    pass
                # 確保 ctrl 被釋放
                try:
                    pyautogui.keyUp('ctrl')
                except Exception:
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
            if 'pickup_coordinates' in self._app.config:
                self.pickup_coordinates = self._app.config['pickup_coordinates']
                print(f"載入取物座標: {len(self.pickup_coordinates)} 個座標")
        except Exception as e:
            print(f"載入取物座標失敗: {str(e)}")
            self.pickup_coordinates = []

    def save_pickup_coordinates(self, parent_window=None):
        """儲存取物座標設定"""
        try:
            self._app.config['pickup_coordinates'] = self.pickup_coordinates
            with open(self._app.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._app.config, f, indent=2, ensure_ascii=False)
            print("取物座標已儲存")
            messagebox.showinfo(self._app.get_text("success"), self._app.get_text("pickup_coordinates_saved"))
            self._app.root.lift()
            self._app.root.focus_force()

            # 重新激活主視窗而不是設定視窗
            if parent_window:
                self._app.root.lift()
                self._app.root.focus_force()
                # 根據用戶設定決定是否置頂主視窗
                if self._app.should_keep_topmost():
                    self._app.root.attributes("-topmost", True)

        except Exception as e:
            print(f"儲存取物座標失敗: {str(e)}")
            messagebox.showerror("錯誤", f"儲存失敗: {str(e)}")

    def setup_pickup_coordinates(self):
        """設定取物座標 - 一次性連續設定5個座標"""
        # 創建設定視窗（設定視窗 - 中間層級）
        setup_window = self._app.create_settings_window(self._app.get_text("setup_f6_pickup_coordinates_title"), "750x500")
        setup_window.resizable(False, False)

        # 置中顯示
        setup_window.transient(self._app.root)
        setup_window.grab_set()

        # 說明標籤
        info_label = ttk.Label(setup_window, text=self._app.get_text("setup_f6_pickup_coordinates_description"), font=("", 14, "bold"))
        info_label.pack(pady=10)

        instruction_text = self._app.get_text("setup_f6_pickup_instructions")

        instruction_label = ttk.Label(setup_window, text=instruction_text,
                                     font=("", 10), justify='left')
        instruction_label.pack(pady=10)

        # 座標顯示區域
        coords_frame = ttk.LabelFrame(setup_window, text=self._app.get_text("coordinate_status"), padding="10")
        coords_frame.pack(fill='x', padx=20, pady=10)

        # 確保pickup_coordinates有5個位置
        if self.pickup_coordinates is None:
            self.pickup_coordinates = self._app.pickup_coordinates
        if self.pickup_coordinates is None:
            self.pickup_coordinates = [[0, 0] for _ in range(5)]
        while len(self.pickup_coordinates) < 5:
            self.pickup_coordinates.append([0, 0])

        # 創建座標顯示標籤
        self.coord_display_labels = []
        for i in range(5):
            frame = ttk.Frame(coords_frame)
            frame.pack(fill='x', pady=2)

            ttk.Label(frame, text=self._app.get_text("coordinate_template").format(number=i+1), width=8).pack(side='left')

            coord_label = ttk.Label(frame, text=f"({self.pickup_coordinates[i][0]}, {self.pickup_coordinates[i][1]})",
                                   width=15, relief='sunken')
            coord_label.pack(side='left', padx=(5, 10))
            self.coord_display_labels.append(coord_label)

            # 狀態指示器
            status_label = ttk.Label(frame, text=self._app.get_text("coordinate_not_set"), foreground="gray", width=10)
            status_label.pack(side='left', padx=5)
            self.coord_display_labels.append(status_label)  # 將狀態標籤也加入列表

        # 按鈕區域
        button_frame = ttk.Frame(setup_window)
        button_frame.pack(fill='x', padx=20, pady=20)

        ttk.Button(button_frame, text=self._app.get_text("start_continuous_setup"),
                  command=lambda: self.start_continuous_setup(setup_window), width=25).pack(side='left', padx=5)
        ttk.Button(button_frame, text=self._app.get_text("test_f6_pickup"),
                  command=self.test_pickup, width=15).pack(side='left', padx=5)
        ttk.Button(button_frame, text=self._app.get_text("clear_all_coordinates"),
                  command=self.clear_all_coordinates, width=12).pack(side='left', padx=5)
        ttk.Button(button_frame, text=self._app.get_text("save_coordinates"),
                  command=lambda: [self.save_pickup_coordinates(), setup_window.destroy()], width=18).pack(side='right', padx=5)
        ttk.Button(button_frame, text=self._app.get_text("close"),
                  command=setup_window.destroy, width=8).pack(side='right', padx=5)

        # 初始化座標顯示
        self.update_coordinate_display()

    def start_continuous_setup(self, parent_window):
        """開始連續設定5個取物座標"""
        # 檢查遊戲視窗是否最小化
        window_title = self._app.monitor_tab.window_var.get()
        if window_title and self._app.check_game_window_minimized(window_title):
            return

        try:
            # 隱藏設定視窗和主視窗
            parent_window.withdraw()
            self._app.root.withdraw()

            # 等待視窗完全隱藏
            time.sleep(0.5)

            messagebox.showinfo(self._app.get_text("start_setup_title"),
                self._app.get_text("start_setup_message"))

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
                        messagebox.showinfo(self._app.get_text("setup_cancelled"), self._app.get_text("setup_cancelled_message"))
                        break

                    # 提示當前要設定的座標
                    try:
                        # 創建一個小的提示視窗（子視窗 - 最高層級）
                        hint_window = self._app.create_child_window(self._app.get_text("setup_coordinate_title").format(current=i+1, total=5), "450x140")
                        hint_window.geometry("+100+100")
                        hint_window.attributes('-alpha', 0.9)

                        hint_label = ttk.Label(hint_window,
                            text=self._app.get_text("setup_coordinate_hint").format(number=i+1),
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
                        window_title = self._app.monitor_tab.window_var.get()
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
                        except Exception:
                            pass
                        break

                # 取消鍵盤監聽
                keyboard.unhook_all()

                if not cancel_setup:
                    # 更新顯示
                    self.update_coordinate_display()

                    # 自動儲存
                    self.save_pickup_coordinates(parent_window)

                    messagebox.showinfo(self._app.get_text("setup_completed_title"),
                        self._app.get_text("setup_completed_message"))
                    # 重新激活主視窗而不是設定視窗
                    self._app.root.lift()
                    self._app.root.focus_force()
                    # 根據用戶設定決定是否置頂主視窗
                    if self._app.should_keep_topmost():
                        self._app.root.attributes("-topmost", True)
                else:
                    messagebox.showinfo(self._app.get_text("setup_cancelled"), self._app.get_text("setup_cancelled_message"))

            except Exception as e:
                print(f"連續設定失敗: {str(e)}")
                messagebox.showerror(self._app.get_text("setup_failed"), f"{self._app.get_text('setup_failed')}: {str(e)}")
            finally:
                # 取消鍵盤監聽並重新設置全局熱鍵
                try:
                    keyboard.unhook_all()
                    # 重新設置全局熱鍵
                    self._app.setup_hotkeys()
                except Exception:
                    pass

        except Exception as e:
            print(f"連續設定失敗: {str(e)}")
            messagebox.showerror(self._app.get_text("setup_failed"), f"{self._app.get_text('setup_failed')}: {str(e)}")
        finally:
            # 恢復視窗顯示
            try:
                self._app.root.deiconify()
                parent_window.deiconify()
            except Exception:
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
                            status_label.config(text=self._app.get_text("coordinate_set"), foreground="green")
                        else:
                            status_label.config(text=self._app.get_text("coordinate_not_set"), foreground="gray")

        # 更新主界面狀態
        self.update_pickup_status()

    def clear_all_coordinates(self):
        """清除所有取物座標"""
        if messagebox.askyesno(self._app.get_text("confirm"), self._app.get_text("confirm_clear_coordinates")):
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
        window_title = self._app.monitor_tab.window_var.get()
        if not window_title:
            messagebox.showerror("錯誤", "請先選擇遊戲視窗")
            return

        # 檢查遊戲視窗是否最小化
        if self._app.check_game_window_minimized(window_title):
            return

        # 檢查JSON配置是否正確寫入和讀取
        try:
            # 檢查當前配置
            if 'pickup_coordinates' not in self._app.config:
                messagebox.showerror("錯誤", "取物座標配置未找到，請重新設定")
                return

            # 驗證配置中的座標
            config_coords = self._app.config['pickup_coordinates']
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
    def check_inventory_ui_exists(self, game_window):
        """檢測背包UI是否存在（簡化版本）"""
        if not self.inventory_ui_region:
            return False

        try:
            # 擷取當前背包UI區域
            with _mss_singleton as sct:
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
                        print("背包UI檢測: 圖片尺寸不匹配")
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

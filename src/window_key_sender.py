import ctypes
import time
import pygetwindow as gw
from _version import __version__


# Windows API functions
user32 = ctypes.windll.user32
GetForegroundWindow = user32.GetForegroundWindow
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
SendMessageW = user32.SendMessageW
PostMessageW = user32.PostMessageW

# Virtual key code constants
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

# Windows message constants
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_CHAR = 0x0102

# argtypes setup
GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
GetWindowTextLengthW.restype = ctypes.c_int
GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
GetWindowTextW.restype = ctypes.c_int
SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_long]
SendMessageW.restype = ctypes.c_long

CURRENT_VERSION = f"v{__version__}"


class WindowKeySender:
    def __init__(self, app):
        self._app = app
        self._last_key_send_times = {}
        self._focus_watcher_interval = 1000

    def get_game_window_handle(self):
        try:
            if not self._app.window_var.get():
                return None
            windows = gw.getWindowsWithTitle(self._app.window_var.get())
            if windows:
                return windows[0]._hWnd
            return None
        except Exception:
            return None

    def map_key_to_vk_code(self, key):
        key = key.lower()
        if key.isdigit():
            return ord(key)
        if len(key) == 1 and key.isalpha():
            return ord(key.upper())
        key_mapping = {
            'esc': VK_ESCAPE, 'escape': VK_ESCAPE,
            'enter': VK_RETURN, 'return': VK_RETURN,
            'space': VK_SPACE, 'tab': VK_TAB,
            'backspace': VK_BACK, 'delete': VK_DELETE,
            'home': VK_HOME, 'end': VK_END,
            'left': VK_LEFT, 'up': VK_UP, 'right': VK_RIGHT, 'down': VK_DOWN,
            'f3': VK_F3, 'f5': VK_F5, 'f6': VK_F6, 'f7': VK_F7,
            'f8': VK_F8, 'f9': VK_F9, 'f10': VK_F10, 'f12': VK_F12,
        }
        return key_mapping.get(key)

    def send_key_to_window(self, hwnd, vk_code):
        try:
            current_time = time.time()
            key_id = f"{hwnd}_{vk_code}"
            last_send_time = self._last_key_send_times.get(key_id, 0)
            if current_time - last_send_time < 0.2:
                print(f" 血魔防重複: 跳過重複按鍵 {vk_code} (間隔 {(current_time - last_send_time)*1000:.1f}ms)")
                return
            self._last_key_send_times[key_id] = current_time
            print(f" 血魔監控發送按鍵: VK_{vk_code} 到窗口 {hwnd}")
            try:
                import keyboard
                windows = gw.getWindowsWithTitle(self._app.window_var.get())
                if windows:
                    windows[0].activate()
                    time.sleep(0.05)
                key_name = self.vk_to_key_name(vk_code)
                if key_name:
                    print(f" 血魔使用keyboard庫發送: {key_name}")
                    keyboard.press_and_release(key_name)
                    print(f"[OK] 血魔keyboard庫發送成功: {key_name}")
                else:
                    self._send_with_postmessage(hwnd, vk_code)
            except ImportError:
                print("[WARN] keyboard庫未安裝，血魔使用PostMessage方法")
                self._send_with_postmessage(hwnd, vk_code)
            except Exception as keyboard_error:
                print(f"[WARN] keyboard庫發送失敗，血魔回退到PostMessage: {keyboard_error}")
                self._send_with_postmessage(hwnd, vk_code)
        except Exception as e:
            print(f"[ERROR] 血魔按鍵發送失敗: {e}")

    def send_key_to_window_combo(self, hwnd, vk_code):
        try:
            print(f"[SKILL] 技能連段發送按鍵: VK_{vk_code} 到窗口 {hwnd}")
            SendMessageW(hwnd, WM_KEYDOWN, vk_code, 0)
            time.sleep(0.01)
            SendMessageW(hwnd, WM_KEYUP, vk_code, 0)
            print(f"[OK] 技能連段SendMessage發送成功: VK_{vk_code}")
        except Exception as e:
            print(f"[ERROR] 技能連段按鍵發送失敗: {e}")

    def _send_with_postmessage(self, hwnd, vk_code):
        try:
            from ctypes import windll
            PostMessageW_local = windll.user32.PostMessageW
            print(f" 使用PostMessage備用方法: VK_{vk_code}")
            result1 = PostMessageW_local(hwnd, WM_KEYDOWN, vk_code, 0)
            time.sleep(0.1)
            result2 = PostMessageW_local(hwnd, WM_KEYUP, vk_code, 0)
            print(f"[OK] PostMessage發送成功: VK_{vk_code} (down:{result1}, up:{result2})")
        except Exception as e:
            print(f"[ERROR] PostMessage發送失敗: {e}")

    def vk_to_key_name(self, vk_code):
        vk_mapping = {
            0x1B: 'esc',
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
        key = key.lower()
        key_mapping = {
            'esc': 'esc', 'escape': 'esc',
            'enter': 'enter', 'return': 'enter',
            'space': 'space', 'tab': 'tab',
            'backspace': 'backspace', 'delete': 'delete',
            'home': 'home', 'end': 'end',
            'pageup': 'page up', 'pagedown': 'page down',
            'uparrow': 'up', 'downarrow': 'down',
            'leftarrow': 'left', 'rightarrow': 'right',
            'ctrl': 'ctrl', 'alt': 'alt', 'shift': 'shift',
            'win': 'windows', 'cmd': 'windows',
        }
        return key_mapping.get(key, key)

    def activate_game_window(self):
        try:
            if self._app.window_var.get():
                windows = gw.getWindowsWithTitle(self._app.window_var.get())
                if windows:
                    game_window = windows[0]
                    game_window.activate()
                    print(f"已激活遊戲視窗: {self._app.window_var.get()}")
                    time.sleep(0.5)
                else:
                    print("找不到指定的遊戲視窗")
            else:
                print("未設定遊戲視窗")
        except Exception as e:
            print(f"激活遊戲視窗時發生錯誤: {e}")

    def is_game_window_foreground(self, window_title):
        try:
            foreground_hwnd = GetForegroundWindow()
            length = GetWindowTextLengthW(foreground_hwnd)
            if length > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                GetWindowTextW(foreground_hwnd, buffer, length + 1)
                foreground_title = buffer.value
                return window_title.lower() in foreground_title.lower()
            return False
        except Exception as e:
            print(f"檢查前台視窗失敗: {e}")
            return False

    def is_gui_foreground(self):
        try:
            foreground_hwnd = GetForegroundWindow()
            length = GetWindowTextLengthW(foreground_hwnd)
            if length > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                GetWindowTextW(foreground_hwnd, buffer, length + 1)
                foreground_title = buffer.value
                gui_title = f"Sid輔助工具 {CURRENT_VERSION} - 血魔監控 + 一鍵清包 + 自動化工具"
                return gui_title.lower() in foreground_title.lower()
            return False
        except Exception as e:
            print(f"檢查GUI前台狀態失敗: {e}")
            return False

    def _start_window_focus_watcher(self):
        try:
            tab_index = self._app.notebook.index(self._app.notebook.select())
            self._focus_watcher_interval = 200 if tab_index == 1 else 1000
        except Exception:
            self._focus_watcher_interval = 1000
        self._focus_watcher_tick()

    def _focus_watcher_tick(self):
        if self._app.state._is_closing:
            return
        try:
            interval = getattr(self, '_focus_watcher_interval', 1000)
            if interval <= 200:
                if self._app.inventory_region:
                    self._app.update_inventory_preview_from_current()
        except Exception:
            pass
        self._app.root.after(
            getattr(self, '_focus_watcher_interval', 1000),
            self._focus_watcher_tick
        )

    def _is_game_window_active(self):
        try:
            windows = gw.getWindowsWithTitle(self._app.window_var.get())
            if not windows:
                return False
            w = windows[0]
            return not w.isMinimized and w.isActive
        except Exception:
            return False

    def _is_game_window_visible(self):
        try:
            windows = gw.getWindowsWithTitle(self._app.window_var.get())
            if not windows:
                return False
            w = windows[0]
            return not w.isMinimized
        except Exception:
            return False

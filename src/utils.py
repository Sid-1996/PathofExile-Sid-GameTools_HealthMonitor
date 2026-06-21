"""
工具函數模組
包含應用程式的通用工具函數、緊急處理、系統級功能等
"""

import os
import sys
import keyboard
import psutil
import atexit


def get_app_dir():
    """獲取應用程式目錄，適用於開發環境和打包後的exe"""
    if getattr(sys, 'frozen', False):
        # 如果是打包後的exe
        return os.path.dirname(sys.executable)
    else:
        # 如果是開發環境
        return os.path.dirname(__file__)


def emergency_cleanup():
    """緊急清理函數 - 確保應用程序退出時清理資源"""
    try:
        # 清理鍵盤監聽器
        keyboard.unhook_all()
        print("鍵盤監聽器已清理")
    except Exception:
        pass

    try:
        # 停止所有子進程
        import psutil
        current_process = psutil.Process()
        for child in current_process.children(recursive=True):
            try:
                child.terminate()
                child.wait(timeout=1)
            except Exception:
                try:
                    child.kill()
                except Exception:
                    pass
        print("子進程已清理")
    except Exception:
        pass


# 註冊退出時清理函數
atexit.register(emergency_cleanup)


# 全局緊急關閉變數
_app_instance = None


def set_app_instance(instance):
    """設定應用程式實例用於緊急關閉"""
    global _app_instance
    _app_instance = instance


def global_f12_handler():
    """全局F12處理器 - 在任何情況下都能關閉應用程序"""
    global _app_instance
    print("\n[STOP] F12緊急關閉被觸發")
    try:
        if _app_instance and hasattr(_app_instance, 'close_app'):
            _app_instance.close_app()
        else:
            # 如果應用程序實例不可用，直接強制退出
            import os
            os._exit(1)
    except Exception:
        import os
        os._exit(1)


def emergency_exit_handler(signum=None, frame=None):
    """緊急退出處理器 - 確保在任何異常情況下都能關閉應用程序"""
    print("\n[STOP] 收到緊急退出信號，正在強制關閉應用程式...")
    try:
        if _app_instance and hasattr(_app_instance, 'close_app'):
            _app_instance.close_app()
    except Exception:
        pass
    os._exit(1)


def global_exception_handler(exc_type, exc_value, exc_traceback):
    """全局異常處理器 - 捕獲所有未處理的異常"""
    import traceback
    print(f"\n[ERROR] 發生未捕獲的異常: {exc_type.__name__}: {exc_value}")
    print("📋 異常追蹤:")
    traceback.print_exception(exc_type, exc_value, exc_traceback)

    # 嘗試緊急關閉應用程序
    try:
        emergency_exit_handler()
    except Exception:
        os._exit(1)


def setup_signal_handlers():
    """設置信號處理器（適用於Unix-like系統）"""
    try:
        import signal
        signal.signal(signal.SIGTERM, emergency_exit_handler)
        signal.signal(signal.SIGINT, emergency_exit_handler)
    except (ImportError, AttributeError):
        # Windows不支援這些信號，忽略
        pass


def setup_exception_handler():
    """設置全局異常處理器"""
    import sys
    sys.excepthook = global_exception_handler


class Tooltip:
    """可重複使用的 Tooltip：懸浮 widget 顯示說明文字，支援延遲"""
    def __init__(self, widget, text, delay=300):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._tip = None
        self._after_id = None
        widget.bind('<Enter>', self._schedule, add='+')
        widget.bind('<Leave>', self._hide, add='+')

    def _schedule(self, event):
        if self._tip:
            return
        self._after_id = self.widget.after(self.delay, self._show)

    def _show(self):
        if self._tip:
            return
        import tkinter as tk
        from tkinter import ttk
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 25
        self._tip = tk.Toplevel(self.widget)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(self._tip, text=self.text,
                          background="#ffffcc", relief="solid",
                          borderwidth=1, padding=2)
        label.pack()

    def _hide(self, event=None):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None
        if self._tip:
            self._tip.destroy()
            self._tip = None


def format_usage_time(total_seconds):
    """格式化使用時間顯示"""
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours}小時{minutes}分鐘"
    elif minutes > 0:
        return f"{minutes}分鐘{seconds}秒"
    else:
        return f"{seconds}秒"


def show_toast(parent, text, duration=1000):
    """黑底白字半透明提示視窗，自動在 duration 毫秒後消失"""
    import tkinter as tk
    from tkinter import ttk
    toast = tk.Toplevel(parent)
    toast.wm_overrideredirect(True)
    toast.attributes("-topmost", True)
    toast.attributes("-alpha", 0.85)

    parent.update_idletasks()
    px, py = parent.winfo_rootx(), parent.winfo_rooty()
    pw, ph = parent.winfo_width(), parent.winfo_height()
    tw, th = 320, 56
    x = px + (pw - tw) // 2
    y = py + (ph - th) // 2
    toast.geometry(f"{tw}x{th}+{x}+{y}")

    frame = tk.Frame(toast, bg="black", highlightthickness=0)
    frame.pack(fill="both", expand=True)
    label = tk.Label(frame, text=text, font=("Arial", 12, "bold"),
                     bg="black", fg="white", anchor="center", justify="center")
    label.pack(fill="both", expand=True, padx=16, pady=8)

    toast.after(duration, toast.destroy)

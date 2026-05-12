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
    except:
        pass

    try:
        # 停止所有子進程
        import psutil
        current_process = psutil.Process()
        for child in current_process.children(recursive=True):
            try:
                child.terminate()
                child.wait(timeout=1)
            except:
                try:
                    child.kill()
                except:
                    pass
        print("子進程已清理")
    except:
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
    except:
        import os
        os._exit(1)


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


def global_exception_handler(exc_type, exc_value, exc_traceback):
    """全局異常處理器 - 捕獲所有未處理的異常"""
    import traceback
    print(f"\n[ERROR] 發生未捕獲的異常: {exc_type.__name__}: {exc_value}")
    print("📋 異常追蹤:")
    traceback.print_exception(exc_type, exc_value, exc_traceback)

    # 嘗試緊急關閉應用程序
    try:
        emergency_exit_handler()
    except:
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

"""
工具函數模組
包含應用程式的通用工具函數、緊急處理、系統級功能等
"""

import os
import shutil
import sys
import keyboard
import psutil
import atexit


def get_app_dir():
    """獲取應用程式目錄，適用於開發環境和打包後的exe"""
    if getattr(sys, "frozen", False):
        # 如果是打包後的exe
        return os.path.dirname(sys.executable)
    else:
        # 如果是開發環境
        return os.path.dirname(__file__)


def get_user_data_dir():
    """取得使用者資料目錄（%LOCALAPPDATA%\\GameTools_HealthMonitor）。

    config / screenshots 等執行期產生的使用者資料一律放這裡，與 app 目錄分離
    （Velopack 更新會替換整個 app 目錄）。首次呼叫時把舊版放在 exe 同層的資料
    「複製」過來：冪等、不刪來源、逐項隔離錯誤，遷移失敗不阻擋啟動。
    """
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    data_dir = os.path.join(base, "GameTools_HealthMonitor")
    app_dir = get_app_dir()
    if os.path.abspath(data_dir) == os.path.abspath(app_dir):
        return data_dir
    try:
        os.makedirs(data_dir, exist_ok=True)
    except Exception as e:
        print(f"[WARN] 建立使用者資料目錄失敗: {e}")
        return data_dir
    for name in ("health_monitor_config.json", "health_monitor_config.json.backup"):
        src = os.path.join(app_dir, name)
        dst = os.path.join(data_dir, name)
        if os.path.exists(src) and not os.path.exists(dst):
            try:
                shutil.copy2(src, dst)
            except Exception as e:
                print(f"[WARN] 遷移 {name} 失敗: {e}")
    legacy_shots = os.path.join(app_dir, "screenshots")
    if os.path.isdir(legacy_shots):
        try:
            shutil.copytree(legacy_shots, os.path.join(data_dir, "screenshots"), dirs_exist_ok=True)
        except Exception as e:
            print(f"[WARN] 遷移 screenshots 失敗: {e}")
    return data_dir


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
        if _app_instance and hasattr(_app_instance, "close_app"):
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
        if _app_instance and hasattr(_app_instance, "close_app"):
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


def format_usage_time(seconds, lang="zh"):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if lang == "en":
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"
    else:
        if hours > 0:
            return f"{hours}小時{minutes}分鐘{secs}秒"
        elif minutes > 0:
            return f"{minutes}分鐘{secs}秒"
        else:
            return f"{secs}秒"

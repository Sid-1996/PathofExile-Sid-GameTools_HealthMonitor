import winreg
from datetime import datetime
from utils import format_usage_time


class UsageTracker:
    def __init__(self, app):
        self._app = app
        self._usage_time_after_id = None
        self._app.total_usage_time = self.load_usage_time_from_registry()
        print(f"載入總使用時間: {format_usage_time(self._app.total_usage_time)}")

    def load_usage_time_from_registry(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\SidGameTools\HealthMonitor",
                                 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, "TotalUsageTime")
            winreg.CloseKey(key)
            return int(value)
        except FileNotFoundError:
            return 0
        except Exception as e:
            print(f"載入使用時間失敗: {e}")
            return 0

    def save_usage_time_to_registry(self, total_seconds):
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                   r"Software\SidGameTools\HealthMonitor")
            winreg.SetValueEx(key, "TotalUsageTime", 0, winreg.REG_DWORD, total_seconds)
            winreg.CloseKey(key)
            print(f"已保存總使用時間: {format_usage_time(total_seconds)}")
        except Exception as e:
            print(f"保存使用時間失敗: {e}")

    def track_usage_time(self):
        try:
            end_time = datetime.now()
            session_duration = int((end_time - self._app.start_time).total_seconds())
            self._app.total_usage_time += session_duration
            self.save_usage_time_to_registry(self._app.total_usage_time)
            print(f"本次使用時間: {format_usage_time(session_duration)}")
            print(f"累計總使用時間: {format_usage_time(self._app.total_usage_time)}")
        except Exception as e:
            print(f"追蹤使用時間失敗: {e}")

    def update_usage_time_display(self):
        try:
            if hasattr(self._app, 'usage_time_label'):
                usage_time_text = format_usage_time(self._app.total_usage_time)
                self._app.usage_time_label.config(
                    text=self._app.get_text("total_usage_time").format(time=usage_time_text)
                )
        except Exception as e:
            print(f"更新使用時間顯示時發生錯誤: {e}")

    def update_usage_time_periodically(self):
        if self._app.state._is_closing:
            self._usage_time_after_id = None
            return

        try:
            self.update_usage_time_display()
            self._usage_time_after_id = self._app.root.after(60000, self.update_usage_time_periodically)
        except Exception as e:
            print(f"定期更新使用時間時發生錯誤: {e}")

    def start_periodic_update(self):
        self._usage_time_after_id = self._app.root.after(60000, self.update_usage_time_periodically)

    def stop(self):
        if self._usage_time_after_id:
            try:
                self._app.root.after_cancel(self._usage_time_after_id)
            except Exception:
                pass
            self._usage_time_after_id = None
        self.track_usage_time()

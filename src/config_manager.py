"""
配置管理模組
處理應用程式的設定載入、保存、註冊表操作等功能
"""

import json
import os
import sys
import winreg
from datetime import datetime
from utils import get_app_dir


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_filename="health_monitor_config.json"):
        self.config_file = os.path.join(get_app_dir(), config_filename)
        self.config = {}
        self.start_time = datetime.now()
        
        # 註冊表相關常數
        self.REGISTRY_KEY = r"SOFTWARE\SidGameTools\HealthMonitor"
        self.REGISTRY_VALUE = "TotalUsageTime"
    
    def load_config(self):
        """載入設定檔案"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                return True, "設定檔案載入成功"
            else:
                self.config = {}
                return True, "設定檔案不存在，使用預設值"
        except Exception as e:
            self.config = {}
            return False, f"載入設定檔案失敗: {e}"
    
    def save_config(self, config_data=None, show_message=True):
        """儲存設定檔案"""
        try:
            if config_data is not None:
                self.config = config_data
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            return True, "設定檔案儲存成功"
        except Exception as e:
            return False, f"儲存設定檔案失敗: {e}"
    
    def get_config_value(self, key, default=None):
        """獲取設定值"""
        return self.config.get(key, default)
    
    def set_config_value(self, key, value):
        """設定配置值"""
        self.config[key] = value
    
    def update_config_values(self, updates):
        """批量更新配置值"""
        self.config.update(updates)
    
    def get_region_settings(self):
        """獲取區域設定"""
        return {
            'region': self.config.get('region'),
            'mana_region': self.config.get('mana_region'),
            'inventory_region': self.config.get('inventory_region'),
            'inventory_ui_region': self.config.get('inventory_ui_region'),
            'interface_ui_region': self.config.get('interface_ui_region')
        }
    
    def set_region_settings(self, regions):
        """設定區域設定"""
        for key, value in regions.items():
            if value is not None:
                self.config[key] = value
    
    def get_inventory_settings(self):
        """獲取背包設定"""
        return {
            'empty_inventory_colors': self.config.get('empty_inventory_colors', []),
            'inventory_grid_positions': self.config.get('inventory_grid_positions', []),
            'grid_offset_x': self.config.get('grid_offset_x', 0),
            'grid_offset_y': self.config.get('grid_offset_y', 0)
        }
    
    def set_inventory_settings(self, settings):
        """設定背包設定"""
        for key, value in settings.items():
            if value is not None:
                self.config[key] = value
    
    def get_trigger_settings(self):
        """獲取觸發設定"""
        return self.config.get('settings', [])
    
    def set_trigger_settings(self, settings):
        """設定觸發設定"""
        self.config['settings'] = settings
    
    def get_ui_settings(self):
        """獲取UI設定"""
        return {
            'language': self.config.get('language', 'zh-tw'),
            'always_on_top': self.config.get('always_on_top', False),
            'preview_enabled': self.config.get('preview_enabled', True),
            'multi_trigger': self.config.get('multi_trigger', False),
            'last_selected_tab': self.config.get('last_selected_tab', 0),
            'window_geometry': self.config.get('window_geometry'),
            'window_title': self.config.get('window_title', '')
        }
    
    def set_ui_settings(self, settings):
        """設定UI設定"""
        for key, value in settings.items():
            if value is not None:
                self.config[key] = value
    
    def load_usage_time_from_registry(self):
        """從註冊表載入總使用時間"""
        try:
            # 開啟註冊表鍵
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_KEY, 0, winreg.KEY_READ)
            
            # 讀取使用時間
            total_seconds, _ = winreg.QueryValueEx(key, self.REGISTRY_VALUE)
            
            # 關閉註冊表鍵
            winreg.CloseKey(key)
            
            return total_seconds
        except FileNotFoundError:
            # 如果註冊表鍵不存在，返回0
            return 0
        except Exception as e:
            print(f"載入使用時間失敗: {e}")
            return 0
    
    def save_usage_time_to_registry(self, total_seconds):
        """保存總使用時間到註冊表"""
        try:
            # 創建或開啟註冊表鍵
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_KEY)
            
            # 設定使用時間
            winreg.SetValueEx(key, self.REGISTRY_VALUE, 0, winreg.REG_DWORD, total_seconds)
            
            # 關閉註冊表鍵
            winreg.CloseKey(key)
        except Exception as e:
            print(f"保存使用時間失敗: {e}")
    
    def track_usage_time(self):
        """追蹤並保存使用時間"""
        try:
            # 計算本次使用時間
            usage_time = datetime.now() - self.start_time
            usage_seconds = int(usage_time.total_seconds())
            
            # 載入之前的總使用時間
            total_seconds = self.load_usage_time_from_registry()
            
            # 加上本次使用時間
            total_seconds += usage_seconds
            
            # 保存總使用時間
            self.save_usage_time_to_registry(total_seconds)
            
            return total_seconds
        except Exception as e:
            print(f"追蹤使用時間失敗: {e}")
            return 0
    
    def format_usage_time(self, total_seconds):
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
    
    def get_current_usage_time(self):
        """獲取當前使用時間（本次運行）"""
        current_time = datetime.now() - self.start_time
        return int(current_time.total_seconds())
    
    def get_total_usage_time(self):
        """獲取總使用時間（包含歷史記錄）"""
        historical_time = self.load_usage_time_from_registry()
        current_time = self.get_current_usage_time()
        return historical_time + current_time
    
    def backup_config(self, backup_suffix=None):
        """備份設定檔案"""
        try:
            if backup_suffix is None:
                backup_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            backup_file = f"{self.config_file}.backup_{backup_suffix}"
            
            with open(self.config_file, 'r', encoding='utf-8') as src:
                with open(backup_file, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            
            return True, f"設定檔案已備份至: {backup_file}"
        except Exception as e:
            return False, f"備份設定檔案失敗: {e}"
    
    def restore_config(self, backup_file):
        """恢復設定檔案"""
        try:
            if not os.path.exists(backup_file):
                return False, f"備份檔案不存在: {backup_file}"
            
            with open(backup_file, 'r', encoding='utf-8') as src:
                with open(self.config_file, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            
            # 重新載入設定
            self.load_config()
            
            return True, "設定檔案已恢復"
        except Exception as e:
            return False, f"恢復設定檔案失敗: {e}"


# 全域配置管理器實例
_config_manager = None


def get_config_manager():
    """獲取全域配置管理器實例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


# 便利函數，用於向後兼容
def load_config():
    """載入設定（全域便利函數）"""
    return get_config_manager().load_config()


def save_config(config_data=None, show_message=True):
    """儲存設定（全域便利函數）"""
    return get_config_manager().save_config(config_data, show_message)


def get_config_value(key, default=None):
    """獲取設定值（全域便利函數）"""
    return get_config_manager().get_config_value(key, default)


def set_config_value(key, value):
    """設定配置值（全域便利函數）"""
    return get_config_manager().set_config_value(key, value)

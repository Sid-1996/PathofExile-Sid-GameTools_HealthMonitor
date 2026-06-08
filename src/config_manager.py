"""
配置管理模組
處理應用程式的設定載入、保存、註冊表操作等功能
"""

import json
import os
import sys
from datetime import datetime
from utils import get_app_dir


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_filename="health_monitor_config.json"):
        self.config_file = os.path.join(get_app_dir(), config_filename)
        self.config = {}
    
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
        """儲存設定檔案（帶備份和異常恢復機制）"""
        try:
            if config_data is not None:
                self.config = config_data
            
            # 在保存前創建備份，防止配置文件被破壞
            backup_file = self.config_file + '.backup'
            if os.path.exists(self.config_file):
                try:
                    import shutil
                    shutil.copy2(self.config_file, backup_file)
                    print(f"[DEBUG] 配置文件備份已創建: {backup_file}")
                except Exception as backup_error:
                    print(f"[WARN] 創建備份失敗: {backup_error}")
            
            # 保存配置文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            print(f"[DEBUG] 配置文件已保存: {self.config_file}")
            return True, "設定檔案儲存成功"
        except Exception as e:
            error_msg = f"儲存設定檔案失敗: {e}"
            print(f"[ERROR] {error_msg}")
            
            # 嘗試從備份恢復
            backup_file = self.config_file + '.backup'
            if os.path.exists(backup_file):
                try:
                    import shutil
                    shutil.copy2(backup_file, self.config_file)
                    print(f"[WARN] 已從備份恢復配置文件")
                    return False, f"{error_msg} - 已從備份恢復"
                except Exception as restore_error:
                    print(f"[ERROR] 從備份恢復失敗: {restore_error}")
                    return False, f"{error_msg} - 備份恢復失敗"
            
            return False, error_msg
    
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
            'grid_offset_y': self.config.get('grid_offset_y', 0),
            'excluded_inventory_slots': self.config.get('excluded_inventory_slots', [])
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

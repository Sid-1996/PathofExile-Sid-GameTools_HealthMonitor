"""
語言系統模組
處理多語言支援、語言包載入、UI文字更新等功能
"""

import json
import os
import sys
import tkinter as tk
from tkinter import messagebox


def get_app_dir():
    """獲取應用程式目錄，適用於開發環境和打包後的exe"""
    if getattr(sys, 'frozen', False):
        # 如果是打包後的exe
        return os.path.dirname(sys.executable)
    else:
        # 如果是開發環境
        return os.path.dirname(__file__)


def load_language_packs():
    """載入語言包"""
    try:
        language_file = os.path.join(get_app_dir(), "language_packs.json")
        with open(language_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"載入語言包失敗: {e}")
        return {}


# 全域語言包
LANGUAGE_PACKS = load_language_packs()


class LanguageManager:
    """語言管理器"""
    
    def __init__(self, default_language='zh-tw'):
        self.current_language = default_language
        self.language_display_map = {
            "繁體中文": "zh-tw",
            "English": "en"
        }
        self.language_reverse_map = {v: k for k, v in self.language_display_map.items()}
    
    def get_text(self, key):
        """獲取本地化文字"""
        try:
            return LANGUAGE_PACKS.get(self.current_language, {}).get(key, f"[{key}]")
        except:
            return f"[{key}]"
    
    def change_language_display(self, display_name):
        """處理顯示名稱的語言切換"""
        language_code = self.language_display_map.get(display_name, "zh-tw")
        return self.change_language(language_code)
    
    def change_language(self, new_language):
        """切換語言"""
        if new_language == self.current_language:
            return False  # 如果選擇的語言和當前語言相同，不做任何動作
        
        old_language = self.current_language
        self.current_language = new_language
        return True
    
    def get_current_display_name(self):
        """獲取當前語言的顯示名稱"""
        return self.language_reverse_map.get(self.current_language, "繁體中文")
    
    def get_language_display_map(self):
        """獲取語言顯示映射"""
        return self.language_display_map.copy()
    
    def get_language_reverse_map(self):
        """獲取語言反向映射"""
        return self.language_reverse_map.copy()


# 全域語言管理器實例
_language_manager = None


def get_language_manager():
    """獲取全域語言管理器實例"""
    global _language_manager
    if _language_manager is None:
        _language_manager = LanguageManager()
    return _language_manager


# 便利函數，用於向後兼容
def get_text(key):
    """獲取當前語言的文字（全域便利函數）"""
    return get_language_manager().get_text(key)


def get_current_language():
    """獲取當前語言代碼"""
    return get_language_manager().current_language


def set_current_language(language_code):
    """設定當前語言代碼"""
    return get_language_manager().change_language(language_code)

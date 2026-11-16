"""
配置管理模組
處理應用程式的設定載入、保存、註冊表操作等功能
"""

import copy
import json
import logging
import math
import os
import sys
from datetime import datetime
from qt.theme import DEFAULT_THEME, normalize_theme
from utils import get_user_data_dir

logger = logging.getLogger(__name__)


DEFAULT_HOTKEYS = {"f3": "f3", "f5": "f5", "f6": "f6", "f9": "f9", "f10": "f10", "skill_timer": "ins"}


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_filename="health_monitor_config.json", config_path=None):
        # ponytail: config_path 供測試注入暫存路徑，預設行為不變
        base_dir = config_path if config_path else get_user_data_dir()
        self.config_file = os.path.join(base_dir, config_filename)
        self.config = {}
        # 最近一次載入 / 儲存結果（供 GUI 提示與診斷；不寫入磁碟、不影響既有格式）
        self.load_status = None  # 'restored_from_backup' | 'reset_to_defaults' | None
        self.load_error = None
        self.save_error = None

    def load_config(self):
        """載入設定檔案；正式檔無法解析時改用 .backup 並以還原內容修復正式檔。"""
        self.load_status = None
        self.load_error = None
        if not os.path.exists(self.config_file):
            if self._adopt_backup("正式設定檔不存在"):
                return True
            self.config = {}
            self._ensure_hotkeys()
            self._ensure_theme()
            return True
        try:
            self.config = self._read_json(self.config_file)
        except Exception as e:
            self.load_error = str(e)
            logger.error("載入設定檔案失敗: %s", e)
            if self._adopt_backup("設定檔無法解析"):
                return True
            # 正式檔與備份皆無效：改用預設值，損壞檔保留原處供診斷
            logger.error("備份亦不可用，改用預設設定（損壞的設定檔與備份保留原處；設定檔將在下次儲存時被覆寫）: %s", self.config_file)
            self.load_status = "reset_to_defaults"
            self.config = {}
            self._ensure_hotkeys()
            self._ensure_theme()
            return False
        self._ensure_hotkeys()
        self._ensure_theme()
        return True

    @staticmethod
    def _read_json(path):
        """讀取並驗證設定檔（內容必須是 JSON 物件）。"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("設定檔內容必須是 JSON 物件")
        return data

    @staticmethod
    def _read_text(path):
        """讀取原始文字（不存在回 None）。"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return None

    def _adopt_backup(self, reason):
        """備份通過解析/正規化才採用；成功時回寫正式檔（備份本身不動）。"""
        backup_file = self.config_file + ".backup"
        if not os.path.exists(backup_file):
            return False
        try:
            data = self._read_json(backup_file)
        except Exception as e:
            logger.error("%s，且備份檔無法解析: %s", reason, e)
            self.load_error = f"{self.load_error or ''} | backup: {e}".strip(" |")
            return False
        self.config = data
        self._ensure_hotkeys()
        self._ensure_theme()
        try:
            text = json.dumps(self.config, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("%s，備份內容無法序列化: %s", reason, e)
            return False
        self.load_status = "restored_from_backup"
        logger.warning("%s，已從備份還原設定", reason)
        try:
            self._write_text_atomic(self.config_file, text)
        except Exception as e:
            logger.error("已從備份還原設定，但回寫正式檔失敗: %s", e)
        return True

    # ponytail: 白名單與 settings.py 同步（F1-F11 / ins/home/pgup/pgdn/end 各含 Ctrl/Alt，F12 保留）
    _NAV_KEYS = ("ins", "home", "pgup", "pgdn", "end")
    _HOTKEY_WHITELIST = (
        {f"f{i}" for i in range(1, 12)}
        | {f"ctrl+f{i}" for i in range(1, 12)}
        | {f"alt+f{i}" for i in range(1, 12)}
        | set(_NAV_KEYS)
        | {f"ctrl+{k}" for k in _NAV_KEYS}
        | {f"alt+{k}" for k in _NAV_KEYS}
    )

    def _ensure_hotkeys(self) -> None:
        """舊檔回補 hotkeys，非法值/非白名單回退預設（大小寫正規化）。"""
        hk = self.config.get("hotkeys")
        if not isinstance(hk, dict):
            self.config["hotkeys"] = dict(DEFAULT_HOTKEYS)
            return
        fixed: dict[str, str] = {}
        for k in ("f3", "f5", "f6", "f9", "f10", "skill_timer"):
            v = hk.get(k, DEFAULT_HOTKEYS[k])
            if not isinstance(v, str) or not v.strip():
                v = DEFAULT_HOTKEYS[k]
            v = v.strip().lower()
            if v not in self._HOTKEY_WHITELIST:
                logger.warning("hotkeys 非法值 %s=%r 回退為 %s", k, v, DEFAULT_HOTKEYS[k])
                v = DEFAULT_HOTKEYS[k]
            fixed[k] = v
        self.config["hotkeys"] = fixed
        # 語言正規化（大小寫/分隔符容錯，與 language_system.normalize 一致）
        try:
            from language_system import normalize_language_code

            lang = self.config.get("language")
            if isinstance(lang, str):
                self.config["language"] = normalize_language_code(lang)
        except Exception:
            lang = self.config.get("language")
            if isinstance(lang, str):
                low = lang.strip().lower()
                if low in ("zh-tw", "zh_tw", "zh", "tw") or low.startswith("zh"):
                    self.config["language"] = "zh-tw"
                elif low == "en":
                    self.config["language"] = "en"

    def _ensure_theme(self) -> None:
        """舊檔回補 theme；非法值/不支援型別一律回退 DEFAULT_THEME（大小寫與空白正規化）。"""
        if "theme" not in self.config:
            self.config["theme"] = DEFAULT_THEME
            return
        raw = self.config["theme"]
        theme_name = normalize_theme(raw)
        normalized_input = raw.strip().lower() if isinstance(raw, str) else None
        if normalized_input != theme_name:
            logger.warning("theme 非法值 %r 回退為 %s", raw, DEFAULT_THEME)
        self.config["theme"] = theme_name

    def save_config(self, config_data=None):
        """儲存設定檔案：同目錄暫存檔 + fsync + os.replace 原子替換。

        備份只由「已確認可解析的舊正式檔」產生，損壞內容不會覆蓋有效備份。
        """
        if config_data is not None:
            self.config = config_data
        try:
            text = json.dumps(self.config, indent=2, ensure_ascii=False)
        except Exception as e:
            self.save_error = str(e)
            logger.error("儲存設定檔案失敗: %s", e)
            return False
        try:
            if self._read_text(self.config_file) == text:
                # 內容未變：不重寫、不輪替備份（避免無謂備份與暫存檔）
                self.save_error = None
                return True
            self._rotate_backup()
            self._write_text_atomic(self.config_file, text)
        except Exception as e:
            self.save_error = str(e)
            logger.error("儲存設定檔案失敗: %s", e)
            return False
        self.save_error = None
        return True

    # 舊檔要能當備份：欄位型別須符合目前讀取端的期待（缺 key 不影響，由載入端補預設）
    _BACKUP_FIELD_TYPES = {
        "health_threshold": (int, float),
        "red_h_range": (int, float),
        "green_h_range": (int, float),
        "red_saturation_min": (int, float),
        "red_value_min": (int, float),
        "green_saturation_min": (int, float),
        "green_value_min": (int, float),
        "interface_ui_mse_threshold": (int, float),
        "interface_ui_ssim_threshold": (int, float),
        "interface_ui_hist_threshold": (int, float),
        "interface_ui_color_threshold": (int, float),
        "interface_ui_region": (dict, list),  # legacy 版以 list 儲存
        "monitor_interval": (int, float),
        "preview_interval": (int, float),
        "preview_enabled": (bool,),
        "always_on_top": (bool,),
        "multi_trigger": (bool,),
        "multiple_triggers": (bool,),
        "window_title": (str,),
        "language": (str,),
        "theme": (str,),
        "hotkeys": (dict,),
        "settings": (list,),
    }

    def _rotate_backup(self):
        """僅在舊正式檔通過完整驗證時更新 .backup；備份失敗不影響主檔儲存。"""
        old_text = self._read_text(self.config_file)
        if old_text is None:
            return
        if not self._is_valid_old_config(old_text):
            return  # 無效原因已於 _is_valid_old_config 記錄
        try:
            self._write_text_atomic(self.config_file + ".backup", old_text, validate=False)
        except Exception as e:
            logger.warning("更新備份檔失敗: %s", e)

    @staticmethod
    def _type_ok(value, types):
        """欄位型別檢查：bool 不得當成數值，數值必須有限（拒絕 NaN/Infinity）。"""
        if isinstance(value, bool):
            return bool in types
        if isinstance(value, (int, float)):
            return (int in types or float in types) and math.isfinite(value)
        return isinstance(value, types)

    def _is_valid_old_config(self, text):
        """舊正式檔是否適合作為備份：可解析、根為物件、欄位型別正確、正規化不需修補。"""
        try:
            data = json.loads(text)
        except Exception as e:
            logger.warning("目前設定檔無法解析（%s），保留既有備份不覆蓋", e)
            return False
        if not isinstance(data, dict):
            logger.warning("目前設定檔根型別為 %s，保留既有備份不覆蓋", type(data).__name__)
            return False
        for key, types in self._BACKUP_FIELD_TYPES.items():
            if key in data and not self._type_ok(data[key], types):
                logger.warning("目前設定檔欄位型別錯誤（%s），保留既有備份不覆蓋", key)
                return False
        # 用與 load_config 相同的正規化流程檢查既有欄位是否會被改寫（熱鍵/主題/語言）
        saved = self.config
        try:
            self.config = copy.deepcopy(data)
            self._ensure_hotkeys()
            self._ensure_theme()
            normalized = self.config
        finally:
            self.config = saved
        if any(normalized.get(k) != v for k, v in data.items()):
            logger.warning("目前設定檔需正規化修補，保留既有備份不覆蓋")
            return False
        return True

    def _write_text_atomic(self, path, text, validate=True):
        """同目錄寫暫存檔 → flush/fsync → 驗證 → os.replace（同磁碟原子替換）。"""
        tmp = f"{path}.tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(text)
                f.flush()
                os.fsync(f.fileno())
            if validate:
                self._read_json(tmp)  # 寫出的內容必須可解析才替換正式檔
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError as e:
                    logger.warning("清理暫存檔失敗: %s", e)

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
            "region": self.config.get("region"),
            "mana_region": self.config.get("mana_region"),
            "inventory_region": self.config.get("inventory_region"),
            "inventory_ui_region": self.config.get("inventory_ui_region"),
            "interface_ui_region": self.config.get("interface_ui_region"),
        }

    def set_region_settings(self, regions):
        """設定區域設定"""
        for key, value in regions.items():
            if value is not None:
                self.config[key] = value

    def get_inventory_settings(self):
        """獲取背包設定"""
        return {
            "empty_inventory_colors": self.config.get("empty_inventory_colors", []),
            "inventory_grid_positions": self.config.get("inventory_grid_positions", []),
            "grid_offset_x": self.config.get("grid_offset_x", 0),
            "grid_offset_y": self.config.get("grid_offset_y", 0),
            "excluded_inventory_slots": self.config.get("excluded_inventory_slots", []),
        }

    def set_inventory_settings(self, settings):
        """設定背包設定"""
        for key, value in settings.items():
            if value is not None:
                self.config[key] = value

    def get_trigger_settings(self):
        """獲取觸發設定"""
        return self.config.get("settings", [])

    def set_trigger_settings(self, settings):
        """設定觸發設定"""
        self.config["settings"] = settings

    def get_ui_settings(self):
        """獲取UI設定"""
        return {
            "language": self.config.get("language", "zh-tw"),
            "theme": self.config.get("theme", DEFAULT_THEME),
            "always_on_top": self.config.get("always_on_top", False),
            "preview_enabled": self.config.get("preview_enabled", True),
            "multi_trigger": self.config.get("multi_trigger", False),
            "last_selected_tab": self.config.get("last_selected_tab", 0),
            "window_title": self.config.get("window_title", ""),
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

            with open(self.config_file, "r", encoding="utf-8") as src:
                with open(backup_file, "w", encoding="utf-8") as dst:
                    dst.write(src.read())

            return True
        except Exception as e:
            logger.error("備份設定檔案失敗: %s", e)
            return False

    def restore_config(self, backup_file):
        """恢復設定檔案"""
        try:
            if not os.path.exists(backup_file):
                logger.error("備份檔案不存在: %s", backup_file)
                return False

            with open(backup_file, "r", encoding="utf-8") as src:
                with open(self.config_file, "w", encoding="utf-8") as dst:
                    dst.write(src.read())

            # 重新載入設定
            self.load_config()

            return True
        except Exception as e:
            logger.error("恢復設定檔案失敗: %s", e)
            return False


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


def save_config(config_data=None):
    """儲存設定（全域便利函數）"""
    return get_config_manager().save_config(config_data)


def get_config_value(key, default=None):
    """獲取設定值（全域便利函數）"""
    return get_config_manager().get_config_value(key, default)


def set_config_value(key, value):
    """設定配置值（全域便利函數）"""
    return get_config_manager().set_config_value(key, value)


if __name__ == "__main__":
    import tempfile

    tmp = tempfile.mkdtemp()
    cm = ConfigManager(config_path=tmp)
    assert cm.load_config(), "load_config on empty dir should succeed"
    cm.set_config_value("language", "en")
    assert cm.save_config(), "save_config should succeed"
    cm.set_config_value("language", "zh-cn")
    assert cm.save_config(), "second save should succeed"
    cm2 = ConfigManager(config_path=tmp)
    assert cm2.load_config() and cm2.get_config_value("language") == "zh-cn", "round-trip language=zh-cn failed"
    backup = cm.config_file + ".backup"
    assert os.path.exists(backup), "second save should rotate .backup"

    # 損壞正式檔 → 由備份還原（且備份內容不被損壞文字覆蓋）
    with open(cm.config_file, "w", encoding="utf-8") as f:
        f.write('{"hotkeys": ')
    cm3 = ConfigManager(config_path=tmp)
    assert cm3.load_config(), "corrupt config should be recovered from backup"
    assert cm3.load_status == "restored_from_backup"
    assert cm3.get_config_value("language") == "en", "restored content should be the last good save"
    with open(backup, encoding="utf-8") as f:
        assert json.load(f)["language"] == "en", "valid backup must not be overwritten by corrupt data"

    # 原子寫入失敗 → 原正式檔完整、暫存檔清理
    with open(cm3.config_file, encoding="utf-8") as f:
        original = f.read()
    real_replace = os.replace

    def _boom(*args, **kwargs):
        raise OSError("disk full")

    os.replace = _boom
    try:
        cm3.set_config_value("language", "zh-tw")
        assert cm3.save_config() is False, "failed save should report False"
    finally:
        os.replace = real_replace
    with open(cm3.config_file, encoding="utf-8") as f:
        assert f.read() == original, "failed save must not damage the config file"
    assert not os.path.exists(cm3.config_file + ".tmp"), "temp file should be cleaned up"
    print("config_manager self-check OK")

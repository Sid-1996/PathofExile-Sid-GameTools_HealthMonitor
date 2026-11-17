"""config_manager 讀寫 round-trip、備份復原與原子寫入測試。"""

import json
import os
import shutil
from pathlib import Path

import pytest

from config_manager import ConfigManager

CONFIG_NAME = "health_monitor_config.json"


def _backup_path(cm):
    return cm.config_file + ".backup"


def _read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_raw(path, text):
    Path(path).write_text(text, encoding="utf-8")


def test_save_load_roundtrip(tmp_config_manager):
    cm = tmp_config_manager
    cm.set_config_value("language", "en")
    ok = cm.save_config()
    assert ok

    from config_manager import ConfigManager

    cm2 = ConfigManager(config_path=os.path.dirname(cm.config_file))
    ok = cm2.load_config()
    assert ok
    assert cm2.get_config_value("language") == "en"
    assert cm2.load_status is None, "正常載入不應標記異常狀態"


def test_missing_config_uses_defaults(tmp_config_manager):
    cm = tmp_config_manager
    ok = cm.load_config()
    assert ok
    assert cm.get_config_value("language", "zh-tw") == "zh-tw"


def test_ui_settings_defaults(tmp_config_manager):
    cm = tmp_config_manager
    ui = cm.get_ui_settings()
    assert ui["language"] == "zh-tw"
    assert ui["always_on_top"] is False


def test_trigger_settings_roundtrip(tmp_config_manager):
    cm = tmp_config_manager
    settings = [{"type": "HP", "percent": 30, "key": "1"}]
    cm.set_trigger_settings(settings)
    assert cm.get_trigger_settings() == settings


def test_corrupt_config_is_restored_from_backup(tmp_config_manager):
    cm = tmp_config_manager
    cm.set_config_value("health_threshold", 0.55)
    cm.set_config_value("language", "en")
    assert cm.save_config() is True
    cm.set_config_value("language", "zh-cn")
    assert cm.save_config() is True  # 產生 .backup（內容為 0.55 / en）
    _write_raw(cm.config_file, '{"hotkeys": {"f3":')  # 模擬中途截斷

    from config_manager import ConfigManager

    fresh = ConfigManager(config_path=os.path.dirname(cm.config_file))
    assert fresh.load_config() is True
    assert fresh.load_status == "restored_from_backup"
    assert fresh.get_config_value("health_threshold") == 0.55
    assert fresh.get_config_value("language") == "en", "不應套用損壞前未完成的變更"
    assert _read_json(fresh.config_file)["health_threshold"] == 0.55, "正式檔應被修復"
    assert _read_json(_backup_path(cm))["health_threshold"] == 0.55, "備份不得被損壞內容覆蓋"


def test_corrupt_config_and_invalid_backup_falls_back_to_defaults(tmp_config_manager):
    cm = tmp_config_manager
    _write_raw(cm.config_file, "{broken")
    _write_raw(_backup_path(cm), "not json either")

    from config_manager import ConfigManager

    fresh = ConfigManager(config_path=os.path.dirname(cm.config_file))
    assert fresh.load_config() is False
    assert fresh.load_status == "reset_to_defaults"
    assert fresh.get_ui_settings()["language"] == "zh-tw"
    assert fresh.load_error, "應保留可診斷資訊"


def test_missing_config_is_restored_from_backup(tmp_config_manager):
    cm = tmp_config_manager
    cm.set_config_value("health_threshold", 0.42)
    assert cm.save_config() is True
    shutil.copy2(cm.config_file, _backup_path(cm))
    os.remove(cm.config_file)

    from config_manager import ConfigManager

    fresh = ConfigManager(config_path=os.path.dirname(cm.config_file))
    assert fresh.load_config() is True
    assert fresh.load_status == "restored_from_backup"
    assert fresh.get_config_value("health_threshold") == 0.42
    assert os.path.exists(cm.config_file), "還原時應回寫正式檔"


def test_save_after_corruption_does_not_overwrite_valid_backup(tmp_config_manager):
    cm = tmp_config_manager
    cm.set_config_value("health_threshold", 0.55)
    assert cm.save_config() is True
    cm.set_config_value("health_threshold", 0.66)
    assert cm.save_config() is True  # .backup 內容為 0.55
    valid_backup = _read_json(_backup_path(cm))
    _write_raw(cm.config_file, '{"health_threshold":')  # 損壞

    from config_manager import ConfigManager

    saver = ConfigManager(config_path=os.path.dirname(cm.config_file))  # 刻意不先 load
    saver.config = {"health_threshold": 0.9}
    assert saver.save_config() is True
    assert _read_json(saver.config_file)["health_threshold"] == 0.9
    assert _read_json(_backup_path(cm)) == valid_backup, "損壞檔不得覆蓋有效備份"


def test_atomic_write_failure_keeps_original_config(tmp_config_manager, monkeypatch):
    cm = tmp_config_manager
    cm.set_config_value("health_threshold", 0.9)
    assert cm.save_config() is True
    original = Path(cm.config_file).read_text(encoding="utf-8")

    import config_manager as cm_mod

    def _fail(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(cm_mod.os, "replace", _fail)
    cm.set_config_value("health_threshold", 0.1)
    assert cm.save_config() is False
    assert Path(cm.config_file).read_text(encoding="utf-8") == original
    assert not os.path.exists(cm.config_file + ".tmp"), "暫存檔應被清理"
    assert cm.save_error, "應保留失敗原因供 GUI 與診斷使用"


def test_backup_update_failure_keeps_config_valid(tmp_config_manager):
    cm = tmp_config_manager
    assert cm.save_config() is True
    os.mkdir(_backup_path(cm))  # .backup 路徑被目錄佔用 → 輪替必定失敗
    cm.set_config_value("language", "en")
    assert cm.save_config() is True, "備份失敗不應讓整次儲存失敗"
    assert _read_json(cm.config_file)["language"] == "en"
    assert not os.path.exists(cm.config_file + ".tmp")
    assert not os.path.exists(_backup_path(cm) + ".tmp")


def test_repeated_save_does_not_accumulate_backups_or_temp_files(tmp_config_manager):
    cm = tmp_config_manager
    base_dir = os.path.dirname(cm.config_file)
    assert cm.save_config() is True
    assert not os.path.exists(_backup_path(cm)), "首次儲存沒有舊檔可備份"
    assert cm.save_config() is True
    assert not os.path.exists(_backup_path(cm)), "內容未變不應產生備份"

    cm.set_config_value("health_threshold", 0.55)
    assert cm.save_config() is True
    assert os.path.exists(_backup_path(cm))
    backup_before = _read_json(_backup_path(cm))

    assert cm.save_config() is True  # 重複儲存相同內容
    assert _read_json(_backup_path(cm)) == backup_before, "不應做多餘的備份輪替"
    assert sorted(os.listdir(base_dir)) == [CONFIG_NAME, CONFIG_NAME + ".backup"]


@pytest.mark.parametrize(
    "invalid_old",
    [
        "[]",  # 根型別錯誤（語法正確）
        json.dumps({"hotkeys": "f3"}),  # 欄位型別錯誤
        json.dumps({"settings": "not-a-list"}),
        json.dumps({"health_threshold": "high"}),
        json.dumps({"hotkeys": {"f3": "bogus"}}),  # 值非法（正規化會修補）
        json.dumps({"theme": "purple"}),
    ],
)
def test_invalid_old_config_never_overwrites_valid_backup(tmp_config_manager, invalid_old):
    cm = tmp_config_manager
    cm.set_config_value("health_threshold", 0.55)
    assert cm.save_config() is True
    cm.set_config_value("language", "en")
    assert cm.save_config() is True  # .backup 內容為 0.55
    valid_backup = _read_json(_backup_path(cm))

    _write_raw(cm.config_file, invalid_old)
    saver = ConfigManager(config_path=os.path.dirname(cm.config_file))  # 刻意不先 load
    saver.config = {"health_threshold": 0.9}
    assert saver.save_config() is True, "無效舊檔不應讓儲存失敗"
    assert _read_json(saver.config_file)["health_threshold"] == 0.9
    assert _read_json(_backup_path(cm)) == valid_backup, "無效舊檔不得覆蓋有效備份"


@pytest.mark.parametrize(
    "raw",
    [
        '{"health_threshold": true}',
        '{"health_threshold": false}',
        '{"health_threshold": NaN}',
        '{"health_threshold": Infinity}',
        '{"health_threshold": -Infinity}',
        '{"preview_enabled": 1}',  # 數值出現在 bool 欄位
    ],
)
def test_numeric_type_boundaries_rejected_as_backup(tmp_config_manager, raw):
    """bool 與非有限浮點數不得被當成有效舊設定（不得覆蓋有效備份）。"""
    cm = tmp_config_manager
    cm.set_config_value("health_threshold", 0.55)
    assert cm.save_config() is True
    cm.set_config_value("language", "en")
    assert cm.save_config() is True
    valid_backup = _read_json(_backup_path(cm))

    _write_raw(cm.config_file, raw)
    saver = ConfigManager(config_path=os.path.dirname(cm.config_file))
    saver.config = {"health_threshold": 0.9}
    assert saver.save_config() is True, "無效舊檔不應讓儲存失敗"
    assert _read_json(_backup_path(cm)) == valid_backup, f"{raw} 不得覆蓋有效備份"


@pytest.mark.parametrize("raw", ['{"health_threshold": 1}', '{"health_threshold": 0.7}', '{"red_h_range": 5.0}'])
def test_finite_numeric_old_config_still_rotates_backup(tmp_config_manager, raw):
    """正常 int / float 仍屬有效舊設定（不得過度拒絕）。"""
    cm = tmp_config_manager
    cm.set_config_value("health_threshold", 0.55)
    assert cm.save_config() is True
    cm.set_config_value("language", "en")
    assert cm.save_config() is True
    valid_backup = _read_json(_backup_path(cm))

    _write_raw(cm.config_file, raw)
    saver = ConfigManager(config_path=os.path.dirname(cm.config_file))
    saver.config = {"health_threshold": 0.9}
    assert saver.save_config() is True
    assert _read_json(_backup_path(cm)) != valid_backup, "合法數值舊檔應正常輪替備份"


def test_unrepairable_callers_can_still_load_after_double_corruption(tmp_config_manager):
    """雙檔皆損壞：預設設定必須完整可用，且後續儲存能建立新的有效設定檔。"""
    cm = tmp_config_manager
    _write_raw(cm.config_file, "{broken")
    _write_raw(_backup_path(cm), "also broken")

    fresh = ConfigManager(config_path=os.path.dirname(cm.config_file))
    assert fresh.load_config() is False
    assert fresh.load_status == "reset_to_defaults"
    # 回 False 但記憶體設定必須是可用的預設值（MainWindow 不看回傳值）
    assert isinstance(fresh.config, dict) and fresh.config
    assert fresh.config["hotkeys"] and fresh.config["theme"]
    assert fresh.get_ui_settings()["language"] == "zh-tw"

    fresh.set_config_value("window_title", "My Game Window")
    assert fresh.save_config() is True
    assert _read_json(fresh.config_file)["window_title"] == "My Game Window"

    reloaded = ConfigManager(config_path=os.path.dirname(cm.config_file))
    assert reloaded.load_config() is True, "儲存後應能正常載入（不再走預設值）"
    assert reloaded.load_status is None
    assert reloaded.get_config_value("window_title") == "My Game Window"


def test_double_corruption_notice_is_accurate_in_all_languages():
    """三語言的 defaults 提示都必須說明：損壞檔保留供診斷，但設定檔會在下次儲存時被覆寫。"""
    packs = json.loads((Path(__file__).resolve().parent.parent / "src" / "language_packs.json").read_text(encoding="utf-8"))
    langs = ("zh-tw", "en", "zh-cn")
    for lang in langs:
        text = packs[lang]["config_reset_to_defaults"]
        assert ("diagnos" in text) or ("診斷" in text) or ("诊断" in text), f"{lang} 提示未說明損壞檔保留供診斷"
        assert ("overwritten" in text) or ("覆寫" in text) or ("覆写" in text), f"{lang} 提示未說明設定檔將被覆寫"
        assert packs[lang]["config_restored_from_backup"], f"{lang} 缺少備份還原提示"

    keys = {lang: {k for k in packs[lang] if k.startswith("config_")} for lang in langs}
    assert keys["zh-tw"] == keys["en"] == keys["zh-cn"], "三語言的 config 提示鍵必須一致"


def _make_corrupt_with_valid_backup(cm):
    """建立「正式檔損壞、備份有效」狀態：回傳（正式檔路徑, 備份路徑）。"""
    cm.set_config_value("health_threshold", 0.55)
    cm.set_config_value("language", "en")
    assert cm.save_config() is True
    cm.set_config_value("language", "zh-cn")
    assert cm.save_config() is True  # 產生有效 .backup（內容為 0.55 / en）
    _write_raw(cm.config_file, '{"hotkeys": {"f3":')
    return cm.config_file, _backup_path(cm)


def test_reload_after_backup_restore_keeps_pending_status(tmp_config_manager):
    """第二次載入（模擬 GUI 建立時的重複載入）不得清除尚未通知的還原事件。"""
    cm = tmp_config_manager
    config_file, backup_file = _make_corrupt_with_valid_backup(cm)

    fresh = ConfigManager(config_path=os.path.dirname(cm.config_file))
    assert fresh.load_config() is True
    assert fresh.load_status == "restored_from_backup"

    # 正式檔已被修復，第二次載入本身成功，但待通知事件必須保留給 GUI
    assert fresh.load_config() is True
    assert fresh.load_status == "restored_from_backup", "第二次載入不得清除待通知的還原事件"
    assert fresh.get_config_value("health_threshold") == 0.55
    assert _read_json(config_file)["health_threshold"] == 0.55, "正式檔內容不得被第二次載入破壞"
    assert _read_json(backup_file)["health_threshold"] == 0.55, "備份不得被覆蓋"


def test_consume_load_status_is_one_shot(tmp_config_manager):
    """GUI 消費事件後即清除：同一事件只會被提示一次。"""
    cm = tmp_config_manager
    _make_corrupt_with_valid_backup(cm)

    fresh = ConfigManager(config_path=os.path.dirname(cm.config_file))
    assert fresh.load_config() is True
    assert fresh.consume_load_status() == "restored_from_backup"
    assert fresh.consume_load_status() is None
    assert fresh.load_status is None


def test_next_launch_does_not_inherit_pending_status(tmp_config_manager):
    """狀態只存在於記憶體：下一次啟動（新 manager）不得沿用舊的還原事件。"""
    cm = tmp_config_manager
    _make_corrupt_with_valid_backup(cm)

    fresh = ConfigManager(config_path=os.path.dirname(cm.config_file))
    assert fresh.load_config() is True
    assert fresh.load_status == "restored_from_backup"

    relaunch = ConfigManager(config_path=os.path.dirname(cm.config_file))
    assert relaunch.load_config() is True
    assert relaunch.load_status is None, "新的啟動不得沿用上一輪的待通知事件"
    assert relaunch.consume_load_status() is None


def test_double_corruption_status_survives_reload(tmp_config_manager):
    """雙檔皆損壞：重複載入仍維持 defaults 提示，且記憶體設定仍可用。"""
    cm = tmp_config_manager
    _write_raw(cm.config_file, "{broken")
    _write_raw(_backup_path(cm), "not json either")

    fresh = ConfigManager(config_path=os.path.dirname(cm.config_file))
    assert fresh.load_config() is False
    assert fresh.load_status == "reset_to_defaults"
    assert fresh.load_config() is False
    assert fresh.load_status == "reset_to_defaults", "defaults 提示不得被第二次載入清除"
    assert fresh.get_ui_settings()["language"] == "zh-tw"


def test_normal_load_produces_no_pending_status(tmp_config_manager):
    """正常載入不產生任何待通知事件（GUI 不該收到錯誤通知）。"""
    cm = tmp_config_manager
    cm.set_config_value("language", "en")
    assert cm.save_config() is True

    fresh = ConfigManager(config_path=os.path.dirname(cm.config_file))
    assert fresh.load_config() is True
    assert fresh.load_status is None
    assert fresh.consume_load_status() is None


def test_repeated_load_does_not_touch_files(tmp_config_manager):
    """重複載入不得產生暫存檔，也不得改動正式檔與備份內容。"""
    cm = tmp_config_manager
    base_dir = os.path.dirname(cm.config_file)
    _make_corrupt_with_valid_backup(cm)

    fresh = ConfigManager(config_path=base_dir)
    assert fresh.load_config() is True
    main_before = Path(cm.config_file).read_text(encoding="utf-8")
    backup_before = Path(_backup_path(cm)).read_text(encoding="utf-8")

    assert fresh.load_config() is True
    assert fresh.load_config() is True
    assert Path(cm.config_file).read_text(encoding="utf-8") == main_before
    assert Path(_backup_path(cm)).read_text(encoding="utf-8") == backup_before
    assert sorted(os.listdir(base_dir)) == [CONFIG_NAME, CONFIG_NAME + ".backup"]

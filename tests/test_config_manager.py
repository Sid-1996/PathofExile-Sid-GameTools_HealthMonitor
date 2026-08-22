"""config_manager 讀寫 round-trip 與設定值存取測試。"""


def test_save_load_roundtrip(tmp_config_manager):
    cm = tmp_config_manager
    cm.set_config_value("language", "en")
    ok = cm.save_config()
    assert ok

    from config_manager import ConfigManager
    import os

    cm2 = ConfigManager(config_path=os.path.dirname(cm.config_file))
    ok = cm2.load_config()
    assert ok
    assert cm2.get_config_value("language") == "en"


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

"""language_system 字串查詢與語言切換測試。"""

from language_system import LanguageManager


def test_get_text_zh_tw():
    lm = LanguageManager("zh-tw")
    text = lm.get_text("tab_health_monitor")
    assert "[tab_health_monitor]" not in text
    assert text


def test_get_text_unknown_key():
    lm = LanguageManager("zh-tw")
    assert lm.get_text("nonexistent_key") == "[nonexistent_key]"


def test_change_language_noop_same():
    lm = LanguageManager("zh-tw")
    assert lm.change_language("zh-tw") is False


def test_change_language_switch():
    lm = LanguageManager("zh-tw")
    assert lm.change_language("en") is True
    assert lm.current_language == "en"
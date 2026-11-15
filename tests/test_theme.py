"""qt.theme token / 正規化 / 設定持久化測試（純 Python，不引入 pytest-qt）。

對比度一律使用 WCAG 2.x 相對亮度公式（非簡化 RGB 差值）。
"""

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from qt import theme

_ROOT = Path(__file__).resolve().parent.parent

# 會被當成「文字顏色」使用的 token（必須通過 AA 4.5:1）
_TEXT_TOKENS = (
    "fg",
    "fg_muted",
    "accent",
    "success",
    "warning",
    "error",
    "info",
    "success_soft",
    "warning_soft",
    "error_soft",
    "info_soft",
    "monitor",
)


# ── WCAG 對比度 ──


def _channel(value: int) -> float:
    c = value / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")[:6]
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def _contrast_ratio(fg: str, bg: str) -> float:
    a, b = _relative_luminance(fg), _relative_luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


# ── fixtures / helpers ──


@pytest.fixture
def fake_fluent(monkeypatch):
    """攔截 qfluentwidgets 呼叫，回傳記錄下來的套用順序（不建立 QApplication）。"""
    calls: list[str] = []
    monkeypatch.setattr(theme, "_applied_theme", None)
    monkeypatch.setattr(theme, "_apply_fluent_theme", lambda name: calls.append(name))
    return calls


def _write_config(cm, data: dict) -> None:
    with open(cm.config_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _reload(cm):
    from config_manager import ConfigManager

    fresh = ConfigManager(config_path=os.path.dirname(cm.config_file))
    assert fresh.load_config() is True
    return fresh


# ── A. normalize_theme ──


@pytest.mark.parametrize("value", ["dark", "DARK", " Dark ", "light", "LIGHT", " Light ", "\tLight\n"])
def test_normalize_accepts_valid_with_case_and_whitespace(value):
    assert theme.normalize_theme(value) == value.strip().lower()


@pytest.mark.parametrize("value", ["blue", "", "  ", 123, 1.5, None, True, [], {}, "darkk", "auto"])
def test_normalize_falls_back_to_dark(value):
    assert theme.normalize_theme(value) == theme.DEFAULT_THEME == "dark"


def test_default_theme_is_dark():
    assert theme.DEFAULT_THEME == "dark"
    assert set(theme.VALID_THEMES) == {"dark", "light"}


# ── B. TOKENS 結構 / 格式 / 對比度 ──


def test_dark_and_light_token_keys_identical():
    assert set(theme.TOKENS["dark"]) == set(theme.TOKENS["light"])
    assert set(theme.TOKENS) == {"dark", "light"}


def test_all_tokens_are_valid_lowercase_hex():
    for name, tok in theme.TOKENS.items():
        for key, value in tok.items():
            assert re.fullmatch(r"#[0-9a-f]{6}([0-9a-f]{2})?", value), f"{name}.{key} 非合法 HEX: {value!r}"


def test_token_hex_format_consistent_across_themes():
    for key, dark_value in theme.TOKENS["dark"].items():
        assert len(theme.TOKENS["light"][key]) == len(dark_value), f"{key} 兩套主題 HEX 格式不一致"


def test_required_tokens_present():
    required = {
        "window_bg",
        "surface",
        "border",
        "border_strong",
        "fg",
        "fg_muted",
        "badge_fg",
        "accent",
        "success",
        "warning",
        "error",
        "info",
        "success_soft",
        "warning_soft",
        "error_soft",
        "info_soft",
        "monitor",
        "statusbar_bg",
        "toast_bg",
    }
    assert required == set(theme.TOKENS["dark"])


def test_dark_tokens_match_existing_gui_colors():
    """dark token 必須與改動前 GUI 實際使用的色值一致（不得趁 Phase 0 重新設計）。"""
    expected = {
        "window_bg": "#202020",
        "surface": "#1e1e2e",
        "border": "#3b3b3b",
        "border_strong": "#3d3d5c",
        "fg": "#f8f8f2",
        "fg_muted": "#b8b8c8",
        "badge_fg": "#000000",
        "accent": "#bd93f9",
        "success": "#50fa7b",
        "warning": "#f1fa8c",
        "error": "#ff5555",
        "info": "#8be9fd",
        "success_soft": "#a6e3a1",
        "warning_soft": "#f9e2af",
        "error_soft": "#f38ba8",
        "info_soft": "#89b4fa",
        "monitor": "#00bcd4",
        "statusbar_bg": "#1e1e2ed9",
        "toast_bg": "#282a36f5",
    }
    assert theme.TOKENS["dark"] == expected


@pytest.mark.parametrize("name", ["dark", "light"])
def test_text_tokens_meet_wcag_aa_on_window_bg(name):
    tok = theme.TOKENS[name]
    for key in _TEXT_TOKENS:
        ratio = _contrast_ratio(tok[key], tok["window_bg"])
        assert ratio >= 4.5, f"{name}.{key} 對 window_bg 對比僅 {ratio:.2f}:1"


@pytest.mark.parametrize("name", ["dark", "light"])
def test_text_tokens_meet_wcag_aa_on_surface(name):
    tok = theme.TOKENS[name]
    for key in _TEXT_TOKENS:
        ratio = _contrast_ratio(tok[key], tok["surface"])
        assert ratio >= 4.5, f"{name}.{key} 對 surface 對比僅 {ratio:.2f}:1"


def test_contrast_helper_reference_values():
    """校準：白底黑字 21:1、同色 1:1。"""
    assert round(_contrast_ratio("#000000", "#ffffff"), 2) == 21.0
    assert round(_contrast_ratio("#f0f4f9", "#f0f4f9"), 2) == 1.0


# ── C. apply_theme ──


def test_apply_theme_applies_dark_and_reports_name(fake_fluent):
    assert theme.apply_theme("dark") == "dark"
    assert fake_fluent == ["dark"]
    assert theme.current_theme() == "dark"
    assert theme.current_tokens() is theme.TOKENS["dark"]


def test_apply_theme_normalizes_input(fake_fluent):
    assert theme.apply_theme(" LIGHT ") == "light"
    assert fake_fluent == ["light"]
    assert theme.current_tokens() == theme.TOKENS["light"]


@pytest.mark.parametrize("value", ["blue", 123, None, ""])
def test_apply_theme_invalid_falls_back_to_dark(fake_fluent, value):
    theme.apply_theme("light")
    fake_fluent.clear()
    assert theme.apply_theme(value) == "dark"
    assert fake_fluent == ["dark"]


def test_apply_theme_is_idempotent(fake_fluent):
    theme.apply_theme("light")
    theme.apply_theme("light")
    theme.apply_theme("LIGHT")
    assert fake_fluent == ["light"], "重複套用同一主題不得再呼叫 qfluentwidgets"


def test_apply_theme_accent_is_token_derived():
    assert theme.accent_color("dark") == theme.TOKENS["dark"]["accent"] == "#bd93f9"
    assert theme.accent_color("light") == theme.TOKENS["light"]["accent"]
    assert theme.accent_color("bogus") == theme.TOKENS["dark"]["accent"]


def test_apply_theme_does_not_touch_config_on_disk(tmp_config_manager, fake_fluent):
    cm = tmp_config_manager
    cm.set_config_value("language", "en")
    cm.set_config_value("theme", "dark")
    assert cm.save_config() is True
    before = Path(cm.config_file).read_bytes()

    theme.apply_theme("dark")
    theme.apply_theme("light")

    assert Path(cm.config_file).read_bytes() == before, "套用主題不得改寫設定檔"
    assert cm.config["language"] == "en"
    assert cm.config["theme"] == "dark"


def test_theme_module_import_does_not_touch_qt():
    """import qt.theme 時不得建立/操作 QApplication（Qt 一律延遲 import）。"""
    code = f"import sys;sys.path.insert(0, r'{_ROOT / 'src'}');import qt.theme as t;assert 'PySide6' not in sys.modules, 'qt.theme 不得在 import 時載入 Qt';assert t.current_theme() == 'dark'"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr


# ── D. ConfigManager 相容性（舊設定檔 / 非法值 / 持久化）──


def test_old_config_without_theme_defaults_to_dark(tmp_config_manager):
    cm = tmp_config_manager
    _write_config(cm, {"language": "en", "always_on_top": True, "health_threshold": 35})
    fresh = _reload(cm)
    assert fresh.get_config_value("theme") == "dark"
    assert fresh.get_ui_settings()["theme"] == "dark"
    # 其他設定值不得被重設
    assert fresh.get_config_value("language") == "en"
    assert fresh.get_config_value("always_on_top") is True
    assert fresh.get_config_value("health_threshold") == 35


def test_missing_file_defaults_to_dark(tmp_config_manager):
    assert tmp_config_manager.get_config_value("theme") == "dark"
    assert tmp_config_manager.get_ui_settings()["theme"] == "dark"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("dark", "dark"),
        ("light", "light"),
        ("LIGHT", "light"),
        (" Light ", "light"),
    ],
)
def test_valid_theme_values_loaded(tmp_config_manager, raw, expected):
    cm = tmp_config_manager
    _write_config(cm, {"theme": raw})
    fresh = _reload(cm)
    assert fresh.get_config_value("theme") == expected


@pytest.mark.parametrize("raw", ["blue", 123, None, "", "  ", ["light"], {"theme": "light"}, True])
def test_invalid_theme_values_fall_back_to_dark(tmp_config_manager, caplog, raw):
    cm = tmp_config_manager
    _write_config(cm, {"theme": raw, "language": "en"})
    with caplog.at_level(logging.WARNING, logger="config_manager"):
        fresh = _reload(cm)
    assert fresh.get_config_value("theme") == "dark"
    assert fresh.get_config_value("language") == "en", "回退主題不得影響其他設定"
    assert any("theme" in rec.getMessage() for rec in caplog.records), "非法值應留下 warning"


def test_theme_light_persists_roundtrip(tmp_config_manager):
    cm = tmp_config_manager
    _write_config(cm, {"language": "en"})  # 模擬既有使用者設定檔
    cm.load_config()
    cm.set_config_value("theme", "light")
    assert cm.save_config() is True

    fresh = _reload(cm)
    assert fresh.get_config_value("theme") == "light"
    assert fresh.get_ui_settings()["theme"] == "light"
    assert os.path.exists(cm.config_file + ".backup")

    with open(cm.config_file, encoding="utf-8") as f:
        assert json.load(f)["theme"] == "light"


def test_save_config_writes_theme_key(tmp_config_manager):
    cm = tmp_config_manager
    assert cm.get_config_value("theme") == "dark"
    assert cm.save_config() is True
    with open(cm.config_file, encoding="utf-8") as f:
        assert json.load(f)["theme"] == "dark"

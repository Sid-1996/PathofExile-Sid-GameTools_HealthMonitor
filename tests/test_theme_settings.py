"""Phase 4A：Dark / Light 主題選擇器測試（外觀 UI、切換、防重入、持久化）。

以 offscreen QPA 建立真實 MainWindow（沿用 conftest.theme_window fixture），
驗證真實行為：實際套用的主題、fan-out 次數、設定值、設定檔落地；不只驗證 mock 被呼叫。

注意：真實「關閉程式 → 重開」不在此驗證（無獨立程序環境），僅驗證設定檔往返 +
以設定值重新套用主題（自動化等價驗證），真機重啟驗證另行安排。
"""

import json
import os
import time

import pytest

pytest.importorskip("PySide6.QtWidgets")

import qt.theme as theme  # noqa: E402


def _select(theme_window, name: str) -> None:
    """模擬使用者在下拉選單選取某主題（走真實 currentTextChanged 訊號路徑）。"""
    combo = theme_window.settings_tab.theme_combo
    index = combo.findData(name)
    assert index >= 0, f"下拉沒有 {name} 選項"
    combo.setCurrentIndex(index)


@pytest.fixture(autouse=True)
def _reset_theme(theme_window):
    """每個測試前還原 dark 主題與設定值（module 級 fixture 會跨測試共用）。"""
    theme._applied_theme = None
    theme.apply_theme("dark")
    theme_window.config["theme"] = "dark"
    theme_window._config_save_timer.stop()
    yield
    theme_window._config_save_timer.stop()
    theme._applied_theme = None
    theme.apply_theme("dark")
    theme_window.config["theme"] = "dark"


# ── UI ────────────────────────────────────────────────────────────────────
def test_appearance_card_visible_with_theme_selector(theme_window):
    """外觀卡片必須對使用者顯示，且只有主題選單一個下拉。"""
    from qfluentwidgets import ComboBox

    tab = theme_window.settings_tab
    card = tab.appearance_card
    assert not card.isHidden(), "外觀卡片必須對使用者顯示"
    combos = card.findChildren(ComboBox)
    assert len(combos) == 1, f"外觀卡片應只有一個下拉，實得 {len(combos)}"
    assert combos[0] is tab.theme_combo
    assert tab.theme_combo.count() == 2, "主題只提供 Dark / Light 兩項"
    assert tab.theme_combo.itemData(0) == "dark"
    assert tab.theme_combo.itemData(1) == "light"


def test_theme_option_texts_are_localized(theme_window):
    """顯示文字必須來自 i18n（不得直接顯示內部值 dark / light）。"""
    g = theme_window.get_text
    combo = theme_window.settings_tab.theme_combo
    assert combo.itemText(0) == g("theme_dark")
    assert combo.itemText(1) == g("theme_light")
    assert g("theme_dark").strip() and g("theme_light").strip()


def test_theme_i18n_keys_exist_in_every_language():
    """所有支援語系都必須有主題相關字串。"""
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    packs = json.loads((root / "src" / "language_packs.json").read_text(encoding="utf-8"))
    assert len(packs) >= 3
    for lang, data in packs.items():
        for key in ("theme", "theme_dark", "theme_light", "theme_hint"):
            assert key in data, f"{lang} 缺少 {key}"
            assert isinstance(data[key], str) and data[key].strip(), f"{lang}.{key} 為空"


def test_theme_selector_reflects_applied_theme(theme_window):
    """下拉選項必須反映「實際套用的主題」，而非僅反映設定值。"""
    tab = theme_window.settings_tab
    assert tab.theme_combo.currentData() == theme.current_theme()
    theme.apply_theme("light")
    assert tab.theme_combo.currentData() == "light"
    theme.apply_theme("dark")
    assert tab.theme_combo.currentData() == "dark"


def test_refresh_theme_does_not_emit_selection_signal(theme_window):
    """refresh_theme() 不得觸發選項變更訊號（否則會重入切換流程）。"""
    combo = theme_window.settings_tab.theme_combo
    seen: list[str] = []
    combo.currentTextChanged.connect(seen.append)
    try:
        theme_window.settings_tab.refresh_theme()
        assert seen == [], f"refresh_theme 不應發出選項變更：{seen}"
    finally:
        combo.currentTextChanged.disconnect(seen.append)


# ── 切換 ──────────────────────────────────────────────────────────────────
def test_switch_dark_to_light_applies_theme_and_updates_config(theme_window):
    """Dark → Light：立即套用主題並更新設定值。"""
    from qfluentwidgets import isDarkTheme

    tab = theme_window.settings_tab
    _select(theme_window, "light")
    assert theme.current_theme() == "light"
    assert isDarkTheme() is False
    assert theme_window.config["theme"] == "light"
    assert tab.theme_combo.currentData() == "light"


def test_switch_light_to_dark_applies_theme_and_updates_config(theme_window):
    """Light → Dark：立即套用主題並更新設定值。"""
    from qfluentwidgets import isDarkTheme

    _select(theme_window, "light")
    _select(theme_window, "dark")
    assert theme.current_theme() == "dark"
    assert isDarkTheme() is True
    assert theme_window.config["theme"] == "dark"


def test_invalid_theme_option_is_not_applied(theme_window):
    """非法選項不得套用主題、不得寫設定，UI 必須還原為實際主題。"""
    tab = theme_window.settings_tab
    before = theme.current_theme()
    tab.theme_combo.addItem("bogus", None, "neon")
    index = tab.theme_combo.findData("neon")
    try:
        tab.theme_combo.setCurrentIndex(index)
        assert theme.current_theme() == before, "非法選項不得套用主題"
        assert theme_window.config.get("theme") == before, "非法選項不得寫入設定"
        assert tab.theme_combo.currentData() == before, "UI 必須還原為實際主題"
    finally:
        tab.theme_combo.removeItem(index)


def test_single_user_switch_triggers_exactly_one_fanout(theme_window, monkeypatch):
    """單次使用者切換只觸發一次頁面 fan-out。"""
    calls: list[int] = []
    original = theme_window._fan_out_tab_themes

    def spy():
        calls.append(1)
        original()

    monkeypatch.setattr(theme_window, "_fan_out_tab_themes", spy)
    _select(theme_window, "light")
    assert len(calls) == 1, f"fan-out 應恰為 1 次，實得 {len(calls)}"


def test_theme_switch_does_not_reenter_selection_callback(theme_window):
    """切換流程不得重入：選項變更訊號只在使用者操作時發出一次。"""
    combo = theme_window.settings_tab.theme_combo
    seen: list[str] = []
    combo.currentTextChanged.connect(seen.append)
    try:
        _select(theme_window, "light")
        assert len(seen) == 1, f"選項訊號應僅在使用者操作時發出一次，實得 {len(seen)}"
    finally:
        combo.currentTextChanged.disconnect(seen.append)


def test_selecting_same_theme_does_not_reapply(theme_window, monkeypatch):
    """選取「目前已是的主题」不得重複套用或重複寫設定。"""
    calls: list[int] = []
    original = theme_window._fan_out_tab_themes

    def spy():
        calls.append(1)
        original()

    monkeypatch.setattr(theme_window, "_fan_out_tab_themes", spy)
    _select(theme_window, "light")
    assert len(calls) == 1
    combo = theme_window.settings_tab.theme_combo
    combo.setCurrentIndex(combo.findData("light"))
    assert len(calls) == 1, "同一主題不得再次觸發 fan-out"


# ── 設定持久化 ────────────────────────────────────────────────────────────
def test_language_refresh_keeps_theme_and_relabels_options(theme_window):
    """語言刷新只換顯示文字：不得改變主題，也不得觸發選項變更訊號。"""
    tab = theme_window.settings_tab
    _select(theme_window, "light")
    combo = tab.theme_combo
    seen: list[str] = []
    combo.currentTextChanged.connect(seen.append)
    try:
        theme_window.language_manager.change_language("en")
        tab.update_language()
        g = theme_window.get_text
        assert combo.itemText(combo.findData("light")) == g("theme_light")
        assert combo.itemText(combo.findData("dark")) == g("theme_dark")
        assert combo.currentData() == "light"
        assert theme.current_theme() == "light", "語言刷新不得改變主題"
        assert seen == [], f"語言刷新不得觸發選項變更：{seen}"
    finally:
        combo.currentTextChanged.disconnect(seen.append)
        theme_window.language_manager.change_language("zh-tw")
        tab.update_language()


def test_theme_change_is_written_to_config_file(theme_window):
    """切換後既有 debounce 儲存機制必須把 theme 寫進設定檔。"""
    from PySide6.QtWidgets import QApplication

    _select(theme_window, "light")
    cfg_path = theme_window.config_manager.config_file
    deadline = time.time() + 3.0
    persisted = False
    while time.time() < deadline:
        QApplication.processEvents()
        time.sleep(0.05)
        try:
            with open(cfg_path, encoding="utf-8") as f:
                persisted = json.load(f).get("theme") == "light"
        except Exception:
            pass
        if persisted:
            break
    assert persisted, f"theme 未寫入設定檔：{cfg_path}"


def test_theme_survives_config_roundtrip(theme_window):
    """設定檔往返：切 Light → 存檔 → 重新載入仍為 light → 以設定值可恢復主題。

    這是「重啟」的自動化等價驗證（設定檔往返 + 重新套用），非真實程序重啟。
    """
    from config_manager import ConfigManager

    _select(theme_window, "light")
    theme_window.save_config()
    cfg_dir = os.path.dirname(theme_window.config_manager.config_file)
    cm = ConfigManager(config_path=cfg_dir)
    cm.load_config()
    assert cm.get_config_value("theme") == "light"
    theme._applied_theme = None
    theme.apply_theme(cm.get_config_value("theme"))
    assert theme.current_theme() == "light"


def test_page_refresh_does_not_schedule_config_save(theme_window):
    """頁面刷新不得排程儲存（避免刷新與使用者切換互相覆蓋）。"""
    theme_window._config_save_timer.stop()
    theme.apply_theme("light")
    assert theme_window._config_save_timer.isActive() is False, "頁面刷新不應排程設定儲存"


def test_config_without_theme_key_defaults_to_dark(tmp_path):
    """沒有 theme key 的舊設定必須初始化為 Dark。"""
    from config_manager import ConfigManager

    (tmp_path / "health_monitor_config.json").write_text(json.dumps({"language": "zh-tw"}), encoding="utf-8")
    cm = ConfigManager(config_path=str(tmp_path))
    cm.load_config()
    assert cm.get_config_value("theme") == "dark"


def test_illegal_theme_value_in_config_falls_back_to_dark(tmp_path):
    """設定檔內非法 theme 值必須安全回退 Dark。"""
    from config_manager import ConfigManager

    (tmp_path / "health_monitor_config.json").write_text(json.dumps({"theme": "neon"}), encoding="utf-8")
    cm = ConfigManager(config_path=str(tmp_path))
    cm.load_config()
    assert cm.get_config_value("theme") == "dark"

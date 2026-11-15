"""Phase 2A 測試：StatusTab / AboutTab 的主題 Token 遷移與刷新管線整合。
Phase 2B 測試：SkillTimerModule（ComboTab 內嵌）＋ HelpTab 的主題 Token 遷移。

使用 tests/conftest.py 的 `theme_window`（offscreen 真實 MainWindow，單一實例共用）。
每個測試開始都回到 dark，並在結束後還原日誌狀態，避免測試互相污染。
"""

import copy
import re

import pytest

pytest.importorskip("PySide6.QtWidgets")

STATUS_TYPES = ["success", "warning", "error", "info", "hotkey", "monitor"]
TYPE_TOKENS = {
    "success": "success",
    "warning": "warning",
    "error": "error",
    "info": "info",
    "hotkey": "accent",
    "monitor": "monitor",
}

LEGACY_DARK_STATUS_TITLE = "font-size: 20px; font-weight: 600; color: #f8f8f2;"
LEGACY_DARK_STATUS_COUNT = "color: #b8b8c8;"
LEGACY_DARK_ABOUT_CARD = "QWidget { background-color: #1e1e2e; border: 1px solid #3b3b3b; border-radius: 8px; }QLabel { background: transparent; }"


# ── fixtures ─────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _isolate(theme_window):
    """每個測試前回到 dark 並重設日誌，結束後還原（避免測試間污染）。"""
    import qt.theme as theme

    st = theme_window.status_tab
    theme.apply_theme("dark")
    snapshot = list(st.status_log)
    yield
    theme.apply_theme("dark")
    st.status_log = snapshot
    st.last_status_message = snapshot[-1][1] if snapshot else ""
    st.auto_scroll_cb.setChecked(True)
    st._refresh_status_display()


@pytest.fixture
def theme(theme_window):
    import qt.theme as theme_mod

    return theme_mod


def _reset_log(tab, entries=None):
    """直接重設日誌（不經 add_status_message，避免多出 records_cleared 行）。"""
    from qt.status import _message_color

    tab.status_log = list(entries or [])
    tab.last_status_message = tab.status_log[-1][1] if tab.status_log else ""
    tab.text_edit.clear()
    for now, message, mtype in tab.status_log:
        tab._insert_line(f"[{now}] {message}", _message_color(mtype))
    tab._update_status_count()


def _log_line_colors(tab):
    """逐 block 取第一段文字的前景色（None = 空 block）。"""
    from PySide6.QtCore import Qt

    doc = tab.text_edit.document()
    colors = []
    block = doc.begin()
    while block.isValid():
        it = block.begin()
        color = None
        if not it.atEnd():
            frag = it.fragment()
            brush = frag.charFormat().foreground()
            if frag.isValid() and brush.style() != Qt.BrushStyle.NoBrush:
                color = brush.color().name()
        colors.append(color)
        block = block.next()
    return colors


# ── StatusTab：顏色 token ────────────────────────────────────────────────
def test_status_dark_uses_dark_tokens(theme_window, theme):
    st = theme_window.status_tab
    dark = theme.TOKENS["dark"]
    assert st.title_label.styleSheet() == LEGACY_DARK_STATUS_TITLE
    assert st.count_label.styleSheet() == LEGACY_DARK_STATUS_COUNT
    assert st.text_edit.styleSheet() == "border: none;"
    assert dark["fg"] in st.title_label.styleSheet()
    assert dark["fg_muted"] in st.count_label.styleSheet()


def test_status_light_uses_light_tokens(theme_window, theme):
    st = theme_window.status_tab
    theme.apply_theme("light")
    light = theme.TOKENS["light"]
    assert light["fg"] in st.title_label.styleSheet()
    assert light["fg_muted"] in st.count_label.styleSheet()
    assert theme.TOKENS["dark"]["fg"] not in st.title_label.styleSheet()
    assert theme.TOKENS["dark"]["fg_muted"] not in st.count_label.styleSheet()
    # 字級/字重不得因切換而消失
    assert "font-size: 20px" in st.title_label.styleSheet()
    assert "font-weight: 600" in st.title_label.styleSheet()


def test_status_log_colors_follow_theme(theme_window, theme):
    st = theme_window.status_tab
    _reset_log(st, [(f"10:00:{i:02d}", f"msg-{t}", t) for i, t in enumerate(STATUS_TYPES)])

    dark = theme.TOKENS["dark"]
    assert _log_line_colors(st)[: len(STATUS_TYPES)] == [dark[TYPE_TOKENS[t]] for t in STATUS_TYPES]

    theme.apply_theme("light")
    light = theme.TOKENS["light"]
    assert _log_line_colors(st)[: len(STATUS_TYPES)] == [light[TYPE_TOKENS[t]] for t in STATUS_TYPES]

    theme.apply_theme("dark")
    assert _log_line_colors(st)[: len(STATUS_TYPES)] == [dark[TYPE_TOKENS[t]] for t in STATUS_TYPES]


def test_status_unknown_type_falls_back_to_info(theme_window, theme):
    st = theme_window.status_tab
    _reset_log(st, [("10:00:00", "weird", "not-a-type")])
    assert _log_line_colors(st)[0] == theme.TOKENS[theme.current_theme()]["info"]


def test_status_light_contrast_tokens_are_used(theme_window, theme):
    """light 不得殘留 dark 的淺色字（深淺色對調後會變成近白字）。"""
    st = theme_window.status_tab
    _reset_log(st, [(f"10:00:{i:02d}", f"m{i}", t) for i, t in enumerate(STATUS_TYPES)])
    theme.apply_theme("light")
    dark_colors = set(theme.TOKENS["dark"][v] for v in TYPE_TOKENS.values())
    assert not (set(_log_line_colors(st)) & dark_colors)


# ── StatusTab：狀態保持 ──────────────────────────────────────────────────
def test_status_cycle_is_reversible(theme_window, theme):
    st = theme_window.status_tab
    title, count, log_qss = st.title_label.styleSheet(), st.count_label.styleSheet(), st.text_edit.styleSheet()
    for _ in range(3):
        theme.apply_theme("light")
        theme.apply_theme("dark")
    assert st.title_label.styleSheet() == title
    assert st.count_label.styleSheet() == count
    assert st.text_edit.styleSheet() == log_qss


def test_status_log_content_survives_switch(theme_window, theme):
    st = theme_window.status_tab
    _reset_log(st, [(f"10:00:{i:02d}", f"line-{i}", STATUS_TYPES[i % len(STATUS_TYPES)]) for i in range(12)])
    before_text = st.text_edit.toPlainText()
    before_log = list(st.status_log)
    before_count = st.count_label.text()
    before_checked = st.auto_scroll_cb.isChecked()

    theme.apply_theme("light")
    theme.apply_theme("dark")

    assert st.text_edit.toPlainText() == before_text, "切換主題不得改寫日誌內容"
    assert st.status_log == before_log, "切換主題不得改動日誌資料"
    assert st.count_label.text() == before_count, "切換主題不得重算/改動筆數"
    assert st.auto_scroll_cb.isChecked() == before_checked


def test_status_refresh_does_not_clear_or_scroll(theme_window, theme, monkeypatch):
    """refresh_theme() 不得呼叫 clear()/setPlainText()，且不得改動捲軸值。"""
    st = theme_window.status_tab
    st.text_edit.setFixedHeight(90)
    try:
        _reset_log(st, [(f"10:00:{i:02d}", f"line-{i}", "info") for i in range(40)])
        st.auto_scroll_cb.setChecked(False)
        bar = st.text_edit.verticalScrollBar()
        assert bar.maximum() > 0, "測試前提：日誌必須超過一頁才有捲軸可驗"
        bar.setValue(min(7, bar.maximum()))
        value, maximum = bar.value(), bar.maximum()

        def boom(*a, **k):
            raise AssertionError("主題刷新不得清空日誌")

        monkeypatch.setattr(st.text_edit, "clear", boom)
        monkeypatch.setattr(st.text_edit, "setPlainText", boom)
        theme.apply_theme("light")
        theme.apply_theme("dark")

        assert bar.value() == value, "切換主題不得重設捲動位置"
        assert bar.maximum() == maximum
    finally:
        st.text_edit.setMinimumHeight(0)
        st.text_edit.setMaximumHeight(16777215)


def test_status_refresh_is_idempotent(theme_window, theme):
    st = theme_window.status_tab
    _reset_log(st, [("10:00:00", "a", "success")])
    first_title, first_count = st.title_label.styleSheet(), st.count_label.styleSheet()
    blocks = st.text_edit.document().blockCount()
    for _ in range(5):
        st.refresh_theme()
    assert st.title_label.styleSheet() == first_title
    assert st.count_label.styleSheet() == first_count
    assert st.text_edit.document().blockCount() == blocks, "重複刷新不得新增行"
    assert st.text_edit.styleSheet() == "border: none;"


# ── AboutTab ────────────────────────────────────────────────────────────
def _about_qss(tab):
    return [widget.styleSheet() for widget, _ in tab._styled]


def _about_buttons(tab):
    from qfluentwidgets import PushButton

    return tab.findChildren(PushButton)


def test_about_dark_uses_dark_tokens(theme_window, theme):
    ab = theme_window.about_tab
    dark = theme.TOKENS["dark"]
    qss = _about_qss(ab)
    assert LEGACY_DARK_ABOUT_CARD in qss, "Dark 卡片樣式必須與遷移前逐字元一致"
    assert f"font-size: 26px; font-weight: 700; color: {dark['fg']};" in qss
    assert f"font-size: 13px; color: {dark['fg_muted']};" in qss
    assert f"font-size: 15px; font-weight: 600; color: {dark['fg']};" in qss
    assert f"font-size: 13px; color: {dark['success']};" in qss
    assert f"font-size: 13px; color: {dark['info']};" in qss
    assert f"font-size: 12px; color: {dark['error']};" in qss
    assert f"font-size: 14px; font-weight: 600; color: {dark['fg']}; background: transparent;" in qss


def test_about_light_uses_light_tokens(theme_window, theme):
    ab = theme_window.about_tab
    theme.apply_theme("light")
    light = theme.TOKENS["light"]
    dark = theme.TOKENS["dark"]
    qss = _about_qss(ab)
    assert f"QWidget {{ background-color: {light['surface']}; border: 1px solid {light['border']}; border-radius: 8px; }}QLabel {{ background: transparent; }}" in qss
    assert f"color: {light['fg_muted']};" in " ".join(qss)
    assert f"font-size: 26px; font-weight: 700; color: {light['fg']};" in qss
    assert f"font-size: 12px; color: {light['error']};" in qss
    joined = " ".join(qss)
    for legacy in (dark["surface"], dark["border"], dark["fg"], dark["fg_muted"], dark["success"], dark["info"], dark["error"]):
        assert legacy not in joined, f"light 頁面殘留 dark 色 {legacy}"


def test_about_cycle_is_reversible(theme_window, theme):
    ab = theme_window.about_tab
    before = _about_qss(ab)
    for _ in range(3):
        theme.apply_theme("light")
        theme.apply_theme("dark")
    assert _about_qss(ab) == before


def test_about_keeps_font_sizes_and_layout(theme_window, theme):
    """字級/字重/版面不得因切換而改變（About 仍有卡片標題/說明/免責三種字級）。"""
    ab = theme_window.about_tab
    before = list(_about_qss(ab))
    texts_before = [c.text() for c in ab.findChildren(type(ab.usage_time_label))]
    theme.apply_theme("light")
    after = list(_about_qss(ab))
    assert [q.split("color:")[0] for q in after] == [q.split("color:")[0] for q in before]
    assert [c.text() for c in ab.findChildren(type(ab.usage_time_label))] == texts_before


def test_about_links_still_work(theme_window, theme, monkeypatch):
    import qt.about as about_mod

    ab = theme_window.about_tab
    opened = []
    monkeypatch.setattr(about_mod.webbrowser, "open", lambda url, *a, **k: opened.append(url))

    labels = [b.text() for b in _about_buttons(ab)]
    assert len(labels) >= 6, "連結/贊助按鈕不得因主題遷移而消失"

    github_text = ab._app.get_text("github_button")
    btn = next(b for b in _about_buttons(ab) if b.text() == github_text)
    theme.apply_theme("light")
    btn.click()
    assert opened == [about_mod._GITHUB_URL], "切換主題後連結仍必須可用"


def test_about_refresh_does_not_rebuild(theme_window, theme, monkeypatch):
    ab = theme_window.about_tab

    def boom(*a, **k):
        raise AssertionError("refresh_theme 不得重建 About 頁")

    monkeypatch.setattr(ab, "_rebuild_content", boom)
    theme.apply_theme("light")
    theme.apply_theme("dark")


def test_about_refresh_is_idempotent(theme_window, theme):
    ab = theme_window.about_tab
    count = len(ab._styled)
    first = _about_qss(ab)
    for _ in range(5):
        ab.refresh_theme()
    assert _about_qss(ab) == first
    assert len(ab._styled) == count, "重複刷新不得登記新元件"


def test_about_scroll_area_does_not_use_os_palette(theme_window, theme):
    """QScrollArea/content 若 autoFillBackground，底色會來自 OS palette（深色 Windows 的深灰），
    不受主題控制 → 必須透明，Light 才不會殘留深色區塊。"""
    ab = theme_window.about_tab
    assert "transparent" in ab._scroll.styleSheet()
    assert ab._scroll.viewport().autoFillBackground() is False
    assert ab._scroll.widget().autoFillBackground() is False


def test_about_language_rebuild_keeps_registry_clean(theme_window, theme):
    """update_language() 重建內容後，樣式登記不得殘留舊元件。"""
    ab = theme_window.about_tab
    ab.update_language()
    live = [w for w, _ in ab._styled]
    assert all(w.parent() is not None for w in live)
    theme.apply_theme("light")
    assert all(w.styleSheet() for w in live)
    theme.apply_theme("dark")


# ── 整合：fan-out ────────────────────────────────────────────────────────
def test_fan_out_refreshes_all_migrated_tabs(theme_window, theme):
    theme.apply_theme("light")
    light = theme.TOKENS["light"]
    assert light["fg_muted"] in theme_window.settings_tab._data_path_label.styleSheet()
    assert light["fg"] in theme_window.status_tab.title_label.styleSheet()
    assert any(light["surface"] in q for q in _about_qss(theme_window.about_tab))

    theme.apply_theme("dark")
    dark = theme.TOKENS["dark"]
    assert dark["fg_muted"] in theme_window.settings_tab._data_path_label.styleSheet()
    assert dark["fg"] in theme_window.status_tab.title_label.styleSheet()
    assert any(dark["surface"] in q for q in _about_qss(theme_window.about_tab))


def test_all_tabs_migrated_and_refreshed(theme_window, theme):
    """Phase 2E 後所有分頁都已遷移，fan-out 必須逐一刷新（含 inventory）。"""
    from PySide6.QtWidgets import QGroupBox

    for attr in ("monitor_tab", "inventory_tab", "combo_tab", "status_tab", "help_tab", "version_tab", "about_tab", "settings_tab"):
        tab = getattr(theme_window, attr, None)
        assert callable(getattr(tab, "refresh_theme", None)), f"{attr} 應有 refresh_theme()"

    groups = [g for g in theme_window.inventory_tab.findChildren(QGroupBox) if g.styleSheet()]
    assert groups, "測試前提：inventory 分頁的群組框應有樣式登記"
    theme.apply_theme("light")
    assert all(theme.TOKENS["light"]["border_strong"] in g.styleSheet() for g in groups)
    theme.apply_theme("dark")
    assert all(theme.TOKENS["dark"]["border_strong"] in g.styleSheet() for g in groups)


def test_single_tab_failure_does_not_block_others(theme_window, theme, monkeypatch):
    def boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(theme_window.status_tab, "refresh_theme", boom)
    theme.apply_theme("light")
    assert theme.TOKENS["light"]["fg_muted"] in theme_window.settings_tab._data_path_label.styleSheet()
    assert any(theme.TOKENS["light"]["surface"] in q for q in _about_qss(theme_window.about_tab))
    theme.apply_theme("dark")


def test_theme_signal_still_connected_once(theme_window, theme, monkeypatch):
    calls = []
    original = type(theme_window)._fan_out_tab_themes

    def counted(self):
        calls.append(1)
        return original(self)

    monkeypatch.setattr(type(theme_window), "_fan_out_tab_themes", counted)
    for _ in range(3):
        theme_window._connect_theme_signals()
    theme.apply_theme("light")
    assert len(calls) == 1, "重複連接訊號導致 fan-out 被觸發多次"
    theme.apply_theme("dark")
    assert theme_window._theme_signal_connected is True


def test_theme_switch_keeps_business_state(theme_window, theme):
    w = theme_window
    st = w.status_tab
    state = (w._monitoring, w._global_pause, w._ahk_click_on)
    log = list(st.status_log)
    hotkeys = dict(w.config.get("hotkeys", {}))
    text = st.text_edit.toPlainText()

    theme.apply_theme("light")
    theme.apply_theme("dark")

    assert (w._monitoring, w._global_pause, w._ahk_click_on) == state
    assert st.status_log == log
    assert dict(w.config.get("hotkeys", {})) == hotkeys
    assert st.text_edit.toPlainText() == text


# ══════════════════════════════════════════════════════════════════════════
# Phase 2B：SkillTimerModule（ComboTab 內嵌）＋ HelpTab
# ══════════════════════════════════════════════════════════════════════════

LEGACY_DARK_HELP_CARD = "QWidget { background-color: #1e1e2e; border: 1px solid #3b3b3b; border-radius: 8px; }QLabel { background: transparent; }"


def _qss_prop(qss: str, prop: str):
    """取出 QSS 屬性值（負向 lookbehind 避免 'background-color' 被 'color' 誤命中）。"""
    m = re.search(rf"(?<![-\w]){re.escape(prop)}:\s*([^;]+);", qss)
    return m.group(1).strip() if m else None


def _st_qss(st):
    """Skill Timer 各處 QSS 快照（供逐項比對 token 與冪等性）。"""
    return {
        "frame": st.frame.styleSheet(),
        "header": st._header_labels[0].styleSheet(),
        "slot": st._slot_labels[0].styleSheet(),
        "sep": st._separators[0].styleSheet(),
        "status": st._status_labels[0].styleSheet(),
        "key_edit": st.slots[0]._key_edit.styleSheet(),
        "interval_spin": st.slots[0]._interval_spin.styleSheet(),
    }


def _st_snapshot(st):
    return [(s.key, s.modifier, s.interval_ms, s.enabled) for s in st.slots]


def _st_restore(st, snapshot):
    for slot, (key, modifier, interval_ms, enabled) in zip(st.slots, snapshot):
        slot.set_ui_value(key, modifier, interval_ms, enabled)


def _help_qss(tab):
    return [w.styleSheet() for w, _ in tab._styled]


def _relative_luminance(hex_color: str) -> float:
    raw = hex_color.lstrip("#")
    r, g, b = (int(raw[i : i + 2], 16) / 255 for i in (0, 2, 4))

    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _contrast(a: str, b: str) -> float:
    """WCAG 相對對比度。"""
    la, lb = _relative_luminance(a), _relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# ── SkillTimerModule：顏色 token ─────────────────────────────────────────
def test_skill_timer_dark_uses_dark_tokens(theme_window, theme):
    st = theme_window.combo_tab.skill_timer
    dark = theme.TOKENS["dark"]
    assert st.frame.styleSheet() == f"QGroupBox {{ color: {dark['fg']}; }}"
    assert st._header_labels[0].styleSheet() == f"color: {dark['fg_muted']}; font-weight: 600;"
    assert st._slot_labels[0].styleSheet() == f"color: {dark['fg']};"
    assert st._separators[0].styleSheet() == f"color: {dark['fg_muted']};"
    assert st._status_labels[0].styleSheet() == f"color: {dark['error']}; font-family: Consolas;"
    assert st.slots[0]._key_edit.styleSheet() == f"background-color: {dark['surface']}; color: {dark['fg']};"
    assert st.slots[0]._interval_spin.styleSheet() == f"background-color: {dark['surface']}; color: {dark['fg']};"


def test_skill_timer_light_uses_light_tokens(theme_window, theme):
    st = theme_window.combo_tab.skill_timer
    theme.apply_theme("light")
    light = theme.TOKENS["light"]
    dark = theme.TOKENS["dark"]
    assert st.frame.styleSheet() == f"QGroupBox {{ color: {light['fg']}; }}"
    assert st._header_labels[0].styleSheet() == f"color: {light['fg_muted']}; font-weight: 600;"
    assert st._slot_labels[0].styleSheet() == f"color: {light['fg']};"
    assert st._separators[0].styleSheet() == f"color: {light['fg_muted']};"
    assert st._status_labels[0].styleSheet() == f"color: {light['error']}; font-family: Consolas;"
    assert st.slots[0]._key_edit.styleSheet() == f"background-color: {light['surface']}; color: {light['fg']};"
    joined = " ".join(_st_qss(st).values())
    for legacy in (dark["fg"], dark["fg_muted"], dark["surface"], dark["error"]):
        assert legacy not in joined, f"light 殘留 dark 色 {legacy}"


def test_skill_timer_status_color_follows_running_state(theme_window, theme):
    st = theme_window.combo_tab.skill_timer
    tok = theme.TOKENS[theme.current_theme()]
    try:
        st._set_status(0, True)
        assert st._status_labels[0].styleSheet() == f"color: {tok['success']}; font-family: Consolas;"
        st._set_status(0, False)
        assert st._status_labels[0].styleSheet() == f"color: {tok['error']}; font-family: Consolas;"
    finally:
        st._set_status(0, False)


def test_skill_timer_status_color_follows_theme_while_running(theme_window, theme, monkeypatch):
    """執行中狀態在 light 也要用 light 的 success 色（不是殘留 dark 綠）。"""
    from qt import skill_timer as st_mod

    class FakePG:
        @staticmethod
        def press(k):
            pass

        @staticmethod
        def hotkey(*args):
            pass

    monkeypatch.setattr(st_mod, "pyautogui", FakePG(), raising=False)
    monkeypatch.setattr(st_mod, "_PYAUTOGUI_OK", True)

    st = theme_window.combo_tab.skill_timer
    slot = st.slots[0]
    snapshot = _st_snapshot(st)
    slot.key = "q"
    slot.interval_ms = 200
    slot.enabled = True
    assert slot.start() is True
    try:
        st._set_status(0, True)
        theme.apply_theme("light")
        assert st._status_labels[0].styleSheet() == f"color: {theme.TOKENS['light']['success']}; font-family: Consolas;"
        theme.apply_theme("dark")
        assert st._status_labels[0].styleSheet() == f"color: {theme.TOKENS['dark']['success']}; font-family: Consolas;"
    finally:
        slot.stop()
        st._set_status(0, False)
        _st_restore(st, snapshot)


def test_skill_timer_cycle_is_reversible(theme_window, theme):
    st = theme_window.combo_tab.skill_timer
    before = _st_qss(st)
    for _ in range(3):
        theme.apply_theme("light")
        theme.apply_theme("dark")
    assert _st_qss(st) == before


def test_skill_timer_refresh_is_idempotent(theme_window, theme):
    st = theme_window.combo_tab.skill_timer
    first = _st_qss(st)
    for _ in range(5):
        st.refresh_theme()
    assert _st_qss(st) == first, "重複刷新不得累積 QSS"


def test_skill_timer_keeps_slot_state_across_theme_switch(theme_window, theme):
    st = theme_window.combo_tab.skill_timer
    app = theme_window
    original_cfg = app.config.get("skill_timer")
    snapshot = _st_snapshot(st)
    try:
        st.load_config([{"enabled": True, "key": "q", "modifier": "shift", "interval_ms": 250}])
        before = st.get_config()
        theme.apply_theme("light")
        theme.apply_theme("dark")
        assert st.get_config() == before, "切換主題不得改動技能槽設定"
        assert st.slots[0].key == "q"
        assert st.slots[0].modifier == "shift"
        assert st.slots[0].interval_ms == 250
        assert st.slots[0].enabled is True
    finally:
        _st_restore(st, snapshot)
        if original_cfg is None:
            app.config.pop("skill_timer", None)
        else:
            app.config["skill_timer"] = original_cfg


def test_skill_timer_running_state_survives_theme_switch(theme_window, theme, monkeypatch):
    """切換主題不得停止／重啟計時器（冷卻間隔與執行狀態不變）。"""
    from qt import skill_timer as st_mod

    class FakePG:
        @staticmethod
        def press(k):
            pass

        @staticmethod
        def hotkey(*args):
            pass

    monkeypatch.setattr(st_mod, "pyautogui", FakePG(), raising=False)
    monkeypatch.setattr(st_mod, "_PYAUTOGUI_OK", True)

    st = theme_window.combo_tab.skill_timer
    slot = st.slots[0]
    snapshot = _st_snapshot(st)
    slot.key = "q"
    slot.interval_ms = 200
    slot.enabled = True
    assert slot.start() is True
    try:
        st._set_status(0, True)
        theme.apply_theme("light")
        theme.apply_theme("dark")
        assert slot.is_running, "切換主題不得停止計時器"
        assert slot.interval_ms == 200, "切換主題不得改動冷卻間隔"
        assert st._status_labels[0].styleSheet() == f"color: {theme.TOKENS['dark']['success']}; font-family: Consolas;"
    finally:
        slot.stop()
        st._set_status(0, False)
        _st_restore(st, snapshot)


def test_combo_forwards_theme_refresh_to_skill_timer(theme_window, theme):
    combo = theme_window.combo_tab
    st = combo.skill_timer
    theme.apply_theme("light")
    assert st.frame.styleSheet() == f"QGroupBox {{ color: {theme.TOKENS['light']['fg']}; }}"
    theme.apply_theme("dark")
    assert st.frame.styleSheet() == f"QGroupBox {{ color: {theme.TOKENS['dark']['fg']}; }}"


def test_skill_timer_refreshed_exactly_once_per_switch(theme_window, theme, monkeypatch):
    """Skill Timer 不得自行連主題訊號；只由 ComboTab 轉發，單次切換只刷新一次。"""
    st = theme_window.combo_tab.skill_timer
    calls = []
    original = st.refresh_theme

    def counted():
        calls.append(1)
        original()

    monkeypatch.setattr(st, "refresh_theme", counted)
    theme.apply_theme("light")
    assert len(calls) == 1, "單次切換不得重複刷新 Skill Timer"
    theme.apply_theme("dark")
    assert len(calls) == 2


# ── HelpTab：顏色 token ──────────────────────────────────────────────────
def test_help_dark_uses_dark_tokens(theme_window, theme):
    hp = theme_window.help_tab
    dark = theme.TOKENS["dark"]
    qss = _help_qss(hp)
    assert LEGACY_DARK_HELP_CARD in qss, "Dark 卡片樣式必須與遷移前逐字元一致"
    assert f"font-size: 26px; font-weight: 700; color: {dark['fg']};" in qss
    assert f"font-size: 13px; color: {dark['fg_muted']};" in qss
    assert f"font-size: 11px; color: {dark['error']};" in qss
    assert f"font-size: 14px; font-weight: 600; color: {dark['fg']}; background: transparent;" in qss
    assert f"font-size: 14px; font-weight: 700; color: {dark['success']};" in qss
    assert f"font-size: 14px; font-weight: 700; color: {dark['accent']};" in qss
    assert f"font-size: 12px; color: {dark['fg']};" in qss
    assert f"font-weight: 600; color: {dark['fg']};" in qss
    assert f"font-size: 12px; color: {dark['info']};" in qss
    badge = f"background-color: {dark['error']}; color: {dark['badge_fg']}; padding: 2px 8px; border-radius: 4px; font-family: Consolas; font-weight: 600; font-size: 12px;"
    assert badge in qss


def test_help_light_uses_light_tokens(theme_window, theme):
    hp = theme_window.help_tab
    theme.apply_theme("light")
    light = theme.TOKENS["light"]
    dark = theme.TOKENS["dark"]
    qss = _help_qss(hp)
    assert f"QWidget {{ background-color: {light['surface']}; border: 1px solid {light['border']}; border-radius: 8px; }}QLabel {{ background: transparent; }}" in qss
    assert f"font-size: 26px; font-weight: 700; color: {light['fg']};" in qss
    assert f"font-size: 13px; color: {light['fg_muted']};" in qss
    assert f"font-size: 14px; font-weight: 700; color: {light['success']};" in qss
    assert f"font-size: 12px; color: {light['info']};" in qss
    joined = " ".join(qss)
    for legacy in (dark["surface"], dark["border"], dark["fg"], dark["fg_muted"], dark["success"], dark["info"], dark["error"], dark["warning"], dark["accent"], dark["badge_fg"]):
        assert legacy not in joined, f"light 頁面殘留 dark 色 {legacy}"


def test_help_badges_use_badge_fg_and_pass_contrast(theme_window, theme):
    """Badge 的前景 + 背景都要處理：dark 黑字、light 白字，兩者皆 ≥4.5:1。"""
    hp = theme_window.help_tab
    for mode in ("dark", "light"):
        theme.apply_theme(mode)
        tok = theme.TOKENS[mode]
        badges = [w for w, spec in hp._styled if spec[0] == "badge"]
        assert len(badges) == 8, "快捷鍵 badge 數量不得變動"
        for badge in badges:
            qss = badge.styleSheet()
            bg = _qss_prop(qss, "background-color")
            fg = _qss_prop(qss, "color")
            assert fg == tok["badge_fg"], f"{mode} badge 前景必須是 badge_fg"
            assert bg in tok.values(), f"{mode} badge 背景必須來自 token"
            ratio = _contrast(bg, fg)
            assert ratio >= 4.5, f"{mode} badge {bg}/{fg} 對比不足 {ratio:.2f}:1"


def test_help_cycle_is_reversible(theme_window, theme):
    hp = theme_window.help_tab
    before = _help_qss(hp)
    for _ in range(3):
        theme.apply_theme("light")
        theme.apply_theme("dark")
    assert _help_qss(hp) == before


def test_help_keeps_fonts_and_layout(theme_window, theme):
    """字級/字重/文字不得因切換而改變（只換顏色）。"""
    hp = theme_window.help_tab
    from PySide6.QtWidgets import QLabel

    before = [(spec, w.styleSheet().split("color:")[0]) for w, spec in hp._styled]
    texts_before = [w.text() for w, _ in hp._styled if isinstance(w, QLabel)]
    theme.apply_theme("light")
    after = [(spec, w.styleSheet().split("color:")[0]) for w, spec in hp._styled]
    assert after == before
    assert [w.text() for w, _ in hp._styled if isinstance(w, QLabel)] == texts_before


def test_help_links_still_work_after_theme_switch(theme_window, theme, monkeypatch):
    from PySide6.QtCore import Qt
    from qfluentwidgets import PushButton

    hp = theme_window.help_tab
    opened = []
    monkeypatch.setattr(theme_window, "open_video_link", lambda url, *a, **k: opened.append(url))

    repo_url = "https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor"
    url_label = next(w for w, _ in hp._styled if getattr(w, "text", lambda: "")() == repo_url)
    assert url_label.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByMouse

    btns = hp.findChildren(PushButton)
    assert len(btns) >= 2, "Help 頁按鈕不得因主題遷移而消失"
    theme.apply_theme("light")
    for b in btns:
        b.click()
    assert len(opened) == len(btns), "切換主題後連結按鈕仍必須可用"


def test_help_refresh_does_not_rebuild(theme_window, theme, monkeypatch):
    hp = theme_window.help_tab

    def boom(*a, **k):
        raise AssertionError("refresh_theme 不得重建 Help 頁")

    monkeypatch.setattr(hp, "_rebuild_content", boom)
    theme.apply_theme("light")
    theme.apply_theme("dark")


def test_help_refresh_is_idempotent(theme_window, theme):
    hp = theme_window.help_tab
    count = len(hp._styled)
    first = _help_qss(hp)
    for _ in range(5):
        hp.refresh_theme()
    assert _help_qss(hp) == first
    assert len(hp._styled) == count, "重複刷新不得登記新元件"


def test_help_scroll_area_does_not_use_os_palette(theme_window, theme):
    hp = theme_window.help_tab
    assert "transparent" in hp._scroll.styleSheet()
    assert hp._scroll.viewport().autoFillBackground() is False
    assert hp._scroll.widget().autoFillBackground() is False


def test_help_language_rebuild_keeps_registry_clean(theme_window, theme):
    hp = theme_window.help_tab
    hp.update_language()
    live = [w for w, _ in hp._styled]
    assert live, "重建後仍必須有樣式登記"
    assert all(w.parent() is not None for w in live)
    theme.apply_theme("light")
    assert all(w.styleSheet() for w in live)
    theme.apply_theme("dark")


# ── 整合：fan-out ────────────────────────────────────────────────────────
def test_fan_out_refreshes_skill_timer_and_help(theme_window, theme):
    theme.apply_theme("light")
    light = theme.TOKENS["light"]
    st = theme_window.combo_tab.skill_timer
    assert light["fg"] in st.frame.styleSheet()
    assert light["surface"] in st.slots[0]._key_edit.styleSheet()
    assert any(light["surface"] in q for q in _help_qss(theme_window.help_tab))

    theme.apply_theme("dark")
    dark = theme.TOKENS["dark"]
    assert dark["fg"] in st.frame.styleSheet()
    assert dark["surface"] in st.slots[0]._key_edit.styleSheet()
    assert any(dark["surface"] in q for q in _help_qss(theme_window.help_tab))


def test_help_failure_does_not_block_other_tabs(theme_window, theme, monkeypatch):
    def boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(theme_window.help_tab, "refresh_theme", boom)
    theme.apply_theme("light")
    assert theme.TOKENS["light"]["fg"] in theme_window.combo_tab.skill_timer.frame.styleSheet()
    assert theme.TOKENS["light"]["fg"] in theme_window.status_tab.title_label.styleSheet()
    theme.apply_theme("dark")


def test_theme_switch_keeps_skill_timer_and_help_state(theme_window, theme):
    w = theme_window
    st = w.combo_tab.skill_timer
    hp = w.help_tab
    snapshot = _st_snapshot(st)
    cfg_before = st.get_config()
    help_texts_before = [x.text() for x, _ in hp._styled if hasattr(x, "text")]
    try:
        theme.apply_theme("light")
        theme.apply_theme("dark")
        assert _st_snapshot(st) == snapshot
        assert st.get_config() == cfg_before
        assert [x.text() for x, _ in hp._styled if hasattr(x, "text")] == help_texts_before
    finally:
        _st_restore(st, snapshot)


# ══════════════════════════════════════════════════════════════════════════
# Phase 2C：ComboTab（剩餘區域）＋ VersionTab
# ══════════════════════════════════════════════════════════════════════════

# 遷移前的硬編碼色（Combo / Version 舊常數與字面值），light 下不得殘留
LEGACY_COMBO_COLORS = ("#50fa7b", "#ff5555", "#b8b8c8", "#3b3b3b", "#f8f8f2", "#1e1e2e", "#2d2d2d")
LEGACY_VERSION_COLORS = ("#50fa7b", "#ff5555", "#8be9fd", "#b8b8c8", "#f8f8f2", "#1e1e2e", "#3b3b3b")


def _combo_qss(combo):
    """ComboTab 自管 QSS 快照（登記表 + 分頁 notebook + 狀態文字）。"""
    qss = [w.styleSheet() for w, _ in combo._styled]
    qss.append(combo.combo_notebook.styleSheet())
    qss.append(combo.combo_status_label.styleSheet())
    return qss


def _version_qss(vt):
    """VersionTab 自管 QSS 快照（頁面登記表 + 最新版本狀態文字）。"""
    qss = [w.styleSheet() for w, _ in vt._styled]
    qss.append(vt.latest_version_label.styleSheet())
    return qss


def _combo_widgets(combo):
    """關鍵元件的身分（用來驗證主題切換不得重建 widget）。"""
    refs = combo.combo_ui_refs[0]
    return (
        id(combo.combo_notebook),
        id(combo.combo_start_btn),
        id(combo.combo_stop_btn),
        id(combo.combo_status_label),
        id(combo.skill_timer),
        id(refs["key_combos"][0]),
        id(refs["delay_entries"][0]),
        id(refs["enabled_check"]),
    )


# ── ComboTab：顏色 token ──────────────────────────────────────────────────
def test_combo_dark_uses_dark_tokens(theme_window, theme):
    combo = theme_window.combo_tab
    dark = theme.TOKENS["dark"]
    joined = " ".join(_combo_qss(combo))
    assert f"QGroupBox {{ border: 1px solid {dark['border']}; border-radius: 8px;" in joined
    assert f"color: {dark['fg']}; background: transparent; }}" in joined
    assert f"font-size: 20px; font-weight: 600; color: {dark['fg']};" in joined
    assert f"font-weight: 600; color: {dark['fg']};" in joined
    assert f"font-size: 12px; color: {dark['fg_muted']};" in joined
    assert f"font-size: 11px; color: {dark['fg_muted']};" in joined
    assert f"color: {dark['error']}; font-size: 13px;" in joined
    assert f"QTabBar::tab:selected {{ color: {dark['fg']}; border-bottom: 2px solid {dark['accent']}; }}" in joined


def test_combo_light_uses_light_tokens(theme_window, theme):
    combo = theme_window.combo_tab
    theme.apply_theme("light")
    light = theme.TOKENS["light"]
    joined = " ".join(_combo_qss(combo))
    assert f"QGroupBox {{ border: 1px solid {light['border']}; border-radius: 8px;" in joined
    assert f"font-size: 20px; font-weight: 600; color: {light['fg']};" in joined
    assert f"font-size: 12px; color: {light['fg_muted']};" in joined
    assert f"color: {light['error']}; font-size: 13px;" in joined
    assert f"QTabBar::tab:selected {{ color: {light['fg']}; border-bottom: 2px solid {light['accent']}; }}" in joined


def test_combo_light_has_no_dark_residue(theme_window, theme):
    """Light 下 Combo 自管 QSS 不得殘留 dark token 或遷移前的硬編碼深色。"""
    combo = theme_window.combo_tab
    theme.apply_theme("light")
    joined = " ".join(_combo_qss(combo))
    dark_values = set(theme.TOKENS["dark"].values())
    for legacy in sorted(dark_values | set(LEGACY_COMBO_COLORS)):
        assert legacy not in joined, f"light Combo 殘留 dark 色 {legacy}"


def test_combo_light_text_contrast_is_readable(theme_window, theme):
    """Light 下文字 token 對 surface 的對比度須達 WCAG AA（4.5:1）。"""
    light = theme.TOKENS["light"]
    for key in ("fg", "fg_muted", "success", "error", "info", "accent"):
        ratio = _contrast(light[key], light["surface"])
        assert ratio >= 4.5, f"light {key} 對比不足 {ratio:.2f}:1"


def test_combo_group_boxes_and_tabs_have_no_os_palette_fill(theme_window, theme):
    """QGroupBox / QTabWidget 原生底色來自 OS palette（深色 Windows = 深灰）→ 必須透明。"""
    combo = theme_window.combo_tab
    groups = [w for w, spec in combo._styled if spec[0] == "group"]
    assert len(groups) == 5, "測試前提：Combo 有 5 個自管群組框（3 個技能設定 + 全域控制 + 使用提示）"
    for box in groups:
        qss = box.styleSheet()
        assert "background: transparent;" in qss, f"QGroupBox 未透明：{qss[:60]}"
    tab_qss = combo.combo_notebook.styleSheet()
    assert "QTabWidget::pane { border: 2px solid transparent; background: transparent; }" in tab_qss
    assert "QTabBar { background: transparent; }" in tab_qss
    assert "QTabBar::tab { background: transparent;" in tab_qss


def test_combo_scroll_area_does_not_use_os_palette(theme_window, theme):
    """左欄 QScrollArea/content 必須透明，否則整欄會被 OS palette 深色填滿。"""
    from PySide6.QtWidgets import QScrollArea

    combo = theme_window.combo_tab
    scrolls = combo.findChildren(QScrollArea)
    assert scrolls, "測試前提：Combo 左欄仍是 QScrollArea"
    scroll = scrolls[0]
    assert "transparent" in scroll.styleSheet()
    assert scroll.viewport().autoFillBackground() is False
    assert scroll.widget().autoFillBackground() is False


# ── ComboTab：刷新行為 ────────────────────────────────────────────────────
def test_combo_cycle_is_reversible(theme_window, theme):
    combo = theme_window.combo_tab
    before = _combo_qss(combo)
    for _ in range(3):
        theme.apply_theme("light")
        theme.apply_theme("dark")
    assert _combo_qss(combo) == before


def test_combo_refresh_is_idempotent(theme_window, theme):
    combo = theme_window.combo_tab
    count = len(combo._styled)
    first = _combo_qss(combo)
    for _ in range(5):
        combo.refresh_theme()
    assert _combo_qss(combo) == first, "重複刷新不得累積 QSS"
    assert len(combo._styled) == count, "重複刷新不得登記新元件"


def test_combo_refresh_does_not_rebuild_widgets(theme_window, theme, monkeypatch):
    combo = theme_window.combo_tab

    def boom(*a, **k):
        raise AssertionError("refresh_theme 不得重建 Combo 頁")

    monkeypatch.setattr(combo, "_build_ui", boom)
    before = _combo_widgets(combo)
    theme.apply_theme("light")
    theme.apply_theme("dark")
    assert _combo_widgets(combo) == before, "切換主題不得重建 Combo 元件"


def test_combo_keeps_input_values_and_business_data(theme_window, theme):
    """切換主題不得清掉輸入值、選項與連段設定資料。"""
    combo = theme_window.combo_tab
    refs = combo.combo_ui_refs[0]
    original_sets = copy.deepcopy(combo.combo_sets)
    original_enabled = list(combo.combo_enabled)
    try:
        refs["delay_entries"][0].setText("123")
        refs["key_combos"][0].setCurrentText("Z")
        refs["enabled_check"].setChecked(False)
        theme.apply_theme("light")
        theme.apply_theme("dark")
        assert refs["delay_entries"][0].text() == "123", "延遲輸入值不得被清掉"
        assert refs["key_combos"][0].currentText() == "Z", "技能選項不得被重設"
        assert refs["enabled_check"].isChecked() is False, "勾選狀態不得被重設"
        assert combo.combo_sets[0]["delays"][0] == 123
        assert combo.combo_sets[0]["combo_keys"][0] == "Z"
        assert combo.combo_enabled[0] is False
    finally:
        combo.combo_sets = original_sets
        combo.combo_enabled = original_enabled
        combo._apply_combo_ui_from_config()


def test_combo_status_tone_follows_business_state(theme_window, theme):
    """狀態色依業務狀態（success/error）決定，切換主題不得覆蓋成固定色。"""
    combo = theme_window.combo_tab
    try:
        combo._set_status_tone("success")
        assert combo.combo_status_label.styleSheet() == f"color: {theme.TOKENS['dark']['success']}; font-size: 13px;"
        theme.apply_theme("light")
        assert combo.combo_status_label.styleSheet() == f"color: {theme.TOKENS['light']['success']}; font-size: 13px;"
        combo.refresh_theme()
        assert combo.combo_status_label.styleSheet() == f"color: {theme.TOKENS['light']['success']}; font-size: 13px;", "刷新不得覆蓋業務狀態色"
        theme.apply_theme("dark")
        assert combo.combo_status_label.styleSheet() == f"color: {theme.TOKENS['dark']['success']}; font-size: 13px;"
    finally:
        combo._set_status_tone("error")


def test_combo_refresh_forwards_skill_timer_exactly_once(theme_window, theme, monkeypatch):
    """ComboTab 只轉發一次 Skill Timer 刷新（Skill Timer 不自行連主題訊號）。"""
    combo = theme_window.combo_tab
    st = combo.skill_timer
    calls = []
    original = st.refresh_theme

    def counted():
        calls.append(1)
        original()

    monkeypatch.setattr(st, "refresh_theme", counted)
    combo.refresh_theme()
    assert len(calls) == 1, "Combo 刷新不得重複刷新 Skill Timer"


def test_combo_theme_refresh_called_once_per_switch(theme_window, theme, monkeypatch):
    """單次主題切換不得重複呼叫 Combo 的 refresh_theme（不可重複連訊號）。"""
    combo = theme_window.combo_tab
    calls = []
    original = combo.refresh_theme

    def counted():
        calls.append(1)
        original()

    monkeypatch.setattr(combo, "refresh_theme", counted)
    theme.apply_theme("light")
    assert len(calls) == 1, "單次切換不得重複刷新 Combo"
    theme.apply_theme("dark")
    assert len(calls) == 2


def test_combo_interaction_still_works_after_theme_switch(theme_window, theme):
    """切換主題後互動元件仍要能把值寫回業務資料。"""
    combo = theme_window.combo_tab
    refs = combo.combo_ui_refs[0]
    original_sets = copy.deepcopy(combo.combo_sets)
    try:
        theme.apply_theme("light")
        refs["key_combos"][1].setCurrentText("X")
        refs["delay_entries"][1].setText("77")
        assert combo.combo_sets[0]["combo_keys"][1] == "X", "切換主題後技能選項仍須連動資料"
        assert combo.combo_sets[0]["delays"][1] == 77, "切換主題後延遲輸入仍須連動資料"
    finally:
        combo.combo_sets = original_sets
        combo._apply_combo_ui_from_config()


# ── VersionTab：顏色 token ───────────────────────────────────────────────
def test_version_dark_uses_dark_tokens(theme_window, theme):
    vt = theme_window.version_tab
    dark = theme.TOKENS["dark"]
    joined = " ".join(_version_qss(vt))
    assert f"QWidget {{ background-color: {dark['surface']}; border: 1px solid {dark['border']}; border-radius: 8px; }}QLabel {{ background: transparent; }}" in joined
    assert f"QPlainTextEdit {{ background-color: {dark['surface']}; border: 1px solid {dark['border']}; border-radius: 6px; color: {dark['fg_muted']}; font-size: 12px; }}" in joined
    assert f"font-size: 20px; font-weight: 600; color: {dark['fg']};" in joined
    assert f"font-size: 16px; font-weight: 700; color: {dark['info']};" in joined
    assert f"font-size: 14px; font-weight: 600; color: {dark['fg']}; background: transparent;" in joined
    assert f"font-size: 16px; font-weight: 700; color: {dark['success']};" in joined


def test_version_light_uses_light_tokens(theme_window, theme):
    vt = theme_window.version_tab
    theme.apply_theme("light")
    light = theme.TOKENS["light"]
    joined = " ".join(_version_qss(vt))
    assert f"QWidget {{ background-color: {light['surface']}; border: 1px solid {light['border']}; border-radius: 8px; }}QLabel {{ background: transparent; }}" in joined
    assert f"QPlainTextEdit {{ background-color: {light['surface']}; border: 1px solid {light['border']}; border-radius: 6px; color: {light['fg_muted']}; font-size: 12px; }}" in joined
    assert f"font-size: 20px; font-weight: 600; color: {light['fg']};" in joined
    assert f"font-size: 16px; font-weight: 700; color: {light['info']};" in joined
    assert f"font-size: 16px; font-weight: 700; color: {light['success']};" in joined


def test_version_light_has_no_dark_residue(theme_window, theme):
    vt = theme_window.version_tab
    theme.apply_theme("light")
    joined = " ".join(_version_qss(vt))
    dark_values = set(theme.TOKENS["dark"].values())
    for legacy in sorted(dark_values | set(LEGACY_VERSION_COLORS)):
        assert legacy not in joined, f"light Version 殘留 dark 色 {legacy}"


def test_version_light_text_contrast_is_readable(theme_window, theme):
    light = theme.TOKENS["light"]
    for key in ("fg", "fg_muted", "success", "error", "info", "accent", "warning"):
        ratio = _contrast(light[key], light["surface"])
        assert ratio >= 4.5, f"light {key} 對比不足 {ratio:.2f}:1"


def test_version_latest_tone_follows_update_state(theme_window, theme):
    """最新版本文字的語意色（success/error/info）依更新狀態決定，不被主題刷新覆蓋。"""
    vt = theme_window.version_tab
    try:
        vt._set_latest_tone("error")
        assert vt.latest_version_label.styleSheet() == f"font-size: 16px; font-weight: 700; color: {theme.TOKENS['dark']['error']};"
        theme.apply_theme("light")
        assert vt.latest_version_label.styleSheet() == f"font-size: 16px; font-weight: 700; color: {theme.TOKENS['light']['error']};"
        vt.refresh_theme()
        assert vt.latest_version_label.styleSheet() == f"font-size: 16px; font-weight: 700; color: {theme.TOKENS['light']['error']};"
        vt._set_latest_tone("info")
        assert vt.latest_version_label.styleSheet() == f"font-size: 16px; font-weight: 700; color: {theme.TOKENS['light']['info']};"
    finally:
        vt._set_latest_tone("success")


# ── VersionTab：刷新行為 ──────────────────────────────────────────────────
def test_version_cycle_is_reversible(theme_window, theme):
    vt = theme_window.version_tab
    before = _version_qss(vt)
    for _ in range(3):
        theme.apply_theme("light")
        theme.apply_theme("dark")
    assert _version_qss(vt) == before


def test_version_refresh_is_idempotent(theme_window, theme):
    vt = theme_window.version_tab
    count = len(vt._styled)
    first = _version_qss(vt)
    for _ in range(5):
        vt.refresh_theme()
    assert _version_qss(vt) == first, "重複刷新不得累積 QSS"
    assert len(vt._styled) == count, "重複刷新不得登記新元件"


def test_version_refresh_does_not_rebuild_widgets(theme_window, theme, monkeypatch):
    vt = theme_window.version_tab

    def boom(*a, **k):
        raise AssertionError("refresh_theme 不得重建 Version 頁")

    monkeypatch.setattr(vt, "_build_ui", boom)
    before = (id(vt.latest_version_label), id(vt.release_notes_text), id(vt.check_update_btn), id(vt.download_btn), id(vt.test_connection_btn))
    theme.apply_theme("light")
    theme.apply_theme("dark")
    after = (id(vt.latest_version_label), id(vt.release_notes_text), id(vt.check_update_btn), id(vt.download_btn), id(vt.test_connection_btn))
    assert after == before, "切換主題不得重建 Version 元件"


def test_version_theme_switch_triggers_no_network(theme_window, theme, monkeypatch):
    """切換主題不得觸發版本檢查/下載/網路請求。"""
    import qt.version as version_mod

    def boom(*a, **k):
        raise AssertionError("切換主題不得觸發任何網路請求或版本檢查")

    monkeypatch.setattr(version_mod.requests, "get", boom)
    monkeypatch.setattr(version_mod.auto_update, "check_for_update", boom)
    monkeypatch.setattr(version_mod.auto_update, "create_manager", boom)
    monkeypatch.setattr(version_mod.VersionTab, "_run_check", lambda self, silent: boom())
    theme.apply_theme("light")
    theme.apply_theme("dark")


def test_version_update_state_survives_theme_switch(theme_window, theme, monkeypatch):
    """更新狀態（可攜模式提示 / 按鈕可用性）不得因切換主題而改變。"""
    vt = theme_window.version_tab
    monkeypatch.setattr(vt, "_fetch_release_notes", lambda version_tag: None)
    vt._update_manager = None
    try:
        vt._on_version_checked(None)
        assert vt._latest_tone == "info"
        before_text = vt.latest_version_label.text()
        before_status = vt.version_status_label.text()
        before_enabled = vt.download_btn.isEnabled()

        theme.apply_theme("light")
        assert vt.latest_version_label.text() == before_text, "切換主題不得改寫最新版本文字"
        assert vt.version_status_label.text() == before_status, "切換主題不得改寫狀態文字"
        assert vt.download_btn.isEnabled() == before_enabled, "切換主題不得改變按鈕可用性"
        assert vt.latest_version_label.styleSheet() == f"font-size: 16px; font-weight: 700; color: {theme.TOKENS['light']['info']};"

        theme.apply_theme("dark")
        assert vt.latest_version_label.text() == before_text
        assert vt.version_status_label.text() == before_status
    finally:
        vt._update_manager = None
        vt._set_latest_tone("success")


def test_version_buttons_still_work_after_theme_switch(theme_window, theme, monkeypatch):
    """切換主題後按鈕仍要能驅動原本的更新流程（此處只驗證 UI 狀態轉換）。"""
    vt = theme_window.version_tab
    monkeypatch.setattr(vt, "_run_check", lambda silent: None)
    try:
        theme.apply_theme("light")
        vt.check_update_btn.click()
        assert vt.latest_version_label.text() == vt._app.get_text("checking_version")
        assert vt.version_status_label.text() == vt._app.get_text("connecting_github")
        assert vt.check_update_btn.isEnabled() is True
    finally:
        vt._updating = False
        theme.apply_theme("dark")


def test_version_dialog_widgets_use_current_theme(theme_window, theme, monkeypatch):
    """動態建立的對話框元件：建立當下即取得當前主題，且切換主題會跟著翻新。"""
    import qt.version as version_mod
    from PySide6.QtWidgets import QDialog

    class FakeInfo:
        version = "9.9.9"

    vt = theme_window.version_tab
    monkeypatch.setattr(QDialog, "exec", lambda self: 0)
    try:
        vt._show_update_notification(FakeInfo())
        assert vt._dialog_styled, "更新通知對話框的元件必須登記樣式"
        joined = " ".join(w.styleSheet() for w, _ in vt._dialog_styled)
        dark = theme.TOKENS["dark"]
        assert f"font-size: 16px; font-weight: 700; color: {dark['success']};" in joined
        assert f"QWidget {{ background-color: {dark['surface']}; border: 1px solid {dark['border']}; border-radius: 8px; }}QLabel {{ background: transparent; }}" in joined

        theme.apply_theme("light")
        light = theme.TOKENS["light"]
        joined = " ".join(w.styleSheet() for w, _ in vt._dialog_styled)
        assert f"font-size: 16px; font-weight: 700; color: {light['success']};" in joined
        assert f"QWidget {{ background-color: {light['surface']}; border: 1px solid {light['border']}; border-radius: 8px; }}QLabel {{ background: transparent; }}" in joined
    finally:
        dialog = vt._notification_dialog
        vt._notification_dialog = None
        vt._dialog_styled.clear()
        if dialog is not None:
            dialog.close()
            dialog.deleteLater()
        theme.apply_theme("dark")


def test_version_progress_dialog_keeps_value_and_theme(theme_window, theme, monkeypatch):
    """下載進度對話框：進度值不得因切換主題而變動，樣式須跟著主題。"""
    import qt.version as version_mod
    from PySide6.QtWidgets import QDialog

    class FakeInfo:
        version = "9.9.9"

    vt = theme_window.version_tab

    class _FakeThread:
        """假的背景 thread：不下載、不發訊號（避免測試被模態對話框卡住）。"""

        def __init__(self, *a, **k):
            pass

        def start(self):
            pass

        def is_alive(self):
            return False

        def join(self, timeout=None):
            pass

    monkeypatch.setattr(QDialog, "exec", lambda self: 0)
    monkeypatch.setattr(version_mod.threading, "Thread", _FakeThread)
    try:
        vt._start_download(FakeInfo())
        vt._progress_bar.setValue(42)
        light = theme.TOKENS["light"]
        theme.apply_theme("light")
        assert vt._progress_bar.value() == 42, "切換主題不得重設下載進度"
        assert f"QProgressBar {{ background-color: {light['surface']}; border: 1px solid {light['border']};" in vt._progress_bar.styleSheet()
        assert f"QProgressBar::chunk {{ background-color: {light['accent']}; }}" in vt._progress_bar.styleSheet()
    finally:
        vt._downloading = False
        vt._close_progress_dialog()
        vt.download_btn.setEnabled(False)
        vt.check_update_btn.setEnabled(True)
        theme.apply_theme("dark")


def test_version_dialog_registry_cleared_on_close(theme_window, theme):
    """對話框關閉後樣式登記必須清空（避免持有已刪除元件）。"""
    vt = theme_window.version_tab
    vt._dialog_styled.clear()
    vt._close_progress_dialog()
    assert vt._dialog_styled == []


# ── 整合：fan-out ────────────────────────────────────────────────────────
def test_fan_out_refreshes_combo_and_version(theme_window, theme):
    theme.apply_theme("light")
    light = theme.TOKENS["light"]
    combo_qss = " ".join(_combo_qss(theme_window.combo_tab))
    version_qss = " ".join(_version_qss(theme_window.version_tab))
    assert f"color: {light['fg']};" in combo_qss
    assert f"color: {light['fg_muted']};" in combo_qss
    assert f"background-color: {light['surface']};" in version_qss
    assert f"color: {light['fg']};" in version_qss

    theme.apply_theme("dark")
    dark = theme.TOKENS["dark"]
    combo_qss = " ".join(_combo_qss(theme_window.combo_tab))
    version_qss = " ".join(_version_qss(theme_window.version_tab))
    assert f"color: {dark['fg']};" in combo_qss
    assert f"background-color: {dark['surface']};" in version_qss


def test_combo_failure_does_not_block_other_tabs(theme_window, theme, monkeypatch):
    def boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(theme_window.combo_tab, "refresh_theme", boom)
    theme.apply_theme("light")
    assert theme.TOKENS["light"]["fg"] in " ".join(_version_qss(theme_window.version_tab))
    assert theme.TOKENS["light"]["fg"] in theme_window.status_tab.title_label.styleSheet()
    theme.apply_theme("dark")


def test_version_failure_does_not_block_other_tabs(theme_window, theme, monkeypatch):
    def boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(theme_window.version_tab, "refresh_theme", boom)
    theme.apply_theme("light")
    assert theme.TOKENS["light"]["fg"] in " ".join(_combo_qss(theme_window.combo_tab))
    assert theme.TOKENS["light"]["fg"] in theme_window.combo_tab.skill_timer.frame.styleSheet()
    theme.apply_theme("dark")


def test_inventory_refreshes_with_theme(theme_window, theme):
    """Phase 2E：Inventory 分頁會跟著主題切換刷新。"""
    inventory = theme_window.inventory_tab
    assert callable(getattr(inventory, "refresh_theme", None))
    theme.apply_theme("light")
    assert theme.TOKENS["light"]["fg"] in inventory.page_title_label.styleSheet()
    theme.apply_theme("dark")
    assert theme.TOKENS["dark"]["fg"] in inventory.page_title_label.styleSheet()

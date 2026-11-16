"""Phase 1 GUI 測試：MainWindow 主題刷新管線、狀態列、Toast、SettingsTab BodyLabel。

以 offscreen QPA 建立真實 MainWindow（不引入 pytest-qt）；熱鍵掛鉤與 AHK 監聽以 monkeypatch
停用，避免測試程序安裝全域鍵盤勾子。
"""

import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6.QtWidgets")


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    app.setApplicationName("GameTools Health Monitor (test)")
    yield app


_REFRESH_CALLS: list[int] = []


@pytest.fixture(scope="module")
def window(qapp, tmp_path_factory, monkeypatch_module):
    """真實 MainWindow（single instance），config 指向暫存目錄。"""
    import config_manager as cm_mod
    import qt.main_window as mw
    import qt.theme as theme

    tmp = tmp_path_factory.mktemp("cfg")
    cm = cm_mod.ConfigManager(config_path=str(tmp))
    cm.load_config()

    monkeypatch_module.setattr(mw.MainWindow, "config_manager_factory", lambda self: cm)
    monkeypatch_module.setattr(mw.MainWindow, "setup_hotkeys", lambda self: None)
    monkeypatch_module.setattr(mw, "AutoClickManager", lambda *a, **k: _NoopAutoClick())

    # 計數包裝：訊號是否被連到同一個 slot 兩次，看「每次切換被呼叫幾次」最直接
    _orig_refresh = mw.MainWindow._refresh_theme_all

    def _counted(self):
        _REFRESH_CALLS.append(1)
        return _orig_refresh(self)

    monkeypatch_module.setattr(mw.MainWindow, "_refresh_theme_all", _counted)

    if "--smoke" not in sys.argv:
        sys.argv.append("--smoke")

    theme.apply_theme("dark")
    w = mw.MainWindow()
    yield w
    # 真正刪除 C++ 物件（含其 qconfig.themeChangedFinished 連線），避免下一個測試模組
    # 建立 MainWindow 時多一個實例一起回應主題訊號（與 conftest.theme_window 對齊）。
    try:
        from PySide6.QtCore import QCoreApplication, QEvent

        from qfluentwidgets import qconfig

        # 明確斷開 qconfig 連線：實測 close + deleteLater + DeferredDelete flush 後，
        # connection 仍可能殘留（qconfig.receivers == 1），導致洩漏到下一個測試模組。
        try:
            qconfig.themeChangedFinished.disconnect(w._refresh_theme_all)
        except (RuntimeError, TypeError):
            pass  # 本就未連線
        w._is_closing = True
        w.close()
        w.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    except Exception:
        pass


class _NoopAutoClick:
    def setup_auto_click_listener(self):
        pass

    def stop_auto_click_ahk(self):
        pass


@pytest.fixture(scope="module")
def monkeypatch_module():
    from _pytest.monkeypatch import MonkeyPatch

    mp = MonkeyPatch()
    yield mp
    mp.undo()


@pytest.fixture(autouse=True)
def _dark_baseline(window):
    """每個測試開始都回到 dark，避免測試互相污染。"""
    import qt.theme as theme

    theme.apply_theme("dark")
    yield


LEGACY_DARK_STATUS_BAR = "#status_bar { background: rgba(30,30,46,0.85); border-top: 1px solid #3d3d5c; }QLabel { font-size: 12px; color: #b8b8c8; }"


# ── 狀態列 ────────────────────────────────────────────────────────────────
def test_status_bar_dark_matches_phase0_look(window):
    """Dark 狀態列必須與 Phase 0 前的字面值逐字元一致（含 alpha 表示法）。"""
    import qt.theme as theme

    qss = window._status_bar.styleSheet()
    assert theme.qss_color("#1e1e2ed9") == "rgba(30,30,46,0.85)"
    assert qss == LEGACY_DARK_STATUS_BAR


def test_status_bar_light_uses_light_tokens(window):
    import qt.theme as theme

    theme.apply_theme("light")
    qss = window._status_bar.styleSheet()
    light = theme.TOKENS["light"]
    assert light["fg_muted"] in qss
    assert light["border_strong"] in qss
    assert theme.qss_color(light["statusbar_bg"]) in qss
    assert theme.TOKENS["dark"]["fg_muted"] not in qss


def test_status_bar_lamps_follow_business_state(window):
    import qt.theme as theme

    tok = theme.current_tokens()
    old_mon, old_pause, old_click = window._monitoring, window._global_pause, window._ahk_click_on
    try:
        window._monitoring = True
        window._global_pause = True
        window._ahk_click_on = False
        window._refresh_status_bar_theme()
        assert f"color: {tok['success']};" == window._status_monitor_label.styleSheet()
        assert f"color: {tok['warning']};" == window._status_pause_label.styleSheet()
        assert f"color: {tok['fg_muted']};" == window._status_click_label.styleSheet()

        theme.apply_theme("light")
        lt = theme.current_tokens()
        assert f"color: {lt['success']};" == window._status_monitor_label.styleSheet()
        assert f"color: {lt['warning']};" == window._status_pause_label.styleSheet()
    finally:
        window._monitoring = old_mon
        window._global_pause = old_pause
        window._ahk_click_on = old_click
        window._refresh_status_bar_theme()


def test_status_bar_theme_refresh_keeps_state(window):
    """切換主題只改顏色，不得動到監控狀態。"""
    import qt.theme as theme

    old = (window._monitoring, window._global_pause, window._ahk_click_on)
    theme.apply_theme("light")
    theme.apply_theme("dark")
    assert (window._monitoring, window._global_pause, window._ahk_click_on) == old
    assert window.is_monitoring() == old[0]


# ── Toast ────────────────────────────────────────────────────────────────
def test_toast_new_notice_uses_current_tokens(window):
    import qt.theme as theme

    theme.apply_theme("light")
    window._show_notice_impl("hello", "warning")
    notice = window._floating_notice
    assert notice is not None
    qss = notice._label.styleSheet()
    light = theme.TOKENS["light"]
    assert light["warning"] in qss
    assert theme.qss_color(light["toast_bg"]) in qss
    assert light["border_strong"] in qss
    assert theme.TOKENS["dark"]["toast_bg"] not in qss
    notice.hide_notice()


def test_toast_visible_updates_on_theme_switch(window):
    """已顯示中的 toast 切換主題也要換色，且動畫/可見狀態不受影響。"""
    import qt.theme as theme

    window._show_notice_impl("live", "success")
    notice = window._floating_notice
    assert notice.isVisible()
    assert notice._anim_timer.isActive()

    theme.apply_theme("light")
    qss = notice._label.styleSheet()
    assert theme.TOKENS["light"]["success"] in qss
    assert theme.qss_color(theme.TOKENS["light"]["toast_bg"]) in qss
    assert notice.isVisible(), "切換主題不得關閉顯示中的 toast"
    assert notice._anim_timer.isActive(), "切換主題不得中斷淡入淡出計時器"
    assert notice._opacity.opacity() <= 1.0  # 透明度效果仍掛著

    theme.apply_theme("dark")
    assert theme.TOKENS["dark"]["success"] in notice._label.styleSheet()
    notice.hide_notice()


def test_toast_unknown_type_falls_back_to_info(window):
    import qt.theme as theme

    window._show_notice_impl("x", "not-a-type")
    notice = window._floating_notice
    assert notice._msg_type == "info"
    assert theme.current_tokens()["info"] in notice._label.styleSheet()
    notice.hide_notice()


# ── SettingsTab BodyLabel ────────────────────────────────────────────────
def test_settings_body_labels_keep_font_size_across_theme_switch(window):
    import qt.theme as theme
    from PySide6.QtGui import QFont

    title = window.settings_tab._title_label
    assert title.font().pixelSize() == 20
    assert title.font().weight() == QFont.Weight.DemiBold

    for _ in range(2):
        theme.apply_theme("light")
        assert title.font().pixelSize() == 20, "切到 light 後字級被重設"
        assert "1f2328" in title.styleSheet().lower(), "BodyLabel 顏色未跟隨 light token"
        theme.apply_theme("dark")
        assert title.font().pixelSize() == 20, "切回 dark 後字級被重設"
        assert "f8f8f2" in title.styleSheet().lower(), "BodyLabel 顏色未回到 dark token"


def test_settings_body_labels_do_not_use_stylesheet_font(window):
    """字級一律走 setFont；若殘留 QSS font-size，setTheme 時會被覆蓋（已實測）。"""
    tab = window.settings_tab
    labels = [tab._title_label, tab._lang_label, tab._hot_header, tab._hot_title, tab._hot_hint, tab._data_header, tab._data_label, *tab._hotkey_row_labels.values()]
    for label in labels:
        assert "font-size" not in label.styleSheet(), f"{label} 仍用 QSS 設定字級"
        assert label.lightColor.isValid() and label.darkColor.isValid(), f"{label} 未設定雙主題顏色"


def test_settings_data_path_label_follows_theme(window):
    import qt.theme as theme

    label = window.settings_tab._data_path_label
    assert theme.TOKENS["dark"]["fg_muted"] in label.styleSheet()
    theme.apply_theme("light")
    assert theme.TOKENS["light"]["fg_muted"] in label.styleSheet()
    assert theme.TOKENS["dark"]["fg_muted"] not in label.styleSheet()


def test_settings_appearance_slot_shows_theme_selector(window):
    """Phase 4A：外觀卡片正式開放 Dark / Light 選項。

    （Phase 1 的「預留容器必須隱藏」前提已隨 Phase 4A 開放功能而失效，
    此處改驗證新契約：卡片可見、且只有主題選單一個下拉、兩個 Dark / Light 選項。）
    """
    from qfluentwidgets import ComboBox

    tab = window.settings_tab
    card = tab.appearance_card
    assert not card.isHidden(), "外觀卡片必須對使用者顯示"
    combos = card.findChildren(ComboBox)
    assert len(combos) == 1, f"外觀卡片應只有主題選單一個下拉，實得 {len(combos)}"
    assert combos[0] is tab.theme_combo
    assert tab.theme_combo.count() == 2
    assert [tab.theme_combo.itemData(i) for i in range(2)] == ["dark", "light"]


# ── 刷新管線 ─────────────────────────────────────────────────────────────
def test_no_qss_accumulation_over_cycle(window):
    import qt.theme as theme

    win_qss = window._status_bar.styleSheet()
    path_qss = window.settings_tab._data_path_label.styleSheet()
    for _ in range(3):
        theme.apply_theme("light")
        theme.apply_theme("dark")
    assert window._status_bar.styleSheet() == win_qss
    assert window.settings_tab._data_path_label.styleSheet() == path_qss


def test_theme_signal_connected_once(window):
    """重複呼叫 _connect_theme_signals() 不得造成同一 slot 被多次觸發。"""
    import qt.theme as theme

    before = len(_REFRESH_CALLS)
    theme.apply_theme("light")
    assert len(_REFRESH_CALLS) - before == 1, "一次切換應只觸發一次主題刷新"

    for _ in range(3):
        window._connect_theme_signals()

    before = len(_REFRESH_CALLS)
    theme.apply_theme("dark")
    assert len(_REFRESH_CALLS) - before == 1, "重複連接導致 slot 被觸發多次"
    assert window._theme_signal_connected is True


def test_refresh_tolerates_tabs_without_refresh_theme(window, monkeypatch):
    """沒有 refresh_theme 的分頁不得讓管線中斷。

    Phase 2E 後所有分頁都已遷移，此處以模擬「未遷移分頁」驗證 fan-out 的容錯性。
    """
    import qt.theme as theme

    monkeypatch.setattr(window.inventory_tab, "refresh_theme", None)
    theme.apply_theme("light")  # 不應拋錯
    assert theme.TOKENS["light"]["fg_muted"] in window._status_bar.styleSheet()
    theme.apply_theme("dark")


def test_refresh_tolerates_failing_tab(window, monkeypatch):
    """單一分頁刷新失敗不得影響狀態列等其他元件。"""
    import qt.theme as theme

    def boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(window.settings_tab, "refresh_theme", boom)
    theme.apply_theme("light")
    assert theme.TOKENS["light"]["fg_muted"] in window._status_bar.styleSheet()
    theme.apply_theme("dark")


def test_apply_theme_same_value_is_noop(window):
    import qt.theme as theme

    qss = window._status_bar.styleSheet()
    assert theme.apply_theme("dark") == "dark"
    assert window._status_bar.styleSheet() == qss
    assert theme.current_theme() == "dark"


# ── 既有功能不退化 ───────────────────────────────────────────────────────
def test_settings_language_and_hotkey_controls_intact(window):
    tab = window.settings_tab
    assert [tab.lang_combo.itemText(i) for i in range(tab.lang_combo.count())] == ["繁體中文", "简体中文", "English"]
    assert set(tab._combos) == {"f3", "f5", "f6", "f9", "f10", "skill_timer"}
    assert set(tab._hotkey_row_labels) == {"f3", "f5", "f6", "f9", "f10", "skill_timer"}
    assert tab.preview_switch.isChecked() == bool(window.config.get("preview_enabled", True))
    assert tab._reset_btn.isEnabled() and tab._open_data_btn.isEnabled()


def test_main_window_hotkey_signals_still_wired(window):
    """F9/F12/Toast 仍連到既有 slot（Phase 1 不得動業務 wiring）。"""
    old_pause = window._global_pause
    try:
        window.f9_request.emit()  # 應觸發 toggle_global_pause
        assert window._global_pause != old_pause, "F9 訊號未接到 toggle_global_pause"
    finally:
        window._global_pause = old_pause
        window._refresh_status_bar_theme()

    assert window.f12_request is not None and window.f10_request is not None
    window.floating_notice_request.emit("wiring check", "info")
    assert window._floating_notice is not None, "toast 訊號未接到 _show_notice_impl"
    assert window._floating_notice._label.text() == "wiring check"
    window._floating_notice.hide_notice()

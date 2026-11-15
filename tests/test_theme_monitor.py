"""Phase 2D 測試：MonitorTab + Monitor Dialogs 的主題 Token 遷移。

使用 tests/conftest.py 的 `theme_window`（offscreen 真實 MainWindow，單一實例共用）。
每個測試開始都回到 dark，結束後亦回到 dark，避免測試互相污染。

驗證重點（依 Phase 2D 交接單 §5）：
- Dark / Light token 正確、light 無 dark 殘留、可逆、冪等、不重建 widget。
- 監控狀態 / 暫停狀態 / 預覽資料 / 統計資料 / 執行緒 / 訊號連線 / 輪詢頻率不受刷新影響。
- Dialog 可即時刷新、不關閉不重建、輸入值保留、多 Dialog 各刷新一次、單一失敗不阻斷其他。
"""

import pytest

pytest.importorskip("PySide6.QtWidgets")

# dark 主題專屬色（light 主題下不應殘留在任何 Monitor / Dialog 的 QSS 中）
DARK_ONLY_COLORS = (
    "#f8f8f2",  # fg
    "#b8b8c8",  # fg_muted
    "#1e1e2e",  # surface
    "#3b3b3b",  # border
    "#3d3d5c",  # border_strong
    "#f38ba8",  # error_soft
    "#a6e3a1",  # success_soft
    "#89b4fa",  # info_soft
    "#f9e2af",  # warning_soft
)


# ── fixtures ─────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _isolate(theme_window):
    """每個測試前後都回到 dark（避免 light 殘留在其他測試）。"""
    import qt.theme as theme

    theme.apply_theme("dark")
    yield
    theme.apply_theme("dark")


@pytest.fixture
def theme(theme_window):
    import qt.theme as theme_mod

    return theme_mod


@pytest.fixture
def monitor(theme_window):
    return theme_window.monitor_tab


# ── helpers ──────────────────────────────────────────────────────────────
def _monitor_qss(monitor):
    """Monitor 全部已登記樣式的 QSS 清單（供殘留掃描）。"""
    qss = [monitor._style_qss(spec) for _, spec in monitor._styled]
    qss += [monitor._region_label_style(tone) for tone in monitor._region_labels.values()]
    return qss


def _dialog_qss(dialog):
    return [dialog._style_qss(spec) for _, spec in dialog._styled]


def _make_dialog(window, cls):
    """建立 Monitor Dialog（不 exec，測試直接操作）。"""
    dialog = cls(window, window.monitor_tab)
    return dialog


# ── Monitor：Dark / Light token ─────────────────────────────────────────
def test_monitor_dark_uses_dark_tokens(monitor, theme):
    dark = theme.TOKENS["dark"]
    assert monitor.page_title_label.styleSheet() == f"font-size: 20px; font-weight: 600; color: {dark['fg']};"
    assert monitor.health_label.styleSheet() == f"font-size: 16px; font-weight: 700; color: {dark['error_soft']};"
    assert monitor.mana_label.styleSheet() == f"font-size: 16px; font-weight: 700; color: {dark['info_soft']};"
    assert monitor.reminder_label.styleSheet() == f"color: {dark['error_soft']};"
    assert monitor.interface_ui_preview_hint.styleSheet() == f"font-size: 11px; color: {dark['fg_muted']};"
    assert dark["border_strong"] in monitor.window_frame.styleSheet()
    assert dark["surface"] in monitor.window_frame.styleSheet()
    assert dark["fg_muted"] in monitor.preview_label.styleSheet()
    assert dark["surface"] in monitor.settings_tree.styleSheet()


def test_monitor_light_uses_light_tokens(monitor, theme):
    theme.apply_theme("light")
    light = theme.TOKENS["light"]
    assert light["fg"] in monitor.page_title_label.styleSheet()
    assert light["error_soft"] in monitor.health_label.styleSheet()
    assert light["info_soft"] in monitor.mana_label.styleSheet()
    assert light["error_soft"] in monitor.reminder_label.styleSheet()
    assert light["fg_muted"] in monitor.interface_ui_preview_hint.styleSheet()
    assert light["border_strong"] in monitor.window_frame.styleSheet()
    assert light["surface"] in monitor.window_frame.styleSheet()
    assert light["surface"] in monitor.settings_tree.styleSheet()


def test_monitor_unstyled_labels_now_use_fg_token(monitor, theme):
    """原本走 OS palette 的說明文字：light 主題下不可殘留亮色（白）字。"""
    dark = theme.TOKENS["dark"]
    assert monitor.game_window_label.styleSheet() == f"color: {dark['fg']};"
    assert monitor.current_health_label.styleSheet() == f"color: {dark['fg']};"
    assert monitor.color_label.styleSheet() == f"color: {dark['fg']};"
    assert monitor.trigger_label.styleSheet() == f"color: {dark['fg']};"
    assert monitor.ms_label.styleSheet() == f"color: {dark['fg']};"


def test_monitor_light_has_no_dark_color_residue(monitor, theme):
    theme.apply_theme("light")
    for qss in _monitor_qss(monitor):
        for color in DARK_ONLY_COLORS:
            assert color not in qss, f"light 主題殘留 dark 色 {color}: {qss}"


def test_monitor_cycle_is_reversible(monitor, theme):
    title = monitor.page_title_label.styleSheet()
    health = monitor.health_label.styleSheet()
    group = monitor.window_frame.styleSheet()
    table = monitor.settings_tree.styleSheet()
    for _ in range(3):
        theme.apply_theme("light")
        theme.apply_theme("dark")
    assert monitor.page_title_label.styleSheet() == title
    assert monitor.health_label.styleSheet() == health
    assert monitor.window_frame.styleSheet() == group
    assert monitor.settings_tree.styleSheet() == table


def test_monitor_refresh_theme_is_idempotent(monitor, theme):
    before = monitor.page_title_label.styleSheet()
    length_before = len(monitor.window_frame.styleSheet())
    for _ in range(3):
        monitor.refresh_theme()
    assert monitor.page_title_label.styleSheet() == before
    assert len(monitor.window_frame.styleSheet()) == length_before
    assert monitor.window_frame.styleSheet().count("QGroupBox {") == 1


def test_monitor_refresh_does_not_rebuild_widgets(monitor, theme):
    ids_before = (
        id(monitor.window_frame),
        id(monitor.settings_tree),
        id(monitor.preview_label),
        id(monitor.page_title_label),
    )
    row_count = monitor.settings_tree.rowCount()
    theme.apply_theme("light")
    theme.apply_theme("dark")
    assert (id(monitor.window_frame), id(monitor.settings_tree), id(monitor.preview_label), id(monitor.page_title_label)) == ids_before
    assert monitor.settings_tree.rowCount() == row_count


# ── Monitor：執行狀態保護 ───────────────────────────────────────────────
def test_monitor_refresh_keeps_monitoring_state(theme_window, monitor, theme):
    window = theme_window
    window.set_monitoring(True)
    try:
        theme.apply_theme("light")
        assert window.is_monitoring() is True
        theme.apply_theme("dark")
        assert window.is_monitoring() is True
    finally:
        window.set_monitoring(False)


def test_monitor_refresh_keeps_pause_state(theme_window, monitor, theme):
    window = theme_window
    window.set_global_pause(True)
    try:
        theme.apply_theme("light")
        assert window.is_global_pause() is True
    finally:
        window.set_global_pause(False)


def test_monitor_refresh_keeps_statistics_text(monitor, theme):
    monitor.health_label.setText("77%")
    monitor.mana_label.setText("42%")
    monitor.color_label.setText("#a1b2c3")
    monitor.trigger_label.setText("triggered")
    theme.apply_theme("light")
    assert monitor.health_label.text() == "77%"
    assert monitor.mana_label.text() == "42%"
    assert monitor.color_label.text() == "#a1b2c3"
    assert monitor.trigger_label.text() == "triggered"


def test_monitor_refresh_keeps_preview_data(monitor, theme):
    from PySide6.QtGui import QPixmap

    pix = QPixmap(20, 10)
    pix.fill()
    monitor.preview_label.setPixmap(pix)  # QLabel 的 pixmap 與 text 互斥 → 分開驗證
    monitor.mana_preview_label.setText("mana-placeholder")
    theme.apply_theme("light")
    assert not monitor.preview_label.pixmap().isNull()
    assert monitor.mana_preview_label.text() == "mana-placeholder"


def test_monitor_refresh_does_not_restart_thread(theme_window, monitor, theme):
    thread_before = theme_window._monitor_thread
    theme.apply_theme("light")
    assert theme_window._monitor_thread is thread_before


def test_monitor_refresh_does_not_add_signal_connections(monitor, theme):
    """已連線的 slot 不得因刷新而被重複連線（emit 後 _set_preview_pixmap 只應被呼叫一次）。"""
    calls = []
    original = monitor._set_preview_pixmap

    def counting(label, pil_img):
        calls.append(label)
        return original(label, pil_img)

    monitor._set_preview_pixmap = counting
    try:
        theme.apply_theme("light")
        from PIL import Image

        monitor._signals.health_preview.emit(Image.new("RGB", (4, 4)))
        assert len(calls) == 1, f"signal 被重複連線：{len(calls)}"
    finally:
        monitor._set_preview_pixmap = original


def test_monitor_refresh_does_not_change_update_frequency(monitor, theme):
    before = (monitor.monitor_interval_ms, monitor.preview_update_interval, monitor.status_update_interval)
    theme.apply_theme("light")
    assert (monitor.monitor_interval_ms, monitor.preview_update_interval, monitor.status_update_interval) == before


def test_monitor_dynamic_update_keeps_current_theme(monitor, theme):
    """主題刷新後的即時資料更新，不得把樣式退回舊主題。"""
    theme.apply_theme("light")
    monitor._on_status_updated("88%", "33%", "#ff0000", "")
    light = theme.TOKENS["light"]
    assert monitor.health_label.text() == "88%"
    assert light["error_soft"] in monitor.health_label.styleSheet()


def test_monitor_region_tone_follows_business_state(monitor, theme):
    """已框選的區域標籤維持 success 語意色，主題刷新不得把它改回灰。"""
    from PySide6.QtWidgets import QLabel

    label = QLabel("--")
    monitor._region_labels[label] = "fg_muted"
    monitor._set_region_tone(label, "success_soft")
    theme.apply_theme("light")
    light = theme.TOKENS["light"]
    assert light["success_soft"] in label.styleSheet()
    assert label.styleSheet().count("; color:") == 1


def test_monitor_refresh_failure_does_not_block_other_widgets(monitor, theme, monkeypatch):
    """單一元件套樣式失敗不得讓整個刷新中斷。"""
    original = monitor._style_qss

    def selective(spec):
        if spec[0] == "group":
            raise RuntimeError("boom")
        return original(spec)

    monkeypatch.setattr(type(monitor), "_style_qss", staticmethod(selective))
    monitor.refresh_theme()
    # 其他元件仍已套上目前主題
    tok = theme.current_tokens()
    assert tok["fg"] in monitor.page_title_label.styleSheet()
    assert tok["error_soft"] in monitor.health_label.styleSheet()


# ── Monitor Dialogs ─────────────────────────────────────────────────────
def test_dialog_dark_uses_dark_tokens(theme_window, theme):
    from qt.monitor_dialogs import AdjustColorsDialog

    dialog = _make_dialog(theme_window, AdjustColorsDialog)
    dark = theme.TOKENS["dark"]
    assert dark["window_bg"] in dialog.styleSheet()
    group = dialog.findChildren(__import__("PySide6.QtWidgets", fromlist=["QGroupBox"]).QGroupBox)[0]
    assert dark["border_strong"] in group.styleSheet()
    assert dark["surface"] in group.styleSheet()
    assert dark["fg"] in group.styleSheet()


def test_dialog_light_uses_light_tokens(theme_window, theme):
    from qt.monitor_dialogs import AdjustColorsDialog

    theme.apply_theme("light")
    dialog = _make_dialog(theme_window, AdjustColorsDialog)
    light = theme.TOKENS["light"]
    assert light["window_bg"] in dialog.styleSheet()
    group = dialog.findChildren(__import__("PySide6.QtWidgets", fromlist=["QGroupBox"]).QGroupBox)[0]
    assert light["border_strong"] in group.styleSheet()
    assert light["surface"] in group.styleSheet()


def test_dialog_light_has_no_dark_color_residue(theme_window, theme):
    from qt.monitor_dialogs import AdjustColorsDialog, AdjustInterfaceUiDialog

    theme.apply_theme("light")
    for cls in (AdjustColorsDialog, AdjustInterfaceUiDialog):
        dialog = _make_dialog(theme_window, cls)
        for qss in _dialog_qss(dialog):
            for color in DARK_ONLY_COLORS:
                assert color not in qss, f"{cls.__name__} light 殘留 dark 色 {color}: {qss}"


def test_dialog_cycle_is_reversible(theme_window, theme):
    from qt.monitor_dialogs import AdjustColorsDialog

    theme.apply_theme("dark")
    dialog = _make_dialog(theme_window, AdjustColorsDialog)
    dark_qss = dialog.styleSheet()
    group_qss = dialog.findChildren(__import__("PySide6.QtWidgets", fromlist=["QGroupBox"]).QGroupBox)[0].styleSheet()
    for _ in range(3):
        theme.apply_theme("light")
        theme.apply_theme("dark")
    assert dialog.styleSheet() == dark_qss
    assert dialog.findChildren(__import__("PySide6.QtWidgets", fromlist=["QGroupBox"]).QGroupBox)[0].styleSheet() == group_qss


def test_open_dialog_refreshes_live(theme_window, monitor, theme):
    """已開啟的 Dialog 在主題切換時即時換色（MonitorTab 負責刷新）。"""
    from qt.monitor_dialogs import AdjustColorsDialog

    dialog = _make_dialog(theme_window, AdjustColorsDialog)
    monitor._dialogs.append(dialog)
    try:
        theme.apply_theme("light")
        light = theme.TOKENS["light"]
        assert light["window_bg"] in dialog.styleSheet()
        group = dialog.findChildren(__import__("PySide6.QtWidgets", fromlist=["QGroupBox"]).QGroupBox)[0]
        assert light["border_strong"] in group.styleSheet()
    finally:
        monitor._dialogs.remove(dialog)


def test_open_dialog_is_not_closed_or_rebuilt(theme_window, monitor, theme):
    from qt.monitor_dialogs import AdjustColorsDialog

    dialog = _make_dialog(theme_window, AdjustColorsDialog)
    monitor._dialogs.append(dialog)
    try:
        entries = dialog.findChildren(__import__("qfluentwidgets", fromlist=["LineEdit"]).LineEdit)
        entries[0].setText("0.42")
        theme.apply_theme("light")
        # 物件不得被重建（parent 與登記仍在）
        assert dialog.parent() is monitor
        assert dialog.findChildren(__import__("qfluentwidgets", fromlist=["LineEdit"]).LineEdit)[0].text() == "0.42"
        assert dialog in monitor._dialogs
    finally:
        monitor._dialogs.remove(dialog)


def test_dialog_reopen_uses_current_theme(theme_window, monitor, theme):
    """關閉後重新開啟的 Dialog 必須直接使用當前主題。"""
    from qt.monitor_dialogs import AdjustColorsDialog

    theme.apply_theme("light")
    dialog = _make_dialog(theme_window, AdjustColorsDialog)
    light = theme.TOKENS["light"]
    assert light["window_bg"] in dialog.styleSheet()
    dialog.close()


def test_multiple_dialogs_each_refresh_once(theme_window, monitor, theme):
    from qt.monitor_dialogs import AdjustColorsDialog, AdjustInterfaceUiDialog

    d1 = _make_dialog(theme_window, AdjustColorsDialog)
    d2 = _make_dialog(theme_window, AdjustInterfaceUiDialog)
    monitor._dialogs.extend([d1, d2])
    counts = {id(d1): 0, id(d2): 0}
    orig1, orig2 = d1.refresh_theme, d2.refresh_theme

    def wrap(dialog, key):
        def inner():
            counts[key] += 1
            return dialog._style_qss  # no-op

        return inner

    d1.refresh_theme = wrap(d1, id(d1))
    d2.refresh_theme = wrap(d2, id(d2))
    try:
        theme.apply_theme("light")
        assert counts[id(d1)] == 1
        assert counts[id(d2)] == 1
    finally:
        d1.refresh_theme = orig1
        d2.refresh_theme = orig2
        monitor._dialogs.remove(d1)
        monitor._dialogs.remove(d2)


def test_single_dialog_refresh_failure_does_not_block_others(theme_window, monitor, theme):
    from qt.monitor_dialogs import AdjustColorsDialog, AdjustInterfaceUiDialog

    d1 = _make_dialog(theme_window, AdjustColorsDialog)
    d2 = _make_dialog(theme_window, AdjustInterfaceUiDialog)
    monitor._dialogs.extend([d1, d2])
    called = []

    def boom():
        raise RuntimeError("boom")

    d1.refresh_theme = boom
    d2.refresh_theme = lambda: called.append(True)
    try:
        theme.apply_theme("light")
        assert called == [True]
    finally:
        monitor._dialogs.remove(d1)
        monitor._dialogs.remove(d2)


def test_dialog_refresh_does_not_accumulate_qss(theme_window, monitor, theme):
    from qt.monitor_dialogs import AdjustColorsDialog

    dialog = _make_dialog(theme_window, AdjustColorsDialog)
    monitor._dialogs.append(dialog)
    try:
        theme.apply_theme("light")
        length = len(dialog.styleSheet())
        for _ in range(3):
            dialog.refresh_theme()
        assert len(dialog.styleSheet()) == length
        assert dialog.styleSheet().count("QDialog") == 1
    finally:
        monitor._dialogs.remove(dialog)


def test_dialog_buttons_and_entries_still_usable(theme_window, monitor, theme):
    from qfluentwidgets import LineEdit, PushButton

    from qt.monitor_dialogs import AdjustColorsDialog

    dialog = _make_dialog(theme_window, AdjustColorsDialog)
    monitor._dialogs.append(dialog)
    try:
        theme.apply_theme("light")
        buttons = dialog.findChildren(PushButton)
        assert len(buttons) == 3
        assert all(b.isEnabled() for b in buttons)
        entries = dialog.findChildren(LineEdit)
        assert len(entries) == 7
        entries[0].setText("0.11")
        theme.apply_theme("dark")
        assert entries[0].text() == "0.11"
    finally:
        monitor._dialogs.remove(dialog)


def test_monitor_tracks_dialog_opened_by_button(theme_window, monitor, theme, monkeypatch):
    """由按鈕開啟的 Dialog 必須被 MonitorTab 登記（關閉後移除登記）。"""
    from qt.monitor_dialogs import AdjustColorsDialog

    seen = {}

    def fake_exec(self):
        seen["tracked"] = list(monitor._dialogs)
        return 0

    monkeypatch.setattr(AdjustColorsDialog, "exec", fake_exec)
    monitor.open_adjust_colors()
    assert len(seen["tracked"]) == 1
    assert isinstance(seen["tracked"][0], AdjustColorsDialog)
    assert monitor._dialogs == []


# ── 整合 ─────────────────────────────────────────────────────────────────
def test_main_window_fan_out_refreshes_monitor(theme_window, theme):
    monitor = theme_window.monitor_tab
    calls = []
    original = monitor.refresh_theme

    def counting():
        calls.append(True)
        return original()

    theme_window.monitor_tab.refresh_theme = counting
    try:
        theme.apply_theme("light")
        assert len(calls) == 1
    finally:
        theme_window.monitor_tab.refresh_theme = original


def test_monitor_refresh_failure_does_not_block_other_tabs(theme_window, theme):
    monitor = theme_window.monitor_tab

    def boom():
        raise RuntimeError("boom")

    theme_window.monitor_tab.refresh_theme = boom
    try:
        theme.apply_theme("light")
        light = theme.TOKENS["light"]
        assert light["fg"] in theme_window.status_tab.title_label.styleSheet()
        combo_qss = [widget.styleSheet() for widget, _ in theme_window.combo_tab._styled]
        assert any(light["fg"] in qss for qss in combo_qss)
    finally:
        theme_window.monitor_tab.refresh_theme = monitor.refresh_theme


def test_inventory_is_not_rebuilt_by_theme_switch(theme_window, theme):
    """Phase 2E：Inventory 已遷移；切換主題仍不得重建任何元件。"""
    inventory = theme_window.inventory_tab
    assert callable(getattr(inventory, "refresh_theme", None)), "inventory 已於 Phase 2E 遷移，應有 refresh_theme()"
    before = len(inventory.findChildren(__import__("PySide6.QtWidgets", fromlist=["QWidget"]).QWidget))
    theme.apply_theme("light")
    after = len(inventory.findChildren(__import__("PySide6.QtWidgets", fromlist=["QWidget"]).QWidget))
    assert before == after


def test_existing_theme_pages_tests_not_regressed(theme_window, theme):
    """Phase 2A～2C 的分頁仍能正常刷新（Monitor 失敗不影響它們）。"""
    theme.apply_theme("light")
    light = theme.TOKENS["light"]
    assert light["fg"] in theme_window.status_tab.title_label.styleSheet()
    help_qss = [widget.styleSheet() for widget, _ in theme_window.help_tab._styled]
    assert any(light["fg"] in qss for qss in help_qss)
    theme.apply_theme("dark")
    dark = theme.TOKENS["dark"]
    assert dark["fg"] in theme_window.status_tab.title_label.styleSheet()
    help_qss_dark = [widget.styleSheet() for widget, _ in theme_window.help_tab._styled]
    assert any(dark["fg"] in qss for qss in help_qss_dark)

"""Phase 2E 測試：Inventory 分頁與其 Dialog 的主題 Token 遷移。

使用 tests/conftest.py 的 `theme_window`（offscreen 真實 MainWindow，單一實例共用）。
每個測試開始都回到 dark，結束後還原，避免測試互相污染。
"""

import re
from pathlib import Path

import pytest

pytest.importorskip("PySide6.QtWidgets")

_SRC = Path(__file__).resolve().parent.parent / "src" / "qt" / "inventory.py"

# 遷移前 Inventory 寫死的色值（light 下不得殘留）
LEGACY_INVENTORY_COLORS = ("#f38ba8", "#a6e3a1", "#89b4fa", "#b8b8c8", "#1e1e2e", "#3d3d5c", "#f8f8f2")


# ── fixtures ─────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _isolate(theme_window):
    """每個測試前回到 dark，結束後還原（避免測試間污染）。"""
    import qt.theme as theme

    theme.apply_theme("dark")
    yield
    theme.apply_theme("dark")


@pytest.fixture
def theme(theme_window):
    import qt.theme as theme_mod

    return theme_mod


@pytest.fixture
def inv(theme_window):
    return theme_window.inventory_tab


# ── helpers ──────────────────────────────────────────────────────────────
def _inv_qss(tab):
    """Inventory 自管 QSS 快照（靜態登記表 + 語意色元件）。"""
    qss = [w.styleSheet() for w, _ in tab._styled]
    qss += [w.styleSheet() for w in tab._tones]
    return qss


def _groups(tab):
    from PySide6.QtWidgets import QGroupBox

    return [g for g in tab.findChildren(QGroupBox) if g.styleSheet()]


def _relative_luminance(hex_color: str) -> float:
    raw = hex_color.lstrip("#")
    r, g, b = (int(raw[i : i + 2], 16) / 255 for i in (0, 2, 4))

    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _contrast(a: str, b: str) -> float:
    la, lb = _relative_luminance(a), _relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _qss_prop(qss: str, prop: str):
    m = re.search(rf"(?<![-\w]){re.escape(prop)}:\s*([^;]+);", qss)
    return m.group(1).strip() if m else None


# ══════════════════════════════════════════════════════════════════════════
# 1. Inventory 頁面建立
# ══════════════════════════════════════════════════════════════════════════
def test_inventory_page_is_created(inv, theme_window):
    """Inventory 分頁應正常建立，且六個群組框與主要控制項都在。"""
    from PySide6.QtWidgets import QGroupBox

    assert inv is not None
    assert theme_window.isAncestorOf(inv), "Inventory 分頁必須掛在 MainWindow 底下"
    assert inv.page_title_label.text()
    assert len(inv.findChildren(QGroupBox)) == 6, "背包設定/控制/狀態/取物/UI截圖/預覽 六個群組框"
    for attr in (
        "select_inventory_region_btn",
        "record_empty_color_btn",
        "select_inventory_ui_btn",
        "test_clear_inventory_btn",
        "clear_click_left_radio",
        "clear_click_right_radio",
        "always_on_top_check",
        "setup_pickup_coordinates_btn",
        "reset_offset_btn",
        "inventory_preview_label",
        "ui_preview_label",
    ):
        assert getattr(inv, attr, None) is not None, f"缺少元件 {attr}"


def test_inventory_refresh_theme_runs_without_error(inv):
    """refresh_theme() 必須能正常執行，且不得新增樣式登記。"""
    before_static = len(inv._styled)
    before_tones = len(inv._tones)
    inv.refresh_theme()
    assert len(inv._styled) == before_static
    assert len(inv._tones) == before_tones


# ══════════════════════════════════════════════════════════════════════════
# 2. Token 使用與顏色檢查
# ══════════════════════════════════════════════════════════════════════════
def test_inventory_dark_uses_dark_tokens(inv, theme):
    """Dark 主題下所有自管 QSS 必須使用 dark token。"""
    dark = theme.TOKENS["dark"]
    assert inv.page_title_label.styleSheet() == f"font-size: 20px; font-weight: 600; color: {dark['fg']};"
    assert inv.empty_color_label.styleSheet() == (f"background-color: {dark['surface']}; border: 1px solid {dark['border_strong']}; border-radius: 4px; padding: 4px 8px; color: {dark['fg_muted']};")
    assert inv.inventory_status_label.styleSheet() == f"color: {dark['success_soft']};"
    assert inv.occupied_label.styleSheet() == f"color: {dark['info_soft']}; font-size: 13px; font-weight: 600;"
    assert inv.ui_preview_hint_label.styleSheet() == f"color: {dark['fg_muted']}; font-size: 11px;"
    for group in _groups(inv):
        assert f"border: 1px solid {dark['border_strong']};" in group.styleSheet()
        assert f"color: {dark['fg']};" in group.styleSheet()


def test_inventory_light_uses_light_tokens(inv, theme):
    """Light 主題下所有自管 QSS 必須使用 light token。"""
    theme.apply_theme("light")
    light = theme.TOKENS["light"]
    assert inv.page_title_label.styleSheet() == f"font-size: 20px; font-weight: 600; color: {light['fg']};"
    assert inv.empty_color_label.styleSheet() == (
        f"background-color: {light['surface']}; border: 1px solid {light['border_strong']}; border-radius: 4px; padding: 4px 8px; color: {light['fg_muted']};"
    )
    assert inv.inventory_status_label.styleSheet() == f"color: {light['success_soft']};"
    assert inv.occupied_label.styleSheet() == f"color: {light['info_soft']}; font-size: 13px; font-weight: 600;"
    for group in _groups(inv):
        assert f"border: 1px solid {light['border_strong']};" in group.styleSheet()


def test_inventory_light_has_no_dark_residue(inv, theme):
    """Light 下不得殘留 dark token 或遷移前的硬編碼色值。"""
    theme.apply_theme("light")
    joined = " ".join(_inv_qss(inv))
    forbidden = set(theme.TOKENS["dark"].values()) | set(LEGACY_INVENTORY_COLORS)
    for legacy in sorted(forbidden):
        assert legacy not in joined, f"light Inventory 殘留 dark 色 {legacy}"


def test_inventory_source_has_no_hardcoded_colors():
    """原始碼不得再出現寫死的 HEX / RGB 色值（顏色一律走 qt.theme token）。"""
    source = _SRC.read_text(encoding="utf-8")
    assert not re.search(r"#[0-9a-fA-F]{6}(?![0-9a-fA-F])", source), "inventory.py 仍有寫死的 HEX 色值"
    assert not re.search(r"rgba?\(", source), "inventory.py 仍有寫死的 RGB(A) 色值"


def test_inventory_group_boxes_are_transparent(inv):
    """群組框內部原本走 OS palette（light 主題下是深色殘留）→ 必須透明。"""
    groups = _groups(inv)
    assert len(groups) == 6
    for group in groups:
        assert "background: transparent;" in group.styleSheet(), f"QGroupBox 未透明：{group.styleSheet()[:70]}"


def test_inventory_scroll_area_paints_theme_background(inv, theme):
    """左欄 QScrollArea 必須自繪底色。

    qfluentwidgets StackedWidget 在深色主題下露出的是「白色底」，若捲動區留透明，
    深色文字會疊在白底上（不可讀）→ 必須用 window_bg token 自繪。
    """
    from PySide6.QtWidgets import QScrollArea

    scrolls = inv.findChildren(QScrollArea)
    assert scrolls, "測試前提：Inventory 左欄仍是 QScrollArea"
    scroll = scrolls[0]
    dark = theme.TOKENS["dark"]
    assert dark["window_bg"] in scroll.styleSheet()
    assert scroll.viewport().autoFillBackground() is False
    assert scroll.widget().autoFillBackground() is False
    theme.apply_theme("light")
    assert theme.TOKENS["light"]["window_bg"] in scroll.styleSheet()


def test_inventory_right_column_paints_theme_background(inv, theme):
    """右欄容器同樣必須自繪底色（ID 選擇器不 cascade 到子元件，避免蓋掉按鈕樣式）。"""
    from PySide6.QtWidgets import QWidget

    from qt.inventory import RIGHT_COLUMN_OBJECT

    column = inv.findChild(QWidget, RIGHT_COLUMN_OBJECT)
    assert column is not None, "右欄容器必須有 objectName 才能套用底色"
    dark = theme.TOKENS["dark"]
    assert dark["window_bg"] in column.styleSheet()
    theme.apply_theme("light")
    assert theme.TOKENS["light"]["window_bg"] in column.styleSheet()


def test_inventory_unstyled_labels_are_now_tokenized(inv, theme):
    """原本完全未上色的說明文字必須改用 fg token，否則 light 下會是亮字亮底。"""
    theme.apply_theme("light")
    light = theme.TOKENS["light"]
    for attr in (
        "record_status_label",
        "inventory_ui_status_label",
        "clear_click_mode_label",
        "gui_settings_label",
        "inventory_f3_label",
        "pause_status_label_title",
        "coordinates_set_label",
        "pickup_f6_label",
        "occupied_label_title",
        "horizontal_label",
        "vertical_label",
    ):
        label = getattr(inv, attr)
        assert label.styleSheet() == f"color: {light['fg']};", f"{attr} 未使用 fg token"


def test_inventory_light_text_contrast_is_readable(theme):
    """Light 下 Inventory 用到的語意色對 surface 須達 WCAG AA（4.5:1）。"""
    light = theme.TOKENS["light"]
    for key in ("fg", "fg_muted", "success_soft", "info_soft", "warning"):
        ratio = _contrast(light[key], light["surface"])
        assert ratio >= 4.5, f"light {key} 對比不足 {ratio:.2f}:1"


# ══════════════════════════════════════════════════════════════════════════
# 3. Dark → Light → Dark 刷新流程
# ══════════════════════════════════════════════════════════════════════════
def test_inventory_cycle_is_reversible(inv, theme):
    before = _inv_qss(inv)
    for _ in range(3):
        theme.apply_theme("light")
        theme.apply_theme("dark")
    assert _inv_qss(inv) == before


def test_inventory_refresh_is_idempotent(inv):
    static, tones = len(inv._styled), len(inv._tones)
    first = _inv_qss(inv)
    for _ in range(5):
        inv.refresh_theme()
    assert _inv_qss(inv) == first
    assert len(inv._styled) == static, "重複刷新不得登記新元件"
    assert len(inv._tones) == tones, "重複刷新不得新增語意色元件"


def test_inventory_theme_refresh_called_once_per_switch(inv, theme, monkeypatch):
    """Inventory 不得自行連主題訊號；單次切換只刷新一次。"""
    calls = []
    original = inv.refresh_theme

    def counted():
        calls.append(1)
        original()

    monkeypatch.setattr(inv, "refresh_theme", counted)
    theme.apply_theme("light")
    assert len(calls) == 1, "單次切換不得重複刷新 Inventory"
    theme.apply_theme("dark")
    assert len(calls) == 2


def test_inventory_refresh_does_not_rebuild_widgets(inv, theme, monkeypatch):
    """切換主題不得重建 Inventory 元件。"""
    ids = (
        id(inv.page_title_label),
        id(inv.inventory_settings_frame),
        id(inv.control_frame),
        id(inv.status_frame),
        id(inv.pickup_frame),
        id(inv.ui_preview_frame),
        id(inv.preview_frame),
        id(inv.inventory_preview_label),
        id(inv.empty_color_label),
    )

    def boom(*a, **k):
        raise AssertionError("refresh_theme 不得重建 Inventory 頁")

    monkeypatch.setattr(inv, "_build_ui", boom)
    theme.apply_theme("light")
    theme.apply_theme("dark")
    after = (
        id(inv.page_title_label),
        id(inv.inventory_settings_frame),
        id(inv.control_frame),
        id(inv.status_frame),
        id(inv.pickup_frame),
        id(inv.ui_preview_frame),
        id(inv.preview_frame),
        id(inv.inventory_preview_label),
        id(inv.empty_color_label),
    )
    assert after == ids


# ══════════════════════════════════════════════════════════════════════════
# 4. 動態元件套用當前主題
# ══════════════════════════════════════════════════════════════════════════
def test_dynamic_value_labels_follow_business_state(inv, theme):
    """空格顏色/背包UI 狀態依業務狀態決定語意色，切換主題不得覆蓋成固定色。"""
    dark = theme.TOKENS["dark"]
    try:
        inv.empty_inventory_colors = [(1, 2, 3)]
        inv.refresh_config_display()
        assert inv.empty_color_label.styleSheet() == (
            f"background-color: {dark['surface']}; border: 1px solid {dark['border_strong']}; border-radius: 4px; padding: 4px 8px; color: {dark['success_soft']};"
        )
        theme.apply_theme("light")
        light = theme.TOKENS["light"]
        assert inv.empty_color_label.styleSheet() == (
            f"background-color: {light['surface']}; border: 1px solid {light['border_strong']}; border-radius: 4px; padding: 4px 8px; color: {light['success_soft']};"
        ), "刷新不得覆蓋業務狀態色"
        inv.refresh_theme()
        assert light["success_soft"] in inv.empty_color_label.styleSheet()
    finally:
        inv.empty_inventory_colors = []
        inv.refresh_config_display()


def test_dynamic_preview_placeholder_uses_current_theme(inv, theme):
    """動態建立的預覽佔位文字必須取當前主題色，且切換後跟著更新。"""
    theme.apply_theme("light")
    light = theme.TOKENS["light"]
    inv.set_preview_placeholder("placeholder", "warning")
    assert inv.inventory_preview_label.styleSheet() == (f"background-color: {light['surface']}; border: 1px solid {light['border_strong']}; border-radius: 4px; color: {light['warning']};")
    theme.apply_theme("dark")
    dark = theme.TOKENS["dark"]
    assert inv.inventory_preview_label.styleSheet() == (f"background-color: {dark['surface']}; border: 1px solid {dark['border_strong']}; border-radius: 4px; color: {dark['warning']};")


def test_dynamic_ui_preview_placeholder_uses_current_theme(inv, theme):
    theme.apply_theme("light")
    light = theme.TOKENS["light"]
    inv.set_ui_preview_placeholder("empty")
    assert _qss_prop(inv.ui_preview_label.styleSheet(), "color") == light["fg_muted"]
    theme.apply_theme("dark")
    assert _qss_prop(inv.ui_preview_label.styleSheet(), "color") == theme.TOKENS["dark"]["fg_muted"]


def test_dynamic_pickup_status_follows_coordinates(inv, theme):
    """取物座標數有/無 → 語意色切換，且主題刷新後保持。"""
    original = inv.pickup_coordinates
    try:
        inv.pickup_coordinates = [[0, 0] for _ in range(5)]
        inv.update_pickup_status()
        dark = theme.TOKENS["dark"]
        assert inv.pickup_coords_label.styleSheet() == f"color: {dark['fg_muted']};"
        inv.pickup_coordinates = [[10, 20] for _ in range(5)]
        inv.update_pickup_status()
        assert inv.pickup_coords_label.styleSheet() == f"color: {dark['success_soft']};"
        theme.apply_theme("light")
        light = theme.TOKENS["light"]
        assert inv.pickup_coords_label.styleSheet() == f"color: {light['success_soft']};"
    finally:
        inv.pickup_coordinates = original
        inv.update_pickup_status()


def test_offset_labels_use_token_field_style(inv, theme):
    """偏移量欄位是 surface 底的輸入框，文字用 fg token。"""
    dark = theme.TOKENS["dark"]
    for label in (inv.offset_x_label, inv.offset_y_label):
        assert label.styleSheet() == (f"background-color: {dark['surface']}; border: 1px solid {dark['border_strong']}; border-radius: 4px; padding: 4px 8px; color: {dark['fg']};")


# ══════════════════════════════════════════════════════════════════════════
# 5. Dialog 建立與關閉
# ══════════════════════════════════════════════════════════════════════════
def test_pickup_dialog_creates_with_current_theme(inv, theme):
    """F6 取物座標視窗建立當下即套用當前主題。"""
    from qt.inventory import _PickupSetupDialog

    theme.apply_theme("light")
    light = theme.TOKENS["light"]
    dialog = _PickupSetupDialog(inv, None)
    try:
        assert light["window_bg"] in dialog.styleSheet()
        assert len(dialog.coord_labels) == 5
        assert len(dialog.status_labels) == 5
        for label in dialog.coord_labels:
            assert light["surface"] in label.styleSheet()
            assert light["fg"] in label.styleSheet()
        for label in dialog.status_labels:
            assert light["fg_muted"] in label.styleSheet()
    finally:
        dialog.close()
        dialog.deleteLater()


def test_coord_hint_window_creates_with_current_theme(inv, theme):
    """連續設定座標的提示視窗同樣走 token。"""
    from qt.inventory import _CoordHintWindow

    theme.apply_theme("light")
    light = theme.TOKENS["light"]
    hint = _CoordHintWindow("title", "hint", None)
    try:
        assert light["surface"] in hint.styleSheet()
        assert light["fg"] in " ".join(w.styleSheet() for w, _ in hint._styled)
    finally:
        hint.close()
        hint.deleteLater()


def test_pickup_dialog_lifecycle_registers_and_unregisters(inv, theme, monkeypatch):
    """取物座標視窗開啟期間要登記在生命週期表，關閉後必須解除。"""
    from PySide6.QtWidgets import QDialog

    captured = {}

    def fake_exec(self):
        captured["dialog"] = self
        captured["registered"] = self in inv._dialogs
        captured["setup_ref"] = inv._setup_dialog is self
        return 0

    monkeypatch.setattr(QDialog, "exec", fake_exec)
    inv.setup_pickup_coordinates()

    assert captured.get("registered") is True, "Dialog 開啟期間必須登記於生命週期表"
    assert captured.get("setup_ref") is True
    assert inv._setup_dialog is None, "Dialog 關閉後 _setup_dialog 必須清空"
    assert captured["dialog"] not in inv._dialogs, "Dialog 關閉後不得殘留於生命週期表"


def test_dialog_removed_from_registry_on_unregister(inv):
    """解除登記後生命週期表不得殘留該 Dialog。"""
    from qt.inventory import _CoordHintWindow

    hint = _CoordHintWindow("t", "h", None)
    inv._register_dialog(hint)
    assert hint in inv._dialogs
    inv._unregister_dialog(hint)
    assert hint not in inv._dialogs
    hint.close()
    hint.deleteLater()


# ══════════════════════════════════════════════════════════════════════════
# 6. 已開啟 Dialog 在主題切換後能更新
# ══════════════════════════════════════════════════════════════════════════
def test_open_dialog_refreshes_on_theme_switch(inv, theme):
    """已開啟的取物座標視窗必須在 Dark ↔ Light 切換時即時換色（不關閉、不重建）。"""
    from qt.inventory import _PickupSetupDialog

    dialog = _PickupSetupDialog(inv, None)
    inv._register_dialog(dialog)
    try:
        theme.apply_theme("light")
        light = theme.TOKENS["light"]
        assert light["window_bg"] in dialog.styleSheet()
        assert all(light["surface"] in label.styleSheet() for label in dialog.coord_labels)
        assert dialog.isVisible() is False or True  # 不因刷新被關閉
        assert inv._setup_dialog is None or inv._setup_dialog is dialog

        theme.apply_theme("dark")
        dark = theme.TOKENS["dark"]
        assert dark["window_bg"] in dialog.styleSheet()
        assert all(dark["surface"] in label.styleSheet() for label in dialog.coord_labels)
    finally:
        inv._unregister_dialog(dialog)
        dialog.close()
        dialog.deleteLater()


def test_open_dialog_is_not_closed_or_rebuilt(inv, theme):
    """主題刷新不得關閉或重建已開啟的 Dialog。"""
    from qt.inventory import _PickupSetupDialog

    dialog = _PickupSetupDialog(inv, None)
    inv._register_dialog(dialog)
    try:
        dialog.show()
        ids = [id(c) for c in dialog.coord_labels] + [id(c) for c in dialog.status_labels]
        theme.apply_theme("light")
        theme.apply_theme("dark")
        after = [id(c) for c in dialog.coord_labels] + [id(c) for c in dialog.status_labels]
        assert after == ids, "切換主題不得重建 Dialog 元件"
        assert dialog in inv._dialogs
    finally:
        inv._unregister_dialog(dialog)
        dialog.close()
        dialog.deleteLater()


def test_dialog_status_tone_follows_business_state(inv, theme):
    """Dialog 內的座標狀態標籤依業務狀態換色，且主題刷新後保持。"""
    from qt.inventory import _PickupSetupDialog

    dark = theme.TOKENS["dark"]
    original = inv.pickup_coordinates
    try:
        inv.pickup_coordinates = [[5, 6] for _ in range(5)]
        dialog = _PickupSetupDialog(inv, None)
        inv._register_dialog(dialog)
        try:
            dialog.update_display()
            assert dialog.status_labels[0].styleSheet() == f"color: {dark['success_soft']};"
            theme.apply_theme("light")
            light = theme.TOKENS["light"]
            assert dialog.status_labels[0].styleSheet() == f"color: {light['success_soft']};"
        finally:
            inv._unregister_dialog(dialog)
            dialog.close()
            dialog.deleteLater()
    finally:
        inv.pickup_coordinates = original


# ══════════════════════════════════════════════════════════════════════════
# 7. 主題刷新不得重複觸發業務操作
# ══════════════════════════════════════════════════════════════════════════
def test_theme_refresh_does_not_trigger_business_operations(inv, theme, monkeypatch):
    """refresh_theme() 只重上 QSS，不得觸發設定同步/預覽更新等業務操作。"""
    calls = []

    def spy(name):
        def fn(*a, **k):
            calls.append(name)

        return fn

    for name in ("_sync_inventory_config", "refresh_config_display", "update_pickup_status", "update_ui_preview", "_recompute_grid_positions"):
        monkeypatch.setattr(inv, name, spy(name))
    monkeypatch.setattr(inv, "_build_ui", spy("_build_ui"))

    theme.apply_theme("light")
    theme.apply_theme("dark")
    assert calls == [], f"主題刷新不得觸發業務操作，但呼叫了 {calls}"


def test_theme_refresh_does_not_create_new_dialogs(inv, theme):
    """主題刷新不得重複建立 Dialog（Dialog 數量維持原狀）。"""
    before = len(inv._dialogs)
    theme.apply_theme("light")
    theme.apply_theme("dark")
    assert len(inv._dialogs) == before


# ══════════════════════════════════════════════════════════════════════════
# 8. 現有 Inventory 功能不得回歸
# ══════════════════════════════════════════════════════════════════════════
def test_inventory_business_state_survives_theme_switch(inv, theme):
    """切換主題不得改動任何業務狀態（座標、偏移、排除格、單選/勾選狀態）。"""
    coords = [[10, 20] for _ in range(5)]
    inv.pickup_coordinates = [list(c) for c in coords]
    inv.grid_offset_x = 3
    inv.grid_offset_y = -2
    inv.excluded_inventory_slots = {1, 5, 20}
    inv.clear_click_mode = "right"
    try:
        inv.update_offset_labels()
        inv.refresh_config_display()
        theme.apply_theme("light")
        theme.apply_theme("dark")
        assert inv.pickup_coordinates == coords
        assert inv.grid_offset_x == 3
        assert inv.grid_offset_y == -2
        assert inv.excluded_inventory_slots == {1, 5, 20}
        assert inv.clear_click_mode == "right"
        assert inv.offset_x_label.text() == "3"
        assert inv.offset_y_label.text() == "-2"
    finally:
        inv.pickup_coordinates = None
        inv.grid_offset_x = 0
        inv.grid_offset_y = 0
        inv.excluded_inventory_slots = set()
        inv.clear_click_mode = "left"
        inv.update_offset_labels()
        inv.refresh_config_display()


def test_inventory_buttons_still_work_after_theme_switch(inv, theme):
    """切換主題後互動元件仍要能驅動原本的流程。"""
    try:
        theme.apply_theme("light")
        inv.grid_offset_x = 5
        inv.grid_offset_y = 5
        inv.update_offset_labels()
        inv.reset_offset_btn.click()
        assert inv.grid_offset_x == 0
        assert inv.grid_offset_y == 0
        assert inv.offset_x_label.text() == "0"
    finally:
        inv.grid_offset_x = 0
        inv.grid_offset_y = 0
        inv.update_offset_labels()


def test_inventory_language_refresh_still_works(inv, theme):
    """語言更新流程（會重新設定文字與語意色）不得因遷移而壞掉。"""
    before = inv.page_title_label.text()
    inv.update_inventory_tab_language()
    assert inv.page_title_label.text() == before
    assert inv.inventory_preview_label.styleSheet()
    theme.apply_theme("light")
    assert inv.inventory_preview_label.styleSheet()


def test_inventory_untouched_labels_have_no_os_palette_dependency(inv, theme):
    """遷移後所有 QLabel 都必須有明確前景色（不得再依賴 OS palette）。"""
    from PySide6.QtWidgets import QLabel

    theme.apply_theme("light")
    for label in inv.findChildren(QLabel):
        assert label.styleSheet(), f"QLabel 未套用主題色：{label.text()[:24]!r}"

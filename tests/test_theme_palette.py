"""Phase 3B：全域 Qt Palette 與原生控件主題統一測試。

測試建立真實 Qt 控件（QApplication / QMessageBox / QCheckBox / QScrollBar / QLineEdit），
檢查 Palette role 值、全域 QSS 內容與**實際渲染結果**，不是只比對原始碼字串。

注意：apply_theme() 對「目前主題」是 no-op，測試需要重新套用時必須先重置 _applied_theme。
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLineEdit,
    QMessageBox,
    QRadioButton,
    QScrollBar,
)

import qt.theme as theme

# ── 必檢查的 Palette role（Phase 3B 要求清單）────────────────────────────
CORE_ROLES = [
    QPalette.ColorRole.Window,
    QPalette.ColorRole.WindowText,
    QPalette.ColorRole.Base,
    QPalette.ColorRole.AlternateBase,
    QPalette.ColorRole.Text,
    QPalette.ColorRole.PlaceholderText,
    QPalette.ColorRole.Button,
    QPalette.ColorRole.ButtonText,
    QPalette.ColorRole.BrightText,
    QPalette.ColorRole.Highlight,
    QPalette.ColorRole.HighlightedText,
    QPalette.ColorRole.ToolTipBase,
    QPalette.ColorRole.ToolTipText,
    QPalette.ColorRole.Light,
    QPalette.ColorRole.Midlight,
    QPalette.ColorRole.Dark,
    QPalette.ColorRole.Mid,
    QPalette.ColorRole.Shadow,
    QPalette.ColorRole.Link,
    QPalette.ColorRole.LinkVisited,
]


@pytest.fixture(autouse=True)
def _restore_dark_theme():
    """每個測試結束後把主題還原為 dark（避免污染同 session 的其他測試）。"""
    yield
    theme._applied_theme = None
    theme.apply_theme("dark")


@pytest.fixture
def host(qapp):
    """容器視窗：把受測控件放在容器內（有偏移），避免 offscreen 游標停在 (0,0) 造成誤判為 hover。"""
    from PySide6.QtWidgets import QVBoxLayout, QWidget

    w = QWidget()
    w.setStyleSheet("background-color: #202020;")
    lay = QVBoxLayout(w)
    w.resize(420, 320)
    w.show()
    qapp.processEvents()
    yield w, lay
    w.close()


@pytest.fixture
def apply_force():
    """強制重新套用主題（繞過 apply_theme 對同一主題的 no-op）。"""

    def _apply(name):
        theme._applied_theme = None
        return theme.apply_theme(name)

    return _apply


def _pixel_colors(widget):
    """回傳 widget 渲染後的像素顏色統計 [(hex, count), ...]。"""
    img = widget.grab()
    img = img if hasattr(img, "pixelColor") else img.toImage()
    counts: dict[str, int] = {}
    for y in range(img.height()):
        for x in range(img.width()):
            name = img.pixelColor(x, y).name()
            counts[name] = counts.get(name, 0) + 1
    return sorted(counts.items(), key=lambda kv: -kv[1])


def _count_color(widget, hex_color):
    return sum(cnt for name, cnt in _pixel_colors(widget) if name.lower() == hex_color.lower())


def _indicator_pixels(widget, size=20):
    """indicator 區域（前 size x size 像素）的顏色序列（用來比對自繪元件是否被外部樣式改動）。"""
    img = widget.grab()
    img = img if hasattr(img, "pixelColor") else img.toImage()
    return [img.pixelColor(x, y).name() for y in range(min(size, img.height())) for x in range(min(size, img.width()))]


def _dominant_color(widget):
    colors = _pixel_colors(widget)
    return colors[0][0] if colors else ""


def _pixel_colors_of_region(img, size: int) -> dict[str, int]:
    """回傳圖片左上角 size x size 區域的顏色統計 {hex: count}。"""
    counts: dict[str, int] = {}
    for y in range(min(size, img.height())):
        for x in range(min(size, img.width())):
            name = img.pixelColor(x, y).name().lower()
            counts[name] = counts.get(name, 0) + 1
    return counts


# ── 1/2. Dark / Light Palette role 值 ─────────────────────────────────────
@pytest.mark.parametrize("theme_name", ["dark", "light"])
def test_palette_core_roles_follow_tokens(theme_name):
    """每個核心 role 都必須等於對應 token，不得殘留 OS 預設值。"""
    tok = theme.TOKENS[theme_name]
    pal = theme.build_palette(theme_name)
    expected = {
        QPalette.ColorRole.Window: tok["window_bg"],
        QPalette.ColorRole.WindowText: tok["fg"],
        QPalette.ColorRole.Base: tok["surface"],
        QPalette.ColorRole.AlternateBase: tok["window_bg"],
        QPalette.ColorRole.Text: tok["fg"],
        QPalette.ColorRole.PlaceholderText: tok["fg_muted"],
        QPalette.ColorRole.BrightText: tok["fg"],
        QPalette.ColorRole.Button: tok["surface"],
        QPalette.ColorRole.ButtonText: tok["fg"],
        QPalette.ColorRole.Highlight: tok["accent"],
        QPalette.ColorRole.HighlightedText: tok["window_bg"],
        QPalette.ColorRole.ToolTipBase: tok["surface"],
        QPalette.ColorRole.ToolTipText: tok["fg"],
        QPalette.ColorRole.Link: tok["accent"],
        QPalette.ColorRole.LinkVisited: tok["fg_muted"],
    }
    for role, want in expected.items():
        assert pal.color(role).name() == want, f"{theme_name} {role} 應為 {want}"
    # 3D 角色必須有值（不得留空或 OS 預設）
    for role in (
        QPalette.ColorRole.Light,
        QPalette.ColorRole.Midlight,
        QPalette.ColorRole.Dark,
        QPalette.ColorRole.Mid,
        QPalette.ColorRole.Shadow,
    ):
        assert pal.color(role).isValid(), f"{theme_name} {role} 未設定"
        assert pal.color(role).name() != "#000000" or theme_name == "dark"


def test_palette_dark_and_light_differ():
    """Dark 與 Light 的 palette 必須不同（否則原生控件不會跟隨主題）。"""
    dark = theme.build_palette("dark")
    light = theme.build_palette("light")
    assert dark.color(QPalette.ColorRole.Window).name() != light.color(QPalette.ColorRole.Window).name()
    assert dark.color(QPalette.ColorRole.Base).name() != light.color(QPalette.ColorRole.Base).name()
    assert dark.color(QPalette.ColorRole.Highlight).name() != light.color(QPalette.ColorRole.Highlight).name()


# ── 3. Disabled 群組 ──────────────────────────────────────────────────────
def test_palette_disabled_group_has_readable_colors():
    """Disabled 字色必須仍可辨識（不可變成看不見），且底色沿用正常群組。"""
    for theme_name in ("dark", "light"):
        tok = theme.TOKENS[theme_name]
        pal = theme.build_palette(theme_name)
        disabled_text = pal.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text).name()
        assert disabled_text == tok["fg_muted"]
        assert pal.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText).name() == tok["fg_muted"]
        assert pal.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Window).name() == tok["window_bg"]
        assert pal.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base).name() == tok["surface"]
        # 不可與正常字色相同（否則 disabled 與 enabled 無區別）
        assert disabled_text != pal.color(QPalette.ColorRole.Text).name()


# ── 4. Link / LinkVisited 不得殘留 OS 紫色 ────────────────────────────────
def _os_link_colors(qapp) -> set[str]:
    """平台預設的 link 色集合。

    注意：**不可**用 QPalette()（預設建構子）當 OS 基準 —— 它取的是「目前 app palette」，
    而本測試檔會先套用全域 palette，基準會被自己覆蓋而誤判（實測 Link 會等於 accent）。
    改用 style 的 standardPalette（不受 setPalette / setStyleSheet 影響）+ 已知 OS 深色紫色值。
    """
    colors = {"#f0c0f4"}  # Windows 深色主題的 OS 紫色 link（實測值）
    sp = qapp.style().standardPalette()
    colors.add(sp.color(QPalette.ColorRole.Link).name().lower())
    colors.add(sp.color(QPalette.ColorRole.LinkVisited).name().lower())
    return colors


def test_palette_link_is_not_os_default_purple(qapp):
    """OS 深色 palette 的 Link 是紫色 #f0c0f4；全域 palette 必須覆蓋掉。"""
    os_links = _os_link_colors(qapp)
    for theme_name in ("dark", "light"):
        tok = theme.TOKENS[theme_name]
        pal = theme.build_palette(theme_name)
        assert pal.color(QPalette.ColorRole.Link).name() == tok["accent"]
        assert pal.color(QPalette.ColorRole.LinkVisited).name() == tok["fg_muted"]
        assert pal.color(QPalette.ColorRole.Link).name().lower() not in os_links
        assert pal.color(QPalette.ColorRole.LinkVisited).name().lower() not in os_links


# ── 5. QCheckBox / QRadioButton indicator ─────────────────────────────────
@pytest.mark.parametrize("theme_name", ["dark", "light"])
def test_global_qss_defines_indicator_states(theme_name):
    """全域 QSS 必須定義 indicator 的正常 / hover / checked / disabled 狀態。"""
    qss = theme.build_global_qss(theme_name)
    tok = theme.TOKENS[theme_name]
    assert "QCheckBox::indicator {" in qss
    assert "QCheckBox::indicator:hover" in qss
    assert "QCheckBox::indicator:checked" in qss
    assert "QCheckBox::indicator:disabled" in qss
    assert "QRadioButton::indicator {" in qss
    assert "QRadioButton::indicator:checked" in qss
    assert tok["surface"] in qss
    assert tok["accent"] in qss
    assert tok["border_strong"] in qss


def test_native_checkbox_indicator_renders_theme_colors(qapp, host, apply_force):
    """實測：原生 QCheckBox 的 indicator 必須渲染成 token 色（不再是 OS 深灰）。"""
    tok = theme.TOKENS["dark"]
    apply_force("dark")
    widget, lay = host
    cb = QCheckBox("原生")
    lay.addWidget(cb)
    qapp.processEvents()
    try:
        cb.setChecked(False)
        qapp.processEvents()
        assert _count_color(cb, tok["surface"]) > 0, "未勾選 indicator 底色應為 surface token"
        assert _count_color(cb, tok["border_strong"]) > 0, "未勾選 indicator 邊框應為 border_strong token"
        cb.setChecked(True)
        qapp.processEvents()
        assert _count_color(cb, tok["accent"]) > 0, "已勾選 indicator 應填 accent token"
    finally:
        cb.deleteLater()


def test_global_qss_does_not_use_broad_lineedit_selectors():
    """QLineEdit / QSpinBox / QComboBox 不可出現在全域 QSS（會誤傷 qfluentwidgets 自繪元件）。"""
    qss = theme.build_global_qss("dark")
    for selector in ("QLineEdit", "QSpinBox", "QComboBox", "QAbstractItemView"):
        assert selector not in qss, f"全域 QSS 不得包含 {selector} 選擇器"


# ── 6/7. QScrollBar ───────────────────────────────────────────────────────
@pytest.mark.parametrize("theme_name", ["dark", "light"])
def test_global_qss_scrollbar_both_orientations_and_states(theme_name):
    """水平/垂直捲軸的 groove、handle、hover、disabled 都要有規則。"""
    qss = theme.build_global_qss(theme_name)
    assert "QScrollBar::groove:vertical" in qss
    assert "QScrollBar::groove:horizontal" in qss
    assert "QScrollBar::handle:vertical" in qss
    assert "QScrollBar::handle:horizontal" in qss
    assert "QScrollBar::handle:hover" in qss
    assert "QScrollBar::handle:disabled" in qss
    assert "min-height: 24px" in qss and "min-width: 24px" in qss, "handle 必須保留可操作的最小尺寸"


def test_native_scrollbar_handle_uses_token_and_keeps_width(qapp, host, apply_force):
    """實測：捲軸 handle 用 token 色，且寬度不得被 QSS 縮細。"""
    tok = theme.TOKENS["dark"]
    apply_force("dark")
    widget, lay = host
    bar = QScrollBar(Qt.Orientation.Vertical)
    bar.setRange(0, 100)
    bar.setPageStep(10)
    bar.setFixedWidth(12)
    lay.addWidget(bar)
    qapp.processEvents()
    try:
        assert bar.width() >= 10, f"捲軸寬度不可被縮細：{bar.width()}"
        assert _count_color(bar, tok["fg_muted"]) > 0, "捲軸 handle 應使用 fg_muted token"
    finally:
        bar.deleteLater()


def test_scrollbar_disabled_state_differs(qapp, host, apply_force):
    """disabled 捲軸的 handle 不得與 enabled 相同（必須看得出停用）。"""
    tok = theme.TOKENS["dark"]
    apply_force("dark")
    widget, lay = host
    bar = QScrollBar(Qt.Orientation.Vertical)
    bar.setRange(0, 100)
    bar.setFixedWidth(12)
    lay.addWidget(bar)
    qapp.processEvents()
    try:
        bar.setEnabled(True)
        qapp.processEvents()
        enabled_colors = {name for name, _ in _pixel_colors(bar)}
        bar.setEnabled(False)
        qapp.processEvents()
        disabled_colors = {name for name, _ in _pixel_colors(bar)}
        assert enabled_colors != disabled_colors, "停用捲軸外觀必須與啟用不同"
        assert tok["border"] in disabled_colors, "停用 handle 應使用 border token"
    finally:
        bar.deleteLater()


# ── 8. Selection ──────────────────────────────────────────────────────────
@pytest.mark.parametrize("theme_name", ["dark", "light"])
def test_selection_palette_roles(theme_name):
    """選取背景用 accent、選取文字用 window_bg（高對比）。"""
    tok = theme.TOKENS[theme_name]
    pal = theme.build_palette(theme_name)
    assert pal.color(QPalette.ColorRole.Highlight).name() == tok["accent"]
    assert pal.color(QPalette.ColorRole.HighlightedText).name() == tok["window_bg"]


def test_lineedit_selection_uses_palette_highlight(qapp, apply_force):
    """實測：QLineEdit 選取文字的背景必須跟著 palette Highlight（accent）。"""
    tok = theme.TOKENS["light"]
    apply_force("light")
    edit = QLineEdit("selection test")
    edit.show()
    qapp.processEvents()
    try:
        edit.selectAll()
        qapp.processEvents()
        assert _count_color(edit, tok["accent"]) > 0, "選取背景應為 accent token"
    finally:
        edit.close()


# ── 9. 原生 QMessageBox ───────────────────────────────────────────────────
@pytest.mark.parametrize("theme_name", ["dark", "light"])
def test_native_messagebox_follows_theme(qapp, apply_force, theme_name):
    """實測：原生 QMessageBox 的底色必須跟著主題（light 不得再是深色）。"""
    tok = theme.TOKENS[theme_name]
    apply_force(theme_name)
    mb = QMessageBox(QMessageBox.Icon.Information, "標題", "訊息", QMessageBox.StandardButton.Ok)
    mb.show()
    qapp.processEvents()
    try:
        assert _dominant_color(mb) == tok["window_bg"], "QMessageBox 底色應為 window_bg token"
    finally:
        mb.close()


def test_messagebox_opened_before_switch_follows_new_theme(qapp, apply_force):
    """已開啟的原生 QMessageBox 在主題切換後也要跟著翻新（PaletteChange 事件）。"""
    apply_force("dark")
    mb = QMessageBox(QMessageBox.Icon.Information, "標題", "訊息", QMessageBox.StandardButton.Ok)
    mb.show()
    qapp.processEvents()
    try:
        apply_force("light")
        qapp.processEvents()
        assert _dominant_color(mb) == theme.TOKENS["light"]["window_bg"]
    finally:
        mb.close()


# ── 10. Dark → Light → Dark 循環 ─────────────────────────────────────────
def test_theme_cycle_leaves_no_residue(qapp, apply_force):
    """循環切換後 palette 與全域 QSS 必須回到與第一次完全相同的值。"""
    apply_force("dark")
    dark_pal = theme.build_palette("dark")
    dark_qss = theme.build_global_qss("dark")
    apply_force("light")
    apply_force("dark")
    for role in CORE_ROLES:
        assert qapp.palette().color(role).name() == dark_pal.color(role).name(), f"{role} 循環後殘留"
    assert qapp.styleSheet() == dark_qss, "全域 QSS 循環後殘留"


def test_palette_never_carries_business_semantic_colors():
    """Palette 不得承載業務語意色（success/warning/error/info 等）。"""
    for theme_name in ("dark", "light"):
        tok = theme.TOKENS[theme_name]
        pal = theme.build_palette(theme_name)
        semantic = {tok[k] for k in ("success", "warning", "error", "info") if k in tok}
        semantic |= {tok[k] for k in ("success_soft", "warning_soft", "error_soft", "info_soft") if k in tok}
        semantic |= {tok["monitor"]}
        used = {pal.color(role).name() for role in CORE_ROLES}
        assert not (used & semantic), f"{theme_name} palette 混入了業務語意色"


# ── 11/12. fan-out 次數與刷新時序 ─────────────────────────────────────────
def test_theme_switch_triggers_exactly_one_fanout(theme_window, apply_force):
    """一次 apply_theme 只能觸發一次頁面 fan-out。"""
    from qfluentwidgets import qconfig

    calls = []
    original = theme_window._fan_out_tab_themes

    def spy():
        calls.append(1)
        return original()

    theme_window._fan_out_tab_themes = spy
    try:
        apply_force("light")
        assert len(calls) == 1, f"fan-out 應為 1 次，實得 {len(calls)}"
        apply_force("dark")
        assert len(calls) == 2, f"第二次切換 fan-out 應為 2 次，實得 {len(calls)}"
    finally:
        theme_window._fan_out_tab_themes = original


def test_page_refresh_happens_after_palette_and_qss_updated(qapp, theme_window, apply_force):
    """頁面刷新發生的當下，palette 與全域 QSS 必須已是新主題。"""
    from qfluentwidgets import qconfig

    observed = []

    def spy():
        observed.append(
            (
                qapp.palette().color(QPalette.ColorRole.Window).name(),
                qapp.palette().color(QPalette.ColorRole.Highlight).name(),
                qapp.styleSheet(),
            )
        )

    qconfig.themeChangedFinished.connect(spy)
    try:
        apply_force("light")
        assert observed, "themeChangedFinished 未觸發"
        window_color, highlight, qss = observed[0]
        assert window_color == theme.TOKENS["light"]["window_bg"]
        assert highlight == theme.TOKENS["light"]["accent"]
        assert qss == theme.build_global_qss("light")
    finally:
        qconfig.themeChangedFinished.disconnect(spy)


def test_apply_theme_is_idempotent_for_palette(qapp, apply_force):
    """重複套用同一主題不得再改動 palette 與全域 QSS（不得累積）。"""
    apply_force("dark")
    first_palette = qapp.palette().color(QPalette.ColorRole.Window).name()
    first_qss = qapp.styleSheet()
    apply_force("dark")
    assert qapp.palette().color(QPalette.ColorRole.Window).name() == first_palette
    assert qapp.styleSheet() == first_qss


# ── 13. 已開啟 Dialog ─────────────────────────────────────────────────────
def test_open_dialog_follows_theme_switch(qapp, apply_force):
    """已開啟的原生 Dialog 在主題切換後必須跟著翻新。"""
    apply_force("dark")
    dlg = QDialog()
    dlg.resize(200, 120)
    dlg.show()
    qapp.processEvents()
    try:
        assert dlg.palette().color(QPalette.ColorRole.Window).name() == theme.TOKENS["dark"]["window_bg"]
        apply_force("light")
        qapp.processEvents()
        assert dlg.palette().color(QPalette.ColorRole.Window).name() == theme.TOKENS["light"]["window_bg"]
        assert dlg.isVisible(), "主題切換不得關閉既有 Dialog"
    finally:
        dlg.close()


def test_themed_dialog_still_refreshes(theme_window, apply_force):
    """既有 ThemedDialog（Phase 2D/2E）在主題切換後可正常重新上色。"""
    from qt.monitor_dialogs import _ThemedDialog

    dlg = _ThemedDialog(theme_window)
    dlg.show()
    qapp = QApplication.instance()
    qapp.processEvents()
    try:
        assert theme.TOKENS["dark"]["window_bg"] in dlg.styleSheet()
        apply_force("light")
        dlg.refresh_theme()  # 已登記的 Dialog 由頁面 fan-out 呼叫
        qapp.processEvents()
        assert dlg.isVisible()
        # ThemedDialog 自帶 QSS 底色，palette 的 Window role 會被 QSS 覆蓋 → 以 QSS 內容驗證
        assert theme.TOKENS["light"]["window_bg"] in dlg.styleSheet()
        assert theme.TOKENS["dark"]["window_bg"] not in dlg.styleSheet()
    finally:
        dlg.close()


# ── 14. qfluentwidgets 自繪元件不受全域 QSS 影響 ──────────────────────────
def test_fluent_self_drawn_widgets_unaffected_by_global_qss(qapp):
    """qfluentwidgets 的 CheckBox / RadioButton 自繪 indicator，不得被全域 QSS 覆蓋。"""
    from qfluentwidgets import CheckBox as FluentCheckBox
    from qfluentwidgets import RadioButton as FluentRadioButton

    widgets = [FluentCheckBox("fluent"), FluentRadioButton("fluent radio")]
    for wid in widgets:
        wid.show()
    qapp.processEvents()
    try:
        saved = qapp.styleSheet()
        qapp.setStyleSheet("")
        qapp.processEvents()
        before = [wid.grab().toImage() if hasattr(wid.grab(), "toImage") else wid.grab() for wid in widgets]
        qapp.setStyleSheet(theme.build_global_qss("dark"))
        qapp.processEvents()
        for wid, img_before in zip(widgets, before):
            img_after = wid.grab()
            img_after = img_after if hasattr(img_after, "pixelColor") else img_after.toImage()
            assert img_after == img_before, f"{type(wid).__name__} 的渲染被全域 QSS 改變了"
        qapp.setStyleSheet(saved)
    finally:
        for wid in widgets:
            wid.close()


def test_fluent_widget_palette_untouched(qapp, host, apply_force):
    """只換 app palette（不換 qfluentwidgets 主題）不得改變自繪元件的 indicator 渲染。"""
    from qfluentwidgets import CheckBox as FluentCheckBox

    apply_force("dark")
    widget, lay = host
    cb = FluentCheckBox("fluent")
    lay.addWidget(cb)
    qapp.processEvents()
    try:
        before = _indicator_pixels(cb)
        qapp.setPalette(theme.build_palette("light"))
        qapp.processEvents()
        assert _indicator_pixels(cb) == before, "qfluentwidgets CheckBox 的 indicator 不應被全域 palette 改變"
    finally:
        cb.deleteLater()


# ── 15. 原生勾選呈現：accent 實心方塊（不使用 QSS 圖片）─────────────────
def test_global_qss_uses_no_subcontrol_image():
    """全域 QSS 不得使用 image: url()。

    實測：Qt 的 QSS subcontrol 背景圖在此環境渲染不確定（同一份 QSS 跨行程時而
    有勾號時而沒有，且與其他 border 規則併用會整個消失）→ 勾選態採 accent 實心方塊。
    """
    for theme_name in ("dark", "light"):
        qss = theme.build_global_qss(theme_name)
        assert "image: url(" not in qss, f"{theme_name} 全域 QSS 不應使用 QSS 圖片"


def test_native_checkbox_checked_is_solid_accent_square(qapp, host, apply_force):
    """實測：勾選態的 indicator 必須是 accent 實心方塊（呈現需可重現）。"""
    tok = theme.TOKENS["dark"]
    apply_force("dark")
    widget, lay = host
    cb = QCheckBox("原生")
    lay.addWidget(cb)
    qapp.processEvents()
    try:
        cb.setChecked(True)
        qapp.processEvents()
        img = cb.grab()
        img = img if hasattr(img, "pixelColor") else img.toImage()
        region = _pixel_colors_of_region(img, 18)
        assert region.get(tok["accent"], 0) > 100, "勾選方塊底色應為 accent token"
    finally:
        cb.deleteLater()


# ── 16. 原生對話框按鈕（Palette 管不到，Windows 主題引擎自繪）────────────
def test_global_qss_defines_native_dialog_button_rule():
    """全域 QSS 必須補原生對話框按鈕規則，且選擇器限定 QDialogButtonBox。"""
    qss = theme.build_global_qss("light")
    assert "QDialogButtonBox QPushButton {" in qss
    assert "QDialogButtonBox QPushButton:disabled {" in qss
    assert theme.TOKENS["light"]["fg"] in qss


def test_native_dialog_button_text_is_readable_in_light(qapp, apply_force):
    """實測：light 主題下原生對話框按鈕文字不得是白字（淺底不可讀）。"""
    tok = theme.TOKENS["light"]
    apply_force("light")
    dlg = QDialog()
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    from PySide6.QtWidgets import QVBoxLayout

    lay = QVBoxLayout(dlg)
    lay.addWidget(box)
    dlg.resize(240, 140)
    dlg.show()
    qapp.processEvents()
    try:
        btn = box.button(QDialogButtonBox.StandardButton.Ok)
        assert btn is not None
        img = btn.grab()
        img = img if hasattr(img, "pixelColor") else img.toImage()
        names = [img.pixelColor(x, y).name().lower() for y in range(img.height()) for x in range(img.width())]
        assert tok["fg"] in names, "按鈕文字應使用 fg token（不可為白字）"
        assert tok["surface"] in names, "按鈕底色應使用 surface token"
    finally:
        dlg.close()


def test_fluent_push_button_unaffected_by_dialog_button_rule(qapp):
    """頁面內的 qfluentwidgets 按鈕不得被 QDialogButtonBox 規則改變。"""
    from qfluentwidgets import PushButton as FluentPushButton

    btn = FluentPushButton("fluent")
    btn.show()
    qapp.processEvents()
    try:
        saved = qapp.styleSheet()
        qapp.setStyleSheet("")
        qapp.processEvents()
        img_before = btn.grab()
        img_before = img_before if hasattr(img_before, "pixelColor") else img_before.toImage()
        qapp.setStyleSheet(theme.build_global_qss("light"))
        qapp.processEvents()
        img_after = btn.grab()
        img_after = img_after if hasattr(img_after, "pixelColor") else img_after.toImage()
        assert img_after == img_before, "qfluentwidgets PushButton 的渲染被全域 QSS 改變了"
        qapp.setStyleSheet(saved)
    finally:
        btn.close()

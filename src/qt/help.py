"""
help.py（Qt 版）— 使用說明分頁
────────────────────────────────────────────────────────
對應 tk 版 `tab_help.py`（Phase 7）。
- QScrollArea 承載卡片式內容；語言切換時整頁重建（與 tk 行為一致）。
- Phase 2B：卡片/文字/Badge 顏色一律取自 qt.theme token（語言重建時重上）。
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget
from qfluentwidgets import PushButton

from _version import __version__
from qt.theme import current_tokens

CURRENT_VERSION = f"v{__version__}"


class HelpTab(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app
        # (widget, 樣式規格)：只記 token 名稱，不記顏色；refresh_theme() 時才解析成目前主題
        self._styled: list[tuple[QWidget, tuple]] = []
        self._build_ui()

    # ────────────────────────────────────────────────────
    #  主題樣式（顏色唯一來源：qt.theme）
    # ────────────────────────────────────────────────────

    @staticmethod
    def _style_qss(spec: tuple) -> str:
        """(種類, token, 字級, 字重, 透明底色) → QSS。沿用原版字級/字重，只換顏色來源。"""
        kind, token, px, weight, transparent = spec
        tok = current_tokens()
        if kind == "card":
            return f"QWidget {{ background-color: {tok['surface']}; border: 1px solid {tok['border']}; border-radius: 8px; }}QLabel {{ background: transparent; }}"
        if kind == "badge":
            return f"background-color: {tok[token]}; color: {tok['badge_fg']}; padding: 2px 8px; border-radius: 4px; font-family: Consolas; font-weight: 600; font-size: 12px;"
        parts = []
        if px is not None:
            parts.append(f"font-size: {px}px;")
        if weight:
            parts.append(f"font-weight: {weight};")
        parts.append(f"color: {tok[token]};")
        if transparent:
            parts.append("background: transparent;")
        return " ".join(parts)

    def _apply_style(self, widget: QWidget, spec: tuple) -> None:
        """套用樣式並登記，供 refresh_theme() 重上。"""
        self._styled.append((widget, spec))
        widget.setStyleSheet(self._style_qss(spec))

    def refresh_theme(self) -> None:
        """主題切換刷新：只重上既有元件 QSS，不重建、不改版面/字級/內容。"""
        alive: list[tuple[QWidget, tuple]] = []
        for widget, spec in self._styled:
            try:
                widget.setStyleSheet(self._style_qss(spec))
            except RuntimeError:
                continue  # 已被語言切換重建刪除的舊元件
            alive.append((widget, spec))
        self._styled = alive

    # ────────────────────────────────────────────────────
    #  UI 建構
    # ────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        # 原生 QScrollArea/viewport 底色來自 OS palette；改透明，讓頁面跟著 FluentWindow 主題底色。
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._scroll.viewport().setAutoFillBackground(False)
        layout.addWidget(self._scroll)
        self._rebuild_content()

    def _rebuild_content(self):
        old = self._scroll.takeWidget()
        if old is not None:
            old.deleteLater()
        self._styled.clear()  # 舊元件已排入刪除，樣式登記一併清空

        content = QWidget()
        self._scroll.setWidget(content)
        content.setAutoFillBackground(False)
        root = QVBoxLayout(content)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)
        g = self._app.get_text

        # ── 標題區 ──
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)
        title_label = QLabel(g("poe_sid_tools_title"))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._apply_style(title_label, ("label", "fg", 26, 700, False))
        header_layout.addWidget(title_label)
        subtitle_label = QLabel(g("opensource_subtitle"))
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._apply_style(subtitle_label, ("label", "fg_muted", 13, None, False))
        header_layout.addWidget(subtitle_label)

        video_btn = PushButton(g("watch_demo_video"))
        video_btn.clicked.connect(lambda: self._app.open_video_link("https://dai.ly/xa9cau2"))
        video_btn.setFixedWidth(180)
        header_layout.addWidget(video_btn, 0, Qt.AlignmentFlag.AlignCenter)
        video_note = QLabel(g("video_recommendation"))
        video_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._apply_style(video_note, ("label", "error", 11, None, False))
        header_layout.addWidget(video_note)
        root.addWidget(header)

        # ── 三欄卡片列 ──
        row_grid = QGridLayout()
        row_grid.setSpacing(12)

        def _hk(k, d):
            try:
                if hasattr(self._app, "get_hotkey"):
                    return self._app.get_hotkey(k, d).upper()
            except Exception:
                pass
            return d.upper()

        def _short(hk):
            try:
                if hasattr(self._app, "hotkey_short"):
                    return self._app.hotkey_short(hk.lower())
            except Exception:
                pass
            return hk

        hotkey_card = self._info_card(
            g("global_hotkeys_title"),
            [
                (_short(_hk("f3", "f3")), g("hotkey_f3_desc"), "error"),
                (_short(_hk("f5", "f5")), g("hotkey_f5_desc"), "info"),
                (_short(_hk("f6", "f6")), g("hotkey_f6_desc"), "success"),
                (_short(_hk("skill_timer", "ins")), g("hotkey_skill_timer_desc"), "accent"),
                (_short(_hk("f9", "f9")), g("hotkey_f9_desc"), "warning"),
                (_short(_hk("f10", "f10")), g("hotkey_f10_desc"), "accent"),
                ("F12", g("hotkey_f12_desc"), "fg_muted"),
                ("CTRL+Click", g("hotkey_ctrl_click_desc"), "info"),
            ],
        )
        row_grid.addWidget(hotkey_card, 0, 0)

        version_card, version_layout = self._group_card(g("version_info"))
        version_info = g("version_info_text").format(version=CURRENT_VERSION)
        version_label = QLabel(version_info)
        version_label.setWordWrap(True)
        self._apply_style(version_label, ("label", "fg", 13, None, False))
        version_layout.addWidget(version_label)
        version_layout.addStretch(1)
        row_grid.addWidget(version_card, 0, 1)

        quickstart_card, quickstart_layout = self._group_card(g("quick_start"))
        quickstart_label = QLabel(g("quickstart_text"))
        quickstart_label.setWordWrap(True)
        self._apply_style(quickstart_label, ("label", "fg", 13, None, False))
        quickstart_layout.addWidget(quickstart_label)
        quickstart_layout.addStretch(1)
        row_grid.addWidget(quickstart_card, 0, 2)
        row_grid.setColumnStretch(0, 1)
        row_grid.setColumnStretch(1, 1)
        row_grid.setColumnStretch(2, 1)
        root.addLayout(row_grid)

        # ── 功能特色 + 詳細設定 ──
        mid_grid = QGridLayout()
        mid_grid.setSpacing(12)

        features_card, features_layout = self._group_card(g("core_features"))
        feat_cols = QHBoxLayout()
        feat_cols.setSpacing(24)
        left_features = QVBoxLayout()
        left_features.setSpacing(4)
        self._feature_block(left_features, g("health_monitor_system"), g("health_monitor_desc"), "error")
        self._feature_block(left_features, g("smart_inventory_system"), g("smart_inventory_desc"), "info")
        right_features = QVBoxLayout()
        right_features.setSpacing(4)
        self._feature_block(right_features, g("skill_combo_system"), g("skill_combo_desc"), "success")
        self._feature_block(right_features, g("automation_tools"), g("automation_tools_desc"), "accent")
        feat_cols.addLayout(left_features)
        feat_cols.addLayout(right_features)
        features_layout.addLayout(feat_cols)
        mid_grid.addWidget(features_card, 0, 0, 1, 2)

        setup_card, setup_layout = self._group_card(g("detailed_setup_guide"))
        setup_label = QLabel(g("setup_guide_text"))
        setup_label.setWordWrap(True)
        self._apply_style(setup_label, ("label", "fg", 12, None, False))
        setup_layout.addWidget(setup_label)
        setup_layout.addStretch(1)
        mid_grid.addWidget(setup_card, 0, 2)
        mid_grid.setColumnStretch(0, 1)
        mid_grid.setColumnStretch(1, 1)
        mid_grid.setColumnStretch(2, 1)
        root.addLayout(mid_grid)

        # ── 重要事項 ──
        notes_card, notes_layout = self._group_card(g("important_notes"))
        notes_label = QLabel(g("notes_text"))
        notes_label.setWordWrap(True)
        self._apply_style(notes_label, ("label", "fg", 13, None, False))
        notes_layout.addWidget(notes_label)
        root.addWidget(notes_card)

        # ── 開源資訊 ──
        open_card, open_layout = self._group_card(g("opensource_info"))
        open_row = QHBoxLayout()
        open_row.setSpacing(24)

        left_info = QVBoxLayout()
        left_info.setSpacing(4)
        repo_title = QLabel(g("github_repo_label"))
        self._apply_style(repo_title, ("label", "fg", None, 600, False))
        left_info.addWidget(repo_title)
        repo_url = QLabel("https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor")
        self._apply_style(repo_url, ("label", "info", 12, None, False))
        mono = repo_url.font()
        mono.setFamily("Consolas")
        repo_url.setFont(mono)
        repo_url.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        left_info.addWidget(repo_url)
        github_btn = PushButton(g("visit_github_button"))
        github_btn.clicked.connect(lambda: self._app.open_video_link("https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor"))
        left_info.addWidget(github_btn)
        license_title = QLabel(g("license_label"))
        self._apply_style(license_title, ("label", "fg", None, 600, False))
        left_info.addWidget(license_title)
        license_text = QLabel(g("license_text"))
        license_text.setWordWrap(True)
        self._apply_style(license_text, ("label", "fg", 12, None, False))
        left_info.addWidget(license_text)
        open_row.addLayout(left_info, 1)

        right_info = QVBoxLayout()
        right_info.setSpacing(2)
        features_title = QLabel(g("features_list_label"))
        self._apply_style(features_title, ("label", "fg", None, 600, False))
        right_info.addWidget(features_title)
        for feature in [
            g("feature_f3"),
            g("feature_f5"),
            g("feature_f6"),
            g("feature_f9"),
            g("feature_f10"),
            g("feature_skill_combo"),
            g("feature_auto_click"),
        ]:
            item_label = QLabel(f"• {feature}")
            # 原本 unstyled → 走 OS palette，light 主題下白字白底；改套 fg token
            self._apply_style(item_label, ("label", "fg", None, None, False))
            right_info.addWidget(item_label)
        open_row.addLayout(right_info, 1)
        open_layout.addLayout(open_row)
        root.addWidget(open_card)

        root.addStretch(1)

    def _feature_block(self, layout, title, desc, token):
        title_label = QLabel(title)
        self._apply_style(title_label, ("label", token, 14, 700, False))
        layout.addWidget(title_label)
        desc_label = QLabel(desc)
        desc_label.setWordWrap(True)
        self._apply_style(desc_label, ("label", "fg", 12, None, False))
        layout.addWidget(desc_label)
        layout.addSpacing(8)

    def _group_card(self, title):
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        self._apply_style(box, ("card", None, None, None, None))
        title_label = QLabel(title)
        self._apply_style(title_label, ("label", "fg", 14, 600, True))
        layout.addWidget(title_label)
        return box, layout

    def _info_card(self, title, items):
        card, layout = self._group_card(title)
        for key, desc, token in items:
            row = QHBoxLayout()
            row.setSpacing(10)
            key_label = QLabel(f" {key} ")
            self._apply_style(key_label, ("badge", token, None, None, None))
            row.addWidget(key_label, 0, Qt.AlignmentFlag.AlignTop)
            desc_label = QLabel(desc)
            desc_label.setWordWrap(True)
            self._apply_style(desc_label, ("label", "fg", 12, None, True))
            row.addWidget(desc_label, 1)
            layout.addLayout(row)
        return card

    # ── 語言更新（整頁重建）──────────────────────────

    def update_language(self):
        self._rebuild_content()

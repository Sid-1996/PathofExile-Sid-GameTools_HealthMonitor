"""
help.py（Qt 版）— 使用說明分頁
────────────────────────────────────────────────────────
對應 tk 版 `tab_help.py`（Phase 7）。
- QScrollArea 承載卡片式內容；語言切換時整頁重建（與 tk 行為一致）。
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget
from qfluentwidgets import PushButton

from _version import __version__

CURRENT_VERSION = f"v{__version__}"

# 與舊 dracula 色系對齊
FG = "#f8f8f2"
MUTED = "#b8b8c8"
ERROR = "#ff5555"
INFO = "#8be9fd"
SUCCESS = "#50fa7b"
WARNING = "#f1fa8c"
HOTKEY = "#bd93f9"


class HelpTab(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app
        self._build_ui()

    # ────────────────────────────────────────────────────
    #  UI 建構
    # ────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(self._scroll)
        self._rebuild_content()

    def _rebuild_content(self):
        old = self._scroll.takeWidget()
        if old is not None:
            old.deleteLater()

        content = QWidget()
        self._scroll.setWidget(content)
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
        title_label.setStyleSheet(f"font-size: 26px; font-weight: 700; color: {FG};")
        header_layout.addWidget(title_label)
        subtitle_label = QLabel(g("opensource_subtitle"))
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet(f"font-size: 13px; color: {MUTED};")
        header_layout.addWidget(subtitle_label)

        video_btn = PushButton(g("watch_demo_video"))
        video_btn.clicked.connect(lambda: self._app.open_video_link("https://dai.ly/xa9cau2"))
        video_btn.setFixedWidth(180)
        header_layout.addWidget(video_btn, 0, Qt.AlignmentFlag.AlignCenter)
        video_note = QLabel(g("video_recommendation"))
        video_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        video_note.setStyleSheet(f"font-size: 11px; color: {ERROR};")
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
                (_short(_hk("f3", "f3")), g("hotkey_f3_desc"), ERROR),
                (_short(_hk("f5", "f5")), g("hotkey_f5_desc"), INFO),
                (_short(_hk("f6", "f6")), g("hotkey_f6_desc"), SUCCESS),
                (_short(_hk("skill_timer", "ins")), g("hotkey_skill_timer_desc"), HOTKEY),
                (_short(_hk("f9", "f9")), g("hotkey_f9_desc"), WARNING),
                (_short(_hk("f10", "f10")), g("hotkey_f10_desc"), HOTKEY),
                ("F12", g("hotkey_f12_desc"), MUTED),
                ("CTRL+Click", g("hotkey_ctrl_click_desc"), INFO),
            ],
        )
        row_grid.addWidget(hotkey_card, 0, 0)

        version_card, version_layout = self._group_card(g("version_info"))
        version_info = g("version_info_text").format(version=CURRENT_VERSION)
        version_label = QLabel(version_info)
        version_label.setWordWrap(True)
        version_label.setStyleSheet(f"font-size: 13px; color: {FG};")
        version_layout.addWidget(version_label)
        version_layout.addStretch(1)
        row_grid.addWidget(version_card, 0, 1)

        quickstart_card, quickstart_layout = self._group_card(g("quick_start"))
        quickstart_label = QLabel(g("quickstart_text"))
        quickstart_label.setWordWrap(True)
        quickstart_label.setStyleSheet(f"font-size: 13px; color: {FG};")
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
        self._feature_block(left_features, g("health_monitor_system"), g("health_monitor_desc"), ERROR)
        self._feature_block(left_features, g("smart_inventory_system"), g("smart_inventory_desc"), INFO)
        right_features = QVBoxLayout()
        right_features.setSpacing(4)
        self._feature_block(right_features, g("skill_combo_system"), g("skill_combo_desc"), SUCCESS)
        self._feature_block(right_features, g("automation_tools"), g("automation_tools_desc"), HOTKEY)
        feat_cols.addLayout(left_features)
        feat_cols.addLayout(right_features)
        features_layout.addLayout(feat_cols)
        mid_grid.addWidget(features_card, 0, 0, 1, 2)

        setup_card, setup_layout = self._group_card(g("detailed_setup_guide"))
        setup_label = QLabel(g("setup_guide_text"))
        setup_label.setWordWrap(True)
        setup_label.setStyleSheet(f"font-size: 12px; color: {FG};")
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
        notes_label.setStyleSheet(f"font-size: 13px; color: {FG};")
        notes_layout.addWidget(notes_label)
        root.addWidget(notes_card)

        # ── 開源資訊 ──
        open_card, open_layout = self._group_card(g("opensource_info"))
        open_row = QHBoxLayout()
        open_row.setSpacing(24)

        left_info = QVBoxLayout()
        left_info.setSpacing(4)
        repo_title = QLabel(g("github_repo_label"))
        repo_title.setStyleSheet(f"font-weight: 600; color: {FG};")
        left_info.addWidget(repo_title)
        repo_url = QLabel("https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor")
        repo_url.setStyleSheet(f"font-family: Consolas; font-size: 12px; color: {INFO};")
        repo_url.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        left_info.addWidget(repo_url)
        github_btn = PushButton(g("visit_github_button"))
        github_btn.clicked.connect(lambda: self._app.open_video_link("https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor"))
        left_info.addWidget(github_btn)
        license_title = QLabel(g("license_label"))
        license_title.setStyleSheet(f"font-weight: 600; color: {FG};")
        left_info.addWidget(license_title)
        license_text = QLabel(g("license_text"))
        license_text.setWordWrap(True)
        license_text.setStyleSheet(f"font-size: 12px; color: {FG};")
        left_info.addWidget(license_text)
        open_row.addLayout(left_info, 1)

        right_info = QVBoxLayout()
        right_info.setSpacing(2)
        features_title = QLabel(g("features_list_label"))
        features_title.setStyleSheet(f"font-weight: 600; color: {FG};")
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
            right_info.addWidget(QLabel(f"• {feature}"))
        open_row.addLayout(right_info, 1)
        open_layout.addLayout(open_row)
        root.addWidget(open_card)

        root.addStretch(1)

    def _feature_block(self, layout, title, desc, color):
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {color};")
        layout.addWidget(title_label)
        desc_label = QLabel(desc)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"font-size: 12px; color: {FG};")
        layout.addWidget(desc_label)
        layout.addSpacing(8)

    def _group_card(self, title):
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        box.setStyleSheet("QWidget { background-color: #1e1e2e; border: 1px solid #3b3b3b; border-radius: 8px; }QLabel { background: transparent; }")
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #f8f8f2; background: transparent;")
        layout.addWidget(title_label)
        return box, layout

    def _info_card(self, title, items):
        card, layout = self._group_card(title)
        for key, desc, color in items:
            row = QHBoxLayout()
            row.setSpacing(10)
            key_label = QLabel(f" {key} ")
            key_label.setStyleSheet(f"background-color: {color}; color: #000; padding: 2px 8px; border-radius: 4px; font-family: Consolas; font-weight: 600; font-size: 12px;")
            row.addWidget(key_label, 0, Qt.AlignmentFlag.AlignTop)
            desc_label = QLabel(desc)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("font-size: 12px; color: #f8f8f2; background: transparent;")
            row.addWidget(desc_label, 1)
            layout.addLayout(row)
        return card

    # ── 語言更新（整頁重建）──────────────────────────

    def update_language(self):
        self._rebuild_content()

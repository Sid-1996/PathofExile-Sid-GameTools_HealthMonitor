"""SettingsTab — 設置分頁（熱鍵/通用/更新）。

設計：單一 ScrollArea，四張卡，熱鍵卡為核心（Issue #1）。
白名單：F1-F12 / Ctrl+F1-F12 / Alt+F1-F12（map_key_to_vk_code 已支援）。
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

from qfluentwidgets import BodyLabel, ComboBox, ExpandLayout, FluentIcon, HeaderCardWidget, PushButton, ScrollArea, SettingCardGroup, SwitchButton


_HOTKEY_OPTIONS = [
    *[f"f{i}" for i in range(1, 13)],
    *[f"ctrl+f{i}" for i in range(1, 13)],
    *[f"alt+f{i}" for i in range(1, 13)],
]

_HOTKEY_LABELS = {"f3": "F3 一鍵清包", "f5": "F5 返藏身處", "f6": "F6 一鍵取物", "f9": "F9 全域暫停", "f10": "F10 監控開關"}


class SettingsTab(ScrollArea):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app
        self.view = QWidget(self)
        self.view.setObjectName("settings_view")
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.enableTransparentBackground()

        self._combos: dict[str, ComboBox] = {}
        self._build_ui()
        self._load_from_config()

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self.view)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        title = BodyLabel(self._app.get_text("settings_title"), self.view)
        title.setStyleSheet("font-size: 20px; font-weight: 600; color: #f8f8f2;")
        lay.addWidget(title)

        group = SettingCardGroup(self._app.get_text("settings_group_general"), self.view)
        # 通用
        self.preview_switch = SwitchButton(self.view)
        self.preview_switch.setOnText("ON")
        self.preview_switch.setOffText("OFF")
        self.preview_switch.checkedChanged.connect(self._on_preview_changed)
        group.addSettingCard(self._mk_switch_card("preview_enabled", self.preview_switch))

        self.topmost_switch = SwitchButton(self.view)
        self.topmost_switch.setOnText("ON")
        self.topmost_switch.setOffText("OFF")
        self.topmost_switch.checkedChanged.connect(self._on_topmost_changed)
        group.addSettingCard(self._mk_switch_card("always_on_top", self.topmost_switch))
        lay.addWidget(group)

        # 熱鍵
        hot_group = SettingCardGroup(self._app.get_text("settings_group_hotkeys"), self.view)
        hot_card = HeaderCardWidget(self.view)
        hot_card.setTitle(f"{self._app.get_text('hotkey_settings_title')} — {self._app.get_text('hotkey_settings_desc')}")

        expand = ExpandLayout()
        for key in ("f3", "f5", "f6", "f9", "f10"):
            row = QWidget(hot_card.view)
            row_lay = QVBoxLayout(row)
            row_lay.setContentsMargins(16, 6, 16, 6)
            label = BodyLabel(f"{_HOTKEY_LABELS[key]}", row)
            label.setStyleSheet("color: #f8f8f2;")
            combo = ComboBox(row)
            combo.addItems([o.upper() for o in _HOTKEY_OPTIONS])
            combo.setCurrentText("F3")
            self._combos[key] = combo
            row_lay.addWidget(label)
            row_lay.addWidget(combo)
            expand.addWidget(row)

        apply_btn = PushButton(self._app.get_text("apply"), hot_card.view)
        apply_btn.clicked.connect(self._on_apply_hotkeys)
        expand.addWidget(apply_btn)

        hint = BodyLabel(self._app.get_text("hotkey_settings_hint"), hot_card.view)
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #b8b8c8; font-size: 12px;")
        hint.setTextFormat(Qt.TextFormat.PlainText)
        expand.addWidget(hint)

        hot_card.viewLayout.setContentsMargins(0, 0, 0, 0)
        hot_card.viewLayout.addLayout(expand)
        hot_group.addSettingCard(hot_card)
        lay.addWidget(hot_group)

        # 更新
        upd_group = SettingCardGroup(self._app.get_text("settings_group_update"), self.view)
        self.prerelease_switch = SwitchButton(self.view)
        self.prerelease_switch.setOnText("ON")
        self.prerelease_switch.setOffText("OFF")
        self.prerelease_switch.checkedChanged.connect(self._on_prerelease_changed)
        upd_group.addSettingCard(self._mk_switch_card("allow_prerelease", self.prerelease_switch))
        lay.addWidget(upd_group)

        lay.addStretch(1)

    def _mk_switch_card(self, key: str, switch: SwitchButton):
        from qfluentwidgets import SettingCard

        icon_map = {
            "preview_enabled": FluentIcon.VIEW,
            "always_on_top": FluentIcon.PIN,
            "allow_prerelease": FluentIcon.UPDATE,
        }
        title_map = {
            "preview_enabled": self._app.get_text("enable_preview"),
            "always_on_top": self._app.get_text("always_on_top"),
            "allow_prerelease": self._app.get_text("allow_prerelease_label"),
        }
        content_map = {
            "preview_enabled": self._app.get_text("enable_preview_tip"),
            "always_on_top": self._app.get_text("always_on_top_tip"),
            "allow_prerelease": self._app.get_text("allow_prerelease_tip"),
        }
        card = SettingCard(icon_map.get(key, FluentIcon.SETTING), title_map.get(key, key), content_map.get(key, ""), parent=self.view)
        card.hBoxLayout.addWidget(switch, 0, Qt.AlignmentFlag.AlignRight)
        card.hBoxLayout.addSpacing(16)
        return card

    def _load_from_config(self) -> None:
        cfg = self._app.config
        self.preview_switch.setChecked(bool(cfg.get("preview_enabled", True)))
        self.topmost_switch.setChecked(bool(cfg.get("always_on_top", False)))
        self.prerelease_switch.setChecked(bool(cfg.get("allow_prerelease", False)))
        hk = cfg.get("hotkeys", {})
        for k, combo in self._combos.items():
            v = str(hk.get(k, k)).strip().lower()
            combo.setCurrentText(v.upper() if v.upper() in [o.upper() for o in _HOTKEY_OPTIONS] else k.upper())

    def _on_preview_changed(self, checked: bool) -> None:
        self._app.preview_enabled = bool(checked)
        self._app.config["preview_enabled"] = bool(checked)
        self._app.schedule_config_save()

    def _on_topmost_changed(self, checked: bool) -> None:
        self._app.always_on_top = bool(checked)
        self._app.config["always_on_top"] = bool(checked)
        self._app.schedule_config_save()
        try:
            self._app.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, bool(checked))
            self._app.show()
        except Exception:
            pass

    def _on_prerelease_changed(self, checked: bool) -> None:
        self._app.config["allow_prerelease"] = bool(checked)
        self._app.schedule_config_save()

    def _on_apply_hotkeys(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        chosen = {k: c.currentText().strip().lower() for k, c in self._combos.items()}
        # 重複檢測（F12 不在集內）
        vals = list(chosen.values())
        if len(vals) != len(set(vals)):
            QMessageBox.warning(self, self._app.get_text("warning"), self._app.get_text("hotkey_conflict"))
            return
        self._app.config["hotkeys"] = chosen
        self._app.schedule_config_save()
        try:
            self._app.reload_hotkeys()
            self._app.add_status_message(self._app.get_text("hotkey_settings_applied"), "success")
            self._app.show_floating_notice(self._app.get_text("hotkey_settings_applied"), "success")
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox as MB

            MB.critical(self, self._app.get_text("error"), self._app.get_text("hotkey_apply_failed").format(error=e))

    def update_language(self) -> None:
        # 語言切換時重建標題（簡化：下次進入時生效，狀態由 MainWindow.update_language 觸發重載）
        self._load_from_config()

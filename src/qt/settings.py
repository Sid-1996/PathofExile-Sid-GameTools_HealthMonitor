"""SettingsTab — 設置分頁（熱鍵/通用）。

設計：單一 ScrollArea，三張卡，熱鍵卡為核心（Issue #1）。
白名單：F1-F11 / Ins/Home/PgUp/PgDn/End 各含 Ctrl/Alt（F12 保留為緊急關閉）。
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from qfluentwidgets import BodyLabel, CardWidget, ComboBox, FluentIcon, PushButton, ScrollArea, SettingCardGroup, SwitchButton


_NAV_KEYS = ["ins", "home", "pgup", "pgdn", "end"]
_HOTKEY_OPTIONS = [
    *[f"f{i}" for i in range(1, 12)],
    *[f"ctrl+f{i}" for i in range(1, 12)],
    *[f"alt+f{i}" for i in range(1, 12)],
    *_NAV_KEYS,
    *[f"ctrl+{k}" for k in _NAV_KEYS],
    *[f"alt+{k}" for k in _NAV_KEYS],
]


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
        self._hotkey_row_labels: dict[str, BodyLabel] = {}
        self._build_ui()
        self._load_from_config()

    def _hotkey_labels(self) -> dict[str, str]:
        g = self._app.get_text
        return {
            "f3": g("hotkey_f3_desc"),
            "f5": g("hotkey_f5_desc"),
            "f6": g("hotkey_f6_desc"),
            "f9": g("hotkey_f9_desc"),
            "f10": g("hotkey_f10_desc"),
            "skill_timer": g("hotkey_skill_timer_desc"),
        }

    def _build_ui(self) -> None:
        g = self._app.get_text
        lay = QVBoxLayout(self.view)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        title = BodyLabel(g("settings_title"), self.view)
        title.setStyleSheet("font-size: 20px; font-weight: 600; color: #f8f8f2;")
        lay.addWidget(title)
        self._title_label = title

        # 語言（置頂，唯一入口）
        self._lang_card = CardWidget(self.view)
        lang_lay = QHBoxLayout(self._lang_card)
        lang_lay.setContentsMargins(16, 14, 16, 14)
        lang_lay.setSpacing(12)
        self._lang_label = BodyLabel(g("language"), self._lang_card)
        self._lang_label.setStyleSheet("color: #f8f8f2;")
        self._lang_label.setMinimumWidth(140)
        self.lang_combo = ComboBox(self._lang_card)
        self.lang_combo.addItems(["繁體中文", "English"])
        self.lang_combo.setMinimumWidth(160)
        # ponytail: 以 reverse_map 初始化，避免硬編碼
        try:
            cur = self._app.current_language
            rev = self._app.language_manager.language_reverse_map
            self.lang_combo.setCurrentText(rev.get(cur, "繁體中文"))
        except Exception:
            pass
        self.lang_combo.currentTextChanged.connect(lambda t: self._app.change_language_display(t))
        lang_lay.addWidget(self._lang_label)
        lang_lay.addWidget(self.lang_combo)
        lang_lay.addStretch(1)
        lay.addWidget(self._lang_card)

        group = SettingCardGroup(g("settings_group_general"), self.view)
        self._general_group = group
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

        # 熱鍵（CardWidget 垂直流，避免 HeaderCardWidget view 被壓扁）
        hot_header = BodyLabel(g("settings_group_hotkeys"), self.view)
        hot_header.setStyleSheet("font-size: 14px; font-weight: 600; color: #f8f8f2;")
        lay.addWidget(hot_header)
        self._hot_header = hot_header
        hot_card = CardWidget(self.view)
        hot_lay = QVBoxLayout(hot_card)
        hot_lay.setContentsMargins(16, 16, 16, 16)
        hot_lay.setSpacing(12)
        hot_title = BodyLabel(f"{g('hotkey_settings_title')} — {g('hotkey_settings_desc')}", hot_card)
        hot_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #f8f8f2;")
        hot_title.setWordWrap(True)
        hot_lay.addWidget(hot_title)
        self._hot_title = hot_title

        labels = self._hotkey_labels()
        for key in ("f3", "f5", "f6", "f9", "f10", "skill_timer"):
            row = QWidget(hot_card)
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_lay.setSpacing(12)
            label = BodyLabel(labels.get(key, key), row)
            label.setStyleSheet("color: #f8f8f2;")
            label.setMinimumWidth(140)
            combo = ComboBox(row)
            combo.addItems([o.upper() for o in _HOTKEY_OPTIONS])
            combo.setCurrentText("F3")
            combo.setMinimumWidth(160)
            self._combos[key] = combo
            self._hotkey_row_labels[key] = label
            row_lay.addWidget(label)
            row_lay.addWidget(combo)
            row_lay.addStretch(1)
            hot_lay.addWidget(row)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.apply_btn = PushButton(g("apply"), hot_card)
        self.apply_btn.clicked.connect(self._on_apply_hotkeys)
        btn_row.addWidget(self.apply_btn)
        hot_lay.addLayout(btn_row)

        hint = BodyLabel(g("hotkey_settings_hint"), hot_card)
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #b8b8c8; font-size: 12px;")
        hint.setTextFormat(Qt.TextFormat.PlainText)
        hot_lay.addWidget(hint)
        self._hot_hint = hint

        lay.addWidget(hot_card)

        lay.addStretch(1)

    def _mk_switch_card(self, key: str, switch: SwitchButton):
        from qfluentwidgets import SettingCard

        icon_map = {
            "preview_enabled": FluentIcon.VIEW,
            "always_on_top": FluentIcon.PIN,
        }
        title_map = {
            "preview_enabled": self._app.get_text("enable_preview"),
            "always_on_top": self._app.get_text("always_on_top"),
        }
        content_map = {
            "preview_enabled": self._app.get_text("enable_preview_tip"),
            "always_on_top": self._app.get_text("always_on_top_tip"),
        }
        card = SettingCard(icon_map.get(key, FluentIcon.SETTING), title_map.get(key, key), content_map.get(key, ""), parent=self.view)
        card.hBoxLayout.addWidget(switch, 0, Qt.AlignmentFlag.AlignRight)
        card.hBoxLayout.addSpacing(16)
        return card

    def _load_from_config(self) -> None:
        cfg = self._app.config
        self.preview_switch.setChecked(bool(cfg.get("preview_enabled", True)))
        self.topmost_switch.setChecked(bool(cfg.get("always_on_top", False)))
        # ponytail: blockSignals 避免 setCurrentText 誤觸語言/熱鍵回呼
        try:
            self.lang_combo.blockSignals(True)
            rev = self._app.language_manager.language_reverse_map
            self.lang_combo.setCurrentText(rev.get(self._app.current_language, "繁體中文"))
        except Exception:
            pass
        finally:
            try:
                self.lang_combo.blockSignals(False)
            except Exception:
                pass
        hk = cfg.get("hotkeys", {})
        for k, combo in self._combos.items():
            v = str(hk.get(k, k)).strip().lower()
            try:
                combo.blockSignals(True)
                combo.setCurrentText(v.upper() if v.upper() in [o.upper() for o in _HOTKEY_OPTIONS] else k.upper())
            finally:
                try:
                    combo.blockSignals(False)
                except Exception:
                    pass

    def _on_preview_changed(self, checked: bool) -> None:
        self._app.preview_enabled = bool(checked)
        self._app.config["preview_enabled"] = bool(checked)
        self._app.schedule_config_save()

    def _on_topmost_changed(self, checked: bool) -> None:
        self._app.always_on_top = bool(checked)
        self._app.config["always_on_top"] = bool(checked)
        self._app.schedule_config_save()
        try:
            # FluentWindow 需 hide/show 重算置頂陰影
            was_visible = self._app.isVisible()
            self._app.hide()
            self._app.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, bool(checked))
            if was_visible:
                self._app.show()
            else:
                self._app.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, bool(checked))
                self._app.show()
                self._app.hide()
        except Exception:
            try:
                self._app.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, bool(checked))
                self._app.show()
            except Exception:
                pass

    def _on_apply_hotkeys(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        chosen = {k: c.currentText().strip().lower() for k, c in self._combos.items()}
        vals = list(chosen.values())
        if len(vals) != len(set(vals)):
            QMessageBox.warning(self, self._app.get_text("warning"), self._app.get_text("hotkey_conflict"))
            return
        if any(v == "f12" for v in vals):
            QMessageBox.warning(self, self._app.get_text("warning"), self._app.get_text("hotkey_f12_reserved"))
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
            try:
                self._app.show_floating_notice(self._app.get_text("hotkey_apply_failed").format(error=e), "error")
            except Exception:
                pass

    def update_language(self) -> None:
        g = self._app.get_text
        # 標題與分組
        try:
            self._title_label.setText(g("settings_title"))
            self._general_group.titleLabel.setText(g("settings_group_general"))  # pyright: ignore
            self._hot_header.setText(g("settings_group_hotkeys"))
            self._hot_title.setText(f"{g('hotkey_settings_title')} — {g('hotkey_settings_desc')}")
            self._hot_hint.setText(g("hotkey_settings_hint"))
            self._lang_label.setText(g("language"))
            self.apply_btn.setText(g("apply"))
        except Exception:
            pass
        # 行標精準化（不碰 ComboBox 內部子標）
        labels = self._hotkey_labels()
        for k, label in self._hotkey_row_labels.items():
            try:
                label.setText(labels.get(k, k))
            except Exception:
                pass
        self._load_from_config()
        try:
            self.view.adjustSize()
            self.adjustSize()
        except Exception:
            pass

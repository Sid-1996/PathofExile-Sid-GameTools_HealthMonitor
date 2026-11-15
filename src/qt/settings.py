"""SettingsTab — 設置分頁（熱鍵/通用）。

設計：單一 ScrollArea，三張卡，熱鍵卡為核心（Issue #1）。
白名單：F1-F11 / Ins/Home/PgUp/PgDn/End 各含 Ctrl/Alt（F12 保留為緊急關閉）。
"""

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from qfluentwidgets import BodyLabel, CardWidget, ComboBox, FluentIcon, PushButton, ScrollArea, SettingCardGroup, SwitchButton

from qt.theme import VALID_THEMES, current_theme, current_tokens, normalize_theme, token_pair


def _style_body_label(label: BodyLabel, *, px: int | None = None, weight: QFont.Weight | None = None, token: str = "fg") -> BodyLabel:
    """套用主題顏色與字級。

    顏色走 qfluentwidgets 的 `setTextColor(light, dark)`（切主題時由套件自行重上色）；
    字級走 `setFont()`。**不可**再用 setStyleSheet()，那會在 setTheme() 時被
    `updateStyleSheet()` 整段覆蓋（顏色與字級都消失）。
    """
    light, dark = token_pair(token)
    label.setTextColor(light, dark)
    if px is not None or weight is not None:
        font = label.font()
        if px is not None:
            font.setPixelSize(px)
        if weight is not None:
            font.setWeight(weight)
        label.setFont(font)
    return label


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
        _style_body_label(title, px=20, weight=QFont.Weight.DemiBold)
        lay.addWidget(title)
        self._title_label = title

        # 語言（置頂，唯一入口）
        self._lang_card = CardWidget(self.view)
        lang_lay = QHBoxLayout(self._lang_card)
        lang_lay.setContentsMargins(16, 14, 16, 14)
        lang_lay.setSpacing(12)
        self._lang_label = BodyLabel(g("language"), self._lang_card)
        _style_body_label(self._lang_label)
        self._lang_label.setMinimumWidth(140)
        self.lang_combo = ComboBox(self._lang_card)
        self.lang_combo.addItems(["繁體中文", "简体中文", "English"])
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

        # ── 外觀主題（Phase 4A：正式開放 Dark / Light 選擇器）──
        # 只放「主題」一項，不另建設定來源；套用邏輯一律走 qt.theme.apply_theme()。
        self.appearance_card = CardWidget(self.view)
        appearance_lay = QVBoxLayout(self.appearance_card)
        appearance_lay.setContentsMargins(16, 14, 16, 14)
        appearance_lay.setSpacing(8)
        theme_row = QHBoxLayout()
        theme_row.setSpacing(12)
        self._theme_label = BodyLabel(g("theme"), self.appearance_card)
        _style_body_label(self._theme_label)
        self._theme_label.setMinimumWidth(140)
        # 已寫入設定、但尚未套用（等待重新啟動）的主題；None = 沒有待套用的變更
        self._pending_theme: str | None = None
        self.theme_combo = ComboBox(self.appearance_card)
        # userData 帶內部主題名（dark / light）；顯示文字走 i18n，不直接顯示內部值
        self.theme_combo.addItem(g("theme_dark"), None, "dark")
        self.theme_combo.addItem(g("theme_light"), None, "light")
        self.theme_combo.setMinimumWidth(160)
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        theme_row.addWidget(self._theme_label)
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch(1)
        appearance_lay.addLayout(theme_row)
        self._theme_hint = BodyLabel(g("theme_hint"), self.appearance_card)
        _style_body_label(self._theme_hint, px=12, token="fg_muted")
        self._theme_hint.setWordWrap(True)
        appearance_lay.addWidget(self._theme_hint)
        lay.addWidget(self.appearance_card)

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
        _style_body_label(hot_header, px=14, weight=QFont.Weight.DemiBold)
        lay.addWidget(hot_header)
        self._hot_header = hot_header
        hot_card = CardWidget(self.view)
        hot_lay = QVBoxLayout(hot_card)
        hot_lay.setContentsMargins(16, 16, 16, 16)
        hot_lay.setSpacing(12)
        hot_title = BodyLabel(f"{g('hotkey_settings_title')} — {g('hotkey_settings_desc')}", hot_card)
        _style_body_label(hot_title, px=13, weight=QFont.Weight.DemiBold)
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
            _style_body_label(label)
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
        _style_body_label(hint, px=12, token="fg_muted")
        hint.setTextFormat(Qt.TextFormat.PlainText)
        hot_lay.addWidget(hint)
        self._hot_hint = hint

        lay.addWidget(hot_card)

        # ── 資料與重設（精簡版）──
        data_header = BodyLabel(g("settings_group_data"), self.view)
        _style_body_label(data_header, px=14, weight=QFont.Weight.DemiBold)
        lay.addWidget(data_header)
        self._data_header = data_header
        data_card = CardWidget(self.view)
        data_lay = QVBoxLayout(data_card)
        data_lay.setContentsMargins(16, 16, 16, 16)
        data_lay.setSpacing(10)
        # 路徑列
        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        self._data_label = BodyLabel(g("data_dir_label"), data_card)
        _style_body_label(self._data_label)
        from utils import get_user_data_dir

        data_dir = get_user_data_dir()
        self._data_path_label = QLabel(data_dir, data_card)
        self._data_path_label.setStyleSheet(self._data_path_qss())
        self._data_path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._data_path_label.setWordWrap(True)
        path_row.addWidget(self._data_label)
        path_row.addWidget(self._data_path_label, 1)
        data_lay.addLayout(path_row)
        btn_row2 = QHBoxLayout()
        btn_row2.setSpacing(8)
        self._open_data_btn = PushButton(g("open_data_dir"), data_card)
        self._open_data_btn.setIcon(FluentIcon.FOLDER)
        self._open_data_btn.clicked.connect(self._on_open_data_dir)
        btn_row2.addWidget(self._open_data_btn)
        self._copy_path_btn = PushButton(g("copy_path"), data_card)
        self._copy_path_btn.setIcon(FluentIcon.COPY)
        self._copy_path_btn.clicked.connect(self._on_copy_path)
        btn_row2.addWidget(self._copy_path_btn)
        btn_row2.addStretch(1)
        self._reset_btn = PushButton(g("reset_settings"), data_card)
        self._reset_btn.setIcon(FluentIcon.DELETE)
        self._reset_btn.clicked.connect(self._on_reset_settings)
        btn_row2.addWidget(self._reset_btn)
        data_lay.addLayout(btn_row2)
        lay.addWidget(data_card)

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

    def _data_path_qss(self) -> str:
        return f"color: {current_tokens()['fg_muted']}; font-size: 12px;"

    def _theme_option_texts(self) -> dict[str, str]:
        """主題選項的 i18n 顯示文字（內部值 dark / light 不直接顯示給使用者）。"""
        g = self._app.get_text
        return {"dark": g("theme_dark"), "light": g("theme_light")}

    def _sync_theme_combo(self) -> None:
        """把主題選項同步為「目前實際套用的主題」（若有已儲存待套用的主題則以它為準）。

        程式主動更新控件時暫時阻擋訊號，避免回呼 _on_theme_changed 造成重入；
        阻擋狀態用 blockSignals() 的回傳值保存並原樣還原（不永久關閉訊號）。
        """
        target = self._pending_theme or current_theme()
        index = self.theme_combo.findData(target)
        if index < 0 or self.theme_combo.currentIndex() == index:
            return
        blocked = self.theme_combo.blockSignals(True)
        try:
            self.theme_combo.setCurrentIndex(index)
        finally:
            self.theme_combo.blockSignals(blocked)

    def _reload_theme_combo_texts(self) -> None:
        """語系切換後更新主題選項文字（顯示文字改變不得觸發主題切換）。"""
        blocked = self.theme_combo.blockSignals(True)
        try:
            for name, text in self._theme_option_texts().items():
                index = self.theme_combo.findData(name)
                if index >= 0:
                    self.theme_combo.setItemText(index, text)
        finally:
            self.theme_combo.blockSignals(blocked)
        self._sync_theme_combo()

    def _on_theme_changed(self, text: str) -> None:
        """使用者切換主題：寫入設定 → 重新啟動（重啟後由新程序完整套用新主題）。

        執行期間不再做熱切換：熱切換無法完整刷新所有頁面／對話框／控制項，
        與其顯示半套主題，不如讓新程序在啟動階段一次性載入完整主題。

        1. 立即把新主題寫進設定檔（重啟後由新程序讀取；debounce 不夠保證寫入完成）；
        2. 詢問使用者是否立即重新啟動；不重啟則保留設定，下次啟動生效。
        """
        raw = self.theme_combo.currentData()
        if not isinstance(raw, str) or raw.strip().lower() not in VALID_THEMES:
            # 非法選項：不套用、不寫設定；UI 還原為目前實際主題
            self._sync_theme_combo()
            return
        name = normalize_theme(raw)
        if name == current_theme():
            # 同一主題：不重啟（僅補齊設定值）
            if self._app.config.get("theme") != name:
                self._app.config["theme"] = name
                self._app.schedule_config_save()
            self._pending_theme = None
            self._sync_theme_combo()
            return
        # 不同主題：先確實寫入設定（寫入失敗就維持現狀，不得留下半套狀態）
        self._app.config["theme"] = name
        try:
            saved = self._app.config_manager.save_config(self._app.config)
        except Exception:
            saved = False
        if not saved:
            self._app.config["theme"] = current_theme()
            self._sync_theme_combo()
            self._app.add_status_message(self._app.get_text("save_failed").format(error="theme"), "error")
            return
        self._pending_theme = name
        self._app.restart_with_theme()

    def refresh_theme(self) -> None:
        """主題切換刷新：原生 QSS 需重上；BodyLabel 由 setTextColor(light, dark) 自動跟隨。"""
        if hasattr(self, "_data_path_label"):
            self._data_path_label.setStyleSheet(self._data_path_qss())
        self._sync_theme_combo()

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
        # 主題選項以「實際套用的主題」為準（config 可能尚未套用或已被外部改動）
        self._sync_theme_combo()

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

    def _on_open_data_dir(self) -> None:
        from utils import get_user_data_dir

        path = get_user_data_dir()
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(self, self._app.get_text("warning"), str(e))

    def _on_copy_path(self) -> None:
        from PySide6.QtWidgets import QApplication

        from utils import get_user_data_dir

        try:
            QApplication.clipboard().setText(get_user_data_dir())
            self._app.show_floating_notice(self._app.get_text("copied"), "success")
        except Exception:
            pass

    def _on_reset_settings(self) -> None:
        from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout

        g = self._app.get_text
        dlg = QDialog(self)
        dlg.setWindowTitle(g("confirm_reset_title"))
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel(g("confirm_reset_msg")))
        cb = QCheckBox(g("delete_screenshots_too"))
        lay.addWidget(cb)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            from utils import get_user_data_dir
            import os
            import shutil
            import sys
            import threading
            import time
            from pathlib import Path

            base = get_user_data_dir()
            for name in ("health_monitor_config.json", "health_monitor_config.json.backup"):
                p = os.path.join(base, name)
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass
            if cb.isChecked():
                shots = os.path.join(base, "screenshots")
                if os.path.isdir(shots):
                    try:
                        shutil.rmtree(shots)
                    except Exception:
                        pass
            # ponytail: 標記重設重啟，_shutdown 將跳過 save_config 避免刪後復活
            self._app._reset_no_save = True
            # ponytail: 一律重啟以清記憶體預覽與區域快取（最乾淨）
            if getattr(sys, "frozen", False):
                launch_args: list[str] = []
                cwd = str(Path(sys.executable).parent)
            else:
                launch_args = ["src/app.py"]
                if "--debug" in sys.argv:
                    launch_args.append("--debug")
                cwd = str(Path(__file__).resolve().parent.parent.parent)
            if not self._app._relaunch_detached(launch_args, cwd):
                from PySide6.QtWidgets import QMessageBox

                QMessageBox.warning(self, g("warning"), g("language_restart_failed").format(error="Popen failed"))
                return
            threading.Thread(target=lambda: (time.sleep(3), os._exit(1)), daemon=True).start()
            try:
                self._app.close_app()
            except Exception:
                pass
            os._exit(0)
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.critical(self, g("error"), g("reset_failed").format(error=e))

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
            if hasattr(self, "_theme_label"):
                self._theme_label.setText(g("theme"))
                self._theme_hint.setText(g("theme_hint"))
                self._reload_theme_combo_texts()
            if hasattr(self, "_data_header"):
                self._data_header.setText(g("settings_group_data"))
                self._data_label.setText(g("data_dir_label"))
                self._open_data_btn.setText(g("open_data_dir"))
                self._copy_path_btn.setText(g("copy_path"))
                self._reset_btn.setText(g("reset_settings"))
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

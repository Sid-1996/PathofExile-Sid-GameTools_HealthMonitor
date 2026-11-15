"""
combo.py（Qt 版）— 技能連招分頁
────────────────────────────────────────────────────────
對應 tk 版 `tab_combo.py`（Phase 6）。
- 左欄：3 組連段套組（QTabWidget）+ 全域控制區
- 右欄：技能計時器（SkillTimerModule）+ 使用提示
- 連段執行在背景 thread + keyboard hotkey 回呼中進行，UI 一律走 thread-safe signal
  （`self._app.add_status_message`），不直接碰 widget。
- 執行狀態（combo_sets / combo_enabled / combo_thread / combo_hotkeys）存於 tab 實例。
"""

import logging
import threading
import time
from ctypes import windll
from functools import partial

import keyboard
import pyautogui

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import ComboBox, LineEdit, PrimaryPushButton, PushButton

from qt.skill_timer import SkillTimerModule
from qt.theme import current_tokens

logger = logging.getLogger(__name__)

SendMessageW = windll.user32.SendMessageW
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101

# ── 常數 ──────────────────────────────────────────────────
_TRIGGER_KEYS = ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "A", "S", "D", "F", "G", "H", "J", "K", "L", "Z", "X", "C", "V", "B", "N", "M", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
_SKILL_KEYS = ["off"] + _TRIGGER_KEYS


class ComboTab(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app

        # (widget, 樣式規格)：只記 token 名稱與非色彩樣式，refresh_theme() 時才解析成目前主題
        self._styled: list[tuple[QWidget, tuple]] = []
        # 連段系統狀態色（未啟動/已停止=error、執行中=success）；與業務狀態同步，不可被主題刷新覆蓋
        self._status_tone = "error"

        # 執行狀態（對應 tk 的 self._state）
        self.combo_sets = []
        self.combo_enabled = []
        self.combo_hotkeys: dict = {}
        self.combo_thread: threading.Thread | None = None
        self._combo_running = False
        self._combo_running_lock = threading.Lock()
        self._started_once = False

        self.combo_ui_refs: list[dict] = []

        self._load_combo_config()
        self._initialize_combo_sets()
        self._build_ui()
        self._apply_combo_ui_from_config()

    # ────────────────────────────────────────────────────
    #  主題樣式（顏色唯一來源：qt.theme token）
    # ────────────────────────────────────────────────────

    @staticmethod
    def _style_qss(spec: tuple) -> str:
        """(種類, token, 字級, 字重, 透明底色) → QSS。沿用原版字級/字重，只換顏色來源。"""
        kind, token, px, weight, transparent = spec
        tok = current_tokens()
        if kind == "group":
            # 原本只寫 border + color，QGroupBox 會用 OS palette 的 Window 色補底（light 下是深色殘留）；
            # 顯式 background: transparent 讓卡片跟著頁面底色。
            return (
                f"QGroupBox {{ border: 1px solid {tok['border']}; border-radius: 8px; margin-top: 10px; "
                f"padding-top: 6px; color: {tok['fg']}; background: transparent; }}"
                "QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }"
            )
        if kind == "tabs":
            # 原生 QTabBar 的底色與選取色來自 OS palette（light 下整條是深色），改用 token 自繪。
            # pane 必須一併清掉原生 frame（否則原生 frame 仍用 OS palette 的 Base 色填滿分頁區）；
            # 用 2px transparent 保留原生 frame 的 2px 內縮，維持內容位置不位移。
            return (
                "QTabWidget::pane { border: 2px solid transparent; background: transparent; }"
                "QTabBar { background: transparent; }"
                f"QTabBar::tab {{ background: transparent; color: {tok['fg_muted']}; border: none; padding: 3px 14px; }}"
                f"QTabBar::tab:selected {{ color: {tok['fg']}; border-bottom: 2px solid {tok['accent']}; }}"
                f"QTabBar::tab:hover {{ color: {tok['fg']}; }}"
            )
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

    def _status_qss(self) -> str:
        """連段系統狀態文字色（依業務狀態取 token，不受主題刷新影響）。"""
        return f"color: {current_tokens()[self._status_tone]}; font-size: 13px;"

    def _set_status_tone(self, tone: str) -> None:
        """更新狀態色（tone 為 token 名稱）；只換色，不動文字與業務狀態。"""
        self._status_tone = tone
        self.combo_status_label.setStyleSheet(self._status_qss())

    def refresh_theme(self) -> None:
        """主題切換刷新：只重上既有元件 QSS，不重建、不改版面/字級/內容/輸入值。

        內嵌的技能計時器由 ComboTab 轉發刷新一次（其 QSS 不在本模組登記表內，不會重複刷新）。
        """
        alive: list[tuple[QWidget, tuple]] = []
        for widget, spec in self._styled:
            try:
                widget.setStyleSheet(self._style_qss(spec))
            except RuntimeError:
                continue  # 已被刪除的舊元件
            alive.append((widget, spec))
        self._styled = alive
        # 狀態色依業務狀態重上（success/error），不可被主題刷新覆蓋成固定色
        if getattr(self, "combo_status_label", None) is not None:
            self.combo_status_label.setStyleSheet(self._status_qss())
        if getattr(self, "skill_timer", None):
            self.skill_timer.refresh_theme()

    # ── 執行狀態 ─────────────────────────────────────────

    def is_combo_running(self) -> bool:
        with self._combo_running_lock:
            return self._combo_running

    def set_combo_running(self, state: bool):
        with self._combo_running_lock:
            self._combo_running = state

    def wait_combo_stopped(self, timeout: float = 2.0):
        thread = self.combo_thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=timeout)

    # ────────────────────────────────────────────────────
    #  Config 載入與預設值
    # ────────────────────────────────────────────────────

    def _load_combo_config(self):
        config = self._app.config
        if config.get("combo_sets"):
            self.combo_sets = config["combo_sets"]
            for combo_set in self.combo_sets:
                if "trigger_delay" not in combo_set:
                    combo_set["trigger_delay"] = ""
                if "stationary_attacks" not in combo_set:
                    combo_set["stationary_attacks"] = [False, False, False, False, False]
        if config.get("combo_enabled"):
            self.combo_enabled = config["combo_enabled"]

    def _initialize_combo_sets(self):
        while len(self.combo_sets) < 3:
            self.combo_sets.append(
                {
                    "trigger_key": "Q" if len(self.combo_sets) == 0 else "W" if len(self.combo_sets) == 1 else "E",
                    "trigger_delay": "",
                    "combo_keys": ["", "", "", "", ""],
                    "delays": ["", "", "", "", ""],
                    "stationary_attacks": [False, False, False, False, False],
                }
            )
        while len(self.combo_enabled) < 3:
            self.combo_enabled.append(True if len(self.combo_enabled) == 0 else False)

    # ────────────────────────────────────────────────────
    #  UI 建構
    # ────────────────────────────────────────────────────

    def _styled_group(self, title):
        box = QGroupBox(title)
        self._apply_style(box, ("group", None, None, None, None))
        return box

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel(self._app.get_text("skill_combo_system_title"))
        self._apply_style(title, ("label", "fg", 20, 600, False))
        root.addWidget(title)

        body = QHBoxLayout()
        body.setSpacing(12)
        root.addLayout(body, 1)

        # ── 左欄（可捲動）：連段套組 Notebook + 控制區 ──
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        # 原生 QScrollArea/viewport 底色來自 OS palette（light 下是深色殘留）；改透明，讓頁面跟著主題底色。
        # 注意：QScrollArea.setWidget() 會把 content 的 autoFillBackground 重設回 True，
        # 因此 viewport/content 都要在 setWidget() 之後才關閉。
        left_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        left_content = QWidget()
        left_scroll.setWidget(left_content)
        left_scroll.viewport().setAutoFillBackground(False)
        left_content.setAutoFillBackground(False)
        left_layout = QVBoxLayout(left_content)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        body.addWidget(left_scroll, 3)

        self.combo_notebook = QTabWidget()
        self._apply_style(self.combo_notebook, ("tabs", None, None, None, None))
        for i in range(3):
            tab_frame = QWidget()
            self.combo_notebook.addTab(tab_frame, self._app.get_text("combo_set_template").format(number=i + 1))
            self._build_combo_set_page(tab_frame, i)
        left_layout.addWidget(self.combo_notebook)

        control_box = self._styled_group(self._app.get_text("global_control"))
        control_layout = QVBoxLayout(control_box)
        control_layout.setContentsMargins(12, 12, 12, 12)
        control_layout.setSpacing(8)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.combo_start_btn = PrimaryPushButton(self._app.get_text("start_combo_system"))
        self.combo_start_btn.setToolTip(self._app.get_text("start_combo_system_tip"))
        self.combo_start_btn.clicked.connect(self.start_combo_system)
        btn_row.addWidget(self.combo_start_btn)
        self.combo_stop_btn = PushButton(self._app.get_text("stop_combo_system"))
        self.combo_stop_btn.setEnabled(False)
        self.combo_stop_btn.setToolTip(self._app.get_text("stop_combo_system_tip"))
        self.combo_stop_btn.clicked.connect(self.stop_combo_system)
        btn_row.addWidget(self.combo_stop_btn)
        btn_row.addStretch(1)
        control_layout.addLayout(btn_row)

        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        status_title = QLabel(self._app.get_text("system_status"))
        self._apply_style(status_title, ("label", "fg", 13, 600, False))
        status_row.addWidget(status_title)
        self.combo_status_label = QLabel(self._app.get_text("not_started"))
        self.combo_status_label.setStyleSheet(self._status_qss())
        status_row.addWidget(self.combo_status_label)
        status_row.addStretch(1)
        control_layout.addLayout(status_row)

        left_layout.addWidget(control_box)
        left_layout.addStretch(1)

        # ── 右欄：技能計時器 + 使用提示 ──
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        body.addWidget(right, 2)

        self.skill_timer = SkillTimerModule(parent=right, max_slots=4, on_log=self._app.add_status_message, get_text=self._app.get_text, on_change=self._sync_combo_config)
        self._app.skill_timer = self.skill_timer
        right_layout.addWidget(self.skill_timer)

        help_box = self._styled_group(self._app.get_text("usage_instructions"))
        help_layout = QVBoxLayout(help_box)
        help_layout.setContentsMargins(12, 12, 12, 12)
        help_text = self._app.get_text("skill_combo_usage_title") + "\n\n" + self._app.get_text("skill_combo_usage_content")
        help_label = QLabel(help_text)
        help_label.setWordWrap(True)
        self._apply_style(help_label, ("label", "fg_muted", 12, None, False))
        help_layout.addWidget(help_label)
        right_layout.addWidget(help_box)
        right_layout.addStretch(1)

    def _build_combo_set_page(self, parent, set_index):
        page = QVBoxLayout(parent)
        page.setContentsMargins(12, 12, 12, 12)
        page.setSpacing(12)

        while len(self.combo_ui_refs) <= set_index:
            self.combo_ui_refs.append({})
        refs: dict = self.combo_ui_refs[set_index]
        combo_set = self.combo_sets[set_index]

        enabled_check = QCheckBox(self._app.get_text("enable_this_set"))
        # 原本未上色 → 走 OS palette 字色，light 主題下白字白底；改套 fg token
        self._apply_style(enabled_check, ("label", "fg", None, None, False))
        enabled_check.setChecked(bool(self.combo_enabled[set_index]))
        enabled_check.setToolTip(self._app.get_text("combo_enabled_tip"))
        enabled_check.toggled.connect(lambda checked, idx=set_index: self._on_enabled_toggled(idx, checked))
        page.addWidget(enabled_check)
        refs["enabled_check"] = enabled_check

        # 觸發設定列
        trigger_row = QHBoxLayout()
        trigger_row.setSpacing(8)
        trigger_label = QLabel(self._app.get_text("trigger_skill"))
        self._apply_style(trigger_label, ("label", "fg", None, 600, False))
        trigger_row.addWidget(trigger_label)
        trigger_combo = ComboBox()
        trigger_combo.addItems(_TRIGGER_KEYS)
        trigger_combo.setCurrentText(combo_set.get("trigger_key") or "Q")
        trigger_combo.setToolTip(self._app.get_text("trigger_key_tip"))
        trigger_combo.currentTextChanged.connect(lambda text, idx=set_index: self._on_trigger_key_changed(idx, text))
        trigger_row.addWidget(trigger_combo)
        trigger_row.addSpacing(16)
        trigger_delay_label = QLabel(self._app.get_text("initial_delay_ms"))
        self._apply_style(trigger_delay_label, ("label", "fg", None, 600, False))
        trigger_row.addWidget(trigger_delay_label)
        trigger_delay_entry = LineEdit()
        trigger_delay_entry.setText(str(combo_set.get("trigger_delay", "")))
        trigger_delay_entry.setFixedWidth(72)
        trigger_delay_entry.setToolTip(self._app.get_text("delay_entry_tip"))
        trigger_delay_entry.textChanged.connect(lambda text, idx=set_index: self._on_trigger_delay_changed(idx, text))
        trigger_row.addWidget(trigger_delay_entry)
        trigger_row.addStretch(1)
        page.addLayout(trigger_row)
        refs["trigger_label"] = trigger_label
        refs["trigger_delay_label"] = trigger_delay_label
        refs["trigger_combo"] = trigger_combo
        refs["trigger_delay_entry"] = trigger_delay_entry

        # 技能設定群組
        skills_box = self._styled_group(self._app.get_text("combo_skill_settings"))
        skills_grid = QGridLayout(skills_box)
        skills_grid.setContentsMargins(12, 12, 12, 12)
        skills_grid.setHorizontalSpacing(8)
        skills_grid.setVerticalSpacing(6)

        key_combos = []
        delay_entries = []
        stationary_checks = []
        row_labels = []
        delay_labels = []
        shift_notes = []
        for i in range(5):
            row_label = self._app.get_text("skill_template").format(number=i + 1)
            row_lbl = QLabel(row_label)
            self._apply_style(row_lbl, ("label", "fg", None, 600, False))
            skills_grid.addWidget(row_lbl, i, 0)
            row_labels.append(row_lbl)

            key_combo = ComboBox()
            key_combo.addItems(_SKILL_KEYS)
            key_combo.setCurrentText(combo_set["combo_keys"][i] if combo_set["combo_keys"][i] else "off")
            key_combo.setToolTip(self._app.get_text("trigger_key_tip"))
            key_combo.currentTextChanged.connect(lambda text, idx=set_index, s=i: self._on_combo_key_changed(idx, s, text))
            skills_grid.addWidget(key_combo, i, 1)
            key_combos.append(key_combo)

            delay_label = QLabel(self._app.get_text("delay_ms"))
            # 原本完全未上色 → 走 OS palette 字色，light 主題下白字白底；改套 fg token
            self._apply_style(delay_label, ("label", "fg", None, None, False))
            skills_grid.addWidget(delay_label, i, 2)
            delay_labels.append(delay_label)

            delay_entry = LineEdit()
            delay_entry.setText(str(combo_set["delays"][i]) if combo_set["delays"][i] else "")
            delay_entry.setFixedWidth(72)
            delay_entry.setToolTip(self._app.get_text("delay_entry_tip"))
            delay_entry.textChanged.connect(lambda text, idx=set_index, s=i: self._on_combo_delay_changed(idx, s, text))
            skills_grid.addWidget(delay_entry, i, 3)
            delay_entries.append(delay_entry)

            stationary_check = QCheckBox(self._app.get_text("stationary_attack"))
            # 原本未上色 → 走 OS palette 字色，light 主題下白字白底；改套 fg token
            self._apply_style(stationary_check, ("label", "fg", None, None, False))
            stationary_check.setToolTip(self._app.get_text("stationary_attack_tip"))
            stationary_check.setChecked(bool(combo_set["stationary_attacks"][i]))
            stationary_check.toggled.connect(lambda checked, idx=set_index, s=i: self._on_stationary_toggled(idx, s, checked))
            skills_grid.addWidget(stationary_check, i, 4)
            stationary_checks.append(stationary_check)

            shift_note = QLabel(self._app.get_text("shift_skill_note"))
            self._apply_style(shift_note, ("label", "fg_muted", 11, None, False))
            skills_grid.addWidget(shift_note, i, 5)
            shift_notes.append(shift_note)

        skills_grid.setColumnStretch(6, 1)
        page.addWidget(skills_box)

        refs["skills_box"] = skills_box
        refs["row_labels"] = row_labels
        refs["delay_labels"] = delay_labels
        refs["shift_notes"] = shift_notes
        refs["key_combos"] = key_combos
        refs["delay_entries"] = delay_entries
        refs["stationary_checks"] = stationary_checks

    # ────────────────────────────────────────────────────
    #  Widget → state 更新
    # ────────────────────────────────────────────────────

    def _on_enabled_toggled(self, set_index, checked):
        self.combo_enabled[set_index] = checked
        self._sync_combo_config()

    def _on_trigger_key_changed(self, set_index, text):
        self.combo_sets[set_index]["trigger_key"] = text
        self._sync_combo_config()

    def _on_trigger_delay_changed(self, set_index, text):
        combo_set = self.combo_sets[set_index]
        delay_text = text.strip()
        if delay_text == "":
            combo_set["trigger_delay"] = ""
            return
        try:
            delay = int(delay_text)
            if delay < 0:
                delay = 0
            elif delay > 5000:
                delay = 5000
            combo_set["trigger_delay"] = delay
            entry = self.combo_ui_refs[set_index]["trigger_delay_entry"]
            if entry.text() != str(delay):
                entry.setText(str(delay))
        except ValueError:
            entry = self.combo_ui_refs[set_index]["trigger_delay_entry"]
            current = str(combo_set["trigger_delay"]) if combo_set["trigger_delay"] else ""
            if entry.text() != current:
                entry.setText(current)
        self._sync_combo_config()

    def _on_combo_key_changed(self, set_index, key_index, text):
        self.combo_sets[set_index]["combo_keys"][key_index] = text
        self._sync_combo_config()

    def _on_combo_delay_changed(self, set_index, delay_index, text):
        combo_set = self.combo_sets[set_index]
        delay_text = text.strip()
        if delay_text == "":
            combo_set["delays"][delay_index] = ""
            return
        try:
            delay = int(delay_text)
            if delay < 0:
                delay = 0
            elif delay > 5000:
                delay = 5000
            combo_set["delays"][delay_index] = delay
            entry = self.combo_ui_refs[set_index]["delay_entries"][delay_index]
            if entry.text() != str(delay):
                entry.setText(str(delay))
        except ValueError:
            entry = self.combo_ui_refs[set_index]["delay_entries"][delay_index]
            current = str(combo_set["delays"][delay_index]) if combo_set["delays"][delay_index] else ""
            if entry.text() != current:
                entry.setText(current)
        self._sync_combo_config()

    def _on_stationary_toggled(self, set_index, skill_index, checked):
        self.combo_sets[set_index]["stationary_attacks"][skill_index] = checked
        self._sync_combo_config()

    def _apply_combo_ui_from_config(self):
        for set_index in range(len(self.combo_sets)):
            refs = self.combo_ui_refs[set_index]
            combo_set = self.combo_sets[set_index]
            refs["enabled_check"].setChecked(bool(self.combo_enabled[set_index]))
            refs["trigger_combo"].setCurrentText(combo_set["trigger_key"])
            refs["trigger_delay_entry"].setText(str(combo_set["trigger_delay"]) if combo_set["trigger_delay"] else "")
            for i in range(5):
                refs["key_combos"][i].setCurrentText(combo_set["combo_keys"][i] if combo_set["combo_keys"][i] else "off")
                refs["delay_entries"][i].setText(str(combo_set["delays"][i]) if combo_set["delays"][i] else "")
                refs["stationary_checks"][i].setChecked(bool(combo_set["stationary_attacks"][i]))
        # 技能計時器：還原已儲存的 skill_timer config（_sync_combo_config 會寫入此鍵）
        cfg_st = self._app.config.get("skill_timer")
        if cfg_st and self.skill_timer:
            self.skill_timer.load_config(cfg_st)

    # ────────────────────────────────────────────────────
    #  連段系統控制
    # ────────────────────────────────────────────────────

    def start_combo_system(self):
        if self.is_combo_running():
            QMessageBox.warning(self, self._app.get_text("warning"), self._app.get_text("combo_system_already_running"))
            return

        enabled_sets = [i for i, enabled in enumerate(self.combo_enabled) if enabled]
        if not enabled_sets:
            QMessageBox.warning(self, self._app.get_text("warning"), self._app.get_text("enable_at_least_one_combo_set"))
            return

        for i in enabled_sets:
            combo_set = self.combo_sets[i]
            if not combo_set["trigger_key"]:
                QMessageBox.critical(self, self._app.get_text("error"), self._app.get_text("combo_trigger_key_not_set").format(number=i + 1))
                return
            has_combo = any(key for key in combo_set["combo_keys"] if key and key != "off" and key != "")
            if not has_combo:
                QMessageBox.critical(self, self._app.get_text("error"), self._app.get_text("combo_skill_sequence_empty").format(number=i + 1))
                return

        self.set_combo_running(True)
        self._started_once = True
        self.combo_thread = threading.Thread(target=self.run_combo_system, daemon=True)
        self.combo_thread.start()

        self.combo_start_btn.setEnabled(False)
        self.combo_stop_btn.setEnabled(True)
        self.combo_status_label.setText(self._app.get_text("combo_running"))
        self._set_status_tone("success")

        enabled_count = len(enabled_sets)
        self._app.add_status_message(self._app.get_text("combo_system_started").format(count=enabled_count), "success")
        logger.info("技能連段系統已啟動")

    def stop_combo_system(self):
        if not self.is_combo_running():
            return

        logger.info("正在停止連段系統...")
        self.set_combo_running(False)

        self.wait_combo_stopped(timeout=2.0)

        for hotkey in self.combo_hotkeys.values():
            try:
                keyboard.remove_hotkey(hotkey)
            except Exception:
                pass
        self.combo_hotkeys.clear()

        self.combo_start_btn.setEnabled(True)
        self.combo_stop_btn.setEnabled(False)
        self.combo_status_label.setText(self._app.get_text("combo_stopped"))
        self._set_status_tone("error")

        self._app.add_status_message(self._app.get_text("combo_system_stopped"), "info")
        logger.info("連段系統已完全停止")

    def run_combo_system(self):
        logger.info("連段系統線程已啟動")

        for i, enabled in enumerate(self.combo_enabled):
            if enabled:
                trigger_key = self.combo_sets[i]["trigger_key"].lower()
                try:
                    hotkey_id = keyboard.add_hotkey(trigger_key, partial(self.execute_combo, i), suppress=False)
                    self.combo_hotkeys[f"combo_{i}"] = hotkey_id
                    logger.info("註冊快捷鍵: %s -> 連段套組 %s", trigger_key, i + 1)
                except Exception as e:
                    logger.error("註冊快捷鍵失敗 %s: %s", trigger_key, e)

        while self.is_combo_running():
            time.sleep(0.1)

        logger.info("連段系統線程已結束")

    def execute_combo(self, set_index):
        if not self.is_combo_running():
            return

        if self._app.monitor_tab.window_var.get():
            if not self._app.window_key_sender.is_game_window_foreground(self._app.monitor_tab.window_var.get()):
                logger.info("遊戲視窗 '%s' 不在前台，跳過連段執行", self._app.monitor_tab.window_var.get())
                return

        combo_set = self.combo_sets[set_index]
        combo_keys = combo_set["combo_keys"]
        delays = combo_set["delays"]
        trigger_delay = combo_set.get("trigger_delay", "")
        trigger_key = combo_set.get("trigger_key", "")

        valid_keys = [key for key in combo_keys if key and key != "off" and key != ""]

        self._app.add_status_message(self._app.get_text("combo_trigger_detected").format(set=set_index + 1, key=trigger_key, count=len(valid_keys)), "monitor")

        if valid_keys:
            skills_text = " | ".join([f"{i + 1}:{key}" for i, key in enumerate(valid_keys)])
            self._app.add_status_message(self._app.get_text("combo_skill_sequence").format(sequence=skills_text), "monitor")
        logger.debug("執行連段套組 %s: %s", set_index + 1, valid_keys)

        if trigger_delay and trigger_delay != "off" and trigger_delay != "":
            try:
                delay_ms = int(trigger_delay)
                if delay_ms > 0:
                    delay = delay_ms / 1000.0
                    self._app.add_status_message(self._app.get_text("combo_trigger_delay").format(delay=delay_ms), "info")
                    logger.debug("觸發延遲: %sms", delay_ms)
                    time.sleep(delay)
            except (ValueError, TypeError):
                pass

        for i, key in enumerate(combo_keys):
            if not key or key == "off" or key == "" or not self.is_combo_running():
                if not self.is_combo_running():
                    msg = self._app.get_text("combo_set_interrupted").format(number=set_index + 1)
                    self._app.add_status_message(msg, "warning")
                    self._app.show_floating_notice(msg, "warning")
                    logger.info("連段套組 %s 被中斷", set_index + 1)
                    return
                continue

            try:
                is_stationary = combo_set.get("stationary_attacks", [False] * 5)[i]

                game_hwnd = self._app.window_key_sender.get_game_window_handle()
                if game_hwnd:
                    if is_stationary:
                        shift_vk = self._app.window_key_sender.map_key_to_vk_code("shift")
                        skill_vk = self._app.window_key_sender.map_key_to_vk_code(key.lower())

                        if shift_vk and skill_vk:
                            SendMessageW(game_hwnd, WM_KEYDOWN, shift_vk, 0)
                            time.sleep(0.01)
                            SendMessageW(game_hwnd, WM_KEYDOWN, skill_vk, 0)
                            time.sleep(0.01)
                            SendMessageW(game_hwnd, WM_KEYUP, skill_vk, 0)
                            time.sleep(0.01)
                            SendMessageW(game_hwnd, WM_KEYUP, shift_vk, 0)

                            self._app.add_status_message(
                                self._app.get_text("combo_skill_execution").format(
                                    index=i + 1, skill=f"Shift+{key}", type=self._app.get_text("stationary_attack"), method=self._app.get_text("selective_send")
                                ),
                                "success",
                            )
                            logger.debug("原地攻擊模式: Shift+%s (發送到遊戲窗口)", key)
                        else:
                            pyautogui.keyDown("shift")
                            pyautogui.press(key.lower())
                            pyautogui.keyUp("shift")
                            self._app.add_status_message(
                                self._app.get_text("combo_skill_execution").format(
                                    index=i + 1, skill=f"Shift+{key}", type=self._app.get_text("stationary_attack"), method=self._app.get_text("global_send")
                                ),
                                "warning",
                            )
                            logger.debug("原地攻擊模式: Shift+%s (全局按鍵)", key)
                    else:
                        vk_code = self._app.window_key_sender.map_key_to_vk_code(key.lower())
                        if vk_code:
                            self._app.window_key_sender.send_key_to_window_combo(game_hwnd, vk_code)
                            self._app.add_status_message(
                                self._app.get_text("combo_skill_execution").format(index=i + 1, skill=key, type=self._app.get_text("normal_attack"), method=self._app.get_text("selective_send")),
                                "success",
                            )
                            logger.debug("[SKILL] 技能連段選擇性按下技能鍵: %s (發送到遊戲窗口)", key)
                        else:
                            pyautogui.press(key.lower())
                            self._app.add_status_message(
                                self._app.get_text("combo_skill_execution").format(index=i + 1, skill=key, type=self._app.get_text("normal_attack"), method=self._app.get_text("global_send")),
                                "warning",
                            )
                            logger.debug("[SKILL] 技能連段全局按下技能鍵: %s (鍵碼映射失敗)", key)
                else:
                    if is_stationary:
                        pyautogui.keyDown("shift")
                        pyautogui.press(key.lower())
                        pyautogui.keyUp("shift")
                        self._app.add_status_message(
                            self._app.get_text("combo_skill_execution").format(
                                index=i + 1, skill=f"Shift+{key}", type=self._app.get_text("stationary_attack"), method=self._app.get_text("global_send")
                            ),
                            "warning",
                        )
                        logger.debug("原地攻擊模式: Shift+%s (全局按鍵)", key)
                    else:
                        pyautogui.press(key.lower())
                        self._app.add_status_message(
                            self._app.get_text("combo_skill_execution").format(index=i + 1, skill=key, type=self._app.get_text("normal_attack"), method=self._app.get_text("global_send")), "warning"
                        )
                        logger.debug("全局按下技能鍵: %s (無法獲取窗口句柄)", key)
            except Exception as e:
                msg = self._app.get_text("combo_skill_execution_failed").format(index=i + 1, key=key, error=str(e))
                self._app.add_status_message(msg, "error")
                self._app.show_floating_notice(msg, "error")
                logger.error("按鍵模擬失敗 %s: %s", key, e)
                continue

            if i < len(combo_keys) - 1 and delays[i] and delays[i] != "off":
                try:
                    delay_ms = int(delays[i])
                    if delay_ms > 0:
                        delay = delay_ms / 1000.0
                        self._app.add_status_message(self._app.get_text("combo_skill_delay").format(delay=delay_ms), "info")
                        time.sleep(delay)
                        logger.debug("延遲: %sms", delay_ms)
                except (ValueError, TypeError):
                    pass

        logger.debug("連段套組 %s 執行完成", set_index + 1)

        self._app.add_status_message(self._app.get_text("combo_completed").format(set=set_index + 1, key=trigger_key, count=len(valid_keys)), "success")

    # ────────────────────────────────────────────────────
    #  Config 存檔
    # ────────────────────────────────────────────────────

    def _sync_combo_config(self):
        """把連段套組 + 技能計時器同步進 config 並排程即時儲存（自動儲存，無 popup）。"""
        self._app.config["combo_sets"] = self.combo_sets
        self._app.config["combo_enabled"] = self.combo_enabled
        if getattr(self, "skill_timer", None):
            self._app.config["skill_timer"] = self.skill_timer.get_config()
        self._app.schedule_config_save()

    # ────────────────────────────────────────────────────
    #  語言切換
    # ────────────────────────────────────────────────────

    def update_combo_tab_language(self):
        for i in range(self.combo_notebook.count()):
            self.combo_notebook.setTabText(i, self._app.get_text("combo_set_template").format(number=i + 1))
        for refs in self.combo_ui_refs:
            refs["enabled_check"].setText(self._app.get_text("enable_this_set"))
            refs["enabled_check"].setToolTip(self._app.get_text("combo_enabled_tip"))
            refs["trigger_label"].setText(self._app.get_text("trigger_skill"))
            refs["trigger_combo"].setToolTip(self._app.get_text("trigger_key_tip"))
            refs["trigger_delay_label"].setText(self._app.get_text("initial_delay_ms"))
            refs["trigger_delay_entry"].setToolTip(self._app.get_text("delay_entry_tip"))
            refs["skills_box"].setTitle(self._app.get_text("combo_skill_settings"))
            for i in range(5):
                refs["row_labels"][i].setText(self._app.get_text("skill_template").format(number=i + 1))
                refs["key_combos"][i].setToolTip(self._app.get_text("trigger_key_tip"))
                refs["delay_labels"][i].setText(self._app.get_text("delay_ms"))
                refs["delay_entries"][i].setToolTip(self._app.get_text("delay_entry_tip"))
                refs["stationary_checks"][i].setText(self._app.get_text("stationary_attack"))
                refs["stationary_checks"][i].setToolTip(self._app.get_text("stationary_attack_tip"))
                refs["shift_notes"][i].setText(self._app.get_text("shift_skill_note"))
        if self.is_combo_running():
            self.combo_status_label.setText(self._app.get_text("combo_running"))
        elif self._started_once:
            self.combo_status_label.setText(self._app.get_text("combo_stopped"))
        else:
            self.combo_status_label.setText(self._app.get_text("not_started"))
        self.combo_start_btn.setText(self._app.get_text("start_combo_system"))
        self.combo_start_btn.setToolTip(self._app.get_text("start_combo_system_tip"))
        self.combo_stop_btn.setText(self._app.get_text("stop_combo_system"))
        self.combo_stop_btn.setToolTip(self._app.get_text("stop_combo_system_tip"))
        if self.skill_timer:
            self.skill_timer.refresh_language()

    # ────────────────────────────────────────────────────
    #  主題切換（Phase 2C：combo 樣式全面 token 化）
    #  refresh_theme() 定義於本類別上方（與 skill_timer 的轉發一起處理）。
    # ────────────────────────────────────────────────────

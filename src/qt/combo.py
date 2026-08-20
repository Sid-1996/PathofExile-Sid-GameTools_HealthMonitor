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

SendMessageW = windll.user32.SendMessageW
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101

# ── 常數 ──────────────────────────────────────────────────
SUCCESS = "#50fa7b"
ERROR = "#ff5555"
MUTED = "#b8b8c8"
GROUP_BORDER = "#3b3b3b"

_TRIGGER_KEYS = ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "A", "S", "D", "F", "G", "H", "J", "K", "L", "Z", "X", "C", "V", "B", "N", "M", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
_SKILL_KEYS = ["off"] + _TRIGGER_KEYS


class ComboTab(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app

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
        box.setStyleSheet(
            f"QGroupBox {{ border: 1px solid {GROUP_BORDER}; border-radius: 8px; margin-top: 10px; padding-top: 6px; color: #f8f8f2; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; }}"
        )
        return box

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel(self._app.get_text("skill_combo_system_title"))
        title.setStyleSheet("font-size: 20px; font-weight: 600; color: #f8f8f2;")
        root.addWidget(title)

        body = QHBoxLayout()
        body.setSpacing(12)
        root.addLayout(body, 1)

        # ── 左欄（可捲動）：連段套組 Notebook + 控制區 ──
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_content = QWidget()
        left_scroll.setWidget(left_content)
        left_layout = QVBoxLayout(left_content)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        body.addWidget(left_scroll, 3)

        self.combo_notebook = QTabWidget()
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
        self.combo_stop_btn.clicked.connect(self.stop_combo_system)
        btn_row.addWidget(self.combo_stop_btn)
        btn_row.addStretch(1)
        control_layout.addLayout(btn_row)

        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        status_title = QLabel(self._app.get_text("system_status"))
        status_title.setStyleSheet("font-weight: 600; font-size: 13px;")
        status_row.addWidget(status_title)
        self.combo_status_label = QLabel(self._app.get_text("not_started"))
        self.combo_status_label.setStyleSheet(f"color: {ERROR}; font-size: 13px;")
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
        help_label.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
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
        enabled_check.setChecked(bool(self.combo_enabled[set_index]))
        enabled_check.toggled.connect(lambda checked, idx=set_index: self._on_enabled_toggled(idx, checked))
        page.addWidget(enabled_check)
        refs["enabled_check"] = enabled_check

        # 觸發設定列
        trigger_row = QHBoxLayout()
        trigger_row.setSpacing(8)
        trigger_label = QLabel(self._app.get_text("trigger_skill"))
        trigger_label.setStyleSheet("font-weight: 600;")
        trigger_row.addWidget(trigger_label)
        trigger_combo = ComboBox()
        trigger_combo.addItems(_TRIGGER_KEYS)
        trigger_combo.setCurrentText(combo_set.get("trigger_key") or "Q")
        trigger_combo.currentTextChanged.connect(lambda text, idx=set_index: self._on_trigger_key_changed(idx, text))
        trigger_row.addWidget(trigger_combo)
        trigger_row.addSpacing(16)
        trigger_delay_label = QLabel(self._app.get_text("initial_delay_ms"))
        trigger_delay_label.setStyleSheet("font-weight: 600;")
        trigger_row.addWidget(trigger_delay_label)
        trigger_delay_entry = LineEdit()
        trigger_delay_entry.setText(str(combo_set.get("trigger_delay", "")))
        trigger_delay_entry.setFixedWidth(72)
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
            row_lbl.setStyleSheet("font-weight: 600;")
            skills_grid.addWidget(row_lbl, i, 0)
            row_labels.append(row_lbl)

            key_combo = ComboBox()
            key_combo.addItems(_SKILL_KEYS)
            key_combo.setCurrentText(combo_set["combo_keys"][i] if combo_set["combo_keys"][i] else "off")
            key_combo.currentTextChanged.connect(lambda text, idx=set_index, s=i: self._on_combo_key_changed(idx, s, text))
            skills_grid.addWidget(key_combo, i, 1)
            key_combos.append(key_combo)

            delay_label = QLabel(self._app.get_text("delay_ms"))
            skills_grid.addWidget(delay_label, i, 2)
            delay_labels.append(delay_label)

            delay_entry = LineEdit()
            delay_entry.setText(str(combo_set["delays"][i]) if combo_set["delays"][i] else "")
            delay_entry.setFixedWidth(72)
            delay_entry.textChanged.connect(lambda text, idx=set_index, s=i: self._on_combo_delay_changed(idx, s, text))
            skills_grid.addWidget(delay_entry, i, 3)
            delay_entries.append(delay_entry)

            stationary_check = QCheckBox(self._app.get_text("stationary_attack"))
            stationary_check.setToolTip(self._app.get_text("stationary_attack_tip"))
            stationary_check.setChecked(bool(combo_set["stationary_attacks"][i]))
            stationary_check.toggled.connect(lambda checked, idx=set_index, s=i: self._on_stationary_toggled(idx, s, checked))
            skills_grid.addWidget(stationary_check, i, 4)
            stationary_checks.append(stationary_check)

            shift_note = QLabel(self._app.get_text("shift_skill_note"))
            shift_note.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
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
        self.combo_status_label.setStyleSheet(f"color: {SUCCESS}; font-size: 13px;")

        enabled_count = len(enabled_sets)
        self._app.add_status_message(self._app.get_text("combo_system_started").format(count=enabled_count), "success")
        print("技能連段系統已啟動")

    def stop_combo_system(self):
        if not self.is_combo_running():
            return

        print("[STOP] 正在停止連段系統...")
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
        self.combo_status_label.setStyleSheet(f"color: {ERROR}; font-size: 13px;")

        self._app.add_status_message(self._app.get_text("combo_system_stopped"), "info")
        print("[STOP] 連段系統已完全停止")

    def run_combo_system(self):
        print("連段系統線程已啟動")

        for i, enabled in enumerate(self.combo_enabled):
            if enabled:
                trigger_key = self.combo_sets[i]["trigger_key"].lower()
                try:
                    hotkey_id = keyboard.add_hotkey(trigger_key, partial(self.execute_combo, i), suppress=False)
                    self.combo_hotkeys[f"combo_{i}"] = hotkey_id
                    print(f"註冊快捷鍵: {trigger_key} -> 連段套組 {i + 1}")
                except Exception as e:
                    print(f"註冊快捷鍵失敗 {trigger_key}: {e}")

        while self.is_combo_running():
            time.sleep(0.1)

        print("連段系統線程已結束")

    def execute_combo(self, set_index):
        if not self.is_combo_running():
            return

        if self._app.monitor_tab.window_var.get():
            if not self._app.window_key_sender.is_game_window_foreground(self._app.monitor_tab.window_var.get()):
                print(f"遊戲視窗 '{self._app.monitor_tab.window_var.get()}' 不在前台，跳過連段執行")
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
        print(f"執行連段套組 {set_index + 1}: {valid_keys}")

        if trigger_delay and trigger_delay != "off" and trigger_delay != "":
            try:
                delay_ms = int(trigger_delay)
                if delay_ms > 0:
                    delay = delay_ms / 1000.0
                    self._app.add_status_message(self._app.get_text("combo_trigger_delay").format(delay=delay_ms), "info")
                    print(f"  觸發延遲: {delay_ms}ms")
                    time.sleep(delay)
            except (ValueError, TypeError):
                pass

        for i, key in enumerate(combo_keys):
            if not key or key == "off" or key == "" or not self.is_combo_running():
                if not self.is_combo_running():
                    self._app.add_status_message(self._app.get_text("combo_set_interrupted").format(number=set_index + 1), "warning")
                    print(f"連段套組 {set_index + 1} 被中斷")
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
                            print(f"  原地攻擊模式: Shift+{key} (發送到遊戲窗口)")
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
                            print(f"  原地攻擊模式: Shift+{key} (全局按鍵)")
                    else:
                        vk_code = self._app.window_key_sender.map_key_to_vk_code(key.lower())
                        if vk_code:
                            self._app.window_key_sender.send_key_to_window_combo(game_hwnd, vk_code)
                            self._app.add_status_message(
                                self._app.get_text("combo_skill_execution").format(index=i + 1, skill=key, type=self._app.get_text("normal_attack"), method=self._app.get_text("selective_send")),
                                "success",
                            )
                            print(f"  [SKILL] 技能連段選擇性按下技能鍵: {key} (發送到遊戲窗口)")
                        else:
                            pyautogui.press(key.lower())
                            self._app.add_status_message(
                                self._app.get_text("combo_skill_execution").format(index=i + 1, skill=key, type=self._app.get_text("normal_attack"), method=self._app.get_text("global_send")),
                                "warning",
                            )
                            print(f"  [SKILL] 技能連段全局按下技能鍵: {key} (鍵碼映射失敗)")
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
                        print(f"  原地攻擊模式: Shift+{key} (全局按鍵)")
                    else:
                        pyautogui.press(key.lower())
                        self._app.add_status_message(
                            self._app.get_text("combo_skill_execution").format(index=i + 1, skill=key, type=self._app.get_text("normal_attack"), method=self._app.get_text("global_send")), "warning"
                        )
                        print(f"  全局按下技能鍵: {key} (無法獲取窗口句柄)")
            except Exception as e:
                self._app.add_status_message(self._app.get_text("combo_skill_execution_failed").format(index=i + 1, key=key, error=str(e)), "error")
                print(f"  按鍵模擬失敗 {key}: {e}")
                continue

            if i < len(combo_keys) - 1 and delays[i] and delays[i] != "off":
                try:
                    delay_ms = int(delays[i])
                    if delay_ms > 0:
                        delay = delay_ms / 1000.0
                        self._app.add_status_message(self._app.get_text("combo_skill_delay").format(delay=delay_ms), "info")
                        time.sleep(delay)
                        print(f"  延遲: {delay_ms}ms")
                except (ValueError, TypeError):
                    pass

        print(f"連段套組 {set_index + 1} 執行完成")

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
            refs["trigger_label"].setText(self._app.get_text("trigger_skill"))
            refs["trigger_delay_label"].setText(self._app.get_text("initial_delay_ms"))
            refs["skills_box"].setTitle(self._app.get_text("combo_skill_settings"))
            for i in range(5):
                refs["row_labels"][i].setText(self._app.get_text("skill_template").format(number=i + 1))
                refs["delay_labels"][i].setText(self._app.get_text("delay_ms"))
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
        if self.skill_timer:
            self.skill_timer.refresh_language()

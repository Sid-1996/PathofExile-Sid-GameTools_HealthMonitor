"""
skill_timer.py（Qt 版）
循環計時自動釋放技能模組
────────────────────────────────────────────────────────
對應 tk 版 `skill_timer.py`（Phase 8 提前至 Phase 6，因 ComboTab 右欄內嵌此模組）。
- 完全獨立的 class，無外部套件依賴（只用標準庫 + PySide6 + pyautogui）
- 每個技能槽各自有獨立 threading.Timer 迴圈，互不干擾
- 支援單鍵（q、w、e、r）和組合鍵（ctrl+1、shift+q）
- 毫秒精度，最低 50ms
- SkillSlot 以純 Python attribute 為 state，QLineEdit/QComboBox/QSpinBox/QCheckBox 訊號同步
"""

import threading

try:
    import pyautogui

    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0
    _PYAUTOGUI_OK = True
except ImportError:
    _PYAUTOGUI_OK = False

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import ComboBox, PushButton

# ── 常數 ──────────────────────────────────────────────────
_MIN_MS = 50  # 最低間隔 ms
_MAX_SLOTS = 8  # 最多技能槽
_MODIFIERS = ["none", "ctrl", "shift", "alt"]
_COLOR_ON = "#50fa7b"  # 執行中（綠）
_COLOR_OFF = "#ff5555"  # 停止（紅）
_COLOR_HEADER = "#b8b8c8"  # 表頭（灰）
_COLOR_WARN = "#f1fa8c"  # 警告（黃）


# ══════════════════════════════════════════════════════════
#  SkillSlot：單一技能槽，負責計時與送鍵
# ══════════════════════════════════════════════════════════
class SkillSlot:
    """
    每個 SkillSlot 持有自己的狀態（key/modifier/interval_ms/enabled），
    UI widget 透過 bind_widgets 的 signal 同步到這些 attribute。
    """

    def __init__(self):
        self.key = ""
        self.modifier = "none"
        self.interval_ms = 1000
        self.enabled = False

        self._running = False
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

        # UI 綁定（bind_widgets 之後才有值）
        self._key_edit: QLineEdit | None = None
        self._modifier_combo: ComboBox | None = None
        self._interval_spin: QSpinBox | None = None
        self._enabled_check: QCheckBox | None = None

    # ── UI 綁定 ──

    def bind_widgets(self, key_edit, modifier_combo, interval_spin, enabled_check):
        self._key_edit = key_edit
        self._modifier_combo = modifier_combo
        self._interval_spin = interval_spin
        self._enabled_check = enabled_check
        key_edit.textChanged.connect(self._on_key_changed)
        modifier_combo.currentTextChanged.connect(self._on_modifier_changed)
        interval_spin.valueChanged.connect(self._on_interval_changed)
        enabled_check.toggled.connect(self._on_enabled_changed)

    def _on_key_changed(self, text):
        self.key = text.strip()

    def _on_modifier_changed(self, text):
        self.modifier = text

    def _on_interval_changed(self, value):
        self.interval_ms = value

    def _on_enabled_changed(self, checked):
        self.enabled = checked

    def set_ui_value(self, key, modifier, interval_ms, enabled):
        """load_config 用：同步 state + UI。"""
        self.key = key
        self.modifier = modifier
        self.interval_ms = interval_ms
        self.enabled = enabled
        key_edit = self._key_edit
        modifier_combo = self._modifier_combo
        interval_spin = self._interval_spin
        enabled_check = self._enabled_check
        if key_edit is None or modifier_combo is None or interval_spin is None or enabled_check is None:
            return
        key_edit.setText(key)
        modifier_combo.setCurrentText(modifier)
        interval_spin.setValue(max(_MIN_MS, int(interval_ms)))
        enabled_check.setChecked(enabled)

    def set_enabled(self, checked):
        self.enabled = checked
        enabled_check = self._enabled_check
        if enabled_check is not None:
            enabled_check.setChecked(checked)

    # ── 送鍵（在 lock 外部執行，避免死鎖）──

    def _send_key(self):
        if not _PYAUTOGUI_OK:
            return
        key = self.key.strip().lower()
        mod = self.modifier
        if not key:
            return
        try:
            if mod == "none":
                pyautogui.press(key)  # pyright: ignore[reportPossiblyUnboundVariable]
            else:
                pyautogui.hotkey(mod, key)  # pyright: ignore[reportPossiblyUnboundVariable]
        except Exception:
            pass  # 遊戲視窗切走等情況靜默忽略

    # ── 遞迴計時迴圈 ──

    def _loop(self):
        """送鍵 → 排下一次；在 lock 外送鍵避免死鎖"""
        with self._lock:
            if not self._running:
                return

        self._send_key()

        interval_s = max(self.interval_ms, _MIN_MS) / 1000.0
        with self._lock:
            if self._running:
                self._timer = threading.Timer(interval_s, self._loop)
                self._timer.daemon = True
                self._timer.start()

    # ── 公開控制 ──

    def start(self) -> bool:
        """啟動迴圈，回傳 False 代表設定不合法"""
        if not self.key.strip():
            return False
        if self.interval_ms < _MIN_MS:
            return False

        with self._lock:
            if self._running:
                return True  # 已在跑，視為成功
            self._running = True

        interval_s = max(self.interval_ms, _MIN_MS) / 1000.0
        with self._lock:
            self._timer = threading.Timer(interval_s, self._loop)
            self._timer.daemon = True
            self._timer.start()
        return True

    def stop(self):
        with self._lock:
            self._running = False
            if self._timer:
                self._timer.cancel()
                self._timer = None

    @property
    def is_running(self) -> bool:
        return self._running


# ══════════════════════════════════════════════════════════
#  SkillTimerModule：UI 模組（QWidget）
# ══════════════════════════════════════════════════════════
class SkillTimerModule(QWidget):
    """
    QWidget 版技能計時器。可直接 addWidget 進任何父容器。
    """

    def __init__(self, parent=None, max_slots: int = 4, on_log=None, get_text=None, on_change=None):
        """
        parent     : 父容器
        max_slots  : 最多幾個技能槽（上限 _MAX_SLOTS）
        on_log     : 可選 callback(message, type)
        get_text   : 可選 callback(key) -> str，接語言系統
        on_change  : 可選 callback()，任何槽位設定變更時觸發（供即時儲存）
        """
        super().__init__(parent)
        self._on_log = on_log
        self._get_text = get_text
        self._on_change = on_change
        self._n = min(max_slots, _MAX_SLOTS)
        self.slots = [SkillSlot() for _ in range(self._n)]

        self._status_labels: list[QLabel] = []
        self._toggle_btns: list[PushButton] = []
        self._btn_toggle_all: PushButton | None = None

        self._build_ui()

    # ────────────────────────────────────────────────────
    #  輔助：取語言字串（沒有語言函數時用預設値）
    # ────────────────────────────────────────────────────

    def _t(self, key: str, default: str) -> str:
        if self._get_text:
            try:
                result = self._get_text(key)
                if result and not result.startswith("["):
                    return result
            except Exception:
                pass
        return default

    def _hotkey(self) -> str:
        try:
            # ponytail: SkillTimerModule 透過 parent 鏈取得 app config
            cur = self.parent()
            while cur is not None:
                cfg = getattr(cur, "_app", None)
                if cfg is not None and hasattr(cfg, "config"):
                    hk = cfg.config.get("hotkeys", {}).get("skill_timer", "ins")
                    return str(hk).strip() if isinstance(hk, str) and hk.strip() else "ins"
                cfg2 = getattr(cur, "config", None)
                if isinstance(cfg2, dict) and "hotkeys" in cfg2:
                    hk = cfg2.get("hotkeys", {}).get("skill_timer", "ins")
                    return str(hk).strip() if isinstance(hk, str) and hk.strip() else "ins"
                cur = cur.parent() if hasattr(cur, "parent") else None
        except Exception:
            pass
        return "ins"

    @staticmethod
    def _hotkey_short(hk: str) -> str:
        return hk.replace("ctrl+", "C+").replace("alt+", "A+").upper()

    def _update_toggle_all_btn(self):
        btn = self._btn_toggle_all
        if btn is None:
            return
        hk = self._hotkey()
        hk_full = hk.upper()
        hk_short = self._hotkey_short(hk)
        if self.is_any_running:
            base = self._t("skill_timer_stop_all", "■ 全部停止")
            tip_base = self._t("stop_combo_system_tip", "全部停止")
        else:
            base = self._t("skill_timer_start_all", "▶▶ 全部啟動")
            tip_base = self._t("start_combo_system_tip", "全部啟動")
        btn.setText(f"{base} [{hk_short}]")
        btn.setToolTip(f"{base} [{hk_full}]\n{tip_base}")

    # ────────────────────────────────────────────────────
    #  UI 建構
    # ────────────────────────────────────────────────────

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self.frame = QGroupBox(self._t("skill_timer_title", "⏱ 技能計時器(Beta)"))
        root_layout.addWidget(self.frame)

        grid = QGridLayout(self.frame)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        # 表頭
        headers = [
            self._t("skill_timer_enable", "啟用"),
            self._t("skill_timer_slot", "技能槽"),
            self._t("skill_timer_modifier", "修飾鍵"),
            self._t("skill_timer_key", "按鍵"),
            self._t("skill_timer_interval", "間隔 (ms)"),
            self._t("skill_timer_status", "狀態"),
            "",
        ]
        for col, h in enumerate(headers):
            lbl = QLabel(h)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color: {_COLOR_HEADER}; font-weight: 600;")
            grid.addWidget(lbl, 0, col)

        # 分隔線
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {_COLOR_HEADER};")
        grid.addWidget(sep, 1, 0, 1, len(headers))

        # 每個技能槽列
        for i, slot in enumerate(self.slots):
            row = i + 2

            enabled_check = QCheckBox()
            enabled_check.setStyleSheet("margin-left: 8px;")
            enabled_check.setToolTip(self._t("combo_enabled_tip", "啟用此技能"))
            grid.addWidget(enabled_check, row, 0, Qt.AlignmentFlag.AlignCenter)

            slot_label = QLabel(f"Skill {i + 1}")
            slot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(slot_label, row, 1)

            modifier_combo = ComboBox()
            modifier_combo.addItems(_MODIFIERS)
            modifier_combo.setCurrentText("none")
            modifier_combo.setFixedWidth(90)
            modifier_combo.setToolTip(self._t("trigger_type_tip", "修飾鍵：none / shift / ctrl / alt"))
            grid.addWidget(modifier_combo, row, 2)

            key_edit = QLineEdit()
            key_edit.setMaxLength(2)
            key_edit.setFixedWidth(80)
            key_edit.setToolTip(self._t("trigger_key_tip", "按鍵"))
            grid.addWidget(key_edit, row, 3)

            interval_spin = QSpinBox()
            interval_spin.setRange(_MIN_MS, 60000)
            interval_spin.setSingleStep(50)
            interval_spin.setValue(1000)
            interval_spin.setFixedWidth(90)
            interval_spin.setSuffix(" ms")
            interval_spin.setToolTip(self._t("delay_entry_tip", "間隔時間（毫秒）"))
            grid.addWidget(interval_spin, row, 4)

            status_lbl = QLabel(self._t("skill_timer_stopped", "● 停止"))
            status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_lbl.setStyleSheet(f"color: {_COLOR_OFF}; font-family: Consolas;")
            grid.addWidget(status_lbl, row, 5)

            toggle_btn = PushButton("▶")
            toggle_btn.setFixedWidth(40)
            toggle_btn.setToolTip(self._t("toggle_monitoring_tip", "啟動/停止此技能"))
            toggle_btn.clicked.connect(lambda _=False, s=slot, idx=i: self._toggle(s, idx))
            grid.addWidget(toggle_btn, row, 6)

            self._status_labels.append(status_lbl)
            self._toggle_btns.append(toggle_btn)
            slot.bind_widgets(key_edit, modifier_combo, interval_spin, enabled_check)
            key_edit.textChanged.connect(lambda *_: self._notify_change())
            modifier_combo.currentTextChanged.connect(lambda *_: self._notify_change())
            interval_spin.valueChanged.connect(lambda *_: self._notify_change())
            enabled_check.toggled.connect(lambda *_: self._notify_change())

        # 底部控制列
        ctrl_row = self._n + 2
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {_COLOR_HEADER};")
        grid.addWidget(sep2, ctrl_row, 0, 1, len(headers))

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        self._btn_toggle_all = PushButton(self._t("skill_timer_start_all", "▶▶ 全部啟動"))
        self._btn_toggle_all.clicked.connect(self.toggle_all)
        btn_layout.addWidget(self._btn_toggle_all)
        btn_layout.addStretch(1)
        grid.addLayout(btn_layout, ctrl_row + 1, 0, 1, len(headers))
        self._update_toggle_all_btn()

        if not _PYAUTOGUI_OK:
            warn = QLabel(self._t("skill_timer_no_pyautogui", "⚠ 找不到 pyautogui，請執行： pip install pyautogui"))
            warn.setStyleSheet(f"color: {_COLOR_WARN}; font-family: Consolas; font-size: 11px;")
            grid.addWidget(warn, ctrl_row + 2, 0, 1, len(headers))

        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(5, 1)

    # ────────────────────────────────────────────────────
    #  控制邏輯
    # ────────────────────────────────────────────────────

    def _toggle(self, slot: SkillSlot, idx: int):
        if slot.is_running:
            slot.stop()
            self._set_status(idx, False)
        else:
            if not slot.enabled:
                slot.set_enabled(True)
            ok = slot.start()
            if ok:
                self._set_status(idx, True)
            else:
                QMessageBox.warning(
                    self,
                    self._t("error", "Error"),
                    self._t("skill_timer_error", "Skill {slot}: Key cannot be empty and interval must be ≥ {min}ms").format(slot=idx + 1, min=_MIN_MS),
                )

    def _set_status(self, idx: int, running: bool):
        lbl = self._status_labels[idx]
        btn = self._toggle_btns[idx]
        if running:
            lbl.setText(self._t("skill_timer_running", "● 執行中"))
            lbl.setStyleSheet(f"color: {_COLOR_ON}; font-family: Consolas;")
            btn.setText("■")
        else:
            lbl.setText(self._t("skill_timer_stopped", "● 停止"))
            lbl.setStyleSheet(f"color: {_COLOR_OFF}; font-family: Consolas;")
            btn.setText("▶")

        if self._on_log:
            slot = self.slots[idx]
            mod = slot.modifier
            key = slot.key
            ms = slot.interval_ms
            combo = f"{mod}+{key}" if mod != "none" else key
            if running:
                msg = self._t("skill_timer_log_start", "[SkillTimer] Skill {slot} 啟動 | 按鍵={key} | 間隔={ms}ms")
                msg = msg.format(slot=idx + 1, key=combo, ms=ms)
            else:
                msg = self._t("skill_timer_log_stop", "[SkillTimer] Skill {slot} 停止")
                msg = msg.format(slot=idx + 1)
            self._on_log(msg, "info")

    def start_all(self):
        started = 0
        for i, slot in enumerate(self.slots):
            if slot.enabled and not slot.is_running:
                if slot.start():
                    self._set_status(i, True)
                    started += 1
        if self._on_log:
            msg = self._t("skill_timer_log_all_start", "[SkillTimer] 全部啟動，共 {count} 個技能")
            self._on_log(msg.format(count=started), "info")
        self._update_toggle_all_btn()

    def stop_all(self):
        for i, slot in enumerate(self.slots):
            if slot.is_running:
                slot.stop()
                self._set_status(i, False)
        if self._on_log:
            self._on_log(self._t("skill_timer_log_all_stop", "[SkillTimer] 全部停止"), "info")
        self._update_toggle_all_btn()

    def toggle_all(self):
        """單鍵開關：任一在跑→全停，否則全開（未啟用槽忽略）。"""
        if self.is_any_running:
            self.stop_all()
        else:
            self.start_all()

    def _notify_change(self):
        if self._on_change:
            self._on_change()

    @property
    def is_any_running(self) -> bool:
        return any(s.is_running for s in self.slots)

    @property
    def running_slot_indices(self) -> set[int]:
        return {i for i, s in enumerate(self.slots) if s.is_running}

    def restore_slots(self, indices: set[int]):
        restored = 0
        for i in indices:
            if i < len(self.slots):
                slot = self.slots[i]
                if not slot.is_running and slot.enabled:
                    if slot.start():
                        self._set_status(i, True)
                        restored += 1
        if restored and self._on_log:
            msg = self._t("skill_timer_log_restore", "[SkillTimer] 恢復暫停前的技能槽，共 {count} 個")
            self._on_log(msg.format(count=restored), "info")
        if restored:
            self._update_toggle_all_btn()

    # ────────────────────────────────────────────────────
    #  Config 介面
    # ────────────────────────────────────────────────────

    def refresh_language(self):
        self.frame.setTitle(self._t("skill_timer_title", "⏱ 技能計時器(Beta)"))
        for i, slot in enumerate(self.slots):
            if slot.is_running:
                self._status_labels[i].setText(self._t("skill_timer_running", "● 執行中"))
            else:
                self._status_labels[i].setText(self._t("skill_timer_stopped", "● 停止"))
            if slot._enabled_check is not None:
                slot._enabled_check.setToolTip(self._t("combo_enabled_tip", "啟用此技能"))
            if slot._modifier_combo is not None:
                slot._modifier_combo.setToolTip(self._t("trigger_type_tip", "修飾鍵：none / shift / ctrl / alt"))
            if slot._key_edit is not None:
                slot._key_edit.setToolTip(self._t("trigger_key_tip", "按鍵"))
            if slot._interval_spin is not None:
                slot._interval_spin.setToolTip(self._t("delay_entry_tip", "間隔時間（毫秒）"))
            self._toggle_btns[i].setToolTip(self._t("toggle_monitoring_tip", "啟動/停止此技能"))
        self._update_toggle_all_btn()

    def get_config(self) -> list[dict]:
        return [
            {
                "enabled": slot.enabled,
                "key": slot.key,
                "modifier": slot.modifier,
                "interval_ms": slot.interval_ms,
            }
            for slot in self.slots
        ]

    def load_config(self, config: list[dict]):
        for slot, cfg in zip(self.slots, config):
            try:
                interval_ms = int(cfg.get("interval_ms", 1000))
            except (ValueError, TypeError):
                interval_ms = 1000
            slot.set_ui_value(
                cfg.get("key", ""),
                cfg.get("modifier", "none"),
                interval_ms,
                bool(cfg.get("enabled", False)),
            )

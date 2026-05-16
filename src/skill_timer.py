"""
skill_timer.py
循環計時自動釋放技能模組
────────────────────────────────────────────────────────
設計原則：
- 完全獨立的 class，無外部套件依賴（只用標準庫 + tkinter + pyautogui）
- 每個技能槽各自有獨立 threading.Timer 迴圈，互不干擾
- 支援單鍵（q、w、e、r）和組合鍵（ctrl+1、shift+q）
- 毫秒精度，最低 50ms
- UI 風格與 health_monitor.py 一致（ttk）

────────────────────────────────────────────────────────
接入 health_monitor.py 的方式：

① 在檔案頂部 import：
    from skill_timer import SkillTimerModule

② 在 create_combo_tab() 或新增 create_skill_timer_tab() 裡：
    self.skill_timer = SkillTimerModule(
        parent=self.combo_frame,       # 或任何 ttk.Frame
        on_log=self.add_status_message # 接入狀態記錄
    )
    self.skill_timer.frame.pack(fill="x", padx=5, pady=5)

③ 在 on_closing() 或 close_app() 裡加：
    if hasattr(self, 'skill_timer'):
        self.skill_timer.stop_all()

④ 在 save_config() 裡加：
    if hasattr(self, 'skill_timer'):
        self.config['skill_timer'] = self.skill_timer.get_config()

⑤ 在 load_config() 裡加：
    if hasattr(self, 'skill_timer') and 'skill_timer' in self.config:
        self.skill_timer.load_config(self.config['skill_timer'])
────────────────────────────────────────────────────────
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0
    _PYAUTOGUI_OK = True
except ImportError:
    _PYAUTOGUI_OK = False

# ── 常數 ──────────────────────────────────────────────────
_MIN_MS      = 50                          # 最低間隔 ms
_MAX_SLOTS   = 8                           # 最多技能槽
_MODIFIERS   = ["none", "ctrl", "shift", "alt"]
_COLOR_ON    = "#2ecc71"                   # 執行中（綠）
_COLOR_OFF   = "#e74c3c"                   # 停止（紅）


# ══════════════════════════════════════════════════════════
#  SkillSlot：單一技能槽，負責計時與送鍵
# ══════════════════════════════════════════════════════════
class SkillSlot:
    """
    每個 SkillSlot 持有自己的 tk 變數（直接綁定 UI）
    和一個 threading.Timer 遞迴迴圈。
    """

    def __init__(self, root: tk.Misc):
        """
        root：任何 tk widget，讓 StringVar/IntVar 正確綁到主 Tcl 解釋器。
        """
        self.key         = tk.StringVar(root, value="")
        self.modifier    = tk.StringVar(root, value="none")
        self.interval_ms = tk.IntVar(root, value=1000)
        self.enabled     = tk.BooleanVar(root, value=False)

        self._running = False
        self._timer: threading.Timer | None = None
        self._lock   = threading.Lock()

    # ── 送鍵（在 lock 外部執行，避免死鎖）──

    def _send_key(self):
        if not _PYAUTOGUI_OK:
            return
        key = self.key.get().strip().lower()
        mod = self.modifier.get()
        if not key:
            return
        try:
            if mod == "none":
                pyautogui.press(key)
            else:
                pyautogui.hotkey(mod, key)
        except Exception:
            pass  # 遊戲視窗切走等情況靜默忽略

    # ── 遞迴計時迴圈 ──

    def _loop(self):
        """送鍵 → 排下一次；在 lock 外送鍵避免死鎖"""
        # 先確認還在跑
        with self._lock:
            if not self._running:
                return

        # 送鍵（lock 外）
        self._send_key()

        # 排下一次
        interval_s = max(self.interval_ms.get(), _MIN_MS) / 1000.0
        with self._lock:
            if self._running:
                self._timer = threading.Timer(interval_s, self._loop)
                self._timer.daemon = True
                self._timer.start()

    # ── 公開控制 ──

    def start(self) -> bool:
        """啟動迴圈，回傳 False 代表設定不合法"""
        if not self.key.get().strip():
            return False
        if self.interval_ms.get() < _MIN_MS:
            return False

        with self._lock:
            if self._running:
                return True                    # 已在跑，視為成功
            self._running = True

        # 第一次延遲一個間隔再送鍵，避免立刻誤觸
        interval_s = max(self.interval_ms.get(), _MIN_MS) / 1000.0
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
#  SkillTimerModule：UI 模組
# ══════════════════════════════════════════════════════════
class SkillTimerModule:
    """
    建立一個 ttk.LabelFrame（self.frame），
    可直接 pack / grid 進任何父容器。
    """

    def __init__(self, parent: tk.Misc, max_slots: int = 4,
                 on_log=None, get_text=None):
        """
        parent    : 父容器
        max_slots : 最多幾個技能槽（上限 _MAX_SLOTS）
        on_log    : 可選 callback(message, type)，接 add_status_message
        get_text  : 可選 callback(key) -> str，接語言系統
        """
        self._on_log   = on_log
        self._get_text = get_text  # 語言函數
        self._n        = min(max_slots, _MAX_SLOTS)
        self.slots     = [SkillSlot(parent) for _ in range(self._n)]

        # 儲存 UI 元件引用，供 _set_status 更新
        self._status_labels: list[tk.Label]  = []
        self._toggle_btns:   list[ttk.Button] = []

        # ── 根容器 ──
        title = self._t("skill_timer_title", "⏱ 技能計時器")
        self.frame = ttk.LabelFrame(parent, text=title)
        self._build_ui()

    # ────────────────────────────────────────────────────
    #  輔助：取語言字串（沒有語言函數時用預設値）
    # ────────────────────────────────────────────────────

    def _t(self, key: str, default: str) -> str:
        """如果有語言函數就用它，沒有就用預設値"""
        if self._get_text:
            try:
                result = self._get_text(key)
                # 避免語言系統回傳 [key] 樣式的未定義字串
                if result and not result.startswith('['):
                    return result
            except Exception:
                pass
        return default

    # ────────────────────────────────────────────────────
    #  UI 建構
    # ────────────────────────────────────────────────────

    def _build_ui(self):
        f = self.frame

        # 表頭
        headers = [
            self._t("skill_timer_enable",   "啟用"),
            self._t("skill_timer_slot",     "技能槽"),
            self._t("skill_timer_modifier", "修飾鍵"),
            self._t("skill_timer_key",      "按鍵"),
            self._t("skill_timer_interval", "間隔 (ms)"),
            self._t("skill_timer_status",   "狀態"),
            "",
        ]
        widths  = [4,      7,       9,       8,     10,        10,   5]
        for col, (h, w) in enumerate(zip(headers, widths)):
            ttk.Label(f, text=h, width=w, anchor="center",
                      foreground="#555555"
                      ).grid(row=0, column=col, padx=3, pady=(6, 2), sticky="ew")

        # 分隔線（用空 Frame 模擬）
        ttk.Separator(f, orient="horizontal").grid(
            row=1, column=0, columnspan=len(headers),
            sticky="ew", padx=3, pady=2
        )

        # 每個技能槽列
        for i, slot in enumerate(self.slots):
            row = i + 2

            # 啟用 Checkbutton
            ttk.Checkbutton(f, variable=slot.enabled
                            ).grid(row=row, column=0, padx=4, pady=3)

            # 槽標籤
            ttk.Label(f, text=f"Skill {i + 1}", width=7, anchor="center"
                      ).grid(row=row, column=1, padx=3)

            # 修飾鍵
            ttk.Combobox(f, textvariable=slot.modifier,
                         values=_MODIFIERS, state="readonly", width=8
                         ).grid(row=row, column=2, padx=3)

            # 按鍵輸入
            ttk.Entry(f, textvariable=slot.key, width=8
                      ).grid(row=row, column=3, padx=3)

            # 間隔 ms
            ttk.Entry(f, textvariable=slot.interval_ms, width=10
                      ).grid(row=row, column=4, padx=3)

            # 狀態燈（用 tk.Label 才能改背景色）
            stopped_text = self._t("skill_timer_stopped", "● 停止")
            lbl = tk.Label(f, text=stopped_text, width=10,
                           fg=_COLOR_OFF,
                           font=("Consolas", 9))
            lbl.grid(row=row, column=5, padx=3)
            self._status_labels.append(lbl)

            # 獨立啟停按鈕
            btn = ttk.Button(
                f, text="▶", width=4,
                command=lambda s=slot, idx=i: self._toggle(s, idx)
            )
            btn.grid(row=row, column=6, padx=3)
            self._toggle_btns.append(btn)

        # 底部控制列
        ctrl_row = self._n + 2
        ttk.Separator(f, orient="horizontal").grid(
            row=ctrl_row, column=0, columnspan=7,
            sticky="ew", padx=3, pady=(6, 3)
        )

        btn_frame = ttk.Frame(f)
        btn_frame.grid(row=ctrl_row + 1, column=0, columnspan=7,
                       sticky="w", padx=6, pady=(0, 8))

        self._btn_start_all = ttk.Button(btn_frame, text=self._t("skill_timer_start_all", "▶▶ 全部啟動"),
                                          command=self.start_all)
        self._btn_start_all.pack(side="left", padx=(0, 8))

        self._btn_stop_all = ttk.Button(btn_frame, text=self._t("skill_timer_stop_all", "■ 全部停止"),
                                        command=self.stop_all)
        self._btn_stop_all.pack(side="left")

        # pyautogui 缺失警告
        if not _PYAUTOGUI_OK:
            warn = tk.Label(
                f,
                text="⚠ 找不到 pyautogui，請執行：pip install pyautogui",
                fg="#e67e22", font=("Consolas", 8)
            )
            warn.grid(row=ctrl_row + 2, column=0, columnspan=7,
                      sticky="w", padx=6, pady=(0, 4))

    # ────────────────────────────────────────────────────
    #  控制邏輯
    # ────────────────────────────────────────────────────

    def _toggle(self, slot: SkillSlot, idx: int):
        """單一槽啟停切換"""
        if slot.is_running:
            slot.stop()
            self._set_status(idx, False)
        else:
            # 自動勾選啟用
            if not slot.enabled.get():
                slot.enabled.set(True)
            ok = slot.start()
            if ok:
                self._set_status(idx, True)
            else:
                messagebox.showwarning(
                    "設定錯誤",
                    f"Skill {idx + 1}：\n"
                    f"• 請確認「按鍵」欄位不為空\n"
                    f"• 間隔需 ≥ {_MIN_MS} ms"
                )

    def _set_status(self, idx: int, running: bool):
        lbl = self._status_labels[idx]
        btn = self._toggle_btns[idx]
        if running:
            lbl.config(text=self._t("skill_timer_running", "● 執行中"), fg=_COLOR_ON)
            btn.config(text="■")
        else:
            lbl.config(text=self._t("skill_timer_stopped", "● 停止"), fg=_COLOR_OFF)
            btn.config(text="▶")

        if self._on_log:
            slot  = self.slots[idx]
            mod   = slot.modifier.get()
            key   = slot.key.get()
            ms    = slot.interval_ms.get()
            combo = f"{mod}+{key}" if mod != "none" else key
            if running:
                msg = self._t("skill_timer_log_start", "[SkillTimer] Skill {slot} 啟動 | 按鍵={key} | 間隔={ms}ms")
                msg = msg.format(slot=idx+1, key=combo, ms=ms)
            else:
                msg = self._t("skill_timer_log_stop", "[SkillTimer] Skill {slot} 停止")
                msg = msg.format(slot=idx+1)
            self._on_log(msg, "info")

    def start_all(self):
        """啟動所有勾選啟用且尚未跑的槽"""
        started = 0
        for i, slot in enumerate(self.slots):
            if slot.enabled.get() and not slot.is_running:
                if slot.start():
                    self._set_status(i, True)
                    started += 1
        if self._on_log:
            msg = self._t("skill_timer_log_all_start", "[SkillTimer] 全部啟動，共 {count} 個技能")
            self._on_log(msg.format(count=started), "info")

    def stop_all(self):
        """停止所有計時器"""
        for i, slot in enumerate(self.slots):
            if slot.is_running:
                slot.stop()
                self._set_status(i, False)
        if self._on_log:
            self._on_log(self._t("skill_timer_log_all_stop", "[SkillTimer] 全部停止"), "info")

    # ────────────────────────────────────────────────────
    #  Config 介面（接 health_monitor 的 save/load_config）
    # ────────────────────────────────────────────────────

    def refresh_language(self):
        """語言切換時更新所有 UI 文字"""
        # 更新 LabelFrame 標題
        self.frame.config(text=self._t("skill_timer_title", "⏱ 技能計時器"))
        # 更新層技能槽狀態燈
        for i, slot in enumerate(self.slots):
            if slot.is_running:
                self._status_labels[i].config(text=self._t("skill_timer_running", "● 執行中"))
            else:
                self._status_labels[i].config(text=self._t("skill_timer_stopped", "● 停止"))
        # 更新底部按鈕
        self._btn_start_all.config(text=self._t("skill_timer_start_all", "▶▶ 全部啟動"))
        self._btn_stop_all.config(text=self._t("skill_timer_stop_all", "■ 全部停止"))

    def get_config(self) -> list[dict]:
        return [
            {
                "enabled":     slot.enabled.get(),
                "key":         slot.key.get(),
                "modifier":    slot.modifier.get(),
                "interval_ms": slot.interval_ms.get(),
            }
            for slot in self.slots
        ]

    def load_config(self, config: list[dict]):
        for slot, cfg in zip(self.slots, config):
            slot.enabled.set(cfg.get("enabled", False))
            slot.key.set(cfg.get("key", ""))
            slot.modifier.set(cfg.get("modifier", "none"))
            try:
                slot.interval_ms.set(int(cfg.get("interval_ms", 1000)))
            except (ValueError, tk.TclError):
                slot.interval_ms.set(1000)


# ══════════════════════════════════════════════════════════
#  獨立測試（直接執行此檔案）
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    root = tk.Tk()
    root.title("SkillTimerModule 獨立測試")

    log_text = tk.Text(root, height=6, width=60, state="disabled",
                       font=("Consolas", 9))
    log_text.pack(padx=10, pady=(0, 4), fill="x")

    def on_log(msg, typ="info"):
        log_text.config(state="normal")
        log_text.insert("end", msg + "\n")
        log_text.see("end")
        log_text.config(state="disabled")

    module = SkillTimerModule(root, max_slots=4, on_log=on_log)
    module.frame.pack(padx=10, pady=10, fill="x")

    def on_close():
        module.stop_all()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

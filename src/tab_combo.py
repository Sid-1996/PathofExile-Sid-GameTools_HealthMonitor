import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import os
import json
import functools
import pyautogui
import keyboard
from ctypes import windll
from skill_timer import SkillTimerModule
from utils import Tooltip

SendMessageW = windll.user32.SendMessageW
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101


class ComboTab:
    def __init__(self, app, state, parent_frame):
        self._app = app
        self._state = state
        self.parent_frame = parent_frame
        self.combo_ui_refs = []
        self.combo_canvas = None
        self.combo_start_btn = None
        self.combo_stop_btn = None
        self.combo_status_label = None
        self.skill_timer = None
        self.create_combo_tab()

    def create_combo_tab(self):
        main_frame = self.parent_frame

        _combo_canvas = tk.Canvas(main_frame, highlightthickness=0)
        _combo_scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=_combo_canvas.yview)
        _combo_scrollable = ttk.Frame(_combo_canvas)

        _combo_scrollable.bind(
            "<Configure>",
            lambda e: _combo_canvas.configure(scrollregion=_combo_canvas.bbox("all"))
        )

        _combo_canvas_window = _combo_canvas.create_window((0, 0), window=_combo_scrollable, anchor="nw")
        _combo_canvas.configure(yscrollcommand=_combo_scrollbar.set)

        def _on_combo_canvas_resize(event):
            _combo_canvas.itemconfig(_combo_canvas_window, width=event.width)
        _combo_canvas.bind("<Configure>", _on_combo_canvas_resize)

        _combo_scrollbar.pack(side="right", fill="y")
        _combo_canvas.pack(side="left", fill="both", expand=True)
        self.combo_canvas = _combo_canvas
        main_frame = _combo_scrollable

        title_label = ttk.Label(main_frame, text=self._app.get_text("skill_combo_system_title"), font=('Microsoft YaHei', 20, 'bold'))
        title_label.pack(pady=(15, 25))

        # 左右雙欄佈局
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(content_frame)
        left_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))

        right_frame = ttk.Frame(content_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.N, tk.S, tk.W, tk.E), padx=(10, 0))

        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)

        # === 左欄：連段套組（Notebook 分頁）+ 控制區 ===
        self.initialize_combo_sets()

        notebook = ttk.Notebook(left_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        for i in range(3):
            tab_frame = ttk.Frame(notebook, padding="10")
            notebook.add(tab_frame, text=f"套組 {i + 1}")
            self.create_combo_set_frame_horizontal(tab_frame, i)

        # 控制區
        control_frame = ttk.LabelFrame(left_frame, text=self._app.get_text("global_control"), padding="15")
        control_frame.pack(fill=tk.X, pady=(10, 0))

        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=(0, 8))

        self.combo_start_btn = ttk.Button(button_frame, text=self._app.get_text("start_combo_system"),
                                        command=self.start_combo_system, width=18)
        self.combo_start_btn.pack(side=tk.LEFT, padx=(0, 10))
        Tooltip(self.combo_start_btn, self._app.get_text("start_combo_system_tip"))

        self.combo_stop_btn = ttk.Button(button_frame, text=self._app.get_text("stop_combo_system"),
                                       command=self.stop_combo_system, state=tk.DISABLED, width=18)
        self.combo_stop_btn.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(button_frame, text=self._app.get_text("save_combo_settings"), command=self.save_combo_config, width=12).pack(side=tk.LEFT)

        status_frame = ttk.Frame(control_frame)
        status_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(status_frame, text=self._app.get_text("system_status"), font=('Microsoft YaHei', 12, 'bold')).pack(side=tk.LEFT)
        self.combo_status_label = ttk.Label(status_frame, text=self._app.get_text("not_started"), foreground="red", font=('Microsoft YaHei', 12))
        self.combo_status_label.pack(side=tk.LEFT, padx=(8, 0))

        # === 右欄：技能計時器 + 使用提示 ===
        if not hasattr(self._app, 'skill_timer'):
            self.skill_timer = SkillTimerModule(
                parent=right_frame,
                max_slots=4,
                on_log=self._app.status_tab.add_status_message,
                get_text=self._app.get_text
            )
            self.skill_timer.frame.pack(fill="x", padx=5, pady=(5, 10))
            self._app.skill_timer = self.skill_timer

        help_frame = ttk.LabelFrame(right_frame, text=self._app.get_text("usage_instructions"), padding="10")
        help_frame.pack(fill=tk.X, pady=(10, 0))

        help_text = self._app.get_text("skill_combo_usage_title") + "\n\n" + self._app.get_text("skill_combo_usage_content")
        help_label = ttk.Label(help_frame, text=help_text, justify=tk.LEFT,
                             font=('Arial', 9), foreground="gray", wraplength=400)
        help_label.pack(anchor=tk.W)

    def initialize_combo_sets(self):
        if not self._state.combo_sets:
            for i in range(3):
                combo_set = {
                    'trigger_key': 'Q' if i == 0 else 'W' if i == 1 else 'E',
                    'trigger_delay': '',
                    'combo_keys': ['', '', '', '', ''],
                    'delays': ['', '', '', '', ''],
                    'stationary_attacks': [False, False, False, False, False],
                }
                self._state.combo_sets.append(combo_set)

    def create_combo_set_frame_horizontal(self, parent, set_index):
        set_frame = ttk.Frame(parent)
        set_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))

        if len(self.combo_ui_refs) <= set_index:
            self.combo_ui_refs.extend([{}] * (set_index + 1 - len(self.combo_ui_refs)))

        enabled_var = tk.BooleanVar(value=self._state.combo_enabled[set_index])
        enabled_check = ttk.Checkbutton(set_frame, text=self._app.get_text("enable_this_set"),
                                      variable=enabled_var,
                                      command=functools.partial(self.toggle_combo_set, set_index, enabled_var))
        enabled_check.grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(0, 15))
        self.combo_ui_refs[set_index]['enabled_var'] = enabled_var
        trigger_frame = ttk.Frame(set_frame)
        trigger_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 15))

        ttk.Label(trigger_frame, text=self._app.get_text("trigger_skill"), font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W)
        trigger_var = tk.StringVar(value=self._state.combo_sets[set_index]['trigger_key'])
        trigger_combo = ttk.Combobox(trigger_frame, textvariable=trigger_var,
                                   values=['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P',
                                           'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L',
                                           'Z', 'X', 'C', 'V', 'B', 'N', 'M',
                                           '1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
                                   state="readonly", width=10, font=('Arial', 10))
        trigger_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        trigger_combo.bind("<<ComboboxSelected>>",
                         functools.partial(self.update_trigger_key, set_index, trigger_var))
        self.combo_ui_refs[set_index]['trigger_var'] = trigger_var

        ttk.Label(trigger_frame, text=self._app.get_text("initial_delay_ms"), font=('Arial', 10, 'bold')).grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        trigger_delay_var = tk.StringVar(value=self._state.combo_sets[set_index]['trigger_delay'])
        trigger_delay_entry = ttk.Entry(trigger_frame, textvariable=trigger_delay_var, width=8, font=('Arial', 10))
        trigger_delay_entry.grid(row=0, column=3, sticky=tk.W, padx=(10, 0))
        trigger_delay_entry.bind("<KeyRelease>",
                               functools.partial(self.update_trigger_delay, set_index, trigger_delay_var))
        self.combo_ui_refs[set_index]['trigger_delay_var'] = trigger_delay_var

        skills_frame = ttk.LabelFrame(set_frame, text=self._app.get_text("combo_skill_settings"), padding="10")
        skills_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 10))

        for i in range(5):
            row_label = self._app.get_text("skill_template").format(number=i+1)
            ttk.Label(skills_frame, text=row_label, font=('Arial', 9, 'bold')).grid(row=i, column=0, sticky=tk.W, pady=3)

            key_var = tk.StringVar(value=self._state.combo_sets[set_index]['combo_keys'][i] if self._state.combo_sets[set_index]['combo_keys'][i] else 'off')
            key_combo = ttk.Combobox(skills_frame, textvariable=key_var,
                                   values=['off', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P',
                                           'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L',
                                           'Z', 'X', 'C', 'V', 'B', 'N', 'M',
                                           '1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
                                   state="readonly", width=6, font=('Arial', 9))
            key_combo.grid(row=i, column=1, sticky=tk.W, padx=(5, 0), pady=3)
            key_combo.bind("<<ComboboxSelected>>",
                         functools.partial(self.update_combo_key, set_index, i, key_var))

            ttk.Label(skills_frame, text=self._app.get_text("delay_ms"), font=('Arial', 9)).grid(row=i, column=2, sticky=tk.W, padx=(15, 0), pady=3)

            delay_var = tk.StringVar(value=self._state.combo_sets[set_index]['delays'][i] if self._state.combo_sets[set_index]['delays'][i] else '')
            delay_entry = ttk.Entry(skills_frame, textvariable=delay_var, width=8, font=('Arial', 9))
            delay_entry.grid(row=i, column=3, sticky=tk.W, padx=(5, 0), pady=3)
            delay_entry.bind("<KeyRelease>",
                           functools.partial(self.update_combo_delay, set_index, i, delay_var))

            stationary_var = tk.BooleanVar(value=self._state.combo_sets[set_index]['stationary_attacks'][i])
            stationary_check = ttk.Checkbutton(skills_frame, text=self._app.get_text("stationary_attack"), variable=stationary_var,
                                             command=functools.partial(self.update_stationary_attack, set_index, i, stationary_var))
            stationary_check.grid(row=i, column=4, sticky=tk.W, padx=(15, 0), pady=3)
            Tooltip(stationary_check, self._app.get_text("stationary_attack_tip"))

            ttk.Label(skills_frame, text=self._app.get_text("shift_skill_note"), font=('Arial', 8), foreground="gray").grid(
                row=i, column=5, sticky=tk.W, padx=(5, 0), pady=3)

            if 'key_vars' not in self.combo_ui_refs[set_index]:
                self.combo_ui_refs[set_index]['key_vars'] = []
                self.combo_ui_refs[set_index]['delay_vars'] = []
                self.combo_ui_refs[set_index]['stationary_vars'] = []

            if len(self.combo_ui_refs[set_index]['key_vars']) <= i:
                self.combo_ui_refs[set_index]['key_vars'].extend([''] * (i + 1 - len(self.combo_ui_refs[set_index]['key_vars'])))
                self.combo_ui_refs[set_index]['delay_vars'].extend([''] * (i + 1 - len(self.combo_ui_refs[set_index]['delay_vars'])))
                self.combo_ui_refs[set_index]['stationary_vars'].extend([None] * (i + 1 - len(self.combo_ui_refs[set_index]['stationary_vars'])))

            self.combo_ui_refs[set_index]['key_vars'][i] = key_var
            self.combo_ui_refs[set_index]['delay_vars'][i] = delay_var
            self.combo_ui_refs[set_index]['stationary_vars'][i] = stationary_var
        set_frame.columnconfigure(0, weight=1)
        set_frame.columnconfigure(1, weight=1)
        set_frame.columnconfigure(2, weight=1)
        set_frame.columnconfigure(3, weight=1)
        set_frame.columnconfigure(4, weight=1)
        set_frame.columnconfigure(5, weight=1)

        skills_frame.columnconfigure(0, weight=0)
        skills_frame.columnconfigure(1, weight=0)
        skills_frame.columnconfigure(2, weight=0)
        skills_frame.columnconfigure(3, weight=0)
        skills_frame.columnconfigure(4, weight=0)
        skills_frame.columnconfigure(5, weight=1)

    def toggle_combo_set(self, set_index, enabled_var, event=None):
        self._state.combo_enabled[set_index] = enabled_var.get()
        print(f"連段套組 {set_index + 1} {'啟用' if enabled_var.get() else '停用'}")

    def update_trigger_key(self, set_index, trigger_var, event=None):
        self._state.combo_sets[set_index]['trigger_key'] = trigger_var.get()
        print(f"連段套組 {set_index + 1} 觸發鍵更新為: {trigger_var.get()}")

    def update_trigger_delay(self, set_index, trigger_delay_var, event=None):
        delay_text = trigger_delay_var.get().strip()
        if delay_text == '':
            self._state.combo_sets[set_index]['trigger_delay'] = ''
            return

        try:
            delay = int(delay_text)
            if delay < 0:
                delay = 0
            elif delay > 5000:
                delay = 5000
            self._state.combo_sets[set_index]['trigger_delay'] = delay
            trigger_delay_var.set(str(delay))
        except ValueError:
            trigger_delay_var.set(str(self._state.combo_sets[set_index]['trigger_delay']) if self._state.combo_sets[set_index]['trigger_delay'] else '')

    def update_combo_key(self, set_index, key_index, key_var, event=None):
        self._state.combo_sets[set_index]['combo_keys'][key_index] = key_var.get()
        print(f"連段套組 {set_index + 1} 技能{key_index + 1} 更新為: {key_var.get()}")

    def update_combo_delay(self, set_index, delay_index, delay_var, event=None):
        delay_text = delay_var.get().strip()
        if delay_text == '':
            self._state.combo_sets[set_index]['delays'][delay_index] = ''
            return

        try:
            delay = int(delay_text)
            if delay < 0:
                delay = 0
            elif delay > 5000:
                delay = 5000
            self._state.combo_sets[set_index]['delays'][delay_index] = delay
            delay_var.set(str(delay))
        except ValueError:
            delay_var.set(str(self._state.combo_sets[set_index]['delays'][delay_index]) if self._state.combo_sets[set_index]['delays'][delay_index] else '')

    def update_stationary_attack(self, set_index, skill_index, stationary_var):
        self._state.combo_sets[set_index]['stationary_attacks'][skill_index] = stationary_var.get()
        status = "啟用" if stationary_var.get() else "停用"
        print(f"連段套組 {set_index + 1} 技能{skill_index + 1} 原地攻擊: {status}")

    def update_combo_ui_from_config(self):
        try:
            while len(self.combo_ui_refs) < len(self._state.combo_sets):
                self.combo_ui_refs.append({})

            for set_index in range(len(self._state.combo_sets)):
                if set_index < len(self.combo_ui_refs):
                    ui_refs = self.combo_ui_refs[set_index]

                    if 'enabled_var' in ui_refs and set_index < len(self._state.combo_enabled):
                        ui_refs['enabled_var'].set(self._state.combo_enabled[set_index])

                    if 'trigger_var' in ui_refs:
                        ui_refs['trigger_var'].set(self._state.combo_sets[set_index]['trigger_key'])

                    if 'trigger_delay_var' in ui_refs:
                        ui_refs['trigger_delay_var'].set(str(self._state.combo_sets[set_index]['trigger_delay']) if self._state.combo_sets[set_index]['trigger_delay'] else '')

                    if 'key_vars' in ui_refs and 'delay_vars' in ui_refs and 'stationary_vars' in ui_refs:
                        for i in range(len(self._state.combo_sets[set_index]['combo_keys'])):
                            if i < len(ui_refs['key_vars']):
                                ui_refs['key_vars'][i].set(self._state.combo_sets[set_index]['combo_keys'][i] if self._state.combo_sets[set_index]['combo_keys'][i] else 'off')
                            if i < len(ui_refs['delay_vars']):
                                ui_refs['delay_vars'][i].set(str(self._state.combo_sets[set_index]['delays'][i]) if self._state.combo_sets[set_index]['delays'][i] else '')
                            if i < len(ui_refs['stationary_vars']) and i < len(self._state.combo_sets[set_index]['stationary_attacks']):
                                ui_refs['stationary_vars'][i].set(self._state.combo_sets[set_index]['stationary_attacks'][i])

            print("組合UI元件已從設定更新")
        except Exception as e:
            print(f"更新組合UI元件時發生錯誤: {e}")

    def start_combo_system(self):
        if self._state.is_combo_running():
            messagebox.showwarning(self._app.get_text("warning"), self._app.get_text("combo_system_already_running"))
            return

        enabled_sets = [i for i, enabled in enumerate(self._state.combo_enabled) if enabled]
        if not enabled_sets:
            messagebox.showwarning(self._app.get_text("warning"), self._app.get_text("enable_at_least_one_combo_set"))
            return

        for i in enabled_sets:
            combo_set = self._state.combo_sets[i]
            if not combo_set['trigger_key']:
                messagebox.showerror("錯誤", f"連段套組 {i+1} 的觸發技能未設定")
                return
            has_combo = any(key for key in combo_set['combo_keys'] if key and key != 'off' and key != '')
            if not has_combo:
                messagebox.showerror("錯誤", f"連段套組 {i+1} 沒有設定任何連段技能")
                return

        self._state.set_combo_running(True)
        self._state.combo_thread = threading.Thread(target=self.run_combo_system, daemon=True)
        self._state.combo_thread.start()

        self.combo_start_btn.config(state=tk.DISABLED)
        self.combo_stop_btn.config(state=tk.NORMAL)
        self.combo_status_label.config(text=self._app.get_text("combo_running"), foreground="green")

        enabled_count = len(enabled_sets)
        self._app.status_tab.add_status_message(self._app.get_text("combo_system_started").format(count=enabled_count), "success")
        print("技能連段系統已啟動")

    def stop_combo_system(self):
        if not self._state.is_combo_running():
            return

        print("[STOP] 正在停止連段系統...")
        self._state.set_combo_running(False)

        self._state.wait_combo_stopped(timeout=2.0)

        for hotkey in self._state.combo_hotkeys.values():
            try:
                keyboard.remove_hotkey(hotkey)
            except Exception:
                pass
        self._state.combo_hotkeys.clear()

        self.combo_start_btn.config(state=tk.NORMAL)
        self.combo_stop_btn.config(state=tk.DISABLED)
        self.combo_status_label.config(text=self._app.get_text("combo_stopped"), foreground="red")

        self._app.status_tab.add_status_message("技能連擊系統已停止", "info")
        print("[STOP] 連段系統已完全停止")

    def restart_combo_system_silently(self):
        if self._state.is_combo_running():
            return

        enabled_sets = [i for i, enabled in enumerate(self._state.combo_enabled) if enabled]
        if not enabled_sets:
            raise Exception("沒有啟用的連段套組")

        for i in enabled_sets:
            combo_set = self._state.combo_sets[i]
            if not combo_set['trigger_key']:
                raise Exception(f"連段套組 {i+1} 的觸發技能未設定")
            has_combo = any(key for key in combo_set['combo_keys'] if key and key != 'off' and key != '')
            if not has_combo:
                raise Exception(f"連段套組 {i+1} 沒有設定任何連段技能")

        self._state.set_combo_running(True)
        self._state.combo_thread = threading.Thread(target=self.run_combo_system, daemon=True)
        self._state.combo_thread.start()

        try:
            if self.combo_start_btn:
                self.combo_start_btn.config(state=tk.DISABLED)
            if self.combo_stop_btn:
                self.combo_stop_btn.config(state=tk.NORMAL)
            if self.combo_status_label:
                self.combo_status_label.config(text=self._app.get_text("combo_running"), foreground="green")
        except Exception:
            pass

    def run_combo_system(self):
        print("連段系統線程已啟動")

        for i, enabled in enumerate(self._state.combo_enabled):
            if enabled:
                trigger_key = self._state.combo_sets[i]['trigger_key'].lower()
                try:
                    from functools import partial
                    hotkey_id = keyboard.add_hotkey(trigger_key,
                                                  partial(self.execute_combo, i),
                                                  suppress=False)
                    self._state.combo_hotkeys[f"combo_{i}"] = hotkey_id
                    print(f"註冊快捷鍵: {trigger_key} -> 連段套組 {i+1}")
                except Exception as e:
                    print(f"註冊快捷鍵失敗 {trigger_key}: {e}")

        while self._state.is_combo_running():
            time.sleep(0.1)

        print("連段系統線程已結束")

    def execute_combo(self, set_index):
        if not self._state.is_combo_running():
            return

        if self._app.monitor_tab.window_var.get():
            if not self._app.window_key_sender.is_game_window_foreground(self._app.monitor_tab.window_var.get()):
                print(f"遊戲視窗 '{self._app.monitor_tab.window_var.get()}' 不在前台，跳過連段執行")
                return

        combo_set = self._state.combo_sets[set_index]
        combo_keys = combo_set['combo_keys']
        delays = combo_set['delays']
        trigger_delay = combo_set.get('trigger_delay', '')
        trigger_key = combo_set.get('trigger_key', '')

        valid_keys = [key for key in combo_keys if key and key != 'off' and key != '']

        self._app.status_tab.add_status_message(self._app.get_text("combo_trigger_detected").format(
            set=set_index + 1, key=trigger_key, count=len(valid_keys)), "monitor")

        if valid_keys:
            skills_text = " | ".join([f"{i+1}:{key}" for i, key in enumerate(valid_keys)])
            self._app.status_tab.add_status_message(self._app.get_text("combo_skill_sequence").format(sequence=skills_text), "monitor")
        print(f"執行連段套組 {set_index + 1}: {valid_keys}")

        if trigger_delay and trigger_delay != 'off' and trigger_delay != '':
            try:
                delay_ms = int(trigger_delay)
                if delay_ms > 0:
                    delay = delay_ms / 1000.0
                    self._app.status_tab.add_status_message(self._app.get_text("combo_trigger_delay").format(delay=delay_ms), "info")
                    print(f"  觸發延遲: {delay_ms}ms")
                    time.sleep(delay)
            except (ValueError, TypeError):
                pass

        for i, key in enumerate(combo_keys):
            if not key or key == 'off' or key == '' or not self._state.is_combo_running():
                if not self._state.is_combo_running():
                    self._app.status_tab.add_status_message(f"⏹️ 連擊套組 {set_index + 1} 被中斷", "warning")
                    print(f"連段套組 {set_index + 1} 被中斷")
                    return
                continue

            try:
                is_stationary = combo_set.get('stationary_attacks', [False] * 5)[i]

                game_hwnd = self._app.window_key_sender.get_game_window_handle()
                if game_hwnd:
                    if is_stationary:
                        shift_vk = self._app.window_key_sender.map_key_to_vk_code('shift')
                        skill_vk = self._app.window_key_sender.map_key_to_vk_code(key.lower())

                        if shift_vk and skill_vk:
                            SendMessageW(game_hwnd, WM_KEYDOWN, shift_vk, 0)
                            time.sleep(0.01)
                            SendMessageW(game_hwnd, WM_KEYDOWN, skill_vk, 0)
                            time.sleep(0.01)
                            SendMessageW(game_hwnd, WM_KEYUP, skill_vk, 0)
                            time.sleep(0.01)
                            SendMessageW(game_hwnd, WM_KEYUP, shift_vk, 0)

                            self._app.status_tab.add_status_message(self._app.get_text("combo_skill_execution").format(
                                index=i+1, skill=f"Shift+{key}", type=self._app.get_text("stationary_attack"), method=self._app.get_text("selective_send")), "success")
                            print(f"  原地攻擊模式: Shift+{key} (發送到遊戲窗口)")
                        else:
                            pyautogui.keyDown('shift')
                            pyautogui.press(key.lower())
                            pyautogui.keyUp('shift')
                            self._app.status_tab.add_status_message(self._app.get_text("combo_skill_execution").format(
                                index=i+1, skill=f"Shift+{key}", type=self._app.get_text("stationary_attack"), method=self._app.get_text("global_send")), "warning")
                            print(f"  原地攻擊模式: Shift+{key} (全局按鍵)")
                    else:
                        vk_code = self._app.window_key_sender.map_key_to_vk_code(key.lower())
                        if vk_code:
                            self._app.window_key_sender.send_key_to_window_combo(game_hwnd, vk_code)
                            self._app.status_tab.add_status_message(self._app.get_text("combo_skill_execution").format(
                                index=i+1, skill=key, type=self._app.get_text("normal_attack"), method=self._app.get_text("selective_send")), "success")
                            print(f"  [SKILL] 技能連段選擇性按下技能鍵: {key} (發送到遊戲窗口)")
                        else:
                            pyautogui.press(key.lower())
                            self._app.status_tab.add_status_message(self._app.get_text("combo_skill_execution").format(
                                index=i+1, skill=key, type=self._app.get_text("normal_attack"), method=self._app.get_text("global_send")), "warning")
                            print(f"  [SKILL] 技能連段全局按下技能鍵: {key} (鍵碼映射失敗)")
                else:
                    if is_stationary:
                        pyautogui.keyDown('shift')
                        pyautogui.press(key.lower())
                        pyautogui.keyUp('shift')
                        self._app.status_tab.add_status_message(self._app.get_text("combo_skill_execution").format(
                            index=i+1, skill=f"Shift+{key}", type=self._app.get_text("stationary_attack"), method=self._app.get_text("global_send")), "warning")
                        print(f"  原地攻擊模式: Shift+{key} (全局按鍵)")
                    else:
                        pyautogui.press(key.lower())
                        self._app.status_tab.add_status_message(self._app.get_text("combo_skill_execution").format(
                            index=i+1, skill=key, type=self._app.get_text("normal_attack"), method=self._app.get_text("global_send")), "warning")
                        print(f"  全局按下技能鍵: {key} (無法獲取窗口句柄)")
            except Exception as e:
                self._app.status_tab.add_status_message(f"❌ 技能 {i+1}: {key} 執行失敗 - {str(e)}", "error")
                print(f"  按鍵模擬失敗 {key}: {e}")
                continue

            if i < len(combo_keys) - 1 and delays[i] and delays[i] != 'off':
                try:
                    delay_ms = int(delays[i])
                    if delay_ms > 0:
                        delay = delay_ms / 1000.0
                        self._app.status_tab.add_status_message(self._app.get_text("combo_skill_delay").format(delay=delay_ms), "info")
                        time.sleep(delay)
                        print(f"  延遲: {delay_ms}ms")
                except (ValueError, TypeError):
                    pass

        print(f"連段套組 {set_index + 1} 執行完成")

        self._app.status_tab.add_status_message(self._app.get_text("combo_completed").format(
            set=set_index + 1, key=trigger_key, count=len(valid_keys)), "success")

    def save_combo_config(self):
        try:
            config = {
                'combo_sets': self._state.combo_sets,
                'combo_enabled': self._state.combo_enabled
            }

            if os.path.exists(self._app.config_file):
                with open(self._app.config_file, 'r', encoding='utf-8') as f:
                    existing_config = json.load(f)
            else:
                existing_config = {}

            existing_config.update(config)

            if self.skill_timer:
                existing_config['skill_timer'] = self.skill_timer.get_config()

            with open(self._app.config_file, 'w', encoding='utf-8') as f:
                json.dump(existing_config, f, indent=4, ensure_ascii=False)

            messagebox.showinfo("成功", "連段設定已儲存")
            print("連段設定已儲存")

        except Exception as e:
            messagebox.showerror("錯誤", f"儲存連段設定失敗: {str(e)}")
            print(f"儲存連段設定失敗: {e}")

    def load_combo_config(self):
        try:
            if not os.path.exists(self._app.config_file):
                messagebox.showinfo("提示", "沒有找到設定檔案，使用預設設定")
                return

            with open(self._app.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            if 'combo_sets' in config:
                self._state.combo_sets = config['combo_sets']
                for combo_set in self._state.combo_sets:
                    if 'trigger_delay' not in combo_set:
                        combo_set['trigger_delay'] = ''
                    if 'stationary_attacks' not in combo_set:
                        combo_set['stationary_attacks'] = [False, False, False, False, False]

                while len(self._state.combo_sets) < 3:
                    self._state.combo_sets.append({
                        'trigger_key': 'Q' if len(self._state.combo_sets) == 0 else 'W' if len(self._state.combo_sets) == 1 else 'E',
                        'trigger_delay': '',
                        'combo_keys': ['', '', '', '', ''],
                        'delays': ['', '', '', '', ''],
                        'stationary_attacks': [False, False, False, False, False],
                    })

            if 'combo_enabled' in config:
                self._state.combo_enabled = config['combo_enabled']
                while len(self._state.combo_enabled) < 3:
                    self._state.combo_enabled.append(True if len(self._state.combo_enabled) == 0 else False)

            if self.skill_timer and 'skill_timer' in config:
                self.skill_timer.load_config(config['skill_timer'])

        except Exception as e:
            print(f"載入連段設定失敗: {e}")

    def update_language(self):
        try:
            if hasattr(self, 'parent_frame'):
                for widget in self.parent_frame.winfo_children():
                    widget.destroy()
                self.combo_ui_refs = []
                self.combo_canvas = None
                self.combo_start_btn = None
                self.combo_stop_btn = None
                self.combo_status_label = None
                self.skill_timer = None
                if hasattr(self._app, 'skill_timer'):
                    del self._app.skill_timer
                self.create_combo_tab()
        except Exception as e:
            print(f"更新技能連段分頁語言時發生錯誤: {e}")

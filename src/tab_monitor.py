import tkinter as tk
from tkinter import ttk, messagebox
import os
import time
import threading
import cv2
import numpy as np
from PIL import Image, ImageTk
import pygetwindow as gw
import keyboard

from image_utils import (
    draw_health_indicator, draw_mana_indicator, draw_scale_lines,
    resize_and_center_image, get_region_text, get_mana_region_text,
    get_interface_ui_region_text,
)
from capture_utils import (
    build_game_window_monitor, capture_region_to_pil, capture_region_to_cv2,
    save_screenshot, _mss_singleton,
)
from utils import Tooltip, get_app_dir
from custom_dialogs import CustomMessageBox
from monitor_analyzer import get_main_color


def _validate_float_input(P):
    if P == "" or P == "-" or P == ".":
        return True
    if P.replace(".", "").replace("-", "").isdigit():
        if P.count(".") <= 1:
            if P.count("-") <= 1 and (P.find("-") == 0 or P.find("-") == -1):
                return True
    return False


def _validate_int_input(P):
    if P == "" or P == "-":
        return True
    if P.replace("-", "").isdigit():
        if P.count("-") <= 1 and (P.find("-") == 0 or P.find("-") == -1):
            return True
    return False


class MonitorTab:
    def __init__(self, app, state, monitor_frame, notebook):
        self._app = app
        self._state = state
        self.monitor_frame = monitor_frame
        self.notebook = notebook

        self.selection_active = False
        self.selection_start = None
        self.selection_end = None
        self.selected_region = None
        self.selected_mana_region = None
        self.selection_window = None
        self.global_esc_active = False

        self.preview_size = (380, 280)
        self.preview_image = None
        self.mana_preview_image = None
        self.last_preview_update = 0
        self.preview_update_interval = 500
        self.last_health_percent = -1
        self.last_mana_percent = -1
        self.last_mana_preview_update = 0
        self._preview_placeholder_shown = False

        self.last_status_update = 0
        self.status_update_interval = 100

        self.window_var = None
        self.window_combo = None
        self.region_label = None
        self.mana_region_label = None
        self.interface_ui_label = None
        self.type_var = None
        self.percent_var = None
        self.key_var = None
        self.cooldown_var = None
        self.multi_trigger_var = None
        self.settings_tree = None
        self.control_frame = None
        self.start_btn = None
        self.stop_btn = None
        self.save_btn = None
        self.test_preview_btn = None
        self.check_freq_label = None
        self.monitor_interval_var = None
        self.ms_label = None
        self.reminder_frame = None
        self.reminder_label = None
        self.language_label = None
        self.gui_settings_label = None
        self.always_on_top_check = None
        self.preview_control_frame = None
        self.preview_settings_label = None
        self.enable_preview_check = None
        self.preview_interval_label = None
        self.preview_ms_label = None
        self.real_time_status_frame = None
        self.current_health_label = None
        self.health_label = None
        self.current_mana_label = None
        self.mana_label = None
        self.main_color_label = None
        self.color_label = None
        self.trigger_status_label = None
        self.trigger_label = None
        self.preview_frame = None
        self.health_preview_frame = None
        self.mana_preview_frame = None
        self.preview_label = None
        self.mana_preview_label = None
        self.interface_ui_preview_canvas = None
        self.language_display_map = None
        self.language_reverse_map = None

        self.create_monitor_tab()

    def create_monitor_tab(self):
        main_frame = self.monitor_frame

        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))

        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.N, tk.S))

        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=0)
        main_frame.rowconfigure(0, weight=1)

        window_frame = ttk.LabelFrame(left_frame, text=self._app.get_text("game_window_settings"), padding="10")
        window_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(window_frame, text=self._app.get_text("game_window")).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.window_var = tk.StringVar(value='')
        self.window_combo = ttk.Combobox(window_frame, textvariable=self.window_var, width=35)
        self.window_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        ttk.Button(window_frame, text=self._app.get_text("refresh"), command=self.refresh_windows).grid(row=0, column=2, padx=(5, 0))

        ttk.Label(window_frame, text=self._app.get_text("health_bar_region")).grid(row=1, column=0, sticky=tk.W, pady=2)
        self.region_label = ttk.Label(window_frame, text=get_region_text(self._app.config), background="lightgray", relief="sunken", padding=2)
        self.region_label.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))

        ttk.Label(window_frame, text=self._app.get_text("mana_bar_region")).grid(row=2, column=0, sticky=tk.W, pady=2)
        self.mana_region_label = ttk.Label(window_frame, text=get_mana_region_text(self._app.config), background="lightgray", relief="sunken", padding=2)
        self.mana_region_label.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))

        ttk.Label(window_frame, text=self._app.get_text("interface_ui_region")).grid(row=3, column=0, sticky=tk.W, pady=2)
        self.interface_ui_label = ttk.Label(window_frame, text=get_interface_ui_region_text(self._app.interface_ui_region), background="lightgray", relief="sunken", padding=2)
        self.interface_ui_label.grid(row=3, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))

        btn = ttk.Button(window_frame, text=self._app.get_text("select_health_region"), command=self.start_selection)
        btn.grid(row=4, column=0, pady=(5, 0))
        Tooltip(btn, self._app.get_text("select_health_region_tip"))
        btn = ttk.Button(window_frame, text=self._app.get_text("select_mana_region"), command=self.start_mana_selection)
        btn.grid(row=4, column=1, pady=(5, 0), padx=(5, 0))
        Tooltip(btn, self._app.get_text("select_mana_region_tip"))
        btn = ttk.Button(window_frame, text=self._app.get_text("select_interface_ui"), command=self._app.select_interface_ui_region)
        btn.grid(row=4, column=2, pady=(5, 0), padx=(5, 0))
        Tooltip(btn, self._app.get_text("select_interface_ui_tip"))

        window_frame.columnconfigure(1, weight=1)

        settings_frame = ttk.LabelFrame(left_frame, text=self._app.get_text("trigger_settings"), padding="10")
        settings_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        add_frame = ttk.Frame(settings_frame)
        add_frame.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(add_frame, text=self._app.get_text("type")).grid(row=0, column=0, sticky=tk.W)
        self.type_var = tk.StringVar(value="HP")
        type_combo = ttk.Combobox(add_frame, textvariable=self.type_var,
                                 values=["HP", "MP"], state="readonly", width=8)
        type_combo.grid(row=0, column=1, padx=(5, 0))
        type_combo.bind("<<ComboboxSelected>>", self.on_type_changed)

        ttk.Label(add_frame, text=self._app.get_text("percentage")).grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        self.percent_var = tk.StringVar(value="60")
        ttk.Entry(add_frame, textvariable=self.percent_var, width=8).grid(row=0, column=3, padx=(5, 0))

        ttk.Label(add_frame, text=self._app.get_text("hotkey")).grid(row=0, column=4, sticky=tk.W, padx=(10, 0))
        self.key_var = tk.StringVar(value="1")
        ttk.Entry(add_frame, textvariable=self.key_var, width=12).grid(row=0, column=5, padx=(5, 0))

        ttk.Label(add_frame, text=self._app.get_text("cooldown_ms")).grid(row=0, column=6, sticky=tk.W, padx=(10, 0))
        self.cooldown_var = tk.StringVar(value="1500")
        ttk.Entry(add_frame, textvariable=self.cooldown_var, width=8).grid(row=0, column=7, padx=(5, 0))

        btn = ttk.Button(add_frame, text=self._app.get_text("add_trigger"), command=self.add_setting_new)
        btn.grid(row=0, column=8, padx=(10, 0))
        Tooltip(btn, self._app.get_text("add_trigger_tip"))

        options_frame = ttk.Frame(settings_frame)
        options_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))

        btn = ttk.Button(options_frame, text=self._app.get_text("remove_selected"), command=self.remove_setting)
        btn.grid(row=0, column=0, padx=(0, 0))
        Tooltip(btn, self._app.get_text("remove_selected_tip"))
        btn = ttk.Button(options_frame, text=self._app.get_text("adjust_colors"), command=self.adjust_colors)
        btn.grid(row=0, column=1, padx=(20, 0))
        Tooltip(btn, self._app.get_text("adjust_colors_tip"))
        btn = ttk.Button(options_frame, text=self._app.get_text("adjust_interface_ui"), command=self.adjust_interface_ui_thresholds)
        btn.grid(row=0, column=2, padx=(10, 0))
        Tooltip(btn, self._app.get_text("adjust_interface_ui_tip"))

        self.multi_trigger_var = tk.BooleanVar(value=True)
        cb = ttk.Checkbutton(options_frame, text=self._app.get_text("multiple_triggers"),
                             variable=self.multi_trigger_var)
        cb.grid(row=0, column=3, columnspan=2, sticky=tk.W, pady=(0, 0), padx=(20, 0))
        Tooltip(cb, self._app.get_text("multiple_triggers_tip"))

        options_frame.columnconfigure(0, weight=0)
        options_frame.columnconfigure(1, weight=0)
        options_frame.columnconfigure(2, weight=0)
        options_frame.columnconfigure(3, weight=1)
        options_frame.columnconfigure(4, weight=0)

        list_frame = ttk.Frame(settings_frame)
        list_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))

        self.settings_tree = ttk.Treeview(list_frame, columns=("type", "percent", "key", "cooldown"), show="headings", height=4)
        self.settings_tree.heading("type", text=self._app.get_text("type"))
        self.settings_tree.heading("percent", text=self._app.get_text("percentage"))
        self.settings_tree.heading("key", text=self._app.get_text("hotkey"))
        self.settings_tree.heading("cooldown", text=self._app.get_text("cooldown_ms"))
        self.settings_tree.column("type", width=60, anchor="center")
        self.settings_tree.column("percent", width=60, anchor="center")
        self.settings_tree.column("key", width=100, anchor="center")
        self.settings_tree.column("cooldown", width=80, anchor="center")

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.settings_tree.yview)
        self.settings_tree.configure(yscrollcommand=scrollbar.set)

        self.settings_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        settings_frame.columnconfigure(3, weight=1)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.load_settings_to_tree()

        self.control_frame = ttk.LabelFrame(left_frame, text=self._app.get_text("control_panel"), padding="10")
        self.control_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        self.start_btn = ttk.Button(self.control_frame, text=self._app.get_text("start_monitoring"), command=self._app.start_monitoring)
        self.start_btn.grid(row=0, column=0, padx=(0, 5))

        self.stop_btn = ttk.Button(self.control_frame, text=self._app.get_text("stop_monitoring"), command=self._app.stop_monitoring, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=1, padx=(0, 5))

        self.save_btn = ttk.Button(self.control_frame, text=self._app.get_text("save_settings"), command=self._app.save_config)
        self.save_btn.grid(row=0, column=2)

        self.test_preview_btn = ttk.Button(self.control_frame, text=self._app.get_text("test_preview"), command=self.test_preview)
        self.test_preview_btn.grid(row=0, column=3, padx=(5, 0))
        Tooltip(self.test_preview_btn, self._app.get_text("test_preview_tip"))

        self.check_freq_label = ttk.Label(self.control_frame, text=self._app.get_text("check_frequency"))
        self.check_freq_label.grid(row=1, column=0, sticky=tk.W, pady=(15, 0))
        self.monitor_interval_var = tk.StringVar(value=str(int(self._state.monitor_interval * 1000)))
        interval_combo = ttk.Combobox(self.control_frame, textvariable=self.monitor_interval_var,
                                     values=["25", "50", "100"], state="readonly", width=8)
        interval_combo.grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=(15, 0))
        self.ms_label = ttk.Label(self.control_frame, text=self._app.get_text("ms"))
        self.ms_label.grid(row=1, column=2, sticky=tk.W, pady=(15, 0))

        self.reminder_frame = ttk.LabelFrame(self.control_frame, text=self._app.get_text("important_reminder"), padding="8")
        self.reminder_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(20, 5))

        reminder_text = self._app.get_text("reminder_text")

        self.reminder_label = ttk.Label(self.reminder_frame, text=reminder_text,
                                  font=("Arial", 9), foreground="red",
                                  justify=tk.LEFT, wraplength=400)
        self.reminder_label.grid(row=0, column=0, sticky=(tk.W, tk.E))

        language_text = self._app.get_text("language")
        self.language_label = ttk.Label(self.control_frame, text=language_text)
        self.language_label.grid(row=4, column=0, sticky=tk.W, pady=(10, 0))

        self.language_display_map = {
            "\u7e41\u9ad4\u4e2d\u6587": "zh-tw",
            "English": "en"
        }
        self.language_reverse_map = {v: k for k, v in self.language_display_map.items()}

        display_values = list(self.language_display_map.keys())
        current_display = self.language_reverse_map.get(self._app.current_language, "\u7e41\u9ad4\u4e2d\u6587")
        self._app.language_var.set(current_display)

        language_combo = ttk.Combobox(self.control_frame, textvariable=self._app.language_var,
                                     values=display_values, state="readonly", width=12)
        language_combo.grid(row=4, column=1, sticky=tk.W, padx=(5, 0), pady=(10, 0))
        language_combo.bind("<<ComboboxSelected>>", lambda e: self._app.change_language_display(self._app.language_var.get()))

        gui_control_frame = ttk.Frame(self.control_frame)
        gui_control_frame.grid(row=5, column=0, columnspan=3, pady=(10, 0))

        self.gui_settings_label = ttk.Label(gui_control_frame, text=self._app.get_text("gui_settings"))
        self.gui_settings_label.grid(row=0, column=0, sticky=tk.W)
        self.always_on_top_check = ttk.Checkbutton(gui_control_frame, text=self._app.get_text("always_on_top"), variable=self._app.always_on_top_var,
                       command=self._app.toggle_always_on_top)
        self.always_on_top_check.grid(row=0, column=1, columnspan=2, sticky=tk.W, padx=(5, 0))

        self.preview_control_frame = ttk.Frame(self.control_frame)
        self.preview_control_frame.grid(row=6, column=0, columnspan=3, pady=(10, 0))

        self.preview_settings_label = ttk.Label(self.preview_control_frame, text=self._app.get_text("preview_settings"))
        self.preview_settings_label.grid(row=0, column=0, sticky=tk.W)
        self.enable_preview_check = ttk.Checkbutton(self.preview_control_frame, text=self._app.get_text("enable_preview"), variable=self._app.preview_enabled)
        self.enable_preview_check.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))

        self.preview_interval_label = ttk.Label(self.preview_control_frame, text=self._app.get_text("preview_interval"))
        self.preview_interval_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        ttk.Entry(self.preview_control_frame, textvariable=self._app.preview_interval_var, width=8).grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=(5, 0))
        self.preview_ms_label = ttk.Label(self.preview_control_frame, text=self._app.get_text("ms"))
        self.preview_ms_label.grid(row=1, column=2, sticky=tk.W, pady=(5, 0))

        self.real_time_status_frame = ttk.LabelFrame(right_frame, text=self._app.get_text("real_time_status"), padding="10")
        self.real_time_status_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        self.current_health_label = ttk.Label(self.real_time_status_frame, text=self._app.get_text("current_health"), font=("Arial", 10, "bold"))
        self.current_health_label.grid(row=0, column=0, sticky=tk.W, pady=2)
        self.health_label = ttk.Label(self.real_time_status_frame, text="--", font=("Arial", 12, "bold"), foreground="red", width=8, anchor="w")
        self.health_label.grid(row=0, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        self.current_mana_label = ttk.Label(self.real_time_status_frame, text=self._app.get_text("current_mana"), font=("Arial", 10, "bold"))
        self.current_mana_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        self.mana_label = ttk.Label(self.real_time_status_frame, text="--", font=("Arial", 12, "bold"), foreground="blue", width=8, anchor="w")
        self.mana_label.grid(row=1, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        self.main_color_label = ttk.Label(self.real_time_status_frame, text=self._app.get_text("main_color"))
        self.main_color_label.grid(row=2, column=0, sticky=tk.W, pady=2)
        self.color_label = ttk.Label(self.real_time_status_frame, text="--", width=20, anchor="w")
        self.color_label.grid(row=2, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        self.trigger_status_label = ttk.Label(self.real_time_status_frame, text=self._app.get_text("trigger_status"))
        self.trigger_status_label.grid(row=3, column=0, sticky=tk.W, pady=2)
        self.trigger_label = ttk.Label(self.real_time_status_frame, text="--", width=35, anchor="w")
        self.trigger_label.grid(row=3, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        self.preview_frame = ttk.LabelFrame(right_frame, text=self._app.get_text("region_preview"), padding="10")
        self.preview_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.health_preview_frame = ttk.LabelFrame(self.preview_frame, text=self._app.get_text("health_preview"), padding="5")
        self.health_preview_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))

        self.preview_label = ttk.Label(self.health_preview_frame, text=self._app.get_text("select_health_region_first"), relief="sunken", background="lightgray", width=45, anchor="center")
        self.preview_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.mana_preview_frame = ttk.LabelFrame(self.preview_frame, text=self._app.get_text("mana_preview"), padding="5")
        self.mana_preview_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))

        self.mana_preview_label = ttk.Label(self.mana_preview_frame, text=self._app.get_text("select_mana_region_first"), relief="sunken", background="lightblue", width=45, anchor="center")
        self.mana_preview_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.preview_frame.columnconfigure(0, weight=1)
        self.preview_frame.columnconfigure(1, weight=1)
        self.preview_frame.rowconfigure(0, weight=1)
        self.health_preview_frame.columnconfigure(0, weight=1)
        self.health_preview_frame.rowconfigure(0, weight=1)
        self.mana_preview_frame.columnconfigure(0, weight=1)
        self.mana_preview_frame.rowconfigure(0, weight=1)

        interface_ui_preview_frame = ttk.LabelFrame(right_frame, text=self._app.get_text("interface_ui_preview"), padding="5")
        interface_ui_preview_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        self.interface_ui_preview_canvas = tk.Canvas(interface_ui_preview_frame, width=150, height=100, bg='lightgray', relief='sunken')
        self.interface_ui_preview_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E))

        ttk.Label(interface_ui_preview_frame, text=self._app.get_text("interface_ui_preview_hint"),
                 font=("", 7), foreground="gray").grid(row=1, column=0, sticky=tk.W, pady=(3, 0))

        right_frame.rowconfigure(1, weight=1)

        self.preview_size = (380, 280)

        self.health_preview_frame.config(height=300)
        self.mana_preview_frame.config(height=300)

        self.refresh_windows()

        self.last_preview_update = 0
        self.preview_update_interval = 500
        self.last_health_percent = -1
        self.last_mana_percent = -1
        self.last_mana_preview_update = 0
        self._preview_placeholder_shown = False

    @staticmethod
    def _create_scrollable_container(parent):
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Enter>', lambda e: canvas.bind_all("<MouseWheel>",
            lambda ev: canvas.yview_scroll(int(-1*(ev.delta/120)), "units")))
        canvas.bind('<Leave>', lambda e: canvas.unbind_all("<MouseWheel>"))
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        return canvas, scrollable_frame

    def on_type_changed(self, event=None):
        if self.type_var.get() == "HP":
            self.percent_var.set("60")
            self.key_var.set("1")
        else:
            self.percent_var.set("10")
            self.key_var.set("2")

    def test_preview(self):
        if not self.window_var.get():
            messagebox.showerror(self._app.get_text("error"), self._app.get_text("select_game_window_first"))
            return

        if self._app.check_game_window_minimized(self.window_var.get()):
            return

        try:
            windows = gw.getWindowsWithTitle(self.window_var.get())
            if not windows:
                CustomMessageBox.show_error(self._app.get_text("error"), self._app.get_text("game_window_not_found_with_title").format(window_title=self.window_var.get()), self._app.root)
                return

            window = windows[0]

            self._app.root.iconify()

            def _perform_preview_test():
                success_count = 0
                error_messages = []

                try:
                    window.activate()
                    time.sleep(0.2)

                    if self._app.config.get('region'):
                        try:
                            self.capture_preview_async()
                            success_count += 1
                        except Exception as e:
                            error_messages.append(f"{self._app.get_text('health_preview_test_failed')} {e}")

                    if self._app.config.get('mana_region'):
                        try:
                            self.capture_mana_preview_async()
                            success_count += 1
                        except Exception as e:
                            error_messages.append(f"\u9b54\u529b\u9810\u89bd\u6e2c\u8a66\u5931\u6557: {e}")

                except Exception as e:
                    error_messages.append(self._app.get_text("preview_test_failed").format(error=str(e)))

                finally:
                    self._app.root.after(0, self._app.root.deiconify)

                    def _show_result():
                        if success_count > 0:
                            CustomMessageBox.show_info(self._app.get_text("settings_applied"), self._app.get_text("preview_test_completed").format(success_count=success_count), self._app.root)
                        else:
                            CustomMessageBox.show_warning(self._app.get_text("important_reminder"), self._app.get_text("no_testable_regions"), self._app.root)

                        for msg in error_messages:
                            print(msg)

                    self._app.root.after(0, _show_result)

            thread = threading.Thread(target=_perform_preview_test, daemon=True)
            thread.start()

        except Exception as e:
            CustomMessageBox.show_error(self._app.get_text("error"), self._app.get_text("preview_test_failed").format(error=str(e)), self._app.root)

    def auto_load_preview(self):
        if self._app.config.get('region') and self._app.config.get('window_title'):
            try:
                windows = gw.getWindowsWithTitle(self._app.config['window_title'])
                if windows:
                    self.window_var.set(self._app.config['window_title'])

                    health_loaded = self.load_preview_image()
                    mana_loaded = self.load_mana_preview_image()

                    if health_loaded or mana_loaded:
                        print(f"\u5df2\u81ea\u52d5\u8f09\u5165\u8a2d\u5b9a\uff1a\u8996\u7a97={self._app.config['window_title']}")
                    else:
                        print("\u8a2d\u5b9a\u5df2\u8f09\u5165\uff0c\u4f46\u9810\u89bd\u5716\u7247\u9700\u8981\u66f4\u65b0")
                else:
                    print(f"\u904a\u6232\u8996\u7a97 '{self._app.config['window_title']}' \u672a\u627e\u5230")
                    self.window_var.set(self._app.config['window_title'])
                    if hasattr(self, 'preview_label') and self._app.config.get('region'):
                        self.preview_label.config(text=self._app.get_text("game_window_not_found").format(window_title=self._app.config['window_title']), image="")
                    if hasattr(self, 'mana_preview_label') and self._app.config.get('mana_region'):
                        self.mana_preview_label.config(text=self._app.get_text("game_window_not_found").format(window_title=self._app.config['window_title']), image="")
            except Exception as e:
                print(f"\u81ea\u52d5\u8f09\u5165\u9810\u89bd\u5931\u6557: {e}")
                if hasattr(self, 'preview_label'):
                    self.preview_label.config(text=self._app.get_text("settings_load_failed"), image="")
                if hasattr(self, 'mana_preview_label'):
                    self.mana_preview_label.config(text=self._app.get_text("settings_load_failed"), image="")
        else:
            if hasattr(self, 'preview_label'):
                self.preview_label.config(text=self._app.get_text("select_health_bar_first"), image="")
            if hasattr(self, 'mana_preview_label'):
                self.mana_preview_label.config(text=self._app.get_text("select_mana_bar_first"), image="")
            print("\u6c92\u6709\u627e\u5230\u5df2\u5132\u5b58\u7684\u8a2d\u5b9a")

    def refresh_windows(self):
        windows = [w.title for w in gw.getAllWindows() if w.title]
        if hasattr(self, 'window_combo'):
            self.window_combo['values'] = windows
        else:
            print("\u8b66\u544a: window_combo \u4e0d\u5b58\u5728")

    def start_selection(self):
        if not self.window_var.get():
            CustomMessageBox.show_error(self._app.get_text("error"), self._app.get_text("select_game_window_first"), self._app.root)
            return

        if self._app.check_game_window_minimized(self.window_var.get()):
            return

        if self._state.monitoring:
            self._app.stop_monitoring()
            CustomMessageBox.show_info(self._app.get_text("important_reminder"), self._app.get_text("monitoring_auto_stopped_for_selection"), self._app.root)

        try:
            window = gw.getWindowsWithTitle(self.window_var.get())[0]
            window.activate()
            time.sleep(0.1)

            self.selection_active = True

            self._app.root.iconify()

            self.selection_window = self._app.create_child_window("", f"{window.width}x{window.height}")
            self.selection_window.geometry(f"+{window.left}+{window.top}")
            self.selection_window.attributes("-alpha", 0.3)
            self.selection_window.overrideredirect(True)
            self.selection_window.configure(bg='gray')

            canvas = tk.Canvas(self.selection_window, bg='gray', highlightthickness=0)
            canvas.pack(fill=tk.BOTH, expand=True)

            canvas.bind("<ButtonPress-1>", self.on_selection_start)
            canvas.bind("<B1-Motion>", self.on_selection_drag)
            canvas.bind("<ButtonRelease-1>", self.on_selection_end)

            canvas.bind("<Button-3>", self.cancel_selection)

            self.setup_global_esc_listener()

            canvas.create_text(window.width//2, window.height//2,
                             text=self._app.get_text("select_health_bar_instruction"),
                             fill="white", font=("Arial", 14, "bold"),
                             anchor="center")

        except Exception as e:
            CustomMessageBox.show_error(self._app.get_text("error"), self._app.get_text("selection_start_failed").format(error=str(e)), self._app.root)

    def on_selection_start(self, event):
        self.selection_start = (event.x, event.y)

    def on_selection_drag(self, event):
        if self.selection_start:
            self.selection_end = (event.x, event.y)

            canvas = self.selection_window.winfo_children()[0]
            canvas.delete("selection")

            x1, y1 = self.selection_start
            x2, y2 = self.selection_end
            canvas.create_rectangle(x1, y1, x2, y2, outline="red", width=2, tags="selection")

            self.selection_window.update()

    def on_selection_end(self, event):
        if self.selection_start and self.selection_end:
            x1, y1 = self.selection_start
            x2, y2 = self.selection_end

            left = min(x1, x2)
            top = min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)

            self.selected_region = (left, top, width, height)

            self._app.config['region'] = self.selected_region
            self.region_label.config(text=get_region_text(self._app.config), background="lightgreen")

            self._app.root.after(100, self.capture_preview_async)

        self.selection_active = False
        self.remove_global_esc_listener()
        if hasattr(self, 'selection_window') and self.selection_window:
            self.selection_window.destroy()
            self.selection_window = None

        self.finalize_selection_restore_gui()

    def cancel_selection(self, event):
        self.selection_active = False
        self.selection_start = None
        self.selection_end = None

        self.remove_global_esc_listener()

        if hasattr(self, 'selection_window') and self.selection_window:
            self.selection_window.destroy()

        self.finalize_selection_restore_gui()

    def setup_global_esc_listener(self):
        try:
            self.remove_global_esc_listener()

            keyboard.add_hotkey('esc', self.global_esc_handler, suppress=False)
            self.global_esc_active = True
        except Exception as e:
            print(f"\u8a2d\u7f6e\u5168\u5c40ESC\u76e3\u807d\u5931\u6557: {e}")

    def remove_global_esc_listener(self):
        try:
            if hasattr(self, 'global_esc_active') and self.global_esc_active:
                keyboard.remove_hotkey('esc')
                self.global_esc_active = False
        except Exception as e:
            print(f"\u79fb\u9664\u5168\u5c40ESC\u76e3\u807d\u5931\u6557: {e}")

    def global_esc_handler(self):
        try:
            if hasattr(self, 'selection_active') and self.selection_active:
                self._app.root.after(0, lambda: self.cancel_selection(None))
        except Exception as e:
            print(f"\u5168\u5c40ESC\u8655\u7406\u5931\u6557: {e}")

    def finalize_selection_restore_gui(self, success_message_key=None, message_params=None):
        self._app.root.deiconify()
        self._app.root.attributes("-topmost", self._app.always_on_top_var.get())
        self._app.root.lift()
        self._app.root.focus_force()

        if success_message_key:
            message = self._app.get_text(success_message_key)
            if message_params:
                message = message.format(**message_params)
            CustomMessageBox.show_info(self._app.get_text("success"), message, self._app.root)

    def start_mana_selection(self):
        if not self.window_var.get():
            CustomMessageBox.show_error(self._app.get_text("error"), self._app.get_text("select_game_window_first"), self._app.root)
            return

        if self._app.check_game_window_minimized(self.window_var.get()):
            return

        if self._state.monitoring:
            self._app.stop_monitoring()
            CustomMessageBox.show_info(self._app.get_text("important_reminder"), self._app.get_text("monitoring_auto_stopped_for_selection"), self._app.root)

        try:
            window = gw.getWindowsWithTitle(self.window_var.get())[0]
            window.activate()
            time.sleep(0.1)

            self.selection_active = True

            self._app.root.iconify()

            self.selection_window = self._app.create_child_window("", f"{window.width}x{window.height}")
            self.selection_window.geometry(f"+{window.left}+{window.top}")
            self.selection_window.attributes("-alpha", 0.3)
            self.selection_window.overrideredirect(True)
            self.selection_window.configure(bg='blue')

            canvas = tk.Canvas(self.selection_window, bg='blue', highlightthickness=0)
            canvas.pack(fill=tk.BOTH, expand=True)

            canvas.bind("<ButtonPress-1>", self.on_mana_selection_start)
            canvas.bind("<B1-Motion>", self.on_mana_selection_drag)
            canvas.bind("<ButtonRelease-1>", self.on_mana_selection_end)

            canvas.bind("<Button-3>", self.cancel_selection)

            self.selection_window.bind("<Escape>", self.cancel_selection)
            self.selection_window.focus_set()

            self.setup_global_esc_listener()

            canvas.create_text(window.width//2, window.height//2,
                             text=self._app.get_text("select_mana_bar_instruction"),
                             fill="white", font=("Arial", 14, "bold"),
                             anchor="center")

        except Exception as e:
            CustomMessageBox.show_error(self._app.get_text("error"), self._app.get_text("mana_selection_start_failed").format(error=str(e)), self._app.root)

    def on_mana_selection_start(self, event):
        self.selection_start = (event.x, event.y)

    def on_mana_selection_drag(self, event):
        if self.selection_start:
            self.selection_end = (event.x, event.y)

            canvas = self.selection_window.winfo_children()[0]
            canvas.delete("selection")

            x1, y1 = self.selection_start
            x2, y2 = self.selection_end
            canvas.create_rectangle(x1, y1, x2, y2, outline="cyan", width=2, tags="selection")

            self.selection_window.update()

    def on_mana_selection_end(self, event):
        if self.selection_start and self.selection_end:
            x1, y1 = self.selection_start
            x2, y2 = self.selection_end

            left = min(x1, x2)
            top = min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)

            self.selected_mana_region = (left, top, width, height)

            self._app.config['mana_region'] = self.selected_mana_region
            self.mana_region_label.config(text=get_mana_region_text(self._app.config), background="lightgreen")

            self._app.root.after(100, self.capture_mana_preview_async)

        self.selection_active = False
        self.remove_global_esc_listener()
        if hasattr(self, 'selection_window') and self.selection_window:
            self.selection_window.destroy()
            self.selection_window = None

        self.finalize_selection_restore_gui()

    def capture_mana_preview(self):
        if not self.selected_mana_region:
            return

        if not self._app.window_key_sender._is_game_window_active():
            if hasattr(self, 'mana_preview_label'):
                self.mana_preview_label.config(text=self._app.get_text("waiting_for_game_window"), image="")
            return

        try:
            monitor = build_game_window_monitor(self.window_var.get(), self.selected_mana_region)
            img = capture_region_to_pil(monitor)
            img.thumbnail((200, 200))

            save_screenshot(img, "health_monitor_mana_preview.png")

            draw_scale_lines(img)

            resized_img = resize_and_center_image(img, self.preview_size)
            self.mana_preview_image = ImageTk.PhotoImage(resized_img)
            if hasattr(self, 'mana_preview_label'):
                self.mana_preview_label.config(image=self.mana_preview_image, text="")
        except Exception as e:
            print(f"\u9b54\u529b\u9810\u89bd\u64f7\u53d6\u5931\u6557: {e}")
            if hasattr(self, 'mana_preview_label'):
                self.mana_preview_label.config(text=f"\u9b54\u529b\u9810\u89bd\u64f7\u53d6\u5931\u6557\n{str(e)}", image="")

    def capture_preview(self):
        if not self.selected_region:
            return

        if not self._app.window_key_sender._is_game_window_active():
            if hasattr(self, 'preview_label'):
                self.preview_label.config(text=self._app.get_text("waiting_for_game_window"), image="")
            return

        try:
            monitor = build_game_window_monitor(self.window_var.get(), self.selected_region)
            img = capture_region_to_pil(monitor)
            img.thumbnail((200, 200))

            save_screenshot(img, "health_monitor_preview.png")

            draw_scale_lines(img)

            resized_img = resize_and_center_image(img, self.preview_size)
            self.preview_image = ImageTk.PhotoImage(resized_img)
            if hasattr(self, 'preview_label'):
                self.preview_label.config(image=self.preview_image, text="")
        except Exception as e:
            print(f"\u9810\u89bd\u64f7\u53d6\u5931\u6557: {e}")
            if hasattr(self, 'preview_label'):
                self.preview_label.config(text=f"\u9810\u89bd\u64f7\u53d6\u5931\u6557\n{str(e)}", image="")

    def capture_preview_async(self):
        if not self._app.window_key_sender._is_game_window_active():
            self._app.root.after(0, lambda: hasattr(self, 'preview_label') and self.preview_label.config(text=self._app.get_text("waiting_for_game_window"), image=""))
            return

        def _capture():
            if not self.selected_region:
                return

            try:
                monitor = build_game_window_monitor(self.window_var.get(), self.selected_region)
                img = capture_region_to_pil(monitor)
                img.thumbnail((200, 200))

                save_screenshot(img, "health_monitor_preview.png")

                draw_scale_lines(img)
                resized_img = resize_and_center_image(img, self.preview_size)

                def _update_preview():
                    try:
                        self.preview_image = ImageTk.PhotoImage(resized_img)
                        if hasattr(self, 'preview_label'):
                            self.preview_label.config(image=self.preview_image, text="")
                    except Exception as e:
                        print(f"\u8840\u91cf\u9810\u89bd\u66f4\u65b0\u5931\u6557: {e}")
                        if hasattr(self, 'preview_label'):
                            self.preview_label.config(text=f"\u9810\u89bd\u64f7\u53d6\u5931\u6557\n{str(e)}", image="")

                self._app.root.after(0, _update_preview)
            except Exception as e:
                print(f"\u9810\u89bd\u64f7\u53d6\u5931\u6557: {e}")
                _err_msg = str(e)
                def _update_error():
                    if hasattr(self, 'preview_label'):
                        self.preview_label.config(text=f"\u9810\u89bd\u64f7\u53d6\u5931\u6557\n{_err_msg}", image="")
                self._app.root.after(0, _update_error)

        thread = threading.Thread(target=_capture, daemon=True)
        thread.start()

    def load_preview_image(self):
        preview_path = os.path.join(get_app_dir(), "screenshots", "health_monitor_preview.png")
        if os.path.exists(preview_path) and self.selected_region:
            try:
                img = Image.open(preview_path)
                draw_scale_lines(img)
                resized_img = resize_and_center_image(img, self.preview_size)
                self.preview_image = ImageTk.PhotoImage(resized_img)
                if hasattr(self, 'preview_label'):
                    self.preview_label.config(image=self.preview_image, text="")
                return True
            except Exception as e:
                print(f"\u8f09\u5165\u9810\u89bd\u5716\u7247\u5931\u6557: {e}")
                if hasattr(self, 'preview_label'):
                    self.preview_label.config(text="\u8f09\u5165\u9810\u89bd\u5931\u6557", image="")
                return False
        else:
            if self.selected_region and hasattr(self, 'preview_label'):
                self.preview_label.config(text=self._app.get_text("health_region_set_waiting_preview"), image="")
                return False
            elif hasattr(self, 'preview_label'):
                self.preview_label.config(text=self._app.get_text("select_health_bar_first"), image="")
                return False

    def capture_mana_preview_async(self):
        if not self._app.window_key_sender._is_game_window_active():
            self._app.root.after(0, lambda: hasattr(self, 'mana_preview_label') and self.mana_preview_label.config(text=self._app.get_text("waiting_for_game_window"), image=""))
            return

        def _capture():
            if not self.selected_mana_region:
                return

            try:
                monitor = build_game_window_monitor(self.window_var.get(), self.selected_mana_region)
                img = capture_region_to_pil(monitor)
                img.thumbnail((200, 200))

                save_screenshot(img, "health_monitor_mana_preview.png")

                draw_scale_lines(img)
                resized_img = resize_and_center_image(img, self.preview_size)

                def _update_preview():
                    try:
                        self.mana_preview_image = ImageTk.PhotoImage(resized_img)
                        if hasattr(self, 'mana_preview_label'):
                            self.mana_preview_label.config(image=self.mana_preview_image, text="")
                    except Exception as e:
                        print(f"\u9b54\u529b\u9810\u89bd\u66f4\u65b0\u5931\u6557: {e}")
                        if hasattr(self, 'mana_preview_label'):
                            self.mana_preview_label.config(text=f"\u9b54\u529b\u9810\u89bd\u64f7\u53d6\u5931\u6557\n{str(e)}", image="")

                self._app.root.after(0, _update_preview)
            except Exception as e:
                print(f"\u9b54\u529b\u9810\u89bd\u64f7\u53d6\u5931\u6557: {e}")
                _err_msg = str(e)
                def _update_error():
                    if hasattr(self, 'mana_preview_label'):
                        self.mana_preview_label.config(text=f"\u9b54\u529b\u9810\u89bd\u64f7\u53d6\u5931\u6557\n{_err_msg}", image="")
                self._app.root.after(0, _update_error)

        thread = threading.Thread(target=_capture, daemon=True)
        thread.start()

    def load_mana_preview_image(self):
        mana_preview_path = os.path.join(get_app_dir(), "screenshots", "health_monitor_mana_preview.png")
        if os.path.exists(mana_preview_path) and self.selected_mana_region:
            try:
                img = Image.open(mana_preview_path)
                draw_scale_lines(img)
                resized_img = resize_and_center_image(img, self.preview_size)
                self.mana_preview_image = ImageTk.PhotoImage(resized_img)
                if hasattr(self, 'mana_preview_label'):
                    self.mana_preview_label.config(image=self.mana_preview_image, text="")
                return True
            except Exception as e:
                print(f"\u8f09\u5165\u9b54\u529b\u9810\u89bd\u5716\u7247\u5931\u6557: {e}")
                if hasattr(self, 'mana_preview_label'):
                    self.mana_preview_label.config(text=self._app.get_text("mana_preview_load_failed"), image="")
                return False
        else:
            if self.selected_mana_region and hasattr(self, 'mana_preview_label'):
                try:
                    self.capture_mana_preview_async()
                    return True
                except Exception:
                    self.mana_preview_label.config(text=self._app.get_text("mana_region_set_waiting_preview"), image="")
                    return False
            elif hasattr(self, 'mana_preview_label'):
                self.mana_preview_label.config(text=self._app.get_text("select_mana_bar_first"), image="")
                return False

    def add_setting_new(self):
        try:
            setting_type = self.type_var.get()
            percent = int(self.percent_var.get())
            key = self.key_var.get().strip()
            cooldown = int(self.cooldown_var.get())

            if not (0 <= percent <= 100):
                raise ValueError("\u767e\u5206\u6bd4\u5fc5\u987b\u57280-100\u4e4b\u9593")

            if not key:
                raise ValueError("\u8acb\u8f38\u5165\u5feb\u6377\u9375")

            if cooldown < 0:
                raise ValueError("\u51b7\u5374\u6642\u9593\u4e0d\u80fd\u70ba\u8ca0\u6578")

            if not self.validate_key_sequence(key):
                raise ValueError("\u7121\u6548\u7684\u5feb\u6377\u9375\u683c\u5f0f\u3002\u652f\u63f4\u683c\u5f0f\uff1a\u55ae\u9375\uff08\u5982 '5'\uff09\u6216\u591a\u9375\u5e8f\u5217\uff08\u5982 '1-5-esc'\uff09")

            if 'settings' not in self._app.config:
                self._app.config['settings'] = []
            self._app.config['settings'].append({
                'type': setting_type,
                'percent': percent,
                'key': key,
                'cooldown': cooldown
            })

            type_display = "HP" if setting_type == "HP" else "MP"
            self.settings_tree.insert("", tk.END, values=(type_display, percent, key, cooldown))

            self.on_type_changed()

        except ValueError as e:
            CustomMessageBox.show_error(self._app.get_text("input_error"), str(e), self._app.root)
        except Exception as e:
            CustomMessageBox.show_error(self._app.get_text("error"), self._app.get_text("add_setting_failed").format(error=str(e)), self._app.root)

    def validate_key_sequence(self, key_sequence):
        if not key_sequence:
            return False

        keys = [key.strip() for key in key_sequence.split('-')]

        valid_keys = [
            '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
            'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
            'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
            'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f12',
            'esc', 'escape', 'enter', 'return', 'space', 'tab', 'backspace',
            'delete', 'home', 'end', 'pageup', 'pagedown',
            'up', 'down', 'left', 'right', 'uparrow', 'downarrow', 'leftarrow', 'rightarrow',
            'ctrl', 'alt', 'shift', 'win', 'cmd', 'windows'
        ]

        for key in keys:
            if key.lower() not in valid_keys:
                return False

        return True

    def remove_setting(self):
        selected_item = self.settings_tree.selection()
        if not selected_item:
            CustomMessageBox.show_warning(self._app.get_text("important_reminder"), self._app.get_text("select_setting_to_remove_first"), self._app.root)
            return

        if not CustomMessageBox.ask_yes_no(self._app.get_text("confirm"), self._app.get_text("confirm_remove_setting"), self._app.root):
            return

        item_values = self.settings_tree.item(selected_item[0], 'values')
        self.settings_tree.delete(selected_item[0])

        if 'settings' in self._app.config:
            setting_type = item_values[0]
            self._app.config['settings'] = [
                setting for setting in self._app.config['settings']
                if not (setting.get('type', 'HP') == setting_type and
                       setting['percent'] == int(item_values[1]) and
                       setting['key'] == item_values[2])
            ]

    def load_settings_to_tree(self):
        for item in self.settings_tree.get_children():
            self.settings_tree.delete(item)

        for setting in self._app.config.get('settings', []):
            cooldown = setting.get('cooldown', 1000)
            setting_type = setting.get('type', 'HP')
            type_display = "HP" if setting_type == "HP" else "MP"
            self.settings_tree.insert("", tk.END, values=(type_display, setting['percent'], setting['key'], cooldown))

    def update_live_preview(self, img, health_percent):
        if not self._app.preview_enabled.get():
            return

        current_time = time.time() * 1000

        try:
            update_interval = int(self._app.preview_interval_var.get())
        except ValueError:
            update_interval = 250

        should_update = (
            abs(health_percent - self.last_health_percent) >= 5 or
            (current_time - self.last_preview_update) >= update_interval
        )

        if not should_update:
            return

        try:
            self._app.root.after(0, lambda: self._update_preview_image(img, health_percent))

            self.last_preview_update = current_time
            self.last_health_percent = health_percent

        except Exception as e:
            print(f"\u9810\u89bd\u66f4\u65b0\u5931\u6557: {e}")

    def _update_preview_image(self, img, health_percent):
        try:
            pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

            draw_health_indicator(pil_img, health_percent)

            draw_scale_lines(pil_img)

            resized_img = resize_and_center_image(pil_img, self.preview_size)

            self.preview_image = ImageTk.PhotoImage(resized_img)
            if hasattr(self, 'preview_label'):
                self.preview_label.config(image=self.preview_image)

        except Exception as e:
            print(f"\u66f4\u65b0\u9810\u89bd\u5716\u7247\u5931\u6557: {e}")

    def update_live_mana_preview(self, img, mana_percent):
        if not self._app.preview_enabled.get():
            return

        current_time = time.time() * 1000

        try:
            update_interval = int(self._app.preview_interval_var.get())
        except ValueError:
            update_interval = 250

        should_update = (
            abs(mana_percent - self.last_mana_percent) >= 5 or
            (current_time - self.last_mana_preview_update) >= update_interval
        )

        if not should_update:
            return

        try:
            self._app.root.after(0, lambda: self._update_mana_preview_image(img, mana_percent))

            self.last_mana_preview_update = current_time
            self.last_mana_percent = mana_percent

        except Exception as e:
            print(f"\u9b54\u529b\u9810\u89bd\u66f4\u65b0\u5931\u6557: {e}")

    def _update_mana_preview_image(self, img, mana_percent):
        try:
            pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

            draw_mana_indicator(pil_img, mana_percent)

            draw_scale_lines(pil_img)

            resized_img = resize_and_center_image(pil_img, self.preview_size)

            self.mana_preview_image = ImageTk.PhotoImage(resized_img)
            if hasattr(self, 'mana_preview_label'):
                self.mana_preview_label.config(image=self.mana_preview_image)

        except Exception as e:
            print(f"\u66f4\u65b0\u9b54\u529b\u9810\u89bd\u5716\u7247\u5931\u6557: {e}")

    def update_status(self, health, mana, color, trigger):
        current_time = time.time() * 1000

        if (current_time - self.last_status_update) < self.status_update_interval:
            return

        self._app.root.after(0, lambda: self._update_status_labels(health, mana, color, trigger))

        self.last_status_update = current_time

    def _update_status_labels(self, health, mana, color, trigger):
        try:
            self.health_label.config(text=health)
            self.mana_label.config(text=mana)
            self.color_label.config(text=color)
            self.trigger_label.config(text=trigger)
        except Exception as e:
            print(f"\u66f4\u65b0\u72c0\u614b\u6a19\u7c64\u5931\u6557: {e}")

    def _show_health_preview_placeholder(self):
        if hasattr(self, 'preview_label'):
            self.preview_label.config(text=self._app.get_text("waiting_for_game_window"), image="")

    def _show_mana_preview_placeholder(self):
        if hasattr(self, 'mana_preview_label'):
            self.mana_preview_label.config(text=self._app.get_text("waiting_for_game_window"), image="")

    def adjust_colors(self):
        adjust_window = self._app.create_settings_window(self._app.get_text("adjust_colors_title"), "1000x700")
        adjust_window.resizable(False, False)
        adjust_window.focus_force()

        title_label = ttk.Label(adjust_window, text=self._app.get_text("adjust_colors_main_title"),
                               font=("Arial", 12, "bold"))
        title_label.pack(pady=(20, 15))

        container = ttk.Frame(adjust_window)
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 20))

        canvas, scrollable_frame = self._create_scrollable_container(container)

        button_frame = ttk.Frame(adjust_window)
        button_frame.pack(pady=(10, 20))

        main_frame = ttk.Frame(scrollable_frame)
        main_frame.pack(fill=tk.BOTH, expand=True)

        health_frame = ttk.LabelFrame(main_frame, text=self._app.get_text("health_pixel_ratio_threshold"), padding="10")
        health_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(health_frame, text=self._app.get_text("current_value")).grid(row=0, column=0, sticky=tk.W, pady=2)
        current_health_label = ttk.Label(health_frame, text=f"{self._app.health_threshold}",
                                        font=("Arial", 9, "bold"), foreground="blue")
        current_health_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(health_frame, text=self._app.get_text("new_value_0_1")).grid(row=1, column=0, sticky=tk.W, pady=(10, 2))
        health_threshold_var = tk.StringVar(value=str(self._app.health_threshold))
        health_entry = ttk.Entry(health_frame, textvariable=health_threshold_var, width=12)
        health_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 2))

        health_explanation = self._app.get_text("health_pixel_ratio_explanation")
        ttk.Label(health_frame, text=health_explanation, font=("", 9),
                 foreground="gray", justify=tk.LEFT, wraplength=700).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        color_frame = ttk.LabelFrame(main_frame, text=self._app.get_text("color_range_settings"), padding="10")
        color_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(color_frame, text=self._app.get_text("red_h_range_label")).grid(row=0, column=0, sticky=tk.W, pady=2)
        current_red_label = ttk.Label(color_frame, text=f"{self._app.red_h_range}",
                                     font=("Arial", 9, "bold"), foreground="red")
        current_red_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(color_frame, text=self._app.get_text("new_value_0_20")).grid(row=1, column=0, sticky=tk.W, pady=(5, 2))
        red_h_var = tk.StringVar(value=str(self._app.red_h_range))
        red_entry = ttk.Entry(color_frame, textvariable=red_h_var, width=12)
        red_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(5, 2))

        red_explanation = self._app.get_text("red_h_range_explanation")
        ttk.Label(color_frame, text=red_explanation, font=("", 9),
                 foreground="gray", justify=tk.LEFT, wraplength=700).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        ttk.Label(color_frame, text=self._app.get_text("green_h_range_label")).grid(row=3, column=0, sticky=tk.W, pady=(15, 2))
        current_green_label = ttk.Label(color_frame, text=f"{self._app.green_h_range}",
                                       font=("Arial", 9, "bold"), foreground="green")
        current_green_label.grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=(15, 2))

        ttk.Label(color_frame, text=self._app.get_text("new_value_30_90")).grid(row=4, column=0, sticky=tk.W, pady=(5, 2))
        green_h_var = tk.StringVar(value=str(self._app.green_h_range))
        green_entry = ttk.Entry(color_frame, textvariable=green_h_var, width=12)
        green_entry.grid(row=4, column=1, sticky=tk.W, padx=(10, 0), pady=(5, 2))

        green_explanation = self._app.get_text("green_h_range_explanation")
        ttk.Label(color_frame, text=green_explanation, font=("", 9),
                 foreground="gray", justify=tk.LEFT, wraplength=700).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        hsv_frame = ttk.LabelFrame(main_frame, text=self._app.get_text("hsv_fine_tuning"), padding="10")
        hsv_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(hsv_frame, text=self._app.get_text("red_min_saturation")).grid(row=0, column=0, sticky=tk.W, pady=2)
        current_red_sat_label = ttk.Label(hsv_frame, text=f"{self._app.red_saturation_min}",
                                         font=("Arial", 9, "bold"), foreground="red")
        current_red_sat_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(hsv_frame, text=self._app.get_text("new_value_range")).grid(row=1, column=0, sticky=tk.W, pady=(5, 2))
        red_sat_var = tk.StringVar(value=str(self._app.red_saturation_min))
        red_sat_entry = ttk.Entry(hsv_frame, textvariable=red_sat_var, width=12)
        red_sat_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(5, 2))

        ttk.Label(hsv_frame, text=self._app.get_text("red_min_brightness")).grid(row=2, column=0, sticky=tk.W, pady=(10, 2))
        current_red_val_label = ttk.Label(hsv_frame, text=f"{self._app.red_value_min}",
                                         font=("Arial", 9, "bold"), foreground="red")
        current_red_val_label.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 2))

        ttk.Label(hsv_frame, text=self._app.get_text("new_value_range")).grid(row=3, column=0, sticky=tk.W, pady=(5, 2))
        red_val_var = tk.StringVar(value=str(self._app.red_value_min))
        red_val_entry = ttk.Entry(hsv_frame, textvariable=red_val_var, width=12)
        red_val_entry.grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=(5, 2))

        ttk.Label(hsv_frame, text=self._app.get_text("red_hsv_explanation"), font=("", 9),
                 foreground="gray", justify=tk.LEFT, wraplength=700).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        ttk.Label(hsv_frame, text=self._app.get_text("green_min_saturation")).grid(row=0, column=2, sticky=tk.W, padx=(30, 0), pady=2)
        current_green_sat_label = ttk.Label(hsv_frame, text=f"{self._app.green_saturation_min}",
                                           font=("Arial", 9, "bold"), foreground="green")
        current_green_sat_label.grid(row=0, column=3, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(hsv_frame, text=self._app.get_text("new_value_range")).grid(row=1, column=2, sticky=tk.W, padx=(30, 0), pady=(5, 2))
        green_sat_var = tk.StringVar(value=str(self._app.green_saturation_min))
        green_sat_entry = ttk.Entry(hsv_frame, textvariable=green_sat_var, width=12)
        green_sat_entry.grid(row=1, column=3, sticky=tk.W, padx=(10, 0), pady=(5, 2))

        ttk.Label(hsv_frame, text=self._app.get_text("green_min_brightness")).grid(row=2, column=2, sticky=tk.W, padx=(30, 0), pady=(10, 2))
        current_green_val_label = ttk.Label(hsv_frame, text=f"{self._app.green_value_min}",
                                           font=("Arial", 9, "bold"), foreground="green")
        current_green_val_label.grid(row=2, column=3, sticky=tk.W, padx=(10, 0), pady=(10, 2))

        ttk.Label(hsv_frame, text=self._app.get_text("new_value_range")).grid(row=3, column=2, sticky=tk.W, padx=(30, 0), pady=(5, 2))
        green_val_var = tk.StringVar(value=str(self._app.green_value_min))
        green_val_entry = ttk.Entry(hsv_frame, textvariable=green_val_var, width=12)
        green_val_entry.grid(row=3, column=3, sticky=tk.W, padx=(10, 0), pady=(5, 2))

        ttk.Label(hsv_frame, text=self._app.get_text("green_hsv_explanation"), font=("", 9),
                 foreground="gray", justify=tk.LEFT, wraplength=700).grid(row=4, column=2, columnspan=2, sticky=tk.W, pady=(5, 0))

        vcmd_float = (adjust_window.register(_validate_float_input), '%P')
        vcmd_int = (adjust_window.register(_validate_int_input), '%P')

        health_entry.config(validate='key', validatecommand=vcmd_float)
        red_entry.config(validate='key', validatecommand=vcmd_int)
        green_entry.config(validate='key', validatecommand=vcmd_int)
        red_sat_entry.config(validate='key', validatecommand=vcmd_int)
        red_val_entry.config(validate='key', validatecommand=vcmd_int)
        green_sat_entry.config(validate='key', validatecommand=vcmd_int)
        green_val_entry.config(validate='key', validatecommand=vcmd_int)

        def apply_settings():
            try:
                new_health_threshold = float(health_threshold_var.get())
                new_red_h_range = int(red_h_var.get())
                new_green_h_range = int(green_h_var.get())
                new_red_sat_min = int(red_sat_var.get())
                new_red_val_min = int(red_val_var.get())
                new_green_sat_min = int(green_sat_var.get())
                new_green_val_min = int(green_val_var.get())

                if not (0.0 <= new_health_threshold <= 1.0):
                    messagebox.showerror(self._app.get_text("input_error"), self._app.get_text("health_threshold_range_error"))
                    return

                if not (0 <= new_red_h_range <= 20):
                    messagebox.showerror(self._app.get_text("input_error"), self._app.get_text("red_h_range_error"))
                    return

                if not (30 <= new_green_h_range <= 90):
                    messagebox.showerror(self._app.get_text("input_error"), self._app.get_text("green_h_range_error"))
                    return

                if not (50 <= new_red_sat_min <= 255):
                    messagebox.showerror(self._app.get_text("input_error"), self._app.get_text("red_saturation_range_error"))
                    return

                if not (50 <= new_red_val_min <= 255):
                    messagebox.showerror(self._app.get_text("input_error"), self._app.get_text("red_value_range_error"))
                    return

                if not (50 <= new_green_sat_min <= 255):
                    messagebox.showerror(self._app.get_text("input_error"), self._app.get_text("green_saturation_range_error"))
                    return

                if not (50 <= new_green_val_min <= 255):
                    messagebox.showerror(self._app.get_text("input_error"), self._app.get_text("green_value_range_error"))
                    return

                self._app.health_threshold = new_health_threshold
                self._app.red_h_range = new_red_h_range
                self._app.green_h_range = new_green_h_range
                self._app.red_saturation_min = new_red_sat_min
                self._app.red_value_min = new_red_val_min
                self._app.green_saturation_min = new_green_sat_min
                self._app.green_value_min = new_green_val_min

                self._app.config['health_threshold'] = self._app.health_threshold
                self._app.config['red_h_range'] = self._app.red_h_range
                self._app.config['green_h_range'] = self._app.green_h_range
                self._app.config['red_saturation_min'] = self._app.red_saturation_min
                self._app.config['red_value_min'] = self._app.red_value_min
                self._app.config['green_saturation_min'] = self._app.green_saturation_min
                self._app.config['green_value_min'] = self._app.green_value_min
                self._app.save_config()

                current_health_label.config(text=f"{self._app.health_threshold}")
                current_red_label.config(text=f"{self._app.red_h_range}")
                current_green_label.config(text=f"{self._app.green_h_range}")
                current_red_sat_label.config(text=f"{self._app.red_saturation_min}")
                current_red_val_label.config(text=f"{self._app.red_value_min}")
                current_green_sat_label.config(text=f"{self._app.green_saturation_min}")
                current_green_val_label.config(text=f"{self._app.green_value_min}")

                messagebox.showinfo(self._app.get_text("settings_applied"),
                                  self._app.get_text("color_settings_updated").format(
                                      health_threshold=self._app.health_threshold,
                                      red_h_range=self._app.red_h_range,
                                      green_h_range=self._app.green_h_range,
                                      red_saturation_min=self._app.red_saturation_min,
                                      red_value_min=self._app.red_value_min,
                                      green_saturation_min=self._app.green_saturation_min,
                                      green_value_min=self._app.green_value_min))

                adjust_window.destroy()

            except ValueError:
                messagebox.showerror(self._app.get_text("input_error"), self._app.get_text("enter_valid_number"))

        def reset_to_defaults():
            health_threshold_var.set("0.3")
            red_h_var.set("10")
            green_h_var.set("40")
            red_sat_var.set("50")
            red_val_var.set("50")
            green_sat_var.set("50")
            green_val_var.set("50")
            messagebox.showinfo(self._app.get_text("reset_completed"), self._app.get_text("reset_completed_message"))
            adjust_window.lift()
            adjust_window.focus_force()
            adjust_window.attributes("-topmost", True)

        ttk.Button(button_frame, text=self._app.get_text("apply_settings"), command=apply_settings,
                  style="Accent.TButton", width=15).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(button_frame, text=self._app.get_text("reset_to_defaults"), command=reset_to_defaults, width=18).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(button_frame, text=self._app.get_text("cancel"), command=adjust_window.destroy, width=10).grid(row=0, column=2)

    def adjust_interface_ui_thresholds(self):
        adjust_window = self._app.create_settings_window(self._app.get_text("adjust_interface_ui_title"), "550x700")
        adjust_window.resizable(False, False)
        adjust_window.focus_force()

        title_label = ttk.Label(adjust_window, text=self._app.get_text("adjust_interface_ui_main_title"),
                               font=("Arial", 12, "bold"))
        title_label.pack(pady=(20, 15))

        container = ttk.Frame(adjust_window)
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 20))

        canvas, scrollable_frame = self._create_scrollable_container(container)

        button_frame = ttk.Frame(adjust_window)
        button_frame.pack(pady=(10, 20))

        main_frame = ttk.Frame(scrollable_frame)
        main_frame.pack(fill=tk.BOTH, expand=True)

        mse_frame = ttk.LabelFrame(main_frame, text=self._app.get_text("mse_threshold_title"), padding="10")
        mse_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(mse_frame, text=self._app.get_text("current_value")).grid(row=0, column=0, sticky=tk.W, pady=2)
        current_mse_label = ttk.Label(mse_frame, text=f"{self._app.interface_ui_mse_threshold}",
                                     font=("Arial", 9, "bold"), foreground="blue")
        current_mse_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(mse_frame, text=self._app.get_text("new_value_mse_suggested")).grid(row=1, column=0, sticky=tk.W, pady=(10, 2))
        mse_var = tk.StringVar(value=str(int(self._app.interface_ui_mse_threshold)))
        mse_entry = ttk.Entry(mse_frame, textvariable=mse_var, width=12)
        mse_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 2))

        mse_explanation = self._app.get_text("mse_explanation")
        ttk.Label(mse_frame, text=mse_explanation, font=("", 9),
                 foreground="gray", justify=tk.LEFT, wraplength=320).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        ssim_frame = ttk.LabelFrame(main_frame, text=self._app.get_text("ssim_threshold_title"), padding="10")
        ssim_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(ssim_frame, text=self._app.get_text("current_value")).grid(row=0, column=0, sticky=tk.W, pady=2)
        current_ssim_label = ttk.Label(ssim_frame, text=f"{self._app.interface_ui_ssim_threshold}",
                                      font=("Arial", 9, "bold"), foreground="green")
        current_ssim_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(ssim_frame, text=self._app.get_text("new_value_range_0_1")).grid(row=1, column=0, sticky=tk.W, pady=(10, 2))
        ssim_var = tk.StringVar(value=str(self._app.interface_ui_ssim_threshold))
        ssim_entry = ttk.Entry(ssim_frame, textvariable=ssim_var, width=12)
        ssim_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 2))

        ttk.Label(ssim_frame, text=self._app.get_text("ssim_explanation"),
                 font=("Arial", 9), foreground="#666666", wraplength=320).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        hist_frame = ttk.LabelFrame(main_frame, text=self._app.get_text("histogram_threshold_title"), padding="10")
        hist_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(hist_frame, text=self._app.get_text("current_value")).grid(row=0, column=0, sticky=tk.W, pady=2)
        current_hist_label = ttk.Label(hist_frame, text=f"{self._app.interface_ui_hist_threshold}",
                                      font=("Arial", 9, "bold"), foreground="orange")
        current_hist_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(hist_frame, text=self._app.get_text("new_value_range_0_1")).grid(row=1, column=0, sticky=tk.W, pady=(10, 2))
        hist_var = tk.StringVar(value=str(self._app.interface_ui_hist_threshold))
        hist_entry = ttk.Entry(hist_frame, textvariable=hist_var, width=12)
        hist_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 2))

        ttk.Label(hist_frame, text=self._app.get_text("histogram_explanation"),
                 font=("Arial", 9), foreground="#666666", wraplength=320).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        color_frame = ttk.LabelFrame(main_frame, text=self._app.get_text("color_diff_threshold_title"), padding="10")
        color_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(color_frame, text=self._app.get_text("current_value")).grid(row=0, column=0, sticky=tk.W, pady=2)
        current_color_label = ttk.Label(color_frame, text=f"{self._app.interface_ui_color_threshold}",
                                       font=("Arial", 9, "bold"), foreground="red")
        current_color_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(color_frame, text=self._app.get_text("new_value_suggested")).grid(row=1, column=0, sticky=tk.W, pady=(10, 2))
        color_var = tk.StringVar(value=str(int(self._app.interface_ui_color_threshold)))
        color_entry = ttk.Entry(color_frame, textvariable=color_var, width=12)
        color_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 2))

        ttk.Label(color_frame, text=self._app.get_text("color_diff_explanation"),
                 font=("Arial", 9), foreground="#666666", wraplength=320).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        def apply_settings():
            try:
                mse_str = mse_var.get().strip()
                ssim_str = ssim_var.get().strip()
                hist_str = hist_var.get().strip()
                color_str = color_var.get().strip()

                if not mse_str:
                    messagebox.showerror(self._app.get_text("input_error"), self._app.get_text("mse_threshold_empty"))
                    return
                if not ssim_str:
                    messagebox.showerror(self._app.get_text("input_error"), self._app.get_text("ssim_threshold_empty"))
                    return
                if not hist_str:
                    messagebox.showerror(self._app.get_text("input_error"), self._app.get_text("histogram_threshold_empty"))
                    return
                if not color_str:
                    messagebox.showerror(self._app.get_text("input_error"), self._app.get_text("color_threshold_empty"))
                    return

                try:
                    new_mse = int(float(mse_str))
                except ValueError:
                    messagebox.showerror(self._app.get_text("input_error"), self._app.get_text("mse_invalid_number"))
                    return

                try:
                    new_ssim = float(ssim_str)
                except ValueError:
                    messagebox.showerror(self._app.get_text("input_error"), self._app.get_text("ssim_invalid_number"))
                    return

                try:
                    new_hist = float(hist_str)
                except ValueError:
                    messagebox.showerror(self._app.get_text("input_error"), self._app.get_text("histogram_invalid_number"))
                    return

                try:
                    new_color = int(float(color_str))
                except ValueError:
                    messagebox.showerror(self._app.get_text("input_error"), self._app.get_text("color_invalid_number"))
                    return

                if not (100 <= new_mse <= 2000):
                    messagebox.showerror(self._app.get_text("input_error"), self._app.get_text("mse_range_error"))
                    return

                if not (0.0 <= new_ssim <= 1.0):
                    messagebox.showerror(self._app.get_text("input_error"), self._app.get_text("ssim_range_error"))
                    return

                if not (0.0 <= new_hist <= 1.0):
                    messagebox.showerror(self._app.get_text("input_error"), self._app.get_text("histogram_range_error"))
                    return

                if not (5 <= new_color <= 100):
                    messagebox.showerror(self._app.get_text("input_error"), self._app.get_text("color_range_error"))
                    return

                self._app.interface_ui_mse_threshold = new_mse
                self._app.interface_ui_ssim_threshold = new_ssim
                self._app.interface_ui_hist_threshold = new_hist
                self._app.interface_ui_color_threshold = new_color

                self._app.config['interface_ui_mse_threshold'] = self._app.interface_ui_mse_threshold
                self._app.config['interface_ui_ssim_threshold'] = self._app.interface_ui_ssim_threshold
                self._app.config['interface_ui_hist_threshold'] = self._app.interface_ui_hist_threshold
                self._app.config['interface_ui_color_threshold'] = self._app.interface_ui_color_threshold
                self._app.save_config()

                current_mse_label.config(text=f"{self._app.interface_ui_mse_threshold}")
                current_ssim_label.config(text=f"{self._app.interface_ui_ssim_threshold}")
                current_hist_label.config(text=f"{self._app.interface_ui_hist_threshold}")
                current_color_label.config(text=f"{self._app.interface_ui_color_threshold}")

                messagebox.showinfo(self._app.get_text("settings_applied"),
                                  self._app.get_text("interface_ui_settings_updated").format(
                                      mse_threshold=self._app.interface_ui_mse_threshold,
                                      ssim_threshold=self._app.interface_ui_ssim_threshold,
                                      hist_threshold=self._app.interface_ui_hist_threshold,
                                      color_threshold=self._app.interface_ui_color_threshold))

                adjust_window.destroy()

            except Exception as e:
                messagebox.showerror(self._app.get_text("error"), f"{self._app.get_text('settings_applied')}: {str(e)}")

        def reset_to_defaults():
            mse_var.set("800")
            ssim_var.set("0.6")
            hist_var.set("0.7")
            color_var.set("35")
            messagebox.showinfo(self._app.get_text("reset_completed"), self._app.get_text("reset_completed_message"))
            adjust_window.lift()
            adjust_window.focus_force()
            adjust_window.attributes("-topmost", True)

        vcmd_float = (adjust_window.register(_validate_float_input), '%P')
        vcmd_int = (adjust_window.register(_validate_int_input), '%P')

        mse_entry.config(validate='key', validatecommand=vcmd_int)
        ssim_entry.config(validate='key', validatecommand=vcmd_float)
        hist_entry.config(validate='key', validatecommand=vcmd_float)
        color_entry.config(validate='key', validatecommand=vcmd_int)

        ttk.Button(button_frame, text=self._app.get_text("apply_settings"), command=apply_settings,
                  style="Accent.TButton", width=15).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(button_frame, text=self._app.get_text("reset_to_defaults"), command=reset_to_defaults, width=18).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(button_frame, text=self._app.get_text("cancel"), command=adjust_window.destroy, width=10).grid(row=0, column=2)

    def update_monitor_tab_language(self):
        self.control_frame.config(text=self._app.get_text("control_panel"))
        self.start_btn.config(text=self._app.get_text("start_monitoring"))
        self.stop_btn.config(text=self._app.get_text("stop_monitoring"))
        self.save_btn.config(text=self._app.get_text("save_settings"))
        self.test_preview_btn.config(text=self._app.get_text("test_preview"))
        self.check_freq_label.config(text=self._app.get_text("check_frequency"))
        self.ms_label.config(text=self._app.get_text("ms"))
        self.reminder_frame.config(text=self._app.get_text("important_reminder"))
        self.reminder_label.config(text=self._app.get_text("reminder_text"))
        self.language_label.config(text=self._app.get_text("language"))
        self.gui_settings_label.config(text=self._app.get_text("gui_settings"))
        self.always_on_top_check.config(text=self._app.get_text("always_on_top"))
        self.preview_settings_label.config(text=self._app.get_text("preview_settings"))
        self.enable_preview_check.config(text=self._app.get_text("enable_preview"))
        self.preview_interval_label.config(text=self._app.get_text("preview_interval"))
        self.preview_ms_label.config(text=self._app.get_text("ms"))
        self.region_label.config(text=get_region_text(self._app.config))
        self.mana_region_label.config(text=get_mana_region_text(self._app.config))
        self.interface_ui_label.config(text=get_interface_ui_region_text(self._app.interface_ui_region))
        self.real_time_status_frame.config(text=self._app.get_text("real_time_status"))
        self.current_health_label.config(text=self._app.get_text("current_health"))
        self.current_mana_label.config(text=self._app.get_text("current_mana"))
        self.main_color_label.config(text=self._app.get_text("main_color"))
        self.trigger_status_label.config(text=self._app.get_text("trigger_status"))
        self.preview_frame.config(text=self._app.get_text("region_preview"))
        self.health_preview_frame.config(text=self._app.get_text("health_preview"))
        self.mana_preview_frame.config(text=self._app.get_text("mana_preview"))
        self.preview_label.config(text=self._app.get_text("select_health_region_first"))
        self.mana_preview_label.config(text=self._app.get_text("select_mana_region_first"))

        current_display = self.language_reverse_map.get(self._app.current_language, "\u7e41\u9ad4\u4e2d\u6587")
        self._app.language_var.set(current_display)

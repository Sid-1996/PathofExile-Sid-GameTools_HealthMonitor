import tkinter as tk
from tkinter import ttk
from _version import __version__

CURRENT_VERSION = f"v{__version__}"


class HelpTab:
    def __init__(self, app, state, parent_frame):
        self._app = app
        self._state = state
        self.parent_frame = parent_frame
        self.help_canvas = None
        self.create_help_tab()

    def create_help_tab(self):
        canvas = tk.Canvas(self.parent_frame, bg='#f8f9fa')
        scrollbar = ttk.Scrollbar(self.parent_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='Card.TFrame')

        self.help_canvas = canvas

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window_id_help = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set, bg='#f8f9fa')

        def _on_canvas_resize_help(event):
            canvas.itemconfig(canvas_window_id_help, width=event.width)
        canvas.bind("<Configure>", _on_canvas_resize_help)

        def _on_mousewheel_help(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel_help))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        header_frame = ttk.Frame(scrollable_frame, style='Card.TFrame')
        header_frame.pack(fill="x", padx=20, pady=(20, 10))

        title_label = ttk.Label(header_frame, text=self._app.get_text("poe_sid_tools_title"),
                                font=("Microsoft YaHei", 24, "bold"), foreground='#2c3e50')
        title_label.pack(pady=(10, 5))

        subtitle_label = ttk.Label(header_frame, text=self._app.get_text("opensource_subtitle"),
                                   font=("Microsoft YaHei", 12), foreground='#7f8c8d')
        subtitle_label.pack(pady=(0, 10))

        video_frame = ttk.Frame(header_frame)
        video_frame.pack(pady=(0, 10))

        video_button = ttk.Button(video_frame, text=self._app.get_text("watch_demo_video"),
                                  command=lambda: self._app.open_video_link("https://dai.ly/xa9cau2"))
        video_button.pack()

        video_note_label = ttk.Label(video_frame, text=self._app.get_text("video_recommendation"),
                                     font=("Microsoft YaHei", 9), foreground='#e74c3c')
        video_note_label.pack(pady=(5, 0))

        content_frame = ttk.Frame(scrollable_frame, style='Card.TFrame')
        content_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        content_frame.columnconfigure(2, weight=1)
        content_frame.rowconfigure(0, weight=0)
        content_frame.rowconfigure(1, weight=1)
        content_frame.rowconfigure(2, weight=0)

        hotkey_card = self.create_info_card(content_frame, self._app.get_text("global_hotkeys_title"), [
            ("F3", self._app.get_text("hotkey_f3_desc"), "#e74c3c"),
            ("F5", self._app.get_text("hotkey_f5_desc"), "#3498db"),
            ("F6", self._app.get_text("hotkey_f6_desc"), "#2ecc71"),
            ("F9", self._app.get_text("hotkey_f9_desc"), "#f39c12"),
            ("F10", self._app.get_text("hotkey_f10_desc"), "#9b59b6"),
            ("F12", self._app.get_text("hotkey_f12_desc"), "#95a5a6"),
            ("CTRL+Click", self._app.get_text("hotkey_ctrl_click_desc"), "#1abc9c")
        ])
        hotkey_card.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10), pady=(0, 10))

        version_card = ttk.LabelFrame(content_frame, text=self._app.get_text("version_info"), padding="15")
        version_card.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10), pady=(0, 10))

        version_info = self._app.get_text("version_info_text").format(version=CURRENT_VERSION)
        ttk.Label(version_card, text=version_info, justify="left",
                  font=('Microsoft YaHei', 10)).pack(anchor="w")

        quickstart_card = ttk.LabelFrame(content_frame, text=self._app.get_text("quick_start"), padding="15")
        quickstart_card.grid(row=0, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 0), pady=(0, 10))

        quickstart_text = self._app.get_text("quickstart_text")
        ttk.Label(quickstart_card, text=quickstart_text, justify="left",
                  font=('Microsoft YaHei', 10)).pack(anchor="w")

        features_card = ttk.LabelFrame(content_frame, text=self._app.get_text("core_features"), padding="15")
        features_card.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10), pady=(0, 10))

        features_container = ttk.Frame(features_card)
        features_container.pack(fill="both", expand=True)

        left_features = ttk.Frame(features_container)
        left_features.pack(side="left", fill="both", expand=True, padx=(0, 15))

        ttk.Label(left_features, text=self._app.get_text("health_monitor_system"), font=('Microsoft YaHei', 12, 'bold'),
                  foreground='#e74c3c').pack(anchor="w", pady=(0, 5))
        ttk.Label(left_features, text=self._app.get_text("health_monitor_desc"),
                  font=('Microsoft YaHei', 9), justify="left").pack(anchor="w", pady=(0, 15))

        ttk.Label(left_features, text=self._app.get_text("smart_inventory_system"), font=('Microsoft YaHei', 12, 'bold'),
                  foreground='#3498db').pack(anchor="w", pady=(0, 5))
        ttk.Label(left_features, text=self._app.get_text("smart_inventory_desc"),
                  font=('Microsoft YaHei', 9), justify="left").pack(anchor="w", pady=(0, 15))

        right_features = ttk.Frame(features_container)
        right_features.pack(side="right", fill="both", expand=True, padx=(15, 0))

        ttk.Label(right_features, text=self._app.get_text("skill_combo_system"), font=('Microsoft YaHei', 12, 'bold'),
                  foreground='#2ecc71').pack(anchor="w", pady=(0, 5))
        ttk.Label(right_features, text=self._app.get_text("skill_combo_desc"),
                  font=('Microsoft YaHei', 9), justify="left").pack(anchor="w", pady=(0, 15))

        ttk.Label(right_features, text=self._app.get_text("automation_tools"), font=('Microsoft YaHei', 12, 'bold'),
                  foreground='#9b59b6').pack(anchor="w", pady=(0, 5))
        ttk.Label(right_features, text=self._app.get_text("automation_tools_desc"),
                  font=('Microsoft YaHei', 9), justify="left").pack(anchor="w")

        setup_card = ttk.LabelFrame(content_frame, text=self._app.get_text("detailed_setup_guide"), padding="15")
        setup_card.grid(row=1, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 0), pady=(0, 10))

        setup_guide = self._app.get_text("setup_guide_text")
        ttk.Label(setup_card, text=setup_guide, justify="left",
                  font=('Microsoft YaHei', 9)).pack(anchor="w")

        notes_card = ttk.LabelFrame(scrollable_frame, text=self._app.get_text("important_notes"), padding="15")
        notes_card.pack(fill="x", padx=20, pady=(0, 10))

        notes_text = self._app.get_text("notes_text")
        ttk.Label(notes_card, text=notes_text, justify="left",
                  font=('Microsoft YaHei', 10)).pack(anchor="w")

        opensource_card = ttk.LabelFrame(scrollable_frame, text=self._app.get_text("opensource_info"), padding="15")
        opensource_card.pack(fill="x", padx=20, pady=(0, 20))

        opensource_container = ttk.Frame(opensource_card)
        opensource_container.pack(fill="x")

        opensource_container.columnconfigure(0, weight=1)
        opensource_container.columnconfigure(1, weight=1)

        left_info = ttk.Frame(opensource_container)
        left_info.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 20))

        ttk.Label(left_info, text=self._app.get_text("github_repo_label"), font=('Microsoft YaHei', 11, 'bold')).pack(anchor="w")
        ttk.Label(left_info, text="https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor",
                  font=('Consolas', 9), foreground='#3498db').pack(anchor="w", pady=(0, 5))

        github_button = ttk.Button(left_info, text=self._app.get_text("visit_github_button"),
                                   command=lambda: self._app.open_video_link("https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor"))
        github_button.pack(anchor="w", pady=(0, 10))

        ttk.Label(left_info, text=self._app.get_text("license_label"), font=('Microsoft YaHei', 11, 'bold')).pack(anchor="w")
        ttk.Label(left_info, text=self._app.get_text("license_text"), font=('Microsoft YaHei', 10)).pack(anchor="w", pady=(0, 10))

        right_info = ttk.Frame(opensource_container)
        right_info.grid(row=0, column=1, sticky=(tk.W, tk.E))

        ttk.Label(right_info, text=self._app.get_text("features_list_label"), font=('Microsoft YaHei', 11, 'bold')).pack(anchor="w", pady=(0, 5))

        free_features = [
            self._app.get_text("feature_f3"),
            self._app.get_text("feature_f5"),
            self._app.get_text("feature_f6"),
            self._app.get_text("feature_f9"),
            self._app.get_text("feature_f10"),
            self._app.get_text("feature_skill_combo"),
            self._app.get_text("feature_auto_click")
        ]

        for feature in free_features:
            ttk.Label(right_info, text=feature, font=('Microsoft YaHei', 9)).pack(anchor="w")

    def create_info_card(self, parent, title, items):
        card = ttk.LabelFrame(parent, text=title, padding="15")

        for item in items:
            item_frame = ttk.Frame(card)
            item_frame.pack(fill="x", pady=(0, 8))

            key_label = ttk.Label(item_frame, text=f" {item[0]} ", font=('Consolas', 10, 'bold'),
                                  background=item[2], foreground='white', padding=(5, 2))
            key_label.pack(side="left")

            desc_label = ttk.Label(item_frame, text=f" {item[1]}", font=('Microsoft YaHei', 10))
            desc_label.pack(side="left", padx=(10, 0))

        return card

    def update_language(self):
        try:
            if hasattr(self, 'parent_frame'):
                for widget in self.parent_frame.winfo_children():
                    widget.destroy()
                self.create_help_tab()
        except Exception as e:
            print(f"更新幫助分頁語言時發生錯誤: {e}")

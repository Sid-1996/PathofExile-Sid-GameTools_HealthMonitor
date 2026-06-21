import tkinter as tk
from tkinter import ttk
from datetime import datetime
from utils import Tooltip


class StatusTab:
    def __init__(self, app, state, parent_frame):
        self._app = app
        self._state = state
        self.parent_frame = parent_frame
        self.status_log = []
        self.status_log_max_lines = 100
        self.last_status_message = ""
        self.status_text_widget = None
        self.auto_scroll_var = None
        self.status_count_label = None
        self.create_status_tab()

    def create_status_tab(self):
        main_frame = self.parent_frame

        self.title_label = ttk.Label(main_frame, text=self._app.get_text("tool_execution_status"), font=("Microsoft YaHei", 20, "bold"))
        self.title_label.pack(pady=(15, 35))

        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill="x", pady=(0, 15))

        self.clear_btn = ttk.Button(control_frame, text=self._app.get_text("clear_records"), command=self.clear_status_log)
        self.clear_btn.pack(side="left", padx=(0, 10))
        Tooltip(self.clear_btn, self._app.get_text("clear_records_tip"))

        self.auto_scroll_var = tk.BooleanVar(value=True)
        self.auto_scroll_cb = ttk.Checkbutton(control_frame, text=self._app.get_text("auto_scroll_to_latest"), variable=self.auto_scroll_var)
        self.auto_scroll_cb.pack(side="left", padx=(0, 10))

        self.status_count_label = ttk.Label(control_frame, text=self._app.get_text("total_records"))
        self.status_count_label.pack(side="right")

        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill="both", expand=True, pady=(10, 0))

        self.status_text_widget = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg="#1e1e1e",
            fg="#ffffff",
            insertbackground="#ffffff",
            selectbackground="#264f78"
        )

        status_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.status_text_widget.yview)
        self.status_text_widget.configure(yscrollcommand=status_scrollbar.set)

        self.configure_status_text_tags()

        self.status_text_widget.pack(side="left", fill="both", expand=True)
        status_scrollbar.pack(side="right", fill="y")

        self.status_text_widget.config(state=tk.DISABLED)

        self.add_status_message(self._app.get_text("tool_started_successfully"), "success")

    def configure_status_text_tags(self):
        self.status_text_widget.tag_config("success", foreground="#4CAF50")
        self.status_text_widget.tag_config("warning", foreground="#FF9800")
        self.status_text_widget.tag_config("error", foreground="#F44336")
        self.status_text_widget.tag_config("info", foreground="#2196F3")
        self.status_text_widget.tag_config("hotkey", foreground="#9C27B0")
        self.status_text_widget.tag_config("monitor", foreground="#00BCD4")

    def add_status_message(self, message, msg_type="info"):
        if self._state._is_closing:
            return

        if message == self.last_status_message:
            return

        self.last_status_message = message

        current_time = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{current_time}] {message}\n"

        self.status_log.append((current_time, message, msg_type))

        if len(self.status_log) > self.status_log_max_lines:
            self.status_log = self.status_log[-self.status_log_max_lines:]
            try:
                if self.status_text_widget and self.status_text_widget.winfo_exists():
                    self.refresh_status_display()
                    return
            except (RuntimeError, tk.TclError):
                return

        try:
            widget_exists = bool(self.status_text_widget and self.status_text_widget.winfo_exists())
        except (RuntimeError, tk.TclError):
            return

        if widget_exists:
            try:
                self.status_text_widget.config(state=tk.NORMAL)
                self.status_text_widget.insert(tk.END, formatted_message, msg_type)
                self.status_text_widget.config(state=tk.DISABLED)
            except (RuntimeError, tk.TclError):
                return

            try:
                if self.auto_scroll_var.get():
                    self.status_text_widget.see(tk.END)
            except (RuntimeError, tk.TclError):
                return

            try:
                self.update_status_count()
            except (RuntimeError, tk.TclError):
                return

    def schedule_ui_callback(self, callback, delay=0):
        if self._state._is_closing:
            return None

        try:
            if not self._app.root.winfo_exists():
                return None
        except (RuntimeError, tk.TclError):
            return None

        def guarded_callback():
            if self._state._is_closing:
                return

            try:
                if not self._app.root.winfo_exists():
                    return
            except (RuntimeError, tk.TclError):
                return

            try:
                callback()
            except (RuntimeError, tk.TclError):
                return

        try:
            return self._app.root.after(delay, guarded_callback)
        except (RuntimeError, tk.TclError):
            return None

    def refresh_status_display(self):
        if not self.status_text_widget:
            return

        self.status_text_widget.config(state=tk.NORMAL)
        self.status_text_widget.delete(1.0, tk.END)

        for time_str, message, msg_type in self.status_log:
            formatted_message = f"[{time_str}] {message}\n"
            self.status_text_widget.insert(tk.END, formatted_message, msg_type)

        self.status_text_widget.config(state=tk.DISABLED)

        if self.auto_scroll_var.get():
            self.status_text_widget.see(tk.END)

        self.update_status_count()

    def clear_status_log(self):
        self.status_log.clear()
        self.last_status_message = ""

        if self.status_text_widget:
            self.status_text_widget.config(state=tk.NORMAL)
            self.status_text_widget.delete(1.0, tk.END)
            self.status_text_widget.config(state=tk.DISABLED)

        self.update_status_count()
        self.add_status_message(self._app.get_text("records_cleared"), "info")

    def update_status_count(self):
        if self.status_count_label:
            count = len(self.status_log)
            self.status_count_label.config(text=self._app.get_text("total_records").format(count=count))

    def update_language(self):
        try:
            if hasattr(self, 'status_count_label'):
                count = len(getattr(self, 'status_log', []))
                self.status_count_label.config(text=self._app.get_text("total_records").format(count=count))

            if hasattr(self, 'title_label'):
                self.title_label.config(text=self._app.get_text("tool_execution_status"))

            if hasattr(self, 'clear_btn'):
                self.clear_btn.config(text=self._app.get_text("clear_records"))

            if hasattr(self, 'auto_scroll_cb'):
                self.auto_scroll_cb.config(text=self._app.get_text("auto_scroll_to_latest"))
        except Exception as e:
            print(f"更新狀態分頁語言時發生錯誤: {e}")

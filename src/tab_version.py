"""
tab_version.py
版本檢查分頁 — 版本比對、程式內下載更新、重啟套用
──────────────────────────────────────────────────────
版本比對改用 GitHub raw latest_version.txt（無 API 限制）。
Release notes 仍從 GitHub API 取得（僅在手動查看詳情時觸發）。
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import requests

import updater_core
from _version import __version__
from utils import Tooltip

CURRENT_VERSION = f"v{__version__}"
GITHUB_REPO = "Sid-1996/PathofExile-Sid-GameTools_HealthMonitor"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


class VersionTab:
    def __init__(self, app, state, parent_frame):
        self._app = app
        self._state = state
        self.parent_frame = parent_frame
        self.latest_version_var = None
        self.latest_version_label = None
        self.version_status_var = None
        self.version_status_label = None
        self.release_notes_text = None
        self.check_update_btn = None
        self.download_btn = None
        self.test_connection_btn = None
        self._silent_version_check_after_id = None
        self._updating = False
        self._downloading = False
        self._cancel_event = None
        self._pending_update_info = None
        self.create_version_tab()

    # ── UI 建構 ──────────────────────────────────────────

    def create_version_tab(self):
        main_frame = self.parent_frame

        title_label = ttk.Label(main_frame, text=self._app.get_text("version_check_title"), font=("Microsoft YaHei", 18, "bold"))
        title_label.pack(pady=(15, 35))

        current_frame = ttk.LabelFrame(main_frame, text=self._app.get_text("current_version_info"), padding="20")
        current_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(current_frame, text=self._app.get_text("current_version_label"), font=("Microsoft YaHei", 12, "bold")).pack(anchor=tk.W)
        current_version_label = ttk.Label(current_frame, text=CURRENT_VERSION, font=("Microsoft YaHei", 14, "bold"), foreground="blue")
        current_version_label.pack(anchor=tk.W, pady=(5, 0))

        remote_frame = ttk.LabelFrame(main_frame, text=self._app.get_text("latest_version_info"), padding="20")
        remote_frame.pack(fill=tk.X, pady=(0, 20))

        self.latest_version_var = tk.StringVar(value=self._app.get_text("checking_version"))
        ttk.Label(remote_frame, text=self._app.get_text("latest_version_label"), font=("Microsoft YaHei", 12, "bold")).pack(anchor=tk.W)
        self.latest_version_label = ttk.Label(remote_frame, textvariable=self.latest_version_var, font=("Microsoft YaHei", 14, "bold"), foreground="green")
        self.latest_version_label.pack(anchor=tk.W, pady=(5, 10))

        self.version_status_var = tk.StringVar(value=self._app.get_text("checking_version_status"))
        self.version_status_label = ttk.Label(remote_frame, textvariable=self.version_status_var, font=("Microsoft YaHei", 11))
        self.version_status_label.pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(remote_frame, text=self._app.get_text("update_notes_label"), font=("Microsoft YaHei", 11, "bold")).pack(anchor=tk.W, pady=(5, 5))

        self.release_notes_text = tk.Text(remote_frame, height=6, wrap=tk.WORD, font=("Microsoft YaHei", 10), foreground="gray", bg=self._app.root.cget("bg"), relief="flat", borderwidth=0)
        self.release_notes_text.insert(1.0, self._app.get_text("loading_text"))
        self.release_notes_text.config(state="disabled")
        self.release_notes_text.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=(0, 10))

        scrollbar = ttk.Scrollbar(remote_frame, orient="vertical", command=self.release_notes_text.yview)
        self.release_notes_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 10))

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(25, 0))

        self.check_update_btn = ttk.Button(button_frame, text=self._app.get_text("check_update_button"), command=self.check_for_updates)
        self.check_update_btn.pack(side=tk.LEFT, padx=(0, 10))
        Tooltip(self.check_update_btn, self._app.get_text("check_update_button_tip"))

        self.download_btn = ttk.Button(button_frame, text=self._app.get_text("download_update_button"), command=self._on_download_click, state="disabled")
        self.download_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.test_connection_btn = ttk.Button(button_frame, text=self._app.get_text("test_connection_button"), command=self.test_github_connection)
        self.test_connection_btn.pack(side=tk.LEFT)
        Tooltip(self.test_connection_btn, self._app.get_text("test_connection_button_tip"))

        self._silent_version_check_after_id = self._app.root.after(2000, self.silent_version_check)

    # ── 版本檢查 ─────────────────────────────────────────

    def check_for_updates(self):
        if self._updating:
            return
        self._updating = True

        def _check():
            try:
                self._app.root.after(0, lambda: self.latest_version_var.set(self._app.get_text("checking_version")))
                self._app.root.after(0, lambda: self.version_status_var.set(self._app.get_text("connecting_github")))

                info = updater_core.check_for_update(CURRENT_VERSION)

                def _update_ui():
                    if info is None:
                        self.latest_version_var.set(self._app.get_text("using_latest_version"))
                        self.latest_version_label.config(foreground="green")
                        self.version_status_var.set(self._app.get_text("using_latest_version"))
                        self.download_btn.config(state="disabled")
                    else:
                        self.latest_version_var.set(f"v{info.version}")
                        self.latest_version_label.config(foreground="red")
                        self.version_status_var.set(self._app.get_text("new_version_found"))
                        self.download_btn.config(state="normal")
                        self._pending_update_info = info
                        self._fetch_release_notes(info.version)

                self._app.root.after(0, _update_ui)

            except requests.exceptions.Timeout:
                self._app.root.after(0, lambda: self._show_check_error("connection_timeout", "github_timeout"))
            except requests.exceptions.ConnectionError:
                self._app.root.after(0, lambda: self._show_check_error("connection_failed", "github_connection_failed"))
            except Exception as e:
                self._app.root.after(0, lambda err=str(e): self._show_check_error("check_error", "check_error_with_message", error=err))
            finally:
                self._updating = False

        threading.Thread(target=_check, daemon=True).start()

    def _show_check_error(self, version_key, status_key, error=None):
        self.latest_version_var.set(self._app.get_text(version_key))
        msg = self._app.get_text(status_key)
        if error:
            msg = msg.format(error=error)
        self.version_status_var.set(msg)
        self.latest_version_label.config(foreground="red")

    def silent_version_check(self):
        self._silent_version_check_after_id = None
        if self._state._is_closing:
            return

        def _silent_check():
            try:
                info = updater_core.check_for_update(CURRENT_VERSION)

                def _update_ui():
                    if info is None:
                        return
                    skipped = self._app.config.get("skipped_version", "")
                    if skipped == f"v{info.version}":
                        return

                    self.latest_version_var.set(f"v{info.version}")
                    self.latest_version_label.config(foreground="red")
                    self.version_status_var.set(self._app.get_text("new_version_found"))
                    self.download_btn.config(state="normal")
                    self._pending_update_info = info
                    self._fetch_release_notes(info.version)
                    self._show_update_notification(info)

                self._app.root.after(0, _update_ui)
            except Exception:
                pass

        threading.Thread(target=_silent_check, daemon=True).start()

    def _fetch_release_notes(self, version_tag):
        """從 GitHub API 取 release notes（僅在有新版時觸發）"""

        def _fetch():
            try:
                resp = requests.get(GITHUB_API_URL, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    body = data.get("body", "")
                    if body:
                        self._app.root.after(0, lambda: self._update_release_notes_display(body))
            except Exception:
                pass

        threading.Thread(target=_fetch, daemon=True).start()

    def test_github_connection(self):
        def _test():
            try:
                self._app.root.after(0, lambda: self.version_status_var.set(self._app.get_text("testing_connection")))
                response = requests.get("https://api.github.com", timeout=5)
                if response.status_code == 200:
                    self._app.root.after(0, lambda: self.version_status_var.set(self._app.get_text("github_connection_ok")))
                else:
                    self._app.root.after(0, lambda: self.version_status_var.set(self._app.get_text("github_connection_warning").format(status_code=response.status_code)))
            except Exception as e:
                self._app.root.after(0, lambda err=str(e): self.version_status_var.set(self._app.get_text("connection_test_failed").format(error=err)))

        threading.Thread(target=_test, daemon=True).start()

    # ── 下載更新 ─────────────────────────────────────────

    def _on_download_click(self):
        if self._downloading or self._pending_update_info is None:
            return
        if not updater_core.is_frozen():
            messagebox.showwarning(
                self._app.get_text("warning"),
                self._app.get_text("updater_source_mode_warning"),
            )
            return
        self._start_download(self._pending_update_info)

    def _start_download(self, info):
        self._downloading = True
        self._cancel_event = threading.Event()
        self.download_btn.config(state="disabled")
        self.check_update_btn.config(state="disabled")

        # 建立進度對話框
        progress_win = tk.Toplevel(self._app.root)
        progress_win.title(self._app.get_text("downloading_update"))
        progress_win.geometry("420x150")
        progress_win.resizable(False, False)
        progress_win.transient(self._app.root)
        progress_win.grab_set()
        progress_win.protocol("WM_DELETE_WINDOW", lambda: None)

        ttk.Label(progress_win, text=self._app.get_text("downloading_update").format(version=f"v{info.version}"), font=("Microsoft YaHei", 11, "bold")).pack(pady=(15, 10))

        progress_var = tk.DoubleVar(value=0)
        progress_bar = ttk.Progressbar(progress_win, variable=progress_var, maximum=100, length=380)
        progress_bar.pack(pady=(0, 5))

        status_var = tk.StringVar(value="0 KB / ? KB")
        ttk.Label(progress_win, textvariable=status_var, font=("Consolas", 9)).pack(pady=(0, 10))

        def cancel():
            self._cancel_event.set()

        cancel_btn = ttk.Button(progress_win, text=self._app.get_text("cancel"), command=cancel)
        cancel_btn.pack()

        def _progress_cb(downloaded, total):
            def _update():
                if total > 0:
                    pct = downloaded / total * 100
                    progress_var.set(pct)
                    dl_kb = downloaded / 1024
                    total_kb = total / 1024
                    status_var.set(f"{dl_kb:.0f} KB / {total_kb:.0f} KB ({pct:.0f}%)")
                else:
                    dl_kb = downloaded / 1024
                    status_var.set(f"{dl_kb:.0f} KB")

            self._app.root.after(0, _update)

        def _do_download():
            try:
                exe_path = updater_core.download_update(info, progress_cb=_progress_cb, cancel_event=self._cancel_event)
                self._app.root.after(0, lambda: self._on_download_finished(exe_path, info))
            except RuntimeError as e:
                if "使用者取消下載" in str(e):
                    self._app.root.after(0, lambda: self._on_download_cancelled(progress_win))
                else:
                    self._app.root.after(0, lambda err=str(e): self._on_download_error(err, progress_win))
            except Exception as e:
                self._app.root.after(0, lambda err=str(e): self._on_download_error(err, progress_win))

        threading.Thread(target=_do_download, daemon=True).start()

    def _on_download_cancelled(self, progress_win):
        progress_win.grab_release()
        progress_win.destroy()
        self._downloading = False
        self.download_btn.config(state="normal")
        self.check_update_btn.config(state="normal")

    def _on_download_error(self, error_msg, progress_win):
        progress_win.grab_release()
        progress_win.destroy()
        self._downloading = False
        self.download_btn.config(state="normal")
        self.check_update_btn.config(state="normal")
        messagebox.showerror(self._app.get_text("error"), self._app.get_text("apply_update_failed").format(error=error_msg))

    def _on_download_finished(self, exe_path, info):
        self._downloading = False
        self.download_btn.config(state="disabled")
        self.check_update_btn.config(state="normal")

        result = messagebox.askyesno(self._app.get_text("download_complete"), self._app.get_text("restart_to_apply").format(current=CURRENT_VERSION, latest=f"v{info.version}"))

        if result:
            try:
                self._app.config["just_updated"] = info.version
                self._app.config_manager.save_config(self._app.config)
                updater_core.apply_update(exe_path)
                os._exit(0)
            except Exception as e:
                messagebox.showerror(self._app.get_text("error"), self._app.get_text("apply_update_failed").format(error=str(e)))

    # ── Release Notes 格式化 ─────────────────────────────

    def format_release_notes(self, markdown_text):
        if not markdown_text or markdown_text == self._app.get_text("no_update_notes"):
            return self._app.get_text("no_update_notes")

        import re

        text = re.sub(r"```[\s\S]*?```", "", markdown_text)
        text = re.sub(r"^### (.*)$", r"● \1", text, flags=re.MULTILINE)
        text = re.sub(r"^## (.*)$", r"◆ \1", text, flags=re.MULTILINE)
        text = re.sub(r"^# (.*)$", r"■ \1", text, flags=re.MULTILINE)
        text = re.sub(r"^\* (.*)$", r"• \1", text, flags=re.MULTILINE)
        text = re.sub(r"^- (.*)$", r"• \1", text, flags=re.MULTILINE)
        text = re.sub(r"^\d+\. (.*)$", r"➤ \1", text, flags=re.MULTILINE)
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        text = re.sub(r"\*\*([^\*]+)\*\*", r"\1", text)
        text = re.sub(r"\*([^\*]+)\*", r"\1", text)
        text = re.sub(r"_([^_]+)_", r"\1", text)
        text = re.sub(r"\n\s*\n\s*\n", "\n\n", text)
        if len(text) > 800:
            text = text[:800] + "..."
        return text.strip()

    def _update_release_notes_display(self, release_body):
        formatted_notes = self.format_release_notes(release_body)
        self.release_notes_text.config(state="normal")
        self.release_notes_text.delete(1.0, tk.END)
        self.release_notes_text.insert(1.0, formatted_notes)
        self.release_notes_text.config(state="disabled")

    # ── 通知對話框 ───────────────────────────────────────

    def _show_update_notification(self, info):
        update_window = tk.Toplevel(self._app.root)
        update_window.title(self._app.get_text("new_version_found_title"))
        update_window.geometry("500x380")
        update_window.resizable(True, True)
        update_window.transient(self._app.root)
        update_window.grab_set()
        update_window.geometry("+%d+%d" % (self._app.root.winfo_rootx() + 50, self._app.root.winfo_rooty() + 50))

        title_frame = ttk.Frame(update_window)
        title_frame.pack(fill=tk.X, padx=20, pady=20)
        ttk.Label(title_frame, text=self._app.get_text("new_version_found_title_2"), font=("Arial", 16, "bold"), foreground="green").pack()

        info_frame = ttk.LabelFrame(update_window, text=self._app.get_text("version_information"), padding="15")
        info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        ttk.Label(info_frame, text=self._app.get_text("current_version_display").format(version=CURRENT_VERSION), font=("Arial", 10)).pack(anchor=tk.W, pady=(0, 5))
        ttk.Label(info_frame, text=self._app.get_text("latest_version_display").format(version=f"v{info.version}"), font=("Arial", 10, "bold"), foreground="red").pack(anchor=tk.W, pady=(0, 10))

        button_frame = ttk.Frame(update_window)
        button_frame.pack(fill=tk.X, padx=20, pady=(0, 20))

        skip_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(button_frame, text=self._app.get_text("skip_this_version"), variable=skip_var).pack(side=tk.LEFT, padx=(0, 10))

        def on_close():
            if skip_var.get():
                self._app.config["skipped_version"] = f"v{info.version}"
                self._app.config_manager.save_config(self._app.config)
            update_window.destroy()

        def start_download():
            on_close()
            self._pending_update_info = info
            self._start_download(info)

        def view_details():
            self._app.notebook.select(self.parent_frame)
            self.latest_version_var.set(f"v{info.version}")
            self.latest_version_label.config(foreground="red")
            self.version_status_var.set(self._app.get_text("new_version_found"))
            self.download_btn.config(state="normal")
            self._pending_update_info = info
            self._fetch_release_notes(info.version)
            on_close()

        ttk.Button(button_frame, text=self._app.get_text("download_now_button"), command=start_download).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text=self._app.get_text("view_details_button"), command=view_details).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text=self._app.get_text("remind_later_button"), command=on_close).pack(side=tk.RIGHT)

    # ── 語言更新 ─────────────────────────────────────────

    def update_language(self):
        try:
            if hasattr(self, "parent_frame"):
                for widget in self.parent_frame.winfo_children():
                    widget.destroy()
                self.create_version_tab()
        except Exception as e:
            print(f"更新版本分頁語言時發生錯誤: {e}")

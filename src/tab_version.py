import tkinter as tk
from tkinter import ttk, messagebox
import threading
import requests
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
        self.download_url = ""
        self._silent_version_check_after_id = None
        self.create_version_tab()

    def create_version_tab(self):
        main_frame = self.parent_frame

        title_label = ttk.Label(main_frame, text=self._app.get_text("version_check_title"), font=('Microsoft YaHei', 18, 'bold'))
        title_label.pack(pady=(15, 35))

        current_frame = ttk.LabelFrame(main_frame, text=self._app.get_text("current_version_info"), padding="20")
        current_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(current_frame, text=self._app.get_text("current_version_label"), font=('Microsoft YaHei', 12, 'bold')).pack(anchor=tk.W)
        current_version_label = ttk.Label(current_frame, text=CURRENT_VERSION,
                                        font=('Microsoft YaHei', 14, 'bold'), foreground='blue')
        current_version_label.pack(anchor=tk.W, pady=(5, 0))

        remote_frame = ttk.LabelFrame(main_frame, text=self._app.get_text("latest_version_info"), padding="20")
        remote_frame.pack(fill=tk.X, pady=(0, 20))

        self.latest_version_var = tk.StringVar(value=self._app.get_text("checking_version"))
        ttk.Label(remote_frame, text=self._app.get_text("latest_version_label"), font=('Microsoft YaHei', 12, 'bold')).pack(anchor=tk.W)
        self.latest_version_label = ttk.Label(remote_frame, textvariable=self.latest_version_var,
                                            font=('Microsoft YaHei', 14, 'bold'), foreground='green')
        self.latest_version_label.pack(anchor=tk.W, pady=(5, 10))

        self.version_status_var = tk.StringVar(value=self._app.get_text("checking_version_status"))
        self.version_status_label = ttk.Label(remote_frame, textvariable=self.version_status_var,
                                            font=('Microsoft YaHei', 11))
        self.version_status_label.pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(remote_frame, text=self._app.get_text("update_notes_label"), font=('Microsoft YaHei', 11, 'bold')).pack(anchor=tk.W, pady=(5, 5))

        self.release_notes_text = tk.Text(remote_frame, height=6, wrap=tk.WORD,
                                        font=('Microsoft YaHei', 10), foreground='gray',
                                        bg=self._app.root.cget('bg'), relief='flat', borderwidth=0)
        self.release_notes_text.pack(fill=tk.X, pady=(0, 10))
        self.release_notes_text.insert(1.0, self._app.get_text("loading_text"))
        self.release_notes_text.config(state='disabled')

        scrollbar = ttk.Scrollbar(remote_frame, orient="vertical", command=self.release_notes_text.yview)
        self.release_notes_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 10))
        self.release_notes_text.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=(0, 10))

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(25, 0))

        self.check_update_btn = ttk.Button(button_frame, text=self._app.get_text("check_update_button"),
                                         command=self.check_for_updates)
        self.check_update_btn.pack(side=tk.LEFT, padx=(0, 10))
        Tooltip(self.check_update_btn, self._app.get_text("check_update_button_tip"))

        self.download_btn = ttk.Button(button_frame, text=self._app.get_text("download_page_button"),
                                     command=self.open_download_page, state='disabled')
        self.download_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.test_connection_btn = ttk.Button(button_frame, text=self._app.get_text("test_connection_button"),
                                            command=self.test_github_connection)
        self.test_connection_btn.pack(side=tk.LEFT)
        Tooltip(self.test_connection_btn, self._app.get_text("test_connection_button_tip"))

        self._silent_version_check_after_id = self._app.root.after(2000, self.silent_version_check)

    def check_for_updates(self):
        def _check():
            try:
                self.latest_version_var.set(self._app.get_text("checking_version"))
                self.version_status_var.set(self._app.get_text("connecting_github"))

                response = requests.get(GITHUB_API_URL, timeout=10)

                if response.status_code == 200:
                    release_data = response.json()
                    latest_version = release_data.get('tag_name', 'unknown')
                    release_body = release_data.get('body', self._app.get_text("no_update_notes"))
                    download_url = release_data.get('html_url', '')

                    self.latest_version_var.set(latest_version)
                    self.download_url = download_url

                    if self.compare_versions(CURRENT_VERSION, latest_version):
                        self.version_status_var.set(self._app.get_text("new_version_found"))
                        self.latest_version_label.config(foreground='red')
                        self.download_btn.config(state='normal')
                    else:
                        self.version_status_var.set(self._app.get_text("using_latest_version"))
                        self.latest_version_label.config(foreground='green')
                        self.download_btn.config(state='disabled')

                    if release_body and release_body != self._app.get_text("no_update_notes"):
                        self.update_release_notes_display(release_body)

                else:
                    self.latest_version_var.set(self._app.get_text("check_failed"))
                    self.version_status_var.set(self._app.get_text("check_failed_http").format(status_code=response.status_code))
                    self.latest_version_label.config(foreground='red')

            except requests.exceptions.Timeout:
                self.latest_version_var.set(self._app.get_text("connection_timeout"))
                self.version_status_var.set(self._app.get_text("github_timeout"))
                self.latest_version_label.config(foreground='red')
            except requests.exceptions.ConnectionError:
                self.latest_version_var.set(self._app.get_text("connection_failed"))
                self.version_status_var.set(self._app.get_text("github_connection_failed"))
                self.latest_version_label.config(foreground='red')
            except Exception as e:
                self.latest_version_var.set(self._app.get_text("check_error"))
                self.version_status_var.set(self._app.get_text("check_error_with_message").format(error=str(e)))
                self.latest_version_label.config(foreground='red')

        threading.Thread(target=_check, daemon=True).start()

    def compare_versions(self, current, latest):
        try:
            current_clean = current.lstrip('v').split('.')
            latest_clean = latest.lstrip('v').split('.')

            while len(current_clean) < 3:
                current_clean.append('0')
            while len(latest_clean) < 3:
                latest_clean.append('0')

            for i in range(3):
                current_part = int(current_clean[i])
                latest_part = int(latest_clean[i])

                if latest_part > current_part:
                    return True
                elif latest_part < current_part:
                    return False

            return False
        except Exception as e:
            print(f"版本比較錯誤: {e}")
            return False

    def open_download_page(self):
        try:
            if self.download_url:
                import webbrowser
                webbrowser.open(self.download_url)
            else:
                import webbrowser
                webbrowser.open(f"https://github.com/{GITHUB_REPO}/releases")
        except Exception as e:
            messagebox.showerror(self._app.get_text("download_page_error_title"),
                               self._app.get_text("download_page_error_message").format(error=e))

    def test_github_connection(self):
        def _test():
            try:
                self.version_status_var.set(self._app.get_text("testing_connection"))
                response = requests.get("https://api.github.com", timeout=5)
                if response.status_code == 200:
                    self.version_status_var.set(self._app.get_text("github_connection_ok"))
                else:
                    self.version_status_var.set(self._app.get_text("github_connection_warning").format(status_code=response.status_code))
            except Exception as e:
                self.version_status_var.set(self._app.get_text("connection_test_failed").format(error=str(e)))

        threading.Thread(target=_test, daemon=True).start()

    def format_release_notes(self, markdown_text):
        if not markdown_text or markdown_text == self._app.get_text("no_update_notes"):
            return self._app.get_text("no_update_notes")

        import re

        text = re.sub(r'```[\s\S]*?```', '', markdown_text)

        text = re.sub(r'^### (.*)$', r'● \1', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.*)$', r'◆ \1', text, flags=re.MULTILINE)
        text = re.sub(r'^# (.*)$', r'■ \1', text, flags=re.MULTILINE)

        text = re.sub(r'^\* (.*)$', r'• \1', text, flags=re.MULTILINE)
        text = re.sub(r'^- (.*)$', r'• \1', text, flags=re.MULTILINE)
        text = re.sub(r'^\d+\. (.*)$', r'➤ \1', text, flags=re.MULTILINE)

        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

        text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^\*]+)\*', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)

        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)

        if len(text) > 800:
            text = text[:800] + "..."

        return text.strip()

    def update_release_notes_display(self, release_body):
        formatted_notes = self.format_release_notes(release_body)

        self.release_notes_text.config(state='normal')
        self.release_notes_text.delete(1.0, tk.END)
        self.release_notes_text.insert(1.0, formatted_notes)
        self.release_notes_text.config(state='disabled')

    def silent_version_check(self):
        self._silent_version_check_after_id = None
        if self._state._is_closing:
            return

        def _silent_check():
            try:
                response = requests.get(GITHUB_API_URL, timeout=10)

                if response.status_code == 200:
                    release_data = response.json()
                    latest_version = release_data.get('tag_name', 'unknown')
                    release_body = release_data.get('body', self._app.get_text("no_update_notes"))
                    download_url = release_data.get('html_url', '')

                    def update_ui():
                        try:
                            skipped = self._app.config.get('skipped_version', '')
                            if skipped == latest_version:
                                return

                            self.latest_version_var.set(latest_version)
                            self.download_url = download_url

                            if self.compare_versions(CURRENT_VERSION, latest_version):
                                self.version_status_var.set(self._app.get_text("new_version_found"))
                                self.latest_version_label.config(foreground='red')
                                self.download_btn.config(state='normal')
                                self.show_update_notification(latest_version, release_body, download_url)
                            else:
                                self.version_status_var.set(self._app.get_text("using_latest_version"))
                                self.latest_version_label.config(foreground='green')
                                self.download_btn.config(state='disabled')

                            if release_body and release_body != self._app.get_text("no_update_notes"):
                                self.update_release_notes_display(release_body)

                        except Exception as e:
                            print(f"UI更新失敗: {e}")

                    self._app.root.after(0, update_ui)
            except requests.exceptions.Timeout:
                pass
            except requests.exceptions.ConnectionError:
                pass
            except Exception as e:
                print(f"靜默檢查版本錯誤: {e}")

        threading.Thread(target=_silent_check, daemon=True).start()

    def show_update_notification(self, latest_version, release_body, download_url):
        update_window = tk.Toplevel(self._app.root)
        update_window.title(self._app.get_text("new_version_found_title"))
        update_window.geometry("500x350")
        update_window.resizable(True, True)
        update_window.transient(self._app.root)
        update_window.grab_set()

        update_window.geometry("+%d+%d" % (
            self._app.root.winfo_rootx() + 50,
            self._app.root.winfo_rooty() + 50
        ))

        title_frame = ttk.Frame(update_window)
        title_frame.pack(fill=tk.X, padx=20, pady=20)

        ttk.Label(title_frame, text=self._app.get_text("new_version_found_title_2"),
                 font=('Arial', 16, 'bold'), foreground='green').pack()

        info_frame = ttk.LabelFrame(update_window, text=self._app.get_text("version_information"), padding="15")
        info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        ttk.Label(info_frame, text=self._app.get_text("current_version_display").format(version=CURRENT_VERSION),
                 font=('Arial', 10)).pack(anchor=tk.W, pady=(0, 5))
        ttk.Label(info_frame, text=self._app.get_text("latest_version_display").format(version=latest_version),
                 font=('Arial', 10, 'bold'), foreground='red').pack(anchor=tk.W, pady=(0, 10))

        if release_body and release_body != self._app.get_text("no_update_notes"):
            ttk.Label(info_frame, text=self._app.get_text("update_notes_label"), font=('Arial', 10, 'bold')).pack(anchor=tk.W)
            notes_frame = ttk.Frame(info_frame)
            notes_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
            notes_scrollbar = ttk.Scrollbar(notes_frame)
            notes_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            notes_text = tk.Text(notes_frame, height=6, font=('Arial', 9),
                                wrap=tk.WORD, yscrollcommand=notes_scrollbar.set,
                                state=tk.NORMAL)
            notes_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            notes_scrollbar.config(command=notes_text.yview)
            notes_text.insert(tk.END, release_body)
            notes_text.config(state=tk.DISABLED)

        button_frame = ttk.Frame(update_window)
        button_frame.pack(fill=tk.X, padx=20, pady=(0, 20))

        skip_var = tk.BooleanVar(value=False)
        skip_cb = ttk.Checkbutton(button_frame, text=self._app.get_text("skip_this_version"), variable=skip_var)
        skip_cb.pack(side=tk.LEFT, padx=(0, 10))

        def on_close():
            if skip_var.get():
                self._app.config['skipped_version'] = latest_version
                self._app.config_manager.save_config(self._app.config)
            update_window.destroy()

        def open_download():
            try:
                import webbrowser
                webbrowser.open(download_url)
                on_close()
            except Exception as e:
                messagebox.showerror(self._app.get_text("download_page_error_title"),
                                   self._app.get_text("download_page_error_message").format(error=e))

        def switch_to_version_tab():
            self._app.notebook.select(self.parent_frame)
            self.latest_version_var.set(latest_version)
            self.version_status_var.set(self._app.get_text("new_version_found"))
            self.update_release_notes_display(release_body)
            self.latest_version_label.config(foreground='red')
            self.download_btn.config(state='normal')
            self.download_url = download_url
            on_close()

        ttk.Button(button_frame, text=self._app.get_text("download_now_button"),
                  command=open_download).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text=self._app.get_text("view_details_button"),
                  command=switch_to_version_tab).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text=self._app.get_text("remind_later_button"),
                  command=on_close).pack(side=tk.RIGHT)

    def update_language(self):
        try:
            if hasattr(self, 'parent_frame'):
                for widget in self.parent_frame.winfo_children():
                    widget.destroy()
                self.create_version_tab()
        except Exception as e:
            print(f"更新版本分頁語言時發生錯誤: {e}")

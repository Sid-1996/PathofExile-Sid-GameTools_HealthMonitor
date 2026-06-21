import tkinter as tk
from tkinter import ttk, messagebox
from _version import __version__
from utils import format_usage_time

CURRENT_VERSION = f"v{__version__}"


class AboutTab:
    def __init__(self, app, state, parent_frame):
        self._app = app
        self._state = state
        self.parent_frame = parent_frame
        self.about_canvas = None
        self.create_about_tab()

    def create_about_tab(self):
        main_frame = self.parent_frame

        canvas = tk.Canvas(main_frame, bg='#f8f9fa', highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='Card.TFrame')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_canvas_resize_about(event):
            canvas.itemconfig(canvas_window_id, width=event.width)
        canvas.bind("<Configure>", _on_canvas_resize_about)

        canvas.pack(side="left", fill="both", expand=True)
        self.about_canvas = canvas
        scrollbar.pack(side="right", fill="y")

        header_frame = ttk.Frame(scrollable_frame, style='Card.TFrame')
        header_frame.pack(fill="x", padx=20, pady=(20, 10))

        title_label = ttk.Label(header_frame, text=self._app.get_text("about_title"),
                                font=("Microsoft YaHei", 24, "bold"), foreground='#2c3e50')
        title_label.pack(pady=(10, 5))

        subtitle_label = ttk.Label(header_frame, text=self._app.get_text("about_subtitle"),
                                   font=("Microsoft YaHei", 12), foreground='#7f8c8d')
        subtitle_label.pack(pady=(0, 10))

        content_frame = ttk.Frame(scrollable_frame, style='Card.TFrame')
        content_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        left_frame = ttk.Frame(content_frame)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))

        info_card = ttk.LabelFrame(left_frame, text=self._app.get_text("software_info"), padding="20")
        info_card.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(info_card, text=self._app.get_text("version_display").format(version=CURRENT_VERSION),
                  font=('Microsoft YaHei', 14, 'bold')).pack(anchor=tk.W, pady=(0, 8))
        ttk.Label(info_card, text=self._app.get_text("status_display"),
                  font=('Microsoft YaHei', 12), foreground='#27ae60').pack(anchor=tk.W, pady=(0, 8))

        usage_time_text = format_usage_time(self._app.total_usage_time, lang=self._app.current_language)
        usage_time_label = ttk.Label(info_card, text=self._app.get_text("total_usage_time").format(time=usage_time_text),
                                     font=('Microsoft YaHei', 12), foreground='#1976D2')
        usage_time_label.pack(anchor=tk.W, pady=(0, 8))
        self._app.usage_time_label = usage_time_label

        ttk.Label(info_card, text=self._app.get_text("license_display"),
                  font=('Microsoft YaHei', 12)).pack(anchor=tk.W)

        links_card = ttk.LabelFrame(left_frame, text=self._app.get_text("official_links"), padding="20")
        links_card.pack(fill=tk.X, pady=(10, 0))

        links_grid = ttk.Frame(links_card)
        links_grid.pack(fill=tk.X)

        row1_frame = ttk.Frame(links_grid)
        row1_frame.pack(fill=tk.X, pady=(0, 8))

        def open_github():
            try:
                import webbrowser
                webbrowser.open("https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor")
            except Exception as e:
                messagebox.showerror("錯誤", f"無法打開 GitHub 頁面: {e}")

        github_btn = ttk.Button(row1_frame, text=self._app.get_text("github_button"), command=open_github, width=12)
        github_btn.pack(side=tk.LEFT, padx=(0, 8))

        def discord_placeholder():
            messagebox.showinfo("提示", self._app.get_text("discord_placeholder_message"))

        discord_btn = ttk.Button(row1_frame, text=self._app.get_text("discord_button"), command=discord_placeholder,
                                 state='disabled', width=12)
        discord_btn.pack(side=tk.LEFT)

        row2_frame = ttk.Frame(links_grid)
        row2_frame.pack(fill=tk.X)

        def open_sid_toolbox():
            try:
                import webbrowser
                webbrowser.open("https://lelive.weebly.com/")
            except Exception as e:
                messagebox.showerror("錯誤", f"無法打開 Sid流亡工具箱 頁面: {e}")

        sid_btn = ttk.Button(row2_frame, text=self._app.get_text("sid_toolbox_button"), command=open_sid_toolbox, width=12)
        sid_btn.pack(side=tk.LEFT)

        right_frame = ttk.Frame(content_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))

        support_card = ttk.LabelFrame(right_frame, text=self._app.get_text("support_developer"), padding="20")
        support_card.pack(fill=tk.BOTH, expand=True)

        support_text = ttk.Label(support_card,
                                 text=self._app.get_text("support_text"),
                                 font=('Microsoft YaHei', 12), foreground='#2E7D32',
                                 justify=tk.CENTER)
        support_text.pack(pady=(0, 15))

        sponsor_frame = ttk.Frame(support_card)
        sponsor_frame.pack(fill=tk.X)

        def open_ecpay():
            try:
                import webbrowser
                webbrowser.open("https://p.ecpay.com.tw/E0E3A")
            except Exception as e:
                messagebox.showerror("錯誤", f"無法打開ECPay頁面: {e}")

        ecpay_btn = ttk.Button(sponsor_frame, text=self._app.get_text("ecpay_button"), command=open_ecpay)
        ecpay_btn.pack(side=tk.LEFT, padx=(0, 8), expand=True, fill=tk.X)

        def open_paypal():
            try:
                import webbrowser
                webbrowser.open("https://www.paypal.com/ncp/payment/GJS4D5VTSVWG4")
            except Exception as e:
                messagebox.showerror("錯誤", f"無法打開PayPal頁面: {e}")

        paypal_btn = ttk.Button(sponsor_frame, text=self._app.get_text("paypal_button"), command=open_paypal)
        paypal_btn.pack(side=tk.LEFT, expand=True, fill=tk.X)

        disclaimer_frame = ttk.LabelFrame(scrollable_frame, text=self._app.get_text("important_disclaimer"), padding="20")
        disclaimer_frame.pack(fill=tk.X, padx=20, pady=(0, 20))

        disclaimer_text = self._app.get_text("disclaimer_text")

        disclaimer_label = ttk.Label(disclaimer_frame, text=disclaimer_text,
                                     wraplength=800, font=('Microsoft YaHei', 11),
                                     justify=tk.LEFT, foreground='#d32f2f')
        disclaimer_label.pack(anchor=tk.W)

    def update_language(self):
        try:
            if hasattr(self, 'parent_frame'):
                for widget in self.parent_frame.winfo_children():
                    widget.destroy()
                self.create_about_tab()
        except Exception as e:
            print(f"更新關於分頁語言時發生錯誤: {e}")

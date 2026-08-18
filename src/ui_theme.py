"""統一的深色 UI theme — 全應用唯一樣式來源。

以 ttkbootstrap 的 dracula-dark 為基底主題，集中定義字型、配色、ttk Style，
並提供分頁共用的佈局 helper（頁首標題、卡片、滾動容器），
取代各 tab 檔內散落的硬編值。
"""

import tkinter as tk
from tkinter import ttk

import ttkbootstrap as ttkb

# ── 字型 ──────────────────────────────────────────────
FONT_FAMILY = "Microsoft YaHei"
MONO_FAMILY = "Consolas"

TITLE_FONT = (FONT_FAMILY, 20, "bold")
SUBTITLE_FONT = (FONT_FAMILY, 13, "bold")
BODY_FONT = (FONT_FAMILY, 10)
SMALL_FONT = (FONT_FAMILY, 9)
MONO_FONT = (MONO_FAMILY, 10)

# ── dracula-dark 色系（與 ttkbootstrap 主題對齊，供 tk 原生 widget 使用）──
BG = "#282a36"  # 視窗/分頁底色
CARD_BG = "#2f313d"  # 卡片底色（比背景亮一階）
INPUT_BG = "#3b3d4a"  # 輸入框底色
BORDER = "#44475a"  # 邊框/分隔線
FG = "#f8f8f2"  # 主文字
FG_MUTED = "#b8b8c8"  # 次要文字
FG_DARK = "#6272a4"  # 更弱的文字
ACCENT = "#bd93f9"  # 強調色（dracula 紫，按鈕、選取）
ACCENT_ACTIVE = "#cba6f7"
SELECT_BG = "#44475a"  # 選取背景
SELECT_FG = "#ffffff"

# 狀態色（log tag、健康/魔力指示）
SUCCESS = "#50fa7b"
WARNING = "#f1fa8c"
ERROR = "#ff5555"
INFO = "#8be9fd"
HOTKEY = "#bd93f9"
MONITOR = "#00BCD4"

# tk 原生 widget（不受 ttk theme 影響）預設底色
TK_BG = BG


def setup_theme(root):
    """在 root 建立後、所有 ttk widget 產生前呼叫一次。"""
    root.configure(bg=BG)
    style = ttkb.Style(theme="dracula-dark")

    # 全域基底：只設定字型，顏色交由 dracula-dark 主題主導
    style.configure(".", font=BODY_FONT)

    # Frame / 卡片
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD_BG, borderwidth=1, relief="solid")
    style.configure("Card.TLabelframe", background=CARD_BG, bordercolor=BORDER, borderwidth=1)
    style.configure("Card.TLabelframe.Label", background=CARD_BG, foreground=FG, font=SUBTITLE_FONT)

    # Label
    style.configure("TLabel", background=BG, foreground=FG, font=BODY_FONT)
    style.configure("Title.TLabel", background=BG, foreground=FG, font=TITLE_FONT)
    style.configure("Subtitle.TLabel", background=BG, foreground=FG_MUTED, font=SMALL_FONT)
    style.configure("Card.TLabel", background=CARD_BG, foreground=FG, font=BODY_FONT)
    style.configure("CardTitle.TLabel", background=CARD_BG, foreground=FG, font=SUBTITLE_FONT)

    # Labelframe
    style.configure("TLabelframe", background=BG, bordercolor=BORDER, borderwidth=1, relief="solid")
    style.configure("TLabelframe.Label", background=BG, foreground=FG, font=SMALL_FONT)

    # Button —— 顏色由 dracula-dark 主題繪製（圓角/現代），只調整間距
    style.configure("TButton", padding=(10, 5))
    style.configure(
        "Accent.TButton",
        background=ACCENT,
        foreground=SELECT_FG,
        focuscolor=ACCENT_ACTIVE,
        padding=(10, 5),
    )
    style.map("Accent.TButton", background=[("pressed", ACCENT_ACTIVE), ("active", ACCENT_ACTIVE), ("disabled", BG)])

    # 輸入
    style.configure("TEntry", padding=(6, 3))
    style.configure("TCombobox", padding=(6, 3))

    # Checkbutton / Radiobutton
    style.configure("TCheckbutton", background=BG, font=BODY_FONT)
    style.configure("TRadiobutton", background=BG, font=BODY_FONT)

    # Notebook —— 選取色由主題 primary 主導，只調整 tab 間距
    style.configure("TNotebook", background=BG, bordercolor=BORDER, borderwidth=1)
    style.configure("TNotebook.Tab", padding=(18, 8))

    # Treeview
    style.configure("Treeview", rowheight=24)
    style.configure("Treeview.Heading", font=SMALL_FONT, relief="flat")
    style.map("Treeview", background=[("selected", SELECT_BG)], foreground=[("selected", SELECT_FG)])


class ScrollArea:
    """統一的可捲動容器：內容放進 .frame，滾輪由全域 handler 路由。"""

    def __init__(self, parent, bg=BG):
        self.canvas = tk.Canvas(parent, bg=bg, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.canvas.yview)
        self.frame = ttk.Frame(self.canvas, style="TFrame")
        self.frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._window_id = self.canvas.create_window((0, 0), window=self.frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._window_id, width=e.width))

    def pack(self):
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

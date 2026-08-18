"""統一的深色 UI theme — 全應用唯一樣式來源。

集中定義字型、配色、ttk Style，並提供分頁共用的佈局 helper
（頁首標題、卡片、滾動容器），取代各 tab 檔內散落的硬編值。
"""

import tkinter as tk
from tkinter import ttk

# ── 字型 ──────────────────────────────────────────────
FONT_FAMILY = "Microsoft YaHei"
MONO_FAMILY = "Consolas"

TITLE_FONT = (FONT_FAMILY, 20, "bold")
SUBTITLE_FONT = (FONT_FAMILY, 13, "bold")
BODY_FONT = (FONT_FAMILY, 10)
SMALL_FONT = (FONT_FAMILY, 9)
MONO_FONT = (MONO_FAMILY, 10)

# ── 深色 palette ──────────────────────────────────────
BG = "#1e1e1e"  # 視窗/分頁底色
CARD_BG = "#252526"  # 卡片底色
INPUT_BG = "#2d2d30"  # 輸入框底色
BORDER = "#3c3c3c"  # 邊框/分隔線
FG = "#d4d4d4"  # 主文字
FG_MUTED = "#9d9d9d"  # 次要文字
FG_DARK = "#6e6e6e"  # 更弱的文字
ACCENT = "#0e639c"  # 強調色（按鈕、選取）
ACCENT_ACTIVE = "#1177bb"
SELECT_BG = "#264f78"  # 選取背景
SELECT_FG = "#ffffff"

# 狀態色（log tag、健康/魔力指示）
SUCCESS = "#4CAF50"
WARNING = "#FF9800"
ERROR = "#F44336"
INFO = "#2196F3"
HOTKEY = "#9C27B0"
MONITOR = "#00BCD4"

# tk 原生 widget（不受 ttk theme 影響）預設底色
TK_BG = BG


def setup_theme(root):
    """在 root 建立後、所有 ttk widget 產生前呼叫一次。"""
    root.configure(bg=BG)
    style = ttk.Style(root)
    style.theme_use("clam")

    # 全域基底
    style.configure(
        ".",
        background=BG,
        foreground=FG,
        fieldbackground=INPUT_BG,
        troughcolor=BG,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        selectbackground=SELECT_BG,
        selectforeground=SELECT_FG,
    )

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

    # Button
    style.configure(
        "TButton",
        background=INPUT_BG,
        foreground=FG,
        bordercolor=BORDER,
        focuscolor=ACCENT,
        lightcolor=INPUT_BG,
        darkcolor=INPUT_BG,
        padding=(10, 5),
    )
    style.map(
        "TButton",
        background=[("pressed", ACCENT_ACTIVE), ("active", CARD_BG), ("disabled", BG)],
        foreground=[("disabled", FG_DARK)],
    )
    style.configure(
        "Accent.TButton",
        background=ACCENT,
        foreground=SELECT_FG,
        bordercolor=ACCENT,
        focuscolor=ACCENT_ACTIVE,
        lightcolor=ACCENT,
        darkcolor=ACCENT,
    )
    style.map("Accent.TButton", background=[("pressed", ACCENT_ACTIVE), ("active", ACCENT_ACTIVE), ("disabled", BG)])

    # 輸入
    style.configure(
        "TEntry",
        background=INPUT_BG,
        foreground=FG,
        fieldbackground=INPUT_BG,
        insertcolor=FG,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        padding=(6, 3),
    )
    style.configure("TCombobox", background=INPUT_BG, foreground=FG, fieldbackground=INPUT_BG, bordercolor=BORDER, arrowcolor=FG)
    style.map("TCombobox", fieldbackground=[("readonly", INPUT_BG)], foreground=[("readonly", FG)])

    # Checkbutton / Radiobutton
    style.configure("TCheckbutton", background=BG, foreground=FG, font=BODY_FONT, focuscolor=BG)
    style.map("TCheckbutton", indicatorcolor=[("selected", ACCENT)], background=[("active", BG)])
    style.configure("TRadiobutton", background=BG, foreground=FG, font=BODY_FONT, focuscolor=BG)
    style.map("TRadiobutton", indicatorcolor=[("selected", ACCENT)], background=[("active", BG)])

    # Notebook
    style.configure("TNotebook", background=BG, bordercolor=BORDER, borderwidth=1)
    style.configure(
        "TNotebook.Tab",
        background=CARD_BG,
        foreground=FG_MUTED,
        font=BODY_FONT,
        padding=(18, 8),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", ACCENT), ("active", CARD_BG)],
        foreground=[("selected", SELECT_FG), ("active", FG)],
    )

    # Treeview
    style.configure(
        "Treeview",
        background=INPUT_BG,
        fieldbackground=INPUT_BG,
        foreground=FG,
        bordercolor=BORDER,
        rowheight=24,
    )
    style.configure("Treeview.Heading", background=CARD_BG, foreground=FG, font=SMALL_FONT, relief="flat")
    style.map("Treeview", background=[("selected", SELECT_BG)], foreground=[("selected", SELECT_FG)])

    # Scrollbar
    style.configure("Vertical.TScrollbar", background=CARD_BG, troughcolor=BG, bordercolor=BG, arrowcolor=FG)
    style.map("Vertical.TScrollbar", background=[("active", ACCENT)])


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

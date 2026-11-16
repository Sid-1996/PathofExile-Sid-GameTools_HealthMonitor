"""集中式主題核心（Theme Tokens + qfluentwidgets Theme 套用）。

Phase 0：只建立 token 層與設定層，**畫面與改動前完全一致**。

設計原則
- 顏色只有一份真相（本檔）。其他模組不得再寫死 HEX，一律 `from qt import theme`。
- 模組 import 時不觸碰 QApplication / qfluentwidgets（Qt 相關一律延遲 import），
  因此 token 與正規化邏輯可在純 Python 環境（含 pytest）驗證。
- `TOKENS["dark"]` 與現有 Dracula GUI 實際使用的色值 1:1 對齊，不趁機調色；
  `TOKENS["light"]` 是後續遷移用的完整定義（尚未套用到任何 QSS）。
"""

from __future__ import annotations

import logging
from typing import Any, Final

logger = logging.getLogger(__name__)

VALID_THEMES: Final[tuple[str, str]] = ("dark", "light")
DEFAULT_THEME: Final = "dark"

# 6 碼 = #RRGGBB（實色），8 碼 = #RRGGBBAA（半透明 chrome）。
# dark 值皆取自現有 GUI 實際色字面值（統計自 src/qt/*.py 與 src/app.py），非重新設計。
_DARK: Final[dict[str, str]] = {
    # 底層表面
    "window_bg": "#202020",  # qfluentwidgets FluentWindow dark 底色（套件 paintEvent，非本專案字面值）
    "surface": "#1e1e2e",  # 卡片 / 輸入框底色
    "border": "#3b3b3b",
    "border_strong": "#3d3d5c",
    # 文字
    "fg": "#f8f8f2",
    "fg_muted": "#b8b8c8",
    # Badge 前景（help 頁快捷鍵 badge：dark 用亮色底＋黑字，light 用深色底＋白字）
    "badge_fg": "#000000",
    # 強調色（按鈕 / 焦點）
    "accent": "#bd93f9",
    # 語意色：主組（Dracula，7 個模組使用）
    "success": "#50fa7b",
    "warning": "#f1fa8c",
    "error": "#ff5555",
    "info": "#8be9fd",
    # 語意色：次組（Catppuccin，monitor / inventory / monitor_dialogs 使用）
    "success_soft": "#a6e3a1",
    "warning_soft": "#f9e2af",
    "error_soft": "#f38ba8",
    "info_soft": "#89b4fa",
    # 狀態日誌（monitor 類型訊息）
    "monitor": "#00bcd4",
    # 半透明 chrome（對應現有 rgba() 字面值）
    "statusbar_bg": "#1e1e2ed9",  # rgba(30,30,46,0.85)
    "toast_bg": "#282a36f5",  # rgba(40,42,54,0.96)
}

# light 值已針對 window_bg 驗證 WCAG AA（≥4.5:1），測試見 tests/test_theme.py。
_LIGHT: Final[dict[str, str]] = {
    "window_bg": "#f0f4f9",  # qfluentwidgets FluentWindow light 底色
    "surface": "#ffffff",
    "border": "#d0d7de",
    "border_strong": "#b6c2cf",
    "fg": "#1f2328",
    "fg_muted": "#5f6368",
    "badge_fg": "#ffffff",  # 對 light badge 深色底（success/error/info/accent/warning/fg_muted）全部 ≥4.5:1
    "accent": "#7c3aed",
    "success": "#1a7f37",
    "warning": "#8a6100",
    "error": "#c62828",
    "info": "#0b57d0",
    "success_soft": "#2e7d32",
    "warning_soft": "#876700",
    "error_soft": "#b3261e",
    "info_soft": "#1a5fb4",
    "monitor": "#00747f",
    "statusbar_bg": "#ffffffd9",  # rgba(255,255,255,0.85)
    "toast_bg": "#fffffff5",  # rgba(255,255,255,0.96)
}

TOKENS: Final[dict[str, dict[str, str]]] = {"dark": _DARK, "light": _LIGHT}

# 已實際套用過的主題名；None 代表尚未套用（qconfig 預設是 LIGHT，不能當作已套用）。
_applied_theme: str | None = None


def normalize_theme(value: Any) -> str:
    """把任意輸入正規化為合法主題名。

    合法值只有 `dark` / `light`（大小寫與前後空白容錯）；其餘型別或值一律回退 `dark`。
    """
    if isinstance(value, str):
        name = value.strip().lower()
        if name in VALID_THEMES:
            return name
    return DEFAULT_THEME


def current_theme() -> str:
    """目前生效的主題名（尚未套用時為 DEFAULT_THEME）。"""
    return _applied_theme or DEFAULT_THEME


def current_tokens() -> dict[str, str]:
    """目前主題的 token 表。"""
    return TOKENS[current_theme()]


def accent_color(name: Any = None) -> str:
    """主題 Accent Color；未指定 name 時取目前主題。"""
    return TOKENS[normalize_theme(name if name is not None else current_theme())]["accent"]


def token_pair(key: str) -> tuple[str, str]:
    """回傳 (light, dark)，供 qfluentwidgets 的 `setTextColor(light, dark)` 等雙色 API 使用。"""
    return TOKENS["light"][key], TOKENS["dark"][key]


def qss_color(value: str) -> str:
    """把 token 色值轉成 Qt QSS 可用的顏色字串。

    Qt QSS 的 8 碼格式是 `#AARRGGBB`（與 token 的 `#RRGGBBAA` 相反），因此 8 碼必須轉
    `rgba(r,g,b,a)`。alpha 用**小數**（2 位）：Qt 對整數 alpha 會截斷（`217` → 216/255），
    與舊字面值 `rgba(30,30,46,0.85)` 會差 1/255（實測 #1e1e2c vs #1f1f2c）；用 0.85 才逐位元一致。
    """
    raw = value.lstrip("#")
    if len(raw) == 8:
        r, g, b, a = (int(raw[i : i + 2], 16) for i in (0, 2, 4, 6))
        return f"rgba({r},{g},{b},{a / 255:.2f})"
    return f"#{raw}"


def apply_theme(name: Any = DEFAULT_THEME, *, apply_palette: bool = True) -> str:
    """套用主題並回傳正規化後的主題名；重複套用同一主題為 no-op。

    Phase 3B 套用順序（頁面刷新時三層都必須已是新主題）：

    1. 更新模組狀態 `_applied_theme` —— 頁面 refresh 內讀 `current_tokens()` 必須拿到新主題；
    2. 套用全域 QPalette（原生控件的底色 / 字色 / 選取色）；
    3. 套用全域 QSS（Palette 管不到的 indicator / scrollbar / 選取文字）；
    4. 呼叫 qfluentwidgets `setTheme()` —— 它會「同步」emit `qconfig.themeChangedFinished`，
       MainWindow 的 refresh fan-out 就在此刻執行，故頁面刷新當下 palette、全域 QSS、
       qfluentwidgets 主題都已是新主題。

    `apply_palette=False` 保留舊行為：完全不動原生控件外觀（只換 qfluentwidgets 主題）。
    """
    global _applied_theme

    theme_name = normalize_theme(name)
    if theme_name == _applied_theme:
        return theme_name

    # 必須先更新模組狀態：qfluentwidgets 的 setTheme() 會「同步」emit
    # qconfig.themeChangedFinished，slot 內讀 current_tokens() 必須拿到新主題。
    previous = _applied_theme
    _applied_theme = theme_name
    try:
        if apply_palette:
            _apply_app_palette(theme_name)
            _apply_global_qss(theme_name)
        _apply_fluent_theme(theme_name)
    except Exception:
        _applied_theme = previous
        raise
    logger.debug("主題已套用: %s", theme_name)
    return theme_name


def build_palette(name: Any = None):
    """依 token 建立全域 QPalette（Phase 3B：原生控件底色／字色／選取色的單一來源）。

    只使用既有 token，不新增色值。業務語意色（success / warning / error / info 等）
    一律不進 Palette —— 那些由頁面 QSS 與業務狀態決定，進了會被全域底色蓋掉。
    """
    from PySide6.QtGui import QColor, QPalette

    theme_name = normalize_theme(name if name is not None else current_theme())
    tok = TOKENS[theme_name]
    # 3D 角色（Light/Midlight/Dark/Mid/Shadow）：Windows 樣式幾乎不畫，
    # 但不得殘留 OS 預設值，故仍以既有 token 填滿（淺色主題由亮到暗、深色主題反之）。
    three_d = (
        {
            "Light": tok["border"],
            "Midlight": tok["border_strong"],
            "Dark": tok["surface"],
            "Mid": tok["window_bg"],
            "Shadow": tok["window_bg"],
        }
        if theme_name == "dark"
        else {
            "Light": tok["window_bg"],
            "Midlight": tok["surface"],
            "Dark": tok["border"],
            "Mid": tok["border"],
            "Shadow": tok["border_strong"],
        }
    )
    role_colors = {
        # 底層表面
        QPalette.ColorRole.Window: tok["window_bg"],
        QPalette.ColorRole.WindowText: tok["fg"],
        QPalette.ColorRole.Base: tok["surface"],
        QPalette.ColorRole.AlternateBase: tok["window_bg"],
        # 文字
        QPalette.ColorRole.Text: tok["fg"],
        QPalette.ColorRole.PlaceholderText: tok["fg_muted"],
        QPalette.ColorRole.BrightText: tok["fg"],
        # 原生按鈕（QDialogButtonBox 的 QPushButton）
        QPalette.ColorRole.Button: tok["surface"],
        QPalette.ColorRole.ButtonText: tok["fg"],
        # 選取
        QPalette.ColorRole.Highlight: tok["accent"],
        QPalette.ColorRole.HighlightedText: tok["window_bg"],
        # 工具提示
        QPalette.ColorRole.ToolTipBase: tok["surface"],
        QPalette.ColorRole.ToolTipText: tok["fg"],
        # 超連結（不得殘留 OS 的紫色）
        QPalette.ColorRole.Link: tok["accent"],
        QPalette.ColorRole.LinkVisited: tok["fg_muted"],
        # 3D 角色
        QPalette.ColorRole.Light: three_d["Light"],
        QPalette.ColorRole.Midlight: three_d["Midlight"],
        QPalette.ColorRole.Dark: three_d["Dark"],
        QPalette.ColorRole.Mid: three_d["Mid"],
        QPalette.ColorRole.Shadow: three_d["Shadow"],
    }
    palette = QPalette()
    for role, color in role_colors.items():
        palette.setColor(role, QColor(color))
    # Disabled 群組：底色沿用，字色降到 fg_muted（仍可辨識，不可低到看不出）。
    disabled_colors = {
        QPalette.ColorRole.WindowText: tok["fg_muted"],
        QPalette.ColorRole.Text: tok["fg_muted"],
        QPalette.ColorRole.ButtonText: tok["fg_muted"],
        QPalette.ColorRole.PlaceholderText: tok["fg_muted"],
        QPalette.ColorRole.ToolTipText: tok["fg_muted"],
        QPalette.ColorRole.Link: tok["fg_muted"],
        QPalette.ColorRole.Highlight: tok["border"],
        QPalette.ColorRole.HighlightedText: tok["fg_muted"],
    }
    for role, color in disabled_colors.items():
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(color))
    return palette


def _indicator_metrics() -> tuple[int, int, int]:
    """(indicator 寬, indicator 高, indicator 與文字的間距) —— 取自目前 style 的 pixel metric（自適應 DPI）。"""
    from PySide6.QtWidgets import QApplication, QStyle

    app = QApplication.instance()
    if not isinstance(app, QApplication):
        return (16, 16, 8)
    style = app.style()
    return (
        style.pixelMetric(QStyle.PixelMetric.PM_IndicatorWidth) or 16,
        style.pixelMetric(QStyle.PixelMetric.PM_IndicatorHeight) or 16,
        style.pixelMetric(QStyle.PixelMetric.PM_CheckBoxLabelSpacing) or 8,
    )


def build_global_qss(name: Any = None) -> str:
    """全域 QSS：只收錄 Palette 無法可靠控制的原生控件（Phase 3B）。

    涵蓋範圍嚴格限定：
    - QCheckBox / QRadioButton 的 indicator（正常 / hover / checked / disabled）；
    - QScrollBar 的 groove / handle / hover / disabled（維持可操作尺寸，不縮細）；
    - QDialogButtonBox 內的原生 QPushButton（Palette 管不到：Windows 主題引擎自繪按鈕，
      light 主題下原生按鈕會是淺底白字）。選擇器限定 QDialogButtonBox 後代，
      不會命中頁面內的一般 QPushButton，也不會命中 qfluentwidgets 自繪按鈕。

    刻意「不」收錄 QLineEdit / QSpinBox / QComboBox 等選擇器 —— qfluentwidgets 的
    LineEdit / ComboBox 是自繪元件，全域規則會誤傷。qfluentwidgets 的 CheckBox /
    RadioButton 雖是原生子類別，但它們自繪 indicator 且覆寫 sizeHint，
    故下列 indicator 規則對它們無效（實測像素與 sizeHint 皆不變）。
    """
    tok = TOKENS[normalize_theme(name if name is not None else current_theme())]
    iw, ih, spacing = _indicator_metrics()
    # 刻意「不」用 image: url() 畫勾號：Qt 的 QSS subcontrol 背景圖在此環境不可靠 ——
    # 實測同一份 QSS 跨行程結果不一致（有時有勾號、有時只有色塊），且與其他 border 規則
    # 併用時會整個消失。無法驗證的呈現比沒有勾號更糟，故勾選態採確定的 accent 實心方塊。
    return f"""
QCheckBox::indicator {{ width: {iw}px; height: {ih}px; border: 1px solid {tok["border_strong"]}; border-radius: 3px; background: {tok["surface"]}; }}
QCheckBox::indicator:hover {{ border: 1px solid {tok["accent"]}; background: {tok["window_bg"]}; }}
QCheckBox::indicator:checked {{ border: 1px solid {tok["accent"]}; background: {tok["accent"]}; }}
QCheckBox::indicator:checked:hover {{ border: 1px solid {tok["accent"]}; background: {tok["accent"]}; }}
QCheckBox::indicator:disabled {{ border: 1px solid {tok["border"]}; background: {tok["window_bg"]}; }}
QCheckBox {{ spacing: {spacing}px; min-height: {ih + spacing}px; }}
QRadioButton::indicator {{ width: {iw}px; height: {ih}px; border: 1px solid {tok["border_strong"]}; border-radius: 7px; background: {tok["surface"]}; }}
QRadioButton::indicator:hover {{ border: 1px solid {tok["accent"]}; background: {tok["window_bg"]}; }}
QRadioButton::indicator:checked {{ border: 1px solid {tok["accent"]}; background: {tok["accent"]}; }}
QRadioButton::indicator:disabled {{ border: 1px solid {tok["border"]}; background: {tok["window_bg"]}; }}
QRadioButton {{ spacing: {spacing}px; min-height: {ih + spacing}px; }}
QScrollBar {{ background: transparent; }}
QScrollBar::groove:vertical {{ background: transparent; border: none; }}
QScrollBar::groove:horizontal {{ background: transparent; border: none; }}
QScrollBar::handle:vertical {{ background: {tok["fg_muted"]}; border-radius: 4px; min-height: 24px; }}
QScrollBar::handle:horizontal {{ background: {tok["fg_muted"]}; border-radius: 4px; min-width: 24px; }}
QScrollBar::handle:hover {{ background: {tok["accent"]}; }}
QScrollBar::handle:pressed {{ background: {tok["accent"]}; }}
QScrollBar::handle:disabled {{ background: {tok["border"]}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0px; height: 0px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QDialogButtonBox QPushButton {{ color: {tok["fg"]}; background: {tok["surface"]}; border: 1px solid {tok["border_strong"]}; border-radius: 4px; padding: 4px 14px; }}
QDialogButtonBox QPushButton:hover {{ border: 1px solid {tok["accent"]}; }}
QDialogButtonBox QPushButton:pressed {{ background: {tok["window_bg"]}; }}
QDialogButtonBox QPushButton:disabled {{ color: {tok["fg_muted"]}; background: {tok["window_bg"]}; border: 1px solid {tok["border"]}; }}
""".strip()


def _apply_fluent_theme(theme_name: str) -> None:
    """呼叫 qfluentwidgets 原生 Theme API。

    save=False：設定檔唯一來源是 health_monitor_config.json，不建立第二套保存機制。
    accent 在此集中管理，其他模組不得再呼叫 setThemeColor。
    """
    from qfluentwidgets import Theme, setTheme, setThemeColor

    setTheme(Theme.DARK if theme_name == "dark" else Theme.LIGHT, save=False)
    setThemeColor(TOKENS[theme_name]["accent"], save=False)


def _apply_app_palette(theme_name: str) -> None:
    """把 token Palette 套到 QApplication；已存在的 widget 會收到 PaletteChange 事件而跟著翻新。"""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if isinstance(app, QApplication):
        app.setPalette(build_palette(theme_name))


def _apply_global_qss(theme_name: str) -> None:
    """套用全域 QSS（Palette 管不到的原生控件）。"""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if isinstance(app, QApplication):
        app.setStyleSheet(build_global_qss(theme_name))

"""
about.py（Qt 版）— 關於分頁
────────────────────────────────────────────────────────
對應 tk 版 `tab_about.py`（Phase 7）。
- 軟體資訊（版本/狀態/使用時間）+ 官方連結 + 贊助開發者 + 免責聲明。
- 使用時間由 main_window 的 QTimer 定期更新（`refresh_usage_time`）。
"""

import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QMessageBox, QScrollArea, QVBoxLayout, QWidget
from qfluentwidgets import PushButton

from _version import __version__
from qt.theme import current_tokens
from utils import format_usage_time

CURRENT_VERSION = f"v{__version__}"

_GITHUB_URL = "https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor"
_SID_TOOLBOX_URL = "https://sid-1996.github.io/sid-automation-lab/"
_ECPAY_URL = "https://p.ecpay.com.tw/E0E3A"
_PAYPAL_URL = "https://www.paypal.com/ncp/payment/GJS4D5VTSVWG4"
_AFDIAN_URL = "https://afdian.com/a/sid-1996"


class AboutTab(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app
        # (widget, 樣式規格)：只記 token 名稱，不記顏色；refresh_theme() 時才解析成目前主題
        self._styled: list[tuple[QWidget, tuple]] = []
        self._build_ui()

    # ────────────────────────────────────────────────────
    #  主題樣式（顏色唯一來源：qt.theme）
    # ────────────────────────────────────────────────────

    @staticmethod
    def _style_qss(spec: tuple) -> str:
        """把「(種類, token, 字級, 字重, 透明底色)」規格轉成 QSS。"""
        kind, token, px, weight, transparent = spec
        tok = current_tokens()
        if kind == "card":
            return f"QWidget {{ background-color: {tok['surface']}; border: 1px solid {tok['border']}; border-radius: 8px; }}QLabel {{ background: transparent; }}"
        css = f"font-size: {px}px;"
        if weight:
            css += f" font-weight: {weight};"
        css += f" color: {tok[token]};"
        if transparent:
            css += " background: transparent;"
        return css

    def _apply_style(self, widget: QWidget, spec: tuple) -> None:
        """套用樣式並登記，供 refresh_theme() 重上。"""
        self._styled.append((widget, spec))
        widget.setStyleSheet(self._style_qss(spec))

    def refresh_theme(self) -> None:
        """主題切換刷新：只重上既有元件的 QSS，不重建任何元件、不改版面與高度。"""
        alive: list[tuple[QWidget, tuple]] = []
        for widget, spec in self._styled:
            try:
                widget.setStyleSheet(self._style_qss(spec))
            except RuntimeError:
                continue  # 已被語言切換重建刪除的舊元件
            alive.append((widget, spec))
        self._styled = alive

    # ────────────────────────────────────────────────────
    #  UI 建構
    # ────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        # 原生 QScrollArea/viewport 是用 OS palette 畫底色（深色 Windows = 深灰、淺色 Windows = 白），
        # 與 app 主題無關；改為透明，讓 About 頁跟著 FluentWindow 的主題內容底色（與 status 等分頁一致）。
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._scroll.viewport().setAutoFillBackground(False)
        layout.addWidget(self._scroll)
        self._rebuild_content()

    def _card(self, title):
        box = QWidget()
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(16, 16, 16, 16)
        box_layout.setSpacing(8)
        self._apply_style(box, ("card", None, None, None, None))
        title_label = QLabel(title)
        self._apply_style(title_label, ("label", "fg", 14, 600, True))
        box_layout.addWidget(title_label)
        return box, box_layout

    def _open(self, url, error_key):
        try:
            webbrowser.open(url)
        except Exception as e:
            QMessageBox.critical(self, self._app.get_text("error"), self._app.get_text(error_key).format(error=e))

    def _rebuild_content(self):
        old = self._scroll.takeWidget()
        if old is not None:
            old.deleteLater()
        self._styled.clear()  # 舊元件已排入刪除，樣式登記一併清空

        content = QWidget()
        self._scroll.setWidget(content)
        # QScrollArea.setWidget() 會把內容 widget 的 autoFillBackground 設為 True，
        # 那個底色來自 OS palette（不受主題控制）→ 必須關掉，頁面才會跟著主題底色。
        content.setAutoFillBackground(False)
        root = QVBoxLayout(content)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)
        g = self._app.get_text

        # ── 標題區 ──
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)
        title_label = QLabel(g("about_title"))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._apply_style(title_label, ("label", "fg", 26, 700, False))
        header_layout.addWidget(title_label)
        subtitle_label = QLabel(g("about_subtitle"))
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._apply_style(subtitle_label, ("label", "fg_muted", 13, None, False))
        header_layout.addWidget(subtitle_label)
        root.addWidget(header)

        # ── 左右雙欄：軟體資訊/官方連結 | 贊助開發者 ──
        body = QHBoxLayout()
        body.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(12)

        info_card, info_layout = self._card(g("software_info"))
        version_label = QLabel(g("version_display").format(version=CURRENT_VERSION))
        self._apply_style(version_label, ("label", "fg", 15, 600, False))
        info_layout.addWidget(version_label)
        status_label = QLabel(g("status_display"))
        self._apply_style(status_label, ("label", "success", 13, None, False))
        info_layout.addWidget(status_label)
        self.usage_time_label = QLabel()
        self._apply_style(self.usage_time_label, ("label", "info", 13, None, False))
        info_layout.addWidget(self.usage_time_label)
        license_label = QLabel(g("license_display"))
        self._apply_style(license_label, ("label", "fg", 13, None, False))
        info_layout.addWidget(license_label)
        left.addWidget(info_card)

        links_card, links_layout = self._card(g("official_links"))
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        github_btn = PushButton(g("github_button"))
        github_btn.clicked.connect(lambda: self._open(_GITHUB_URL, "open_github_failed"))
        row1.addWidget(github_btn)
        discord_btn = PushButton(g("discord_button"))
        discord_btn.setEnabled(False)
        discord_btn.clicked.connect(lambda: QMessageBox.information(self, g("info"), g("discord_placeholder_message")))
        row1.addWidget(discord_btn)
        row1.addStretch(1)
        links_layout.addLayout(row1)
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        sid_btn = PushButton(g("sid_toolbox_button"))
        sid_btn.clicked.connect(lambda: self._open(_SID_TOOLBOX_URL, "open_sid_toolbox_failed"))
        row2.addWidget(sid_btn)
        row2.addStretch(1)
        links_layout.addLayout(row2)
        left.addWidget(links_card)
        left.addStretch(1)

        right = QVBoxLayout()
        right.setSpacing(12)
        support_card, support_layout = self._card(g("support_developer"))
        support_text = QLabel(g("support_text"))
        support_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._apply_style(support_text, ("label", "success", 13, None, False))
        support_layout.addWidget(support_text)

        sponsor_row1 = QHBoxLayout()
        sponsor_row1.setSpacing(8)
        ecpay_btn = PushButton(g("ecpay_button"))
        ecpay_btn.clicked.connect(lambda: self._open(_ECPAY_URL, "open_ecpay_failed"))
        sponsor_row1.addWidget(ecpay_btn)
        paypal_btn = PushButton(g("paypal_button"))
        paypal_btn.clicked.connect(lambda: self._open(_PAYPAL_URL, "open_paypal_failed"))
        sponsor_row1.addWidget(paypal_btn)
        support_layout.addLayout(sponsor_row1)

        afdian_btn = PushButton(g("afdian_button"))
        afdian_btn.clicked.connect(lambda: self._open(_AFDIAN_URL, "open_afdian_failed"))
        support_layout.addWidget(afdian_btn)
        support_layout.addStretch(1)
        right.addWidget(support_card)
        right.addStretch(1)

        body.addLayout(left, 3)
        body.addLayout(right, 2)
        root.addLayout(body, 1)

        # ── 免責聲明 ──
        disclaimer_card, disclaimer_layout = self._card(g("important_disclaimer"))
        disclaimer_label = QLabel(g("disclaimer_text"))
        disclaimer_label.setWordWrap(True)
        self._apply_style(disclaimer_label, ("label", "error", 12, None, False))
        disclaimer_layout.addWidget(disclaimer_label)
        root.addWidget(disclaimer_card)

        self.refresh_usage_time()

    # ────────────────────────────────────────────────────
    #  使用時間顯示
    # ────────────────────────────────────────────────────

    def refresh_usage_time(self):
        if self.usage_time_label is not None:
            usage_time_text = format_usage_time(self._app.total_usage_time, lang=self._app.current_language)
            self.usage_time_label.setText(self._app.get_text("total_usage_time").format(time=usage_time_text))

    # ── 語言更新（整頁重建）──────────────────────────

    def update_language(self):
        self._rebuild_content()

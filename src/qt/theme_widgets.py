"""共用主題元件基類（Phase 2E 抽出）。

Monitor Dialog（Phase 2D）與 Inventory Dialog（Phase 2E）需要同一套
「樣式登記 + refresh_theme()」機制：登記表只保存 token 名稱與非色彩樣式，
切換主題時才解析成當前主題重上 QSS —— 不關閉、不重建、不動輸入值與版面。

抽出此基類是為了讓兩個頁面共用同一份生命週期邏輯，而不是各寫一份；
各頁面仍各自實作 `_style_qss()`，因此版面與配色行為完全由各自的 spec 決定。

注意：本模組 import 時只會載入 PySide6（不需要 QApplication 實例），
顏色一律延遲到 `refresh_theme()` / `_style_qss()` 執行時才由 qt.theme 解析。
"""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QWidget


class ThemedDialog(QDialog):
    """對話框基類：樣式登記 + refresh_theme()。

    樣式登記只保存 token 名稱與非色彩樣式；`refresh_theme()` 才解析成當前主題，
    因此重複刷新不累積 QSS，也不重建任何元件。
    """

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app
        self._styled: list[tuple[QWidget, tuple]] = []
        self._apply_style(self, ("dialog",))

    @staticmethod
    def _style_qss(spec: tuple) -> str:
        """(種類[, token]) → QSS；顏色全部來自 qt.theme token（由子類別實作）。"""
        raise NotImplementedError

    def _apply_style(self, widget: QWidget, spec: tuple) -> None:
        """套用樣式並登記，供 refresh_theme() 重上（同一元件重複套用只更新 spec）。"""
        for i, (w, _) in enumerate(self._styled):
            if w is widget:
                self._styled[i] = (widget, spec)
                break
        else:
            self._styled.append((widget, spec))
        widget.setStyleSheet(self._style_qss(spec))

    def refresh_theme(self) -> None:
        """主題切換刷新：只重上既有元件 QSS（不關閉、不重建、不動輸入值與版面）。"""
        alive: list[tuple[QWidget, tuple]] = []
        for widget, spec in self._styled:
            try:
                widget.setStyleSheet(self._style_qss(spec))
            except RuntimeError:
                continue  # 已被刪除的舊元件
            alive.append((widget, spec))
        self._styled = alive

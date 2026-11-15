"""MonitorTab 的兩個校準視窗（PySide6 移植）：血條顏色偵測 / 介面UI閾值。

對應 tk 版 `tab_monitor.py` 的 `adjust_colors` 與 `adjust_interface_ui_thresholds`。
改寫點：tk 的 validate command → QIntValidator/QDoubleValidator；apply 後同步 app 屬性 + config。

Phase 2D（主題遷移）：顏色一律取自 `qt.theme` token（不再寫死 HEX）。
Dialog 建立當下即套用「當前」主題；`refresh_theme()` 只重上 QSS，不關閉、不重建、
不動輸入值與版面（由 MonitorTab 呼叫，見 `monitor.py`）。
"""

from PySide6.QtGui import QDoubleValidator, QIntValidator
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import LineEdit, PushButton

from qt.theme import current_tokens
from qt.theme_widgets import ThemedDialog


class _ThemedDialog(ThemedDialog):
    """Monitor Dialog 基類：樣式登記 + refresh_theme()。

    樣式登記與 `refresh_theme()` 的生命週期邏輯來自共用基類
    `qt.theme_widgets.ThemedDialog`（Phase 2E 抽出，讓 Inventory Dialog 沿用
    同一套已驗證機制）；此處只負責 Monitor 專屬的 QSS 種類與版面工具，
    樣式行為與 Phase 2D 完全一致。
    """

    # ── 主題樣式 ──────────────────────────────────────────────

    @staticmethod
    def _style_qss(spec: tuple) -> str:
        """(種類[, token]) → QSS；顏色全部來自 qt.theme token。"""
        kind = spec[0]
        tok = current_tokens()
        if kind == "dialog":
            # 原生 QDialog 會用 OS palette 的 Window 色鋪底（light 主題下是深色殘留），改用 token。
            return f"QDialog {{ background-color: {tok['window_bg']}; }}"
        if kind == "group":
            # 群組框原本只寫 border + color，內部由 OS palette 鋪底；改用 surface 當卡片底。
            return (
                f"QGroupBox {{ border: 1px solid {tok['border_strong']}; border-radius: 8px; "
                f"margin-top: 10px; padding-top: 6px; color: {tok['fg']}; background: {tok['surface']}; }}"
                "QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }"
            )
        if kind == "scroll":
            return "QScrollArea { background: transparent; border: none; }"
        if kind == "title":
            return f"font-size: 15px; font-weight: 600; color: {tok['fg']};"
        if kind == "value":
            return f"font-size: 13px; font-weight: 700; color: {tok[spec[1]]};"
        if kind == "hint":
            return f"color: {tok['fg_muted']}; font-size: 13px;"
        if kind == "label":
            return f"color: {tok['fg']};"
        raise ValueError(f"未知的樣式種類: {kind}")

    # ── 共用元件 ──────────────────────────────────────────────

    def _section(self, title: str) -> QGroupBox:
        box = QGroupBox(title)
        self._apply_style(box, ("group",))
        return box

    def _entry(self, default, validator) -> LineEdit:
        edit = LineEdit()
        edit.setText(str(default))
        edit.setValidator(validator)
        edit.setFixedWidth(100)
        return edit

    def _row(self, grid, row, label_text, value_text, tone: str) -> None:
        """左側說明文字 + 右側目前值（值色依語意 token：info/success/error/warning）。"""
        label = QLabel(label_text)
        self._apply_style(label, ("label",))
        grid.addWidget(label, row, 0)
        current = QLabel(value_text)
        self._apply_style(current, ("value", tone))
        grid.addWidget(current, row, 1)

    def _add_entry(self, grid, row, entry, explanation_key, get_text) -> None:
        grid.addWidget(entry, row, 1)
        if explanation_key:
            explanation = get_text(explanation_key)
            hint = QLabel(explanation)
            hint.setWordWrap(True)
            self._apply_style(hint, ("hint",))
            grid.addWidget(hint, row + 1, 0, 1, 2)

    def _button_row(self, on_apply, on_reset) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        apply_btn = PushButton(self._app.get_text("apply_settings"))
        apply_btn.clicked.connect(on_apply)
        reset_btn = PushButton(self._app.get_text("reset_to_defaults"))
        reset_btn.clicked.connect(on_reset)
        cancel_btn = PushButton(self._app.get_text("cancel"))
        cancel_btn.clicked.connect(self.reject)
        row.addWidget(apply_btn)
        row.addWidget(reset_btn)
        row.addWidget(cancel_btn)
        row.addStretch(1)
        return row

    def _scroll_area(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._apply_style(scroll, ("scroll",))
        return scroll

    def _scroll_content(self, scroll: QScrollArea) -> QWidget:
        """建立捲動內容並關閉 viewport/content 的自動鋪底。

        `setWidget()` 會把 content 的 autoFillBackground 重設為 True，因此必須在
        setWidget 之後才關閉，否則仍會用 OS palette 色鋪底（light 主題下是深色殘留）。
        """
        content = QWidget()
        scroll.setWidget(content)
        content.setAutoFillBackground(False)
        scroll.viewport().setAutoFillBackground(False)
        return content


class AdjustColorsDialog(_ThemedDialog):
    """血條偵測校準：health_threshold / red_h_range / green_h_range / HSV 下限。"""

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self.setWindowTitle(app.get_text("adjust_colors_title"))
        self.resize(700, 640)
        self.setMinimumWidth(620)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel(app.get_text("adjust_colors_main_title"))
        self._apply_style(title, ("title",))
        root.addWidget(title)

        scroll = self._scroll_area()
        content = self._scroll_content(scroll)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(4, 4, 4, 4)
        content_layout.setSpacing(10)
        root.addWidget(scroll, 1)

        g = app.get_text
        float_validator = QDoubleValidator(0.0, 1.0, 3)
        int_validator = QIntValidator(0, 255)

        # 健康像素比例閾值
        health_box = self._section(g("health_pixel_ratio_threshold"))
        health_grid = QGridLayout(health_box)
        health_grid.setContentsMargins(12, 12, 12, 12)
        self._row(health_grid, 0, g("current_value"), f"{app.health_threshold}", "info_soft")
        self._add_entry(health_grid, 1, self._entry(app.health_threshold, float_validator), "health_pixel_ratio_explanation", g)
        content_layout.addWidget(health_box)

        # 色相範圍
        color_box = self._section(g("color_range_settings"))
        color_grid = QGridLayout(color_box)
        color_grid.setContentsMargins(12, 12, 12, 12)
        color_grid.setColumnStretch(0, 1)
        color_grid.setColumnStretch(1, 0)
        self._row(color_grid, 0, g("red_h_range"), f"{app.red_h_range}", "error_soft")
        self._add_entry(color_grid, 1, self._entry(app.red_h_range, int_validator), "red_h_range_explanation", g)
        self._row(color_grid, 3, g("green_h_range"), f"{app.green_h_range}", "success_soft")
        self._add_entry(color_grid, 4, self._entry(app.green_h_range, int_validator), "green_h_range_explanation", g)
        content_layout.addWidget(color_box)

        # HSV 微調 — 紅/綠分區避免同 grid 同 row 覆蓋（英文長文案疊影，見截圖）
        red_hsv_box = self._section(g("hsv_fine_tuning") + " — " + g("red_min_saturation").rstrip(":"))
        red_hsv_grid = QGridLayout(red_hsv_box)
        red_hsv_grid.setContentsMargins(12, 12, 12, 12)
        red_hsv_grid.setColumnStretch(0, 1)
        red_hsv_grid.setColumnStretch(1, 0)
        self._row(red_hsv_grid, 0, g("red_min_saturation"), f"{app.red_saturation_min}", "error_soft")
        self._add_entry(red_hsv_grid, 1, self._entry(app.red_saturation_min, int_validator), None, g)
        self._row(red_hsv_grid, 2, g("red_min_brightness"), f"{app.red_value_min}", "error_soft")
        self._add_entry(red_hsv_grid, 3, self._entry(app.red_value_min, int_validator), "red_hsv_explanation", g)
        content_layout.addWidget(red_hsv_box)

        green_hsv_box = self._section(g("hsv_fine_tuning") + " — " + g("green_min_saturation").rstrip(":"))
        green_hsv_grid = QGridLayout(green_hsv_box)
        green_hsv_grid.setContentsMargins(12, 12, 12, 12)
        green_hsv_grid.setColumnStretch(0, 1)
        green_hsv_grid.setColumnStretch(1, 0)
        self._row(green_hsv_grid, 0, g("green_min_saturation"), f"{app.green_saturation_min}", "success_soft")
        self._add_entry(green_hsv_grid, 1, self._entry(app.green_saturation_min, int_validator), None, g)
        self._row(green_hsv_grid, 2, g("green_min_brightness"), f"{app.green_value_min}", "success_soft")
        self._add_entry(green_hsv_grid, 3, self._entry(app.green_value_min, int_validator), "green_hsv_explanation", g)
        content_layout.addWidget(green_hsv_box)

        content_layout.addStretch(1)
        root.addLayout(self._button_row(self._apply, self._reset))

    def _values(self):
        return [e.text() for e in self.findChildren(LineEdit)]

    def _apply(self):
        g = self._app.get_text
        texts = self._values()
        try:
            new_health = float(texts[0])
            new_red_h, new_green_h, new_red_sat, new_red_val, new_green_sat, new_green_val = map(int, texts[1:7])
        except ValueError:
            QMessageBox.warning(self, g("input_error"), g("enter_valid_number"))
            return

        checks = [
            (0.0 <= new_health <= 1.0, "health_threshold_range_error"),
            (0 <= new_red_h <= 20, "red_h_range_error"),
            (30 <= new_green_h <= 90, "green_h_range_error"),
            (50 <= new_red_sat <= 255, "red_saturation_range_error"),
            (50 <= new_red_val <= 255, "red_value_range_error"),
            (50 <= new_green_sat <= 255, "green_saturation_range_error"),
            (50 <= new_green_val <= 255, "green_value_range_error"),
        ]
        for ok, error_key in checks:
            if not ok:
                QMessageBox.warning(self, g("input_error"), g(error_key))
                return

        app = self._app
        app.health_threshold = new_health
        app.red_h_range = new_red_h
        app.green_h_range = new_green_h
        app.red_saturation_min = new_red_sat
        app.red_value_min = new_red_val
        app.green_saturation_min = new_green_sat
        app.green_value_min = new_green_val
        app.config.update(
            {
                "health_threshold": new_health,
                "red_h_range": new_red_h,
                "green_h_range": new_green_h,
                "red_saturation_min": new_red_sat,
                "red_value_min": new_red_val,
                "green_saturation_min": new_green_sat,
                "green_value_min": new_green_val,
            }
        )
        app.save_config()
        QMessageBox.information(
            self,
            g("settings_applied"),
            g("color_settings_updated").format(
                health_threshold=new_health,
                red_h_range=new_red_h,
                green_h_range=new_green_h,
                red_saturation_min=new_red_sat,
                red_value_min=new_red_val,
                green_saturation_min=new_green_sat,
                green_value_min=new_green_val,
            ),
        )
        self.accept()

    def _reset(self):
        g = self._app.get_text
        defaults = [0.3, 10, 40, 50, 50, 50, 50]
        for edit, value in zip(self.findChildren(LineEdit), defaults):
            edit.setText(str(value))
        QMessageBox.information(self, g("reset_completed"), g("reset_completed_message"))
        self.raise_()
        self.activateWindow()


class AdjustInterfaceUiDialog(_ThemedDialog):
    """介面UI出現判斷閾值：MSE / SSIM / 直方圖 / 顏色差異。"""

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self.setWindowTitle(app.get_text("adjust_interface_ui_title"))
        self.resize(520, 560)
        self.setMinimumWidth(480)

        g = app.get_text
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel(g("adjust_interface_ui_main_title"))
        self._apply_style(title, ("title",))
        root.addWidget(title)

        scroll = self._scroll_area()
        content = self._scroll_content(scroll)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(4, 4, 4, 4)
        content_layout.setSpacing(10)
        root.addWidget(scroll, 1)

        self._entries = {}

        def add_section(title_key, current_key, current_value, color, entry, empty_key, invalid_key, range_key, explanation_key, lo, hi):
            box = self._section(g(title_key))
            grid = QGridLayout(box)
            grid.setContentsMargins(12, 12, 12, 12)
            self._row(grid, 0, g("current_value"), f"{current_value}", color)
            grid.addWidget(entry, 1, 1)
            self._entries[current_key] = (entry, empty_key, invalid_key, range_key, lo, hi)
            if explanation_key:
                hint = QLabel(g(explanation_key))
                hint.setWordWrap(True)
                self._apply_style(hint, ("hint",))
                grid.addWidget(hint, 2, 0, 1, 2)
            content_layout.addWidget(box)

        mse = LineEdit()
        mse.setValidator(QIntValidator(0, 20000))
        add_section("mse_threshold_title", "mse", app.interface_ui_mse_threshold, "info_soft", mse, "mse_threshold_empty", "mse_invalid_number", "mse_range_error", "mse_explanation", 100, 2000)

        for key, label_key, current, color, empty_key, invalid_key, range_key, explanation_key, lo, hi in [
            ("ssim", "ssim_threshold_title", app.interface_ui_ssim_threshold, "success_soft", "ssim_threshold_empty", "ssim_invalid_number", "ssim_range_error", "ssim_explanation", 0.0, 1.0),
            (
                "hist",
                "histogram_threshold_title",
                app.interface_ui_hist_threshold,
                "warning_soft",
                "histogram_threshold_empty",
                "histogram_invalid_number",
                "histogram_range_error",
                "histogram_explanation",
                0.0,
                1.0,
            ),
            (
                "color",
                "color_diff_threshold_title",
                app.interface_ui_color_threshold,
                "error_soft",
                "color_threshold_empty",
                "color_invalid_number",
                "color_range_error",
                "color_diff_explanation",
                5,
                100,
            ),
        ]:
            validator = QDoubleValidator(0.0, 2000.0, 3) if key != "color" else QIntValidator(0, 20000)
            entry = LineEdit()
            entry.setValidator(validator)
            add_section(label_key, key, current, color, entry, empty_key, invalid_key, range_key, explanation_key, lo, hi)

        content_layout.addStretch(1)
        root.addLayout(self._button_row(self._apply, self._reset))

    def _apply(self):
        g = self._app.get_text
        parsed = {}
        for key, (entry, empty_key, invalid_key, range_key, lo, hi) in self._entries.items():
            text = entry.text().strip()
            if not text:
                QMessageBox.warning(self, g("input_error"), g(empty_key))
                return
            try:
                value = int(float(text)) if key in ("mse", "color") else float(text)
            except ValueError:
                QMessageBox.warning(self, g("input_error"), g(invalid_key))
                return
            if not (lo <= value <= hi):
                QMessageBox.warning(self, g("input_error"), g(range_key))
                return
            parsed[key] = value

        app = self._app
        app.interface_ui_mse_threshold = parsed["mse"]
        app.interface_ui_ssim_threshold = parsed["ssim"]
        app.interface_ui_hist_threshold = parsed["hist"]
        app.interface_ui_color_threshold = parsed["color"]
        app.config.update(
            {
                "interface_ui_mse_threshold": parsed["mse"],
                "interface_ui_ssim_threshold": parsed["ssim"],
                "interface_ui_hist_threshold": parsed["hist"],
                "interface_ui_color_threshold": parsed["color"],
            }
        )
        app.save_config()
        QMessageBox.information(
            self,
            g("settings_applied"),
            g("interface_ui_settings_updated").format(
                mse_threshold=parsed["mse"],
                ssim_threshold=parsed["ssim"],
                hist_threshold=parsed["hist"],
                color_threshold=parsed["color"],
            ),
        )
        self.accept()

    def _reset(self):
        g = self._app.get_text
        defaults = {"mse": "800", "ssim": "0.6", "hist": "0.7", "color": "35"}
        for key, (entry, *_rest) in self._entries.items():
            entry.setText(defaults[key])
        QMessageBox.information(self, g("reset_completed"), g("reset_completed_message"))
        self.raise_()
        self.activateWindow()

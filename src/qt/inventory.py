"""InventoryTab（Qt 版）— 一鍵清包分頁（Phase 5a：UI 骨架 + 語言 + config 載入/儲存）。

對應 tk 版 `tab_inventory.py`。Phase 5b 將補上三種 region 框選、預覽渲染與
exclusion click；Phase 5c 移植 F3 清包 / F6 拾取與介面UI偵測。
worker thread 的 UI 更新一律走 Signal（延續 MonitorTab/StatusTab 模式）。
"""

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import CheckBox, PushButton, RadioButton

from inventory_utils import calculate_inventory_grid_positions
from qt.monitor import _pil_to_qpixmap

# ── 色票（與 qt.monitor 對齊）──
ERROR = "#f38ba8"
SUCCESS = "#a6e3a1"
INFO = "#89b4fa"
MUTED = "#b8b8c8"
INPUT_BG = "#1e1e2e"
GROUP_BORDER = "#3d3d5c"


class _InventorySignals(QObject):
    """worker → UI 更新（Phase 5b/c 使用；先定義避免 __init__ 重構）。"""

    status_message = Signal(str, str)
    preview_ready = Signal(object)


class InventoryTab(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app

        # ── 狀態（對應 tk 版 tab_inventory.InventoryTab.__init__）──
        self._preview_has_image = False
        self._preview_meta = None
        self._inventory_click_mode = "exclude"
        self.excluded_inventory_slots = set()
        self.grid_offset_x = 0
        self.grid_offset_y = 0
        self.inventory_region = None
        self.inventory_ui_region = None
        self.empty_inventory_colors = []
        self.occupied_threshold = 50
        self.last_inventory_window = None
        self.last_inventory_ui_window = None
        self.last_interface_ui_window = None
        self.pickup_coordinates = None
        self.continuous_setup_running = False
        self.occupied_slots_cache = set()
        self.inventory_grid_positions = []
        self.inventory_ui_screenshot = None
        self.interface_ui_screenshot = None
        self.clear_click_mode = "left"

        self._signals = _InventorySignals(self)

        self._load_config()
        self._build_ui()
        self._apply_config_to_ui()

    # ────────────────────────── config ──────────────────────────

    def _load_config(self):
        cfg = self._app.config
        self.inventory_region = cfg.get("inventory_region")
        self.empty_inventory_colors = [tuple(c) for c in cfg.get("empty_inventory_colors", [])]
        self.grid_offset_x = cfg.get("grid_offset_x", 0)
        self.grid_offset_y = cfg.get("grid_offset_y", 0)
        self.excluded_inventory_slots = set(cfg.get("excluded_inventory_slots", []))
        self.inventory_ui_region = cfg.get("inventory_ui_region")
        self.pickup_coordinates = cfg.get("pickup_coordinates")
        self.clear_click_mode = cfg.get("inventory_clear_click_mode", "left")
        positions = [tuple(p) for p in cfg.get("inventory_grid_positions", [])]
        self.inventory_grid_positions = positions or calculate_inventory_grid_positions(self.inventory_region, self.grid_offset_x, self.grid_offset_y)

    def save_inventory_config(self):
        """儲存背包設定（對應 tk 版 save_inventory_config）。"""
        try:
            cfg = self._app.config
            cfg["inventory_region"] = self.inventory_region
            cfg["empty_inventory_colors"] = self.empty_inventory_colors
            cfg["inventory_grid_positions"] = [list(pos) for pos in self.inventory_grid_positions]
            cfg["grid_offset_x"] = self.grid_offset_x
            cfg["grid_offset_y"] = self.grid_offset_y
            cfg["excluded_inventory_slots"] = sorted(self.excluded_inventory_slots)
            cfg["inventory_window_title"] = self._app.monitor_tab.window_var.get()
            cfg["inventory_ui_region"] = self.inventory_ui_region
            cfg["inventory_clear_click_mode"] = self.clear_click_mode
            if self.pickup_coordinates is not None:
                cfg["pickup_coordinates"] = self.pickup_coordinates
            self._app.save_config()
            self._app.add_status_message(self._app.get_text("inventory_settings_saved"), "success")
        except Exception as e:
            self._app.add_status_message(self._app.get_text("save_failed").format(error=str(e)), "error")

    def refresh_config_display(self):
        """同步各狀態標籤（空格顏色數、背包UI狀態、取物座標數）。"""
        if self.empty_inventory_colors:
            recorded = len([c for c in self.empty_inventory_colors if c != (0, 0, 0)])
            self.empty_color_label.setText(self._app.get_text("recorded_colors_template").format(count=recorded))
            self.empty_color_label.setStyleSheet(self._value_label_style(SUCCESS))
        else:
            self.empty_color_label.setText(self._app.get_text("not_recorded"))
            self.empty_color_label.setStyleSheet(self._value_label_style(MUTED))

        if self.inventory_ui_region and self.inventory_ui_screenshot is not None:
            self.inventory_ui_label.setText(self._app.get_text("inventory_ui_recorded"))
            self.inventory_ui_label.setStyleSheet(self._value_label_style(SUCCESS))
        else:
            self.inventory_ui_label.setText(self._app.get_text("not_recorded"))
            self.inventory_ui_label.setStyleSheet(self._value_label_style(MUTED))

        valid_coords = sum(1 for x, y in (self.pickup_coordinates or []) if x != 0 or y != 0)
        self.pickup_coords_label.setText(self._app.get_text("coordinates_count").format(count=valid_coords))

        self.occupied_label.setText(self._app.get_text("slots_count").format(count=len(self.occupied_slots_cache)))

    # ────────────────────────── UI ──────────────────────────

    def _styled_group(self, title):
        box = QGroupBox(title)
        box.setStyleSheet(
            f"QGroupBox {{ border: 1px solid {GROUP_BORDER}; border-radius: 8px; margin-top: 10px; padding-top: 6px; color: #f8f8f2; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; }}"
        )
        return box

    @staticmethod
    def _value_label_style(color):
        return f"background-color: {INPUT_BG}; border: 1px solid {GROUP_BORDER}; border-radius: 4px; padding: 4px 8px; color: {color};"

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        self.page_title_label = QLabel(self._app.get_text("inventory_title"))
        self.page_title_label.setStyleSheet("font-size: 20px; font-weight: 600; color: #f8f8f2;")
        root.addWidget(self.page_title_label)

        body = QHBoxLayout()
        body.setSpacing(12)
        root.addLayout(body, 1)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_content = QWidget()
        left_scroll.setWidget(left_content)
        left_layout = QVBoxLayout(left_content)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        body.addWidget(left_scroll, 3)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        body.addWidget(right, 2)

        self._build_inventory_settings_group(left_layout)
        self._build_control_group(left_layout)
        self._build_status_group(left_layout)
        self._build_pickup_group(left_layout)
        self._build_ui_preview_group(left_layout)
        left_layout.addStretch(1)

        self._build_preview_group(right_layout)
        right_layout.addStretch(1)

    def _build_inventory_settings_group(self, layout):
        self.inventory_settings_frame = self._styled_group(self._app.get_text("inventory_settings"))
        grid = QGridLayout(self.inventory_settings_frame)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        layout.addWidget(self.inventory_settings_frame)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.select_inventory_region_btn = PushButton(self._app.get_text("select_inventory_region"))
        self.select_inventory_region_btn.setToolTip(self._app.get_text("select_inventory_region_tip"))
        self.select_inventory_region_btn.clicked.connect(self._not_implemented)
        row.addWidget(self.select_inventory_region_btn)

        self.record_empty_color_btn = PushButton(self._app.get_text("record_empty_color"))
        self.record_empty_color_btn.setToolTip(self._app.get_text("record_empty_color_tip"))
        self.record_empty_color_btn.clicked.connect(self._not_implemented)
        row.addWidget(self.record_empty_color_btn)

        self.select_inventory_ui_btn = PushButton(self._app.get_text("select_inventory_ui"))
        self.select_inventory_ui_btn.setToolTip(self._app.get_text("select_inventory_ui_tip"))
        self.select_inventory_ui_btn.clicked.connect(self._not_implemented)
        row.addWidget(self.select_inventory_ui_btn)

        row.addStretch(1)
        grid.addLayout(row, 0, 0, 1, 2)

        self.record_status_label = QLabel(self._app.get_text("record_status"))
        grid.addWidget(self.record_status_label, 1, 0)

        self.empty_color_label = QLabel(self._app.get_text("not_recorded"))
        self.empty_color_label.setStyleSheet(self._value_label_style(MUTED))
        grid.addWidget(self.empty_color_label, 1, 1)

        self.inventory_ui_status_label = QLabel(self._app.get_text("inventory_ui_status"))
        grid.addWidget(self.inventory_ui_status_label, 2, 0)

        self.inventory_ui_label = QLabel(self._app.get_text("not_recorded"))
        self.inventory_ui_label.setStyleSheet(self._value_label_style(MUTED))
        grid.addWidget(self.inventory_ui_label, 2, 1)

        grid.setColumnStretch(1, 1)

    def _build_control_group(self, layout):
        self.control_frame = self._styled_group(self._app.get_text("control_panel"))
        grid = QGridLayout(self.control_frame)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        layout.addWidget(self.control_frame)

        self.test_clear_inventory_btn = PushButton(self._app.get_text("test_clear_inventory"))
        self.test_clear_inventory_btn.setToolTip(self._app.get_text("test_clear_inventory_tip"))
        self.test_clear_inventory_btn.clicked.connect(self._not_implemented)
        grid.addWidget(self.test_clear_inventory_btn, 0, 0)

        self.save_inventory_settings_btn = PushButton(self._app.get_text("save_inventory_settings"))
        self.save_inventory_settings_btn.clicked.connect(self.save_inventory_config)
        grid.addWidget(self.save_inventory_settings_btn, 0, 1)

        self.clear_click_mode_label = QLabel(self._app.get_text("clear_click_mode"))
        grid.addWidget(self.clear_click_mode_label, 1, 0)

        click_mode = QHBoxLayout()
        click_mode.setSpacing(8)
        self.clear_click_left_radio = RadioButton(self._app.get_text("clear_click_left"))
        self.clear_click_left_radio.setToolTip(self._app.get_text("clear_click_left_tip"))
        self.clear_click_left_radio.toggled.connect(lambda checked: self._set_click_mode("left") if checked else None)
        click_mode.addWidget(self.clear_click_left_radio)

        self.clear_click_right_radio = RadioButton(self._app.get_text("clear_click_right"))
        self.clear_click_right_radio.setToolTip(self._app.get_text("clear_click_right_tip"))
        self.clear_click_right_radio.toggled.connect(lambda checked: self._set_click_mode("right") if checked else None)
        click_mode.addWidget(self.clear_click_right_radio)
        click_mode.addStretch(1)
        grid.addLayout(click_mode, 1, 1)

        self.gui_settings_label = QLabel(self._app.get_text("gui_settings"))
        grid.addWidget(self.gui_settings_label, 2, 0)

        self.always_on_top_check = CheckBox(self._app.get_text("always_on_top"))
        self.always_on_top_check.toggled.connect(self._on_always_on_top_toggled)
        grid.addWidget(self.always_on_top_check, 2, 1)

        grid.setColumnStretch(1, 1)

    def _build_status_group(self, layout):
        self.status_frame = self._styled_group(self._app.get_text("status"))
        grid = QGridLayout(self.status_frame)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        layout.addWidget(self.status_frame)

        self.inventory_f3_label = QLabel(self._app.get_text("f3_hotkey"))
        grid.addWidget(self.inventory_f3_label, 0, 0)

        self.inventory_status_label = QLabel(self._app.get_text("ready"))
        self.inventory_status_label.setStyleSheet(f"color: {SUCCESS};")
        grid.addWidget(self.inventory_status_label, 0, 1)

        self.pause_status_label_title = QLabel(self._app.get_text("global_pause"))
        grid.addWidget(self.pause_status_label_title, 1, 0)

        self.pause_status_label = QLabel(self._app.get_text("normal_operation"))
        self.pause_status_label.setStyleSheet(f"color: {SUCCESS};")
        grid.addWidget(self.pause_status_label, 1, 1)

        grid.setColumnStretch(1, 1)

    def _build_pickup_group(self, layout):
        self.pickup_frame = self._styled_group(self._app.get_text("pickup_coordinates"))
        grid = QGridLayout(self.pickup_frame)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        layout.addWidget(self.pickup_frame)

        self.setup_pickup_coordinates_btn = PushButton(self._app.get_text("setup_pickup_coordinates"))
        self.setup_pickup_coordinates_btn.setToolTip(self._app.get_text("setup_pickup_coordinates_tip"))
        self.setup_pickup_coordinates_btn.clicked.connect(self._not_implemented)
        grid.addWidget(self.setup_pickup_coordinates_btn, 0, 0)

        self.save_pickup_coordinates_btn = PushButton(self._app.get_text("save_coordinates"))
        self.save_pickup_coordinates_btn.clicked.connect(self._not_implemented)
        grid.addWidget(self.save_pickup_coordinates_btn, 0, 1)

        self.coordinates_set_label = QLabel(self._app.get_text("coordinates_set"))
        grid.addWidget(self.coordinates_set_label, 1, 0)

        self.pickup_coords_label = QLabel(self._app.get_text("coordinates_count").format(count=0))
        self.pickup_coords_label.setStyleSheet(f"color: {MUTED};")
        grid.addWidget(self.pickup_coords_label, 1, 1)

        self.pickup_f6_label = QLabel(self._app.get_text("f6_hotkey"))
        grid.addWidget(self.pickup_f6_label, 2, 0)

        self.pickup_status_label = QLabel(self._app.get_text("ready"))
        self.pickup_status_label.setStyleSheet(f"color: {SUCCESS};")
        grid.addWidget(self.pickup_status_label, 2, 1)

        grid.setColumnStretch(1, 1)

    def _build_ui_preview_group(self, layout):
        self.ui_preview_frame = self._styled_group(self._app.get_text("inventory_ui_screenshot"))
        vbox = QVBoxLayout(self.ui_preview_frame)
        vbox.setContentsMargins(12, 12, 12, 12)
        vbox.setSpacing(6)
        layout.addWidget(self.ui_preview_frame)

        self.ui_preview_label = QLabel(self._app.get_text("inventory_ui_screenshot_not_set"))
        self.ui_preview_label.setFixedHeight(150)
        self.ui_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ui_preview_label.setStyleSheet(f"background-color: {INPUT_BG}; border: 1px solid {GROUP_BORDER}; border-radius: 4px; color: {MUTED};")
        vbox.addWidget(self.ui_preview_label)

        self.ui_preview_hint_label = QLabel(self._app.get_text("inventory_ui_screenshot_hint"))
        self.ui_preview_hint_label.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        vbox.addWidget(self.ui_preview_hint_label)

    def _build_preview_group(self, layout):
        self.preview_frame = self._styled_group(self._app.get_text("inventory_preview"))
        vbox = QVBoxLayout(self.preview_frame)
        vbox.setContentsMargins(12, 12, 12, 12)
        vbox.setSpacing(8)
        layout.addWidget(self.preview_frame)

        stats = QHBoxLayout()
        self.occupied_label_title = QLabel(self._app.get_text("occupied_slots"))
        stats.addWidget(self.occupied_label_title)
        self.occupied_label = QLabel(self._app.get_text("slots_count").format(count=0))
        self.occupied_label.setStyleSheet(f"color: {INFO}; font-size: 13px; font-weight: 600;")
        stats.addWidget(self.occupied_label)
        stats.addStretch(1)
        vbox.addLayout(stats)

        self.grid_adjustment_label = QLabel(self._app.get_text("grid_alignment_adjustment"))
        self.grid_adjustment_label.setStyleSheet(f"color: {MUTED};")
        vbox.addWidget(self.grid_adjustment_label)

        offset_grid = QGridLayout()
        offset_grid.setHorizontalSpacing(6)
        offset_grid.setVerticalSpacing(4)

        self.horizontal_label = QLabel(self._app.get_text("horizontal"))
        offset_grid.addWidget(self.horizontal_label, 0, 0)

        left_btn = PushButton("◀")
        left_btn.setFixedWidth(40)
        left_btn.clicked.connect(lambda: self.adjust_grid_offset(-1, 0))
        offset_grid.addWidget(left_btn, 0, 1)

        self.offset_x_label = QLabel("0")
        self.offset_x_label.setFixedWidth(48)
        self.offset_x_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.offset_x_label.setStyleSheet(self._value_label_style("#f8f8f2"))
        offset_grid.addWidget(self.offset_x_label, 0, 2)

        right_btn = PushButton("▶")
        right_btn.setFixedWidth(40)
        right_btn.clicked.connect(lambda: self.adjust_grid_offset(1, 0))
        offset_grid.addWidget(right_btn, 0, 3)

        self.vertical_label = QLabel(self._app.get_text("vertical"))
        offset_grid.addWidget(self.vertical_label, 1, 0)

        up_btn = PushButton("▲")
        up_btn.setFixedWidth(40)
        up_btn.clicked.connect(lambda: self.adjust_grid_offset(0, -1))
        offset_grid.addWidget(up_btn, 1, 1)

        self.offset_y_label = QLabel("0")
        self.offset_y_label.setFixedWidth(48)
        self.offset_y_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.offset_y_label.setStyleSheet(self._value_label_style("#f8f8f2"))
        offset_grid.addWidget(self.offset_y_label, 1, 2)

        down_btn = PushButton("▼")
        down_btn.setFixedWidth(40)
        down_btn.clicked.connect(lambda: self.adjust_grid_offset(0, 1))
        offset_grid.addWidget(down_btn, 1, 3)

        self.reset_offset_btn = PushButton(self._app.get_text("reset"))
        self.reset_offset_btn.clicked.connect(self.reset_grid_offset)
        offset_grid.addWidget(self.reset_offset_btn, 1, 4)

        offset_grid.setColumnStretch(4, 1)
        vbox.addLayout(offset_grid)

        self.inventory_preview_label = QLabel(self._app.get_text("select_inventory_region_first"))
        self.inventory_preview_label.setMinimumSize(300, 200)
        self.inventory_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.inventory_preview_label.setStyleSheet(f"background-color: {INPUT_BG}; border: 1px solid {GROUP_BORDER}; border-radius: 4px; color: {MUTED};")
        vbox.addWidget(self.inventory_preview_label, 1)

        self.inventory_exclude_hint = QLabel(self._app.get_text("inventory_exclude_hint"))
        self.inventory_exclude_hint.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        vbox.addWidget(self.inventory_exclude_hint)

    # ────────────────────────── 預覽輔助 ──────────────────────────

    def set_preview_placeholder(self, text, color=MUTED):
        self.inventory_preview_label.setText(text)
        self.inventory_preview_label.setStyleSheet(f"background-color: {INPUT_BG}; border: 1px solid {GROUP_BORDER}; border-radius: 4px; color: {color};")
        self._preview_has_image = False

    def set_preview_pil(self, pil_img):
        pix = _pil_to_qpixmap(pil_img)
        scaled = pix.scaled(
            self.inventory_preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.inventory_preview_label.setPixmap(scaled)
        self._preview_has_image = True
        self._preview_meta = {
            "image_width": pil_img.width,
            "image_height": pil_img.height,
            "pixmap_width": scaled.width(),
            "pixmap_height": scaled.height(),
            "label_width": self.inventory_preview_label.width(),
            "label_height": self.inventory_preview_label.height(),
        }

    def set_ui_preview_placeholder(self, text, color=MUTED):
        self.ui_preview_label.setText(text)
        self.ui_preview_label.setStyleSheet(f"background-color: {INPUT_BG}; border: 1px solid {GROUP_BORDER}; border-radius: 4px; color: {color};")

    def set_ui_preview_pil(self, pil_img):
        pix = _pil_to_qpixmap(pil_img)
        scaled = pix.scaled(
            self.ui_preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.ui_preview_label.setPixmap(scaled)

    # ────────────────────────── 操作 ──────────────────────────

    def _set_click_mode(self, mode):
        self.clear_click_mode = mode

    def _on_always_on_top_toggled(self, checked):
        self._app.always_on_top = checked
        self._app.toggle_always_on_top()

    def adjust_grid_offset(self, delta_x, delta_y):
        self.grid_offset_x += delta_x
        self.grid_offset_y += delta_y
        max_offset = 20
        self.grid_offset_x = max(-max_offset, min(max_offset, self.grid_offset_x))
        self.grid_offset_y = max(-max_offset, min(max_offset, self.grid_offset_y))
        self.update_offset_labels()
        self._recompute_grid_positions()

    def reset_grid_offset(self):
        self.grid_offset_x = 0
        self.grid_offset_y = 0
        self.update_offset_labels()
        self._recompute_grid_positions()

    def update_offset_labels(self):
        self.offset_x_label.setText(str(self.grid_offset_x))
        self.offset_y_label.setText(str(self.grid_offset_y))

    def _recompute_grid_positions(self):
        self.inventory_grid_positions = calculate_inventory_grid_positions(self.inventory_region, self.grid_offset_x, self.grid_offset_y)

    def _not_implemented(self):
        self._app.add_status_message(self._app.get_text("inventory_setup_incomplete"), "warning")

    # ────────────────────────── 語言 ──────────────────────────

    def update_inventory_tab_language(self):
        try:
            self.page_title_label.setText(self._app.get_text("inventory_title"))
            self.inventory_settings_frame.setTitle(self._app.get_text("inventory_settings"))
            self.control_frame.setTitle(self._app.get_text("control_panel"))
            self.status_frame.setTitle(self._app.get_text("status"))
            self.pickup_frame.setTitle(self._app.get_text("pickup_coordinates"))
            self.ui_preview_frame.setTitle(self._app.get_text("inventory_ui_screenshot"))
            self.preview_frame.setTitle(self._app.get_text("inventory_preview"))

            self.select_inventory_region_btn.setText(self._app.get_text("select_inventory_region"))
            self.select_inventory_region_btn.setToolTip(self._app.get_text("select_inventory_region_tip"))
            self.record_empty_color_btn.setText(self._app.get_text("record_empty_color"))
            self.record_empty_color_btn.setToolTip(self._app.get_text("record_empty_color_tip"))
            self.select_inventory_ui_btn.setText(self._app.get_text("select_inventory_ui"))
            self.select_inventory_ui_btn.setToolTip(self._app.get_text("select_inventory_ui_tip"))
            self.test_clear_inventory_btn.setText(self._app.get_text("test_clear_inventory"))
            self.test_clear_inventory_btn.setToolTip(self._app.get_text("test_clear_inventory_tip"))
            self.save_inventory_settings_btn.setText(self._app.get_text("save_inventory_settings"))
            self.setup_pickup_coordinates_btn.setText(self._app.get_text("setup_pickup_coordinates"))
            self.setup_pickup_coordinates_btn.setToolTip(self._app.get_text("setup_pickup_coordinates_tip"))
            self.save_pickup_coordinates_btn.setText(self._app.get_text("save_coordinates"))

            self.record_status_label.setText(self._app.get_text("record_status"))
            self.inventory_ui_status_label.setText(self._app.get_text("inventory_ui_status"))
            self.inventory_f3_label.setText(self._app.get_text("f3_hotkey"))
            self.pause_status_label_title.setText(self._app.get_text("global_pause"))
            self.pause_status_label.setText(self._app.get_text("normal_operation"))
            self.coordinates_set_label.setText(self._app.get_text("coordinates_set"))
            self.pickup_f6_label.setText(self._app.get_text("f6_hotkey"))
            self.occupied_label_title.setText(self._app.get_text("occupied_slots"))
            self.grid_adjustment_label.setText(self._app.get_text("grid_alignment_adjustment"))
            self.horizontal_label.setText(self._app.get_text("horizontal"))
            self.vertical_label.setText(self._app.get_text("vertical"))
            self.reset_offset_btn.setText(self._app.get_text("reset"))
            self.clear_click_mode_label.setText(self._app.get_text("clear_click_mode"))
            self.clear_click_left_radio.setText(self._app.get_text("clear_click_left"))
            self.clear_click_right_radio.setText(self._app.get_text("clear_click_right"))
            self.gui_settings_label.setText(self._app.get_text("gui_settings"))
            self.always_on_top_check.setText(self._app.get_text("always_on_top"))
            self.ui_preview_hint_label.setText(self._app.get_text("inventory_ui_screenshot_hint"))
            self.inventory_exclude_hint.setText(self._app.get_text("inventory_exclude_hint"))

            self.refresh_config_display()
            if not self._preview_has_image:
                self.set_preview_placeholder(self._app.get_text("select_inventory_region_first"))
        except Exception as e:
            print(f"更新一鍵清包分頁語言時發生錯誤: {e}")

    def _apply_config_to_ui(self):
        self.clear_click_left_radio.setChecked(self.clear_click_mode == "left")
        self.clear_click_right_radio.setChecked(self.clear_click_mode == "right")
        self.always_on_top_check.setChecked(bool(self._app.always_on_top))
        self.update_offset_labels()
        self.refresh_config_display()

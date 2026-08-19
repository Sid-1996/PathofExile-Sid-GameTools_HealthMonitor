"""InventoryTab（Qt 版）— 一鍵清包分頁（Phase 5b：框選 + 預覽 + exclusion）。

對應 tk 版 `tab_inventory.py`。Phase 5c 將移植 F3 清包 / F6 拾取與介面UI偵測。
worker thread 的 UI 更新一律走 Signal（延續 MonitorTab/StatusTab 模式）。
"""

import time

import cv2
import numpy as np
import pygetwindow as gw

from PIL import Image

from PySide6.QtCore import QObject, QPoint, QRect, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import CheckBox, PushButton, RadioButton

from capture_utils import capture_region_to_cv2, capture_region_to_pil, load_screenshot_from_file, save_screenshot
from image_utils import get_interface_ui_region_text
from inventory_utils import calculate_inventory_grid_positions, should_clear_inventory
from qt.monitor import _pil_to_qpixmap, _SelectionOverlay

# ── 色票（與 qt.monitor 對齊）──
ERROR = "#f38ba8"
SUCCESS = "#a6e3a1"
INFO = "#89b4fa"
MUTED = "#b8b8c8"
INPUT_BG = "#1e1e2e"
GROUP_BORDER = "#3d3d5c"


class _ClickableLabel(QLabel):
    """可點擊 + 可監聽 resize 的預覽標籤（排除格 toggle 與 resize 重繪）。"""

    clicked = Signal(QPoint)
    resized = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(event.position().toPoint())
        super().mousePressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resized.emit()


class _InventorySignals(QObject):
    """worker → UI 更新（Phase 5c 使用；先定義避免 __init__ 重構）。"""

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
        self.load_ui_screenshot_from_file()
        self.load_interface_ui_screenshot_from_file()

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
        self.select_inventory_region_btn.clicked.connect(self.start_inventory_selection)
        row.addWidget(self.select_inventory_region_btn)

        self.record_empty_color_btn = PushButton(self._app.get_text("record_empty_color"))
        self.record_empty_color_btn.setToolTip(self._app.get_text("record_empty_color_tip"))
        self.record_empty_color_btn.clicked.connect(self.record_empty_inventory_color)
        row.addWidget(self.record_empty_color_btn)

        self.select_inventory_ui_btn = PushButton(self._app.get_text("select_inventory_ui"))
        self.select_inventory_ui_btn.setToolTip(self._app.get_text("select_inventory_ui_tip"))
        self.select_inventory_ui_btn.clicked.connect(self.start_inventory_ui_selection)
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

        self.inventory_preview_label = _ClickableLabel(self._app.get_text("select_inventory_region_first"))
        self.inventory_preview_label.setMinimumSize(300, 200)
        self.inventory_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.inventory_preview_label.setStyleSheet(f"background-color: {INPUT_BG}; border: 1px solid {GROUP_BORDER}; border-radius: 4px; color: {MUTED};")
        self.inventory_preview_label.clicked.connect(self._on_preview_click)
        self.inventory_preview_label.resized.connect(self._on_preview_resize)
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
        self._app.save_config()

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
        if self._preview_has_image:
            self.update_inventory_preview_from_current()
        self.update_ui_preview()

    def _not_implemented(self):
        self._app.add_status_message(self._app.get_text("inventory_setup_incomplete"), "warning")

    # ────────────────────────── 框選 overlay（Phase 5b） ──────────────────────────

    def start_inventory_selection(self):
        self._start_region_selection("inventory")

    def start_inventory_ui_selection(self):
        self._start_region_selection("inventory_ui")

    def start_interface_ui_selection(self):
        self._start_region_selection("interface_ui")

    def _start_region_selection(self, kind):
        window_title = self._app.monitor_tab.window_var.get()
        if not window_title:
            QMessageBox.warning(self, self._app.get_text("warning"), self._app.get_text("set_game_window_first"))
            return
        if self._app.check_game_window_minimized(window_title):
            return
        if self._app.is_monitoring():
            self._app.stop_monitoring()
        try:
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                QMessageBox.critical(self, self._app.get_text("error"), self._app.get_text("game_window_not_found"))
                return
            game_window = windows[0]
            game_window.activate()
            time.sleep(0.1)
            self.window().hide()

            instruction_key = {
                "inventory": "drag_select_inventory_region",
                "inventory_ui": "select_inventory_ui_instruction",
                "interface_ui": "select_interface_ui_instruction",
            }[kind]
            rect = QRect(game_window.left, game_window.top, game_window.width, game_window.height)
            self._overlay = _SelectionOverlay(
                rect,
                "inventory",
                self._app.get_text(instruction_key),
                on_done=lambda region: self._on_region_selection_done(kind, region),
                on_cancel=self._finalize_selection_restore_gui,
            )
            self._overlay.show()
            self._overlay.raise_()
            self._overlay.activateWindow()
        except Exception as e:
            self._finalize_selection_restore_gui()
            QMessageBox.critical(self, self._app.get_text("error"), self._app.get_text("selection_failed").format(error=str(e)))

    def _on_region_selection_done(self, kind, region):
        try:
            if kind == "inventory":
                self.inventory_region = region
                self._recompute_grid_positions()
                self.set_preview_placeholder(self._app.get_text("select_inventory_region_first"))
                self._app.add_status_message(self._app.get_text("inventory_region_set"), "success")
            elif kind == "inventory_ui":
                self.inventory_ui_region = region
                self._capture_ui_screenshot("inventory_ui")
            elif kind == "interface_ui":
                self._app.interface_ui_region = region
                self._capture_ui_screenshot("interface_ui")
        finally:
            self._finalize_selection_restore_gui()

    def _capture_ui_screenshot(self, kind):
        window_title = self._app.monitor_tab.window_var.get()
        windows = gw.getWindowsWithTitle(window_title)
        if not windows:
            return
        game_window = windows[0]
        region = self.inventory_ui_region if kind == "inventory_ui" else self._app.interface_ui_region
        if region is None:
            return
        monitor = {
            "top": game_window.top + region["y"],
            "left": game_window.left + region["x"],
            "width": region["width"],
            "height": region["height"],
        }
        img = capture_region_to_pil(monitor)
        if kind == "inventory_ui":
            save_screenshot(img, "inventory_ui.png")
            self.inventory_ui_screenshot = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            self.refresh_config_display()
            self.update_ui_preview()
            self._app.add_status_message(self._app.get_text("inventory_ui_recorded"), "success")
        else:
            save_screenshot(img, "interface_ui.png")
            self.interface_ui_screenshot = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            self.update_interface_ui_preview()
            self._app.add_status_message(
                self._app.get_text("interface_ui_region_set").format(x=region["x"], y=region["y"], width=region["width"], height=region["height"]),
                "success",
            )
            if hasattr(self._app, "monitor_tab") and hasattr(self._app.monitor_tab, "interface_ui_label"):
                self._app.monitor_tab.interface_ui_label.setText(get_interface_ui_region_text(self._app.interface_ui_region, self._app.get_text))
                self._app.monitor_tab.interface_ui_label.setStyleSheet(self._app.monitor_tab._region_label_style(color=SUCCESS))

    def _finalize_selection_restore_gui(self):
        win = self.window()
        win.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self._app.always_on_top)
        win.show()
        win.raise_()
        win.activateWindow()

    # ────────────────────────── 空格顏色記錄 ──────────────────────────

    def record_empty_inventory_color(self):
        if not self.inventory_region:
            QMessageBox.warning(self, self._app.get_text("warning"), self._app.get_text("select_inventory_region_first"))
            return
        region = self.inventory_region
        window_title = self._app.monitor_tab.window_var.get()
        if not window_title:
            QMessageBox.warning(self, self._app.get_text("warning"), self._app.get_text("set_game_window_first"))
            return
        if self._app.check_game_window_minimized(window_title):
            return
        try:
            self.window().hide()
            time.sleep(0.5)
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                self._finalize_selection_restore_gui()
                QMessageBox.critical(self, self._app.get_text("error"), self._app.get_text("game_window_not_found"))
                return
            game_window = windows[0]
            game_window.activate()
            time.sleep(0.5)

            self.inventory_grid_positions = calculate_inventory_grid_positions(region, self.grid_offset_x, self.grid_offset_y)
            if not self.inventory_grid_positions:
                self._finalize_selection_restore_gui()
                QMessageBox.critical(self, self._app.get_text("error"), self._app.get_text("inventory_grid_position_calc_failed"))
                return

            monitor = {
                "top": game_window.top + region["y"],
                "left": game_window.left + region["x"],
                "width": region["width"],
                "height": region["height"],
            }
            img = capture_region_to_cv2(monitor)

            self.empty_inventory_colors = []
            for pos_x, pos_y in self.inventory_grid_positions:
                img_x = pos_x - region["x"]
                img_y = pos_y - region["y"]
                if 0 <= img_x < img.shape[1] and 0 <= img_y < img.shape[0]:
                    x1 = max(0, img_x - 10)
                    y1 = max(0, img_y - 10)
                    x2 = min(img.shape[1], img_x + 10)
                    y2 = min(img.shape[0], img_y + 10)
                    cell_pixels = img[y1:y2, x1:x2]
                    if cell_pixels.size > 0:
                        avg_color = np.mean(cell_pixels, axis=(0, 1))
                        self.empty_inventory_colors.append((int(avg_color[2]), int(avg_color[1]), int(avg_color[0])))
                    else:
                        self.empty_inventory_colors.append((0, 0, 0))
                else:
                    self.empty_inventory_colors.append((0, 0, 0))

            self._finalize_selection_restore_gui()
            self.refresh_config_display()
            self.update_inventory_preview_from_current()
            recorded_count = len([c for c in self.empty_inventory_colors if c != (0, 0, 0)])
            QMessageBox.information(self, self._app.get_text("success"), self._app.get_text("empty_color_recorded_message").format(count=recorded_count))
        except Exception as e:
            self._finalize_selection_restore_gui()
            QMessageBox.critical(self, self._app.get_text("error"), self._app.get_text("operation_failed").format(error=str(e)))

    # ────────────────────────── 預覽渲染 ──────────────────────────

    def update_inventory_preview_from_current(self):
        """從當前背包區域重新擷取圖片並更新預覽（對應 tk 版同名方法）。"""
        if not self.inventory_region:
            return
        region = self.inventory_region
        try:
            if not hasattr(self._app, "window_key_sender") or not self._app.window_key_sender._is_game_window_visible():
                self.set_preview_placeholder(self._app.get_text("waiting_for_game_window"))
                return
            window_title = self._app.monitor_tab.window_var.get()
            if not window_title:
                return
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                return
            game_window = windows[0]

            if self.inventory_ui_region and self.inventory_ui_screenshot is not None:
                if not self.is_inventory_ui_visible(game_window):
                    self.set_preview_placeholder(self._app.get_text("waiting_inventory_open"))
                    return
            elif self.inventory_ui_region and self.inventory_ui_screenshot is None:
                self.set_preview_placeholder(self._app.get_text("inventory_ui_not_recorded"), "orange")
                return

            monitor = {
                "top": game_window.top + region["y"],
                "left": game_window.left + region["x"],
                "width": region["width"],
                "height": region["height"],
            }
            img = capture_region_to_cv2(monitor)
            _, occupied_slots = should_clear_inventory(img, self.empty_inventory_colors, self.inventory_grid_positions, region, self.excluded_inventory_slots)
            self.update_inventory_preview_with_items(img, occupied_slots)
        except Exception as e:
            print(f"重新獲取預覽失敗: {e}")

    def update_inventory_preview_with_items(self, img, occupied_slots):
        """繪製網格/佔用標記/排除疊加層並縮放顯示到預覽標籤（對應 tk 版）。"""
        try:
            display_img = img.copy()
            height, width = display_img.shape[:2]
            rows, cols = 5, 12
            cell_width = width // cols
            cell_height = height // rows
            offset_x = int(self.grid_offset_x)
            offset_y = int(self.grid_offset_y)

            for i in range(1, rows):
                y = i * cell_height + offset_y
                if 0 <= y < height:
                    cv2.line(display_img, (0, y), (width, y), (128, 128, 128), 1)
            for i in range(1, cols):
                x = i * cell_width + offset_x
                if 0 <= x < width:
                    cv2.line(display_img, (x, 0), (x, height), (128, 128, 128), 1)

            occupied_count = 0
            for row in range(rows):
                for col in range(cols):
                    center_x = col * cell_width + cell_width // 2 + offset_x
                    center_y = row * cell_height + cell_height // 2 + offset_y
                    if not (0 <= center_x < width and 0 <= center_y < height):
                        continue
                    grid_index = row * cols + col
                    if grid_index in occupied_slots:
                        occupied_count += 1
                        size = 6
                        cv2.line(display_img, (center_x - size, center_y - size), (center_x + size, center_y + size), (0, 0, 255), 2)
                        cv2.line(display_img, (center_x + size, center_y - size), (center_x - size, center_y + size), (0, 0, 255), 2)
                    else:
                        cv2.circle(display_img, (center_x, center_y), 2, (0, 255, 0), -1)

            self._draw_exclusion_overlay(display_img, width, height)

            label = self.inventory_preview_label
            avail_w = max(label.width(), 300)
            avail_h = max(label.height(), 200)
            scale = min(avail_w / width, avail_h / height, 1.0)
            new_width = int(width * scale)
            new_height = int(height * scale)
            if scale < 1.0:
                display_img = cv2.resize(display_img, (new_width, new_height))
            s_offset_x = int(offset_x * scale) if scale < 1.0 else offset_x
            s_offset_y = int(offset_y * scale) if scale < 1.0 else offset_y

            rgb = cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB)
            pix = _pil_to_qpixmap(Image.fromarray(rgb))
            label.setPixmap(pix)
            label.setText("")

            cx = (avail_w - new_width) // 2
            cy = (avail_h - new_height) // 2
            self._preview_meta = {
                "img_w": new_width,
                "img_h": new_height,
                "cell_w": new_width // cols,
                "cell_h": new_height // rows,
                "offset_x": s_offset_x,
                "offset_y": s_offset_y,
                "canvas_x": cx,
                "canvas_y": cy,
            }
            self._last_preview_img = img
            self._last_occupied_slots = occupied_slots
            self._preview_has_image = True
            self.occupied_slots_cache = set(occupied_slots)
            self.occupied_label.setText(self._app.get_text("slots_count").format(count=occupied_count))
        except Exception as e:
            print(f"更新預覽失敗: {e}")

    def _draw_exclusion_overlay(self, img, width, height):
        rows, cols = 5, 12
        cell_w = width // cols
        cell_h = height // rows
        offset_x = int(self.grid_offset_x)
        offset_y = int(self.grid_offset_y)
        for idx in self.excluded_inventory_slots:
            row = idx // 12
            col = idx % 12
            x1 = col * cell_w + offset_x
            y1 = row * cell_h + offset_y
            x2 = x1 + cell_w
            y2 = y1 + cell_h
            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.line(img, (x1, y1), (x2, y2), (255, 0, 0), 1)
            cv2.line(img, (x2, y1), (x1, y2), (255, 0, 0), 1)

    def _on_preview_click(self, pos):
        if not self._preview_has_image or not self._preview_meta:
            self._app.add_status_message(self._app.get_text("inventory_exclusion_toggle_unavailable"), "warning")
            return
        meta = self._preview_meta
        click_x = pos.x() - meta["canvas_x"] - meta["offset_x"]
        click_y = pos.y() - meta["canvas_y"] - meta["offset_y"]
        if click_x < 0 or click_y < 0 or click_x >= meta["img_w"] or click_y >= meta["img_h"]:
            return
        col = click_x // meta["cell_w"]
        row = click_y // meta["cell_h"]
        if col < 0 or col >= 12 or row < 0 or row >= 5:
            return
        idx = row * 12 + col
        if idx in self.excluded_inventory_slots:
            self.excluded_inventory_slots.discard(idx)
        else:
            self.excluded_inventory_slots.add(idx)
        self._render_preview_resize()
        self._app.add_status_message(
            self._app.get_text("inventory_slot_exclusion_toggled").format(
                index=idx,
                state=self._app.get_text("excluded") if idx in self.excluded_inventory_slots else self._app.get_text("included"),
            ),
            "info",
        )
        self._app.save_config()

    def _on_preview_resize(self):
        from PySide6.QtCore import QTimer

        QTimer.singleShot(150, self._render_preview_resize)

    def _render_preview_resize(self):
        if self._preview_has_image and hasattr(self, "_last_preview_img"):
            self.update_inventory_preview_with_items(self._last_preview_img, self._last_occupied_slots)

    # ────────────────────────── UI / 介面UI 預覽 ──────────────────────────

    def update_ui_preview(self):
        if self.inventory_ui_screenshot is None:
            self.set_ui_preview_placeholder(self._app.get_text("ui_preview_empty"))
            return
        rgb = cv2.cvtColor(self.inventory_ui_screenshot, cv2.COLOR_BGR2RGB)
        self.set_ui_preview_pil(Image.fromarray(rgb))

    def update_interface_ui_preview(self):
        label = getattr(self._app.monitor_tab, "interface_ui_preview_label", None)
        if label is None:
            return
        if self.interface_ui_screenshot is None:
            label.setPixmap(QPixmap())
            label.setText(self._app.get_text("interface_ui_preview_empty"))
            label.setStyleSheet(f"background-color: {INPUT_BG}; border: 1px solid {GROUP_BORDER}; border-radius: 4px; color: {MUTED};")
            return
        rgb = cv2.cvtColor(self.interface_ui_screenshot, cv2.COLOR_BGR2RGB)
        pix = _pil_to_qpixmap(Image.fromarray(rgb))
        scaled = pix.scaled(label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        label.setPixmap(scaled)
        label.setText("")

    def load_ui_screenshot_from_file(self):
        img = load_screenshot_from_file("inventory_ui.png")
        if img is not None:
            self.inventory_ui_screenshot = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            self.update_ui_preview()
            self.refresh_config_display()
            return True
        return False

    def load_interface_ui_screenshot_from_file(self):
        img = load_screenshot_from_file("interface_ui.png")
        if img is not None:
            self.interface_ui_screenshot = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            self.update_interface_ui_preview()
            return True
        return False

    # ────────────────────────── UI 可見性（Phase 5c 前先用於預覽 gating） ──────────────────────────

    def is_inventory_ui_visible(self, game_window):
        """檢查背包UI是否可見（MSE + 主色比較，對應 tk 版）。"""
        if not self.inventory_ui_region or self.inventory_ui_screenshot is None:
            return False
        try:
            monitor = {
                "top": game_window.top + self.inventory_ui_region["y"],
                "left": game_window.left + self.inventory_ui_region["x"],
                "width": self.inventory_ui_region["width"],
                "height": self.inventory_ui_region["height"],
            }
            current_img = capture_region_to_cv2(monitor)
            if current_img.shape != self.inventory_ui_screenshot.shape:
                return False
            mse = np.mean((current_img - self.inventory_ui_screenshot) ** 2)
            current_main_color = np.mean(current_img, axis=(0, 1))
            recorded_main_color = np.mean(self.inventory_ui_screenshot, axis=(0, 1))
            color_diff = np.mean(np.abs(current_main_color - recorded_main_color))
            return mse < 150 and color_diff < 10
        except Exception as e:
            print(f"檢查背包UI可見性失敗: {e}")
            return False

    def check_inventory_ui_exists(self, game_window):
        return self.is_inventory_ui_visible(game_window)

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
        self.update_ui_preview()
        self.update_interface_ui_preview()

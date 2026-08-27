"""InventoryTab（Qt 版）— 一鍵清包分頁（Phase 5c 完成：F3 清包 / F6 拾取 / 介面UI偵測）。

對應 tk 版 `tab_inventory.py`。worker thread 的 UI 更新一律走 Signal（延續 MonitorTab/StatusTab 模式）。
"""

import threading
import time

import cv2
import numpy as np
import pyautogui
import pygetwindow as gw

from PIL import Image

from PySide6.QtCore import QObject, QPoint, QRect, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
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

from capture_utils import _mss_singleton, capture_region_to_cv2, capture_window_region_bgr, load_screenshot_from_file, save_screenshot
from typing import Dict, Optional
import base64

from image_utils import get_interface_ui_region_text
from inventory_utils import calculate_inventory_grid_positions, find_inventory_items, normalize_region, should_clear_inventory
from qt.monitor import _pil_to_qpixmap, _SelectionOverlay

# ── ponytail: 參照 ocr-trigger 11_template_matching 的 base64 內聯與 TM_CCOEFF_NORMED 多尺度 ──
def _img_to_b64(img_bgr: np.ndarray) -> str:
    _, buf = cv2.imencode(".png", img_bgr)
    return base64.b64encode(buf).decode("ascii")


def _b64_to_img(data: str) -> np.ndarray | None:
    try:
        buf = base64.b64decode(data)
        arr = np.frombuffer(buf, dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception:
        return None


# ── 色票（與 qt.monitor 對齊）──
ERROR = "#f38ba8"
SUCCESS = "#a6e3a1"
INFO = "#89b4fa"
MUTED = "#b8b8c8"
INPUT_BG = "#1e1e2e"
GROUP_BORDER = "#3d3d5c"

# ── 清包時 GUI 縮小尺寸（對應 tk 版 tab_inventory.py）──
CLEAR_MIN_MINSIZE = (400, 350)
CLEAR_MINIMIZED_WIDTH = 650
CLEAR_MINIMIZED_HEIGHT = 500


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
    """worker → UI 更新（跨 thread，Qt queued connection 自動切到主執行緒）。"""

    status_message = Signal(str, str)
    preview_ready = Signal(object)
    progress_update = Signal(object, object, str)
    f3_request = Signal()
    f6_request = Signal()
    restore_f3_gui = Signal(bool, bool)
    restore_f6_gui = Signal(bool, bool)


class _PickupSetupDialog(QDialog):
    """F6 取物座標設定視窗（對應 tk 版 setup_pickup_coordinates 的設定視窗）。"""

    def __init__(self, tab, parent=None):
        super().__init__(parent)
        self._tab = tab
        self.setWindowTitle(tab._app.get_text("setup_f6_pickup_coordinates_title"))
        self.setMinimumSize(720, 420)
        self._build(tab._app.get_text)

    def _build(self, get_text):
        layout = QVBoxLayout(self)

        info = QLabel(get_text("setup_f6_pickup_coordinates_description"))
        info.setWordWrap(True)
        layout.addWidget(info)

        coords_group = QGroupBox(get_text("coordinate_status"))
        coords_group.setStyleSheet(
            f"QGroupBox {{ border: 1px solid {GROUP_BORDER}; border-radius: 8px; margin-top: 10px; padding-top: 6px; color: #f8f8f2; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; }}"
        )
        coords_layout = QGridLayout(coords_group)
        coords_layout.setContentsMargins(12, 12, 12, 12)
        self.coord_labels = []
        self.status_labels = []
        for i in range(5):
            idx_label = QLabel(get_text("coordinate_template").format(number=i + 1))
            coord_label = QLabel()
            coord_label.setStyleSheet(f"background-color: {INPUT_BG}; border: 1px solid {GROUP_BORDER}; border-radius: 4px; padding: 4px 8px;")
            status_label = QLabel(get_text("coordinate_not_set"))
            status_label.setStyleSheet(f"color: {MUTED};")
            coords_layout.addWidget(idx_label, i, 0)
            coords_layout.addWidget(coord_label, i, 1)
            coords_layout.addWidget(status_label, i, 2)
            self.coord_labels.append(coord_label)
            self.status_labels.append(status_label)
        coords_layout.setColumnStretch(1, 1)
        layout.addWidget(coords_group)

        buttons = QHBoxLayout()
        self.start_btn = PushButton(get_text("start_continuous_setup"))
        self.start_btn.setToolTip(get_text("setup_pickup_coordinates_tip"))
        self.start_btn.clicked.connect(lambda: self._tab.start_continuous_setup(self))
        buttons.addWidget(self.start_btn)
        self.test_btn = PushButton(get_text("test_f6_pickup"))
        self.test_btn.clicked.connect(self._tab.test_pickup)
        buttons.addWidget(self.test_btn)
        self.clear_btn = PushButton(get_text("clear_all_coordinates"))
        self.clear_btn.setToolTip(get_text("clear_all_coordinates_tip"))
        self.clear_btn.clicked.connect(self._tab.clear_all_coordinates)
        buttons.addWidget(self.clear_btn)
        buttons.addStretch(1)
        self.close_btn = PushButton(get_text("close"))
        self.close_btn.clicked.connect(self.reject)
        buttons.addWidget(self.close_btn)
        layout.addLayout(buttons)

    def update_display(self):
        coords = self._tab.pickup_coordinates or [[0, 0]] * 5
        while len(coords) < 5:
            coords.append([0, 0])
        for i in range(5):
            self.coord_labels[i].setText(f"({coords[i][0]}, {coords[i][1]})")
            if coords[i][0] != 0 or coords[i][1] != 0:
                self.status_labels[i].setText(self._tab._app.get_text("coordinate_set"))
                self.status_labels[i].setStyleSheet(f"color: {SUCCESS};")
            else:
                self.status_labels[i].setText(self._tab._app.get_text("coordinate_not_set"))
                self.status_labels[i].setStyleSheet(f"color: {MUTED};")


class _CoordHintWindow(QDialog):
    """連續設定座標時的小提示視窗（frameless + 置頂 + 半透明）。"""

    def __init__(self, title, hint_text, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setWindowOpacity(0.9)
        layout = QVBoxLayout(self)
        label = QLabel(hint_text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        layout.addWidget(label)
        self.setWindowTitle(title)
        self.move(100, 100)


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
        self.inventory_region: Optional[Dict[str, int]] = None
        self.inventory_ui_region: Optional[Dict[str, int]] = None
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

        # ── 清包 GUI 縮小/恢復狀態（對應 tk 版 _state 相關欄位）──
        self._gui_minimized_for_clear = False
        self._original_gui_geometry = None
        self._original_gui_state = None
        self._gui_was_foreground_before_minimize = True
        self._original_min_size = None
        self._setup_dialog = None

        self._signals = _InventorySignals(self)
        self._signals.progress_update.connect(self.update_inventory_preview_with_progress)
        self._signals.f3_request.connect(self.quick_clear_inventory)
        self._signals.f6_request.connect(self.f6_pickup_items)
        self._signals.restore_f3_gui.connect(self._restore_f3_gui)
        self._signals.restore_f6_gui.connect(self._restore_f6_gui)

        self._load_config()
        self._build_ui()
        self._apply_config_to_ui()
        self.load_ui_screenshot_from_file()
        self.load_interface_ui_screenshot_from_file()

    # ────────────────────────── config ──────────────────────────

    def _load_config(self):
        cfg = self._app.config
        self.inventory_region = normalize_region(cfg.get("inventory_region"))
        self.empty_inventory_colors = [tuple(c) for c in cfg.get("empty_inventory_colors", [])]
        self.grid_offset_x = cfg.get("grid_offset_x", 0)
        self.grid_offset_y = cfg.get("grid_offset_y", 0)
        self.excluded_inventory_slots = set(cfg.get("excluded_inventory_slots", []))
        self.inventory_ui_region = normalize_region(cfg.get("inventory_ui_region"))
        self.pickup_coordinates = cfg.get("pickup_coordinates")
        self.clear_click_mode = cfg.get("inventory_clear_click_mode", "left")
        positions = [tuple(p) for p in cfg.get("inventory_grid_positions", [])]
        self.inventory_grid_positions = positions or calculate_inventory_grid_positions(self.inventory_region, self.grid_offset_x, self.grid_offset_y)

    def _sync_inventory_config(self):
        """把背包相關狀態同步進 config 並排程即時儲存（移除儲存按鈕後的統一入口）。"""
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
        self._app.schedule_config_save()

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
        self.test_clear_inventory_btn.clicked.connect(self.test_inventory_clearing)
        grid.addWidget(self.test_clear_inventory_btn, 0, 0)

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
        self.always_on_top_check.setToolTip(self._app.get_text("always_on_top_tip"))
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
        self.setup_pickup_coordinates_btn.clicked.connect(self.setup_pickup_coordinates)
        grid.addWidget(self.setup_pickup_coordinates_btn, 0, 0)

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
        self.offset_x_label.setToolTip(self._app.get_text("offset_entry_tip"))
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
        self.offset_y_label.setToolTip(self._app.get_text("offset_entry_tip"))
        offset_grid.addWidget(self.offset_y_label, 1, 2)

        down_btn = PushButton("▼")
        down_btn.setFixedWidth(40)
        down_btn.clicked.connect(lambda: self.adjust_grid_offset(0, 1))
        offset_grid.addWidget(down_btn, 1, 3)

        self.reset_offset_btn = PushButton(self._app.get_text("reset"))
        self.reset_offset_btn.setToolTip(self._app.get_text("reset_offset_tip"))
        self.reset_offset_btn.clicked.connect(self.reset_grid_offset)
        offset_grid.addWidget(self.reset_offset_btn, 1, 4)

        offset_grid.setColumnStretch(4, 1)
        vbox.addLayout(offset_grid)

        self.inventory_preview_label = _ClickableLabel(self._app.get_text("select_inventory_region_first"))
        self.inventory_preview_label.setMinimumSize(300, 200)
        # 上限切斷回饋循環：QLabel sizeHint 會追著 pixmap 走，反覆 setPreview 會讓 label 無限撐大
        self.inventory_preview_label.setMaximumSize(400, 300)
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

    def _update_preview_placeholder_state(self):
        if self._preview_has_image:
            return
        if self.inventory_region:
            self.set_preview_placeholder(self._app.get_text("inventory_preview_guide"), "orange")
        else:
            self.set_preview_placeholder(self._app.get_text("select_inventory_region_first"))

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
        self._sync_inventory_config()

    def _on_always_on_top_toggled(self, checked):
        self._app.set_always_on_top(checked)

    def adjust_grid_offset(self, delta_x, delta_y):
        self.grid_offset_x += delta_x
        self.grid_offset_y += delta_y
        max_offset = 20
        self.grid_offset_x = max(-max_offset, min(max_offset, self.grid_offset_x))
        self.grid_offset_y = max(-max_offset, min(max_offset, self.grid_offset_y))
        self.update_offset_labels()
        self._recompute_grid_positions()
        self._sync_inventory_config()

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
                QMessageBox.critical(self, self._app.get_text("error"), self._app.get_text("game_window_not_found_with_title").format(window_title=window_title))
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
        # overlay 回傳 tuple (x,y,w,h)，本子系統一律用 dict 存取 → 在此正規化
        region = normalize_region(region)
        if not isinstance(region, dict):
            return
        try:
            if kind == "inventory":
                self.inventory_region = region
                self._recompute_grid_positions()
                self._update_preview_placeholder_state()
                self._app.add_status_message(self._app.get_text("inventory_region_set"), "success")
            elif kind == "inventory_ui":
                self.inventory_ui_region = region
                self._capture_ui_screenshot("inventory_ui")
            elif kind == "interface_ui":
                self._app.interface_ui_region = region
                self._capture_ui_screenshot("interface_ui")
        finally:
            self._finalize_selection_restore_gui()
            self._sync_inventory_config()

    def _capture_ui_screenshot(self, kind):
        window_title = self._app.monitor_tab.window_var.get()
        region = self.inventory_ui_region if kind == "inventory_ui" else self._app.interface_ui_region
        if region is None:
            return
        result = capture_window_region_bgr(window_title, region)
        if result is None:
            return
        img_bgr = np.array(result[1], copy=True)
        img = Image.fromarray(np.ascontiguousarray(img_bgr[:, :, ::-1]), "RGB")
        if kind == "inventory_ui":
            save_screenshot(img, "inventory_ui.png")
            self.inventory_ui_screenshot = img_bgr
            # ponytail: 參照 ocr-trigger 內聯 base64，隨 config 一併持久化，重啟字節一致
            try:
                self._app.config["inventory_ui_template"] = _img_to_b64(img_bgr)
            except Exception:
                pass
            self.refresh_config_display()
            self.update_ui_preview()
            self._app.add_status_message(self._app.get_text("inventory_ui_recorded"), "success")
        else:
            save_screenshot(img, "interface_ui.png")
            self.interface_ui_screenshot = img_bgr
            try:
                self._app.config["interface_ui_template"] = _img_to_b64(img_bgr)
            except Exception:
                pass
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
                QMessageBox.critical(self, self._app.get_text("error"), self._app.get_text("game_window_not_found_with_title").format(window_title=window_title))
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
            self._sync_inventory_config()
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

            result = capture_window_region_bgr(window_title, region)
            if result is None:
                self.set_preview_placeholder(self._app.get_text("waiting_for_game_window"))
                return
            img = result[1]
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
        self._sync_inventory_config()

    def _on_preview_resize(self):
        from PySide6.QtCore import QTimer

        QTimer.singleShot(150, self._render_preview_resize)

    def _render_preview_resize(self):
        if self._preview_has_image and hasattr(self, "_last_preview_img"):
            self.update_inventory_preview_with_items(self._last_preview_img, self._last_occupied_slots)

    def update_inventory_preview_with_progress(self, img, occupied_slots, progress_text=""):
        """更新背包預覽，顯示60個格子的狀態和處理進度（對應 tk 版；worker 透過 signal 呼叫）。"""
        try:
            display_img = img.copy()
            height, width = display_img.shape[:2]
            rows, cols = 5, 12
            cell_width = width // cols
            cell_height = height // rows

            for i in range(1, rows):
                y = i * cell_height
                cv2.line(display_img, (0, y), (width, y), (128, 128, 128), 1)
            for i in range(1, cols):
                x = i * cell_width
                cv2.line(display_img, (x, 0), (x, height), (128, 128, 128), 1)

            for grid_index in occupied_slots:
                if grid_index < len(self.inventory_grid_positions):
                    abs_x, abs_y = self.inventory_grid_positions[grid_index]
                    if not self.inventory_region:
                        continue
                    center_x = abs_x - self.inventory_region["x"]
                    center_y = abs_y - self.inventory_region["y"]
                    if 0 <= center_x < width and 0 <= center_y < height:
                        size = 4
                        cv2.line(display_img, (center_x - size, center_y - size), (center_x + size, center_y + size), (0, 0, 255), 1)
                        cv2.line(display_img, (center_x + size, center_y - size), (center_x - size, center_y + size), (0, 0, 255), 1)

            self._draw_exclusion_overlay(display_img, width, height)

            label = self.inventory_preview_label
            avail_w = max(label.width(), 300)
            avail_h = max(label.height(), 200)
            scale = min(avail_w / width, avail_h / height, 1.0)
            new_width = int(width * scale)
            new_height = int(height * scale)
            if scale < 1.0:
                display_img = cv2.resize(display_img, (new_width, new_height))

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
                "offset_x": 0,
                "offset_y": 0,
                "canvas_x": cx,
                "canvas_y": cy,
            }
            self._last_preview_img = img
            self._last_occupied_slots = occupied_slots
            self._preview_has_image = True
            self.occupied_label.setText(self._app.get_text("slots_count").format(count=len(occupied_slots)))
        except Exception as e:
            print(f"更新進度預覽失敗: {e}")

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
        # 優先內聯 b64（重啟字節一致，參照 ocr-trigger），回退檔
        b64 = self._app.config.get("inventory_ui_template")
        if isinstance(b64, str) and b64:
            img_bgr = _b64_to_img(b64)
            if img_bgr is not None:
                self.inventory_ui_screenshot = img_bgr
                self.update_ui_preview()
                self.refresh_config_display()
                return True
        img = load_screenshot_from_file("inventory_ui.png")
        if img is not None:
            self.inventory_ui_screenshot = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            # 補寫 b64 以便下次重啟走內聯
            try:
                self._app.config["inventory_ui_template"] = _img_to_b64(self.inventory_ui_screenshot)
            except Exception:
                pass
            self.update_ui_preview()
            self.refresh_config_display()
            return True
        return False

    def load_interface_ui_screenshot_from_file(self):
        b64 = self._app.config.get("interface_ui_template")
        if isinstance(b64, str) and b64:
            img_bgr = _b64_to_img(b64)
            if img_bgr is not None:
                self.interface_ui_screenshot = img_bgr
                self.update_interface_ui_preview()
                return True
        img = load_screenshot_from_file("interface_ui.png")
        if img is not None:
            self.interface_ui_screenshot = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            try:
                self._app.config["interface_ui_template"] = _img_to_b64(self.interface_ui_screenshot)
            except Exception:
                pass
            self.update_interface_ui_preview()
            return True
        return False

    # ────────────────────────── F3 清包（Phase 5c） ──────────────────────────

    def request_f3(self):
        self._signals.f3_request.emit()

    def return_to_hideout(self):
        """F5 返回藏身處（送出 /hideout 指令）"""
        if self._app.is_global_pause():
            print("[STOP] 全域暫停中，跳過 F5 熱鍵")
            self._app.add_status_message(self._app.get_text("f5_skip_global_pause"), "warning")
            return

        self._app.add_status_message(self._app.get_text("f5_hotkey_pressed"), "hotkey")

        try:
            window_title = self._app.monitor_tab.window_var.get()
            if not window_title:
                print("F5: 未設定遊戲視窗，無法使用返回藏身處")
                self._app.add_status_message(self._app.get_text("f5_fail_game_window_not_set"), "error")
                return

            if not self._app.window_key_sender.is_game_window_foreground(window_title):
                print(f"F5: 遊戲視窗 '{window_title}' 不在前景，取消返回藏身處操作")
                self._app.add_status_message(self._app.get_text("f5_cancel_game_window_not_foreground"), "warning")
                return

            self._app.add_status_message(self._app.get_text("f5_processing_return_to_hideout"), "info")
            print("F5: 執行返回藏身處")

            import pyperclip

            pyautogui.press("enter")
            time.sleep(0.025)
            pyperclip.copy("/hideout")
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.025)
            pyautogui.press("enter")

            print("F5: 返回藏身處指令已送出")
            self._app.add_status_message(self._app.get_text("f5_success_hide_command_sent"), "success")
        except Exception as e:
            print(f"F5: 返回藏身處失敗: {str(e)}")
            self._app.add_status_message(self._app.get_text("f5_fail_with_error").format(error=str(e)), "error")

    def _validate_f3(self):
        if self._app.is_global_pause():
            print("[STOP] 全域暫停中，跳過F3熱鍵")
            self._app.add_status_message(self._app.get_text("f3_skip_global_pause"), "warning")
            return None
        self._app.inventory_clear_interrupt = False
        self._app.add_status_message(self._app.get_text("f3_hotkey_pressed"), "hotkey")
        if not self.inventory_region or not self.empty_inventory_colors:
            self._app.add_status_message(self._app.get_text("f3_fail_inventory_incomplete"), "error")
            QMessageBox.warning(self, self._app.get_text("f3_inventory_reminder"), self._app.get_text("inventory_setup_incomplete"))
            return None
        if not self.inventory_ui_region or self.inventory_ui_screenshot is None:
            self._app.add_status_message(self._app.get_text("f3_fail_inventory_ui_not_set"), "error")
            QMessageBox.warning(self, self._app.get_text("f3_inventory_reminder"), self._app.get_text("inventory_ui_screenshot_not_set"))
            return None
        window_title = self._app.monitor_tab.window_var.get()
        if not window_title:
            self._app.add_status_message(self._app.get_text("f3_fail_game_window_not_set"), "error")
            QMessageBox.warning(self, self._app.get_text("f3_inventory_reminder"), self._app.get_text("set_game_window_first"))
            return None
        return window_title

    def _capture_and_prepare_f3_gui(self, window_title):
        if not self._app.window_key_sender.is_game_window_foreground(window_title):
            self._app.add_status_message(self._app.get_text("f3_cancel_game_not_foreground"), "warning")
            print(f"F3: 遊戲視窗 '{window_title}' 不在前台，將嘗試激活")
        win = self.window()
        gui_was_visible = not win.isMinimized() and not win.isHidden()
        gui_was_foreground = False
        gui_was_topmost = self._app.should_keep_topmost()
        if gui_was_visible:
            try:
                import win32gui

                gui_was_foreground = win32gui.GetForegroundWindow() == win.winId()
            except Exception:
                gui_was_foreground = False
        print(f"F3: GUI視窗狀態 - 原本{'顯示' if gui_was_visible else '最小化'}，{'在前台' if gui_was_foreground else '在後台'}，{'保持在最上方' if gui_was_topmost else '不保持在最上方'}")
        if gui_was_foreground or gui_was_topmost:
            if gui_was_topmost:
                win.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
                win.show()
                print("F3: 已取消 GUI 置頂設定")
            win.lower()
            print("F3: 已將 GUI 移到後台")
        self._hide_setting_windows()
        return gui_was_foreground, gui_was_topmost

    def _hide_setting_windows(self):
        try:
            for w in QApplication.topLevelWidgets():
                if w is self.window() or not w.isVisible():
                    continue
                t = str(w.windowTitle())
                if "F3" in t or "F6" in t or "清包" in t or "設定" in t or "setup" in t.lower():
                    w.hide()
                    print(f"F3/F6: 隱藏設定視窗: {t}")
        except Exception as e:
            print(f"隱藏設定視窗時發生錯誤: {e}")

    def quick_clear_inventory(self):
        window_title = self._validate_f3()
        if window_title is None:
            return
        gui_was_foreground, gui_was_topmost = self._capture_and_prepare_f3_gui(window_title)

        def _worker(window_title_local, gui_was_foreground_local, gui_was_topmost_local):
            try:
                windows = gw.getWindowsWithTitle(window_title_local)
                if not windows:
                    self._app.add_status_message(self._app.get_text("f3_fail_game_window_not_found"), "error")
                    return
                game_window = windows[0]
                print(f"F3(worker): 找到遊戲視窗: {game_window.title}")
                try:
                    game_window.activate()
                    time.sleep(0.5)
                except Exception as e:
                    print(f"F3(worker): 激活遊戲視窗失敗: {e}")
                if not self._app.window_key_sender.is_game_window_foreground(window_title_local):
                    print("F3(worker): 警告 - 遊戲視窗可能未在前台")
                    try:
                        pyautogui.click(game_window.left + game_window.width // 2, game_window.top + game_window.height // 2)
                        time.sleep(0.2)
                    except Exception:
                        pass
                if not self.is_inventory_ui_visible(game_window):
                    print("F3(worker): 背包UI未開啟，跳過清包操作")
                    self._app.add_status_message(self._app.get_text("f3_cancel_inventory_not_open"), "warning")
                    return
                self._execute_f3_clear(game_window, window_title_local)
            except Exception as e:
                print(f"F3(worker): 發生例外: {e}")
                self._app.add_status_message(self._app.get_text("f3_fail_with_error").format(error=str(e)), "error")
            finally:
                self._app.inventory_clear_interrupt = False
                self._signals.restore_f3_gui.emit(gui_was_foreground_local, gui_was_topmost_local)

        t = threading.Thread(target=_worker, args=(window_title, gui_was_foreground, gui_was_topmost), daemon=True)
        t.start()

    def _restore_f3_gui(self, gui_was_foreground_local, gui_was_topmost_local):
        if gui_was_foreground_local or gui_was_topmost_local:
            try:
                self.window().raise_()
                self.window().activateWindow()
                if gui_was_topmost_local:
                    self.window().setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
                    self.window().show()
                    print("F3(worker): 已恢復 GUI 到前台並重新置頂")
                else:
                    print("F3(worker): 已恢復 GUI 到前台")
            except Exception as e:
                print(f"F3(worker): 恢復 GUI 失敗: {e}")

    def _execute_f3_clear(self, game_window, window_title_local):
        if not self.inventory_region or not self.inventory_grid_positions:
            return
        try:
            self._app.add_status_message(self._app.get_text("f3_processing_game_window_found"), "info")
        except Exception:
            pass
        monitor = {
            "top": game_window.top + self.inventory_region["y"],
            "left": game_window.left + self.inventory_region["x"],
            "width": self.inventory_region["width"],
            "height": self.inventory_region["height"],
        }
        img = capture_region_to_cv2(monitor)
        needs_clearing, occupied_slots = should_clear_inventory(img, self.empty_inventory_colors, self.inventory_grid_positions, self.inventory_region, self.excluded_inventory_slots)
        if needs_clearing:
            self._app.add_status_message(self._app.get_text("f3_processing_items_detected").format(count=len(occupied_slots)), "info")
            print(f"F3(worker): 檢測到 {len(occupied_slots)} 個格子有物品，正在清空...")
            self.clear_inventory_item(game_window, img)
            if self._app.inventory_clear_interrupt:
                self._app.add_status_message(self._app.get_text("f3_cancel_user_interrupt"), "warning")
                print("F3(worker): 清包被中斷")
            else:
                self._app.add_status_message(self._app.get_text("f3_completed_inventory_cleared"), "success")
                print("F3(worker): 已清空背包物品")
        else:
            self._app.add_status_message(self._app.get_text("f3_completed_inventory_cleared"), "success")
            print("F3(worker): 背包已淨空，無需操作")

    def clear_inventory_item(self, game_window, img):
        """清空背包物品 - 動態辨識版（對應 tk 版）。"""
        if not self.inventory_region or not self.inventory_grid_positions:
            return
        try:
            print("階段1：開始初始識別，創建清包列表")
            initial_item_positions = find_inventory_items(img, self.empty_inventory_colors, self.inventory_grid_positions, self.inventory_region, self.excluded_inventory_slots, -1)
            if not initial_item_positions:
                print("沒有找到需要清空的物品")
                return
            print(f"找到 {len(initial_item_positions)} 個物品位置，開始動態清包")

            monitor = {
                "top": game_window.top + self.inventory_region["y"],
                "left": game_window.left + self.inventory_region["x"],
                "width": self.inventory_region["width"],
                "height": self.inventory_region["height"],
            }

            total_processed = 0
            max_iterations = 40
            skipped_positions = set()

            print("開始動態清包模式 - 持續按住 Ctrl 鍵")
            pyautogui.keyDown("ctrl")
            time.sleep(0.025)

            while total_processed < max_iterations:
                if self._app.inventory_clear_interrupt:
                    print("F3清包被用戶中斷")
                    break
                try:
                    center_x = game_window.left + game_window.width // 2
                    center_y = game_window.top + game_window.height // 2
                    pyautogui.moveTo(center_x, center_y, duration=0.015)
                    time.sleep(0.025)

                    with _mss_singleton as sct:
                        current_screenshot = sct.grab(monitor)
                        current_img = np.frombuffer(current_screenshot.rgb, dtype=np.uint8).reshape(current_screenshot.height, current_screenshot.width, 3)
                        current_img = cv2.cvtColor(current_img, cv2.COLOR_RGB2BGR)

                    should_continue, current_occupied = should_clear_inventory(
                        current_img, self.empty_inventory_colors, self.inventory_grid_positions, self.inventory_region, self.excluded_inventory_slots, -1
                    )

                    progress_text = self._app.get_text("inventory_clear_dynamic_progress").format(count=total_processed)
                    self._signals.progress_update.emit(current_img, current_occupied, progress_text)
                    print(f"辨識結果：剩餘 {len(current_occupied)} 個物品需要清理")

                    if not should_continue:
                        print(f"背包已清空，結束動態清包 (總共處理了 {total_processed} 個道具)")
                        break
                except Exception as e:
                    print(f"辨識過程發生錯誤: {e}")
                    break

                current_item_positions = find_inventory_items(current_img, self.empty_inventory_colors, self.inventory_grid_positions, self.inventory_region, self.excluded_inventory_slots, -1)
                available_positions = [pos for pos in current_item_positions if pos not in skipped_positions]

                if not available_positions:
                    if skipped_positions:
                        print(f" 所有剩餘物品都無法存放進倉庫（已跳過 {len(skipped_positions)} 個位置）")
                        self._app.add_status_message(self._app.get_text("inventory_full_cannot_continue"), "warning")
                    else:
                        print("重新辨識發現沒有需要清理的物品，結束")
                    break

                next_pos = available_positions[0]
                screen_x = game_window.left + next_pos[0]
                screen_y = game_window.top + next_pos[1]

                slot_index = None
                for idx, grid_pos in enumerate(self.inventory_grid_positions):
                    if grid_pos == next_pos:
                        slot_index = idx
                        break

                print(f"準備點擊第 {total_processed + 1} 個物品 - 格子索引 {slot_index}, 螢幕坐標 ({screen_x}, {screen_y})")

                pyautogui.moveTo(screen_x, screen_y, duration=0.015)
                time.sleep(0.025)
                if self.clear_click_mode == "left":
                    pyautogui.click(screen_x, screen_y)
                    print(f"[OK] 已完成左鍵點擊第 {total_processed + 1} 個道具")
                else:
                    pyautogui.rightClick(screen_x, screen_y)
                    print(f"[OK] 已完成右鍵點擊第 {total_processed + 1} 個道具")
                time.sleep(0.025)
                total_processed += 1

                center_x = game_window.left + game_window.width // 2
                center_y = game_window.top + game_window.height // 2
                pyautogui.moveTo(center_x, center_y, duration=0.015)
                print(f"滑鼠已移動到遊戲視窗正中央 ({center_x}, {center_y})")

                time.sleep(0.015)

                try:
                    center_x = game_window.left + game_window.width // 2
                    center_y = game_window.top + game_window.height // 2
                    pyautogui.moveTo(center_x, center_y, duration=0.015)
                    time.sleep(0.025)

                    with _mss_singleton as sct:
                        check_screenshot = sct.grab(monitor)
                        check_img = np.frombuffer(check_screenshot.rgb, dtype=np.uint8).reshape(check_screenshot.height, check_screenshot.width, 3)
                        check_img = cv2.cvtColor(check_img, cv2.COLOR_RGB2BGR)

                    check_item_positions = find_inventory_items(check_img, self.empty_inventory_colors, self.inventory_grid_positions, self.inventory_region, self.excluded_inventory_slots, -1)

                    if next_pos in check_item_positions:
                        skipped_positions.add(next_pos)
                        print(f"[WARN] 物品位置 {next_pos} 無法清空，已加入跳過列表 (跳過總數: {len(skipped_positions)})")
                        total_processed -= 1
                    else:
                        print(f"[OK] 物品位置 {next_pos} 已成功清空")
                except Exception as e:
                    print(f"檢查物品清空狀態時發生錯誤: {e}")

            print("釋放 Ctrl 鍵")
            pyautogui.keyUp("ctrl")
            time.sleep(0.025)

            total_processed = self._perform_final_retry(game_window, monitor, total_processed, max_iterations)
        except Exception as e:
            print(f"清空物品失敗: {e}")
        finally:
            try:
                pyautogui.keyUp("ctrl")
                print("確保CTRL鍵已釋放")
            except Exception as e:
                print(f"釋放CTRL鍵時發生錯誤: {e}")

    def _perform_final_retry(self, game_window, monitor, total_processed, max_iterations):
        print("階段3：最終確認和重試邏輯")
        try:
            center_x = game_window.left + game_window.width // 2
            center_y = game_window.top + game_window.height // 2
            pyautogui.moveTo(center_x, center_y, duration=0.015)
            time.sleep(0.025)
            with _mss_singleton as sct:
                final_screenshot = sct.grab(monitor)
                final_img = np.frombuffer(final_screenshot.rgb, dtype=np.uint8).reshape(final_screenshot.height, final_screenshot.width, 3)
                final_img = cv2.cvtColor(final_img, cv2.COLOR_RGB2BGR)
            final_should_clear, final_occupied = should_clear_inventory(final_img, self.empty_inventory_colors, self.inventory_grid_positions, self.inventory_region, self.excluded_inventory_slots, -1)
            final_progress_text = self._app.get_text("inventory_clear_done").format(count=total_processed)
            self._signals.progress_update.emit(final_img, final_occupied, final_progress_text)
            print(f"最終確認：清包完成 {total_processed} 個道具，剩餘: {len(final_occupied)} 個")
            if final_should_clear and total_processed < max_iterations:
                print("檢測到還有剩餘物品，執行最終重試")
                self._app.add_status_message(self._app.get_text("f3_retry_final"), "info")
                retry_item_positions = find_inventory_items(final_img, self.empty_inventory_colors, self.inventory_grid_positions, self.inventory_region, self.excluded_inventory_slots, -1)
                if retry_item_positions:
                    print(f"重試：找到 {len(retry_item_positions)} 個剩餘物品")
                    retry_tasks = []
                    for pos in retry_item_positions:
                        screen_x = game_window.left + pos[0]
                        screen_y = game_window.top + pos[1]
                        slot_index = None
                        for idx, grid_pos in enumerate(self.inventory_grid_positions):
                            if grid_pos == pos:
                                slot_index = idx
                                break
                        if slot_index is not None:
                            retry_tasks.append((screen_x, screen_y, slot_index))
                    print(f"重試：已創建重試任務列表，包含 {len(retry_tasks)} 個任務")
                    pyautogui.keyDown("ctrl")
                    time.sleep(0.025)
                    retry_processed = 0
                    for task in retry_tasks[:5]:
                        if self._app.inventory_clear_interrupt:
                            break
                        screen_x, screen_y, slot_index = task
                        print(f"重試處理第 {retry_processed + 1} 個剩餘物品，位置: ({screen_x}, {screen_y})")
                        pyautogui.moveTo(screen_x, screen_y, duration=0.015)
                        time.sleep(0.025)
                        pyautogui.rightClick(screen_x, screen_y)
                        time.sleep(0.025)
                        print(f"已執行右鍵點擊重試第 {retry_processed + 1} 個道具 (包含正確的延遲)")
                        retry_processed += 1
                        total_processed += 1
                    pyautogui.keyUp("ctrl")
                    time.sleep(0.025)
                    print(f"重試完成，已額外處理 {retry_processed} 個剩餘物品")
                    center_x = game_window.left + game_window.width // 2
                    center_y = game_window.top + game_window.height // 2
                    pyautogui.moveTo(center_x, center_y, duration=0.015)
                    time.sleep(0.025)
                    with _mss_singleton as sct:
                        retry_final_screenshot = sct.grab(monitor)
                        retry_final_img = np.frombuffer(retry_final_screenshot.rgb, dtype=np.uint8).reshape(retry_final_screenshot.height, retry_final_screenshot.width, 3)
                        retry_final_img = cv2.cvtColor(retry_final_img, cv2.COLOR_RGB2BGR)
                    _, retry_final_occupied = should_clear_inventory(
                        retry_final_img, self.empty_inventory_colors, self.inventory_grid_positions, self.inventory_region, self.excluded_inventory_slots, -1
                    )
                    final_progress_text = self._app.get_text("inventory_clear_done_retry").format(count=total_processed)
                    self._signals.progress_update.emit(retry_final_img, retry_final_occupied, final_progress_text)
                    print(f"重試最終確認：總共處理 {total_processed} 個道具，剩餘: {len(retry_final_occupied)} 個")
        except Exception as e:
            print(f"最終確認過程發生錯誤: {e}")
        print(f"F3: 優化清包完成，已清空 {total_processed} 個背包物品")
        return total_processed

    # ────────────────────────── 清包測試（Phase 5c） ──────────────────────────

    def check_gui_overlap_with_inventory(self, game_window):
        try:
            if not self.inventory_region:
                return False
            win = self.window()
            if win.isMinimized() or win.isHidden():
                return False
            geo = win.geometry()
            gui_x, gui_y, gui_width, gui_height = geo.x(), geo.y(), geo.width(), geo.height()
            if gui_width <= 1 or gui_height <= 1:
                return False
            inventory_left = game_window.left + self.inventory_region["x"]
            inventory_top = game_window.top + self.inventory_region["y"]
            inventory_right = inventory_left + self.inventory_region["width"]
            inventory_bottom = inventory_top + self.inventory_region["height"]
            gui_right = gui_x + gui_width
            gui_bottom = gui_y + gui_height
            overlap_x = max(0, min(gui_right, inventory_right) - max(gui_x, inventory_left))
            overlap_y = max(0, min(gui_bottom, inventory_bottom) - max(gui_y, inventory_top))
            overlap_area = overlap_x * overlap_y
            inventory_area = self.inventory_region["width"] * self.inventory_region["height"]
            overlap_ratio = overlap_area / inventory_area if inventory_area > 0 else 0
            return overlap_ratio > 0.1
        except Exception as e:
            print(f"檢查GUI重疊時發生錯誤: {e}")
            return False

    def check_gui_overlap_with_inventory_ui(self, game_window):
        try:
            if not self.inventory_ui_region:
                return False
            win = self.window()
            if win.isMinimized() or win.isHidden():
                return False
            geo = win.geometry()
            gui_x, gui_y, gui_width, gui_height = geo.x(), geo.y(), geo.width(), geo.height()
            if gui_width <= 1 or gui_height <= 1:
                return False
            ui_left = game_window.left + self.inventory_ui_region["x"]
            ui_top = game_window.top + self.inventory_ui_region["y"]
            ui_right = ui_left + self.inventory_ui_region["width"]
            ui_bottom = ui_top + self.inventory_ui_region["height"]
            gui_right = gui_x + gui_width
            gui_bottom = gui_y + gui_height
            overlap_x = max(0, min(gui_right, ui_right) - max(gui_x, ui_left))
            overlap_y = max(0, min(gui_bottom, ui_bottom) - max(gui_y, ui_top))
            overlap_area = overlap_x * overlap_y
            ui_area = self.inventory_ui_region["width"] * self.inventory_ui_region["height"]
            overlap_ratio = overlap_area / ui_area if ui_area > 0 else 0
            return overlap_ratio > 0.05
        except Exception as e:
            print(f"檢查GUI與背包UI重疊時發生錯誤: {e}")
            return False

    def _disable_topmost_for_test(self):
        if self._app.always_on_top:
            self.window().setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
            self.window().lower()
            self.window().show()
            print("已暫時移除 GUI 置頂設定並將 GUI 移到後台")
            return True
        return False

    def _restore_gui_after_test(self, gui_minimized_for_test, original_state, original_geometry, gui_was_topmost, should_clear, occupied_slots, img):
        win = self.window()
        if gui_minimized_for_test:
            win.showNormal()
            if original_state == "zoomed":
                win.showMaximized()
            elif original_geometry:
                win.setGeometry(original_geometry)
            time.sleep(0.2)
            print("GUI已恢復")
        self.update_inventory_preview_with_items(img, occupied_slots)
        if not gui_minimized_for_test:
            try:
                win.raise_()
                win.activateWindow()
                print("已重新激活GUI視窗，用戶可以查看背包預覽")
            except Exception:
                pass
        if gui_was_topmost:
            win.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
            win.show()
            print("已恢復 GUI 置頂設定")
        status_key = "test_clear_inventory_needs_clear" if should_clear else "test_clear_inventory_empty"
        result_msg = self._app.get_text("test_clear_inventory_status").format(status=self._app.get_text(status_key))
        result_msg += self._app.get_text("test_clear_inventory_occupied_slots").format(count=len(occupied_slots))
        if occupied_slots:
            result_msg += self._app.get_text("test_clear_inventory_occupied_positions")
            for i, index in enumerate(occupied_slots[:10]):
                if index < len(self.inventory_grid_positions):
                    x, y = self.inventory_grid_positions[index]
                    result_msg += self._app.get_text("test_clear_inventory_slot_line").format(index=i + 1, slot=index, x=x, y=y)
                else:
                    result_msg += self._app.get_text("test_clear_inventory_invalid_slot_line").format(index=i + 1, slot=index)
            if len(occupied_slots) > 10:
                result_msg += self._app.get_text("test_clear_inventory_more").format(count=len(occupied_slots) - 10)
        QMessageBox.information(self, self._app.get_text("test_clear_inventory_result_title"), result_msg)

    def _minimize_gui_for_test_if_needed(self, game_window):
        gui_minimized_for_test = False
        needs_gui_minimize = False
        if self._app.always_on_top:
            if self.inventory_ui_region and self.check_gui_overlap_with_inventory_ui(game_window):
                needs_gui_minimize = True
                print("檢測到GUI可能遮擋背包UI檢測區域")
            if self.check_gui_overlap_with_inventory(game_window):
                needs_gui_minimize = True
                print("檢測到GUI可能遮擋背包區域")
        else:
            print("GUI未設定為永遠保持在最上方，跳過遮擋檢查")
        if needs_gui_minimize:
            print("正在縮小GUI以避免遮擋...")
            original_state = "zoomed" if self.window().isMaximized() else "normal"
            original_geometry = self.window().geometry()
            self.window().showMinimized()
            time.sleep(0.2)
            gui_minimized_for_test = True
            print("GUI已縮小")
            return gui_minimized_for_test, original_state, original_geometry
        return gui_minimized_for_test, None, None

    def _open_inventory_if_needed(self, game_window):
        inventory_ui_exists = self.check_inventory_ui_exists(game_window)
        print(f"背包UI狀態: {'存在' if inventory_ui_exists else '不存在'}")
        if not inventory_ui_exists:
            print("背包未開啟，正在自動開啟...")
            try:
                game_window.activate()
                time.sleep(0.2)
            except Exception:
                pyautogui.click(game_window.left + game_window.width // 2, game_window.top + game_window.height // 2)
                time.sleep(0.2)
            pyautogui.press("i")
            time.sleep(0.8)
            print("已發送 I 鍵開啟背包")
            if self.inventory_ui_region:
                inventory_ui_exists = self.check_inventory_ui_exists(game_window)
                print(f"開啟後背包UI狀態: {'存在' if inventory_ui_exists else '不存在'}")
                if not inventory_ui_exists:
                    print("警告: 背包可能未正確開啟，但繼續執行")
        return inventory_ui_exists

    def test_inventory_clearing(self):
        """測試背包清空功能 - 增強版本，自動檢測並開啟背包（對應 tk 版）。"""
        if not self.inventory_region:
            QMessageBox.warning(self, self._app.get_text("warning"), self._app.get_text("select_inventory_region_first"))
            return
        if not self.empty_inventory_colors:
            QMessageBox.warning(self, self._app.get_text("warning"), self._app.get_text("record_empty_color_first"))
            return
        if not self.inventory_ui_region:
            QMessageBox.warning(self, self._app.get_text("warning"), self._app.get_text("select_inventory_ui_region_first"))
            return
        if not self.inventory_grid_positions:
            QMessageBox.warning(self, self._app.get_text("warning"), self._app.get_text("please_adjust_inventory_region_first"))
            return
        window_title = self._app.monitor_tab.window_var.get()
        if not window_title:
            QMessageBox.warning(self, self._app.get_text("warning"), self._app.get_text("set_game_window_first"))
            return
        if self._app.check_game_window_minimized(window_title):
            return
        try:
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                QMessageBox.critical(self, self._app.get_text("error"), self._app.get_text("game_window_not_found_with_title").format(window_title=window_title))
                return
            game_window = windows[0]
            print(f"找到遊戲視窗: {game_window.title}")
            gui_was_topmost = self._disable_topmost_for_test()
            gui_minimized_for_test, original_state, original_geometry = self._minimize_gui_for_test_if_needed(game_window)
            try:
                game_window.activate()
                time.sleep(0.2)
                print("遊戲視窗已激活")
            except Exception as e:
                print(f"激活遊戲視窗失敗: {e}")
                try:
                    pyautogui.click(game_window.left + game_window.width // 2, game_window.top + game_window.height // 2)
                    time.sleep(0.2)
                    print("已嘗試點擊遊戲視窗")
                except Exception as e2:
                    print(f"點擊遊戲視窗也失敗: {e2}")
            self._open_inventory_if_needed(game_window)
            monitor = {
                "top": game_window.top + self.inventory_region["y"],
                "left": game_window.left + self.inventory_region["x"],
                "width": self.inventory_region["width"],
                "height": self.inventory_region["height"],
            }
            img = capture_region_to_cv2(monitor)
            should_clear, occupied_slots = should_clear_inventory(img, self.empty_inventory_colors, self.inventory_grid_positions, self.inventory_region, self.excluded_inventory_slots)
            self._restore_gui_after_test(gui_minimized_for_test, original_state, original_geometry, gui_was_topmost, should_clear, occupied_slots, img)
        except Exception as e:
            QMessageBox.critical(self, self._app.get_text("error"), self._app.get_text("operation_failed").format(error=str(e)))
            try:
                self.window().showNormal()
            except Exception:
                pass

    # ────────────────────────── F6 拾取（Phase 5c） ──────────────────────────

    def request_f6(self):
        self._signals.f6_request.emit()

    def _validate_f6(self):
        if self._app.is_global_pause():
            print("[STOP] 全域暫停中，跳過F6熱鍵")
            self._app.add_status_message(self._app.get_text("f6_skip_global_pause"), "warning")
            return None
        self._app.add_status_message(self._app.get_text("f6_hotkey_pressed"), "hotkey")
        print("=== F6取物功能被調用（非阻塞版） ===")
        window_title = self._app.monitor_tab.window_var.get()
        if not window_title:
            print("F6: 未設定遊戲視窗，無法使用一鍵取物功能")
            self._app.add_status_message(self._app.get_text("f6_fail_game_window_not_set"), "error")
            return None
        print(f"F6: 遊戲視窗已設定為: {window_title}")
        return window_title

    def _capture_and_prepare_f6_gui(self):
        win = self.window()
        gui_was_visible = not win.isMinimized() and not win.isHidden()
        gui_was_foreground = False
        gui_was_topmost = self._app.should_keep_topmost()
        if gui_was_visible:
            try:
                import win32gui

                gui_was_foreground = win32gui.GetForegroundWindow() == win.winId()
            except Exception:
                gui_was_foreground = False
        print(f"F6: GUI視窗狀態 - 原本{'顯示' if gui_was_visible else '最小化'}，{'在前台' if gui_was_foreground else '在後台'}，{'保持在最上方' if gui_was_topmost else '不保持在最上方'}")
        if gui_was_foreground or gui_was_topmost:
            if gui_was_topmost:
                win.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
                win.show()
                print("F6: 已取消 GUI 置頂設定")
            win.lower()
            print("F6: 已將 GUI 移到後台")
        self._hide_setting_windows()
        return gui_was_foreground, gui_was_topmost

    def _execute_f6_pickup(self, game_window, valid_coords_local):
        self._app.add_status_message(self._app.get_text("f6_processing_inventory_ui_check_passed"), "info")
        print(f"F6(worker): 開始執行取物，共 {len(valid_coords_local)} 個座標")
        try:
            original_pos = pyautogui.position()
        except Exception:
            original_pos = None
        try:
            pyautogui.keyDown("ctrl")
            time.sleep(0.05)
        except Exception as e:
            print(f"F6(worker): 按鍵Down失敗: {e}")
        try:
            for i, (rel_x, rel_y) in enumerate(valid_coords_local):
                abs_x = game_window.left + rel_x
                abs_y = game_window.top + rel_y
                print(f"F6(worker): 處理座標 {i + 1}/{len(valid_coords_local)} -> ({abs_x},{abs_y})")
                pyautogui.moveTo(abs_x, abs_y, duration=0.05)
                time.sleep(0.05)
                pyautogui.click()
                time.sleep(0.05)
            print("F6(worker): 取物完成")
            self._app.add_status_message(self._app.get_text("f6_completed_coordinates_processed").format(count=len(valid_coords_local)), "success")
            if original_pos:
                try:
                    pyautogui.moveTo(original_pos.x, original_pos.y, duration=0.05)
                except Exception:
                    pass
        finally:
            try:
                pyautogui.keyUp("ctrl")
            except Exception:
                pass

    def _restore_f6_gui(self, gui_was_foreground_local, gui_was_topmost_local):
        if gui_was_foreground_local or gui_was_topmost_local:
            try:
                self.window().raise_()
                self.window().activateWindow()
                if gui_was_topmost_local:
                    self.window().setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
                    self.window().show()
                    print("F6(worker): 已恢復 GUI 到前台並重新置頂")
                else:
                    print("F6(worker): 已恢復 GUI 到前台")
            except Exception as e:
                print(f"F6(worker): 恢復 GUI 失敗: {e}")

    def f6_pickup_items(self):
        window_title = self._validate_f6()
        if not window_title:
            return
        gui_was_foreground, gui_was_topmost = self._capture_and_prepare_f6_gui()

        valid_coords = []
        seen = set()
        if self.pickup_coordinates:
            for x, y in self.pickup_coordinates:
                if x != 0 or y != 0:
                    t = (x, y)
                    if t not in seen:
                        valid_coords.append((x, y))
                        seen.add(t)
        print(f"F6: 有效取物座標 {len(valid_coords)} 個")
        if not valid_coords:
            print("F6: 無有效座標，跳過背景執行")
            self._app.add_status_message(self._app.get_text("f6_no_valid_coordinates"), "warning")
            return

        def _worker(window_title_local, valid_coords_local, gui_was_foreground_local, gui_was_topmost_local):
            try:
                windows = gw.getWindowsWithTitle(window_title_local)
                if not windows:
                    print("F6(worker): 找不到遊戲視窗")
                    self._app.add_status_message(self._app.get_text("f6_fail_game_window_not_set"), "error")
                    return
                game_window = windows[0]
                print(f"F6(worker): 找到遊戲視窗: {game_window.title}")
                try:
                    game_window.activate()
                    time.sleep(0.5)
                except Exception as e:
                    print(f"F6(worker): 激活遊戲視窗失敗: {e}")
                if not self._app.window_key_sender.is_game_window_foreground(window_title_local):
                    print("F6(worker): 警告 - 遊戲視窗可能未在前台")
                if not self.is_inventory_ui_visible(game_window):
                    print("F6(worker): 背包UI未打開，無法執行取物功能")
                    self._app.add_status_message(self._app.get_text("f6_cancel_inventory_ui_not_open"), "warning")
                    return
                self._execute_f6_pickup(game_window, valid_coords_local)
            except Exception as e:
                print(f"F6(worker): 發生例外: {e}")
                self._app.add_status_message(self._app.get_text("f6_fail_with_error").format(error=str(e)), "error")
                try:
                    pyautogui.keyUp("ctrl")
                except Exception:
                    pass
            finally:
                self._signals.restore_f6_gui.emit(gui_was_foreground_local, gui_was_topmost_local)

        t = threading.Thread(target=_worker, args=(window_title, valid_coords, gui_was_foreground, gui_was_topmost), daemon=True)
        t.start()

    def save_pickup_coordinates(self, parent_window=None):
        """同步取物座標進 config 並排程即時儲存（自動儲存，無 popup）。"""
        self._app.config["pickup_coordinates"] = self.pickup_coordinates
        self._app.schedule_config_save()

    def setup_pickup_coordinates(self):
        """設定取物座標 - 一次性連續設定5個座標（對應 tk 版）。"""
        if self.pickup_coordinates is None:
            self.pickup_coordinates = [[0, 0] for _ in range(5)]
        while len(self.pickup_coordinates) < 5:
            self.pickup_coordinates.append([0, 0])
        dlg = _PickupSetupDialog(self, self.window())
        self._setup_dialog = dlg
        dlg.update_display()
        dlg.exec()
        self._setup_dialog = None

    def start_continuous_setup(self, parent_window):
        """開始連續設定5個取物座標（對應 tk 版；同步流程）。"""
        if self.pickup_coordinates is None:
            self.pickup_coordinates = [[0, 0] for _ in range(5)]
        window_title = self._app.monitor_tab.window_var.get()
        if window_title and self._app.check_game_window_minimized(window_title):
            return
        try:
            parent_window.hide()
            self.window().hide()
            time.sleep(0.5)
            QMessageBox.information(self.window(), self._app.get_text("start_setup_title"), self._app.get_text("start_setup_message"))

            import keyboard

            cancel_setup = False

            def on_esc_press():
                nonlocal cancel_setup
                cancel_setup = True
                print("[ERROR] 用戶按下ESC，取消設定")

            keyboard.on_press_key("esc", lambda _: on_esc_press())

            try:
                for i in range(5):
                    if cancel_setup:
                        QMessageBox.information(self.window(), self._app.get_text("setup_cancelled"), self._app.get_text("setup_cancelled_message"))
                        break

                    print(f"等待設定座標 {i + 1}... (按ESC取消)")
                    hint = _CoordHintWindow(
                        self._app.get_text("setup_coordinate_title").format(current=i + 1, total=5),
                        self._app.get_text("setup_coordinate_hint").format(number=i + 1),
                        self.window(),
                    )
                    hint.show()
                    QApplication.processEvents()

                    enter_pressed = False

                    def on_enter_press():
                        nonlocal enter_pressed
                        enter_pressed = True

                    keyboard.on_press_key("enter", lambda _: on_enter_press())

                    while not enter_pressed and not cancel_setup:
                        time.sleep(0.1)

                    if cancel_setup:
                        hint.close()
                        QMessageBox.information(self.window(), self._app.get_text("setup_cancelled"), self._app.get_text("setup_cancelled_message"))
                        break

                    abs_x, abs_y = pyautogui.position()
                    window_title = self._app.monitor_tab.window_var.get()
                    if window_title:
                        windows = gw.getWindowsWithTitle(window_title)
                        if windows:
                            game_window = windows[0]
                            rel_x = abs_x - game_window.left
                            rel_y = abs_y - game_window.top
                            self.pickup_coordinates[i] = [rel_x, rel_y]
                            print(f"[OK] 座標 {i + 1} 已設定: 絕對座標({abs_x}, {abs_y}) -> 相對座標({rel_x}, {rel_y})")
                        else:
                            self.pickup_coordinates[i] = [abs_x, abs_y]
                            print(f"[WARN] 找不到遊戲視窗，使用絕對座標 {i + 1}: ({abs_x}, {abs_y})")
                    else:
                        self.pickup_coordinates[i] = [abs_x, abs_y]
                        print(f"[WARN] 未設定遊戲視窗，使用絕對座標 {i + 1}: ({abs_x}, {abs_y})")

                    self._app.schedule_config_save()
                    hint.close()
                    time.sleep(0.3)
            except Exception as e:
                print(f"連續設定失敗: {str(e)}")
                QMessageBox.critical(self.window(), self._app.get_text("setup_failed"), f"{self._app.get_text('setup_failed')}: {str(e)}")
            finally:
                try:
                    keyboard.unhook_all()
                    self._app.setup_hotkeys()
                except Exception:
                    pass

            if not cancel_setup:
                self.update_coordinate_display()
                self.save_pickup_coordinates(parent_window)
                QMessageBox.information(self.window(), self._app.get_text("setup_completed_title"), self._app.get_text("setup_completed_message"))
                self.window().raise_()
                self.window().activateWindow()
                if self._app.should_keep_topmost():
                    self.window().setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
                    self.window().show()
        except Exception as e:
            print(f"連續設定失敗: {str(e)}")
            QMessageBox.critical(self.window(), self._app.get_text("setup_failed"), f"{self._app.get_text('setup_failed')}: {str(e)}")
        finally:
            try:
                self.window().showNormal()
                parent_window.show()
            except Exception:
                pass

    def update_coordinate_display(self):
        if self._setup_dialog is not None:
            self._setup_dialog.update_display()
        self.refresh_config_display()
        self.update_pickup_status()

    def clear_all_coordinates(self):
        if QMessageBox.question(self.window(), self._app.get_text("confirm"), self._app.get_text("confirm_clear_coordinates")) == QMessageBox.StandardButton.Yes:
            self.pickup_coordinates = [[0, 0] for _ in range(5)]
            self.update_coordinate_display()
            self.save_pickup_coordinates()
            print("已清除所有取物座標")

    def test_pickup(self):
        """測試F6取物功能（對應 tk 版）。"""
        print("=== 開始測試F6取物功能 ===")
        if self.pickup_coordinates is None:
            self.pickup_coordinates = [[0, 0] for _ in range(5)]
        if not any(x != 0 or y != 0 for x, y in self.pickup_coordinates):
            QMessageBox.critical(self.window(), self._app.get_text("error"), self._app.get_text("pickup_coordinates_required"))
            return
        window_title = self._app.monitor_tab.window_var.get()
        if not window_title:
            QMessageBox.critical(self.window(), self._app.get_text("error"), self._app.get_text("pickup_game_window_required"))
            return
        if self._app.check_game_window_minimized(window_title):
            return
        try:
            if "pickup_coordinates" not in self._app.config:
                QMessageBox.critical(self.window(), self._app.get_text("error"), self._app.get_text("pickup_config_missing"))
                return
            config_coords = self._app.config["pickup_coordinates"]
            if len(config_coords) != 5:
                QMessageBox.critical(self.window(), self._app.get_text("error"), self._app.get_text("pickup_config_incomplete"))
                return
            for i, (config_x, config_y) in enumerate(config_coords):
                current_x, current_y = self.pickup_coordinates[i]
                if config_x != current_x or config_y != current_y:
                    print(f"警告：座標{i + 1}配置不一致 - 配置:({config_x},{config_y}) vs 當前:({current_x},{current_y})")
            print("[OK] 座標和遊戲視窗設定檢查通過")
        except Exception as e:
            QMessageBox.critical(self.window(), self._app.get_text("error"), self._app.get_text("operation_failed").format(error=str(e)))
            return
        try:
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                QMessageBox.critical(self.window(), self._app.get_text("error"), self._app.get_text("game_window_not_found_with_title").format(window_title=window_title))
                return
            game_window = windows[0]
            print(f"[OK] 找到遊戲視窗: {window_title}")
            print("激活遊戲視窗...")
            game_window.activate()
            print("等待1秒確保遊戲視窗已激活...")
            time.sleep(1)
            print("執行F6取物功能...")
            self.f6_pickup_items()
            print("=== F6取物測試完成 ===")
        except Exception as e:
            print(f"測試取物功能失敗: {e}")
            print("F6: 測試模式 - 異常處理時不恢復GUI視窗")
            QMessageBox.critical(self.window(), self._app.get_text("error"), self._app.get_text("pickup_test_failed").format(error=str(e)))

    def update_pickup_status(self):
        if hasattr(self, "pickup_coords_label"):
            valid_coords = sum(1 for x, y in (self.pickup_coordinates or []) if x != 0 or y != 0)
            self.pickup_coords_label.setText(self._app.get_text("coordinates_count").format(count=valid_coords))
            if valid_coords > 0:
                self.pickup_coords_label.setStyleSheet(f"color: {SUCCESS};")
            else:
                self.pickup_coords_label.setStyleSheet(f"color: {MUTED};")

    # ────────────────────────── UI 可見性 ──────────────────────────

    def is_inventory_ui_visible(self, game_window):
        """檢查背包UI是否可見 — 參照 ocr-trigger TM_CCOEFF_NORMED 多尺度（抗 DPI/窗口縮放）。"""
        if not self.inventory_ui_region or self.inventory_ui_screenshot is None:
            print("[INV_UI] fail: region or screenshot is None")
            return False
        try:
            result = capture_window_region_bgr(game_window.title, self.inventory_ui_region)
            if result is None:
                try:
                    import time as _time

                    _time.sleep(0.2)
                    result = capture_window_region_bgr(game_window.title, self.inventory_ui_region)
                except Exception:
                    pass
            if result is None:
                print(f"[INV_UI] fail: capture None region={self.inventory_ui_region} win={getattr(game_window, 'title', '?')}")
                return False
            current_bgr = result[1]
            stored_bgr = self.inventory_ui_screenshot
            # 灰度多尺度 TM_CCOEFF_NORMED（ocr-trigger 11_template_matching 精簡版）
            try:
                tmpl_gray = cv2.cvtColor(stored_bgr, cv2.COLOR_BGR2GRAY)
                search_gray = cv2.cvtColor(current_bgr, cv2.COLOR_BGR2GRAY)
            except Exception:
                # 回退 MSE（極少觸發）
                mse = np.mean((current_bgr.astype(np.float32) - stored_bgr.astype(np.float32)) ** 2)
                return mse < 300
            th, tw = tmpl_gray.shape[:2]
            best = -1.0
            # 覆蓋 22→28 約 27% 漂移，取 0.85-1.15 七檔，步進 0.05（與 ocr-trigger 預設對齊）
            scales = [0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15]
            for scale in scales:
                sw = max(8, int(tw * scale))
                sh = max(8, int(th * scale))
                if sw > search_gray.shape[1] or sh > search_gray.shape[0]:
                    continue
                if scale == 1.0:
                    scaled = tmpl_gray
                else:
                    interp = cv2.INTER_LINEAR if scale > 1.0 else cv2.INTER_AREA
                    scaled = cv2.resize(tmpl_gray, (sw, sh), interpolation=interp)
                res = cv2.matchTemplate(search_gray, scaled, cv2.TM_CCOEFF_NORMED)
                cur_max = float(res.max()) if res.size else -1.0
                if cur_max > best:
                    best = cur_max
                if best >= 0.75:
                    break
            if best < 0:
                print(f"[INV_UI] fail: no valid scale tmpl={tw}x{th} search={search_gray.shape[1]}x{search_gray.shape[0]}")
                return False
            passed = best >= 0.75
            if not passed:
                print(f"[INV_UI] fail: confidence={best:.3f} <0.75 tmpl={tw}x{th} search={search_gray.shape[1]}x{search_gray.shape[0]} region={self.inventory_ui_region}")
            else:
                print(f"[INV_UI] pass: confidence={best:.3f} region={self.inventory_ui_region}")
            return passed
        except Exception as e:
            print(f"檢查背包UI可見性失敗: {e}")
            return False

    def check_inventory_ui_exists(self, game_window):
        return self.is_inventory_ui_visible(game_window)

    def is_interface_ui_visible(self, game_window):
        """檢查介面UI是否可見（判定是否在戰鬥狀態；多指標綜合比較，對應 tk 版）。"""
        if not self._app.interface_ui_region or self.interface_ui_screenshot is None:
            return False
        try:
            result = capture_window_region_bgr(game_window.title, self._app.interface_ui_region)
            if result is None:
                return False
            current_img = result[1]
            if current_img.shape != self.interface_ui_screenshot.shape:
                return False

            mse = np.mean((current_img - self.interface_ui_screenshot) ** 2)
            mse_threshold = self._app.interface_ui_mse_threshold

            ssim_score = 0.5
            try:
                from skimage.metrics import structural_similarity as ssim  # pyright: ignore[reportMissingImports]  # 選用性依賴，未安裝時回退

                gray_current = cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY)
                gray_recorded = cv2.cvtColor(self.interface_ui_screenshot, cv2.COLOR_BGR2GRAY)
                ssim_score = ssim(gray_current, gray_recorded)
            except ImportError:
                ssim_score = 0.8

            hist_current = cv2.calcHist([current_img], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
            hist_recorded = cv2.calcHist([self.interface_ui_screenshot], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
            hist_current = cv2.normalize(hist_current, hist_current).flatten()
            hist_recorded = cv2.normalize(hist_recorded, hist_recorded).flatten()
            hist_similarity = cv2.compareHist(hist_current, hist_recorded, cv2.HISTCMP_CORREL)

            current_main_color = np.mean(current_img, axis=(0, 1))
            recorded_main_color = np.mean(self.interface_ui_screenshot, axis=(0, 1))
            color_diff = np.mean(np.abs(current_main_color - recorded_main_color))

            mse_pass = mse < mse_threshold
            ssim_pass = ssim_score > self._app.interface_ui_ssim_threshold
            hist_pass = hist_similarity > self._app.interface_ui_hist_threshold
            color_pass = color_diff < self._app.interface_ui_color_threshold
            pass_count = sum([mse_pass, ssim_pass, hist_pass, color_pass])

            return (pass_count >= 3) or (mse_pass and color_pass) or (ssim_pass and hist_pass)
        except Exception as e:
            print(f"檢查介面UI可見性失敗: {e}")
            return False

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
            self.setup_pickup_coordinates_btn.setText(self._app.get_text("setup_pickup_coordinates"))
            self.setup_pickup_coordinates_btn.setToolTip(self._app.get_text("setup_pickup_coordinates_tip"))

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
            self.reset_offset_btn.setToolTip(self._app.get_text("reset_offset_tip"))
            self.clear_click_mode_label.setText(self._app.get_text("clear_click_mode"))
            self.clear_click_left_radio.setText(self._app.get_text("clear_click_left"))
            self.clear_click_right_radio.setText(self._app.get_text("clear_click_right"))
            self.gui_settings_label.setText(self._app.get_text("gui_settings"))
            self.always_on_top_check.setText(self._app.get_text("always_on_top"))
            self.always_on_top_check.setToolTip(self._app.get_text("always_on_top_tip"))
            self.offset_x_label.setToolTip(self._app.get_text("offset_entry_tip"))
            self.offset_y_label.setToolTip(self._app.get_text("offset_entry_tip"))
            self.ui_preview_hint_label.setText(self._app.get_text("inventory_ui_screenshot_hint"))
            self.inventory_exclude_hint.setText(self._app.get_text("inventory_exclude_hint"))

            self.refresh_config_display()
            self._update_preview_placeholder_state()
        except Exception as e:
            print(f"更新一鍵清包分頁語言時發生錯誤: {e}")

    def _apply_config_to_ui(self):
        self.clear_click_left_radio.setChecked(self.clear_click_mode == "left")
        self.clear_click_right_radio.setChecked(self.clear_click_mode == "right")
        self.always_on_top_check.setChecked(bool(self._app.always_on_top))
        self.update_offset_labels()
        self.refresh_config_display()
        self._update_preview_placeholder_state()
        self.update_ui_preview()
        self.update_interface_ui_preview()

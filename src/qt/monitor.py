"""MonitorTab — 血魔監控 tab 的 PySide6 移植（Phase 4a：UI + 觸發列表 + 預覽）。

對應 tk 版 `tab_monitor.py`。供 worker thread 呼叫的 `update_*` 一律只 emit Signal，
主執行緒 slot 才碰 widgets（延續 StatusTab 的 thread-safe 模式）。
框選 overlay（start_selection / start_mana_selection）與血條/介面UI校準視窗皆已實作；
介面UI框選委派給 InventoryTab（start_interface_ui_selection），避免重複實作。
"""

import os
import time
import threading
from typing import Callable, Optional

import cv2
import pygetwindow as gw

from PIL import Image

from PySide6.QtCore import QObject, QRect, Qt, Signal, QTimer
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import CheckBox, ComboBox, EditableComboBox, LineEdit, PrimaryPushButton, PushButton

from capture_utils import capture_window_region_pil, save_screenshot
from inventory_utils import normalize_region
from image_utils import (
    draw_health_indicator,
    draw_mana_indicator,
    draw_scale_lines,
    get_interface_ui_region_text,
    get_mana_region_text,
    get_region_text,
    resize_and_center_image,
)
from qt.monitor_dialogs import AdjustColorsDialog, AdjustInterfaceUiDialog
from utils import get_user_data_dir

# ── 色票（與 tk 版 ui_theme 對齊）──
ERROR = "#f38ba8"
SUCCESS = "#a6e3a1"
INFO = "#89b4fa"
WARNING = "#f9e2af"
MUTED = "#b8b8c8"
INPUT_BG = "#1e1e2e"
GROUP_BORDER = "#3d3d5c"


def _validate_key_sequence(key_sequence):
    """檢查快捷鍵序列是否有效（與 tk 版 valid_keys 相同）。"""
    if not key_sequence:
        return False
    valid_keys = {
        *map(str, range(10)),
        *[chr(c) for c in range(ord("a"), ord("z") + 1)],
        "f2",
        "f3",
        "f4",
        "f5",
        "f6",
        "f7",
        "f8",
        "f9",
        "f10",
        "f12",
        "esc",
        "escape",
        "enter",
        "return",
        "space",
        "tab",
        "backspace",
        "delete",
        "home",
        "end",
        "pageup",
        "pagedown",
        "up",
        "down",
        "left",
        "right",
        "uparrow",
        "downarrow",
        "leftarrow",
        "rightarrow",
        "ctrl",
        "alt",
        "shift",
        "win",
        "cmd",
        "windows",
    }
    for key in (k.strip() for k in key_sequence.split("-")):
        if key.lower() not in valid_keys:
            return False
    return True


def _pil_to_qpixmap(pil_img):
    img = pil_img.convert("RGBA")
    data = img.tobytes("raw", "RGBA")
    qimg = QImage(data, img.width, img.height, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg)


class _AutoRefreshCombo(EditableComboBox):
    """遊戲視窗下拉：每次開啟前自動重掃視窗清單（取代手動重新整理按鈕）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.on_refresh: Optional[Callable[[], None]] = None

    def _showComboMenu(self):
        if self.on_refresh:
            self.on_refresh()
        super()._showComboMenu()


class _VarShim:
    """相容層：讓 WindowKeySender 等既有模組可繼續用 .get()/.set() 讀寫視窗標題。"""

    def __init__(self, tab):
        self._tab = tab

    def get(self):
        return self._tab.window_title

    def set(self, value):
        self._tab.window_title = value
        if hasattr(self._tab, "window_combo"):
            self._tab.window_combo.setCurrentText(value)


class _MonitorSignals(QObject):
    status_updated = Signal(str, str, str, str)
    health_preview = Signal(object)
    mana_preview = Signal(object)
    health_placeholder = Signal(str)
    mana_placeholder = Signal(str)
    preview_test_result = Signal(int, list)


class _SelectionOverlay(QWidget):
    """半透明全螢幕框選 overlay：拖曳繪製矩形，右鍵或 ESC 取消。

    置於遊戲視窗 screen 座標之上；回呼都在主執行緒（滑鼠事件）執行。
    """

    def __init__(self, rect, kind, instruction, on_done, on_cancel):
        super().__init__()
        self._kind = kind  # "health"（紅框）或 "mana"（青框）
        self._instruction = instruction
        self._on_done = on_done
        self._on_cancel = on_cancel
        self._start = None
        self._end = None

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(rect)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(128, 128, 128, 96))
        if self._start is not None and self._end is not None:
            color = "cyan" if self._kind == "mana" else "red"
            painter.setPen(QPen(QColor(color), 2))
            painter.drawRect(QRect(self._start, self._end).normalized())
        painter.setPen(QColor("white"))
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._instruction)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._finish(self._on_cancel)
            return
        self._start = event.position().toPoint()
        self._end = self._start

    def mouseMoveEvent(self, event):
        if self._start is not None:
            self._end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self._start is None:
            return
        rect = QRect(self._start, event.position().toPoint()).normalized()
        self._start = None
        self._end = None
        if rect.width() >= 2 and rect.height() >= 2:
            self._finish(lambda: self._on_done((rect.x(), rect.y(), rect.width(), rect.height())))
        else:
            self._finish(self._on_cancel)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._finish(self._on_cancel)
        else:
            super().keyPressEvent(event)

    def _finish(self, callback):
        self.close()
        callback()


class MonitorTab(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app

        # 從 config 還原上次選取的遊戲視窗（視窗不存在也先回填，實際操作時才阻擋）
        _saved_title = str(self._app.config.get("window_title", "") or "")
        if _saved_title.startswith("__SMOKE_"):
            _saved_title = ""  # 拋棄 smoke 測試污染，不暴露測試假視窗標題給使用者
        self.window_title = _saved_title
        self.window_var = _VarShim(self)
        # 從 config 回復已框選區域（legacy list → dict 正規化），供預覽/測試擷取使用
        self.selected_region = normalize_region(self._app.config.get("region"))
        self.selected_mana_region = normalize_region(self._app.config.get("mana_region"))
        self.preview_size = (380, 280)
        self.monitor_interval_ms = int(self._app.config.get("monitor_interval", 0.1) * 1000)
        self.multi_trigger = bool(self._app.config.get("multiple_triggers", True))

        self.last_preview_update = 0
        self.preview_update_interval = 500
        self.last_health_percent = -1
        self.last_mana_percent = -1
        self.last_mana_preview_update = 0
        self.last_status_update = 0
        self.status_update_interval = 100
        self._preview_placeholder_shown = False

        self._signals = _MonitorSignals()
        self._signals.status_updated.connect(self._on_status_updated)
        self._signals.health_preview.connect(self._on_health_preview)
        self._signals.mana_preview.connect(self._on_mana_preview)
        self._signals.health_placeholder.connect(self._on_health_placeholder)
        self._signals.mana_placeholder.connect(self._on_mana_placeholder)
        self._signals.preview_test_result.connect(self._on_preview_test_result)

        self._build_ui()
        self.refresh_windows()
        self.load_settings_to_tree()
        self.auto_load_preview()

    # ────────────────────────── UI 建構 ──────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        self.page_title_label = QLabel(self._app.get_text("monitor_title"))
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

        self._build_window_group(left_layout)
        self._build_trigger_group(left_layout)
        self._build_control_group(left_layout)
        left_layout.addStretch(1)

        self._build_status_group(right_layout)
        self._build_preview_group(right_layout)
        self._build_interface_ui_group(right_layout)
        right_layout.addStretch(1)

    def _styled_group(self, title):
        box = QGroupBox(title)
        box.setStyleSheet(
            f"QGroupBox {{ border: 1px solid {GROUP_BORDER}; border-radius: 8px; margin-top: 10px; padding-top: 6px; color: #f8f8f2; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; }}"
        )
        return box

    def _region_label(self):
        label = QLabel("--")
        label.setWordWrap(True)
        label.setStyleSheet(self._region_label_style(color=MUTED))
        return label

    @staticmethod
    def _region_label_style(color):
        return f"background-color: {INPUT_BG}; border: 1px solid {GROUP_BORDER}; border-radius: 4px; padding: 4px 8px; color: {color};"

    def _build_window_group(self, layout):
        self.window_frame = self._styled_group(self._app.get_text("game_window_settings"))
        grid = QGridLayout(self.window_frame)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        layout.addWidget(self.window_frame)

        self.game_window_label = QLabel(self._app.get_text("game_window"))
        grid.addWidget(self.game_window_label, 0, 0)

        self.window_combo = _AutoRefreshCombo()
        self.window_combo.setFixedWidth(320)
        self.window_combo.setPlaceholderText(self._app.get_text("select_game_window_first"))
        self.window_combo.setToolTip(self._app.get_text("game_window_combo_tip"))
        self.window_combo.on_refresh = self.refresh_windows
        self.window_combo.currentTextChanged.connect(self._on_window_changed)
        grid.addWidget(self.window_combo, 0, 1)

        self.health_bar_region_label = QLabel(self._app.get_text("health_bar_region"))
        grid.addWidget(self.health_bar_region_label, 1, 0)
        self.region_label = self._region_label()
        self.region_label.setText(get_region_text(self._app.config, self._app.get_text))
        grid.addWidget(self.region_label, 1, 1, 1, 2)

        self.mana_bar_region_label = QLabel(self._app.get_text("mana_bar_region"))
        grid.addWidget(self.mana_bar_region_label, 2, 0)
        self.mana_region_label = self._region_label()
        self.mana_region_label.setText(get_mana_region_text(self._app.config, self._app.get_text))
        grid.addWidget(self.mana_region_label, 2, 1, 1, 2)

        self.interface_ui_region_label = QLabel(self._app.get_text("interface_ui_region"))
        grid.addWidget(self.interface_ui_region_label, 3, 0)
        self.interface_ui_label = self._region_label()
        self.interface_ui_label.setText(get_interface_ui_region_text(self._app.interface_ui_region, self._app.get_text))
        grid.addWidget(self.interface_ui_label, 3, 1, 1, 2)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.select_health_region_btn = PushButton(self._app.get_text("select_health_region"))
        self.select_health_region_btn.setToolTip(self._app.get_text("select_health_region_tip"))
        self.select_health_region_btn.clicked.connect(self.start_selection)
        row.addWidget(self.select_health_region_btn)

        self.select_mana_region_btn = PushButton(self._app.get_text("select_mana_region"))
        self.select_mana_region_btn.setToolTip(self._app.get_text("select_mana_region_tip"))
        self.select_mana_region_btn.clicked.connect(self.start_mana_selection)
        row.addWidget(self.select_mana_region_btn)

        self.select_interface_ui_btn = PushButton(self._app.get_text("select_interface_ui"))
        self.select_interface_ui_btn.setToolTip(self._app.get_text("select_interface_ui_tip"))
        self.select_interface_ui_btn.clicked.connect(self._on_select_interface_ui)
        row.addWidget(self.select_interface_ui_btn)

        row.addStretch(1)
        grid.addLayout(row, 4, 0, 1, 3)
        grid.setColumnStretch(1, 1)

    def _build_trigger_group(self, layout):
        self.trigger_settings_frame = self._styled_group(self._app.get_text("trigger_settings"))
        vbox = QVBoxLayout(self.trigger_settings_frame)
        vbox.setContentsMargins(12, 12, 12, 12)
        vbox.setSpacing(10)
        layout.addWidget(self.trigger_settings_frame)

        add_row = QHBoxLayout()
        add_row.setSpacing(8)
        self.type_label = QLabel(self._app.get_text("type"))
        add_row.addWidget(self.type_label)
        self.type_combo = ComboBox()
        self.type_combo.addItems(["HP", "MP"])
        self.type_combo.setCurrentText("HP")
        self.type_combo.setToolTip(self._app.get_text("trigger_type_tip"))
        self.type_combo.currentTextChanged.connect(lambda _: self.on_type_changed())
        add_row.addWidget(self.type_combo)

        self.percentage_label = QLabel(self._app.get_text("percentage"))
        add_row.addWidget(self.percentage_label)
        self.percent_entry = LineEdit()
        self.percent_entry.setText("60")
        self.percent_entry.setFixedWidth(56)
        self.percent_entry.setToolTip(self._app.get_text("percentage_entry_tip"))
        add_row.addWidget(self.percent_entry)

        self.hotkey_label = QLabel(self._app.get_text("hotkey"))
        add_row.addWidget(self.hotkey_label)
        self.key_entry = LineEdit()
        self.key_entry.setText("1")
        self.key_entry.setFixedWidth(72)
        self.key_entry.setToolTip(self._app.get_text("hotkey_entry_tip"))
        add_row.addWidget(self.key_entry)

        self.cooldown_label = QLabel(self._app.get_text("cooldown_ms"))
        add_row.addWidget(self.cooldown_label)
        self.cooldown_entry = LineEdit()
        self.cooldown_entry.setText("1500")
        self.cooldown_entry.setFixedWidth(56)
        self.cooldown_entry.setToolTip(self._app.get_text("cooldown_entry_tip"))
        add_row.addWidget(self.cooldown_entry)

        self.add_trigger_btn = PrimaryPushButton(self._app.get_text("add_trigger"))
        self.add_trigger_btn.setToolTip(self._app.get_text("add_trigger_tip"))
        self.add_trigger_btn.clicked.connect(self.add_setting_new)
        add_row.addWidget(self.add_trigger_btn)
        add_row.addStretch(1)
        vbox.addLayout(add_row)

        options_row = QHBoxLayout()
        options_row.setSpacing(8)
        self.remove_selected_btn = PushButton(self._app.get_text("remove_selected"))
        self.remove_selected_btn.setToolTip(self._app.get_text("remove_selected_tip"))
        self.remove_selected_btn.clicked.connect(self.remove_setting)
        options_row.addWidget(self.remove_selected_btn)

        self.adjust_colors_btn = PushButton(self._app.get_text("adjust_colors"))
        self.adjust_colors_btn.setToolTip(self._app.get_text("adjust_colors_tip"))
        self.adjust_colors_btn.clicked.connect(self.open_adjust_colors)
        options_row.addWidget(self.adjust_colors_btn)

        self.adjust_interface_ui_btn = PushButton(self._app.get_text("adjust_interface_ui"))
        self.adjust_interface_ui_btn.setToolTip(self._app.get_text("adjust_interface_ui_tip"))
        self.adjust_interface_ui_btn.clicked.connect(self.open_adjust_interface_ui)
        options_row.addWidget(self.adjust_interface_ui_btn)

        self.multi_trigger_check = CheckBox(self._app.get_text("multiple_triggers"))
        self.multi_trigger_check.setToolTip(self._app.get_text("multiple_triggers_tip"))
        self.multi_trigger_check.setChecked(self.multi_trigger)
        self.multi_trigger_check.toggled.connect(lambda v: (setattr(self, "multi_trigger", v), self._app.schedule_config_save()))
        options_row.addWidget(self.multi_trigger_check)
        options_row.addStretch(1)
        vbox.addLayout(options_row)

        self.settings_tree = QTableWidget(0, 4)
        self.settings_tree.setHorizontalHeaderLabels([self._app.get_text("type"), self._app.get_text("percentage"), self._app.get_text("hotkey"), self._app.get_text("cooldown_ms")])
        self.settings_tree.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.settings_tree.verticalHeader().setVisible(False)
        self.settings_tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.settings_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.settings_tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.settings_tree.setMaximumHeight(150)
        vbox.addWidget(self.settings_tree)

    def _build_control_group(self, layout):
        self.control_frame = self._styled_group(self._app.get_text("control_panel"))
        vbox = QVBoxLayout(self.control_frame)
        vbox.setContentsMargins(12, 12, 12, 12)
        vbox.setSpacing(10)
        layout.addWidget(self.control_frame)

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(8)
        self.toggle_btn = PrimaryPushButton(self._app.get_text("start_monitoring"))
        self.toggle_btn.setToolTip(self._app.get_text("toggle_monitoring_tip"))
        self.toggle_btn.clicked.connect(self._app.toggle_monitoring_btn)
        buttons_row.addWidget(self.toggle_btn)
        self.update_toggle_btn()
        self.test_preview_btn = PushButton(self._app.get_text("test_preview"))
        self.test_preview_btn.setToolTip(self._app.get_text("test_preview_tip"))
        self.test_preview_btn.clicked.connect(self.test_preview)
        buttons_row.addWidget(self.test_preview_btn)
        buttons_row.addStretch(1)
        vbox.addLayout(buttons_row)

        freq_row = QHBoxLayout()
        freq_row.setSpacing(8)
        self.check_freq_label = QLabel(self._app.get_text("check_frequency"))
        freq_row.addWidget(self.check_freq_label)
        self.interval_combo = ComboBox()
        self.interval_combo.addItems(["25", "50", "100"])
        self.interval_combo.setCurrentText(str(self.monitor_interval_ms))
        self.interval_combo.setToolTip(self._app.get_text("check_interval_tip"))
        self.interval_combo.currentTextChanged.connect(lambda t: (setattr(self, "monitor_interval_ms", int(t)), self._app.schedule_config_save()))
        freq_row.addWidget(self.interval_combo)
        self.ms_label = QLabel(self._app.get_text("ms"))
        freq_row.addWidget(self.ms_label)
        freq_row.addStretch(1)
        vbox.addLayout(freq_row)

        self.reminder_label = QLabel(self._app.get_text("reminder_text"))
        self.reminder_label.setWordWrap(True)
        self.reminder_label.setStyleSheet(f"color: {ERROR};")
        vbox.addWidget(self.reminder_label)

        lang_row = QHBoxLayout()
        lang_row.setSpacing(8)
        self.language_label = QLabel(self._app.get_text("language"))
        lang_row.addWidget(self.language_label)
        self.language_display_map = {"繁體中文": "zh-tw", "English": "en"}
        self.language_reverse_map = {v: k for k, v in self.language_display_map.items()}
        self.language_combo = ComboBox()
        self.language_combo.addItems(list(self.language_display_map.keys()))
        self._setting_language = True
        self.language_combo.setCurrentText(self.language_reverse_map.get(self._app.current_language, "繁體中文"))
        self._setting_language = False
        self.language_combo.currentTextChanged.connect(self._on_language_changed)
        lang_row.addWidget(self.language_combo)
        lang_row.addStretch(1)
        vbox.addLayout(lang_row)

        gui_row = QHBoxLayout()
        gui_row.setSpacing(8)
        self.gui_settings_label = QLabel(self._app.get_text("gui_settings"))
        gui_row.addWidget(self.gui_settings_label)
        self.always_on_top_check = CheckBox(self._app.get_text("always_on_top"))
        self.always_on_top_check.setChecked(self._app.always_on_top)
        self.always_on_top_check.setToolTip(self._app.get_text("always_on_top_tip"))
        self.always_on_top_check.toggled.connect(self._on_always_on_top_toggled)
        gui_row.addWidget(self.always_on_top_check)
        gui_row.addStretch(1)
        vbox.addLayout(gui_row)

        preview_row = QHBoxLayout()
        preview_row.setSpacing(8)
        self.preview_settings_label = QLabel(self._app.get_text("preview_settings"))
        preview_row.addWidget(self.preview_settings_label)
        self.enable_preview_check = CheckBox(self._app.get_text("enable_preview"))
        self.enable_preview_check.setChecked(self._app.preview_enabled)
        self.enable_preview_check.setToolTip(self._app.get_text("enable_preview_tip"))
        self.enable_preview_check.toggled.connect(lambda v: (setattr(self._app, "preview_enabled", v), self._app.schedule_config_save()))
        preview_row.addWidget(self.enable_preview_check)
        self.preview_interval_label = QLabel(self._app.get_text("preview_interval"))
        preview_row.addWidget(self.preview_interval_label)
        self.preview_interval_entry = LineEdit()
        self.preview_interval_entry.setText(str(self._app.preview_interval))
        self.preview_interval_entry.setFixedWidth(56)
        self.preview_interval_entry.setToolTip(self._app.get_text("preview_interval_tip"))
        self.preview_interval_entry.textChanged.connect(self._on_preview_interval_changed)
        preview_row.addWidget(self.preview_interval_entry)
        self.preview_ms_label = QLabel(self._app.get_text("ms"))
        preview_row.addWidget(self.preview_ms_label)
        preview_row.addStretch(1)
        vbox.addLayout(preview_row)

    def update_toggle_btn(self) -> None:
        """依監控狀態更新切換按鈕文字（啟動/停止 + [F10]）。"""
        key = "stop_monitoring" if self._app.is_monitoring() else "start_monitoring"
        self.toggle_btn.setText(f"{self._app.get_text(key)}[F10]")

    def _build_status_group(self, layout):
        self.real_time_status_frame = self._styled_group(self._app.get_text("real_time_status"))
        grid = QGridLayout(self.real_time_status_frame)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)
        layout.addWidget(self.real_time_status_frame)

        self.current_health_label = QLabel(self._app.get_text("current_health"))
        grid.addWidget(self.current_health_label, 0, 0)
        self.health_label = QLabel("--")
        self.health_label.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {ERROR};")
        grid.addWidget(self.health_label, 0, 1)

        self.current_mana_label = QLabel(self._app.get_text("current_mana"))
        grid.addWidget(self.current_mana_label, 1, 0)
        self.mana_label = QLabel("--")
        self.mana_label.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {INFO};")
        grid.addWidget(self.mana_label, 1, 1)

        self.main_color_label = QLabel(self._app.get_text("main_color"))
        grid.addWidget(self.main_color_label, 2, 0)
        self.color_label = QLabel("--")
        grid.addWidget(self.color_label, 2, 1)

        self.trigger_status_label = QLabel(self._app.get_text("trigger_status"))
        grid.addWidget(self.trigger_status_label, 3, 0)
        self.trigger_label = QLabel("--")
        self.trigger_label.setWordWrap(True)
        grid.addWidget(self.trigger_label, 3, 1)

        grid.setColumnStretch(1, 1)

    def _build_preview_group(self, layout):
        self.preview_frame = self._styled_group(self._app.get_text("region_preview"))
        hbox = QHBoxLayout(self.preview_frame)
        hbox.setContentsMargins(12, 12, 12, 12)
        hbox.setSpacing(12)
        layout.addWidget(self.preview_frame)

        self.health_preview_frame = self._styled_group(self._app.get_text("health_preview"))
        hbox.addWidget(self.health_preview_frame, 1)
        self.preview_label = self._preview_canvas_label(self._app.get_text("select_health_region_first"))
        self.health_preview_frame.setLayout(self._preview_layout(self.preview_label))

        self.mana_preview_frame = self._styled_group(self._app.get_text("mana_preview"))
        hbox.addWidget(self.mana_preview_frame, 1)
        self.mana_preview_label = self._preview_canvas_label(self._app.get_text("select_mana_region_first"))
        self.mana_preview_frame.setLayout(self._preview_layout(self.mana_preview_label))

    def _preview_canvas_label(self, placeholder):
        label = QLabel(placeholder)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumSize(260, 170)
        # 上限切斷回饋循環：QLabel sizeHint 會追著 pixmap 走，週期性 setPixmap 會讓 label 無限撐大
        label.setMaximumSize(*self.preview_size)
        label.setStyleSheet(f"background-color: {INPUT_BG}; border: 1px solid {GROUP_BORDER}; border-radius: 4px; color: {MUTED};")
        return label

    @staticmethod
    def _preview_layout(label):
        vbox = QVBoxLayout()
        vbox.setContentsMargins(6, 6, 6, 6)
        vbox.addWidget(label, 1)
        return vbox

    def _build_interface_ui_group(self, layout):
        self.interface_ui_preview_frame = self._styled_group(self._app.get_text("interface_ui_preview"))
        vbox = QVBoxLayout(self.interface_ui_preview_frame)
        vbox.setContentsMargins(12, 12, 12, 12)
        vbox.setSpacing(4)
        layout.addWidget(self.interface_ui_preview_frame)

        self.interface_ui_preview_label = QLabel("--")
        self.interface_ui_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.interface_ui_preview_label.setFixedSize(160, 100)
        self.interface_ui_preview_label.setStyleSheet(f"background-color: {INPUT_BG}; border: 1px solid {GROUP_BORDER}; border-radius: 4px; color: {MUTED};")
        vbox.addWidget(self.interface_ui_preview_label, 0, Qt.AlignmentFlag.AlignHCenter)

        self.interface_ui_preview_hint = QLabel(self._app.get_text("interface_ui_preview_hint"))
        self.interface_ui_preview_hint.setStyleSheet(f"font-size: 11px; color: {MUTED};")
        self.interface_ui_preview_hint.setWordWrap(True)
        vbox.addWidget(self.interface_ui_preview_hint)

    # ────────────────────────── 視窗 / 預覽 ──────────────────────────

    def refresh_windows(self):
        try:
            windows = [w.title for w in gw.getAllWindows() if w.title]
            if [self.window_combo.itemText(i) for i in range(self.window_combo.count())] == windows:
                return
            self.window_combo.blockSignals(True)
            try:
                self.window_combo.clear()
                self.window_combo.addItems(windows)
                # setText（非 setCurrentText）：qfluentwidgets 的 setCurrentText 對不在清單的標題是
                # silent no-op，遊戲視窗不存在時會還原失敗；setText 可顯示任意保存的標題
                self.window_combo.setText(self.window_title)
            finally:
                self.window_combo.blockSignals(False)
        except Exception as e:
            print(f"[WARN] 重新整理視窗清單失敗: {e}")

    def _on_window_changed(self, text):
        """遊戲視窗手動選擇變更：更新標題、排程儲存並刷新預覽佔位文字。"""
        self.window_title = text
        self._app.schedule_config_save()
        if self._app.is_monitoring():
            return
        self.refresh_window_placeholders()

    def refresh_window_placeholders(self):
        """依目前視窗/區域狀態刷新血魔預覽佔位文字（不截圖）。"""
        cfg = self._app.config
        for is_mana in (False, True):
            sig = self._signals.mana_placeholder if is_mana else self._signals.health_placeholder
            if not self.window_title:
                text = self._app.get_text("select_game_window_first")
            elif not cfg.get("mana_region" if is_mana else "region"):
                key = "select_mana_bar_first" if is_mana else "select_health_bar_first"
                text = self._app.get_text(key)
            elif not gw.getWindowsWithTitle(self.window_title):
                text = self._app.get_text("game_window_not_found").format(window_title=self.window_title)
            else:
                text = self._app.get_text("click_test_preview_hint")
            sig.emit(text)

    def auto_load_preview(self):
        if self._app.config.get("region") and self._app.config.get("window_title"):
            try:
                if gw.getWindowsWithTitle(self._app.config["window_title"]):
                    self.window_var.set(self._app.config["window_title"])
                    health_loaded = self.load_preview_image()
                    mana_loaded = self.load_mana_preview_image()
                    if health_loaded or mana_loaded:
                        print(f"已自動載入設定：視窗={self._app.config['window_title']}")
                    else:
                        print("設定已載入，但預覽圖片需要更新")
                else:
                    print(f"遊戲視窗 '{self._app.config['window_title']}' 未找到")
                    self.window_var.set(self._app.config["window_title"])
                    if self._app.config.get("region"):
                        self._signals.health_placeholder.emit(self._app.get_text("game_window_not_found").format(window_title=self._app.config["window_title"]))
                    if self._app.config.get("mana_region"):
                        self._signals.mana_placeholder.emit(self._app.get_text("game_window_not_found").format(window_title=self._app.config["window_title"]))
            except Exception as e:
                print(f"自動載入預覽失敗: {e}")
                self._signals.health_placeholder.emit(self._app.get_text("settings_load_failed"))
                self._signals.mana_placeholder.emit(self._app.get_text("settings_load_failed"))
        else:
            if not self._app.config.get("region"):
                self._signals.health_placeholder.emit(self._app.get_text("select_health_bar_first"))
            if not self._app.config.get("mana_region"):
                self._signals.mana_placeholder.emit(self._app.get_text("select_mana_bar_first"))
            print("沒有找到已儲存的設定")

    def load_preview_image(self):
        path = os.path.join(get_user_data_dir(), "screenshots", "health_monitor_preview.png")
        if os.path.exists(path) and self.selected_region:
            try:
                img = Image.open(path)
                draw_scale_lines(img)
                self._signals.health_preview.emit(resize_and_center_image(img, self.preview_size))
                return True
            except Exception as e:
                print(f"載入預覽圖片失敗: {e}")
                self._signals.health_placeholder.emit(self._app.get_text("ui_preview_failed"))
                return False
        if self.selected_region:
            self._signals.health_placeholder.emit(self._app.get_text("health_region_set_waiting_preview"))
            return False
        self._signals.health_placeholder.emit(self._app.get_text("select_health_bar_first"))
        return False

    def load_mana_preview_image(self):
        path = os.path.join(get_user_data_dir(), "screenshots", "health_monitor_mana_preview.png")
        if os.path.exists(path) and self.selected_mana_region:
            try:
                img = Image.open(path)
                draw_scale_lines(img)
                self._signals.mana_preview.emit(resize_and_center_image(img, self.preview_size))
                return True
            except Exception as e:
                print(f"載入魔力預覽圖片失敗: {e}")
                self._signals.mana_placeholder.emit(self._app.get_text("mana_preview_load_failed"))
                return False
        if self.selected_mana_region:
            self.capture_mana_preview_async()
            return True
        self._signals.mana_placeholder.emit(self._app.get_text("select_mana_bar_first"))
        return False

    def capture_preview_async(self):
        if not self.selected_region:
            return

        def _capture():
            try:
                _, img = capture_window_region_pil(self.window_title, self.selected_region)
                if img is None:
                    self._signals.health_placeholder.emit(self._app.get_text("waiting_for_game_window"))
                    return
                img.thumbnail((200, 200))
                save_screenshot(img, "health_monitor_preview.png")
                draw_scale_lines(img)
                self._signals.health_preview.emit(resize_and_center_image(img, self.preview_size))
            except Exception as e:
                self._signals.health_placeholder.emit(f"預覽擷取失敗\n{str(e)}")

        threading.Thread(target=_capture, daemon=True).start()

    def capture_mana_preview_async(self):
        if not self.selected_mana_region:
            return

        def _capture():
            try:
                _, img = capture_window_region_pil(self.window_title, self.selected_mana_region)
                if img is None:
                    self._signals.mana_placeholder.emit(self._app.get_text("waiting_for_game_window"))
                    return
                img.thumbnail((200, 200))
                save_screenshot(img, "health_monitor_mana_preview.png")
                draw_scale_lines(img)
                self._signals.mana_preview.emit(resize_and_center_image(img, self.preview_size))
            except Exception as e:
                self._signals.mana_placeholder.emit(f"魔力預覽擷取失敗\n{str(e)}")

        threading.Thread(target=_capture, daemon=True).start()

    def test_preview(self):
        if not self.window_title:
            QMessageBox.warning(self, self._app.get_text("error"), self._app.get_text("select_game_window_first"))
            return
        if self._app.check_game_window_minimized(self.window_title):
            return
        try:
            windows = gw.getWindowsWithTitle(self.window_title)
            if not windows:
                QMessageBox.warning(self, self._app.get_text("error"), self._app.get_text("game_window_not_found_with_title").format(window_title=self.window_title))
                return

            def _perform():
                success_count = 0
                errors = []
                try:
                    if self._app.config.get("region"):
                        try:
                            self.capture_preview_async()
                            success_count += 1
                        except Exception as e:
                            errors.append(f"血量預覽測試失敗 {e}")
                    if self._app.config.get("mana_region"):
                        try:
                            self.capture_mana_preview_async()
                            success_count += 1
                        except Exception as e:
                            errors.append(f"魔力預覽測試失敗 {e}")
                except Exception as e:
                    errors.append(self._app.get_text("preview_test_failed").format(error=str(e)))
                finally:
                    self._signals.preview_test_result.emit(success_count, errors)

            threading.Thread(target=_perform, daemon=True).start()
        except Exception as e:
            QMessageBox.critical(self, self._app.get_text("error"), self._app.get_text("preview_test_failed").format(error=str(e)))

    # ────────────────────────── 觸發設定 ──────────────────────────

    def on_type_changed(self):
        if self.type_combo.currentText() == "HP":
            self.percent_entry.setText("60")
            self.key_entry.setText("1")
        else:
            self.percent_entry.setText("10")
            self.key_entry.setText("2")

    def add_setting_new(self):
        try:
            setting_type = self.type_combo.currentText()
            percent = int(self.percent_entry.text())
            key = self.key_entry.text().strip()
            cooldown = int(self.cooldown_entry.text())

            if not (0 <= percent <= 100):
                raise ValueError("百分比必須在0-100之間")
            if not key:
                raise ValueError("請輸入快捷鍵")
            if cooldown < 0:
                raise ValueError("冷卻時間不能為負數")
            if not _validate_key_sequence(key):
                raise ValueError("無效的快捷鍵格式。支援格式：單鍵（如 '5'）或多鍵序列（如 '1-5-esc'）")

            self._app.config.setdefault("settings", []).append({"type": setting_type, "percent": percent, "key": key, "cooldown": cooldown})
            self._append_setting_row(setting_type, percent, key, cooldown)
            self.on_type_changed()
            self._app.schedule_config_save()
        except ValueError as e:
            QMessageBox.warning(self, self._app.get_text("input_error"), str(e))
        except Exception as e:
            QMessageBox.critical(self, self._app.get_text("error"), self._app.get_text("add_setting_failed").format(error=str(e)))

    def _append_setting_row(self, setting_type, percent, key, cooldown):
        row = self.settings_tree.rowCount()
        self.settings_tree.insertRow(row)
        values = ("HP" if setting_type == "HP" else "MP", str(percent), key, str(cooldown))
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.settings_tree.setItem(row, col, item)

    def remove_setting(self):
        row = self.settings_tree.currentRow()
        if row < 0:
            QMessageBox.warning(self, self._app.get_text("important_reminder"), self._app.get_text("select_setting_to_remove_first"))
            return
        if QMessageBox.question(self, self._app.get_text("confirm"), self._app.get_text("confirm_remove_setting")) != QMessageBox.StandardButton.Yes:
            return

        values = []
        for col in range(4):
            item = self.settings_tree.item(row, col)
            values.append(item.text() if item is not None else "")
        self.settings_tree.removeRow(row)
        self._app.config["settings"] = [
            s
            for s in self._app.config.get("settings", [])
            if not ((s.get("type", "HP") == ("HP" if values[0] == "HP" else "MP")) and s["percent"] == int(values[1]) and s["key"] == values[2] and s.get("cooldown", 1000) == int(values[3]))
        ]
        self._app.schedule_config_save()

    def load_settings_to_tree(self):
        self.settings_tree.setRowCount(0)
        for setting in self._app.config.get("settings", []):
            setting_type = setting.get("type", "HP")
            cooldown = setting.get("cooldown", 1000)
            self._append_setting_row(setting_type, setting["percent"], setting["key"], cooldown)

    # ────────────────────────── 即時更新（worker thread 呼叫） ──────────────────────────

    def update_status(self, health, mana, color, trigger):
        now = time.time() * 1000
        if (now - self.last_status_update) < self.status_update_interval:
            return
        self._signals.status_updated.emit(health, mana, color, trigger)
        self.last_status_update = now

    def update_live_preview(self, img, health_percent):
        if not self._app.preview_enabled:
            return
        now = time.time() * 1000
        interval = getattr(self._app, "preview_interval", 250)
        if abs(health_percent - self.last_health_percent) >= 5 or (now - self.last_preview_update) >= interval:
            try:
                self._signals.health_preview.emit(self._make_preview_pil(img, health_percent, is_mana=False))
                self.last_preview_update = now
                self.last_health_percent = health_percent
            except Exception as e:
                print(f"預覽更新失敗: {e}")

    def update_live_mana_preview(self, img, mana_percent):
        if not self._app.preview_enabled:
            return
        now = time.time() * 1000
        interval = getattr(self._app, "preview_interval", 250)
        if abs(mana_percent - self.last_mana_percent) >= 5 or (now - self.last_mana_preview_update) >= interval:
            try:
                self._signals.mana_preview.emit(self._make_preview_pil(img, mana_percent, is_mana=True))
                self.last_mana_preview_update = now
                self.last_mana_percent = mana_percent
            except Exception as e:
                print(f"魔力預覽更新失敗: {e}")

    def _make_preview_pil(self, cv_img, percent, is_mana):
        pil_img = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))
        (draw_mana_indicator if is_mana else draw_health_indicator)(pil_img, percent)
        draw_scale_lines(pil_img)
        return resize_and_center_image(pil_img, self.preview_size)

    def _show_health_preview_placeholder(self, message=None):
        self._signals.health_placeholder.emit(message or self._app.get_text("waiting_for_game_window"))

    def _show_mana_preview_placeholder(self, message=None):
        self._signals.mana_placeholder.emit(message or self._app.get_text("waiting_for_game_window"))

    # ────────────────────────── 主執行緒 slots ──────────────────────────

    def _on_status_updated(self, health, mana, color, trigger):
        self.health_label.setText(health)
        self.mana_label.setText(mana)
        self.color_label.setText(color)
        self.trigger_label.setText(trigger)

    def _on_health_preview(self, pil_img):
        self._set_preview_pixmap(self.preview_label, pil_img)

    def _on_mana_preview(self, pil_img):
        self._set_preview_pixmap(self.mana_preview_label, pil_img)

    @staticmethod
    def _set_preview_pixmap(label, pil_img):
        pix = _pil_to_qpixmap(pil_img)
        target = label.size()
        if target.width() > 0 and target.height() > 0:
            pix = pix.scaled(target, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        label.setPixmap(pix)
        label.setText("")

    def _on_health_placeholder(self, text):
        self.preview_label.setPixmap(QPixmap())
        self.preview_label.setText(text)

    def _on_mana_placeholder(self, text):
        self.mana_preview_label.setPixmap(QPixmap())
        self.mana_preview_label.setText(text)

    def _on_preview_test_result(self, success_count, errors):
        for msg in errors:
            print(msg)
        if success_count > 0:
            QMessageBox.information(self, self._app.get_text("settings_applied"), self._app.get_text("preview_test_completed").format(success_count=success_count))
        else:
            QMessageBox.warning(self, self._app.get_text("important_reminder"), self._app.get_text("no_testable_regions"))

    # ────────────────────────── 框選 overlay（Phase 4b） ──────────────────────────

    def start_selection(self):
        self._start_selection(is_mana=False)

    def start_mana_selection(self):
        self._start_selection(is_mana=True)

    def _start_selection(self, is_mana):
        if not self.window_title:
            QMessageBox.warning(self, self._app.get_text("error"), self._app.get_text("select_game_window_first"))
            return
        if self._app.check_game_window_minimized(self.window_title):
            return
        if self._app.is_monitoring():
            self._app.stop_monitoring()
            QMessageBox.information(self, self._app.get_text("important_reminder"), self._app.get_text("monitoring_auto_stopped_for_selection"))
        try:
            windows = gw.getWindowsWithTitle(self.window_title)
            if not windows:
                return
            game_window = windows[0]
            game_window.activate()
            time.sleep(0.1)

            self.window().hide()

            rect = QRect(game_window.left, game_window.top, game_window.width, game_window.height)
            instruction_key = "select_mana_bar_instruction" if is_mana else "select_health_bar_instruction"
            self._overlay = _SelectionOverlay(
                rect,
                "mana" if is_mana else "health",
                self._app.get_text(instruction_key),
                on_done=lambda region: self._on_selection_done(region, is_mana),
                on_cancel=self._finalize_selection_restore_gui,
            )
            self._overlay.show()
            self._overlay.raise_()
            self._overlay.activateWindow()
        except Exception as e:
            self._finalize_selection_restore_gui()
            error_key = "mana_selection_start_failed" if is_mana else "selection_start_failed"
            QMessageBox.critical(self, self._app.get_text("error"), self._app.get_text(error_key).format(error=str(e)))

    def _on_selection_done(self, region, is_mana):
        if is_mana:
            self.selected_mana_region = region
            self._app.config["mana_region"] = region
            self.mana_region_label.setText(get_mana_region_text(self._app.config, self._app.get_text))
            self.mana_region_label.setStyleSheet(self._region_label_style(color=SUCCESS))
            QTimer.singleShot(100, self.capture_mana_preview_async)
        else:
            self.selected_region = region
            self._app.config["region"] = region
            self.region_label.setText(get_region_text(self._app.config, self._app.get_text))
            self.region_label.setStyleSheet(self._region_label_style(color=SUCCESS))
            QTimer.singleShot(100, self.capture_preview_async)
        self._app.schedule_config_save()
        self._finalize_selection_restore_gui()

    def _finalize_selection_restore_gui(self):
        win = self.window()
        win.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self._app.always_on_top)
        win.show()
        win.raise_()
        win.activateWindow()

    # ────────────────────────── 控制項回呼 ──────────────────────────

    def _on_language_changed(self, display_name):
        if self._setting_language:
            return
        self._app.change_language_display(display_name)

    def _on_always_on_top_toggled(self, checked):
        self._app.set_always_on_top(checked)

    def _on_preview_interval_changed(self, text):
        try:
            self._app.preview_interval = int(text)
        except ValueError:
            pass
        self._app.schedule_config_save()

    def open_adjust_colors(self):
        AdjustColorsDialog(self._app, self).exec()

    def open_adjust_interface_ui(self):
        AdjustInterfaceUiDialog(self._app, self).exec()

    def _on_select_interface_ui(self):
        # 委派給 InventoryTab 的完整介面UI框選流程（overlay + 截圖 + 更新 label/preview）
        self._app.inventory_tab.start_interface_ui_selection()

    # ────────────────────────── 語言更新 ──────────────────────────

    def update_monitor_tab_language(self):
        texts = {
            "page_title_label": "monitor_title",
            "window_frame": "game_window_settings",
            "game_window_label": "game_window",
            "health_bar_region_label": "health_bar_region",
            "mana_bar_region_label": "mana_bar_region",
            "interface_ui_region_label": "interface_ui_region",
            "select_health_region_btn": "select_health_region",
            "select_mana_region_btn": "select_mana_region",
            "select_interface_ui_btn": "select_interface_ui",
            "trigger_settings_frame": "trigger_settings",
            "type_label": "type",
            "percentage_label": "percentage",
            "hotkey_label": "hotkey",
            "cooldown_label": "cooldown_ms",
            "add_trigger_btn": "add_trigger",
            "remove_selected_btn": "remove_selected",
            "adjust_colors_btn": "adjust_colors",
            "adjust_interface_ui_btn": "adjust_interface_ui",
            "multi_trigger_check": "multiple_triggers",
            "control_frame": "control_panel",
            "test_preview_btn": "test_preview",
            "check_freq_label": "check_frequency",
            "ms_label": "ms",
            "preview_ms_label": "ms",
            "reminder_label": "reminder_text",
            "language_label": "language",
            "gui_settings_label": "gui_settings",
            "always_on_top_check": "always_on_top",
            "preview_settings_label": "preview_settings",
            "enable_preview_check": "enable_preview",
            "preview_interval_label": "preview_interval",
            "real_time_status_frame": "real_time_status",
            "current_health_label": "current_health",
            "current_mana_label": "current_mana",
            "main_color_label": "main_color",
            "trigger_status_label": "trigger_status",
            "preview_frame": "region_preview",
            "health_preview_frame": "health_preview",
            "mana_preview_frame": "mana_preview",
            "interface_ui_preview_frame": "interface_ui_preview",
            "interface_ui_preview_hint": "interface_ui_preview_hint",
        }
        for attr, key in texts.items():
            widget = getattr(self, attr, None)
            if widget is not None:
                widget.setText(self._app.get_text(key))

        self.update_toggle_btn()

        self.settings_tree.setHorizontalHeaderLabels([self._app.get_text("type"), self._app.get_text("percentage"), self._app.get_text("hotkey"), self._app.get_text("cooldown_ms")])
        self.region_label.setText(get_region_text(self._app.config, self._app.get_text))
        self.mana_region_label.setText(get_mana_region_text(self._app.config, self._app.get_text))
        self.interface_ui_label.setText(get_interface_ui_region_text(self._app.interface_ui_region, self._app.get_text))

        tips = {
            "window_combo": "game_window_combo_tip",
            "type_combo": "trigger_type_tip",
            "percent_entry": "percentage_entry_tip",
            "key_entry": "hotkey_entry_tip",
            "cooldown_entry": "cooldown_entry_tip",
            "select_health_region_btn": "select_health_region_tip",
            "select_mana_region_btn": "select_mana_region_tip",
            "select_interface_ui_btn": "select_interface_ui_tip",
            "add_trigger_btn": "add_trigger_tip",
            "remove_selected_btn": "remove_selected_tip",
            "adjust_colors_btn": "adjust_colors_tip",
            "adjust_interface_ui_btn": "adjust_interface_ui_tip",
            "multi_trigger_check": "multiple_triggers_tip",
            "toggle_btn": "toggle_monitoring_tip",
            "interval_combo": "check_interval_tip",
            "always_on_top_check": "always_on_top_tip",
            "enable_preview_check": "enable_preview_tip",
            "preview_interval_entry": "preview_interval_tip",
            "test_preview_btn": "test_preview_tip",
        }
        for attr, key in tips.items():
            w = getattr(self, attr, None)
            if w is not None:
                w.setToolTip(self._app.get_text(key))

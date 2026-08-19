"""MainWindow — PySide6 FluentWindow 主外殼。

7 個 navigation 分頁：已移植 StatusTab 與 MonitorTab，其餘為 stub。
逐一移植各 tab 時，把對應 stub 換成真實 QWidget 即可。
業務邏輯模組（config_manager / language_system / …）全保留。
"""

from datetime import datetime

import pygetwindow as gw

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox, QVBoxLayout, QWidget
from qfluentwidgets import FluentIcon, FluentWindow, NavigationItemPosition, setThemeColor

from qt.monitor import MonitorTab
from qt.status import StatusTab
from window_key_sender import WindowKeySender

# ── 主題常數（與舊 dracula 色系對齊）──
ACCENT = "#bd93f9"
MUTED = "#b8b8c8"

# ── 分頁清單：(language key, FluentIcon, 該 tab 未來涵蓋的功能說明) ──
# tab_status / tab_health_monitor 已移植，不在此 stub 清單中。
STUB_TABS = [
    ("tab_inventory_clear", FluentIcon.SHOPPING_CART, "背包格分析、F3 清理、F6 拾取、排他格"),
    ("tab_skill_combo", FluentIcon.GAME, "技能連招編排與週期送鍵"),
    ("tab_help", FluentIcon.HELP, "使用說明"),
    ("tab_version", FluentIcon.UPDATE, "版本檢查、下載與套用更新"),
    ("tab_about", FluentIcon.INFO, "關於本工具"),
]


class StubTab(QWidget):
    """遷移前的佔位 tab：顯示該分頁未來涵蓋的功能。"""

    def __init__(self, title: str, scope: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 20px; font-weight: 600; color: #f8f8f2;")
        scope_label = QLabel(f"尚未移植 — 未來涵蓋：{scope}")
        scope_label.setWordWrap(True)
        scope_label.setStyleSheet(f"font-size: 13px; color: {MUTED};")

        layout.addWidget(title_label)
        layout.addWidget(scope_label)
        layout.addStretch(1)


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self._is_closing = False
        self._pending_timers = []
        self.start_time = datetime.now()

        # ── config / 語言（沿用既有非 GUI 模組）──
        self.config_manager = self.config_manager_factory()  # 取得 singleton
        self.config_manager.load_config()
        self.config = self.config_manager.config
        self.language_manager = self.language_manager_factory()
        self.current_language = self.config.get("language", "zh-tw")
        self.language_manager.change_language(self.current_language)

        # ── 血魔監控相關設定（與 tk 版 health_monitor.py 相同預設）──
        self.interface_ui_region = None
        self.health_threshold = 0.8
        self.red_h_range = 5
        self.green_h_range = 40
        self.red_saturation_min = 50
        self.red_value_min = 50
        self.green_saturation_min = 50
        self.green_value_min = 50
        self.interface_ui_mse_threshold = 800
        self.interface_ui_ssim_threshold = 0.6
        self.interface_ui_hist_threshold = 0.7
        self.interface_ui_color_threshold = 35
        self.preview_enabled = True
        self.preview_interval = 250
        self.always_on_top = False
        self._load_monitor_config()

        setThemeColor(ACCENT)
        self.setWindowTitle(self.get_text("window_title"))

        self._build_tabs()
        self.window_key_sender = WindowKeySender(self)
        self.resize(1280, 800)
        self.setMinimumSize(1000, 700)
        self._center_on_screen()

    def _load_monitor_config(self) -> None:
        cfg = self.config
        self.interface_ui_region = cfg.get("interface_ui_region")
        self.health_threshold = cfg.get("health_threshold", 0.8)
        self.red_h_range = cfg.get("red_h_range", 5)
        self.green_h_range = cfg.get("green_h_range", 40)
        self.red_saturation_min = cfg.get("red_saturation_min", 50)
        self.red_value_min = cfg.get("red_value_min", 50)
        self.green_saturation_min = cfg.get("green_saturation_min", 50)
        self.green_value_min = cfg.get("green_value_min", 50)
        self.interface_ui_mse_threshold = int(cfg.get("interface_ui_mse_threshold", 800))
        self.interface_ui_ssim_threshold = float(cfg.get("interface_ui_ssim_threshold", 0.6))
        self.interface_ui_hist_threshold = float(cfg.get("interface_ui_hist_threshold", 0.7))
        self.interface_ui_color_threshold = int(cfg.get("interface_ui_color_threshold", 35))
        self.preview_enabled = cfg.get("preview_enabled", True)
        self.preview_interval = cfg.get("preview_interval", 250)
        self.always_on_top = cfg.get("always_on_top", False)

    # 小間接：避免在 import 期即觸發 singleton 副作用，亦方便測試替換
    def config_manager_factory(self):
        from config_manager import get_config_manager

        return get_config_manager()

    def language_manager_factory(self):
        from language_system import get_language_manager

        return get_language_manager()

    def get_text(self, key):
        try:
            return self.language_manager.get_text(key)
        except Exception:
            return f"[{key}]"

    def add_status_message(self, message: str, msg_type: str = "info") -> None:
        """供 UI 主執行緒與 worker thread 共用（內部走 signal）。"""
        if hasattr(self, "status_tab"):
            self.status_tab.add_status_message(message, msg_type)

    def register_timer(self, timer) -> None:
        """登記 QTimer，關閉時統一停止（後續階段使用）。"""
        self._pending_timers.append(timer)

    def save_config(self) -> None:
        """血魔監控相關設定的 Qt 版儲存（對應 tk 版 save_config）。"""
        try:
            if hasattr(self, "monitor_tab"):
                mt = self.monitor_tab
                self.config["window_title"] = mt.window_title
                self.config["monitor_interval"] = mt.monitor_interval_ms / 1000.0
                self.config["multiple_triggers"] = mt.multi_trigger
                try:
                    self.config["preview_interval"] = int(mt.preview_interval_entry.text())
                except ValueError:
                    pass
            self.config["preview_enabled"] = self.preview_enabled
            self.config["always_on_top"] = self.always_on_top
            self.config["health_threshold"] = self.health_threshold
            self.config["red_h_range"] = self.red_h_range
            self.config["green_h_range"] = self.green_h_range
            self.config["red_saturation_min"] = self.red_saturation_min
            self.config["red_value_min"] = self.red_value_min
            self.config["green_saturation_min"] = self.green_saturation_min
            self.config["green_value_min"] = self.green_value_min
            self.config["interface_ui_mse_threshold"] = self.interface_ui_mse_threshold
            self.config["interface_ui_ssim_threshold"] = self.interface_ui_ssim_threshold
            self.config["interface_ui_hist_threshold"] = self.interface_ui_hist_threshold
            self.config["interface_ui_color_threshold"] = self.interface_ui_color_threshold
            if self.interface_ui_region:
                self.config["interface_ui_region"] = self.interface_ui_region
            self.config["language"] = self.current_language
            self.config_manager.save_config(self.config)
            self.add_status_message(self.get_text("all_records_saved"), "success")
        except Exception as e:
            self.add_status_message(self.get_text("save_failed").format(error=str(e)), "error")

    # ── 監控迴圈（Phase 4d 移植完整迴圈；目前為佔位）──
    def start_monitoring(self):
        self.add_status_message(self.get_text("start_monitoring") + "（迴圈將於 Phase 4d 移植）", "warning")

    def stop_monitoring(self):
        self.add_status_message(self.get_text("stop_monitoring"), "info")

    def toggle_always_on_top(self) -> None:
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self.always_on_top)
        self.show()

    def check_game_window_minimized(self, window_title) -> bool:
        """遊戲視窗最小化時顯示提醒並回傳 True（對應 tk 版）。"""
        try:
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                return False
            if windows[0].isMinimized:
                QMessageBox.warning(self, self.get_text("warning"), self.get_text("game_window_minimized_warning"))
                return True
            return False
        except Exception as e:
            print(f"[WARN] 檢查遊戲視窗狀態失敗: {e}")
            return False

    def change_language_display(self, display_name: str) -> None:
        mapping = {"繁體中文": "zh-tw", "English": "en"}
        new_language = mapping.get(display_name, "zh-tw")
        if new_language == self.current_language:
            return
        self.current_language = new_language
        self.language_manager.change_language(new_language)
        self.config["language"] = new_language
        self.save_config()
        self.setWindowTitle(self.get_text("window_title"))
        if hasattr(self, "monitor_tab"):
            self.monitor_tab.update_monitor_tab_language()

    def _build_tabs(self) -> None:
        for key, icon, scope in STUB_TABS:
            tab = StubTab(self.get_text(key), scope)
            tab.setObjectName(key)
            self.addSubInterface(tab, icon, self.get_text(key), NavigationItemPosition.TOP)

        # ── MonitorTab（已移植：Phase 4a UI + 觸發列表 + 預覽）──
        self.monitor_tab = MonitorTab(self)
        self.monitor_tab.setObjectName("tab_health_monitor")
        self.addSubInterface(self.monitor_tab, FluentIcon.HEART, self.get_text("tab_health_monitor"), NavigationItemPosition.TOP)

        # ── StatusTab（已移植）──
        self.status_tab = StatusTab(self)
        self.status_tab.setObjectName("tab_status")
        self.addSubInterface(self.status_tab, FluentIcon.HISTORY, self.get_text("tab_status"), NavigationItemPosition.TOP)

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(geo.center() - self.rect().center())

    def _shutdown(self) -> None:
        """關閉清理。後續階段加入：usage_tracker、keyboard.unhook_all、背景 thread join。"""
        for timer in self._pending_timers:
            timer.stop()
        self._pending_timers.clear()
        try:
            self.stop_monitoring()
        except Exception:
            pass
        try:
            self.save_config()
        except Exception:
            pass
        runtime = datetime.now() - self.start_time
        print(f"應用程式運行時間: {runtime}")

    def closeEvent(self, e):
        if self._is_closing:
            e.accept()
            return
        self._is_closing = True
        try:
            self._shutdown()
        except Exception as err:
            print(f"關閉清理失敗: {err}")
        e.accept()

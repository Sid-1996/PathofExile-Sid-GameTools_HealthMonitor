"""MainWindow — PySide6 FluentWindow 主外殼。

已移植 StatusTab / MonitorTab / InventoryTab，其餘為 stub。
逐一移植各 tab 時，把對應 stub 換成真實 QWidget 即可。
業務邏輯模組（config_manager / language_system / …）全保留。
"""

import threading
import time
from datetime import datetime

import pygetwindow as gw

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox, QVBoxLayout, QWidget
from qfluentwidgets import FluentIcon, FluentWindow, NavigationItemPosition, setThemeColor

from monitor_analyzer import (
    analyze_health,
    analyze_mana,
    check_triggers,
    get_health_color_ratio,
    get_main_color,
    get_mana_color_ratio,
    interruptible_sleep,
    is_health_color,
    is_mana_color,
    trigger_actions,
)
from qt.inventory import InventoryTab
from qt.monitor import MonitorTab
from qt.status import StatusTab
from window_key_sender import WindowKeySender

# ── 主題常數（與舊 dracula 色系對齊）──
ACCENT = "#bd93f9"
MUTED = "#b8b8c8"

# ── 分頁清單：(language key, FluentIcon, 該 tab 未來涵蓋的功能說明) ──
# tab_status / tab_health_monitor / tab_inventory_clear 已移植，不在此 stub 清單中。
STUB_TABS = [
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

        # ── 監控狀態（worker thread 用；bool + Lock）──
        self._monitoring = False
        self._monitoring_lock = threading.Lock()
        self._monitor_thread = None
        self._last_trigger_times = {}

        # ── 全域暫停 / F3 清包中斷旗標（InventoryTab F3/F6 流程用）──
        self._global_pause = False
        self.inventory_clear_interrupt = False

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
        self.setup_hotkeys()
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

    # ── 血魔監控迴圈（Phase 4d：worker thread，UI 更新一律走 MonitorTab 的 signal）──

    def is_monitoring(self) -> bool:
        with self._monitoring_lock:
            return self._monitoring

    def set_monitoring(self, state: bool) -> None:
        with self._monitoring_lock:
            self._monitoring = state

    def start_monitoring(self):
        if self.is_monitoring():
            print("[WARN] 監控已在運行中，跳過重複啟動")
            return
        mt = self.monitor_tab
        if not mt.window_title:
            QMessageBox.warning(self, self.get_text("error"), self.get_text("select_game_window_first"))
            return
        if self.check_game_window_minimized(mt.window_title):
            return
        if not self.config.get("region"):
            QMessageBox.warning(self, self.get_text("error"), self.get_text("select_health_bar_region_first"))
            return
        if not self.config.get("settings"):
            QMessageBox.warning(self, self.get_text("error"), self.get_text("set_at_least_one_trigger"))
            return

        try:
            windows = gw.getWindowsWithTitle(mt.window_title)
            if windows:
                windows[0].activate()
                time.sleep(0.1)
        except Exception as e:
            print(f"激活遊戲視窗失敗: {e}")

        self.set_monitoring(True)
        mt.start_btn.setEnabled(False)
        mt.stop_btn.setEnabled(True)
        self.add_status_message(self.get_text("health_monitor_started"), "success")
        self.setWindowOpacity(0.8)  # 非干擾模式

        self._monitor_thread = threading.Thread(target=self.monitor_health, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self):
        if not self.is_monitoring():
            return
        print("[STOP] 正在停止監控")
        self.set_monitoring(False)
        self.monitor_tab.start_btn.setEnabled(True)
        self.monitor_tab.stop_btn.setEnabled(False)
        self.add_status_message(self.get_text("health_monitor_stopped"), "info")
        self.setWindowOpacity(1.0)
        self._monitor_thread = None  # daemon 執行緒會在下次 interruptible_sleep 檢查時退出

    def _is_interface_ui_visible(self, game_window) -> bool:
        """介面UI（戰鬥狀態）偵測 — 委派給 InventoryTab 的移植版實作。"""
        if hasattr(self, "inventory_tab"):
            return self.inventory_tab.is_interface_ui_visible(game_window)
        return False

    def press_key_sequence(self, key_sequence, health_percent=None):
        """多鍵序列依序送出（keyboard 庫 + 防重複），並記錄冷卻時間。"""
        import keyboard

        keys = [key.strip() for key in key_sequence.split("-")]
        game_hwnd = self.window_key_sender.get_game_window_handle()
        if game_hwnd:
            for i, key in enumerate(keys):
                vk_code = self.window_key_sender.map_key_to_vk_code(key)
                if vk_code:
                    self.window_key_sender.send_key_to_window(game_hwnd, vk_code)
                if i < len(keys) - 1:
                    time.sleep(0.025)
        else:
            for i, key in enumerate(keys):
                keyboard.press_and_release(self.window_key_sender.map_key_name(key))
                if i < len(keys) - 1:
                    time.sleep(0.025)

        if health_percent is not None:
            if isinstance(health_percent, str) and health_percent.startswith("mana_"):
                self._last_trigger_times[f"mana_{int(health_percent.split('_')[1])}"] = time.time()
            else:
                self._last_trigger_times[health_percent] = time.time()

    def monitor_health(self):
        from capture_utils import _mss_singleton, capture_region_to_cv2

        with _mss_singleton:
            while self.is_monitoring():
                try:
                    windows = gw.getWindowsWithTitle(self.monitor_tab.window_title)
                    if not windows:
                        self.monitor_tab.update_status("--", "--", self.get_text("window_not_found"), "")
                        self.add_status_message(self.get_text("game_window_closed"), "warning")
                        interruptible_sleep(1.0, self.is_monitoring)
                        continue

                    window = windows[0]

                    if window.isMinimized or not window.isActive:
                        if window.isMinimized:
                            self.monitor_tab.update_status("--", "--", self.get_text("game_window_minimized"), "")
                        else:
                            self.monitor_tab.update_status("--", "--", self.get_text("waiting_for_game_window"), "")
                        if not self.monitor_tab._preview_placeholder_shown:
                            self.monitor_tab._preview_placeholder_shown = True
                            msg_key = "game_window_minimized" if window.isMinimized else "game_window_lost_focus"
                            self.add_status_message(self.get_text(msg_key), "warning")
                            self.monitor_tab._show_health_preview_placeholder()
                            self.monitor_tab._show_mana_preview_placeholder()
                        interruptible_sleep(0.5, self.is_monitoring)
                        continue
                    if self.monitor_tab._preview_placeholder_shown:
                        self.monitor_tab._preview_placeholder_shown = False
                        self.add_status_message(self.get_text("game_window_regained_focus"), "success")

                    x, y, w, h = self.config["region"]
                    monitor = {"top": window.top + y, "left": window.left + x, "width": w, "height": h}
                    img = capture_region_to_cv2(monitor)

                    health_percent = analyze_health(
                        img,
                        lambda seg: is_health_color(
                            seg, self.red_saturation_min, self.red_value_min, self.red_h_range, self.green_h_range, self.green_saturation_min, self.green_value_min, self.health_threshold
                        ),
                        lambda seg: get_health_color_ratio(seg, self.red_saturation_min, self.red_value_min, self.red_h_range, self.green_h_range, self.green_saturation_min, self.green_value_min),
                        self.health_threshold,
                    )
                    main_color = get_main_color(img)

                    mana_percent = "--"
                    if self.config.get("mana_region"):
                        try:
                            mx, my, mw, mh = self.config["mana_region"]
                            mana_monitor = {"top": window.top + my, "left": window.left + mx, "width": mw, "height": mh}
                            mana_img = capture_region_to_cv2(mana_monitor)
                            mana_percent = analyze_mana(mana_img, is_mana_color, get_mana_color_ratio)
                            self.monitor_tab.update_live_mana_preview(mana_img, mana_percent)
                        except Exception as e:
                            print(f"魔力分析錯誤: {e}")
                            mana_percent = "--"

                    mana_value = int(mana_percent) if mana_percent != "--" else None
                    self.monitor_tab.update_status(
                        f"{health_percent}%",
                        f"{mana_percent}%",
                        main_color,
                        check_triggers(
                            health_percent,
                            mana_value,
                            self.config,
                            self._last_trigger_times,
                            self.get_text,
                            self._is_interface_ui_visible,
                            self.monitor_tab.window_title,
                            self.interface_ui_region,
                            None,
                        ),
                    )

                    self.monitor_tab.update_live_preview(img, health_percent)

                    trigger_actions(
                        health_percent,
                        mana_value,
                        self.config,
                        self._last_trigger_times,
                        self.monitor_tab.multi_trigger,
                        self.add_status_message,
                        self.get_text,
                        self._is_interface_ui_visible,
                        self.press_key_sequence,
                        self.monitor_tab.window_title,
                        self.interface_ui_region,
                        None,
                    )

                    interruptible_sleep(self.monitor_tab.monitor_interval_ms / 1000.0, self.is_monitoring)

                except Exception as e:
                    print(f"監控錯誤: {e}")
                    self.monitor_tab.update_status("--", "--", "--", self.get_text("error_prefix").format(error=str(e)))
                    interruptible_sleep(1.0, self.is_monitoring)

    def toggle_always_on_top(self) -> None:
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self.always_on_top)
        self.show()

    def should_keep_topmost(self) -> bool:
        """GUI 是否保持在最上方（對應 tk 版同名方法）。"""
        return bool(self.always_on_top)

    def is_global_pause(self) -> bool:
        return bool(self._global_pause)

    def set_global_pause(self, state: bool) -> None:
        self._global_pause = bool(state)

    def setup_hotkeys(self) -> None:
        """註冊 F3/F6 全局熱鍵（F9 全域暫停等後續階段補齊）。"""
        try:
            import keyboard

            keyboard.add_hotkey("f3", self.inventory_tab.request_f3)
            keyboard.add_hotkey("f6", self.inventory_tab.request_f6)
            print("已註冊 F3/F6 全局熱鍵")
        except Exception as e:
            print(f"註冊熱鍵失敗: {e}")

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
        if hasattr(self, "inventory_tab"):
            self.inventory_tab.update_inventory_tab_language()

    def _build_tabs(self) -> None:
        for key, icon, scope in STUB_TABS:
            tab = StubTab(self.get_text(key), scope)
            tab.setObjectName(key)
            self.addSubInterface(tab, icon, self.get_text(key), NavigationItemPosition.TOP)

        # ── MonitorTab（已移植：Phase 4a UI + 觸發列表 + 預覽）──
        self.monitor_tab = MonitorTab(self)
        self.monitor_tab.setObjectName("tab_health_monitor")
        self.addSubInterface(self.monitor_tab, FluentIcon.HEART, self.get_text("tab_health_monitor"), NavigationItemPosition.TOP)

        # ── InventoryTab（已移植：Phase 5 UI 骨架 + 框選/預覽/排除/F3/F6）──
        self.inventory_tab = InventoryTab(self)
        self.inventory_tab.setObjectName("tab_inventory_clear")
        self.addSubInterface(self.inventory_tab, FluentIcon.SHOPPING_CART, self.get_text("tab_inventory_clear"), NavigationItemPosition.TOP)

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
        """關閉清理。後續階段加入：usage_tracker。"""
        for timer in self._pending_timers:
            timer.stop()
        self._pending_timers.clear()
        try:
            import keyboard

            keyboard.unhook_all()
        except Exception:
            pass
        for timer in self._pending_timers:
            timer.stop()
        self._pending_timers.clear()
        thread = getattr(self, "_monitor_thread", None)
        try:
            self.stop_monitoring()
        except Exception:
            pass
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.0)
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

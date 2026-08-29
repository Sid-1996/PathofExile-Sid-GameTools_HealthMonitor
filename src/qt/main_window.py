"""MainWindow — PySide6 FluentWindow 主外殼。

已移植 StatusTab / MonitorTab / InventoryTab / ComboTab / HelpTab / AboutTab / VersionTab。
業務邏輯模組（config_manager / language_system / …）全保留。
"""

import logging
import sys
import threading
import time
import webbrowser
from datetime import datetime
from typing import Dict, Optional

import pygetwindow as gw

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget
from qfluentwidgets import FluentIcon, FluentWindow, NavigationItemPosition, setThemeColor

from auto_click_manager import AutoClickManager
from inventory_utils import normalize_region
from _version import __version__
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
    reset_battle_debug_state,
    trigger_actions,
)
from qt.about import AboutTab
from qt.combo import ComboTab
from qt.help import HelpTab
from qt.inventory import InventoryTab
from qt.monitor import MonitorTab
from qt.status import StatusTab
from qt.version import VersionTab
from usage_tracker import UsageTracker
from utils import set_app_instance
from window_key_sender import WindowKeySender

logger = logging.getLogger(__name__)

# ── 主題常數（與舊 dracula 色系對齊）──
ACCENT = "#bd93f9"
MUTED = "#b8b8c8"

# ── 最大化/還原檔位：還原時固定縮到這個尺寸（小螢幕自動 clamp）──
RESTORE_SIZE = (1600, 900)


class MainWindow(FluentWindow):
    # 熱鍵 callback 跑在 keyboard 函式庫監聽執行緒，不能在此直接碰 Qt widget；
    # 改走 queued signal 送回主執行緒（修 F10 停止監控 GUI 死結）。
    f10_request = Signal()
    f12_request = Signal()

    def __init__(self):
        self._initialized = False  # 必須在 super().__init__() 之前，避免建構期事件誤觸
        self._was_maximized = False
        super().__init__()
        self._is_closing = False
        self._pending_timers = []
        self.start_time = datetime.now()
        set_app_instance(self)  # F12 緊急關閉（utils）

        # ── 即時儲存：debounced autosave（400ms 合併寫入，避免每次敲鍵都整檔重寫）──
        self._config_save_timer = QTimer(self)
        self._config_save_timer.setSingleShot(True)
        self._config_save_timer.timeout.connect(self.save_config)

        # ── 監控狀態（worker thread 用；bool + Lock）──
        self._monitoring = False
        self._monitoring_lock = threading.Lock()
        self._monitor_thread = None
        self._last_trigger_times = {}

        # ── 全域暫停 / F3 清包中斷旗標（InventoryTab F3/F6 流程用）──
        self._global_pause = False
        self.inventory_clear_interrupt = False

        # ── 使用時間統計（沿用 usage_tracker 保留模組：registry 載入/儲存）──
        self._usage_tracker = UsageTracker(self)  # 設定 self.total_usage_time
        self._usage_timer = QTimer(self)
        self._usage_timer.timeout.connect(self._on_usage_tick)
        self._usage_timer.start(60000)

        # ── config / 語言（沿用既有非 GUI 模組）──
        self.config_manager = self.config_manager_factory()  # 取得 singleton
        self.config_manager.load_config()
        self.config = self.config_manager.config
        self.language_manager = self.language_manager_factory()
        self.current_language = self.config.get("language", "zh-tw")
        self.language_manager.change_language(self.current_language)

        # ── 血魔監控相關設定（與 tk 版 health_monitor.py 相同預設）──
        self.interface_ui_region: Optional[Dict[str, int]] = None
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
        self.f10_request.connect(self.toggle_monitoring)
        self.f12_request.connect(self.close_app)
        self.setup_hotkeys()

        # ── 自動點擊（AHK，沿用 auto_click_manager 保留模組）──
        self.auto_click_manager = AutoClickManager(self)
        if "--smoke" not in sys.argv:
            self.auto_click_manager.setup_auto_click_listener()

        self.setMinimumSize(1000, 700)
        self._snap_to_restore_size()  # 預設 1600×900（小螢幕自動 clamp）
        self._center_on_screen()

        self._initialized = True

    def _load_monitor_config(self) -> None:
        cfg = self.config
        # 相容 tk 世代以 positional list 儲存的 legacy config → 一律正規化為 dict
        self.interface_ui_region = normalize_region(cfg.get("interface_ui_region"))
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

    def schedule_config_save(self) -> None:
        """即時儲存入口：debounce 400ms 後統一整包寫入。關閉/初始化期間忽略。"""
        if self._is_closing or not self._initialized:
            return
        self._config_save_timer.start(400)

    def save_config(self) -> None:
        """血魔監控相關設定的 Qt 版儲存（對應 tk 版 save_config）。"""
        try:
            if hasattr(self, "monitor_tab"):
                mt = self.monitor_tab
                if str(mt.window_title or "").startswith("__SMOKE_"):
                    self.config.pop("window_title", None)  # 清掉 smoke 測試殘留的假視窗標題
                else:
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
            logger.warning("監控已在運行中，跳過重複啟動")
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

        reset_battle_debug_state()

        # 介面UI 未截時僅警示一次，不阻擋（可選過濾語意，參照 ocr-trigger）
        if not (self.interface_ui_region and getattr(self.inventory_tab, "interface_ui_screenshot", None) is not None):
            self.add_status_message(
                self.get_text("interface_ui_not_set_warning")
                if self.get_text("interface_ui_not_set_warning") != "[interface_ui_not_set_warning]"
                else "未截介面UI：將在任何場景觸發，非僅戰鬥（建議框選介面UI以啟用戰鬥過濾）",
                "warning",
            )

        self.set_monitoring(True)
        mt.update_toggle_btn()
        self.add_status_message(self.get_text("health_monitor_started"), "success")
        self.setWindowOpacity(0.8)  # 非干擾模式
        self._refresh_status_bar()  # 狀態列監控燈

        self._monitor_thread = threading.Thread(target=self.monitor_health, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self):
        if not self.is_monitoring():
            return
        logger.info("正在停止監控")
        self.set_monitoring(False)
        self.monitor_tab.update_toggle_btn()
        self.add_status_message(self.get_text("health_monitor_stopped"), "info")
        self.setWindowOpacity(1.0)
        self._refresh_status_bar()  # 狀態列監控燈
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
        from capture_utils import capture_window_region_bgr

        while self.is_monitoring():
            try:
                windows = gw.getWindowsWithTitle(self.monitor_tab.window_title)
                if not windows:
                    self.monitor_tab.update_status("--", "--", self.get_text("window_not_found"), "")
                    self.add_status_message(self.get_text("game_window_closed"), "warning")
                    interruptible_sleep(1.0, self.is_monitoring)
                    continue

                window = windows[0]

                if window.isMinimized:
                    if not self.monitor_tab._preview_placeholder_shown:
                        self.monitor_tab._preview_placeholder_shown = True
                        self.add_status_message(self.get_text("game_window_minimized"), "warning")
                        self.monitor_tab._show_health_preview_placeholder(self.get_text("game_window_minimized"))
                        self.monitor_tab._show_mana_preview_placeholder(self.get_text("game_window_minimized"))
                    self.monitor_tab.update_status("--", "--", self.get_text("game_window_minimized"), "")
                    interruptible_sleep(0.5, self.is_monitoring)
                    continue
                if self.monitor_tab._preview_placeholder_shown:
                    self.monitor_tab._preview_placeholder_shown = False
                    self.add_status_message(self.get_text("monitoring_resumed"), "success")

                # 後台截圖：WGC 成功（被遮擋/失焦）或 mss 成功（僅前景）→ 分析；
                # None（視窗不存在/最小化/WGC 不可用且非前景）→ 暫停等待
                result = capture_window_region_bgr(self.monitor_tab.window_title, self.config["region"])
                if result is None:
                    if not self.monitor_tab._preview_placeholder_shown:
                        self.monitor_tab._preview_placeholder_shown = True
                        self.add_status_message(self.get_text("waiting_for_game_window"), "warning")
                        self.monitor_tab._show_health_preview_placeholder()
                        self.monitor_tab._show_mana_preview_placeholder()
                    self.monitor_tab.update_status("--", "--", self.get_text("waiting_for_game_window"), "")
                    interruptible_sleep(0.3, self.is_monitoring)
                    continue

                img = result[1]
                game_foreground = window.isActive  # 操控一律前景：非前景只分析不按鍵

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
                        mana_result = capture_window_region_bgr(self.monitor_tab.window_title, self.config["mana_region"])
                        if mana_result is not None:
                            mana_img = mana_result[1]
                            mana_percent = analyze_mana(mana_img, is_mana_color, get_mana_color_ratio)
                            self.monitor_tab.update_live_mana_preview(mana_img, mana_percent)
                    except Exception as e:
                        logger.error("魔力分析錯誤: %s", e)
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
                        self.inventory_tab.interface_ui_screenshot,
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
                    self.inventory_tab.interface_ui_screenshot,
                    game_foreground,
                )

                interruptible_sleep(self.monitor_tab.monitor_interval_ms / 1000.0, self.is_monitoring)

            except Exception as e:
                logger.error("監控錯誤: %s", e)
                self.monitor_tab.update_status("--", "--", "--", self.get_text("error_prefix").format(error=str(e)))
                interruptible_sleep(1.0, self.is_monitoring)

    def set_always_on_top(self, checked: bool) -> None:
        """單一事實來源：更新 flag、同步各頁勾選框並排程存檔。"""
        self.always_on_top = bool(checked)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self.always_on_top)
        self.show()
        for tab_name in ("monitor_tab", "inventory_tab"):
            cb = getattr(getattr(self, tab_name, None), "always_on_top_check", None)
            if cb is not None and cb.isChecked() != self.always_on_top:
                cb.blockSignals(True)
                cb.setChecked(self.always_on_top)
                cb.blockSignals(False)
        self.schedule_config_save()

    def should_keep_topmost(self) -> bool:
        """GUI 是否保持在最上方（對應 tk 版同名方法）。"""
        return bool(self.always_on_top)

    def is_global_pause(self) -> bool:
        return bool(self._global_pause)

    def set_global_pause(self, state: bool) -> None:
        self._global_pause = bool(state)
        self._refresh_status_bar()

    def setup_hotkeys(self) -> None:
        """註冊全局熱鍵：F3 清包 / F5 回藏身處 / F6 拾取 / F9 全域暫停 / F10 監控切換 / F12 緊急關閉。"""
        try:
            import keyboard

            keyboard.add_hotkey("f3", self.inventory_tab.request_f3)
            keyboard.add_hotkey("f6", self.inventory_tab.request_f6)
            if hasattr(self.inventory_tab, "return_to_hideout"):
                keyboard.add_hotkey("f5", self.inventory_tab.return_to_hideout)
            keyboard.add_hotkey("f9", self.toggle_global_pause)
            keyboard.add_hotkey("f10", self.f10_request.emit)
            keyboard.add_hotkey("f12", self.f12_request.emit)
            logger.info("已註冊 F3/F5/F6/F9/F10/F12 全局熱鍵")
        except Exception as e:
            logger.error("註冊熱鍵失敗: %s", e)

    def toggle_global_pause(self) -> None:
        """F9：全域暫停 - 暫停/恢復全部熱鍵與監控（安全網）。"""
        # 統一經 set_global_pause 改旗標，狀態列暫停燈只掛在單一變更點
        self.set_global_pause(not self._global_pause)
        if self._global_pause:
            self.add_status_message(self.get_text("global_pause_activated"), "warning")
        else:
            self.add_status_message(self.get_text("global_pause_deactivated"), "success")

    def toggle_monitoring(self) -> None:
        """F10：血魔監控開關（安全網）。"""
        if self._global_pause:
            logger.info("全域暫停中，跳過 F10 熱鍵")
            self.add_status_message(self.get_text("f10_skip_global_pause"), "warning")
            return
        key = "f10_stop_monitoring" if self.is_monitoring() else "f10_start_monitoring"
        self.add_status_message(self.get_text(key), "hotkey")
        self._toggle_monitoring_core()

    def toggle_monitoring_btn(self) -> None:
        """監控切換按鈕：依目前狀態啟動/停止（不顯示 F10 訊息）。"""
        if self._global_pause:
            return
        self._toggle_monitoring_core()

    def _toggle_monitoring_core(self) -> None:
        if self.is_monitoring():
            self.stop_monitoring()
        else:
            self.start_monitoring()

    def close_app(self) -> None:
        """F12 緊急關閉：觸發正常關閉流程。"""
        if self._is_closing:
            return
        self.close()  # 觸發 closeEvent → _shutdown

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
            logger.warning("檢查遊戲視窗狀態失敗: %s", e)
            return False

    def change_language_display(self, display_name: str) -> None:
        mapping = {"繁體中文": "zh-tw", "English": "en"}
        new_language = mapping.get(display_name, "zh-tw")
        if new_language == self.current_language:
            return
        self.current_language = new_language
        self.language_manager.change_language(new_language)
        self.config["language"] = new_language
        self.schedule_config_save()
        self.setWindowTitle(self.get_text("window_title"))
        if hasattr(self, "monitor_tab"):
            self.monitor_tab.update_monitor_tab_language()
        if hasattr(self, "inventory_tab"):
            self.inventory_tab.update_inventory_tab_language()
        if hasattr(self, "combo_tab"):
            self.combo_tab.update_combo_tab_language()
        if hasattr(self, "status_tab"):
            self.status_tab.update_status_tab_language()
        if hasattr(self, "help_tab"):
            self.help_tab.update_language()
        if hasattr(self, "version_tab"):
            self.version_tab.update_language()
        if hasattr(self, "about_tab"):
            self.about_tab.update_language()

    def _on_usage_tick(self) -> None:
        self.total_usage_time += 60
        try:
            self._usage_tracker.save_usage_time_to_registry(self.total_usage_time)
        except Exception:
            pass
        if hasattr(self, "about_tab"):
            self.about_tab.refresh_usage_time()

    def open_video_link(self, url: str) -> None:
        """打開影片/外部連結"""
        try:
            webbrowser.open(url)
        except Exception as e:
            QMessageBox.critical(self, self.get_text("error"), self.get_text("browser_open_failed").format(error=e))

    def _build_tabs(self) -> None:
        # ── 底部狀態列（必須早於 addSubInterface / 連點啟動建立）──
        self._build_status_bar()

        # ── MonitorTab（已移植：Phase 4a UI + 觸發列表 + 預覽）──
        self.monitor_tab = MonitorTab(self)
        self.monitor_tab.setObjectName("tab_health_monitor")
        self.addSubInterface(self.monitor_tab, FluentIcon.HEART, self.get_text("tab_health_monitor"), NavigationItemPosition.TOP)

        # ── InventoryTab（已移植：Phase 5 UI 骨架 + 框選/預覽/排除/F3/F6）──
        self.inventory_tab = InventoryTab(self)
        self.inventory_tab.setObjectName("tab_inventory_clear")
        self.addSubInterface(self.inventory_tab, FluentIcon.SHOPPING_CART, self.get_text("tab_inventory_clear"), NavigationItemPosition.TOP)

        # ── ComboTab（已移植：Phase 6 連段套組 + 技能計時器）──
        self.combo_tab = ComboTab(self)
        self.combo_tab.setObjectName("tab_skill_combo")
        self.addSubInterface(self.combo_tab, FluentIcon.GAME, self.get_text("tab_skill_combo"), NavigationItemPosition.TOP)

        # ── StatusTab（已移植）──
        self.status_tab = StatusTab(self)
        self.status_tab.setObjectName("tab_status")
        self.addSubInterface(self.status_tab, FluentIcon.HISTORY, self.get_text("tab_status"), NavigationItemPosition.TOP)

        # ── HelpTab（已移植：Phase 7 使用說明）──
        self.help_tab = HelpTab(self)
        self.help_tab.setObjectName("tab_help")
        self.addSubInterface(self.help_tab, FluentIcon.HELP, self.get_text("tab_help"), NavigationItemPosition.TOP)

        # ── VersionTab（已移植：Phase 7 版本檢查/下載/更新）──
        self.version_tab = VersionTab(self)
        self.version_tab.setObjectName("tab_version")
        self.addSubInterface(self.version_tab, FluentIcon.UPDATE, self.get_text("tab_version"), NavigationItemPosition.TOP)

        # ── AboutTab（已移植：Phase 7 關於本工具）──
        self.about_tab = AboutTab(self)
        self.about_tab.setObjectName("tab_about")
        self.addSubInterface(self.about_tab, FluentIcon.INFO, self.get_text("tab_about"), NavigationItemPosition.TOP)

    # ── 底部狀態列（監控/連點/全域暫停/版本）──────────────────
    def _build_status_bar(self) -> None:
        """內容區底部的狀態列（導覽列右側）。在 _build_tabs 最前建立，
        確保早於 addSubInterface 與連點(AHK)啟動，連點燈才不會撞上不存在的屬性。"""
        # 把 stackedWidget 移入新的垂直巢層，底部騰出狀態列空間
        self._status_container = QVBoxLayout()
        self._status_container.setSpacing(0)
        self._status_container.setContentsMargins(0, 0, 0, 0)
        self.widgetLayout.removeWidget(self.stackedWidget)
        self.widgetLayout.addLayout(self._status_container)
        self._status_container.addWidget(self.stackedWidget, 1)

        bar = QWidget(self)
        bar.setObjectName("status_bar")
        bar.setFixedHeight(28)
        bar.setStyleSheet("#status_bar { background: rgba(30,30,46,0.85); border-top: 1px solid #3d3d5c; }QLabel { font-size: 12px; color: #b8b8c8; }")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(20)

        self._status_monitor_label = QLabel()
        self._status_click_label = QLabel()
        self._status_pause_label = QLabel()
        self._status_version_label = QLabel()
        layout.addWidget(self._status_monitor_label)
        layout.addWidget(self._status_click_label)
        layout.addWidget(self._status_pause_label)
        layout.addStretch(1)
        layout.addWidget(self._status_version_label)

        self._status_container.addWidget(bar, 0)

        # ponytail: 連點燈初始 OFF；由 set_ahk_click_status 切換
        self._ahk_click_on = False
        self._refresh_status_bar()

    def _refresh_status_bar(self) -> None:
        if not hasattr(self, "_status_monitor_label"):
            return
        mon = self.is_monitoring()
        self._status_monitor_label.setText(f"● {self.get_text('status_monitoring')}：{self.get_text('status_running') if mon else self.get_text('status_stopped')}")
        self._status_monitor_label.setStyleSheet(f"color: {'#50fa7b' if mon else '#b8b8c8'};")

        click_on = self._ahk_click_on
        self._status_click_label.setText(f"● {self.get_text('status_clicking')}：{self.get_text('status_click_on') if click_on else self.get_text('status_click_off')}")
        self._status_click_label.setStyleSheet(f"color: {'#50fa7b' if click_on else '#b8b8c8'};")

        paused = self.is_global_pause()
        self._status_pause_label.setText(f"● {self.get_text('status_pause')}：{self.get_text('status_pause_on') if paused else self.get_text('status_pause_off')}")
        self._status_pause_label.setStyleSheet(f"color: {'#f1fa8c' if paused else '#b8b8c8'};")

        self._status_version_label.setText(f"{self.get_text('status_version')} v{__version__}")

    def set_ahk_click_status(self, on: bool) -> None:
        """連點(AHK)開關燈。由 AutoClickManager 呼叫（純 GUI 回呼，不改 AHK 行為）。"""
        self._ahk_click_on = bool(on)
        self._refresh_status_bar()

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(geo.center() - self.rect().center())

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange and self._initialized:
            if self.isMaximized():
                self._was_maximized = True
            elif self._was_maximized:
                self._was_maximized = False
                QTimer.singleShot(0, self._snap_to_restore_size)  # 等還原動畫結束再歸位

    def _snap_to_restore_size(self) -> None:
        """預設/還原尺寸：1600×900（小螢幕自動 clamp 到可用區）。"""
        w, h = RESTORE_SIZE
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            w = min(w, avail.width())
            h = min(h, avail.height())
        self.resize(w, h)

    def _shutdown(self) -> None:
        """關閉清理。"""
        self._usage_timer.stop()
        self._config_save_timer.stop()
        try:
            self._usage_tracker.stop()  # 計算本次使用時間並寫回 registry
        except Exception:
            pass
        for timer in self._pending_timers:
            timer.stop()
        self._pending_timers.clear()
        try:
            if hasattr(self, "combo_tab"):
                if self.combo_tab.is_combo_running():
                    self.combo_tab.stop_combo_system()
                if self.combo_tab.skill_timer:
                    self.combo_tab.skill_timer.stop_all()
        except Exception:
            pass
        try:
            if hasattr(self, "version_tab"):
                self.version_tab.shutdown_cleanup()
        except Exception:
            pass
        try:
            import keyboard

            keyboard.unhook_all()
        except Exception:
            pass
        try:
            self.auto_click_manager.stop_auto_click_ahk()
        except Exception:
            pass
        for timer in self._pending_timers:
            timer.stop()
        self._pending_timers.clear()
        try:
            from capture_utils import shutdown_background_capture

            shutdown_background_capture()
        except Exception:
            pass
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
        logger.info("應用程式運行時間: %s", runtime)

    def closeEvent(self, e):
        if self._is_closing:
            e.accept()
            return
        self._is_closing = True
        try:
            self._shutdown()
        except Exception as err:
            logger.error("關閉清理失敗: %s", err)
        e.accept()

"""Qt GUI 入口 — PySide6 + qfluentwidgets（取代 tkinter 版 GUI）。

Phase 2/3：Skeleton + StatusTab 已完成，其餘 tab 陸續移植。
業務邏輯模組（config_manager / language_system / monitor_analyzer / capture_utils …）全保留。

smoke 模式（`python src/app.py --smoke`）：背景 thread 連發 5 條訊息驗證 worker→signal→UI，
1s 後檢查 log 並關閉視窗，供 CI/打包驗證。
"""

import json
import os
import sys
import threading
import time
import traceback

from PySide6.QtCore import QPoint, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

from qfluentwidgets import Theme, setTheme

from _version import __version__
from qt.main_window import MainWindow
from utils import get_app_dir


def _find_splash_pixmap():
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "PoeSidTools.png"),
        os.path.join(os.getcwd(), "assets", "PoeSidTools.png"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return QPixmap(path)
    return QPixmap()


def _install_exception_hook():
    def hook(exc_type, exc_value, exc_tb):
        print(f"\n[ERROR] 未捕獲的異常: {exc_type.__name__}: {exc_value}")
        traceback.print_exception(exc_type, exc_value, exc_tb)
        try:
            from utils import emergency_exit_handler

            emergency_exit_handler()
        except Exception:
            os._exit(1)

    sys.excepthook = hook


def _smoke_thread_test(window: MainWindow) -> None:
    """背景 thread 連發訊息，驗證 StatusTab / MonitorTab 的 thread-safe signal 路徑。"""

    def emit():
        for i in range(5):
            window.add_status_message(f"smoke thread message {i}", "info" if i % 2 == 0 else "success")
        if hasattr(window, "monitor_tab"):
            window.monitor_tab.update_status("100%", "50%", "#ff0000", "none")

    threading.Thread(target=emit, daemon=True).start()


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv
    smoke = "--smoke" in argv

    app = QApplication(argv)
    app.setApplicationName("GameTools Health Monitor")
    app.setApplicationVersion(__version__)

    _install_exception_hook()
    setTheme(Theme.DARK)

    splash = QSplashScreen(_find_splash_pixmap())
    splash.show()
    app.processEvents()

    window = MainWindow()
    window.show()
    splash.finish(window)

    if smoke:
        _smoke_thread_test(window)

        def _verify_signal_path():
            n = len(window.status_tab.status_log)
            assert n >= 5, f"expected >=5 log entries, got {n}"
            print(f"SMOKE STATUS THREAD OK ({n} entries)")
            assert hasattr(window, "monitor_tab"), "monitor_tab missing"
            assert window.monitor_tab.health_label.text() == "100%", f"monitor signal path broken: {window.monitor_tab.health_label.text()!r}"
            print(f"SMOKE MONITOR TAB OK ({window.monitor_tab.settings_tree.rowCount()} triggers loaded)")

            # 遊戲視窗下拉：無重新整理按鈕，開啟前自動重掃；refresh 需訊號安全
            mt = window.monitor_tab
            assert not hasattr(mt, "refresh_windows_btn"), "refresh button should be removed"
            assert mt.window_combo.on_refresh.__func__ is mt.refresh_windows.__func__, "auto refresh not wired to popup open"
            mt.window_title = "__SMOKE_KEEP_WINDOW_TITLE__"
            mt.refresh_windows()
            assert mt.window_title == "__SMOKE_KEEP_WINDOW_TITLE__", "refresh_windows clobbered window_title"
            print("SMOKE WINDOW COMBO OK")

            # InventoryTab：grid offset 調整 → 標籤 + 格子位置重算
            assert hasattr(window, "inventory_tab"), "inventory_tab missing"
            it = window.inventory_tab
            start_x, start_y = it.grid_offset_x, it.grid_offset_y
            it.adjust_grid_offset(3, -2)
            assert (it.grid_offset_x, it.grid_offset_y) == (start_x + 3, start_y - 2), "grid offset adjust failed"
            assert it.offset_x_label.text() == str(start_x + 3) and it.offset_y_label.text() == str(start_y - 2), "offset label failed"
            it.reset_grid_offset()
            assert (it.grid_offset_x, it.grid_offset_y) == (0, 0), "reset offset failed"
            print(f"SMOKE INVENTORY TAB OK (region={'set' if it.inventory_region else 'none'}, slots={len(it.inventory_grid_positions)})")

            # InventoryTab：合成影像預覽渲染 + exclusion 點擊 toggle
            import numpy as np

            it.excluded_inventory_slots = set()
            img = np.full((50, 120, 3), 200, dtype=np.uint8)
            it.update_inventory_preview_with_items(img, [0, 59])
            assert it._preview_has_image, "preview render failed"
            assert it.occupied_slots_cache == {0, 59}, f"occupied slots wrong: {it.occupied_slots_cache}"
            meta = it._preview_meta
            assert meta is not None, "preview meta missing"
            cx = meta["canvas_x"] + meta["offset_x"] + int(5.5 * meta["cell_w"])
            cy = meta["canvas_y"] + meta["offset_y"] + int(0.5 * meta["cell_h"])
            it._on_preview_click(QPoint(cx, cy))
            assert 5 in it.excluded_inventory_slots, "exclusion toggle on failed"
            it._on_preview_click(QPoint(cx, cy))
            assert 5 not in it.excluded_inventory_slots, "exclusion toggle off failed"
            print(f"SMOKE INVENTORY PREVIEW OK (meta cell={meta['cell_w']}x{meta['cell_h']})")

            # InventoryTab Phase 5c：清包進度預覽渲染 + F3/F6 入口與 hotkey 註冊
            it.update_inventory_preview_with_progress(img, [0, 59], "smoke progress")
            assert it._preview_has_image, "progress preview render failed"
            assert callable(it.quick_clear_inventory) and callable(it.f6_pickup_items), "F3/F6 entry missing"
            assert callable(it.request_f3) and callable(it.request_f6), "F3/F6 signal entry missing"
            assert callable(window.setup_hotkeys), "setup_hotkeys missing"
            assert callable(window.should_keep_topmost), "should_keep_topmost missing"
            assert window.inventory_clear_interrupt is False, "inventory_clear_interrupt init failed"
            print("SMOKE INVENTORY 5C OK")

            # ComboTab Phase 6：3 套組 UI 接線 + 技能計時器
            assert hasattr(window, "combo_tab"), "combo_tab missing"
            ct = window.combo_tab
            assert len(ct.combo_sets) == 3 and len(ct.combo_enabled) == 3, "combo sets init failed"
            assert ct.combo_notebook.count() == 3, "combo notebook pages failed"
            assert len(ct.combo_ui_refs) == 3, "combo ui refs failed"
            refs0 = ct.combo_ui_refs[0]
            assert len(refs0["key_combos"]) == 5 and len(refs0["delay_entries"]) == 5 and len(refs0["stationary_checks"]) == 5, "combo skill rows failed"
            refs0["trigger_combo"].setCurrentText("R")
            assert ct.combo_sets[0]["trigger_key"] == "R", "trigger key binding failed"
            refs0["key_combos"][0].setCurrentText("W")
            assert ct.combo_sets[0]["combo_keys"][0] == "W", "combo key binding failed"
            refs0["stationary_checks"][0].setChecked(True)
            assert ct.combo_sets[0]["stationary_attacks"][0] is True, "stationary binding failed"
            refs0["enabled_check"].setChecked(True)
            assert ct.combo_enabled[0] is True, "enabled binding failed"
            assert hasattr(ct, "skill_timer"), "skill_timer missing"
            st = ct.skill_timer
            assert len(st.slots) == 4, "skill timer slots failed"
            assert len(st.get_config()) == 4, "skill timer get_config failed"
            assert st.slots[0].start() is False, "empty key start should fail"
            print("SMOKE COMBO TAB OK")

            # Phase 7：Help/About/Version tabs
            assert hasattr(window, "help_tab") and hasattr(window, "about_tab") and hasattr(window, "version_tab"), "phase7 tabs missing"
            assert window.help_tab._scroll is not None, "help scroll missing"
            assert window.about_tab.usage_time_label is not None, "about usage label missing"
            window.about_tab.refresh_usage_time()
            assert window.about_tab.usage_time_label.text(), "usage time refresh failed"
            vt = window.version_tab
            assert callable(vt.check_for_updates) and callable(vt.silent_version_check) and callable(vt.test_github_connection), "version entries missing"
            assert vt.latest_version_label is not None and vt.release_notes_text is not None, "version ui missing"
            assert vt.format_release_notes("## header\n- item\n**bold**") == "◆ header\n• item\nbold", "format_release_notes failed"
            print("SMOKE PHASE7 TABS OK")

            # Phase 9：刪 tk 後的熱鍵與自動點擊接線
            mw = window
            assert callable(mw.toggle_global_pause) and callable(mw.toggle_monitoring) and callable(mw.close_app), "hotkey handlers missing"
            assert hasattr(mw, "auto_click_manager"), "auto_click_manager missing"
            assert callable(mw.auto_click_manager.stop_auto_click_ahk), "auto_click_manager stop missing"
            assert callable(mw.inventory_tab.return_to_hideout), "return_to_hideout missing"
            assert callable(mw.setup_hotkeys), "setup_hotkeys missing"
            mw.toggle_global_pause()
            assert mw.is_global_pause() is True, "global pause toggle on failed"
            mw.toggle_global_pause()
            assert mw.is_global_pause() is False, "global pause toggle off failed"
            print("SMOKE PHASE9 HOTKEYS OK")

            # 即時儲存：改設定 → 等 debounce → config 檔已寫入新值（無需任何儲存按鈕）
            mw.health_threshold = 0.77
            mw.schedule_config_save()
            cfg_path = os.path.join(get_app_dir(), "health_monitor_config.json")
            deadline = time.time() + 3.0
            persisted = False
            while time.time() < deadline:
                QApplication.processEvents()
                time.sleep(0.05)
                if os.path.exists(cfg_path):
                    try:
                        with open(cfg_path, encoding="utf-8") as f:
                            persisted = json.load(f).get("health_threshold") == 0.77
                    except Exception:
                        pass
                if persisted:
                    break
            assert persisted, "autosave did not persist config"
            print("SMOKE AUTOSAVE OK")

            # 介面UI框選按鈕須已接上 InventoryTab 流程，不得再有「後續階段」阻攔 stub
            assert hasattr(window.monitor_tab, "_on_select_interface_ui"), "select_interface_ui button not wired"
            assert "_not_portable_yet" not in dir(window.monitor_tab), "migration stub still present"
            assert callable(window.inventory_tab.start_interface_ui_selection), "interface_ui selection missing"
            print("SMOKE INTERFACE_UI BUTTON OK")

            # 用不存在的視窗標題啟動監控，驗證迴圈啟動→執行→停止
            # （先 seed config，讓 start_monitoring 的 region/settings guard 通過，
            #   避免打包後的乾淨 config 環境下監控無法啟動）
            window.config["region"] = [0, 0, 50, 50]
            window.config["settings"] = [{"type": "HP", "percent": 60, "key": "1", "cooldown": 1500}]
            window.monitor_tab.window_title = "__SMOKE_NO_SUCH_WINDOW__"
            window.start_monitoring()
            assert window.is_monitoring() and window._monitor_thread is not None and window._monitor_thread.is_alive(), "monitor thread not running"
            QTimer.singleShot(1200, _verify_loop)

        def _verify_loop():
            assert window.monitor_tab.health_label.text() == "--", f"loop status update failed: {window.monitor_tab.health_label.text()!r}"
            window.stop_monitoring()
            assert not window.is_monitoring(), "monitoring should be stopped"
            print("SMOKE MONITOR LOOP OK")
            window.close()

        QTimer.singleShot(1000, _verify_signal_path)

    code = app.exec()
    print(f"APP EXIT {code}")
    return code


if __name__ == "__main__":
    sys.exit(main())

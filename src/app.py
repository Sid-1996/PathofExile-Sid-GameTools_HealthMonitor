"""Qt GUI 入口 — PySide6 + qfluentwidgets（取代 tkinter 版 GUI）。

Phase 2/3：Skeleton + StatusTab 已完成，其餘 tab 陸續移植。
業務邏輯模組（config_manager / language_system / monitor_analyzer / capture_utils …）全保留。

smoke 模式（`python src/app.py --smoke`）：背景 thread 連發 5 條訊息驗證 worker→signal→UI，
1s 後檢查 log 並關閉視窗，供 CI/打包驗證。
"""

import json
import logging
import os
import sys
import threading
import time
import traceback

from PySide6.QtCore import QPoint, QTimer
from PySide6.QtWidgets import QApplication

from qfluentwidgets import Theme, setTheme

from _version import __version__
from logging_setup import configure as configure_logging
from qt.main_window import MainWindow
from utils import emergency_exit_handler, get_user_data_dir

logger = logging.getLogger(__name__)


def _install_exception_hook():
    def hook(exc_type, exc_value, exc_tb):
        logger.error("未捕獲的異常: %s: %s", exc_type.__name__, exc_value)
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


def _wait_exit_pid_arg(timeout_s: float = 20.0) -> None:
    """啟動參數含 --wait-exit-pid=N 時，等該 PID 退出後才繼續（內建 relaunch，與 ocr-trigger 一致）"""
    keep: list[str] = []
    pid: int | None = None
    for a in sys.argv[1:]:
        if a.startswith("--wait-exit-pid="):
            try:
                pid = int(a.split("=", 1)[1])
            except ValueError:
                pid = None
        else:
            keep.append(a)
    sys.argv[1:] = keep
    if pid is None:
        return
    try:
        import ctypes

        SYNCHRONIZE = 0x00100000
        WAIT_TIMEOUT = 0x00000102
        k32 = ctypes.windll.kernel32
        h = k32.OpenProcess(SYNCHRONIZE, False, pid)
        if not h:
            return
        try:
            deadline = time.monotonic() + timeout_s
            while time.monotonic() < deadline:
                if k32.WaitForSingleObject(h, 500) != WAIT_TIMEOUT:
                    break
        finally:
            k32.CloseHandle(h)
    except Exception:
        pass


def _relaunch_detached(launch_args: list[str], cwd: str | None) -> bool:
    """分離程序重啟自己；新程序等本程序退出後才初始化"""
    import subprocess
    from pathlib import Path

    cmd = [sys.executable, *launch_args, f"--wait-exit-pid={os.getpid()}"]
    flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS  # type: ignore[attr-defined]
    breakaway = getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0x01000000)
    for extra in (breakaway, 0):
        try:
            subprocess.Popen(cmd, creationflags=flags | extra, close_fds=True, cwd=cwd)  # noqa: S603
            return True
        except OSError:
            continue
    return False


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv
    smoke = "--smoke" in argv

    # 內建 relaunch：帶 --wait-exit-pid=N 時先等舊程序退出（必須在 velopack 之前）
    _wait_exit_pid_arg(timeout_s=20.0)

    # 統一 logging 設定需在最先（任何 console 輸出前）執行；--debug / GTOOLS_LOG_LEVEL
    configure_logging()

    # 啟動前決定語系（在 QApplication 之前，與 ocr-trigger 一致：config 優先，缺省用系統語系）
    try:
        from language_system import detect_system_language, normalize_language_code, get_language_manager

        _cfg_path = os.path.join(get_user_data_dir(), "health_monitor_config.json")
        _detected = detect_system_language()
        try:
            with open(_cfg_path, encoding="utf-8") as _f:
                _cfg = json.load(_f)
            _lang = _cfg.get("language") or _detected
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            _lang = _detected
        get_language_manager().change_language(normalize_language_code(_lang))
    except Exception:
        pass

    # Velopack builder 必須在語系決定後、QApplication 前執行（安裝/更新 hook 可能重啟程序）；開發環境為 no-op
    try:
        import velopack

        velopack.App().run()
    except ImportError:
        logger.warning("velopack 未安裝，自動更新功能停用")
    except Exception as e:
        # ponytail: 開發/可攜環境 NotInstalled 屬正常，不以 ERROR 洗版
        if "NotInstalled" in type(e).__name__ or "not properly installed" in str(e).lower():
            logger.debug("velopack 未安裝環境，跳過更新 hook")
        else:
            logger.warning("velopack 啟動失敗: %s", e)

    app = QApplication(argv)
    app.setApplicationName("GameTools Health Monitor")
    app.setApplicationVersion(__version__)

    _install_exception_hook()
    setTheme(Theme.DARK)

    window = MainWindow()
    window.show()
    app.processEvents()  # 及早處理首次 paint，避免主視窗晚出

    if smoke:
        _smoke_thread_test(window)

        def _verify_signal_path():
            n = len(window.status_tab.status_log)
            assert n >= 5, f"expected >=5 log entries, got {n}"
            print(f"SMOKE STATUS THREAD OK ({n} entries)")
            assert hasattr(window, "monitor_tab"), "monitor_tab missing"
            assert window.monitor_tab.health_label.text() == "100%", f"monitor signal path broken: {window.monitor_tab.health_label.text()!r}"
            print(f"SMOKE MONITOR TAB OK ({window.monitor_tab.settings_tree.rowCount()} triggers loaded)")

            # 預覽 label 回饋循環防護：連續兩次 setPixmap 後尺寸必須穩定（不得逐漸放大）
            from PIL import Image as _PILImage

            _pv = window.monitor_tab
            _pv._set_preview_pixmap(_pv.preview_label, _PILImage.new("RGB", (100, 50), (255, 0, 0)))
            QApplication.processEvents()
            s1 = _pv.preview_label.size()
            _pv._set_preview_pixmap(_pv.preview_label, _PILImage.new("RGB", (100, 50), (255, 0, 0)))
            QApplication.processEvents()
            assert _pv.preview_label.size() == s1, f"preview label feedback loop: {s1} -> {_pv.preview_label.size()}"
            print(f"SMOKE PREVIEW STABLE OK (label {s1.width()}x{s1.height()})")

            # 遊戲視窗下拉：無重新整理按鈕，開啟前自動重掃；refresh 需訊號安全
            mt = window.monitor_tab
            assert not hasattr(mt, "refresh_windows_btn"), "refresh button should be removed"
            ref = getattr(mt.window_combo.on_refresh, "__func__", None)
            assert ref is getattr(mt.refresh_windows, "__func__", None), "auto refresh not wired to popup open"
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
            # 預覽 label 回饋循環防護：重複渲染後尺寸必須穩定
            s_before = it.inventory_preview_label.size()
            it.update_inventory_preview_with_items(img, [0, 59])
            QApplication.processEvents()
            assert it.inventory_preview_label.size() == s_before, f"inventory preview label feedback loop: {s_before} -> {it.inventory_preview_label.size()}"
            print(f"SMOKE INVENTORY PREVIEW STABLE OK (label {s_before.width()}x{s_before.height()})")
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
            # 清空槽位再測：smoke 跑在開發機真實 config 上，槽 0 可能已設鍵
            st.slots[0].key = ""
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

            # 最上方勾選框跨頁同步：撥監控頁 → 背包頁跟隨（測後還原原值）
            orig_top = mw.always_on_top
            mt.always_on_top_check.setChecked(not orig_top)
            assert mw.always_on_top == (not orig_top), "always-on-top flag not updated"
            assert it.always_on_top_check.isChecked() == (not orig_top), "always-on-top cross-tab sync failed"
            mt.always_on_top_check.setChecked(orig_top)
            assert it.always_on_top_check.isChecked() == orig_top, "always-on-top restore failed"
            print("SMOKE ALWAYS_ON_TOP SYNC OK")

            # 即時儲存：改設定 → 等 debounce → config 檔已寫入新值（無需任何儲存按鈕）
            mw.health_threshold = 0.77
            mw.schedule_config_save()
            cfg_path = os.path.join(get_user_data_dir(), "health_monitor_config.json")
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
            print("SMOKE MONITOR LOOP OK")
            # F10 marshal 路徑：模擬 keyboard 監聽執行緒 emit signal，由主執行緒 queued 處理
            assert window.is_monitoring(), "monitor should be running before F10 stop"
            threading.Thread(target=window.f10_request.emit, daemon=True).start()

            def _after_f10():
                assert not window.is_monitoring(), "f10_request did not stop monitoring on main thread"
                print("SMOKE F10 MARSHAL OK")
                window.close()

            QTimer.singleShot(200, _after_f10)

        QTimer.singleShot(1000, _verify_signal_path)

    code = app.exec()
    logger.info("APP EXIT %s", code)
    # closeEvent → _shutdown 已清理全部 Qt 資源；但第三方庫（keyboard/WGC/winrt）
    # 的非 daemon thread 可能讓 process 擱置、工作列圖示殘留。打包版實測確認會發生，
    # 故 event loop 結束後直接強制退出，確保 process 徹底清乾淨。
    os._exit(0 if code is None else code)
    return code


if __name__ == "__main__":
    sys.exit(main())

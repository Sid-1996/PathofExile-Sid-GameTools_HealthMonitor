"""Qt GUI 入口 — PySide6 + qfluentwidgets（取代 tkinter 版 GUI）。

Phase 2/3：Skeleton + StatusTab 已完成，其餘 tab 陸續移植。
業務邏輯模組（config_manager / language_system / monitor_analyzer / capture_utils …）全保留。

smoke 模式（`python src/app.py --smoke`）：背景 thread 連發 5 條訊息驗證 worker→signal→UI，
1s 後檢查 log 並關閉視窗，供 CI/打包驗證。
"""

import os
import sys
import threading
import traceback

from PySide6.QtCore import QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

from qfluentwidgets import Theme, setTheme

from _version import __version__
from qt.main_window import MainWindow


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

            # 用不存在的視窗標題啟動監控，驗證迴圈啟動→執行→停止
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

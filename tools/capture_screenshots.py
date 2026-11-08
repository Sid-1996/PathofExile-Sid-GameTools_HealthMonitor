"""GUI 截圖工具：offscreen 渲染全部 8 頁，存 PNG。

用法: python tools/capture_screenshots.py [--size 1600x900] [--out assets/screenshots]
不開 visible 視窗，跑完即自動退出。
"""

import argparse
import os
import sys
import time

# ponytail: offscreen 必須在 import Qt 前設
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)
# 讓 MainWindow 跳過 auto-click listener（與 app.py --smoke 同路徑）
if "--smoke" not in sys.argv:
    sys.argv.append("--smoke")

# ponytail: argparse 前先移走 --smoke，避免 unrecognized argument
sys.argv = [a for a in sys.argv if a != "--smoke"]

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from qfluentwidgets import Theme, setTheme

TABS = [
    ("monitor_tab", "01-health-monitor"),
    ("inventory_tab", "02-inventory"),
    ("combo_tab", "03-combo"),
    ("status_tab", "04-status"),
    ("help_tab", "05-help"),
    ("version_tab", "06-version"),
    ("about_tab", "07-about"),
    ("settings_tab", "08-settings"),
]


def switch_to(window, widget):
    for fn in ("switchTo", "switch_to"):
        if hasattr(window, fn):
            try:
                getattr(window, fn)(widget)
                return
            except Exception:
                pass
    try:
        window.stackedWidget.setCurrentWidget(widget)
    except Exception as e:
        print(f"switch failed: {e}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", default="1600x900")
    ap.add_argument("--out", default=os.path.join(ROOT, "assets", "screenshots"))
    args = ap.parse_args()
    # parse 完再把 --smoke 還回 argv，讓 MainWindow 跳過 auto-click
    if "--smoke" not in sys.argv:
        sys.argv.append("--smoke")
    w, h = (int(x) for x in args.size.lower().split("x"))
    os.makedirs(args.out, exist_ok=True)

    app = QApplication.instance() or QApplication([])
    app.setApplicationName("GameTools Health Monitor")
    setTheme(Theme.DARK)

    from qt.main_window import MainWindow

    window = MainWindow()
    window.resize(w, h)
    window.show()
    app.processEvents()

    # 讓 Status 頁有內容可截（沿用 smoke 的正常 log 格式）
    try:
        window.add_status_message("Screenshot demo: app started (auto capture)", "info")
        window.add_status_message("Health monitor ready", "success")
        app.processEvents()
    except Exception:
        pass

    for attr, name in TABS:
        tab = getattr(window, attr)
        switch_to(window, tab)
        tab.show()
        app.processEvents()
        time.sleep(0.4)
        app.processEvents()
        path = os.path.join(args.out, f"{name}.png")
        pixmap = window.grab()
        ok = pixmap.save(path, "PNG")
        print(f"{'OK ' if ok else 'FAIL'} {path}")
        if not ok:
            return 1
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())

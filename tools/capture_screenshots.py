"""GUI 截圖工具：渲染全部 8 頁，存 PNG（頁面本體）。

用法: python tools/capture_screenshots.py [--lang en] [--out assets/screenshots]
注意: 需用 QT_QPA_PLATFORM=windows 真實渲染；會閃出視窗。
截圖預設英文（README 首頁為英文），--lang 可改 zh-tw / zh-cn / en。
"""

import argparse
import os
import sys
import time

# ponytail: FluentWindow 半透明底層 + grab() 會抓出白色，必須用 windows 平台真渲染
os.environ.setdefault("QT_QPA_PLATFORM", "windows")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

# 讓 MainWindow 跳過 auto-click listener（與 app.py --smoke 同路徑）
if "--smoke" not in sys.argv:
    sys.argv.append("--smoke")
sys.argv = [a for a in sys.argv if a != "--smoke"]

from PySide6.QtCore import QPoint
from PySide6.QtGui import QPixmap
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
    ap.add_argument("--out", default=os.path.join(ROOT, "assets", "screenshots"))
    ap.add_argument("--lang", default="en")
    args = ap.parse_args()
    if "--smoke" not in sys.argv:
        sys.argv.append("--smoke")
    os.makedirs(args.out, exist_ok=True)

    app = QApplication.instance() or QApplication([])
    app.setApplicationName("GameTools Health Monitor")
    setTheme(Theme.DARK)

    from qt.main_window import MainWindow

    # ponytail: 截圖前把 config 語系覆寫成 args.lang，讓各 Tab 以該語系
    # 建置 UI；並阻擋 MainWindow 內部 load_config 覆回使用者檔，
    # 截完不回寫，絕不動使用者設定檔。
    try:
        from config_manager import get_config_manager

        _cm = get_config_manager()
        _cm.load_config()
        _orig_lang = _cm.config.get("language", "zh-tw")
        _cm.config["language"] = args.lang
        _orig_load = _cm.load_config
        _cm.load_config = lambda: None
        print(f"lang: {_orig_lang} -> {args.lang} (config in-memory only)")
    except Exception as e:
        print(f"lang override failed: {e}")

    window = MainWindow()
    window._reset_no_save = True  # 截圖期間禁止 autosave 落盤
    window.show()
    app.processEvents()
    time.sleep(1.5)
    app.processEvents()

    try:
        window.add_status_message("Screenshot demo: app started (auto capture)", "info")
        window.add_status_message("Health monitor ready", "success")
        app.processEvents()
    except Exception:
        pass

    for attr, name in TABS:
        tab = getattr(window, attr)
        switch_to(window, tab)
        app.processEvents()
        time.sleep(0.8)
        app.processEvents()
        path = os.path.join(args.out, f"{name}.png")
        # ponytail: 用 render() 而非 grab()：grab() 會把 CardWidget 等
        # Fluent 卡片的半透明底層合成成白色（設定頁白底 bug）
        pm = QPixmap(tab.size())
        tab.render(pm, QPoint(0, 0))
        ok = pm.save(path, "PNG")
        print(f"{'OK ' if ok else 'FAIL'} {path}")
        if not ok:
            return 1
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())

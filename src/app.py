"""Qt GUI 入口 — PySide6 + qfluentwidgets（取代 tkinter 版 GUI）。

Phase 2: Skeleton。FluentWindow 外殼 + 7 個 stub tab + 深色主題 + 啟動/關閉生命週期。
後續階段逐一移植各 tab（monitor / inventory / combo / status / help / version / about），
業務邏輯模組（config_manager / language_system / monitor_analyzer / capture_utils …）全保留。

smoke 模式（`python src/app.py --smoke`）：1.5s 後自動退出，供 CI/打包驗證。
"""

import os
import sys
import traceback
from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QSplashScreen, QVBoxLayout, QWidget

from qfluentwidgets import (
    FluentIcon,
    FluentWindow,
    NavigationItemPosition,
    Theme,
    setTheme,
    setThemeColor,
)

from _version import __version__
from config_manager import get_config_manager
from language_system import get_language_manager

# ── 主題常數（與舊 dracula 色系對齊）──────────────────────────
ACCENT = "#bd93f9"
MUTED = "#b8b8c8"

# ── 分頁清單：(language key, FluentIcon, 該 tab 未來涵蓋的功能說明) ──
TABS = [
    ("tab_health_monitor", FluentIcon.HEART, "血量/魔力偵測、觸發按鍵、即時預覽"),
    ("tab_inventory_clear", FluentIcon.SHOPPING_CART, "背包格分析、F3 清理、F6 拾取、排他格"),
    ("tab_skill_combo", FluentIcon.GAME, "技能連招編排與週期送鍵"),
    ("tab_status", FluentIcon.HISTORY, "事件 log、全域熱鍵與執行狀態"),
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
        self.config_manager = get_config_manager()
        self.config_manager.load_config()
        self.config = self.config_manager.config
        self.language_manager = get_language_manager()
        self.current_language = self.config.get("language", "zh-tw")
        self.language_manager.change_language(self.current_language)

        setThemeColor(ACCENT)
        self.setWindowTitle(self.get_text("window_title"))

        self._build_tabs()
        self.resize(1280, 800)
        self.setMinimumSize(1000, 700)
        self._center_on_screen()

    def get_text(self, key):
        try:
            return self.language_manager.get_text(key)
        except Exception:
            return f"[{key}]"

    def register_timer(self, timer: QTimer) -> None:
        """登記 QTimer，關閉時統一停止（後續階段使用）。"""
        self._pending_timers.append(timer)

    def _build_tabs(self) -> None:
        for key, icon, scope in TABS:
            tab = StubTab(self.get_text(key), scope)
            tab.setObjectName(key)
            self.addSubInterface(tab, icon, self.get_text(key), NavigationItemPosition.TOP)

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(geo.center() - self.rect().center())

    def _shutdown(self) -> None:
        """關閉清理。後續階段加入：usage_tracker、keyboard.unhook_all、背景 thread join、config 保存。"""
        for timer in self._pending_timers:
            timer.stop()
        self._pending_timers.clear()
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
        QTimer.singleShot(1500, window.close)

    code = app.exec()
    print(f"APP EXIT {code}")
    return code


if __name__ == "__main__":
    sys.exit(main())

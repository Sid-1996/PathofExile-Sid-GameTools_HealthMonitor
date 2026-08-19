"""MainWindow — PySide6 FluentWindow 主外殼。

7 個 navigation 分頁：本階段已移植 StatusTab，其餘為 stub。
逐一移植各 tab 時，把對應 stub 換成真實 QWidget 即可。
業務邏輯模組（config_manager / language_system / …）全保留。
"""

from datetime import datetime

from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import FluentIcon, FluentWindow, NavigationItemPosition, setThemeColor

from qt.status import StatusTab

# ── 主題常數（與舊 dracula 色系對齊）──
ACCENT = "#bd93f9"
MUTED = "#b8b8c8"

# ── 分頁清單：(language key, FluentIcon, 該 tab 未來涵蓋的功能說明) ──
# tab_status 已移植，不在此 stub 清單中。
STUB_TABS = [
    ("tab_health_monitor", FluentIcon.HEART, "血量/魔力偵測、觸發按鍵、即時預覽"),
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

        setThemeColor(ACCENT)
        self.setWindowTitle(self.get_text("window_title"))

        self._build_tabs()
        self.resize(1280, 800)
        self.setMinimumSize(1000, 700)
        self._center_on_screen()

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

    def _build_tabs(self) -> None:
        for key, icon, scope in STUB_TABS:
            tab = StubTab(self.get_text(key), scope)
            tab.setObjectName(key)
            self.addSubInterface(tab, icon, self.get_text(key), NavigationItemPosition.TOP)

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

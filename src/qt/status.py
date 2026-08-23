"""StatusTab（Qt 版）— 事件 log 分頁。

關鍵設計：`add_status_message` 透過 Qt signal 從任意 thread 發射，
queued connection 自動送到主執行緒更新 UI——這是取代 tk 版
`root.after(0, ...)` 的標準 Qt 模式，讓本 tab 可安全地被 monitor / inventory
等 worker thread呼叫。
"""

from datetime import datetime

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QApplication, QCheckBox, QHBoxLayout, QLabel, QPlainTextEdit, QVBoxLayout, QWidget

from qfluentwidgets import PushButton

# ── 訊息類型 → 前景著色（沿用 dracula 色系）──
COLORS = {
    "success": "#50fa7b",
    "warning": "#f1fa8c",
    "error": "#ff5555",
    "info": "#8be9fd",
    "hotkey": "#bd93f9",
    "monitor": "#00BCD4",
}
INFO = COLORS["info"]
MAX_LINES = 100


class _Signals(QObject):
    message_added = Signal(str, str)


class StatusTab(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app
        self.status_log: list[tuple[str, str, str]] = []
        self.last_status_message = ""
        self._signals = _Signals(self)
        self._signals.message_added.connect(self._append_message)

        self._build_ui()
        self.add_status_message(self._app.get_text("tool_started_successfully"), "success")

    # ── UI ──────────────────────────────────────────────
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        self.title_label = QLabel(self._app.get_text("tool_execution_status"))
        self.title_label.setStyleSheet("font-size: 20px; font-weight: 600; color: #f8f8f2;")
        layout.addWidget(self.title_label)

        control = QHBoxLayout()
        self.clear_btn = PushButton(self._app.get_text("clear_records"))
        self.clear_btn.setToolTip(self._app.get_text("clear_records_tip"))
        self.clear_btn.clicked.connect(self.clear_status_log)
        control.addWidget(self.clear_btn)

        self.auto_scroll_cb = QCheckBox(self._app.get_text("auto_scroll_to_latest"))
        self.auto_scroll_cb.setToolTip(self._app.get_text("auto_scroll_tip"))
        self.auto_scroll_cb.setChecked(True)
        control.addWidget(self.auto_scroll_cb)

        control.addStretch(1)

        self.count_label = QLabel(self._app.get_text("total_records").format(count=0))
        self.count_label.setStyleSheet("color: #b8b8c8;")
        control.addWidget(self.count_label)
        layout.addLayout(control)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        mono = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.text_edit.setFont(mono)
        pal = self.text_edit.palette()
        pal.setColor(QPalette.ColorRole.Base, QApplication.palette().color(QPalette.ColorRole.Base))
        pal.setColor(QPalette.ColorRole.Text, QApplication.palette().color(QPalette.ColorRole.Text))
        self.text_edit.setPalette(pal)
        self.text_edit.setStyleSheet("border: none;")
        layout.addWidget(self.text_edit, 1)

    # ── 公開 API（thread-safe）──────────────────────────
    def add_status_message(self, message: str, msg_type: str = "info") -> None:
        """從任意 thread 呼叫皆安全；signal 會 queued 到主執行緒。"""
        if self._app._is_closing:
            return
        self._signals.message_added.emit(message, msg_type)

    def clear_status_log(self) -> None:
        self.status_log.clear()
        self.last_status_message = ""
        self.text_edit.clear()
        self._update_status_count()
        self.add_status_message(self._app.get_text("records_cleared"), "info")

    # ── private（主執行緒）──────────────────────────────
    def _append_message(self, message: str, msg_type: str) -> None:
        if self._app._is_closing:
            return
        if message == self.last_status_message:
            return
        self.last_status_message = message

        now = datetime.now().strftime("%H:%M:%S")
        self.status_log.append((now, message, msg_type))
        if len(self.status_log) > MAX_LINES:
            self.status_log = self.status_log[-MAX_LINES:]
            self._refresh_status_display()
            return

        self._insert_line(f"[{now}] {message}", COLORS.get(msg_type, INFO))
        self._scroll_to_bottom_if_needed()
        self._update_status_count()

    def _insert_line(self, text: str, color: str) -> None:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.text_edit.setTextCursor(cursor)
        cursor.insertText(text + "\n", fmt)

    def _refresh_status_display(self) -> None:
        self.text_edit.clear()
        for now, message, mtype in self.status_log:
            self._insert_line(f"[{now}] {message}", COLORS.get(mtype, INFO))
        self._scroll_to_bottom_if_needed()
        self._update_status_count()

    def _scroll_to_bottom_if_needed(self) -> None:
        if self.auto_scroll_cb.isChecked():
            sb = self.text_edit.verticalScrollBar()
            sb.setValue(sb.maximum())

    def update_status_tab_language(self) -> None:
        self.title_label.setText(self._app.get_text("tool_execution_status"))
        self.clear_btn.setText(self._app.get_text("clear_records"))
        self.clear_btn.setToolTip(self._app.get_text("clear_records_tip"))
        self.auto_scroll_cb.setText(self._app.get_text("auto_scroll_to_latest"))
        self.auto_scroll_cb.setToolTip(self._app.get_text("auto_scroll_tip"))
        self._update_status_count()

    def _update_status_count(self) -> None:
        self.count_label.setText(self._app.get_text("total_records").format(count=len(self.status_log)))

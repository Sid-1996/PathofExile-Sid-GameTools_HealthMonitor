"""StatusTab（Qt 版）— 事件 log 分頁。

關鍵設計：`add_status_message` 透過 Qt signal 從任意 thread 發射，
queued connection 自動送到主執行緒更新 UI——這是取代 tk 版
`root.after(0, ...)` 的標準 Qt 模式，讓本 tab 可安全地被 monitor / inventory
等 worker thread呼叫。
"""

from datetime import datetime

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QPlainTextEdit, QVBoxLayout, QWidget

from qfluentwidgets import PushButton

from qt.theme import current_tokens

# ── 訊息類型 → 主題 token（顏色唯一來源是 qt.theme；沿用 Dracula 主組語意色）──
_MESSAGE_TOKENS = {
    "success": "success",
    "warning": "warning",
    "error": "error",
    "info": "info",
    "hotkey": "accent",
    "monitor": "monitor",
}
MAX_LINES = 100


def _message_color(msg_type: str) -> str:
    """訊息類型 → 目前主題顏色；未知類型回退 info（與遷移前行為一致）。"""
    return current_tokens()[_MESSAGE_TOKENS.get(msg_type, "info")]


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
        self.title_label.setStyleSheet(self._title_qss())
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
        self.count_label.setStyleSheet(self._count_qss())
        control.addWidget(self.count_label)
        layout.addLayout(control)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        mono = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.text_edit.setFont(mono)
        # ponytail: 只上 border: none（沿用原樣式）；不指定 background，日誌區因此透明、
        # 跟著主題頁底（FluentWindow 的 dark/light 底色），文字色由每行 QTextCharFormat 決定。
        self.text_edit.setStyleSheet("border: none;")
        layout.addWidget(self.text_edit, 1)

    # ── 主題（顏色一律取自 qt.theme token）────────────────
    @staticmethod
    def _title_qss() -> str:
        return f"font-size: 20px; font-weight: 600; color: {current_tokens()['fg']};"

    @staticmethod
    def _count_qss() -> str:
        return f"color: {current_tokens()['fg_muted']};"

    def refresh_theme(self) -> None:
        """主題切換刷新（MainWindow._fan_out_tab_themes 呼叫）。

        只重上顏色：不動日誌內容、捲動位置、計數、自動捲動勾選等狀態；重複呼叫不累積 QSS。
        """
        if hasattr(self, "title_label"):
            self.title_label.setStyleSheet(self._title_qss())
        if hasattr(self, "count_label"):
            self.count_label.setStyleSheet(self._count_qss())
        self._apply_log_colors()

    def _apply_log_colors(self) -> None:
        """把既有日誌行的前景色換成目前主題顏色。

        不重寫文字、不清空、不動捲動位置（逐 block 只 merge 前景色）。
        這是必要的：日誌色是逐字元格式，不重上就會在 light 主題殘留深色主題的淺色字。
        """
        if not self.status_log or not hasattr(self, "text_edit"):
            return
        doc = self.text_edit.document()
        cursor = QTextCursor(doc)
        block = doc.begin()
        index = 0
        while block.isValid() and index < len(self.status_log):
            start = block.position()
            end = start + max(block.length() - 1, 0)
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(_message_color(self.status_log[index][2])))
            cursor.mergeCharFormat(fmt)
            block = block.next()
            index += 1

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

        self._insert_line(f"[{now}] {message}", _message_color(msg_type))
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
            self._insert_line(f"[{now}] {message}", _message_color(mtype))
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

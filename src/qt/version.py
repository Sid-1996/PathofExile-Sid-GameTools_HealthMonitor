"""
version.py（Qt 版）— 版本檢查分頁
────────────────────────────────────────────────────────
對應 tk 版 `tab_version.py`（Phase 7）。
- 更新檢查/下載/套用走 Velopack（auto_update.py，GitHub Releases 為源）；
  release notes 僅在查看時從 GitHub API 取。
- 所有背景 thread 的 UI 更新一律走 `_VersionSignals`（thread-safe queued signal）。
- 下載進度用 modal QDialog + QProgressBar；更新通知用 QDialog。
"""

import os
import re
import sys
import threading

import requests
from PySide6.QtCore import Qt, QObject, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import PrimaryPushButton, PushButton

import auto_update
from _version import __version__

CURRENT_VERSION = f"v{__version__}"
GITHUB_REPO = "Sid-1996/PathofExile-Sid-GameTools_HealthMonitor"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

SUCCESS = "#50fa7b"
ERROR = "#ff5555"
INFO = "#8be9fd"
MUTED = "#b8b8c8"
FG = "#f8f8f2"


class _VersionSignals(QObject):
    """背景 thread → 主執行緒的 thread-safe 更新通道。"""

    version_checked = Signal(object)  # auto_update.InfoShim | None
    error_shown = Signal(str, str, str)  # version_key, status_key, error
    status_text = Signal(str)  # 設定狀態列文字
    latest_text = Signal(str)  # 設定最新版本文字
    release_notes = Signal(str)
    download_progress = Signal(float, float)  # downloaded, total
    download_done = Signal(object, object)  # (None 佔位, InfoShim)
    download_fail = Signal(str)


class VersionTab(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app

        self._updating = False
        self._downloading = False
        self._silent_mode = False
        self._pending_update_info = None
        self._update_manager = None
        self._notification_dialog = None
        self._progress_dialog = None

        self._sig = _VersionSignals()
        self._sig.version_checked.connect(self._on_version_checked)
        self._sig.error_shown.connect(self._show_check_error)
        self._sig.status_text.connect(lambda t: self.version_status_label.setText(t))
        self._sig.latest_text.connect(lambda t: self.latest_version_label.setText(t))
        self._sig.release_notes.connect(self._update_release_notes_display)
        self._sig.download_progress.connect(self._on_progress)
        self._sig.download_done.connect(self._on_download_finished)
        self._sig.download_fail.connect(self._on_download_error)

        self._build_ui()

        if "--smoke" not in sys.argv:
            QTimer.singleShot(2000, self.silent_version_check)

    # ────────────────────────────────────────────────────
    #  UI 建構
    # ────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        g = self._app.get_text

        title_label = QLabel(g("version_check_title"))
        title_label.setStyleSheet(f"font-size: 20px; font-weight: 600; color: {FG};")
        layout.addWidget(title_label)

        # ── 目前版本 ──
        current_card, current_layout = self._card(g("current_version_info"))
        current_title = QLabel(g("current_version_label"))
        current_title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {FG};")
        current_layout.addWidget(current_title)
        current_version_label = QLabel(CURRENT_VERSION)
        current_version_label.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {INFO};")
        current_layout.addWidget(current_version_label)
        layout.addWidget(current_card)

        # ── 最新版本 ──
        remote_card, remote_layout = self._card(g("latest_version_info"))
        latest_title = QLabel(g("latest_version_label"))
        latest_title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {FG};")
        remote_layout.addWidget(latest_title)
        self.latest_version_label = QLabel(g("checking_version"))
        self.latest_version_label.setStyleSheet(self._latest_style(SUCCESS))
        remote_layout.addWidget(self.latest_version_label)
        self.version_status_label = QLabel(g("checking_version_status"))
        self.version_status_label.setStyleSheet(f"font-size: 12px; color: {FG};")
        self.version_status_label.setWordWrap(True)
        remote_layout.addWidget(self.version_status_label)

        notes_title = QLabel(g("update_notes_label"))
        notes_title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {FG};")
        remote_layout.addWidget(notes_title)
        self.release_notes_text = QPlainTextEdit()
        self.release_notes_text.setReadOnly(True)
        self.release_notes_text.setMaximumHeight(140)
        self.release_notes_text.setStyleSheet(f"QPlainTextEdit {{ background-color: #1e1e2e; border: 1px solid #3b3b3b; border-radius: 6px; color: {MUTED}; font-size: 12px; }}")
        self.release_notes_text.setPlainText(g("loading_text"))
        remote_layout.addWidget(self.release_notes_text)
        layout.addWidget(remote_card)

        # ── 按鈕列 ──
        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        self.check_update_btn = PushButton(g("check_update_button"))
        self.check_update_btn.setToolTip(g("check_update_button_tip"))
        self.check_update_btn.clicked.connect(self.check_for_updates)
        button_row.addWidget(self.check_update_btn)
        self.download_btn = PrimaryPushButton(g("download_update_button"))
        self.download_btn.setEnabled(False)
        self.download_btn.setToolTip(g("download_update_tip"))
        self.download_btn.clicked.connect(self._on_download_click)
        button_row.addWidget(self.download_btn)
        self.test_connection_btn = PushButton(g("test_connection_button"))
        self.test_connection_btn.setToolTip(g("test_connection_button_tip"))
        self.test_connection_btn.clicked.connect(self.test_github_connection)
        button_row.addWidget(self.test_connection_btn)
        button_row.addStretch(1)
        layout.addLayout(button_row)
        layout.addStretch(1)

    def _card(self, title):
        box = QWidget()
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(16, 16, 16, 16)
        box_layout.setSpacing(6)
        box.setStyleSheet("QWidget { background-color: #1e1e2e; border: 1px solid #3b3b3b; border-radius: 8px; }QLabel { background: transparent; }")
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {FG}; background: transparent;")
        box_layout.addWidget(title_label)
        return box, box_layout

    @staticmethod
    def _latest_style(color):
        return f"font-size: 16px; font-weight: 700; color: {color};"

    def _allow_prerelease(self) -> bool:
        return bool(self._app.config.get("allow_prerelease", False))

    # ────────────────────────────────────────────────────
    #  版本檢查
    # ────────────────────────────────────────────────────

    def check_for_updates(self):
        if self._updating:
            return
        self._updating = True
        self.latest_version_label.setText(self._app.get_text("checking_version"))
        self.version_status_label.setText(self._app.get_text("connecting_github"))
        self._run_check(silent=False)

    def silent_version_check(self):
        if self._app._is_closing:
            return
        self._run_check(silent=True)

    def _run_check(self, silent: bool):
        self._silent_mode = silent

        def _check():
            try:
                channel = "beta" if self._allow_prerelease() else None
                manager = auto_update.create_manager(channel)
                self._update_manager = manager
                info = auto_update.check_for_update(manager)
                self._sig.version_checked.emit(info)
            except requests.exceptions.Timeout:
                self._sig.error_shown.emit("connection_timeout", "github_timeout", "")
            except requests.exceptions.ConnectionError:
                self._sig.error_shown.emit("connection_failed", "github_connection_failed", "")
            except Exception as e:
                self._sig.error_shown.emit("check_error", "check_error_with_message", str(e))
            finally:
                self._updating = False

        threading.Thread(target=_check, daemon=True).start()

    def _on_version_checked(self, info):
        if info is None:
            self.latest_version_label.setText(self._app.get_text("using_latest_version"))
            self.latest_version_label.setStyleSheet(self._latest_style(SUCCESS))
            self.version_status_label.setText(self._app.get_text("using_latest_version"))
            self.download_btn.setEnabled(False)
            return
        skipped = self._app.config.get("skipped_version", "")
        if skipped == f"v{info.version}":
            return
        self.latest_version_label.setText(f"v{info.version}")
        self.latest_version_label.setStyleSheet(self._latest_style(ERROR))
        self.version_status_label.setText(self._app.get_text("new_version_found"))
        self.download_btn.setEnabled(True)
        self._pending_update_info = info
        self._fetch_release_notes(info.version)
        if self._silent_mode:
            self._show_update_notification(info)

    def _show_check_error(self, version_key, status_key, error):
        self.latest_version_label.setText(self._app.get_text(version_key))
        self.latest_version_label.setStyleSheet(self._latest_style(ERROR))
        msg = self._app.get_text(status_key)
        if error:
            msg = msg.format(error=error)
        self.version_status_label.setText(msg)

    def _fetch_release_notes(self, version_tag):
        """從 GitHub API 取 release notes（僅在有新版時觸發）"""

        def _fetch():
            try:
                resp = requests.get(GITHUB_API_URL, timeout=10)
                if resp.status_code == 200:
                    body = resp.json().get("body", "")
                    if body:
                        self._sig.release_notes.emit(body)
            except Exception:
                pass

        threading.Thread(target=_fetch, daemon=True).start()

    def test_github_connection(self):
        def _test():
            try:
                self._sig.status_text.emit(self._app.get_text("testing_connection"))
                response = requests.get("https://api.github.com", timeout=5)
                if response.status_code == 200:
                    self._sig.status_text.emit(self._app.get_text("github_connection_ok"))
                else:
                    self._sig.status_text.emit(self._app.get_text("github_connection_warning").format(status_code=response.status_code))
            except Exception as e:
                self._sig.status_text.emit(self._app.get_text("connection_test_failed").format(error=str(e)))

        threading.Thread(target=_test, daemon=True).start()

    # ────────────────────────────────────────────────────
    #  下載更新
    # ────────────────────────────────────────────────────

    def _on_download_click(self):
        if self._downloading or self._pending_update_info is None:
            return
        if self._update_manager is None:
            QMessageBox.warning(self, self._app.get_text("warning"), self._app.get_text("updater_source_mode_warning"))
            return
        self._start_download(self._pending_update_info)

    def _start_download(self, info):
        if self._app._is_closing:
            return
        self._downloading = True
        self.download_btn.setEnabled(False)
        self.check_update_btn.setEnabled(False)

        dialog = QDialog(self)
        dialog.setWindowTitle(self._app.get_text("downloading_update"))
        dialog.setFixedSize(440, 150)
        dialog.setModal(True)
        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(16, 16, 16, 16)
        dialog_layout.setSpacing(8)
        dialog_title = QLabel(self._app.get_text("downloading_update").format(version=f"v{info.version}"))
        dialog_title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {FG};")
        dialog_layout.addWidget(dialog_title, 0, Qt.AlignmentFlag.AlignCenter)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        dialog_layout.addWidget(self._progress_bar)
        self._progress_status_label = QLabel("0 KB / ? KB")
        self._progress_status_label.setStyleSheet("font-family: Consolas; font-size: 11px; color: #f8f8f2;")
        dialog_layout.addWidget(self._progress_status_label, 0, Qt.AlignmentFlag.AlignCenter)
        # Velopack 下載不支援中途取消（delta 傳輸量小、速度快），不提供取消按鈕
        self._progress_dialog = dialog

        def _progress_cb(downloaded, total):
            self._sig.download_progress.emit(downloaded, total)

        def _do_download():
            try:
                auto_update.download_update(self._update_manager, info, progress_cb=_progress_cb)
                self._sig.download_done.emit(None, info)
            except Exception as e:
                self._sig.download_fail.emit(self._translate_error(e))

        threading.Thread(target=_do_download, daemon=True).start()
        dialog.exec()

    def _on_progress(self, downloaded, total):
        if total > 0:
            pct = downloaded / total * 100
            self._progress_bar.setValue(int(pct))
            self._progress_status_label.setText(f"{downloaded / 1024:.0f} KB / {total / 1024:.0f} KB ({pct:.0f}%)")
        else:
            self._progress_status_label.setText(f"{downloaded / 1024:.0f} KB")

    def _close_progress_dialog(self):
        if self._progress_dialog is not None:
            self._progress_dialog.accept()
            self._progress_dialog = None

    def _on_download_error(self, error_msg):
        if self._app._is_closing:
            return
        self._downloading = False
        self.download_btn.setEnabled(True)
        self.check_update_btn.setEnabled(True)
        self._close_progress_dialog()
        QMessageBox.critical(self, self._app.get_text("error"), self._app.get_text("apply_update_failed").format(error=error_msg))

    def _on_download_finished(self, _none, info):
        if self._app._is_closing:
            return
        self._downloading = False
        self.download_btn.setEnabled(False)
        self.check_update_btn.setEnabled(True)
        self._close_progress_dialog()

        result = QMessageBox.question(
            self,
            self._app.get_text("download_complete"),
            self._app.get_text("restart_to_apply").format(current=CURRENT_VERSION, latest=f"v{info.version}"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            try:
                self._app.config["just_updated"] = info.version
                self._app.save_config()
                # 套用後由 Velopack 接管重啟（與舊 updater.exe+os._exit 等價的立即離開）；
                # 若使用者選 No，已下載的更新會在下次啟動時由 velopack 自動套用。
                auto_update.apply_and_restart(self._update_manager, info)
                os._exit(0)  # 防護：正常情況 apply 內部不會返回
            except Exception as e:
                QMessageBox.critical(self, self._app.get_text("error"), self._app.get_text("apply_update_failed").format(error=self._translate_error(e)))

    def _translate_error(self, e):
        """將 auto_update 拋出的語言 key 錯誤翻譯為使用者可見訊息。"""
        if isinstance(e, auto_update.AutoUpdateError):
            return self._app.get_text(e.key).format(**e.params)
        return str(e)

    # ────────────────────────────────────────────────────
    #  Release Notes 格式化
    # ────────────────────────────────────────────────────

    def format_release_notes(self, markdown_text):
        if not markdown_text or markdown_text == self._app.get_text("no_update_notes"):
            return self._app.get_text("no_update_notes")

        text = re.sub(r"```[\s\S]*?```", "", markdown_text)
        text = re.sub(r"^### (.*)$", r"● \1", text, flags=re.MULTILINE)
        text = re.sub(r"^## (.*)$", r"◆ \1", text, flags=re.MULTILINE)
        text = re.sub(r"^# (.*)$", r"■ \1", text, flags=re.MULTILINE)
        text = re.sub(r"^\* (.*)$", r"• \1", text, flags=re.MULTILINE)
        text = re.sub(r"^- (.*)$", r"• \1", text, flags=re.MULTILINE)
        text = re.sub(r"^\d+\. (.*)$", r"➤ \1", text, flags=re.MULTILINE)
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        text = re.sub(r"\*\*([^\*]+)\*\*", r"\1", text)
        text = re.sub(r"\*([^\*]+)\*", r"\1", text)
        text = re.sub(r"_([^_]+)_", r"\1", text)
        text = re.sub(r"\n\s*\n\s*\n", "\n\n", text)
        if len(text) > 800:
            text = text[:800] + "..."
        return text.strip()

    def _update_release_notes_display(self, release_body):
        if self.release_notes_text is not None:
            self.release_notes_text.setPlainText(self.format_release_notes(release_body))

    # ────────────────────────────────────────────────────
    #  更新通知對話框
    # ────────────────────────────────────────────────────

    def _show_update_notification(self, info):
        if self._app._is_closing:
            return
        if self._notification_dialog is not None:
            self._notification_dialog.raise_()
            return

        dialog = QDialog(self)
        self._notification_dialog = dialog
        dialog.setWindowTitle(self._app.get_text("new_version_found_title"))
        dialog.setMinimumWidth(480)
        dialog.setModal(True)
        g = self._app.get_text

        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(20, 20, 20, 20)
        dialog_layout.setSpacing(10)

        big_title = QLabel(g("new_version_found_title_2"))
        big_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        big_title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {SUCCESS};")
        dialog_layout.addWidget(big_title)

        info_card = QWidget()
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(16, 16, 16, 16)
        info_layout.setSpacing(6)
        info_card.setStyleSheet("QWidget { background-color: #1e1e2e; border: 1px solid #3b3b3b; border-radius: 8px; }QLabel { background: transparent; }")
        current_label = QLabel(g("current_version_display").format(version=CURRENT_VERSION))
        current_label.setStyleSheet("font-size: 12px; color: #f8f8f2; background: transparent;")
        info_layout.addWidget(current_label)
        latest_label = QLabel(g("latest_version_display").format(version=f"v{info.version}"))
        latest_label.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {ERROR}; background: transparent;")
        info_layout.addWidget(latest_label)
        dialog_layout.addWidget(info_card)

        skip_check = QCheckBox(g("skip_this_version"))
        dialog_layout.addWidget(skip_check)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        download_now_btn = PrimaryPushButton(g("download_now_button"))
        view_details_btn = PushButton(g("view_details_button"))
        remind_later_btn = PushButton(g("remind_later_button"))
        button_row.addWidget(download_now_btn)
        button_row.addWidget(view_details_btn)
        button_row.addStretch(1)
        button_row.addWidget(remind_later_btn)
        dialog_layout.addLayout(button_row)

        def on_close():
            self._notification_dialog = None
            if skip_check.isChecked():
                self._app.config["skipped_version"] = f"v{info.version}"
                self._app.save_config()
            dialog.accept()

        def start_download():
            on_close()
            self._pending_update_info = info
            self._start_download(info)

        def view_details():
            on_close()
            self._app.switchTo(self)
            self._pending_update_info = info
            self._fetch_release_notes(info.version)

        download_now_btn.clicked.connect(start_download)
        view_details_btn.clicked.connect(view_details)
        remind_later_btn.clicked.connect(on_close)
        dialog.exec()

    def shutdown_cleanup(self):
        """關閉時關掉通知視窗（Velopack 下載無法取消，背景 thread 為 daemon 隨程序結束）。"""
        if self._notification_dialog is not None:
            try:
                self._notification_dialog.reject()
            except Exception:
                pass
            self._notification_dialog = None

    # ── 語言更新（整頁重建）──────────────────────────

    def update_language(self):
        # 沿用 tk 行為：重建整個分頁 UI（保留執行狀態旗標）
        self._build_ui()
        if self._downloading:
            self.download_btn.setEnabled(False)
            self.check_update_btn.setEnabled(False)

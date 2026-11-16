"""startup_diagnostics 測試：日誌路徑選擇、frozen 差異、traceback 保留、提示去重與降級。

全部以 tmp_path + monkeypatch 隔離檔案系統；另外保存/還原 sys.excepthook、
threading.excepthook 與 root logger handlers，避免污染其他測試。
"""

import logging
import os
import sys
import tempfile
import threading
import traceback

import pytest

import startup_diagnostics as sd


@pytest.fixture
def diag(tmp_path, monkeypatch):
    """隔離環境：LOCALAPPDATA 指到 tmp、非 frozen、乾淨的冪等狀態；結束後還原全域狀態。"""
    root = logging.getLogger()
    orig_level = root.level
    orig_handlers = list(root.handlers)
    orig_excepthook = sys.excepthook
    orig_thread_hook = threading.excepthook
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.delenv("GTOOLS_LOG_LEVEL", raising=False)
    sd.reset_for_tests()
    try:
        yield sd
    finally:
        sd.reset_for_tests()
        root.handlers[:] = orig_handlers
        root.setLevel(orig_level)
        sys.excepthook = orig_excepthook
        threading.excepthook = orig_thread_hook


def test_log_dir_uses_localappdata_and_ignores_cwd(diag, tmp_path, monkeypatch):
    expected = tmp_path / "LocalAppData" / "GameTools_HealthMonitor"
    assert diag.log_dir() == str(expected)
    assert diag.log_path() == str(expected / "gtools.log")

    other = tmp_path / "cwd_elsewhere"
    other.mkdir()
    monkeypatch.chdir(other)
    assert diag.log_dir() == str(expected), "日誌路徑不得依賴目前工作目錄"


def test_log_dir_falls_back_to_exe_dir_when_frozen_and_localappdata_unwritable(diag, tmp_path, monkeypatch):
    exe_dir = tmp_path / "installed"
    exe_dir.mkdir()
    # 用「父層是檔案」讓 makedirs 必然失敗，模擬不可寫的 LOCALAPPDATA
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setenv("LOCALAPPDATA", str(blocker / "LocalAppData"))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_dir / "app.exe"))

    assert diag.log_dir() == str(exe_dir)


def test_log_dir_skips_exe_dir_when_not_frozen(diag, tmp_path, monkeypatch):
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setenv("LOCALAPPDATA", str(blocker / "LocalAppData"))
    monkeypatch.setattr(sys, "executable", str(tmp_path / "python.exe"))

    # 非 frozen 不應把日誌寫到 sys.executable 所在目錄（開發機那是 Python 安裝目錄）
    result = diag.log_dir()
    assert result == os.path.join(tempfile.gettempdir(), "GameTools_HealthMonitor")
    assert str(tmp_path) not in result


def test_configure_root_logging_always_adds_file_handler_and_is_idempotent(diag):
    handler = diag.configure_root_logging(logging.WARNING)
    assert handler is not None
    assert diag.log_path().endswith("gtools.log")

    diag.logger.error("診斷測試訊息 abc123")
    body = open(diag.log_path(), encoding="utf-8").read()
    assert "診斷測試訊息 abc123" in body, "正常啟動（WARNING）時錯誤必須落地"

    again = diag.configure_root_logging(logging.WARNING)
    assert again is handler, "重複呼叫應冪等"
    tagged = [h for h in logging.getLogger().handlers if getattr(h, "_gtools_diagnostics", False)]
    assert len(tagged) == 2, f"應只有一組 handler（file+stream），實際 {tagged}"


def test_configure_root_logging_keeps_logging_without_console(diag, monkeypatch):
    """打包版 --noconsole：stdout / stderr 皆為 None，仍必須留下檔案日誌。"""
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    assert diag.configure_root_logging(logging.WARNING) is not None
    diag.logger.error("無 console 仍須落檔 msg-7788")
    assert "無 console 仍須落檔 msg-7788" in open(diag.log_path(), encoding="utf-8").read()
    tagged = [h for h in logging.getLogger().handlers if getattr(h, "_gtools_diagnostics", False)]
    assert len(tagged) == 1, f"無 console 時只應有檔案 handler，實際 {tagged}"


def test_configure_root_logging_never_raises_when_log_dir_unusable(diag, monkeypatch, tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setenv("LOCALAPPDATA", str(blocker / "LocalAppData"))
    # 讓所有候選目錄都不可寫（含 TEMP 降級）→ 不得外拋，只是沒有 handler
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(blocker / "Temp"))

    assert diag.configure_root_logging(logging.WARNING) is None
    diag.logger.error("沒有 handler 也不能爆")  # 不得拋例外


def test_bootstrap_swallows_diagnostics_failures(diag, monkeypatch):
    def boom(*a, **k):
        raise OSError("boom")

    monkeypatch.setattr(diag, "configure_root_logging", boom)
    diag.bootstrap()  # 診斷失敗不得擋啟動
    assert sys.excepthook is diag._sys_excepthook


def test_write_crash_preserves_full_traceback(diag):
    def explode():
        raise ValueError("crash-marker-xyz")

    try:
        explode()
    except ValueError:
        exc_info = sys.exc_info()

    path = diag.write_crash("測試", "".join(traceback.format_exception(*exc_info)))
    assert path is not None
    body = open(path, encoding="utf-8").read()
    assert "Traceback (most recent call last)" in body
    assert "crash-marker-xyz" in body
    assert "in explode" in body, "traceback 必須包含失敗函式"
    assert "frozen=" in body and "argv=" in body


def test_report_uncaught_logs_traceback_prompts_once_and_exits(diag, monkeypatch):
    prompts = []
    exits = []
    monkeypatch.setattr(diag, "_show_message_box", lambda title, text: prompts.append(text) or True)
    monkeypatch.setattr(diag, "_graceful_exit", lambda code: exits.append(code))

    try:
        raise RuntimeError("fatal-marker-1")
    except RuntimeError:
        diag.report_uncaught(*sys.exc_info())

    assert exits == [1], "未捕捉例外應結束行程"
    assert len(prompts) == 1
    assert "fatal-marker-1" in prompts[0]
    assert diag._CRASH_LOG_NAME in prompts[0], "提示必須告知日誌位置"
    crash_body = open(os.path.join(diag.log_dir(), diag._CRASH_LOG_NAME), encoding="utf-8").read()
    assert "fatal-marker-1" in crash_body

    # 同一行程第二個錯誤：不再彈窗（避免重複提示）
    try:
        raise RuntimeError("fatal-marker-2")
    except RuntimeError:
        diag.report_uncaught(*sys.exc_info())
    assert len(prompts) == 1, "同一錯誤不得重複提示"
    assert exits == [1, 1], "第二次仍須結束行程"


def test_prompt_skipped_in_smoke_mode(diag, monkeypatch):
    called = []
    monkeypatch.setattr(diag, "_show_message_box", lambda title, text: called.append(text) or True)
    monkeypatch.setattr(sys, "argv", ["app.py", "--smoke"])

    assert diag.prompt_once("x", None) is False
    assert called == [], "自動化 smoke 不得被 modal 視窗卡住"


def test_prompt_without_log_file_omits_path(diag, monkeypatch):
    texts = []
    monkeypatch.setattr(diag, "_show_message_box", lambda title, text: texts.append(text) or True)
    monkeypatch.setattr(sys, "argv", ["app.py"])

    assert diag.prompt_once("RuntimeError: x", None) is True
    assert "RuntimeError: x" in texts[0]
    assert "無法寫入日誌檔" in texts[0]


def test_install_guards_replaces_hooks_once(diag):
    diag.install_guards()
    assert sys.excepthook is diag._sys_excepthook
    assert threading.excepthook is diag._thread_excepthook

    first = sys.excepthook
    diag.install_guards()
    assert sys.excepthook is first


def test_report_uncaught_exits_even_if_every_diagnostic_step_fails(diag, monkeypatch):
    """A：日誌 / crash / 提示 / 清理 全部失敗時，仍必須結束行程（不得無聲卡住或遞迴）。"""
    exits = []
    monkeypatch.setattr(diag, "_show_message_box", lambda t, x: (_ for _ in ()).throw(OSError("no user32")))
    monkeypatch.setattr(diag, "write_crash", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))
    monkeypatch.setattr(diag, "_graceful_exit", lambda code: exits.append(code))

    # 讓 logger 也炸：掛一個 emit 必拋的 handler
    class Boom(logging.Handler):
        def emit(self, record):
            raise RuntimeError("handler boom")

    boom = Boom()
    logging.getLogger().addHandler(boom)
    try:
        try:
            raise RuntimeError("primary-fault")
        except RuntimeError:
            diag.report_uncaught(*sys.exc_info())
    finally:
        logging.getLogger().removeHandler(boom)

    assert exits == [1], "診斷全失敗仍須結束行程"


def test_sys_excepthook_exits_even_when_reporting_raises(diag, monkeypatch):
    """A：report_uncaught 自身拋例外（含 BaseException）時，hook wrapper 仍須結束行程。"""
    exits = []
    monkeypatch.setattr(diag, "_exit", lambda code: exits.append(code))
    monkeypatch.setattr(diag, "report_uncaught", lambda *a, **k: (_ for _ in ()).throw(KeyboardInterrupt()))

    diag._sys_excepthook(ValueError, ValueError("x"), None)
    assert exits == [1], "hook wrapper 的 BaseException 防護 + _exit 必須生效"


def test_report_uncaught_survives_keyboard_interrupt_from_logging(diag, monkeypatch):
    """A：logging 拋 BaseException（如 KeyboardInterrupt）時仍要寫 crash、提示、結束。"""
    exits = []
    prompts = []
    monkeypatch.setattr(diag, "_show_message_box", lambda t, x: prompts.append(x) or True)
    monkeypatch.setattr(diag, "_graceful_exit", lambda code: exits.append(code))

    class Boom(logging.Handler):
        def emit(self, record):
            raise KeyboardInterrupt

    boom = Boom()
    logging.getLogger().addHandler(boom)
    try:
        try:
            raise RuntimeError("ki-in-log-primary")
        except RuntimeError:
            diag.report_uncaught(*sys.exc_info())
    finally:
        logging.getLogger().removeHandler(boom)

    assert exits == [1] and len(prompts) == 1
    body = open(os.path.join(diag.log_dir(), diag._CRASH_LOG_NAME), encoding="utf-8").read()
    assert "ki-in-log-primary" in body, "logging 失敗不得吃掉 crash 檔"


def test_thread_hook_records_traceback_without_exiting(diag, monkeypatch):
    exits = []
    monkeypatch.setattr(diag, "_exit", lambda code: exits.append(code))

    try:
        raise RuntimeError("thread-marker-9")
    except RuntimeError:
        args = threading.ExceptHookArgs((*sys.exc_info(), threading.current_thread()))
        diag._thread_excepthook(args)

    assert exits == [], "背景 thread 例外不應結束行程"
    body = open(os.path.join(diag.log_dir(), diag._CRASH_LOG_NAME), encoding="utf-8").read()
    assert "thread-marker-9" in body


def test_thread_hook_ignores_system_exit(diag):
    args = threading.ExceptHookArgs((SystemExit, SystemExit(0), None, threading.current_thread()))
    diag._thread_excepthook(args)  # 不得拋例外、也不得留 crash 檔
    assert not os.path.exists(os.path.join(diag.log_dir(), diag._CRASH_LOG_NAME))

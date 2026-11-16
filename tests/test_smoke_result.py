"""smoke 結果檔：不依賴 stdout/stderr、成功與失敗都留下可讀證據、正常啟動不受影響。

frozen（--noconsole）版的 sys.stdout / sys.stderr 皆為 None，print() 的輸出會完全消失；
因此 smoke 必須把結果寫入使用者資料目錄的 smoke_result.txt（每次執行前覆寫）。
"""

import logging
import os
import sys
import threading
from pathlib import Path

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


def _body(diag):
    path = diag.smoke_result_path()
    return open(path, encoding="utf-8").read() if os.path.exists(path) else ""


def test_smoke_result_path_is_in_user_data_dir(diag, tmp_path):
    expected = tmp_path / "LocalAppData" / "GameTools_HealthMonitor" / "smoke_result.txt"
    assert diag.smoke_result_path() == str(expected)


def test_write_smoke_echoes_to_stdout_when_available(diag, capsys):
    diag.write_smoke("SMOKE 檢查 stdout-901")
    assert "SMOKE 檢查 stdout-901" in capsys.readouterr().out
    assert "SMOKE 檢查 stdout-901" in _body(diag)


def test_write_smoke_survives_missing_stdout_and_stderr(diag, monkeypatch):
    """frozen --noconsole：stdout / stderr 皆為 None，smoke 結果仍必須落地。"""
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    diag.write_smoke("SMOKE 檢查 no-console-902")
    assert "no-console-902" in _body(diag)


def test_reset_smoke_result_keeps_only_latest_run(diag):
    diag.reset_smoke_result()
    diag.write_smoke("RUN-1")
    diag.reset_smoke_result()
    assert _body(diag) == ""
    diag.write_smoke("RUN-2")
    body = _body(diag)
    assert "RUN-2" in body and "RUN-1" not in body


def test_mark_smoke_ok_writes_ok_marker(diag):
    diag.reset_smoke_result()
    diag.mark_smoke_ok()
    assert "SMOKE RESULT: OK" in _body(diag)


def test_mark_smoke_failed_writes_marker_only_once(diag):
    diag.reset_smoke_result()
    diag.mark_smoke_failed("AssertionError: boom-903")
    diag.mark_smoke_failed("AssertionError: boom-903")
    body = _body(diag)
    assert body.count("SMOKE FAILED") == 1, "同一行程不得重複標記失敗"
    assert "boom-903" in body


def test_mark_smoke_ok_after_failure_is_ignored(diag):
    diag.reset_smoke_result()
    diag.mark_smoke_failed("AssertionError: boom-904")
    diag.mark_smoke_ok()
    body = _body(diag)
    assert "SMOKE RESULT: OK" not in body
    assert "SMOKE FAILED" in body


def test_report_uncaught_in_smoke_mode_marks_failure(diag, monkeypatch):
    """smoke 中的未捕捉例外：留下 FAILED 標記、不彈窗、以非 0 exit code 結束。"""
    monkeypatch.setattr(sys, "argv", ["app.py", "--smoke"])
    prompts = []
    exits = []
    monkeypatch.setattr(diag, "_show_message_box", lambda title, text: prompts.append(text) or True)
    monkeypatch.setattr(diag, "_graceful_exit", lambda code: exits.append(code))
    try:
        raise AssertionError("smoke-fail-905")
    except AssertionError:
        diag.report_uncaught(*sys.exc_info())

    assert exits == [1], "smoke 失敗必須以非 0 exit code 結束"
    assert prompts == [], "smoke 不得被 modal 視窗卡住"
    body = _body(diag)
    assert "SMOKE FAILED" in body and "smoke-fail-905" in body
    assert "SMOKE RESULT: OK" not in body


def test_normal_startup_creates_no_smoke_result_file(diag):
    """正常啟動（無 --smoke）不得產生 smoke 結果檔。"""
    diag.bootstrap()
    assert not os.path.exists(diag.smoke_result_path())


def test_app_routes_smoke_output_through_result_file():
    """app.py 的 smoke 輸出與成功標記必須接到結果檔（frozen 版 stdout 不可用）。"""
    src = (Path(__file__).resolve().parent.parent / "src" / "app.py").read_text(encoding="utf-8")
    assert "startup_diagnostics.reset_smoke_result()" in src
    assert "startup_diagnostics.mark_smoke_ok()" in src
    assert src.count("startup_diagnostics.write_smoke(") >= 10, "smoke 輸出必須全部改走結果檔"
    leftovers = [ln for ln in src.splitlines() if "print(" in ln and "stdout 為 None" not in ln]
    assert leftovers == [], f"app.py 仍有直接 print 的 smoke 輸出: {leftovers}"

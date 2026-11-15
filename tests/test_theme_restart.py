"""主題變更 → 重新啟動套用（執行期間取消熱切換）。

驗收重點：
1. 選擇相同主題不會重啟、選擇不同主題會寫入設定（見 tests/test_theme_settings.py）。
2. 新程序啟動失敗時，舊程序不得被提前關閉（使用者仍可操作）。
3. 開發模式與 PyInstaller 打包環境的啟動路徑都正確。
4. 新程序以就緒標記回報「已成功啟動」，舊程序據此才結束自己。
5. 啟動階段仍會以設定檔的主題完整套用（重啟後載入新主題）。
"""

import json
import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("PySide6.QtWidgets")

import qt.theme as theme  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"


class _FakeProc:
    """subprocess.Popen 的最小替身（不真的開程序）。"""

    def __init__(self, *, alive: bool = True) -> None:
        self.alive = alive
        self.terminated = False
        self.killed = False

    def poll(self):
        return None if self.alive else 0

    def terminate(self):
        self.terminated = True
        self.alive = False

    def kill(self):
        self.killed = True
        self.alive = False

    def wait(self, timeout=None):
        return 0


# ── 啟動路徑（開發模式 / PyInstaller）───────────────────────────────


def test_launch_args_in_dev_mode(theme_window, monkeypatch):
    """開發模式：用同一個 Python 執行 src/app.py，工作目錄為 repo 根目錄。"""
    monkeypatch.delattr(sys, "frozen", raising=False)
    args, cwd = theme_window._launch_args_and_cwd()
    assert args[0] == "src/app.py"
    assert Path(cwd) == REPO_ROOT


def test_launch_args_keep_debug_flag(theme_window, monkeypatch):
    """開發模式：--debug 必須沿用（否則重啟後 log 設定會不見）。"""
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(sys, "argv", [*sys.argv, "--debug"])
    args, _ = theme_window._launch_args_and_cwd()
    assert "--debug" in args


def test_launch_args_in_frozen_mode(theme_window, monkeypatch):
    """PyInstaller 打包：sys.executable 即 EXE，直接重跑且不帶額外參數。"""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Tools\GameTools_HealthMonitor.exe")
    args, cwd = theme_window._launch_args_and_cwd()
    assert args == []
    assert Path(cwd) == Path(r"C:\Tools")


# ── 重新啟動流程 ────────────────────────────────────────────────────


def test_restart_app_waits_for_ready_marker(theme_window, monkeypatch):
    """新程序回報就緒後，舊程序才結束自己。"""
    launched: dict = {}

    def fake_relaunch(launch_args, cwd, extra_args=None):
        launched["args"] = launch_args
        launched["cwd"] = cwd
        launched["extra"] = extra_args or []
        marker = Path([a for a in extra_args if a.startswith("--startup-ready-file=")][0].split("=", 1)[1])
        marker.write_text("12345", encoding="utf-8")
        return _FakeProc()

    monkeypatch.setattr(theme_window, "_relaunch_detached", fake_relaunch)
    monkeypatch.setattr(theme_window, "_arm_exit_watchdog", lambda *a, **k: None)
    closed: list[int] = []
    monkeypatch.setattr(theme_window, "close_app", lambda: closed.append(1))
    monkeypatch.setattr(theme_window, "_report_restart_failed", lambda reason: pytest.fail(f"不應失敗: {reason}"))

    assert theme_window.restart_app() is True
    assert closed, "新程序就緒後必須結束舊程序"
    assert any(a.startswith("--startup-ready-file=") for a in launched["extra"]), "必須帶就緒標記參數"


def test_restart_app_failure_keeps_old_process_running(theme_window, monkeypatch):
    """新程序啟動失敗：舊程序不得被關閉（使用者仍可操作），且必須顯示錯誤。"""
    monkeypatch.setattr(theme_window, "_relaunch_detached", lambda *a, **k: None)
    monkeypatch.setattr(theme_window, "_arm_exit_watchdog", lambda *a, **k: None)
    closed: list[int] = []
    monkeypatch.setattr(theme_window, "close_app", lambda: closed.append(1))
    reasons: list[str] = []
    monkeypatch.setattr(theme_window, "_report_restart_failed", lambda reason: reasons.append(reason))

    assert theme_window.restart_app() is False
    assert closed == [], "啟動失敗不得關閉舊程序"
    assert reasons, "啟動失敗必須回報明確錯誤"


def test_restart_app_terminates_child_when_not_ready(theme_window, monkeypatch):
    """新程序沒有回報就緒 → 必須收掉它，避免與舊程序並存（重複／殘留程序）。"""
    proc = _FakeProc()
    monkeypatch.setattr(theme_window, "_relaunch_detached", lambda *a, **k: proc)
    monkeypatch.setattr(theme_window, "_arm_exit_watchdog", lambda *a, **k: None)
    closed: list[int] = []
    monkeypatch.setattr(theme_window, "close_app", lambda: closed.append(1))
    reasons: list[str] = []
    monkeypatch.setattr(theme_window, "_report_restart_failed", lambda reason: reasons.append(reason))

    assert theme_window.restart_app(timeout_s=0.3) is False
    assert closed == [], "新程序未就緒不得關閉舊程序"
    assert proc.terminated or proc.killed, "半啟動的新程序必須被收掉"
    assert reasons


def test_restart_app_cleans_up_child_that_exited_early(theme_window, monkeypatch):
    """新程序立刻結束（啟動失敗）→ 舊程序維持運作並回報錯誤。"""
    proc = _FakeProc(alive=False)
    monkeypatch.setattr(theme_window, "_relaunch_detached", lambda *a, **k: proc)
    monkeypatch.setattr(theme_window, "_arm_exit_watchdog", lambda *a, **k: None)
    closed: list[int] = []
    monkeypatch.setattr(theme_window, "close_app", lambda: closed.append(1))
    reasons: list[str] = []
    monkeypatch.setattr(theme_window, "_report_restart_failed", lambda reason: reasons.append(reason))

    assert theme_window.restart_app(timeout_s=5.0) is False
    assert closed == []
    assert reasons


# ── 新程序端 ────────────────────────────────────────────────────────


def test_startup_ready_marker_is_written(tmp_path, monkeypatch):
    """新程序於 main() 開頭寫出就緒標記，讓舊程序確認「已成功啟動」。"""
    import app as app_mod

    marker = tmp_path / "ready.marker"
    monkeypatch.setattr(sys, "argv", ["app.py", f"--startup-ready-file={marker}"])
    app_mod._startup_ready_marker()
    assert marker.exists(), "就緒標記必須寫出"
    assert marker.read_text(encoding="utf-8") == str(os.getpid())


def test_startup_ready_marker_absent_without_argument(tmp_path, monkeypatch):
    """未帶參數時不得寫任何檔案（一般啟動不受影響）。"""
    import app as app_mod

    monkeypatch.setattr(sys, "argv", ["app.py"])
    app_mod._startup_ready_marker()  # 不得例外


def test_startup_applies_theme_from_config():
    """啟動階段仍以設定檔的主題完整套用（熱切換移除後的唯一套用點）。"""
    source = (SRC / "app.py").read_text(encoding="utf-8")
    assert 'theme.apply_theme(_config_manager.get_config_value("theme", theme.DEFAULT_THEME))' in source


def test_config_theme_is_applied_on_startup(tmp_path):
    """設定檔中的主題在啟動時會被套用（= 重啟後載入所選主題）。"""
    from config_manager import ConfigManager

    cm = ConfigManager(config_path=str(tmp_path))
    cm.load_config()
    cm.set_config_value("theme", "light")
    theme._applied_theme = None
    try:
        theme.apply_theme(cm.get_config_value("theme", theme.DEFAULT_THEME))
        assert theme.current_theme() == "light"
    finally:
        theme._applied_theme = None
        theme.apply_theme("dark")


# ── i18n ────────────────────────────────────────────────────────────


def test_theme_restart_i18n_keys_exist_in_every_language():
    """三個語系都必須有主題重啟相關字串（提示與錯誤訊息）。"""
    packs = json.loads((SRC / "language_packs.json").read_text(encoding="utf-8"))
    assert len(packs) >= 3
    for lang, data in packs.items():
        for key in ("theme", "theme_dark", "theme_light", "theme_hint", "theme_restart_title", "theme_restart_message", "theme_restart_hint", "theme_restart_failed"):
            assert key in data, f"{lang} 缺少 {key}"
            assert isinstance(data[key], str) and data[key].strip(), f"{lang}.{key} 為空"


def test_theme_hint_mentions_restart_in_every_language():
    """主題提示必須明確告知「需要重新啟動」（不得再寫立即套用）。"""
    packs = json.loads((SRC / "language_packs.json").read_text(encoding="utf-8"))
    for lang, data in packs.items():
        hint = data["theme_hint"]
        assert any(k in hint for k in ("重啟", "重启")) or "restart" in hint.lower(), f"{lang}.theme_hint 未提及重新啟動：{hint}"
        assert "立即套用" not in hint and "Applies immediately" not in hint, f"{lang}.theme_hint 仍宣稱立即套用"

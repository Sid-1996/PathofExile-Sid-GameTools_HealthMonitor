import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

_root = Path(__file__).resolve().parent.parent
_src = _root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))


# ── 測試 session 的使用者資料隔離 ─────────────────────────────────────────
# app.py 在「匯入當下」就會呼叫 startup_diagnostics.bootstrap()，當下若 LOCALAPPDATA
# 指向開發者真實的使用者資料目錄，root logger 的檔案 handler 就會綁到真實的
# gtools.log，之後整個 session 的診斷記錄都會寫進使用者資料（設定檔本身不受影響）。
#
# 隔離必須在「任何測試模組被匯入之前」生效，因此不能用 function-scoped fixture：
# conftest.py 是在該目錄的測試模組之前被匯入的，這裡（模組層級）是本 repo 最早的
# 切入點，即使日後有人在測試模組層級 import app 也擋得住。
_ORIGINAL_LOCALAPPDATA = os.environ.get("LOCALAPPDATA")
TEST_LOCALAPPDATA = tempfile.mkdtemp(prefix="gtools_pytest_localappdata_")
os.environ["LOCALAPPDATA"] = TEST_LOCALAPPDATA

_ARGV_AT_SESSION_START = list(sys.argv)


@pytest.fixture(scope="session")
def test_env_isolation():
    """session 隔離設定：原始（真實）與測試用 LOCALAPPDATA。"""
    return SimpleNamespace(original_localappdata=_ORIGINAL_LOCALAPPDATA, localappdata=TEST_LOCALAPPDATA)


@pytest.fixture(scope="session", autouse=True)
def _session_isolation_guard():
    """session 結束時確認：診斷 handler 未指向真實使用者資料目錄、sys.argv 未殘留 --smoke。"""
    yield
    real_dir = os.path.join(_ORIGINAL_LOCALAPPDATA, "GameTools_HealthMonitor") if _ORIGINAL_LOCALAPPDATA else None
    if real_dir:
        real_dir = os.path.abspath(real_dir)
        for handler in logging.getLogger().handlers:
            filename = getattr(handler, "baseFilename", None)
            if filename:
                assert not os.path.abspath(filename).startswith(real_dir), f"測試的日誌 handler 指向真實使用者資料目錄：{filename}"
    if "--smoke" in sys.argv and "--smoke" not in _ARGV_AT_SESSION_START:
        raise AssertionError("sys.argv 殘留 --smoke（theme_window fixture 未還原）")
    # 證據輸出（-s 時可見）：隔離目錄與其中的診斷日誌
    diag_log = Path(TEST_LOCALAPPDATA) / "GameTools_HealthMonitor" / "gtools.log"
    print(f"[isolation] LOCALAPPDATA={TEST_LOCALAPPDATA}")
    print(f"[isolation] diag log={diag_log} exists={diag_log.exists()}")


def pytest_unconfigure(config):
    """session 結束後還原 LOCALAPPDATA，並清掉本次測試的暫存目錄。"""
    if _ORIGINAL_LOCALAPPDATA is None:
        os.environ.pop("LOCALAPPDATA", None)
    else:
        os.environ["LOCALAPPDATA"] = _ORIGINAL_LOCALAPPDATA
    shutil.rmtree(TEST_LOCALAPPDATA, ignore_errors=True)


@pytest.fixture
def tmp_config_manager(tmp_path):
    """ConfigManager 指向 tmp_path，避免污染 src/ 真實 config。"""
    from config_manager import ConfigManager

    cm = ConfigManager(config_path=str(tmp_path))
    ok = cm.load_config()
    assert ok
    return cm


# ── GUI（offscreen）共用 fixture ─────────────────────────────────────────
# 用途：主題相關分頁測試共用同一個真實 MainWindow，避免每個模組各自複製一份。
# 不引入 pytest-qt；熱鍵勾子與 AHK 監聽以 monkeypatch 停用，避免測試程序安裝全域鍵盤勾子。


@pytest.fixture(scope="module")
def qapp():
    import os

    pytest.importorskip("PySide6.QtWidgets")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    app.setApplicationName("GameTools Health Monitor (test)")
    return app


class _NoopAutoClick:
    def setup_auto_click_listener(self):
        pass

    def stop_auto_click_ahk(self):
        pass


@pytest.fixture(scope="module")
def theme_window(qapp, tmp_path_factory):
    """真實 MainWindow（single instance / module）：config 指向暫存目錄、不啟用熱鍵與 AHK。"""
    import sys

    import config_manager as cm_mod
    import qt.main_window as mw
    import qt.theme as theme
    from _pytest.monkeypatch import MonkeyPatch

    mp = MonkeyPatch()
    tmp = tmp_path_factory.mktemp("cfg_theme_pages")
    cm = cm_mod.ConfigManager(config_path=str(tmp))
    cm.load_config()

    mp.setattr(mw.MainWindow, "config_manager_factory", lambda self: cm)
    mp.setattr(mw.MainWindow, "setup_hotkeys", lambda self: None)
    mp.setattr(mw, "AutoClickManager", lambda *a, **k: _NoopAutoClick())
    # --smoke 必須在 fixture 結束時還原：sys.argv 是全域狀態，殘留會讓後續測試
    # 誤判為 smoke 模式（例如 startup_diagnostics 的錯誤提示被抑制）。
    argv_backup = list(sys.argv)
    if "--smoke" not in sys.argv:
        sys.argv.append("--smoke")

    theme.apply_theme("dark")
    window = mw.MainWindow()
    yield window
    # 真正刪除 C++ 物件（含其 qconfig.themeChangedFinished 連線），避免下一個測試模組
    # 建立 MainWindow 時多一個實例一起回應主題訊號。
    try:
        from PySide6.QtCore import QCoreApplication, QEvent

        window._is_closing = True
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    except Exception:
        pass
    mp.undo()
    sys.argv[:] = argv_backup

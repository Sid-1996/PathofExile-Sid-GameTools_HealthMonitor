import sys
from pathlib import Path

import pytest

_root = Path(__file__).resolve().parent.parent
_src = _root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))


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

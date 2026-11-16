"""測試環境隔離：診斷日誌不得寫入開發者真實的使用者資料目錄。

背景：app.py 在「匯入當下」就會呼叫 startup_diagnostics.bootstrap()，此時若
LOCALAPPDATA 指向開發者真實的使用者資料目錄，root logger 的檔案 handler 就會綁到
真實的 gtools.log，之後整個 session 的診斷記錄都會寫進使用者資料。

隔離由 tests/conftest.py 在模組層級（早於任何測試模組匯入）完成，此處驗證其效果。

注意：本檔刻意不建立任何 root logger handler，也不 import app：
handler 一旦掛上就會殘留在 root logger 上（其他測試的 fixture 會在還原時把它撈回來），
診斷檔案的落點則用 write_crash / write_smoke 等無副作用的寫檔函式驗證。
"""

import logging
import os
from pathlib import Path

import startup_diagnostics as sd


def _real_data_dir(test_env_isolation):
    base = test_env_isolation.original_localappdata
    return Path(base) / "GameTools_HealthMonitor" if base else None


def _fingerprint(path):
    if path is None or not path.exists():
        return None
    stat = path.stat()
    return (stat.st_mtime_ns, stat.st_size)


def test_localappdata_points_to_session_temp_dir(test_env_isolation):
    """LOCALAPPDATA 在 session 期間必須指向測試專用暫存目錄。"""
    assert os.environ["LOCALAPPDATA"] == test_env_isolation.localappdata
    assert Path(test_env_isolation.localappdata).is_dir()
    if test_env_isolation.original_localappdata:
        assert test_env_isolation.localappdata != test_env_isolation.original_localappdata


def test_diagnostics_log_path_is_inside_isolated_dir(test_env_isolation):
    """診斷日誌的落點（bootstrap 實際使用的路徑）必須在隔離目錄內。"""
    path = Path(sd.log_path())
    assert path.parent.name == "GameTools_HealthMonitor"
    assert Path(test_env_isolation.localappdata) in path.parents


def test_diagnostics_files_land_in_isolated_dir(test_env_isolation):
    """診斷檔案（crash / smoke 結果）必須寫進隔離目錄。"""
    crash = sd.write_crash("isolation-probe-918", "probe body")
    assert crash is not None
    crash_path = Path(crash)
    assert Path(test_env_isolation.localappdata) in crash_path.parents
    assert "probe body" in crash_path.read_text(encoding="utf-8")

    sd.write_smoke("isolation-probe-919")
    smoke_path = Path(sd.smoke_result_path())
    assert Path(test_env_isolation.localappdata) in smoke_path.parents
    assert "isolation-probe-919" in smoke_path.read_text(encoding="utf-8")


def test_diagnostics_writes_do_not_touch_real_user_data_dir(test_env_isolation):
    """寫診斷檔案前後，真實使用者的資料目錄必須完全沒有變動。"""
    real_dir = _real_data_dir(test_env_isolation)
    before = {p.name: _fingerprint(p) for p in (real_dir.glob("*") if real_dir and real_dir.is_dir() else [])}

    sd.write_crash("isolation-probe-920", "probe body")
    sd.write_smoke("isolation-probe-921")

    after = {p.name: _fingerprint(p) for p in (real_dir.glob("*") if real_dir and real_dir.is_dir() else [])}
    assert before == after, "測試不得寫入開發者真實的使用者資料目錄"


def test_no_log_handler_points_at_real_user_data_dir(test_env_isolation):
    """任何 root logger handler 都不得指向開發者真實的使用者資料目錄。"""
    real_dir = _real_data_dir(test_env_isolation)
    if real_dir is None:
        return
    real = os.path.abspath(str(real_dir))
    for handler in logging.getLogger().handlers:
        filename = getattr(handler, "baseFilename", None)
        if filename:
            assert not os.path.abspath(filename).startswith(real), f"handler 指向真實使用者資料目錄：{filename}"

"""MainWindow 設定儲存回饋：失敗只提示一次、成功恢復正常狀態、關閉期間只留 log。"""

import logging


class _StubConfigManager:
    """最小替身：模擬 ConfigManager.save_config 的成功／失敗。"""

    def __init__(self, ok=True):
        self.ok = ok
        self.save_error = None
        self.load_status = None

    def save_config(self, config_data=None):
        self.save_error = None if self.ok else "disk full"
        return self.ok


def _capture(window, monkeypatch):
    statuses, notices = [], []
    monkeypatch.setattr(window, "add_status_message", lambda msg, msg_type="info": statuses.append((msg, msg_type)))
    monkeypatch.setattr(window, "show_floating_notice", lambda msg, msg_type="warning": notices.append((msg, msg_type)))
    return statuses, notices


def test_save_failure_notifies_once_then_recovers(theme_window, monkeypatch):
    window = theme_window
    statuses, notices = _capture(window, monkeypatch)
    cm = _StubConfigManager(ok=False)
    monkeypatch.setattr(window, "config_manager", cm)
    monkeypatch.setattr(window, "_config_save_error", False)

    window.save_config()
    assert len(statuses) == 1, "儲存失敗應提示一次"
    assert statuses[0][1] == "error"
    assert len(notices) == 1, "儲存失敗應有 toast"

    window.save_config()  # debounce 連續失敗
    assert len(statuses) == 1 and len(notices) == 1, "同一波失敗不應重複彈窗"

    cm.ok = True
    window.save_config()
    assert window._config_save_error is False, "成功後應恢復正常狀態"
    assert len(statuses) == 1, "成功不應顯示錯誤"

    cm.ok = False
    window.save_config()
    assert len(statuses) == 2, "恢復後再次失敗應重新提示"


def test_save_success_shows_no_error(theme_window, monkeypatch):
    window = theme_window
    statuses, notices = _capture(window, monkeypatch)
    monkeypatch.setattr(window, "config_manager", _StubConfigManager(ok=True))
    monkeypatch.setattr(window, "_config_save_error", False)

    window.save_config()
    assert statuses == [] and notices == []
    assert window._config_save_error is False


def test_load_status_restored_shows_warning_notice(theme_window, monkeypatch):
    window = theme_window
    statuses, notices = _capture(window, monkeypatch)
    cm = _StubConfigManager(ok=True)
    cm.load_status = "restored_from_backup"
    monkeypatch.setattr(window, "config_manager", cm)

    window._notify_config_load_status()
    assert len(statuses) == 1 and statuses[0][1] == "warning"
    assert len(notices) == 1 and notices[0][1] == "warning"


def test_load_status_defaults_and_normal_do_not_duplicate_notices(theme_window, monkeypatch):
    window = theme_window
    statuses, notices = _capture(window, monkeypatch)
    cm = _StubConfigManager(ok=True)
    monkeypatch.setattr(window, "config_manager", cm)

    window._notify_config_load_status()  # 正常載入（load_status=None）→ 無提示
    assert statuses == [] and notices == []

    cm.load_status = "reset_to_defaults"
    window._notify_config_load_status()
    assert len(statuses) == 1 and statuses[0][1] == "error"
    assert len(notices) == 1


def test_save_failure_while_closing_only_logs(theme_window, monkeypatch, caplog):
    window = theme_window
    statuses, notices = _capture(window, monkeypatch)
    monkeypatch.setattr(window, "config_manager", _StubConfigManager(ok=False))
    monkeypatch.setattr(window, "_config_save_error", False)
    monkeypatch.setattr(window, "_is_closing", True)

    with caplog.at_level(logging.ERROR, logger="qt.main_window"):
        window.save_config()

    assert statuses == [] and notices == [], "關閉期間不彈 GUI"
    assert any("設定儲存失敗" in rec.getMessage() for rec in caplog.records), "關閉期間失敗需留下 log"

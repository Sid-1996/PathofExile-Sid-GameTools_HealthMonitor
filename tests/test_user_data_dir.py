"""get_user_data_dir 使用者資料遷移測試。"""

import os

import utils


def _use_fake_dirs(monkeypatch, tmp_path):
    """把 app 目錄與 LOCALAPPDATA 都指向暫存路徑，隔離開發機真實環境。"""
    fake_app = tmp_path / "app"
    fake_local = tmp_path / "localappdata"
    fake_app.mkdir()
    monkeypatch.setattr(utils, "get_app_dir", lambda: str(fake_app))
    monkeypatch.setenv("LOCALAPPDATA", str(fake_local))
    return fake_app, fake_local


def test_migrates_legacy_config_and_screenshots(monkeypatch, tmp_path):
    fake_app, fake_local = _use_fake_dirs(monkeypatch, tmp_path)
    (fake_app / "health_monitor_config.json").write_text('{"a": 1}', encoding="utf-8")
    shots = fake_app / "screenshots"
    shots.mkdir()
    (shots / "p.png").write_bytes(b"png")

    data_dir = utils.get_user_data_dir()

    assert data_dir == str(fake_local / "GameTools_HealthMonitor")
    assert (fake_local / "GameTools_HealthMonitor" / "health_monitor_config.json").read_text(encoding="utf-8") == '{"a": 1}'
    assert (fake_local / "GameTools_HealthMonitor" / "screenshots" / "p.png").read_bytes() == b"png"
    # 複製不刪除：來源保留
    assert (fake_app / "health_monitor_config.json").exists()


def test_migration_is_idempotent(monkeypatch, tmp_path):
    fake_app, fake_local = _use_fake_dirs(monkeypatch, tmp_path)
    (fake_app / "health_monitor_config.json").write_text('{"old": true}', encoding="utf-8")

    utils.get_user_data_dir()
    new_cfg = fake_local / "GameTools_HealthMonitor" / "health_monitor_config.json"
    # 模擬使用者在新位置修改過 config
    new_cfg.write_text('{"new": true}', encoding="utf-8")

    utils.get_user_data_dir()

    assert new_cfg.read_text(encoding="utf-8") == '{"new": true}'


def test_no_legacy_files_is_harmless(monkeypatch, tmp_path):
    fake_app, fake_local = _use_fake_dirs(monkeypatch, tmp_path)
    data_dir = utils.get_user_data_dir()
    assert os.path.isdir(data_dir)
    assert not (fake_local / "GameTools_HealthMonitor" / "screenshots").exists()


def test_backup_file_also_migrates(monkeypatch, tmp_path):
    fake_app, fake_local = _use_fake_dirs(monkeypatch, tmp_path)
    (fake_app / "health_monitor_config.json.backup").write_text("{}", encoding="utf-8")
    utils.get_user_data_dir()
    assert (fake_local / "GameTools_HealthMonitor" / "health_monitor_config.json.backup").exists()

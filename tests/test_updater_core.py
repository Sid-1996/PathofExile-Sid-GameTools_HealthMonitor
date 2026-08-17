"""updater_core 版本解析規則測試。"""

from updater_core import _parse_version


def test_stable_beats_prerelease():
    assert _parse_version("1.2.2") > _parse_version("1.2.2-beta")
    assert _parse_version("1.2.2-beta") > _parse_version("1.2.1")


def test_v_prefix_stripped():
    assert _parse_version("v1.2.1") == _parse_version("1.2.1")


def test_empty_and_garbage():
    assert _parse_version("") == (0,)
    assert _parse_version("abc") == (0,)


def test_newer_wins():
    assert _parse_version("1.3.0") > _parse_version("1.2.9")
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
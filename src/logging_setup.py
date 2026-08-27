"""統一日誌設定。

- console handler：只在有 console（source 模式）時掛載；PyInstaller --noconsole 的
  sys.stdout/stderr 為 None，掛了會在 emit 時靜默失效。
- 預設 level：WARNING（Run.bat 快速啟動保持安靜）。
- --debug flag 或 GTOOLS_LOG_LEVEL=DEBUG → root 昇至 DEBUG 並開啟 rotating file handler
  → %LOCALAPPDATA%\\GameTools_HealthMonitor\\gtools.log（utf-8）。
"""

import logging
import logging.handlers
import os
import sys

from utils import get_user_data_dir

_FORMAT = "%(asctime)s %(levelname)-7s [%(module)s:%(lineno)d] %(message)s"
_configured = False


def configure() -> None:
    """依 --debug / GTOOLS_LOG_LEVEL 設定 root logger。冪等，重複呼叫無副作用。"""
    global _configured
    if _configured:
        return
    _configured = True

    level = _resolve_level()
    root = logging.getLogger()
    root.setLevel(level)

    formatter = logging.Formatter(_FORMAT)

    if sys.stdout is not None or sys.stderr is not None:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        handler.setLevel(level)
        root.addHandler(handler)

    if level <= logging.DEBUG:
        _add_file_handler(root, formatter)


def _resolve_level() -> int:
    if "--debug" in sys.argv:
        return logging.DEBUG
    if os.environ.get("GTOOLS_LOG_LEVEL", "").strip().upper() == "DEBUG":
        return logging.DEBUG
    return logging.WARNING


def _add_file_handler(root: logging.Logger, formatter: logging.Formatter) -> None:
    data_dir = get_user_data_dir()
    try:
        os.makedirs(data_dir, exist_ok=True)
    except Exception:
        return
    handler = logging.handlers.RotatingFileHandler(
        os.path.join(data_dir, "gtools.log"),
        maxBytes=1_000_000,
        backupCount=2,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    root.addHandler(handler)

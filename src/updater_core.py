"""
updater_core.py
自動更新引擎 — 版本檢查、下載、套用
──────────────────────────────────────
移植自 ocr-trigger-clicker/core/12_updater.py
僅使用 requests + 標準庫，無額外依賴。
"""

import os as _os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

import requests

_GITHUB_OWNER = "Sid-1996"
_GITHUB_REPO = "PathofExile-Sid-GameTools_HealthMonitor"
_RAW_VERSION_URL = f"https://raw.githubusercontent.com/{_GITHUB_OWNER}/{_GITHUB_REPO}/master/latest_version.txt"
ASSET_NAME = "GameTools_HealthMonitor.zip"
UPDATER_EXE_NAME = "updater.exe"
_TEMP_PREFIX = "gtool_update_"


@dataclass
class UpdateInfo:
    version: str
    download_url: str
    release_url: str


# ── 版本解析 ──────────────────────────────────────────────


def _parse_version(v: str) -> tuple[int, ...]:
    v = v.strip().lstrip("v")
    if not v:
        return (0,)
    parts = []
    for x in v.split("."):
        m = re.match(r"(\d+)", x)
        parts.append(int(m.group(1)) if m else 0)
    return tuple(parts)


def is_frozen() -> bool:
    """PyInstaller 打包模式下回傳 True"""
    return getattr(sys, "frozen", False)


def current_exe_path() -> Path:
    return Path(sys.executable).resolve()


# ── 版本檢查 ──────────────────────────────────────────────


def check_for_update(current_version: str) -> UpdateInfo | None:
    """從 GitHub raw 取 latest_version.txt，比對後回傳 UpdateInfo 或 None"""
    resp = requests.get(_RAW_VERSION_URL, timeout=10)
    resp.raise_for_status()
    latest = _parse_version(resp.text)
    current = _parse_version(current_version)

    if latest <= current:
        return None

    version_str = ".".join(str(x) for x in latest)
    return UpdateInfo(
        version=version_str,
        download_url=(f"https://github.com/{_GITHUB_OWNER}/{_GITHUB_REPO}/releases/download/v{version_str}/{ASSET_NAME}"),
        release_url=(f"https://github.com/{_GITHUB_OWNER}/{_GITHUB_REPO}/releases/tag/v{version_str}"),
    )


# ── 下載 ──────────────────────────────────────────────────


def _clean_stale_temp_dirs():
    for d in Path(tempfile.gettempdir()).glob(f"{_TEMP_PREFIX}*"):
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)


def download_update(
    info: UpdateInfo,
    progress_cb=None,
    cancel_event=None,
) -> Path:
    """
    下載 ZIP → 解壓 Main EXE + updater.exe → 驗證 MZ header
    回傳 Main EXE 路徑。失敗時自動清理暫存目錄。
    progress_cb(downloaded_bytes, total_bytes): 可選進度回呼。
    cancel_event: threading.Event，set() 時中止下載。
    """
    _clean_stale_temp_dirs()
    tmp_dir = Path(tempfile.mkdtemp(prefix=_TEMP_PREFIX))
    zip_path = tmp_dir / ASSET_NAME
    main_exe_path = tmp_dir / "GameTools_HealthMonitor.exe"

    try:
        resp = requests.get(info.download_url, timeout=60, stream=True)
        resp.raise_for_status()

        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        with open(zip_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if cancel_event and cancel_event.is_set():
                    raise RuntimeError("使用者取消下載")
                f.write(chunk)
                downloaded += len(chunk)
                if progress_cb:
                    progress_cb(downloaded, total)

        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()

            # 解壓主程式 EXE
            exe_entries = [n for n in names if n.endswith(".exe") and UPDATER_EXE_NAME not in n]
            if not exe_entries:
                raise RuntimeError("ZIP 內無主程式 EXE")
            target = next(
                (n for n in exe_entries if "/" not in n and "\\" not in n),
                exe_entries[0],
            )
            with zf.open(target) as src, open(main_exe_path, "wb") as dst:
                shutil.copyfileobj(src, dst)

            # 解壓 updater.exe
            updater_entries = [n for n in names if n == UPDATER_EXE_NAME]
            if not updater_entries:
                raise RuntimeError("ZIP 內缺少 updater.exe")
            updater_dst = tmp_dir / UPDATER_EXE_NAME
            with zf.open(UPDATER_EXE_NAME) as src, open(updater_dst, "wb") as dst:
                shutil.copyfileobj(src, dst)

        # 驗證 MZ header
        with open(main_exe_path, "rb") as f:
            if f.read(2) != b"MZ":
                raise RuntimeError("下載檔案不是有效的 EXE（PE 標頭錯誤）")

        return main_exe_path

    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise


# ── 套用更新 ──────────────────────────────────────────────


def apply_update(new_exe_path: Path) -> None:
    """啟動 updater.exe 背景替換主程式。呼叫後主程式應立即退出。"""
    if not is_frozen():
        raise RuntimeError("原始碼模式不支援自動更新，請手動下載")

    old_exe = current_exe_path()
    updater_exe = new_exe_path.parent / UPDATER_EXE_NAME
    if not updater_exe.exists():
        raise RuntimeError("找不到 updater.exe，無法套用更新")

    debug_log_dir = Path.home() / "AppData" / "Roaming" / "GameTools_HealthMonitor" / "logs"
    debug_log_dir.mkdir(parents=True, exist_ok=True)
    debug_log_path = debug_log_dir / "update_debug.log"

    creationflags_variants = [
        subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_BREAKAWAY_FROM_JOB,
        subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
    ]
    launched = False
    tmp_dir = new_exe_path.parent
    try:
        for flags in creationflags_variants:
            try:
                subprocess.Popen(
                    [
                        str(updater_exe),
                        "--old",
                        str(old_exe),
                        "--new",
                        str(new_exe_path),
                        "--pid",
                        str(_os.getpid()),
                        "--log",
                        str(debug_log_path),
                    ],
                    cwd=str(old_exe.parent),
                    creationflags=flags,
                    close_fds=True,
                )
                launched = True
                break
            except OSError:
                continue

        if not launched:
            raise RuntimeError("無法啟動 updater.exe")

    finally:
        if not launched:
            shutil.rmtree(tmp_dir, ignore_errors=True)

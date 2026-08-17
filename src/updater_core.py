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
_RAW_PRERELEASE_URL = f"https://raw.githubusercontent.com/{_GITHUB_OWNER}/{_GITHUB_REPO}/master/latest_version_prerelease.txt"
_RAW_DELTA_URL = f"https://raw.githubusercontent.com/{_GITHUB_OWNER}/{_GITHUB_REPO}/master/delta_info.json"
ASSET_NAME = "GameTools_HealthMonitor.zip"
DELTA_ASSET_NAME = "GameTools_HealthMonitor-delta.zip"
MANIFEST_FILENAME = "manifest.json"
DELTA_PAYLOAD_DIR = "files"
UPDATER_EXE_NAME = "updater.exe"
_TEMP_PREFIX = "gtool_update_"


class DeltaUpdateError(RuntimeError):
    """delta 不適用於本機安裝（版本基準不符／payload 驗證失敗）。

    只代表「差異更新行不通」，呼叫端應改用完整更新。
    """


@dataclass
class UpdateInfo:
    version: str
    download_url: str
    release_url: str


# ── 版本解析 ──────────────────────────────────────────────


def _parse_version(v: str) -> tuple[int, ...]:
    """解析版本字串，支援 SemVer 後綴（-beta, -alpha 等）。
    Stable 版本比同版本號的 pre-release 高：
      "1.2.2"      → (1, 2, 2, 1)
      "1.2.2-beta" → (1, 2, 2, 0)
    """
    v = v.strip().lstrip("v")
    if not v:
        return (0,)
    match = re.match(r"^(\d+\.\d+\.\d+)(.*)", v)
    if not match:
        return (0,)
    version_part = match.group(1)
    suffix = match.group(2).strip()
    parts = [int(x) for x in version_part.split(".")]
    parts.append(1 if not suffix else 0)
    return tuple(parts)


def is_frozen() -> bool:
    """PyInstaller 打包模式下回傳 True"""
    return getattr(sys, "frozen", False)


def current_exe_path() -> Path:
    return Path(sys.executable).resolve()


# ── 版本檢查 ──────────────────────────────────────────────


def check_for_update(current_version: str, allow_prerelease: bool = False) -> UpdateInfo | None:
    """比對版本，回傳 UpdateInfo 或 None。
    allow_prerelease=True 時會同時檢查 pre-release 版本檔。
    """
    stable_text = ""
    prerelease_text = ""

    resp = requests.get(_RAW_VERSION_URL, timeout=10)
    resp.raise_for_status()
    stable_text = resp.text.strip()

    if allow_prerelease:
        try:
            resp_pre = requests.get(_RAW_PRERELEASE_URL, timeout=10)
            resp_pre.raise_for_status()
            prerelease_text = resp_pre.text.strip()
        except Exception:
            pass

    # 取 stable 與 pre-release 中較高的版本
    if prerelease_text:
        stable_ver = _parse_version(stable_text)
        prerelease_ver = _parse_version(prerelease_text)
        latest_text = prerelease_text if prerelease_ver > stable_ver else stable_text
    else:
        latest_text = stable_text

    latest = _parse_version(latest_text)
    current = _parse_version(current_version)

    if latest <= current:
        return None

    return UpdateInfo(
        version=latest_text,
        download_url=(f"https://github.com/{_GITHUB_OWNER}/{_GITHUB_REPO}/releases/download/v{latest_text}/{ASSET_NAME}"),
        release_url=(f"https://github.com/{_GITHUB_OWNER}/{_GITHUB_REPO}/releases/tag/v{latest_text}"),
    )


# ── 下載 ──────────────────────────────────────────────────


def _clean_stale_temp_dirs():
    for d in Path(tempfile.gettempdir()).glob(f"{_TEMP_PREFIX}*"):
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)


# ── delta manifest ──────────────────────────────────────


def sha256_of_file(path: Path) -> str:
    """回傳檔案 SHA-256 hex。"""
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(root: Path, version: str, base_version: str | None = None) -> dict:
    """掃描安裝樹（含 _internal/），產出 {version, base_version, files:{rel:{size,sha256}}}。"""
    files = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            st = p.stat()
            files[rel] = {"size": st.st_size, "sha256": sha256_of_file(p)}
    return {"version": version, "base_version": base_version, "files": files}


def diff_manifests(prev: dict, new: dict) -> tuple[list[str], list[str], list[str]]:
    """比對兩份 manifest，回傳 (changed, added, removed) 的 rel 路徑清單。"""
    prev_files = prev.get("files", {})
    new_files = new.get("files", {})
    changed = [r for r in prev_files if r in new_files and new_files[r] != prev_files[r]]
    added = [r for r in new_files if r not in prev_files]
    removed = [r for r in prev_files if r not in new_files]
    return changed, added, removed


def download_update(
    info: UpdateInfo,
    progress_cb=None,
    cancel_event=None,
) -> Path:
    """
    下載 ZIP → 解壓整個 onedir 樹（主 EXE + _internal/）→ 驗證 MZ header
    回傳主 EXE 路徑（其父目錄即為 staging，含完整更新樹）。
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
            for member in zf.infolist():
                # 防 zip-slip：確保解壓路徑留在 staging 內
                dest = (tmp_dir / member.filename).resolve()
                if not dest.is_relative_to(tmp_dir.resolve()):
                    raise RuntimeError(f"ZIP 內含非法路徑: {member.filename}")
                if member.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, open(dest, "wb") as dst:
                    shutil.copyfileobj(src, dst)

        if not main_exe_path.exists():
            raise RuntimeError("ZIP 內找不到主程式 GameTools_HealthMonitor.exe")
        if not (tmp_dir / UPDATER_EXE_NAME).exists():
            raise RuntimeError("ZIP 內缺少 updater.exe")

        # 驗證 MZ header
        with open(main_exe_path, "rb") as f:
            if f.read(2) != b"MZ":
                raise RuntimeError("下載檔案不是有效的 EXE（PE 標頭錯誤）")

        # 解壓完成後移除 ZIP，避免被 updater 當作 app 檔複製進安裝目錄
        zip_path.unlink(missing_ok=True)

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


if __name__ == "__main__":
    assert _parse_version("1.2.2") > _parse_version("1.2.2-beta"), "stable must beat pre-release"
    assert _parse_version("v1.2.1") == _parse_version("1.2.1"), "v prefix must be stripped"
    assert _parse_version("1.2.2-beta") > _parse_version("1.2.1"), "newer pre-release beats older"
    assert _parse_version("") == (0,), "empty version -> (0,)"

    # ── manifest / diff self-check ──
    tmp = Path(tempfile.mkdtemp(prefix="gtool_manifest_demo_"))
    try:
        old = tmp / "old"
        new = tmp / "new"
        for d in (old, new):
            d.mkdir()
        (old / "a.txt").write_text("a", encoding="utf-8")
        (old / "b.txt").write_text("b", encoding="utf-8")
        (new / "a.txt").write_text("a", encoding="utf-8")
        (new / "b.txt").write_text("b2", encoding="utf-8")
        (new / "c.txt").write_text("c", encoding="utf-8")
        prev = build_manifest(old, "1.2.1")
        assert prev["version"] == "1.2.1", prev
        assert prev["base_version"] is None, prev
        changed, added, removed = diff_manifests(prev, build_manifest(new, "1.2.2", "1.2.1"))
        assert changed == ["b.txt"], changed
        assert added == ["c.txt"], added
        assert removed == [], removed
        removed_prev = build_manifest(new, "1.2.2", "1.2.1")
        removed_prev["files"].pop("b.txt")
        _, _, removed = diff_manifests(prev, removed_prev)
        assert removed == ["b.txt"], removed
        print("updater_core self-check OK")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

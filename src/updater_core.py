"""
updater_core.py
自動更新引擎 — 版本檢查、下載、套用
──────────────────────────────────────
移植自 ocr-trigger-clicker/core/12_updater.py
僅使用 requests + 標準庫，無額外依賴。
"""

import os as _os
import json
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
    delta_url: str | None = None
    delta_base_version: str | None = None
    delta_bytes: int = 0


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

    info = UpdateInfo(
        version=latest_text,
        download_url=(f"https://github.com/{_GITHUB_OWNER}/{_GITHUB_REPO}/releases/download/v{latest_text}/{ASSET_NAME}"),
        release_url=(f"https://github.com/{_GITHUB_OWNER}/{_GITHUB_REPO}/releases/tag/v{latest_text}"),
    )

    # delta 資訊非必要：取得失敗一律退回整包更新，不能擋掉更新檢查。
    try:
        resp_delta = requests.get(_RAW_DELTA_URL, timeout=10)
        resp_delta.raise_for_status()
        delta_info = resp_delta.json()
        # 用 _parse_version 比對（v 前綴 / -beta 後綴差異），不用字串 ==
        if _parse_version(delta_info.get("version", "")) == latest and _parse_version(delta_info.get("base_version", "")) == current and delta_info.get("asset"):
            info.delta_url = f"https://github.com/{_GITHUB_OWNER}/{_GITHUB_REPO}/releases/download/v{latest_text}/{delta_info['asset']}"
            info.delta_base_version = delta_info["base_version"]
            info.delta_bytes = int(delta_info.get("delta_bytes") or 0)
    except Exception:
        pass

    return info


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


# ── 差異更新（delta）──────────────────────────────────────


def _safe_extract(zip_path: Path, dest: Path) -> None:
    """防 zip-slip 解壓 delta.zip。"""
    dest = dest.resolve()
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            if not (dest / name).resolve().is_relative_to(dest):
                raise DeltaUpdateError("delta 壓縮檔包含非法路徑")
        zf.extractall(dest)


def apply_delta_to_staging(install_dir: Path, staging: Path, delta_root: Path, manifest: dict) -> None:
    """複製目前安裝樹到 staging，覆蓋 delta payload，刪除 removed 清單。"""
    shutil.copytree(install_dir, staging, dirs_exist_ok=True)
    payload_dir = delta_root / DELTA_PAYLOAD_DIR
    files = manifest.get("files", {})
    if payload_dir.is_dir():
        for p in sorted(payload_dir.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(payload_dir).as_posix()
            dst = staging / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
            expect = files.get(rel)
            if expect is None or sha256_of_file(dst) != expect["sha256"]:
                raise DeltaUpdateError(f"delta 檔案驗證失敗: {rel}")
    for rel in manifest.get("removed", []):
        (staging / rel).unlink(missing_ok=True)


def verify_tree(root: Path, manifest: dict) -> bool:
    """整棵 staging 樹對 manifest 全檔驗證（torn copy / 損壞的最後防線）。"""
    files = manifest.get("files", {})
    for rel, meta in files.items():
        p = root / rel
        try:
            if not p.is_file() or p.stat().st_size != meta["size"]:
                return False
            if sha256_of_file(p) != meta["sha256"]:
                return False
        except OSError:
            return False
    return True


def download_delta_update(
    info: UpdateInfo,
    progress_cb=None,
    cancel_event=None,
    fallback_cb=None,
) -> Path:
    """下載 delta.zip → 建立 staging（複製目前安裝樹 + 覆蓋變更）。

    僅「delta 不適用／驗證失敗」（DeltaUpdateError）自動退回整包；
    網路／取消等一般錯誤直接往上拋，與整包下載行為一致。
    回傳 staging 內的主 EXE 路徑（與 download_update 一致，apply_update 免改）。
    """
    if not info.delta_url:
        return download_update(info, progress_cb, cancel_event)

    _clean_stale_temp_dirs()
    tmp_dir = Path(tempfile.mkdtemp(prefix=_TEMP_PREFIX))
    try:
        zip_path = tmp_dir / DELTA_ASSET_NAME
        resp = requests.get(info.delta_url, timeout=60, stream=True)
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

        delta_root = tmp_dir / "delta"
        _safe_extract(zip_path, delta_root)

        manifest_path = delta_root / MANIFEST_FILENAME
        if not manifest_path.is_file():
            raise DeltaUpdateError("delta 缺少 manifest.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if _parse_version(manifest.get("base_version", "")) != _parse_version(info.delta_base_version or ""):
            raise DeltaUpdateError("delta 版本基準不符")

        install_dir = current_exe_path().parent
        if not (install_dir / "_internal").is_dir():
            raise DeltaUpdateError("非 onedir 安裝")

        staging = tmp_dir / "staging"
        apply_delta_to_staging(install_dir, staging, delta_root, manifest)
        if not verify_tree(staging, manifest):
            raise DeltaUpdateError("staging 樹驗證失敗")

        main_exe = staging / "GameTools_HealthMonitor.exe"
        if not main_exe.exists() or main_exe.read_bytes()[:2] != b"MZ":
            raise DeltaUpdateError("staging 內主程式驗證失敗")

        # 記下 removed 清單，供 updater_main 在 swap 後刪除 target 內對應檔案
        (tmp_dir / "removed.json").write_text(json.dumps(manifest.get("removed", [])), encoding="utf-8")
        return main_exe
    except DeltaUpdateError:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        if fallback_cb:
            fallback_cb()
        return download_update(info, progress_cb, cancel_event)
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
    # delta 更新時 removed.json 在 staging 的上層 tmp_dir（整包更新則無此檔）
    removed_path = tmp_dir.parent / "removed.json"
    removed_arg = []
    if removed_path.is_file():
        removed_arg = ["--removed", str(removed_path)]
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
                    ]
                    + removed_arg,
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

        # ── apply_delta_to_staging / verify_tree self-check ──
        install = tmp / "install"
        install.mkdir()
        (install / "a.txt").write_text("a", encoding="utf-8")
        (install / "b.txt").write_text("b", encoding="utf-8")
        (install / "_internal").mkdir()
        (install / "_internal" / "dll.dll").write_text("dllv1", encoding="utf-8")
        staging = tmp / "staging"
        delta_root = tmp / "delta"
        delta_root.mkdir()
        (delta_root / "files").mkdir(parents=True)
        (delta_root / "files" / "_internal").mkdir(parents=True)
        (delta_root / "files" / "b.txt").write_text("b2", encoding="utf-8")
        (delta_root / "files" / "_internal" / "dll.dll").write_text("dllv2", encoding="utf-8")
        manifest = build_manifest(install, "1.2.2", "1.2.1")
        for rel in ("b.txt", "_internal/dll.dll"):
            src = delta_root / "files" / rel
            manifest["files"][rel]["size"] = src.stat().st_size
            manifest["files"][rel]["sha256"] = sha256_of_file(src)
        apply_delta_to_staging(install, staging, delta_root, manifest)
        assert (staging / "b.txt").read_text(encoding="utf-8") == "b2", "payload 應覆蓋"
        assert (staging / "_internal" / "dll.dll").read_text(encoding="utf-8") == "dllv2", "_internal 應覆蓋"
        assert (staging / "a.txt").read_text(encoding="utf-8") == "a", "未變更應保留"
        assert verify_tree(staging, manifest), "staging 應通過整樹驗證"
        (staging / "b.txt").write_text("corrupt", encoding="utf-8")
        assert not verify_tree(staging, manifest), "損壞應驗證失敗"

        # ── removed 清單刪除 self-check ──
        manifest["removed"] = ["_internal/stale.dll"]
        (install / "_internal" / "stale.dll").write_text("stale", encoding="utf-8")
        staging2 = tmp / "staging2"
        apply_delta_to_staging(install, staging2, delta_root, manifest)
        assert not (staging2 / "_internal" / "stale.dll").exists(), "removed 檔應刪除"
        print("updater_core self-check OK")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

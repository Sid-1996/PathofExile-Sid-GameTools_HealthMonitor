"""
updater_main.py
獨立更新程序 — 等待主程式退出 → 替換 EXE → 重啟
由 updater_core.apply_update() 啟動，請勿直接執行。
"""

import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


class _UpdaterParser(argparse.ArgumentParser):
    def error(self, message):
        ctypes.windll.user32.MessageBoxW(
            0,
            f"參數錯誤：{message}\n\n請勿直接執行 updater.exe，此檔案由 GameTools Health Monitor 自動更新時呼叫。",
            "更新錯誤",
            0,
        )
        sys.exit(2)


def _log(log_path, msg):
    if not log_path:
        return
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now()} [updater] {msg}\n")
    except Exception:
        pass


def _wait_for_pid_exit(pid: int, timeout_sec: int, log_path):
    PROCESS_SYNCHRONIZE = 0x00100000
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(PROCESS_SYNCHRONIZE, False, pid)
    if not handle:
        _log(log_path, f"OpenProcess failed for pid={pid}（可能已結束）")
        return
    WAIT_TIMEOUT = 0x00000102
    result = kernel32.WaitForSingleObject(handle, timeout_sec * 1000)
    kernel32.CloseHandle(handle)
    _log(log_path, f"WaitForSingleObject result={result}（0=已結束, {WAIT_TIMEOUT}=逾時）")


def _backup(target_dir: Path, name: str, log_path) -> tuple[bool, Path]:
    """rename 備份 target_dir/name → target_dir/name.old；回傳 (是否備份, 備份路徑)。"""
    src = target_dir / name
    old = target_dir / f"{name}.old"
    if not src.exists():
        return False, old
    try:
        if old.exists():
            if old.is_dir():
                shutil.rmtree(str(old), ignore_errors=True)
            else:
                old.unlink()
        os.rename(str(src), str(old))
        _log(log_path, f"backed up {name}/")
        return True, old
    except OSError as e:
        _log(log_path, f"backup {name} failed ({e}), will copy in place")
        return False, old


def _robust_copy(src, dst, log_path):
    for i in range(10):
        try:
            shutil.copy2(str(src), str(dst))
            return
        except (PermissionError, OSError) as e:
            _log(log_path, f"copy {Path(src).name} attempt {i + 1}/10 failed: {e}")
            time.sleep(1)
    raise OSError(f"copy failed after retries: {Path(src).name}")


def _swap_tree(staging: Path, target_dir: Path, log_path) -> bool:
    """整棵 onedir 樹複製；回傳是否成功。失敗時呼叫端負責 rollback。"""
    for i in range(3):
        try:
            # dirs_exist_ok: 保留使用者旁置檔案（config/screenshots），只覆蓋 app 檔
            shutil.copytree(str(staging), str(target_dir), copy_function=lambda s, d: _robust_copy(s, d, log_path), dirs_exist_ok=True)
            return True
        except OSError as e:
            _log(log_path, f"tree copy attempt {i + 1}/3 failed: {e}")
            time.sleep(1)
    return False


def _restore(target_dir: Path, name: str, old: Path, log_path):
    """rollback：還原 name.old → name"""
    src = target_dir / name
    if not old.exists():
        return
    if src.exists():
        if src.is_dir():
            shutil.rmtree(str(src), ignore_errors=True)
        else:
            try:
                src.unlink()
            except OSError:
                pass
    try:
        os.rename(str(old), str(src))
        _log(log_path, f"restored {name}/")
    except OSError as e:
        _log(log_path, f"restore {name} failed: {e}")


def _delete_removed(target_dir: Path, removed_path, log_path):
    """依 removed 清單刪除 target_dir 內的 rel 檔案（merge-copy 不會自動刪）。"""
    if not removed_path or not Path(removed_path).is_file():
        return
    try:
        removed = json.loads(Path(removed_path).read_text(encoding="utf-8"))
    except Exception as e:
        _log(log_path, f"read removed list failed: {e}")
        return
    for rel in removed:
        p = target_dir / rel
        try:
            if p.is_dir():
                shutil.rmtree(str(p), ignore_errors=True)
            else:
                p.unlink(missing_ok=True)
            _log(log_path, f"removed {rel}")
        except Exception as e:
            _log(log_path, f"remove {rel} failed: {e}")


def _cleanup_staging(staging: Path, log_path):
    """清整個 gtool_update_* temp_root（delta 路徑有 staging/+delta/ 兩層）。

    staging 若是 tmp 根目錄本身（整包更新），直接清 staging；
    若是子目錄（delta 更新，staging.name == "staging"），連同其父 temp_root 一起清。
    執行中的 updater.exe（sys.executable）一律保留。
    """
    roots = [staging]
    if staging.name == "staging" and staging.parent.name.startswith("gtool_update_"):
        roots.append(staging.parent)
    for root in roots:
        try:
            for _entry in root.iterdir():
                if _entry.name == Path(sys.executable).name:
                    continue
                try:
                    if _entry.is_file():
                        _entry.unlink()
                    elif _entry.is_dir():
                        shutil.rmtree(str(_entry), ignore_errors=True)
                except Exception:
                    pass
        except Exception as e:
            _log(log_path, f"cleanup failed: {e}")
        try:
            root.rmdir()
        except Exception:
            pass


def main():
    parser = _UpdaterParser()
    parser.add_argument("--old", required=True)
    parser.add_argument("--new", required=True)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--log", default=None)
    parser.add_argument("--removed", default=None)
    args = parser.parse_args()

    log_path = args.log
    old_path = Path(args.old)
    new_path = Path(args.new)
    staging = new_path.parent
    target_dir = old_path.parent

    _log(log_path, f"updater started, old={old_path}, new={new_path}, waiting pid={args.pid}")
    try:
        _wait_for_pid_exit(args.pid, timeout_sec=30, log_path=log_path)

        # ── Phase 1: 備份現有 _internal/ 與 exe ──
        have_internal_backup, internal_old = _backup(target_dir, "_internal", log_path)
        have_exe_backup, exe_old = _backup(target_dir, "GameTools_HealthMonitor.exe", log_path)

        # ── Phase 2: 整樹交換 ──
        if not _swap_tree(staging, target_dir, log_path):
            _log(log_path, "tree swap failed after all retries, rolling back")
            if have_internal_backup:
                _restore(target_dir, "_internal", internal_old, log_path)
            if have_exe_backup:
                _restore(target_dir, "GameTools_HealthMonitor.exe", exe_old, log_path)
            sys.exit(1)

        # ── Phase 2.5: 清除 delta 標記為 removed 的檔案 ──
        _delete_removed(target_dir, args.removed, log_path)

        # ── Phase 3: 清除備份 ──
        if have_internal_backup and internal_old.exists():
            shutil.rmtree(str(internal_old), ignore_errors=True)
        if have_exe_backup and exe_old.exists():
            try:
                exe_old.unlink()
            except OSError:
                pass

        _log(log_path, "tree swap success, relaunching old exe")
        try:
            subprocess.Popen([str(old_path)], cwd=str(old_path.parent))
        except Exception as e:
            _log(log_path, f"relaunch failed: {e}")

        _log(log_path, "updater finished successfully")
    finally:
        _cleanup_staging(staging, log_path)


def _demo():
    """self-check：驗證 _delete_removed 與 _cleanup_staging（含 temp_root 清理）。"""
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="gtool_update_demo_"))
    target = Path(tempfile.mkdtemp(prefix="target_"))
    log = tmp / "updater.log"

    # 佈置 staging 子目錄（模擬 delta 路徑：tmp/staging）
    staging = tmp / "staging"
    (staging / "_internal").mkdir(parents=True)
    (staging / "_internal" / "app.dll").write_bytes(b"new")
    (staging / "GameTools_HealthMonitor.exe").write_bytes(b"NEWMZ")
    (staging / "updater.exe").write_bytes(b"UPD")

    # 佈置 target：含將被 removed 的檔案與目錄
    (target / "_internal").mkdir()
    (target / "_internal" / "old_removed.dll").write_bytes(b"old")
    (target / "_internal" / "keep.dll").write_bytes(b"old")
    (target / "_internal" / "old_subdir").mkdir()
    (target / "_internal" / "old_subdir" / "x.bin").write_bytes(b"x")
    (target / "GameTools_HealthMonitor.exe").write_bytes(b"OLDMZ")
    (target / "config.json").write_bytes(b"{}")

    removed_file = tmp / "removed.json"
    removed_file.write_text(json.dumps(["_internal/old_removed.dll", "_internal/old_subdir/x.bin", "_internal/old_subdir"]), encoding="utf-8")

    # 模擬 swap（merge-copy）＋ _delete_removed
    shutil.copytree(str(staging), str(target), dirs_exist_ok=True)
    _delete_removed(target, removed_file, log)

    assert (target / "GameTools_HealthMonitor.exe").read_bytes() == b"NEWMZ", "exe 未覆蓋"
    assert (target / "_internal" / "app.dll").read_bytes() == b"new", "dll 未覆蓋"
    assert (target / "_internal" / "keep.dll").read_bytes() == b"old", "keep.dll 不應被動"
    assert not (target / "_internal" / "old_removed.dll").exists(), "removed 檔未刪除"
    assert not (target / "_internal" / "old_subdir").exists(), "removed 目錄未刪除"
    assert (target / "config.json").exists(), "旁置 config 應保留"

    # _cleanup_staging 應清掉整個 temp_root（但保留執行中的 updater.exe 之名稱）
    _cleanup_staging(staging, log)
    assert not (tmp / "staging").exists() or (tmp / "staging" / "updater.exe").exists(), "staging 清理異常"
    assert not (tmp / "removed.json").exists(), "temp_root 未清理 removed.json"

    shutil.rmtree(str(target), ignore_errors=True)
    shutil.rmtree(str(tmp), ignore_errors=True)
    print("updater_main self-check OK")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        _demo()
    else:
        main()

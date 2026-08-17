"""
updater_main.py
獨立更新程序 — 等待主程式退出 → 替換 EXE → 重啟
由 updater_core.apply_update() 啟動，請勿直接執行。
"""

import argparse
import ctypes
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


def _cleanup_staging(staging: Path, log_path):
    try:
        for _entry in staging.iterdir():
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
        staging.rmdir()
    except Exception:
        pass


def main():
    parser = _UpdaterParser()
    parser.add_argument("--old", required=True)
    parser.add_argument("--new", required=True)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--log", default=None)
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


if __name__ == "__main__":
    main()

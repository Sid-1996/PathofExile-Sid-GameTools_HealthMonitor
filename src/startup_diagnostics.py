"""啟動期診斷 — 必須在任何第三方／專案模組載入前就能運作，且自身不得造成二次失敗。

實測依據（Windows + PyInstaller --noconsole）：

- 打包版 `sys.stdout` / `sys.stderr` 皆為 `None`；沒有任何 handler 時 logging 會靜默丟棄
  紀錄（不拋例外）。因此「只掛 console handler」等同完全沒有日誌。
- 舊 `logging_setup` 只在 DEBUG 才掛檔案 handler → 正常啟動（WARNING）沒有任何落點，
  啟動期錯誤不會留下任何痕跡。
- `app.py` 的 PySide6 / config_manager / qt.main_window import 早於任何 logging 設定，
  這些 import 失敗時行程直接結束、無聲無痕。
- PySide6 6.12：Qt slot 內的未捕捉例外會走 `sys.excepthook`（實測確認），故無須另掛
  Qt message handler；背景 thread 的例外走 `threading.excepthook`，不經 sys.excepthook。

本模組僅依賴標準庫，提供：

- `log_dir()` / `log_path()`：不依賴目前工作目錄的日誌位置
  （`%LOCALAPPDATA%\\GameTools_HealthMonitor` → frozen 時 exe 同層 → TEMP 逐級降級）
- `bootstrap()`：一律掛 rotating file handler + 安裝 excepthook / threading.excepthook
- 未捕捉例外 → 完整 traceback 寫入 `startup_crash.log`、一次性錯誤提示（含日誌位置）後結束
- `write_smoke()` / `mark_smoke_ok()` / `mark_smoke_failed()`：frozen（--noconsole）版的
  `sys.stdout` 為 None，`print()` 的輸出會完全消失；smoke 的成功與失敗改以
  `smoke_result.txt`（與 gtools.log 同目錄、每次執行前覆寫）留下可讀證據。
"""

import logging
import logging.handlers
import os
import sys
import tempfile
import threading
import time
import traceback

_APP_DIR_NAME = "GameTools_HealthMonitor"
_LOG_NAME = "gtools.log"
_CRASH_LOG_NAME = "startup_crash.log"
_FORMAT = "%(asctime)s %(levelname)-7s [%(module)s:%(lineno)d] %(message)s"
_MAX_LOG_BYTES = 1_000_000
_MAX_CRASH_BYTES = 256 * 1024
_SMOKE_RESULT_NAME = "smoke_result.txt"
_DIALOG_TITLE = "GameTools Health Monitor"
# 標記本模組掛上的 handler，reset_for_tests() 才能只移除自己的
_HANDLER_TAG = "_gtools_diagnostics"

logger = logging.getLogger(__name__)

# 測試可替換：讓「結束行程」在測試中不真的發生
_exit = os._exit

_state = {"configured": False, "guards": False, "prompted": False, "handlers": [], "smoke_failed": False}


def bootstrap() -> None:
    """最早呼叫：建立日誌落點與全域例外攔截。任何失敗都不得外拋（診斷不得擋啟動）。"""
    try:
        configure_root_logging()
    except BaseException:  # ponytail: 診斷路徑不得因任何失敗而阻擋啟動
        pass
    try:
        install_guards()
    except BaseException:
        pass


def resolve_log_level(argv=None) -> int:
    """`--debug` 或 `GTOOLS_LOG_LEVEL=DEBUG` → DEBUG，其餘 WARNING。"""
    args = sys.argv if argv is None else argv
    if "--debug" in args:
        return logging.DEBUG
    if os.environ.get("GTOOLS_LOG_LEVEL", "").strip().upper() == "DEBUG":
        return logging.DEBUG
    return logging.WARNING


def _log_dir_candidates():
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    yield os.path.join(base, _APP_DIR_NAME)
    if getattr(sys, "frozen", False):
        try:
            yield os.path.dirname(os.path.abspath(sys.executable))
        except (OSError, AttributeError):
            pass
    yield os.path.join(tempfile.gettempdir(), _APP_DIR_NAME)


def _is_writable_dir(path: str) -> bool:
    probe = os.path.join(path, f".write_probe_{os.getpid()}")
    try:
        os.makedirs(path, exist_ok=True)
        with open(probe, "w", encoding="utf-8"):
            pass
        os.remove(probe)
        return True
    except OSError:
        return False


def log_dir() -> str:
    """第一個可寫入的日誌目錄；全部失敗時退回 TEMP（永不外拋、永不依賴 cwd）。"""
    seen = set()
    for candidate in _log_dir_candidates():
        key = os.path.normcase(os.path.abspath(candidate))
        if key in seen:
            continue
        seen.add(key)
        if _is_writable_dir(candidate):
            return candidate
    return tempfile.gettempdir()


def log_path() -> str:
    return os.path.join(log_dir(), _LOG_NAME)


def configure_root_logging(level: int | None = None) -> logging.Handler | None:
    """掛上 rotating file handler（一律）與 console handler（僅在有 console 時）。冪等。

    回傳檔案 handler；無法建立時回傳 None。永不外拋：診斷機制不得造成啟動失敗。
    """
    if _state["configured"]:
        return _state["handlers"][0] if _state["handlers"] else None
    _state["configured"] = True

    if level is None:
        level = resolve_log_level()
    root = logging.getLogger()
    root.setLevel(level)
    formatter = logging.Formatter(_FORMAT)

    # 檔案 handler 一律掛：打包版 stderr 為 None，沒有它就等於沒有日誌
    try:
        file_handler = logging.handlers.RotatingFileHandler(log_path(), maxBytes=_MAX_LOG_BYTES, backupCount=2, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        setattr(file_handler, _HANDLER_TAG, True)
        root.addHandler(file_handler)
        _state["handlers"].append(file_handler)
    except Exception:  # ponytail: 診斷路徑不得因寫檔失敗而中斷啟動
        file_handler = None

    if sys.stdout is not None or sys.stderr is not None:
        stream = logging.StreamHandler(sys.stdout if sys.stdout is not None else sys.stderr)
        stream.setFormatter(formatter)
        stream.setLevel(level)
        setattr(stream, _HANDLER_TAG, True)
        root.addHandler(stream)
        _state["handlers"].append(stream)

    return file_handler


def write_crash(kind: str, text: str) -> str | None:
    """把完整 traceback 追加寫入 `startup_crash.log`；失敗回 None（永不外拋）。"""
    path = os.path.join(log_dir(), _CRASH_LOG_NAME)
    try:
        try:
            if os.path.getsize(path) > _MAX_CRASH_BYTES:
                os.replace(path, path + ".old")
        except OSError:
            pass
        body = text if text.endswith("\n") else text + "\n"
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} {kind} =====\n")
            fh.write(f"pid={os.getpid()} frozen={bool(getattr(sys, 'frozen', False))} exe={sys.executable}\n")
            fh.write(f"argv={sys.argv!r}\n")
            fh.write(body)
        return path
    except Exception:  # ponytail: 診斷路徑不得因寫檔失敗而中斷
        return None


def smoke_result_path() -> str:
    """smoke 結果檔路徑：與 gtools.log 同目錄（使用者資料目錄），不依賴 cwd。"""
    return os.path.join(log_dir(), _SMOKE_RESULT_NAME)


def reset_smoke_result() -> None:
    """清空 smoke 結果檔：每次 smoke 執行前呼叫，只保留最新一次結果。"""
    try:
        with open(smoke_result_path(), "w", encoding="utf-8"):
            pass
    except Exception:  # ponytail: 診斷路徑不得因寫檔失敗而中斷啟動
        pass


def write_smoke(text: str) -> None:
    """smoke 輸出：echo 到 stdout（開發模式）+ 追加到結果檔（frozen 模式 stdout 為 None）。

    結果檔是 frozen --smoke 唯一的可觀測出口；寫入失敗不得影響流程。
    """
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {str(text).rstrip()}"
    try:
        if sys.stdout is not None:
            print(line)
    except Exception:
        pass
    try:
        with open(smoke_result_path(), "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
    except Exception:  # ponytail: 診斷路徑不得因寫檔失敗而中斷啟動
        pass


def mark_smoke_ok() -> None:
    """標記 smoke 成功（已失敗則不再標記成功）。"""
    if _state["smoke_failed"]:
        return
    write_smoke("SMOKE RESULT: OK")


def mark_smoke_failed(reason: str) -> None:
    """標記 smoke 失敗（同一行程只寫一次，避免重複輸出）。"""
    if _state["smoke_failed"]:
        return
    _state["smoke_failed"] = True
    write_smoke(f"SMOKE FAILED: {reason}")


def _prompt_text(summary: str, log_file: str | None) -> str:
    lines = [
        "發生未預期的錯誤，程式已停止。",
        "Unexpected error - the program has stopped.",
        "",
        f"錯誤 / Error: {summary}",
        "",
    ]
    if log_file:
        lines.append("詳細記錄 / Full traceback:")
        lines.append(log_file)
        lines.append("請把這個檔案回報給開發者 / Please send this file to the developer.")
    else:
        lines.append("無法寫入日誌檔（Unable to write log file）。")
    return "\n".join(lines)


def _show_message_box(title: str, text: str) -> bool:
    """用 Win32 MessageBoxW 顯示：不依賴 Qt（Qt 本身可能就是失敗原因）。"""
    try:
        import ctypes

        _MB_ICONERROR = 0x10
        _MB_SETFOREGROUND = 0x10000
        ctypes.windll.user32.MessageBoxW(None, text, title, _MB_ICONERROR | _MB_SETFOREGROUND)
        return True
    except Exception:
        return False


def prompt_once(summary: str, log_file: str | None = None) -> bool:
    """簡潔的一次性錯誤提示（同一行程只顯示一次、不阻塞自動化）。永不外拋。"""
    if _state["prompted"]:
        return False
    _state["prompted"] = True
    if "--smoke" in sys.argv:
        return False  # 自動化 smoke 驗證不得被 modal 視窗卡住
    return _show_message_box(_DIALOG_TITLE, _prompt_text(summary, log_file))


def _flush_logging() -> None:
    for handler in logging.getLogger().handlers:
        try:
            handler.flush()
        except BaseException:  # ponytail: 診斷路徑不得因 handler 失敗而中斷
            pass


def _graceful_exit(code: int) -> None:
    """先讓既有緊急關閉流程清理資源，再強制結束行程。"""
    try:
        from utils import emergency_exit_handler

        emergency_exit_handler()  # 正常情況不會返回（內含 os._exit）
    except BaseException:
        pass
    try:
        logging.shutdown()
    except Exception:
        pass
    _exit(code)


def report_uncaught(exc_type, exc_value, exc_tb, context: str = "未捕捉的例外", exit_code: int = 1) -> None:
    """完整 traceback 進日誌與 crash 檔 → 一次性提示 → 結束行程。

    記錄失敗不影響結束流程；診斷本身不得把錯誤變成「無聲結束」。
    """
    text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    try:
        logger.critical("%s: %s: %s\n%s", context, exc_type.__name__, exc_value, text)
    except BaseException:
        pass
    try:
        crash_path = write_crash(f"{context}: {exc_type.__name__}: {exc_value}", text)
    except BaseException:  # ponytail: 寫檔失敗不得吃掉提示與結束流程
        crash_path = None
    try:
        # smoke 模式下 stdout 不可用，失敗結果必須寫入結果檔才看得到
        if "--smoke" in sys.argv:
            mark_smoke_failed(f"{exc_type.__name__}: {exc_value}")
    except BaseException:
        pass
    try:
        prompt_once(f"{exc_type.__name__}: {exc_value}", crash_path)
    except BaseException:
        pass
    _flush_logging()
    _graceful_exit(exit_code)


def _sys_excepthook(exc_type, exc_value, exc_tb) -> None:
    try:
        report_uncaught(exc_type, exc_value, exc_tb, "未捕捉的例外")
    except BaseException:
        pass
    _exit(1)


def _thread_excepthook(args) -> None:
    """背景 thread 的未捕捉例外：留完整 traceback，不彈窗、不結束行程。

    GUI 主執行緒仍可使用；直接殺行程會讓使用者失去還原資料的機會。
    SystemExit 與 threading 預設行為一致，靜默忽略。
    """
    if getattr(args, "exc_type", None) is None or args.exc_type is SystemExit:
        return
    text = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
    name = getattr(getattr(args, "thread", None), "name", "?")
    try:
        logger.error("執行緒 %s 未捕捉的例外: %s\n%s", name, args.exc_value, text)
    except Exception:
        pass
    write_crash(f"執行緒未捕捉例外（{name}）", text)


def install_guards() -> None:
    """安裝 sys.excepthook / threading.excepthook（冪等；Qt slot 例外也走 sys.excepthook）。"""
    if _state["guards"]:
        return
    _state["guards"] = True
    sys.excepthook = _sys_excepthook
    threading.excepthook = _thread_excepthook


def reset_for_tests() -> None:
    """僅供測試：清除冪等狀態並移除本模組掛上的 handler。"""
    root = logging.getLogger()
    for handler in _state["handlers"]:
        try:
            root.removeHandler(handler)
            handler.close()
        except Exception:
            pass
    _state["handlers"].clear()
    _state.update(configured=False, guards=False, prompted=False, smoke_failed=False)


if __name__ == "__main__":
    # self-check：路徑選擇、traceback 完整性、提示去重、thread hook 不結束行程
    import shutil

    tmp = tempfile.mkdtemp()
    _orig_localappdata = os.environ.get("LOCALAPPDATA")
    _orig_exe = sys.executable
    try:
        os.environ["LOCALAPPDATA"] = tmp
        if hasattr(sys, "frozen"):
            delattr(sys, "frozen")
        reset_for_tests()

        expected = os.path.join(tmp, _APP_DIR_NAME)
        assert log_dir() == expected, f"log_dir 應為 {expected}"
        assert log_path() == os.path.join(expected, _LOG_NAME), "log_path 組合錯誤"

        # cwd 不影響日誌位置
        old_cwd = os.getcwd()
        os.chdir(tmp)
        try:
            assert log_dir() == expected, "log_dir 不應依賴 cwd"
        finally:
            os.chdir(old_cwd)

        # frozen 且 LOCALAPPDATA 不可寫 → 退回 exe 同層
        os.environ["LOCALAPPDATA"] = os.path.join(tmp, "nul", "x")
        setattr(sys, "frozen", True)
        exe_dir = os.path.join(tmp, "exe")
        os.makedirs(exe_dir)
        sys.executable = os.path.join(exe_dir, "app.exe")
        assert log_dir() == exe_dir, f"frozen 應退回 exe 同層，得到 {log_dir()}"
        delattr(sys, "frozen")
        reset_for_tests()

        # 檔案 handler 一律掛上且冪等
        os.environ["LOCALAPPDATA"] = tmp
        handler = configure_root_logging(logging.WARNING)
        assert handler is not None and os.path.exists(log_path()), "檔案 handler 未建立"
        assert configure_root_logging(logging.WARNING) is handler, "重複呼叫應冪等"
        logger.error("self-check 錯誤訊息")
        assert "self-check 錯誤訊息" in open(log_path(), encoding="utf-8").read(), "錯誤未寫入日誌"

        # traceback 完整保留
        try:
            raise ValueError("boom-xyz")
        except ValueError:
            exc_type, exc_value, exc_tb = sys.exc_info()
        crash = write_crash("self-check", "".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
        assert crash is not None, "crash 檔未建立"
        body = open(crash, encoding="utf-8").read()
        assert "Traceback (most recent call last)" in body and "boom-xyz" in body, "traceback 不完整"

        # 提示只顯示一次，且 --smoke 下不顯示
        calls = []
        globals()["_show_message_box"] = lambda title, text: calls.append(text) or True
        assert prompt_once("x", crash) and not prompt_once("x", crash), "提示去重失效"
        reset_for_tests()
        sys.argv += ["--smoke"]
        assert not prompt_once("y", crash), "--smoke 不應彈窗"
        sys.argv.remove("--smoke")
        reset_for_tests()

        # thread hook：留痕但不結束行程
        exited = []
        globals()["_exit"] = lambda code: exited.append(code)
        try:
            raise RuntimeError("thread-boom")
        except RuntimeError:
            _thread_excepthook(threading.ExceptHookArgs((*sys.exc_info(), threading.current_thread())))
        assert not exited, "thread hook 不應結束行程"
        assert "thread-boom" in open(os.path.join(log_dir(), _CRASH_LOG_NAME), encoding="utf-8").read(), "thread 例外未留痕"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        sys.executable = _orig_exe
        if _orig_localappdata is not None:
            os.environ["LOCALAPPDATA"] = _orig_localappdata
        else:
            os.environ.pop("LOCALAPPDATA", None)
        os.environ.pop("GTOOLS_LOG_LEVEL", None)

    print("startup_diagnostics self-check OK")

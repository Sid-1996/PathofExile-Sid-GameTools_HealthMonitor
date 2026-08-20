"""
Capture utility functions extracted from health_monitor.py.

背景截圖：優先使用 Windows Graphics Capture (WGC) 抓「指定視窗」的內容——
即使該視窗被其他視窗遮擋或不在前景，仍能正確取得遊戲畫面（GUI 在前景時預覽不失真）。
WGC 不可用（Win<1903 / 獨佔全螢幕 / 初始化失敗）時，自動降級 mss（僅在前景才正確）。
"""

import os
import threading
import time

import mss
import numpy as np
from PIL import Image
import pygetwindow as gw

from inventory_utils import normalize_region
from utils import get_app_dir

try:
    import cv2

    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import windows_capture as _wc

    WGC_AVAILABLE = True
except ImportError:
    _wc = None  # type: ignore[assignment]
    WGC_AVAILABLE = False

# 新建立 WGC session 首張 frame 的等待上限（frame 非同步到達，未就緒時降級 mss 只能在前景）
WGC_FIRST_FRAME_WAIT = 1.0


class _MssSingleton:
    _local = threading.local()
    _lock = threading.Lock()

    def __enter__(self):
        if not hasattr(self._local, "instance"):
            with self._lock:
                if not hasattr(self._local, "instance"):
                    self._local.instance = mss.mss()
        return self._local.instance

    def __exit__(self, *args):
        pass


_mss_singleton = _MssSingleton()


def capture_region_to_cv2(monitor_dict):
    if not CV2_AVAILABLE:
        raise ImportError("OpenCV (cv2) is required for capture_region_to_cv2")
    with _mss_singleton as sct:
        screenshot = sct.grab(monitor_dict)
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)  # pyright: ignore
    return img


class _WgcWindowSession:
    """單一 HWND 的 WGC 背景截圖 session：事件線程存放最新 frame，讀取端取用。

    Windows.Graphics.Capture 對「被遮擋/失焦」的視窗仍可正確取得內容；
    對「最小化」的視窗無法渲染 → 無 frame（由 typed return 決定呼叫端行為）。
    """

    _COPY_INTERVAL = 0.03  # 節流：最多每 30ms 複製一次全幅 frame（遊戲可能 60-144fps 送 frame）

    def __init__(self, hwnd):
        self._hwnd = hwnd
        self._lock = threading.Lock()
        self._frame = None
        self._closed = False
        self._last_store = 0.0
        self._control = None
        self._first_frame = threading.Event()
        self._start()

    def _start(self):
        if _wc is None:  # pragma: no cover - 僅 WGC_AVAILABLE=True 時才會進到這裡
            raise RuntimeError("WGC unavailable")
        cap = _wc.WindowsCapture(cursor_capture=False, draw_border=False, window_hwnd=self._hwnd)

        @cap.event
        def on_frame_arrived(frame, ctrl):  # noqa: ARG001 - frame 事件回呼簽名由套件要求
            now = time.time()
            if now - self._last_store < self._COPY_INTERVAL:
                return
            self._last_store = now
            bgr = frame.frame_buffer[:, :, :3].copy()  # 脫離 native buffer 生命週期
            with self._lock:
                self._frame = bgr
            self._first_frame.set()

        @cap.event
        def on_closed():
            self._closed = True

        self._control = cap.start_free_threaded()

    def latest_frame(self):
        with self._lock:
            return self._frame

    def wait_first_frame(self, timeout):
        """等待首張 frame 就緒；逾時回傳 False（之後沿用既有降級路徑）。"""
        return self._first_frame.wait(timeout)

    def is_closed(self):
        return self._closed

    def stop(self):
        ctrl = self._control
        if ctrl is not None:
            try:
                ctrl.stop()
            except Exception:
                pass


_wgc_sessions = {}
_wgc_sessions_lock = threading.Lock()


def _get_wgc_session(hwnd):
    """依 hwnd 取得（或建立）WGC session；window 重開/關閉後自動重建。"""
    with _wgc_sessions_lock:
        session = _wgc_sessions.get(hwnd)
        if session is not None and not session.is_closed():
            return session
        if session is not None:
            _wgc_sessions.pop(hwnd, None)
        try:
            session = _WgcWindowSession(hwnd)
            _wgc_sessions[hwnd] = session
        except Exception as e:
            print(f"[WARN] WGC 初始化失敗，降級 mss: {e}")
            return None
        session.wait_first_frame(WGC_FIRST_FRAME_WAIT)
        return session


def shutdown_background_capture():
    """關閉所有 WGC session（app 關閉時呼叫，避免非 daemon 線程殘留）。"""
    with _wgc_sessions_lock:
        sessions = list(_wgc_sessions.values())
        _wgc_sessions.clear()
    for s in sessions:
        s.stop()


def _scale_region(frame_shape, window, region):
    """把 window-relative 的 region 依 frame 實際尺寸縮放/夾取（DPI 或邊框差異時防呆）。"""
    fh, fw = frame_shape[:2]
    if fh <= 0 or fw <= 0:
        return None
    sx = fw / window.width if window.width else 1.0
    sy = fh / window.height if window.height else 1.0
    x = max(0, min(int(round(region["x"] * sx)), fw))
    y = max(0, min(int(round(region["y"] * sy)), fh))
    w = max(1, min(int(round(region["width"] * sx)), fw - x))
    h = max(1, min(int(round(region["height"] * sy)), fh - y))
    return x, y, w, h


def capture_window_region_bgr(window_title, region):
    """背景截圖指定視窗的區域。回傳 ("wgc", bgr_img) / ("mss", bgr_img) / None。

    - "wgc"：WGC 成功（視窗被遮擋/失焦也正確）。
    - "mss"：mss 成功（僅在視窗為前景時走，避免截到遮擋內容）。
    - None ：視窗不存在 / 最小化 / 無法截圖。
    """
    region = normalize_region(region)
    if region is None:
        return None
    windows = gw.getWindowsWithTitle(window_title)
    if not windows:
        return None
    window = windows[0]
    if window.isMinimized:
        return None
    hwnd = window._hWnd

    if WGC_AVAILABLE:
        session = _get_wgc_session(hwnd)
        frame = session.latest_frame() if session is not None else None
        if frame is not None:
            scaled = _scale_region(frame.shape, window, region)
            if scaled is not None:
                x, y, w, h = scaled
                return ("wgc", frame[y : y + h, x : x + w])
        # WGC session 存在但暫無 frame（獨佔全螢幕等）→ 視窗為前景才降 mss
    if window.isActive:
        monitor = {
            "top": window.top + region["y"],
            "left": window.left + region["x"],
            "width": region["width"],
            "height": region["height"],
        }
        img = capture_region_to_cv2(monitor)
        return ("mss", img)
    return None


def capture_window_region_pil(window_title, region):
    """背景截圖指定視窗的區域，回傳 (backend, PIL Image) 或 (None, None)。"""
    result = capture_window_region_bgr(window_title, region)
    if result is None:
        return None, None
    backend, bgr = result
    return backend, Image.fromarray(np.ascontiguousarray(bgr[:, :, ::-1]), "RGB")


def save_screenshot(pil_img, filename, subdir="screenshots"):
    path = os.path.join(get_app_dir(), subdir, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pil_img.save(path)
    return path


def load_screenshot_from_file(filename, subdir="screenshots"):
    path = os.path.join(get_app_dir(), subdir, filename)
    if os.path.exists(path):
        return Image.open(path)
    return None


if __name__ == "__main__":
    import tempfile

    tmp = tempfile.mkdtemp()
    old_app_dir = get_app_dir
    try:

        def get_app_dir():  # noqa: F811
            return tmp

        img = Image.new("RGB", (8, 8), (255, 0, 0))
        path = save_screenshot(img, "t.png")
        assert os.path.exists(path), "save_screenshot failed"
        loaded = load_screenshot_from_file("t.png")
        assert loaded is not None and loaded.size == (8, 8), "roundtrip failed"
        assert load_screenshot_from_file("missing.png") is None, "missing file -> None"
    finally:
        get_app_dir = old_app_dir  # noqa: F811

    class _FakeWindow:
        width = 1920
        height = 1080

    # scale=1（無 DPI 差異）時 region 原樣對應
    r = _scale_region((1080, 1920, 3), _FakeWindow(), {"x": 0, "y": 0, "width": 100, "height": 20})
    assert r == (0, 0, 100, 20), f"scale=1 mapping {r}"
    # 縮放（frame 比 window 大 2x）與夾取
    r2 = _scale_region((2160, 3840, 3), _FakeWindow(), {"x": -5, "y": 0, "width": 2000, "height": 3000})
    assert r2 == (0, 0, 3840, 2160), f"scale+clamp {r2}"
    # 空 region / 無效 frame
    assert _scale_region((0, 0, 3), _FakeWindow(), {"x": 0, "y": 0, "width": 10, "height": 10}) is None, "zero frame -> None"
    assert capture_window_region_bgr("__no_such_window_zzz__", {"x": 0, "y": 0, "width": 10, "height": 10}) is None, "missing window -> None"
    assert capture_window_region_bgr("__no_such_window_zzz__", None) is None, "None region -> None"
    # PIL 轉換：BGR numpy -> RGB PIL
    bgr = np.zeros((4, 4, 3), dtype=np.uint8)
    bgr[:, :, 0] = 255  # 藍
    pil = Image.fromarray(bgr[:, :, ::-1], "RGB")
    assert pil.getpixel((0, 0)) == (0, 0, 255), "BGR->RGB channel order"
    print("capture_utils self-check OK")

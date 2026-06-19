"""
Capture utility functions extracted from health_monitor.py.
"""
import os
import threading
import mss
import numpy as np
from PIL import Image
import pygetwindow as gw

from utils import get_app_dir

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


class _MssSingleton:
    _instance = None
    _lock = threading.Lock()
    def __enter__(self):
        if self._instance is None:
            with self._lock:
                if self._instance is None:
                    self._instance = mss.mss()
        return self._instance
    def __exit__(self, *args):
        pass


_mss_singleton = _MssSingleton()


def capture_region_to_pil(monitor_dict):
    with _mss_singleton as sct:
        screenshot = sct.grab(monitor_dict)
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
    return img


def capture_region_to_cv2(monitor_dict):
    if not CV2_AVAILABLE:
        raise ImportError("OpenCV (cv2) is required for capture_region_to_cv2")
    with _mss_singleton as sct:
        screenshot = sct.grab(monitor_dict)
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)  # pyright: ignore
    return img


def build_game_window_monitor(window_title, region_coords):
    window = gw.getWindowsWithTitle(window_title)[0]
    x, y, w, h = region_coords
    abs_x = window.left + x
    abs_y = window.top + y
    return {"top": abs_y, "left": abs_x, "width": w, "height": h}


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

"""Health/mana analysis and trigger logic for Path of Exile game tools.

This module contains analysis functions extracted from health_monitor.py:
- HSV-based health bar analysis
- HSV-based mana bar analysis
- Dominant color detection via kmeans
- Trigger condition evaluation and action execution
- Interruptible sleep for responsive thread interruption

All functions are designed to be self-contained, accepting callbacks and
configuration values as parameters rather than depending on a class instance.
"""

import time
import cv2
import numpy as np


_last_printed_health = None

def analyze_health(img, is_health_color_fn, get_health_color_ratio_fn, health_threshold):
    """Analyze health percentage from an image region using 18 equally-spaced detection positions."""
    global _last_printed_health
    height = img.shape[0]
    detection_positions = [0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5, 0.45, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1]

    health_count = 0
    debug_info = []

    for i, pos_percent in enumerate(detection_positions):
        y_center = int(height * (1 - pos_percent))
        sample_height = 5
        y_start = max(0, y_center - sample_height // 2)
        y_end = min(height, y_center + sample_height // 2)
        segment = img[y_start:y_end, :]
        is_health = is_health_color_fn(segment)
        debug_info.append(f"血量檢測點{i+1} ({int(pos_percent*100)}%): Y範圍[{y_start}-{y_end}], 有血量色彩: {is_health}")
        if is_health:
            health_count += 1

    if health_count >= 16:
        bottom_half_start = height // 2
        bottom_segment = img[bottom_half_start:height, :]
        bottom_ratio = get_health_color_ratio_fn(bottom_segment)
        core_start = int(height * 0.3)
        core_end = int(height * 0.7)
        core_segment = img[core_start:core_end, :]
        core_ratio = get_health_color_ratio_fn(core_segment)

        is_full_blood = False
        if bottom_ratio > (health_threshold * 0.6):
            is_full_blood = True
            debug_info.append(f"滿血檢測1：下半部血量比例 {bottom_ratio:.3f} > 0.6閾值")
        elif core_ratio > (health_threshold * 0.5) and health_count >= 16:
            is_full_blood = True
            debug_info.append(f"滿血檢測2：核心區域 {core_ratio:.3f} > 0.5閾值，{health_count}個檢測點有血量")
        elif health_count == 18:
            is_full_blood = True
            debug_info.append("滿血檢測3：所有18個檢測點都有血量")
        if is_full_blood:
            health_count = 18

    result = (health_count / 18) * 100
    if health_count >= 6 and result != _last_printed_health:
        _last_printed_health = result
        print(f"血量分析結果: {result:.1f}%")
        for info in debug_info:
            print(info)
    return result


def is_health_color(segment, red_saturation_min, red_value_min, red_h_range,
                    green_h_range, green_saturation_min, green_value_min, health_threshold):
    """Check if a pixel segment is primarily health color (red/green)."""
    hsv = cv2.cvtColor(segment, cv2.COLOR_BGR2HSV)

    lower_red1 = np.array([0, red_saturation_min, red_value_min])
    upper_red1 = np.array([red_h_range, 255, 255])
    lower_red2 = np.array([170, red_saturation_min, red_value_min])
    upper_red2 = np.array([180, 255, 255])

    lower_green = np.array([green_h_range, green_saturation_min, green_value_min])
    upper_green = np.array([green_h_range + 40, 255, 255])

    red_mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    red_mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    green_mask = cv2.inRange(hsv, lower_green, upper_green)

    red_pixels = np.count_nonzero(red_mask1 | red_mask2)
    green_pixels = np.count_nonzero(green_mask)
    total_pixels = segment.shape[0] * segment.shape[1]

    health_ratio = (red_pixels + green_pixels) / total_pixels
    return health_ratio > health_threshold


def get_health_color_ratio(segment, red_saturation_min, red_value_min, red_h_range,
                           green_h_range, green_saturation_min, green_value_min):
    """Get the proportion of health-colored pixels in a segment."""
    hsv = cv2.cvtColor(segment, cv2.COLOR_BGR2HSV)

    lower_red1 = np.array([0, red_saturation_min, red_value_min])
    upper_red1 = np.array([red_h_range, 255, 255])
    lower_red2 = np.array([170, red_saturation_min, red_value_min])
    upper_red2 = np.array([180, 255, 255])

    lower_green = np.array([green_h_range, green_saturation_min, green_value_min])
    upper_green = np.array([green_h_range + 40, 255, 255])

    red_mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    red_mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    green_mask = cv2.inRange(hsv, lower_green, upper_green)

    red_pixels = np.count_nonzero(red_mask1 | red_mask2)
    green_pixels = np.count_nonzero(green_mask)
    total_pixels = segment.shape[0] * segment.shape[1]

    return (red_pixels + green_pixels) / total_pixels


_last_printed_mana = None

def analyze_mana(img, is_mana_color_fn, get_mana_color_ratio_fn):
    """Analyze mana percentage from an image region using 18 equally-spaced detection positions."""
    global _last_printed_mana
    height = img.shape[0]
    detection_positions = [0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5, 0.45, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1]

    mana_count = 0
    debug_info = []

    for i, pos_percent in enumerate(detection_positions):
        y_center = int(height * (1 - pos_percent))
        sample_height = 5
        y_start = max(0, y_center - sample_height // 2)
        y_end = min(height, y_center + sample_height // 2)
        segment = img[y_start:y_end, :]
        is_mana = is_mana_color_fn(segment)
        debug_info.append(f"魔力檢測點{i+1} ({int(pos_percent*100)}%): Y範圍[{y_start}-{y_end}], 有魔力色彩: {is_mana}")
        if is_mana:
            mana_count += 1

    if mana_count >= 16:
        bottom_half_start = height // 2
        bottom_segment = img[bottom_half_start:height, :]
        bottom_ratio = get_mana_color_ratio_fn(bottom_segment)

        core_start = int(height * 0.3)
        core_end = int(height * 0.7)
        core_segment = img[core_start:core_end, :]
        core_ratio = get_mana_color_ratio_fn(core_segment)

        is_full_mana = False
        if bottom_ratio > 0.4:
            is_full_mana = True
            debug_info.append(f"滿魔力檢測1：下半部魔力比例 {bottom_ratio:.3f} > 0.4閾值")
        elif core_ratio > 0.3 and mana_count >= 16:
            is_full_mana = True
            debug_info.append(f"滿魔力檢測2：核心區域 {core_ratio:.3f} > 0.3閾值，{mana_count}個檢測點有魔力")
        elif mana_count == 18:
            is_full_mana = True
            debug_info.append("滿魔力檢測3：所有18個檢測點都有魔力")
        if is_full_mana:
            mana_count = 18

    result = (mana_count / 18) * 100
    if mana_count >= 6 and result != _last_printed_mana:
        _last_printed_mana = result
        print(f"魔力分析結果: {result:.1f}%")
        for info in debug_info:
            print(info)
    return result


def is_mana_color(segment):
    """Check if a pixel segment is primarily mana color (blue)."""
    hsv = cv2.cvtColor(segment, cv2.COLOR_BGR2HSV)
    lower_blue = np.array([90, 50, 50])
    upper_blue = np.array([130, 255, 255])
    blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
    blue_pixels = np.count_nonzero(blue_mask)
    total_pixels = segment.shape[0] * segment.shape[1]
    mana_ratio = blue_pixels / total_pixels
    return mana_ratio > 0.3


def get_mana_color_ratio(segment):
    """Get the proportion of mana-colored (blue) pixels in a segment."""
    hsv = cv2.cvtColor(segment, cv2.COLOR_BGR2HSV)
    lower_blue = np.array([90, 50, 50])
    upper_blue = np.array([130, 255, 255])
    blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
    blue_pixels = np.count_nonzero(blue_mask)
    total_pixels = segment.shape[0] * segment.shape[1]
    return blue_pixels / total_pixels


def get_main_color(img):
    """Get the dominant color of an image using k-means clustering."""
    pixels = img.reshape(-1, 3)
    pixels = np.float32(pixels)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    K = 3
    _, labels, centers = cv2.kmeans(pixels, K, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    centers = np.uint8(centers)
    dominant_color = centers[np.argmax(np.bincount(labels.flatten()))]
    return f"RGB({dominant_color[2]}, {dominant_color[1]}, {dominant_color[0]})"


def check_triggers(health_percent, mana_percent, config, last_trigger_times,
                   get_text_fn, is_interface_ui_visible_fn, window_title,
                   interface_ui_region, interface_ui_screenshot):
    """檢查當前應該觸發哪個設定（優先顯示最低百分比的設定）"""
    if interface_ui_region and interface_ui_screenshot is not None:
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(window_title)
            if windows:
                game_window = windows[0]
                if not is_interface_ui_visible_fn(game_window):
                    return get_text_fn("interface_ui_not_detected")
            else:
                return get_text_fn("game_window_not_found_for_ui_check")
        except Exception as e:
            return f"{get_text_fn('interface_ui_check_failed')}: {str(e)}"

    health_settings = []
    mana_settings = []

    for setting in config.get('settings', []):
        setting_type = setting.get('type', 'HP')
        if setting_type == 'HP':
            health_settings.append(setting)
        else:
            mana_settings.append(setting)

    health_settings.sort(key=lambda x: x['percent'])
    mana_settings.sort(key=lambda x: x['percent'])

    if health_settings:
        for setting in health_settings:
            if health_percent <= setting['percent']:
                cooldown = setting.get('cooldown', 500)
                last_trigger = last_trigger_times.get(setting['percent'], 0)
                current_time = time.time()
                if current_time - last_trigger >= cooldown / 1000:
                    return get_text_fn("trigger_health").format(percent=setting['percent'], key=setting['key'])
                else:
                    remaining = cooldown - (current_time - last_trigger) * 1000
                    return get_text_fn("cooldown_health").format(percent=setting['percent'], key=setting['key'], remaining=f"{remaining:.0f}")

    if mana_percent is not None and mana_settings:
        for setting in mana_settings:
            if mana_percent <= setting['percent']:
                cooldown = setting.get('cooldown', 500)
                last_trigger = last_trigger_times.get(f"mana_{setting['percent']}", 0)
                current_time = time.time()
                if current_time - last_trigger >= cooldown / 1000:
                    return get_text_fn("trigger_mana").format(percent=setting['percent'], key=setting['key'])
                else:
                    remaining = cooldown - (current_time - last_trigger) * 1000
                    return get_text_fn("cooldown_mana").format(percent=setting['percent'], key=setting['key'], remaining=f"{remaining:.0f}")

    return get_text_fn("normal")


def trigger_actions(health_percent, mana_percent, config, last_trigger_times,
                    multi_trigger, add_status_message_fn, get_text_fn,
                    is_interface_ui_visible_fn, press_key_sequence_fn,
                    window_title, interface_ui_region, interface_ui_screenshot):
    """根據血量/魔力百分比觸發對應的快捷鍵動作，優先處理低百分比設定"""
    if interface_ui_region and interface_ui_screenshot is not None:
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(window_title)
            if windows:
                game_window = windows[0]
                if not is_interface_ui_visible_fn(game_window):
                    print(f"血魔檢查: 介面UI不存在，不在戰鬥狀態，跳過治療動作 (血量:{health_percent}%, 魔力:{mana_percent}%)")
                    return
                else:
                    print("血魔檢查: 介面UI存在，正在戰鬥狀態，繼續執行治療動作")
            else:
                print("血魔檢查: 找不到遊戲視窗，跳過介面UI檢查")
        except Exception as e:
            print(f"血魔檢查: 介面UI檢查失敗: {e}，繼續執行治療動作")
    else:
        print("血魔檢查: 未設定介面UI區域，跳過戰鬥狀態檢查")

    health_settings = []
    mana_settings = []

    for setting in config.get('settings', []):
        setting_type = setting.get('type', 'HP')
        if setting_type == 'HP':
            health_settings.append(setting)
        else:
            mana_settings.append(setting)

    health_settings.sort(key=lambda x: x['percent'])
    mana_settings.sort(key=lambda x: x['percent'])

    if health_settings:
        for setting in health_settings:
            if health_percent <= setting['percent']:
                cooldown = setting.get('cooldown', 500)
                last_trigger = last_trigger_times.get(setting['percent'], 0)
                current_time = time.time()
                time_diff = current_time - last_trigger

                print(f" 血量觸發檢查: {health_percent}% <= {setting['percent']}% (設定閾值)")
                print(f" 冷卻檢查: 上次觸發時間 {time_diff:.3f}秒前, 需要冷卻 {cooldown/1000:.1f}秒")

                if time_diff >= cooldown / 1000:
                    try:
                        print(f"[OK] 準備觸發: 血量{setting['percent']}%, 按鍵{setting['key']}")
                        add_status_message_fn(get_text_fn("health_low_triggered").format(percent=setting['percent'], key=setting['key']), "monitor")
                        press_key_sequence_fn(setting['key'], setting['percent'])
                        print(f" 已完成按鍵序列: {setting['key']}")
                    except Exception as e:
                        print(f"[ERROR] 按鍵觸發失敗: {e}")
                else:
                    remaining = cooldown - (time_diff) * 1000
                    print(f"冷卻中: 還需等待 {remaining:.0f}ms")

                if not multi_trigger:
                    print(" 單一觸發模式: 停止檢查其他設定")
                    break
                else:
                    print(" 多重觸發模式: 繼續檢查其他設定")

    if mana_percent is not None and mana_settings:
        for setting in mana_settings:
            if mana_percent <= setting['percent']:
                cooldown = setting.get('cooldown', 500)
                last_trigger = last_trigger_times.get(f"mana_{setting['percent']}", 0)
                current_time = time.time()
                if current_time - last_trigger >= cooldown / 1000:
                    try:
                        add_status_message_fn(get_text_fn("mana_low_triggered").format(percent=setting['percent'], key=setting['key']), "monitor")
                        press_key_sequence_fn(setting['key'], f"mana_{setting['percent']}")
                    except Exception:
                        pass
                else:
                    remaining = cooldown - (current_time - last_trigger) * 1000

                if not multi_trigger:
                    break

    return None


def interruptible_sleep(duration, is_monitoring_fn, interval=0.01):
    """可中斷的睡眠函數，能夠快速響應停止信號"""
    start_time = time.time()
    while is_monitoring_fn() and (time.time() - start_time) < duration:
        time.sleep(interval)

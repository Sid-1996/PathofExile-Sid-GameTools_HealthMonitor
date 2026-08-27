"""Inventory utility functions for Path of Exile game tools.

This module contains inventory analysis functions extracted from health_monitor.py:
- should_clear_inventory: Check if inventory grid has occupied slots
- find_inventory_items: Find occupied item positions in inventory
- calculate_inventory_grid_positions: Compute grid cell positions

All functions are pure (no tkinter dependency).
"""

import numpy as np

from typing import Dict, Optional, cast


def normalize_region(region: object) -> Optional[Dict[str, int]]:
    """把 region 正規化為 dict {x, y, width, height}（容錯 tuple/list/dict，None 保留）。"""
    if region is None:
        return None
    if isinstance(region, dict):
        return cast(Dict[str, int], region)
    if isinstance(region, (tuple, list)) and len(region) == 4:
        return {"x": region[0], "y": region[1], "width": region[2], "height": region[3]}
    return None


def should_clear_inventory(img, empty_inventory_colors, inventory_grid_positions, inventory_region, skip_slots=None, current_slot=None):
    """檢查背包是否需要清空 - 檢查60個格子，可選擇跳過指定格子和之前的格子"""
    inventory_region = normalize_region(inventory_region)
    if not empty_inventory_colors or not inventory_grid_positions or not inventory_region:
        return False, []

    occupied_slots = []
    for i, (pos_x, pos_y) in enumerate(inventory_grid_positions):
        if current_slot is not None and i <= current_slot:
            continue

        if skip_slots is not None and i in skip_slots:
            continue

        if i >= len(empty_inventory_colors):
            continue

        img_x = pos_x - inventory_region["x"]
        img_y = pos_y - inventory_region["y"]

        if 0 <= img_x < img.shape[1] and 0 <= img_y < img.shape[0]:
            x1 = max(0, img_x - 10)
            y1 = max(0, img_y - 10)
            x2 = min(img.shape[1], img_x + 10)
            y2 = min(img.shape[0], img_y + 10)

            cell_pixels = img[y1:y2, x1:x2]
            if cell_pixels.size > 0:
                avg_color = np.mean(cell_pixels, axis=(0, 1))
                current_rgb = (int(avg_color[2]), int(avg_color[1]), int(avg_color[0]))

                baseline_rgb = empty_inventory_colors[i]
                color_diff = sum(abs(a - b) for a, b in zip(current_rgb, baseline_rgb))

                if color_diff > 15:
                    occupied_slots.append(i)

    return len(occupied_slots) > 0, occupied_slots


def find_inventory_items(img, empty_inventory_colors, inventory_grid_positions, inventory_region, skip_slots=None, current_slot=None):
    """分析圖片並找到有物品的格子位置"""
    inventory_region = normalize_region(inventory_region)
    _, occupied_indices = should_clear_inventory(img, empty_inventory_colors, inventory_grid_positions, inventory_region, skip_slots, current_slot)
    occupied_positions = []
    for index in occupied_indices:
        if index < len(inventory_grid_positions):
            occupied_positions.append(inventory_grid_positions[index])
    return occupied_positions


def calculate_inventory_grid_positions(inventory_region, grid_offset_x=0, grid_offset_y=0):
    """計算背包格子位置 (5x12 布局，總共60個格子)"""
    inventory_region = normalize_region(inventory_region)
    if not inventory_region:
        return []

    region_width = inventory_region["width"]
    region_height = inventory_region["height"]
    region_x = inventory_region["x"]
    region_y = inventory_region["y"]

    cols = 12
    rows = 5

    cell_width = region_width / cols
    cell_height = region_height / rows

    positions = []
    for row in range(rows):
        for col in range(cols):
            center_x = (col + 0.5) * cell_width + grid_offset_x
            center_y = (row + 0.5) * cell_height + grid_offset_y

            abs_x = int(region_x + center_x)
            abs_y = int(region_y + center_y)

            positions.append((abs_x, abs_y))

    return positions


if __name__ == "__main__":
    region = {"x": 0, "y": 0, "width": 120, "height": 50}
    positions = calculate_inventory_grid_positions(region)
    assert len(positions) == 60, f"expected 60 slots, got {len(positions)}"
    assert positions[0] == (5, 5), f"first slot {positions[0]}"
    assert positions[59] == (115, 45), f"last slot {positions[59]}"
    assert calculate_inventory_grid_positions(None) == [], "None region -> []"
    assert normalize_region((0, 0, 120, 50)) == region, "tuple -> dict"
    assert normalize_region([0, 0, 120, 50]) == region, "list -> dict"
    assert normalize_region(region) is region, "dict passthrough"
    assert normalize_region(None) is None, "None passthrough"
    print("inventory_utils self-check OK")

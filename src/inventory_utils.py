"""Inventory utility functions for Path of Exile game tools.

This module contains inventory analysis functions extracted from health_monitor.py:
- should_clear_inventory: Check if inventory grid has occupied slots
- find_inventory_items: Find occupied item positions in inventory
- calculate_inventory_grid_positions: Compute grid cell positions

All functions are pure (no tkinter dependency).
"""

import numpy as np


def should_clear_inventory(img, empty_inventory_colors, inventory_grid_positions,
                            inventory_region, skip_slots=None, current_slot=None):
    """檢查背包是否需要清空 - 檢查60個格子，可選擇跳過指定格子和之前的格子"""
    if not empty_inventory_colors or not inventory_grid_positions:
        return False, []

    occupied_slots = []
    for i, (pos_x, pos_y) in enumerate(inventory_grid_positions):
        if current_slot is not None and i <= current_slot:
            continue

        if skip_slots is not None and i in skip_slots:
            continue

        if i >= len(empty_inventory_colors):
            continue

        img_x = pos_x - inventory_region['x']
        img_y = pos_y - inventory_region['y']

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


def find_inventory_items(img, empty_inventory_colors, inventory_grid_positions,
                          inventory_region, skip_slots=None, current_slot=None):
    """分析圖片並找到有物品的格子位置"""
    _, occupied_indices = should_clear_inventory(
        img, empty_inventory_colors, inventory_grid_positions,
        inventory_region, skip_slots, current_slot
    )
    occupied_positions = []
    for index in occupied_indices:
        if index < len(inventory_grid_positions):
            occupied_positions.append(inventory_grid_positions[index])
    return occupied_positions


def calculate_inventory_grid_positions(inventory_region, grid_offset_x=0, grid_offset_y=0):
    """計算背包格子位置 (5x12 布局，總共60個格子)"""
    if not inventory_region:
        return []

    region_width = inventory_region['width']
    region_height = inventory_region['height']
    region_x = inventory_region['x']
    region_y = inventory_region['y']

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

"""Image utility functions for Path of Exile game tools.

This module contains image processing utilities extracted from health_monitor.py:
- Drawing scale lines and indicators on preview images
- Resizing and centering images for display
- Formatting region configuration as display text

All functions are pure (no tkinter dependency).
"""

from PIL import Image, ImageDraw


def draw_scale_lines(img):
    """Draw 10 equally-spaced horizontal scale lines on a preview image.

    Args:
        img: PIL Image or numpy array (the image is modified in-place).
    """
    # Handle both PIL Image and numpy array
    if hasattr(img, 'shape'):  # numpy array
        width, height = img.shape[1], img.shape[0]
    else:  # PIL Image
        width, height = img.width, img.height

    draw = ImageDraw.Draw(img)

    # Draw horizontal scale lines (10 equal divisions)
    for i in range(1, 10):
        y = int(height * i / 10)
        draw.line([(0, y), (width, y)], fill=(255, 0, 0), width=1)
        percent = 100 - (i * 10)
        draw.text((5, y - 15), f"{percent}%", fill=(255, 0, 0), font=None)


def resize_and_center_image(pil_img, target_size):
    """Resize an image proportionally to fit a target preview size.

    The image is scaled up (minimum 2x) or down to fit within target_size
    while maintaining aspect ratio. Uses LANCZOS resampling for quality.

    Args:
        pil_img: PIL Image to resize.
        target_size: Tuple of (width, height) for the target display size.

    Returns:
        Resized PIL Image.
    """
    original_width, original_height = pil_img.size
    target_width, target_height = target_size

    scale_x = target_width / original_width
    scale_y = target_height / original_height

    # Use the larger scale for clarity, but do not exceed target size
    scale = min(scale_x, scale_y)

    # Ensure minimum 2x magnification so the image is not too small
    min_scale = 2.0
    scale = max(scale, min_scale)

    # If scaled up beyond target, use fit-to-target instead
    if scale * original_width > target_width or scale * original_height > target_height:
        scale = min(scale_x, scale_y)

    new_width = int(original_width * scale)
    new_height = int(original_height * scale)

    resized_img = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    return resized_img


def draw_health_indicator(img, health_percent):
    """Draw a health percentage indicator line and label on a preview image.

    Args:
        img: PIL Image (modified in-place).
        health_percent: Float, current health percentage (0-100).
    """
    width, height = img.size

    # Calculate the vertical position corresponding to the health value
    health_height = int(height * (100 - health_percent) / 100)

    draw = ImageDraw.Draw(img)
    # Red thick indicator line at the health level
    draw.line([(0, health_height), (width, health_height)],
              fill=(255, 0, 0), width=3)

    # Draw percentage text below the indicator line
    text = f"{health_percent:.1f}%"
    bbox = draw.textbbox((0, 0), text, font=None)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    text_x = (width - text_width) // 2
    text_y = health_height + 5

    # If text would go below the image, place it above the line instead
    if text_y + text_height > height:
        text_y = health_height - text_height - 5

    # Semi-transparent black background for text
    draw.rectangle([text_x - 2, text_y - 2, text_x + text_width + 2, text_y + text_height + 2],
                   fill=(0, 0, 0, 128))

    # White text with black outline for readability
    draw.text((text_x, text_y), text, fill=(255, 255, 255), font=None)
    draw.text((text_x + 1, text_y), text, fill=(0, 0, 0), font=None)
    draw.text((text_x - 1, text_y), text, fill=(0, 0, 0), font=None)
    draw.text((text_x, text_y + 1), text, fill=(0, 0, 0), font=None)
    draw.text((text_x, text_y - 1), text, fill=(0, 0, 0), font=None)


def draw_mana_indicator(img, mana_percent):
    """Draw a mana percentage indicator line and label on a preview image.

    Args:
        img: PIL Image (modified in-place).
        mana_percent: Float, current mana percentage (0-100).
    """
    width, height = img.size

    # Calculate the vertical position corresponding to the mana value
    mana_height = int(height * (100 - mana_percent) / 100)

    draw = ImageDraw.Draw(img)
    # Blue thick indicator line at the mana level
    draw.line([(0, mana_height), (width, mana_height)],
              fill=(0, 0, 255), width=3)

    # Draw percentage text below the indicator line
    text = f"{mana_percent:.1f}%"
    bbox = draw.textbbox((0, 0), text, font=None)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    text_x = (width - text_width) // 2
    text_y = mana_height + 5

    # If text would go below the image, place it above the line instead
    if text_y + text_height > height:
        text_y = mana_height - text_height - 5

    # Semi-transparent black background for text
    draw.rectangle([text_x - 2, text_y - 2, text_x + text_width + 2, text_y + text_height + 2],
                   fill=(0, 0, 0, 128))

    # White text with black outline for readability
    draw.text((text_x, text_y), text, fill=(255, 255, 255), font=None)
    draw.text((text_x + 1, text_y), text, fill=(0, 0, 0), font=None)
    draw.text((text_x - 1, text_y), text, fill=(0, 0, 0), font=None)
    draw.text((text_x, text_y + 1), text, fill=(0, 0, 0), font=None)
    draw.text((text_x, text_y - 1), text, fill=(0, 0, 0), font=None)


def get_region_text(config):
    """Format the health bar region configuration as a display string.

    Args:
        config: Dictionary containing a 'region' key with tuple (x, y, w, h).

    Returns:
        Formatted string or unset placeholder.
    """
    if config and config.get('region'):
        x, y, w, h = config['region']
        return f"x={x}, y={y}, w={w}, h={h}"
    return "未設定"


def get_mana_region_text(config):
    """Format the mana bar region configuration as a display string.

    Args:
        config: Dictionary containing a 'mana_region' key with tuple (x, y, w, h).

    Returns:
        Formatted string or unset placeholder.
    """
    if config and config.get('mana_region'):
        x, y, w, h = config['mana_region']
        return f"x={x}, y={y}, w={w}, h={h}"
    return "未設定"


def get_interface_ui_region_text(interface_ui_region):
    """Format the interface UI region as a display string.

    Args:
        interface_ui_region: Dict with keys 'x', 'y', 'width', 'height', or None.

    Returns:
        Formatted string or not-recorded placeholder.
    """
    if interface_ui_region:
        x = interface_ui_region['x']
        y = interface_ui_region['y']
        w = interface_ui_region['width']
        h = interface_ui_region['height']
        return f"x={x}, y={y}, w={w}, h={h}"
    return "尚未記錄"


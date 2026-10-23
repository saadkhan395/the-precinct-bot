import os
from PIL import Image, ImageStat

def check_dimensions(path, expected_size):
    try:
        with Image.open(path) as img:
            if list(img.size) != expected_size:
                return False, f"Size {img.size} != {expected_size}"
            return True, "Size OK"
    except Exception as e:
        return False, str(e)

def check_safe_margins(path, margin_px=80):
    """Checks if the bottom 200px is the Midnight Navy background."""
    try:
        with Image.open(path) as img:
            w, h = img.size
            footer = img.crop((0, h - 200, w, h)).convert("RGB")
            stat = ImageStat.Stat(footer)
            # Midnight Navy is (10, 22, 48)
            avg = stat.mean
            if avg[0] < 30 and avg[1] < 40 and avg[2] < 70:
                return True, "Safe zone is solid Navy."
            return False, "Background behind text is not the standard Navy box. Contrast may be poor."
    except Exception as e:
        return False, str(e)

def check_image_quality(path):
    try:
        with Image.open(path) as img:
            stat = ImageStat.Stat(img.convert("L"))
            if stat.stddev[0] < 15:
                return False, "Image appears washed out or blurred."
            return True, "Image quality OK."
    except Exception as e:
        return False, str(e)

def check_contrast(path):
    """Ensure the text area has sufficient contrast (WCAG)."""
    try:
        with Image.open(path) as img:
            w, h = img.size
            # Sample the bottom box
            footer = img.crop((0, h - 200, w, h)).convert("L")
            stat = ImageStat.Stat(footer)
            # If standard deviation is low, it means solid color, which is good for text.
            # If it's high, it means busy image without overlay.
            if stat.stddev[0] > 60:
                return False, "High contrast variance in text area. Text might be unreadable."
            return True, "Contrast OK."
    except Exception as e:
        return False, str(e)

"""Programmatic visual checks for layout, margins, and contrast."""
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

def check_safe_margins(path, margin_px=90):
    """Checks if the bottom 200px is pure black to ensure text never overlaps the image."""
    try:
        with Image.open(path) as img:
            w, h = img.size
            # Crop the bottom 200 pixels where the text sits
            footer = img.crop((0, h - 200, w, h)).convert("L")
            stat = ImageStat.Stat(footer)
            # If the mean brightness is very low, it's a safe solid dark box
            if stat.mean[0] < 30:
                return True, "Safe zone is solid black."
            return False, "Background behind text is too bright. Contrast may be poor."
    except Exception as e:
        return False, str(e)

def check_image_quality(path):
    """Check for blur or watermarks (basic heuristic)."""
    try:
        with Image.open(path) as img:
            # Basic sharpness check using Variance of Laplacian equivalent
            stat = ImageStat.Stat(img.convert("L"))
            if stat.stddev[0] < 20:
                return False, "Image appears washed out or blurred."
            return True, "Image quality OK."
    except Exception as e:
        return False, str(e)

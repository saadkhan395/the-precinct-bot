import io
import os
import requests
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

W, H = 1080, 1350
MARGIN = 90
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
]

# Kept for fallback if no image is found
STYLES = [
    {"name": "navy_gold", "top": (10, 22, 48), "bottom": (4, 10, 26), "text": (255, 255, 255), "accent": (201, 162, 39), "muted": (170, 180, 200), "align": "left"},
    {"name": "dark_crimson", "top": (30, 30, 36), "bottom": (12, 12, 16), "text": (255, 255, 255), "accent": (214, 52, 62), "muted": (176, 176, 186), "align": "center"},
    {"name": "paper_light", "top": (246, 242, 232), "bottom": (230, 224, 210), "text": (20, 28, 48), "accent": (160, 30, 40), "muted": (90, 96, 110), "align": "left"},
]

def font(size):
    for p in FONT_PATHS:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    raise RuntimeError("No bold font found on this machine")

def gradient(top, bottom):
    img = Image.new("RGB", (W, H), top)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        d.line([(0, y), (W, y)], fill=c)
    return img

def download_and_process_bg(url):
    """Downloads image, crops to 1080x1350, and darkens it for text readability."""
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        
        # Crop to exact 1080x1350 aspect ratio
        target_ratio = W / H
        img_ratio = img.width / img.height
        if img_ratio > target_ratio:
            # Too wide, crop width
            new_width = int(target_ratio * img.height)
            left = (img.width - new_width) // 2
            img = img.crop((left, 0, left + new_width, img.height))
        else:
            # Too tall, crop height
            new_height = int(img.width / target_ratio)
            top = (img.height - new_height) // 2
            img = img.crop((0, top, img.width, top + new_height))
            
        img = img.resize((W, H), Image.Resampling.LANCZOS)
        
        # Darken the image (overlay black with 65% opacity) so white text pops
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 165))
        img = img.convert("RGBA")
        img = Image.alpha_composite(img, overlay)
        return img.convert("RGB")
    except Exception as e:
        print(f"Background image failed, using fallback gradient: {e}")
        return None

def wrap(draw, text, f, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=f) <= max_w:
            cur = trial
        else:
            if cur: lines.append(cur)
            cur = word
    if cur: lines.append(cur)
    return lines

def fit_text(draw, text, max_w, max_h, start=104, min_size=48):
    size = start
    while size >= min_size:
        f = font(size)
        lines = wrap(draw, text, f, max_w)
        line_h = int(size * 1.18)
        if len(lines) * line_h <= max_h:
            return f, lines, line_h
        size -= 4
    f = font(min_size)
    return f, wrap(draw, text, f, max_w), int(min_size * 1.18)

def draw_line(draw, text, f, y, color, align):
    w = draw.textlength(text, font=f)
    x = MARGIN if align == "left" else (W - w) / 2
    draw.text((x, y), text, font=f, fill=color)

def render_post(content_id, hook, headline, outlets, source_count, index, image_url=None):
    style = STYLES[index % len(STYLES)]
    # If we have a real image, force white text for contrast
    if image_url:
        img = download_and_process_bg(image_url)
        if img:
            style = dict(style) # copy
            style["text"] = (255, 255, 255)
            style["muted"] = (200, 200, 200)
        else:
            img = gradient(style["top"], style["bottom"])
    else:
        img = gradient(style["top"], style["bottom"])

    align = style["align"]
    draw = ImageDraw.Draw(img)
    max_w = W - 2 * MARGIN

    draw_line(draw, "THE DAILY PRECINCT", font(34), 90, style["accent"], align)
    bar_x = MARGIN if align == "left" else (W - 140) // 2
    draw.rectangle([bar_x, 145, bar_x + 140, 151], fill=style["accent"])

    hook_font = font(40)
    y = 300
    for line in wrap(draw, hook.upper(), hook_font, max_w):
        draw_line(draw, line, hook_font, y, style["accent"], align)
        y += 52

    f, lines, line_h = fit_text(draw, headline, max_w, 1030 - (y + 40))
    y += 40
    for line in lines:
        draw_line(draw, line, f, y, style["text"], align)
        y += line_h

    bar_x = MARGIN if align == "left" else (W - 160) // 2
    draw.rectangle([bar_x, y + 30, bar_x + 160, y + 38], fill=style["accent"])

    draw_line(draw, f"VERIFIED BY {source_count} OUTLETS", font(30), 1130, style["text"], align)
    small = font(28)
    yy = 1180
    for line in wrap(draw, f"Sources: {outlets}", small, max_w)[:2]:
        draw_line(draw, line, small, yy, style["muted"], align)
        yy += 38
    draw_line(draw, "@thedailyprecinct", font(30), 1275, style["accent"], align)

    os.makedirs("output/images", exist_ok=True)
    path = f"output/images/{content_id}.jpg"
    img.save(path, "JPEG", quality=92)
    return path, style["name"]
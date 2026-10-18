import io
import os
import requests
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
MARGIN = 90
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
]

STYLES = [
    {"name": "navy_gold", "accent": (201, 162, 39), "text": (255, 255, 255), "muted": (170, 180, 200)},
    {"name": "dark_crimson", "accent": (214, 52, 62), "text": (255, 255, 255), "muted": (176, 176, 186)},
]

def font(size):
    for p in FONT_PATHS:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    raise RuntimeError("No bold font found")

def download_and_process_bg(url):
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        
        target_ratio = W / H
        img_ratio = img.width / img.height
        if img_ratio > target_ratio:
            new_width = int(target_ratio * img.height)
            left = (img.width - new_width) // 2
            img = img.crop((left, 0, left + new_width, img.height))
        else:
            new_height = int(img.width / target_ratio)
            top = (img.height - new_height) // 2
            img = img.crop((0, top, img.width, top + new_height))
            
        img = img.resize((W, H), Image.Resampling.LANCZOS)
        
        # Solid black box at the bottom, fade to black from the middle
        gradient = Image.new("L", (1, H))
        for y in range(H):
            if y < 650:
                gradient.putpixel((0, y), 0) # Clear at top
            elif y > 900:
                gradient.putpixel((0, y), 255) # Solid black at bottom
            else:
                alpha = int(255 * ((y - 650) / 250))
                gradient.putpixel((0, y), alpha)
                
        gradient = gradient.resize((W, H))
        black_bg = Image.new("RGB", (W, H), (0, 0, 0))
        img = Image.composite(black_bg, img, gradient)
        
        return img
    except Exception as e:
        print(f"Background image failed: {e}")
        return None

def wrap_centered(draw, text, f, max_w):
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

def fit_text_centered(draw, text, max_w, max_h, start=90, min_size=44):
    size = start
    while size >= min_size:
        f = font(size)
        lines = wrap_centered(draw, text, f, max_w)
        line_h = int(size * 1.15)
        if len(lines) * line_h <= max_h:
            return f, lines, line_h
        size -= 4
    f = font(min_size)
    return f, wrap_centered(draw, text, f, max_w), int(min_size * 1.15)

def draw_center(draw, text, f, y, color):
    w = draw.textlength(text, font=f)
    x = (W - w) / 2
    draw.text((x, y), text, font=f, fill=color)

def render_post(content_id, hook, headline, outlets, source_count, index, image_url=None):
    style = STYLES[index % len(STYLES)]
    max_w = W - 2 * MARGIN

    if image_url:
        img = download_and_process_bg(image_url)
    else:
        img = Image.new("RGB", (W, H), (10, 22, 48))
        draw = ImageDraw.Draw(img)
        for y in range(H):
            draw.line([(0, y), (W, y)], fill=(4, 10, 26))

    draw = ImageDraw.Draw(img)

    # Top Branding
    draw.text((MARGIN, 90), "THE DAILY PRECINCT", font=font(34), fill=style["accent"])
    draw.rectangle([MARGIN, 145, MARGIN + 140, 151], fill=style["accent"])

    # --- TEXT BLOCK (Anchored to the solid black bottom) ---
    
    # 1. The Hook (Red/Gold) placed at y=880
    hook_font = font(40)
    draw_center(draw, hook.upper(), hook_font, 880, style["accent"])

    # 2. The Main Headline (White) placed starting at y=950
    # Max height is 220px to guarantee it fits above the sources
    f, lines, line_h = fit_text_centered(draw, headline, max_w, 220, start=88, min_size=42)
    y = 950
    for line in lines:
        draw_center(draw, line, f, y, style["text"])
        y += line_h

    # 3. Bottom Info (Anchored to the very bottom)
    draw_center(draw, f"VERIFIED BY {source_count} OUTLETS", font(28), 1180, style["muted"])
    draw_center(draw, f"Sources: {outlets}", font(26), 1225, style["muted"])
    draw_center(draw, "@thedailyprecinct", font(30), 1280, style["accent"])

    os.makedirs("output/images", exist_ok=True)
    path = f"output/images/{content_id}.jpg"
    img.save(path, "JPEG", quality=92)
    return path, style["name"]

import io
import os
import requests
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
MARGIN = 90
MAX_W = W - (MARGIN * 2)  # 900px maximum text width

FONT_PATHS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]

STYLES = [
    {"name": "navy_gold", "accent": (220, 40, 40), "text": (255, 255, 255), "muted": (180, 180, 180)}, # Red accent
    {"name": "dark_crimson", "accent": (220, 40, 40), "text": (255, 255, 255), "muted": (180, 180, 180)},
]

def font(size):
    for p in FONT_PATHS:
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default()

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
        
        # Create the solid black box at the bottom (starting at y=850)
        draw = ImageDraw.Draw(img)
        draw.rectangle([(0, 850), (W, H)], fill=(0, 0, 0))
        
        return img
    except Exception as e:
        print(f"Background image failed: {e}")
        return Image.new("RGB", (W, H), (0, 0, 0))

def wrap_text(draw, text, f, max_w):
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

def draw_center(draw, text, f, y, color):
    w = draw.textlength(text, font=f)
    x = (W - w) / 2
    draw.text((x, y), text, font=f, fill=color)

def render_post(content_id, hook, headline, outlets, source_count, index, image_url=None):
    style = STYLES[index % len(STYLES)]
    img = download_and_process_bg(image_url) if image_url else Image.new("RGB", (W, H), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Top Branding
    draw.text((MARGIN, 90), "THE DAILY PRECINCT", font=font(34), fill=(255, 255, 255))
    draw.rectangle([MARGIN, 145, MARGIN + 140, 151], fill=style["accent"])

    # --- MIXED TYPOGRAPHY HEADLINE ---
    # Start text higher inside the black box (y=880)
    y_cursor = 880

    # 1. Hook (Red, large, exactly like the reference)
    hook_font = font(62) 
    hook_lines = wrap_text(draw, hook.upper(), hook_font, MAX_W)
    for line in hook_lines:
        draw_center(draw, line, hook_font, y_cursor, style["accent"])
        y_cursor += int(hook_font.size * 1.1)

    # 2. Headline (White, slightly smaller, no outlines)
    if headline:
        y_cursor += 15 # Add a gap
        head_font = font(54) 
        head_lines = wrap_text(draw, headline, head_font, MAX_W)
        for line in head_lines:
            draw_center(draw, line, head_font, y_cursor, style["text"])
            y_cursor += int(head_font.size * 1.15)

    # Bottom Info (Anchored to the very bottom)
    draw_center(draw, f"VERIFIED BY {source_count} OUTLETS", font(26), 1200, style["muted"])
    draw_center(draw, f"Sources: {outlets}", font(24), 1240, style["muted"])
    draw_center(draw, "@thedailyprecinct", font(28), 1290, style["text"])

    os.makedirs("output/images", exist_ok=True)
    path = f"output/images/{content_id}.jpg"
    img.save(path, "JPEG", quality=92)
    return path, style["name"]

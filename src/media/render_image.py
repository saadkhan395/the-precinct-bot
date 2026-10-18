import io
import os
import requests
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
MARGIN = 90
MAX_W = W - (MARGIN * 2)

FONT_PATHS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]

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
        
        # Solid black box from y=800 down
        draw = ImageDraw.Draw(img)
        draw.rectangle([(0, 800), (W, H)], fill=(0, 0, 0))
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

def draw_center(draw, text, f, y, color, stroke=0):
    w = draw.textlength(text, font=f)
    x = (W - w) / 2
    if stroke > 0:
        draw.text((x, y), text, font=f, fill=color, stroke_width=stroke, stroke_fill=(0,0,0))
    else:
        draw.text((x, y), text, font=f, fill=color)

def render_post(content_id, hook, headline, outlets, source_count, index, image_url=None):
    img = download_and_process_bg(image_url) if image_url else Image.new("RGB", (W, H), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Top Branding
    draw.text((MARGIN, 90), "THE DAILY PRECINCT", font=font(34), fill=(255, 255, 255))
    draw.rectangle([MARGIN, 145, MARGIN + 140, 151], fill=(220, 40, 40))

    # --- DYNAMIC LAYOUT ENGINE ---
    hook_font = font(58)
    head_font = font(48)
    
    hook_lines = wrap_text(draw, hook.upper(), hook_font, MAX_W)
    head_lines = wrap_text(draw, headline, head_font, MAX_W)
    
    elements = []
    # Red Hook
    for l in hook_lines:
        elements.append({"text": l, "font": hook_font, "color": (220, 40, 40), "stroke": 3, "h": int(hook_font.size * 1.15)})
        
    # Gap
    if hook_lines and head_lines:
        elements.append({"text": "", "font": head_font, "color": (0,0,0), "stroke": 0, "h": 20})
        
    # White Headline
    for l in head_lines:
        elements.append({"text": l, "font": head_font, "color": (255, 255, 255), "stroke": 2, "h": int(head_font.size * 1.15)})

    total_h = sum(e["h"] for e in elements)
    
    # Center the block mathematically inside the 800-1150 zone (350px high)
    start_y = 800 + (350 - total_h) // 2
    
    y_cursor = start_y
    for e in elements:
        if e["text"]:
            draw_center(draw, e["text"], e["font"], y_cursor, e["color"], e["stroke"])
        y_cursor += e["h"]

    # Bottom Info (Anchored safely below the text block)
    draw_center(draw, f"VERIFIED BY {source_count} OUTLETS", font(26), 1180, (170, 170, 170))
    draw_center(draw, f"Sources: {outlets}", font(24), 1225, (170, 170, 170))
    draw_center(draw, "@thedailyprecinct", font(28), 1280, (220, 40, 40))

    os.makedirs("output/images", exist_ok=True)
    path = f"output/images/{content_id}.jpg"
    img.save(path, "JPEG", quality=92)
    return path, "editorial"

def render_carousel(cid, copy, outlets, source_count, index):
    # Placeholder to avoid import errors in make_carousel_post.py if called
    return [], "editorial"

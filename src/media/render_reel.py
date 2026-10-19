import os
import requests
import io
from PIL import Image, ImageDraw, ImageFont

RW, RH = 1080, 1920
MARGIN = 90
MAX_W = RW - (MARGIN * 2)
BOX_TOP = 1250 # Where the black box starts on vertical video

FONT_PATHS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]

PACING = [
    {"name": "quick", "hook": 2.5, "headline": 4.0, "fact": 3.5, "sources": 3.0, "cta": 3.0},
    {"name": "standard", "hook": 3.0, "headline": 5.0, "fact": 4.5, "sources": 3.5, "cta": 3.5},
]

def font(size):
    for p in FONT_PATHS:
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def download_vertical_bg(url):
    """Downloads image and crops to 1080x1920 with solid black bottom."""
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        
        target_ratio = RW / RH
        img_ratio = img.width / img.height
        if img_ratio > target_ratio:
            new_width = int(target_ratio * img.height)
            left = (img.width - new_width) // 2
            img = img.crop((left, 0, left + new_width, img.height))
        else:
            new_height = int(img.width / target_ratio)
            top = (img.height - new_height) // 2
            img = img.crop((0, top, img.width, top + new_height))
            
        img = img.resize((RW, RH), Image.Resampling.LANCZOS)
        
        # Solid black box at the bottom
        draw = ImageDraw.Draw(img)
        draw.rectangle([(0, BOX_TOP), (RW, RH)], fill=(0, 0, 0))
        return img
    except Exception as e:
        print(f"Reel image failed: {e}")
        return Image.new("RGB", (RW, RH), (10, 10, 10))

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
    x = (RW - w) / 2
    if stroke > 0:
        draw.text((x, y), text, font=f, fill=color, stroke_width=stroke, stroke_fill=(0,0,0))
    else:
        draw.text((x, y), text, font=f, fill=color)

def base_frame(image_url=None):
    """Creates the base vertical frame with the image and black box."""
    if image_url:
        img = download_vertical_bg(image_url)
    else:
        img = Image.new("RGB", (RW, RH), (10, 10, 10))
        draw = ImageDraw.Draw(img)
        draw.rectangle([(0, BOX_TOP), (RW, RH)], fill=(0, 0, 0))
        
    draw = ImageDraw.Draw(img)
    # Top Branding
    draw.text((MARGIN, 120), "THE DAILY PRECINCT", font=font(40), fill=(255, 255, 255))
    draw.rectangle([MARGIN, 180, MARGIN + 150, 188], fill=(220, 40, 40))
    return img, draw

def draw_premium_text(draw, hook, headline, source_count, outlets):
    """Draws the premium red/white text inside the black box."""
    y_cursor = BOX_TOP + 60
    
    # Red Hook
    hook_font = font(64)
    for line in wrap_text(draw, hook.upper(), hook_font, MAX_W):
        draw_center(draw, line, hook_font, y_cursor, (220, 40, 40), stroke=3)
        y_cursor += int(hook_font.size * 1.15)
        
    y_cursor += 20 # Gap
    
    # White Headline
    head_font = font(52)
    for line in wrap_text(draw, headline, head_font, MAX_W):
        draw_center(draw, line, head_font, y_cursor, (255, 255, 255), stroke=2)
        y_cursor += int(head_font.size * 1.15)
        
    # Footer
    draw_center(draw, f"VERIFIED BY {source_count} OUTLETS", font(30), 1760, (180, 180, 180))
    draw_center(draw, f"Sources: {outlets}", font(28), 1810, (180, 180, 180))

def render_scenes(cid, copy, outlets, source_count, index, image_url=None):
    pace = PACING[index % len(PACING)]
    folder = f"output/reels/{cid}_frames"
    os.makedirs(folder, exist_ok=True)
    scenes = []

    def save(img, name, seconds):
        p = f"{folder}/{name}.png"
        img.save(p, "PNG")
        scenes.append((p, seconds))

    # Scene 1: Hook & Headline (Premium Layout)
    img, draw = base_frame(image_url)
    draw_premium_text(draw, copy["hook"], copy["cover_headline"], source_count, outlets)
    save(img, "s01_premium", pace["hook"] + pace["headline"])

    # Scene 2: Facts (Overlay text on the image)
    n = 2
    for s in copy["slides"]:
        for point in s["points"]:
            if n > 5:
                break
            img, draw = base_frame(image_url)
            # Re-use the premium text drawer for facts
            draw_premium_text(draw, s["title"], point, source_count, outlets)
            save(img, f"s{n:02d}_fact", pace["fact"])
            n += 1

    return scenes, "editorial", pace["name"], folder

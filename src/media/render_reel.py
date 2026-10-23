import os
import requests
import io
from PIL import Image, ImageDraw, ImageFont

RW, RH = 1080, 1920
MARGIN = 90
MAX_W = RW - (MARGIN * 2)
BOX_TOP = 1100 # Text safe zone for Reels
BOX_BOTTOM = 1600

C_BG = (10, 22, 48)
C_ACCENT = (201, 162, 39)
C_TEXT = (230, 235, 240)
C_MUTED = (140, 160, 180)

FONT_PATHS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]

PACING = [
    {"name": "quick", "hook": 3.0, "headline": 3.0, "fact": 4.0, "sources": 3.0, "cta": 3.0},
    {"name": "standard", "hook": 3.5, "headline": 4.0, "fact": 5.0, "sources": 3.5, "cta": 3.5},
]

def font(size):
    for p in FONT_PATHS:
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def download_vertical_bg(url):
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
        
        draw = ImageDraw.Draw(img)
        draw.rectangle([(0, BOX_TOP - 50), (RW, BOX_BOTTOM + 150)], fill=C_BG)
        return img
    except Exception:
        img = Image.new("RGB", (RW, RH), C_BG)
        draw = ImageDraw.Draw(img)
        draw.rectangle([(0, BOX_TOP - 50), (RW, BOX_BOTTOM + 150)], fill=C_BG)
        return img

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

def draw_center(draw, text, f, y, color, bg_color=None, padding_x=20, padding_y=10):
    w = draw.textlength(text, font=f)
    x = (RW - w) / 2
    if bg_color:
        draw.rectangle(
            [(x - padding_x, y - padding_y), (x + w + padding_x, y + f.size + padding_y)],
            fill=bg_color
        )
    draw.text((x, y), text, font=f, fill=color)

def base_frame(image_url):
    img = download_vertical_bg(image_url)
    draw = ImageDraw.Draw(img)
    draw.text((MARGIN, 150), "THE DAILY PRECINCT", font=font(40), fill=C_TEXT)
    draw.rectangle([MARGIN, 210, MARGIN + 150, 218], fill=C_ACCENT)
    return img, draw

def draw_premium_text(draw, hook, headline):
    hook_font = font(56)
    head_font = font(46)
    
    hook_lines = wrap_text(draw, hook.upper(), hook_font, MAX_W)
    head_lines = wrap_text(draw, headline, head_font, MAX_W)
    
    elements = []
    for l in hook_lines:
        elements.append({"text": l, "font": hook_font, "color": C_BG, "bg": C_ACCENT, "h": int(hook_font.size * 1.3)})
        
    if hook_lines and head_lines:
        elements.append({"text": "", "font": head_font, "color": C_BG, "bg": None, "h": 30})
        
    for l in head_lines:
        elements.append({"text": l, "font": head_font, "color": C_TEXT, "bg": None, "h": int(head_font.size * 1.4)})

    total_h = sum(e["h"] for e in elements)
    start_y = BOX_TOP + ((BOX_BOTTOM - BOX_TOP) - total_h) // 2
    
    y_cursor = start_y
    for e in elements:
        if e["text"]:
            draw_center(draw, e["text"], e["font"], y_cursor, e["color"], bg_color=e["bg"])
        y_cursor += e["h"]

def render_scenes(cid, copy, outlets, source_count, index, image_urls):
    pace = PACING[index % len(PACING)]
    folder = f"output/reels/{cid}_frames"
    os.makedirs(folder, exist_ok=True)
    scenes = []

    def save(img, name, seconds):
        p = f"{folder}/{name}.png"
        img.save(p, "PNG")
        scenes.append((p, seconds))

    img, draw = base_frame(image_urls[0])
    draw_premium_text(draw, copy["hook"], copy["cover_headline"])
    save(img, "s01_premium", pace["hook"] + pace["headline"])

    n = 2
    for i, s in enumerate(copy["slides"]):
        for point in s["points"]:
            if n > 3: break
            
            img_url = image_urls[n-1] if n-1 < len(image_urls) else image_urls[0]
            img, draw = base_frame(img_url)
            draw_premium_text(draw, s["title"], point)
            save(img, f"s{n:02d}_fact", pace["fact"])
            n += 1

    return scenes, "elite_editorial", pace["name"], folder

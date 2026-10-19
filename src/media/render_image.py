import io
import os
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1350
MARGIN = 90
MAX_W = W - (MARGIN * 2)
BOX_TOP = 800 

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
        
        bottom_box = img.crop((0, BOX_TOP, W, H))
        blurred = bottom_box.filter(ImageFilter.GaussianBlur(radius=20))
        img.paste(blurred, (0, BOX_TOP))
        
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_overlay = ImageDraw.Draw(overlay)
        draw_overlay.rectangle([(0, BOX_TOP), (W, H)], fill=(0, 0, 0, 150))
        
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
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

    draw.text((MARGIN, 90), "THE DAILY PRECINCT", font=font(34), fill=(255, 255, 255))
    draw.rectangle([MARGIN, 145, MARGIN + 140, 151], fill=(220, 40, 40))

    hook_font = font(58)
    head_font = font(48)
    
    hook_lines = wrap_text(draw, hook.upper(), hook_font, MAX_W)
    head_lines = wrap_text(draw, headline, head_font, MAX_W)
    
    elements = []
    for l in hook_lines:
        elements.append({"text": l, "font": hook_font, "color": (220, 40, 40), "stroke": 3, "h": int(hook_font.size * 1.15)})
        
    if hook_lines and head_lines:
        elements.append({"text": "", "font": head_font, "color": (0,0,0), "stroke": 0, "h": 20})
        
    for l in head_lines:
        elements.append({"text": l, "font": head_font, "color": (255, 255, 255), "stroke": 2, "h": int(head_font.size * 1.15)})

    total_h = sum(e["h"] for e in elements)
    start_y = BOX_TOP + (350 - total_h) // 2
    
    y_cursor = start_y
    for e in elements:
        if e["text"]:
            draw_center(draw, e["text"], e["font"], y_cursor, e["color"], e["stroke"])
        y_cursor += e["h"]

    draw_center(draw, f"VERIFIED BY {source_count} OUTLETS", font(26), 1180, (220, 220, 220))
    draw_center(draw, f"Sources: {outlets}", font(24), 1225, (220, 220, 220))
    draw_center(draw, "@thedailyprecinct", font(28), 1280, (220, 40, 40))

    os.makedirs("output/images", exist_ok=True)
    path = f"output/images/{content_id}.jpg"
    img.save(path, "JPEG", quality=92)
    return path, "editorial"

# --- LEGACY COMPATIBILITY FOR RENDER_CAROUSEL.PY ---
STYLES = [{"name": "editorial", "top": (10, 22, 48), "bottom": (4, 10, 26), "text": (255, 255, 255), "accent": (220, 40, 40), "muted": (170, 180, 200), "align": "left"}]

def gradient(top, bottom):
    img = Image.new("RGB", (W, H), top)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        d.line([(0, y), (W, y)], fill=c)
    return img

def wrap(draw, text, f, max_w):
    return wrap_text(draw, text, f, max_w)

def fit_text(draw, text, max_w, max_h, start=104, min_size=48):
    size = start
    while size >= min_size:
        f = font(size)
        lines = wrap_text(draw, text, f, max_w)
        line_h = int(size * 1.18)
        if len(lines) * line_h <= max_h:
            return f, lines, line_h
        size -= 4
    f = font(min_size)
    return f, wrap_text(draw, text, f, max_w), int(min_size * 1.18)

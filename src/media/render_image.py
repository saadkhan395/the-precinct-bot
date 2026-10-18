import io
import os
import requests
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
MARGIN = 90  # Strict left/right margin
MAX_W = W - (MARGIN * 2) # 900px maximum text width
FONT_PATHS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]

STYLES = [
    {"name": "navy_gold", "accent": (201, 162, 39), "text": (255, 255, 255), "muted": (170, 180, 200)},
    {"name": "dark_crimson", "accent": (214, 52, 62), "text": (255, 255, 255), "muted": (176, 176, 186)},
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
        
        # Gradient: Clear at top, solid black at bottom for text
        gradient = Image.new("L", (1, H))
        for y in range(H):
            if y < 650: gradient.putpixel((0, y), 0)
            elif y > 900: gradient.putpixel((0, y), 255)
            else: gradient.putpixel((0, y), int(255 * ((y - 650) / 250)))
                
        gradient = gradient.resize((W, H))
        black_bg = Image.new("RGB", (W, H), (0, 0, 0))
        return Image.composite(black_bg, img, gradient)
    except Exception as e:
        print(f"Background image failed: {e}")
        return None

def fit_text(text, max_w, start_size, min_size=30):
    """Finds the largest font size that fits within the max width and wraps."""
    size = start_size
    while size >= min_size:
        f = font(size)
        # We use a dummy draw to measure
        dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        lines, cur = [], ""
        for word in text.split():
            trial = (cur + " " + word).strip()
            if dummy.textlength(trial, font=f) <= max_w:
                cur = trial
            else:
                if cur: lines.append(cur)
                cur = word
        if cur: lines.append(cur)
        if len(lines) <= 2: # Allow max 2 lines for headline
            return f, lines
        size -= 4
    return font(min_size), [text]

def draw_center(draw, text, f, y, color):
    w = draw.textlength(text, font=f)
    draw.text(((W - w) / 2, y), text, font=f, fill=color)

def render_post(content_id, hook, headline, outlets, source_count, index, image_url=None):
    style = STYLES[index % len(STYLES)]
    img = download_and_process_bg(image_url) if image_url else Image.new("RGB", (W, H), (10, 22, 48))
    draw = ImageDraw.Draw(img)

    # Top Branding
    draw.text((MARGIN, 90), "THE DAILY PRECINCT", font=font(34), fill=style["accent"])
    draw.rectangle([MARGIN, 145, MARGIN + 140, 151], fill=style["accent"])

    # Hook (Strict wrapping)
    hook_f, hook_lines = fit_text(hook.upper(), MAX_W, start_size=44, min_size=30)
    y = 780
    for line in hook_lines:
        draw_center(draw, line, hook_f, y, style["accent"])
        y += int(hook_f.size * 1.2)

    # Headline (Strict wrapping)
    head_f, head_lines = fit_text(headline, MAX_W, start_size=90, min_size=46)
    y = 880
    for line in head_lines:
        draw_center(draw, line, head_f, y, style["text"])
        y += int(head_f.size * 1.15)

    # Sources & Footer
    draw_center(draw, f"VERIFIED BY {source_count} OUTLETS", font(28), 1180, style["muted"])
    draw_center(draw, f"Sources: {outlets}", font(26), 1225, style["muted"])
    draw_center(draw, "@thedailyprecinct", font(30), 1280, style["accent"])

    os.makedirs("output/images", exist_ok=True)
    path = f"output/images/{content_id}.jpg"
    img.save(path, "JPEG", quality=92)
    return path, style["name"]

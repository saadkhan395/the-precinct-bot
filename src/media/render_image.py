import io
import os
import requests
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
MARGIN = 90
MAX_W = W - (MARGIN * 2)  # 900px maximum text width
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
        
        # Premium Bottom Gradient
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

def draw_center(draw, text, f, y, color, stroke_width=0):
    w = draw.textlength(text, font=f)
    x = (W - w) / 2
    if stroke_width > 0:
        draw.text((x, y), text, font=f, fill=color, stroke_width=stroke_width, stroke_fill=(0,0,0))
    else:
        draw.text((x, y), text, font=f, fill=color)

def render_post(content_id, hook, headline, outlets, source_count, index, image_url=None):
    style = STYLES[index % len(STYLES)]
    img = download_and_process_bg(image_url) if image_url else Image.new("RGB", (W, H), (10, 22, 48))
    draw = ImageDraw.Draw(img)

    # Top Branding
    draw.text((MARGIN, 90), "THE DAILY PRECINCT", font=font(34), fill=style["accent"])
    draw.rectangle([MARGIN, 145, MARGIN + 140, 151], fill=style["accent"])

    # --- MIXED TYPOGRAPHY HEADLINE ---
    # Split headline into Kicker (first 4 words) and Rest (remaining words)
    words = headline.split()
    kicker_text = " ".join(words[:4]).upper()
    rest_text = " ".join(words[4:])

    y_cursor = 820

    # 1. Draw Kicker (Large, Red, Outlined)
    kicker_font = font(64) # Large font
    # Wrap kicker if it's too wide
    kicker_lines = wrap_text(draw, kicker_text, kicker_font, MAX_W)
    for line in kicker_lines:
        draw_center(draw, line, kicker_font, y_cursor, style["accent"], stroke_width=3)
        y_cursor += int(kicker_font.size * 1.1)

    # 2. Draw Rest of Headline (Smaller, White, Outlined)
    if rest_text:
        y_cursor += 10 # Add a little gap
        head_font = font(52) # Smaller font
        head_lines = wrap_text(draw, rest_text, head_font, MAX_W)
        for line in head_lines:
            draw_center(draw, line, head_font, y_cursor, style["text"], stroke_width=2)
            y_cursor += int(head_font.size * 1.15)

    # Bottom Info (Anchored to the very bottom)
    draw_center(draw, f"VERIFIED BY {source_count} OUTLETS", font(28), 1180, style["muted"])
    draw_center(draw, f"Sources: {outlets}", font(26), 1225, style["muted"])
    draw_center(draw, "@thedailyprecinct", font(30), 1280, style["accent"])

    os.makedirs("output/images", exist_ok=True)
    path = f"output/images/{content_id}.jpg"
    img.save(path, "JPEG", quality=92)
    return path, style["name"]

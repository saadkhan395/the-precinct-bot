import io
import os
import requests
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
MARGIN = 90
MAX_W = W - (MARGIN * 2)
SPLIT_Y = 780 # The exact pixel where the black box starts

FONT_PATHS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]

def font(size):
    for p in FONT_PATHS:
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def download_and_process_bg(url):
    """Downloads image, crops to exactly 1080x780 (no bleed)."""
    if not url:
        return Image.new("RGB", (W, SPLIT_Y), (10, 10, 10))
        
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        
        # Crop to the exact top block aspect ratio
        target_ratio = W / SPLIT_Y
        img_ratio = img.width / img.height
        if img_ratio > target_ratio:
            new_width = int(target_ratio * img.height)
            left = (img.width - new_width) // 2
            img = img.crop((left, 0, left + new_width, img.height))
        else:
            new_height = int(img.width / target_ratio)
            top = (img.height - new_height) // 2
            img = img.crop((0, top, img.width, top + new_height))
            
        img = img.resize((W, SPLIT_Y), Image.Resampling.LANCZOS)
        return img
    except Exception as e:
        print(f"Background image failed: {e}")
        return Image.new("RGB", (W, SPLIT_Y), (10, 10, 10))

def draw_centered_text(draw, text, f, y, color, bg_color=None, padding_x=20, padding_y=10):
    """Draws text, optionally with a solid background block (like the red highlight)."""
    # Calculate text width
    w = draw.textlength(text, font=f)
    x = (W - w) / 2
    
    # Draw background box if requested
    if bg_color:
        draw.rectangle(
            [(x - padding_x, y - padding_y), (x + w + padding_x, y + f.size + padding_y)],
            fill=bg_color
        )
        
    # Draw text
    draw.text((x, y), text, font=f, fill=color)

def render_post(content_id, hook, headline, outlets, source_count, index, image_url=None):
    # 1. Create the base canvas and paste the strict top image
    img = Image.new("RGB", (W, H), (0, 0, 0))
    top_img = download_and_process_bg(image_url)
    img.paste(top_img, (0, 0))
    
    draw = ImageDraw.Draw(img)

    # 2. Top Branding (Over the image)
    draw.text((MARGIN, 90), "THE DAILY PRECINCT", font=font(34), fill=(255, 255, 255))
    draw.rectangle([MARGIN, 145, MARGIN + 140, 151], fill=(220, 40, 40))

    # 3. Hook (White text with Red Background Block)
    hook_font = font(48)
    hook_y = 840
    
    # We break the hook into words to allow it to wrap if it's too long
    hook_words = hook.upper().split()
    if len(hook) > 25: # If the hook is too long, split it into two lines
        line1 = " ".join(hook_words[:2])
        line2 = " ".join(hook_words[2:])
        draw_centered_text(draw, line1, hook_font, hook_y, (255, 255, 255), bg_color=(220, 40, 40))
        draw_centered_text(draw, line2, hook_font, hook_y + 70, (255, 255, 255), bg_color=(220, 40, 40))
        text_start_y = hook_y + 160
    else:
        draw_centered_text(draw, hook.upper(), hook_font, hook_y, (255, 255, 255), bg_color=(220, 40, 40))
        text_start_y = hook_y + 90

    # 4. Headline (Pure White Text)
    head_font = font(42)
    # Wrap headline to fit MAX_W
    head_lines, cur = [], ""
    for word in headline.split():
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=head_font) <= MAX_W:
            cur = trial
        else:
            if cur: head_lines.append(cur)
            cur = word
    if cur: head_lines.append(cur)

    y = text_start_y
    for line in head_lines:
        draw_centered_text(draw, line, head_font, y, (255, 255, 255))
        y += int(head_font.size * 1.3)

    # 5. Footer Info (Grey text)
    draw.text((MARGIN, 1180), f"VERIFIED BY {source_count} OUTLETS", font=font(24), fill=(150, 150, 150))
    draw.text((MARGIN, 1220), f"Sources: {outlets}", font=font(22), fill=(150, 150, 150))
    draw.text((MARGIN, 1280), "@thedailyprecinct", font=font(26), fill=(220, 40, 40))

    os.makedirs("output/images", exist_ok=True)
    path = f"output/images/{content_id}.jpg"
    img.save(path, "JPEG", quality=92)
    return path, "editorial"

# --- LEGACY COMPATIBILITY FOR REELS/CAROUSELS ---
STYLES = [{"name": "editorial", "top": (10, 22, 48), "bottom": (4, 10, 26), "text": (255, 255, 255), "accent": (220, 40, 40), "muted": (170, 180, 200), "align": "left"}]

def gradient(top, bottom):
    img = Image.new("RGB", (W, H), top)
    return img

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
    return font(min_size), wrap(draw, text, font(min_size), max_w), int(min_size * 1.18)

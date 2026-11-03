import os
import requests
import io
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

RW, RH = 1080, 1920
SAFE_LEFT, SAFE_RIGHT = 80, 80
SAFE_TOP, SAFE_BOTTOM = 180, 260
MAX_W = RW - (SAFE_LEFT + SAFE_RIGHT)

C_BG = (10, 22, 48)        # Midnight Navy
C_ACCENT = (201, 162, 39)  # Muted Gold
C_TEXT = (230, 235, 240)   # Silver/White
C_MUTED = (140, 160, 180)  # Slate Blue

FONT_PATHS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]

def font(size):
    for p in FONT_PATHS:
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def fetch_and_fit_image(url):
    """Downloads image, creates blurred background, and contains foreground."""
    bg = Image.new("RGB", (RW, RH), C_BG)
    if not url:
        return bg
        
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        
        # 1. Blurred Background
        bg_ratio = max(RW / img.width, RH / img.height)
        bg_img = img.resize((int(img.width * bg_ratio), int(img.height * bg_ratio)), Image.Resampling.LANCZOS)
        left, top = (bg_img.width - RW) // 2, (bg_img.height - RH) // 2
        bg_img = bg_img.crop((left, top, left + RW, top + RH))
        bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=30))
        enhancer = ImageEnhance.Brightness(bg_img)
        bg = enhancer.enhance(0.35) 
        
        # 2. Foreground Contain (No Cropping) with border
        max_fg_w, max_fg_h = MAX_W, 700
        img.thumbnail((max_fg_w, max_fg_h), Image.Resampling.LANCZOS)
        x_offset, y_offset = (RW - img.width) // 2, 350
        
        # Add a premium subtle border/shadow
        shadow = Image.new("RGBA", (img.width + 20, img.height + 20), (0,0,0,0))
        draw_shadow = ImageDraw.Draw(shadow)
        draw_shadow.rectangle([(0, 0), (img.width + 20, img.height + 20)], fill=(0,0,0,180))
        
        bg.paste(shadow, (x_offset - 10, y_offset - 10), shadow)
        bg.paste(img, (x_offset, y_offset))
        
        # Thin gold border around image
        draw = ImageDraw.Draw(bg)
        draw.rectangle([x_offset, y_offset, x_offset + img.width, y_offset + img.height], outline=C_ACCENT, width=2)
        
        return bg
    except Exception:
        return bg

def render_document_card(text):
    """If no image is found, generate a stylized document/quote card instead of a blank screen."""
    bg = Image.new("RGB", (RW, RH), C_BG)
    draw = ImageDraw.Draw(bg)
    
    # Draw a simulated "document" or "quote card" in the center
    card_w, card_h = 850, 800
    card_x, card_y = (RW - card_w) // 2, 350
    
    # Card Shadow
    draw.rectangle([card_x + 10, card_y + 10, card_x + card_w + 10, card_y + card_h + 10], fill=(0, 0, 0, 150))
    # Card Background (Off-white/Silver)
    draw.rectangle([card_x, card_y, card_x + card_w, card_y + card_h], fill=(240, 242, 245))
    # Card Border
    draw.rectangle([card_x, card_y, card_x + card_w, card_y + card_h], outline=C_ACCENT, width=6)
    
    # Fake Document Header
    draw.text((card_x + 40, card_y + 40), "THE DAILY PRECINCT", font=font(32), fill=C_BG)
    draw.rectangle([card_x + 40, card_y + 90, card_x + 200, card_y + 96], fill=C_ACCENT)
    
    # Document Text (Wrapped inside the card)
    f = font(44)
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=f) <= card_w - 80:
            cur = trial
        else:
            if cur: lines.append(cur)
            cur = word
    if cur: lines.append(cur)
    
    y = card_y + 150
    for line in lines[:8]: # Limit lines to fit in card
        draw.text((card_x + 40, y), line, font=f, fill=(20, 30, 50))
        y += 65
        
    return bg

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

def draw_branding(draw):
    draw.text((SAFE_LEFT, 100), "THE DAILY PRECINCT", font=font(38), fill=C_TEXT)
    draw.rectangle([SAFE_LEFT, 155, SAFE_LEFT + 140, 161], fill=C_ACCENT)

def draw_text_block(draw, text, f, y_start, color, bg_color=None, max_width=MAX_W):
    lines = wrap_text(draw, text, f, max_width)
    y = y_start
    line_h = int(f.size * 1.3)
    
    if bg_color:
        draw.rectangle(
            [(SAFE_LEFT - 30, y_start - 20), (SAFE_LEFT + max_width + 30, y_start + (len(lines) * line_h) + 20)],
            fill=bg_color
        )
        
    for line in lines:
        draw.text((SAFE_LEFT, y), line, font=f, fill=color)
        y += line_h

def render_scenes(cid, script, image_urls, voiceover_duration):
    folder = f"output/reels/{cid}_frames"
    os.makedirs(folder, exist_ok=True)
    scenes = []

    scene_defs = [
        {"text": script["scene_1_hook"], "font": 72, "bg": C_BG, "img": image_urls[0]},
        {"text": script["scene_2_context"], "font": 46, "bg": C_BG, "img": image_urls[1]},
        {"text": script["scene_3_main"], "font": 46, "bg": C_BG, "img": image_urls[2]},
        {"text": script["scene_4_details"], "font": 40, "bg": C_BG, "img": image_urls[3]},
        {"text": script["scene_5_impact"], "font": 46, "bg": C_BG, "img": image_urls[4]},
        {"text": script["scene_6_next"], "font": 42, "bg": C_BG, "img": image_urls[5]},
        {"text": script["scene_7_cta"], "font": 44, "bg": C_ACCENT, "img": image_urls[6]}
    ]

    total_words = sum(len(s["text"].split()) for s in scene_defs)
    
    for i, scene in enumerate(scene_defs):
        words = len(scene["text"].split())
        duration = max(2.0, (words / total_words) * voiceover_duration)

        # STAGE 2 FIX: If no image exists, render a premium Document Card instead of blank background
        if scene["img"] is None and i != 6: # CTA (Scene 7) always uses solid background
            img = render_document_card(scene["text"])
        else:
            img = fetch_and_fit_image(scene["img"])
            
        draw = ImageDraw.Draw(img)
        draw_branding(draw)

        f = font(scene["font"])
        text_color = C_BG if scene["bg"] == C_ACCENT else C_TEXT
        
        # For Document Cards, we don't need the bottom text block, it's already inside the card
        if not (scene["img"] is None and i != 6):
            draw_text_block(draw, scene["text"], f, 1150, text_color, bg_color=scene["bg"])

        p = f"{folder}/s{i:02d}.png"
        img.save(p, "PNG")
        scenes.append((p, duration))

    return scenes, folder

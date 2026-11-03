import os
import requests
import io
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

RW, RH = 1080, 1920
SAFE_LEFT, SAFE_RIGHT = 80, 80
SAFE_TOP, SAFE_BOTTOM = 180, 260
MAX_W = RW - (SAFE_LEFT + SAFE_RIGHT)

# Brand Colors
C_BG = (10, 22, 48)        # Midnight Navy
C_ACCENT = (201, 162, 39)  # Muted Gold
C_TEXT = (230, 235, 240)   # Silver/White
C_MUTED = (140, 160, 180)  # Slate Blue

FONT_PATHS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]

def font(size):
    for p in FONT_PATHS:
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default()

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

def create_document_mockup(text):
    """Generates a professional news document graphic if no photo exists."""
    bg = Image.new("RGB", (RW, 800), C_BG)
    draw = ImageDraw.Draw(bg)
    
    # Draw stylized "paper" in the center
    paper_w, paper_h = 800, 600
    paper_x, paper_y = (RW - paper_w) // 2, (800 - paper_h) // 2
    
    # Paper Shadow
    draw.rectangle([(paper_x + 15, paper_y + 15), (paper_x + paper_w + 15, paper_y + paper_h + 15)], fill=(0, 0, 0))
    # Paper Base
    draw.rectangle([(paper_x, paper_y), (paper_x + paper_w, paper_y + paper_h)], fill=(245, 245, 245))
    
    # Decorative document lines (redacted look)
    for i in range(5):
        y = paper_y + 50 + (i * 40)
        width = paper_w - 100 if i % 2 == 0 else paper_w - 300
        draw.rectangle([(paper_x + 50, y), (paper_x + 50 + width, y + 15)], fill=(200, 200, 200))
        
    # Add Text overlay
    f = font(40)
    lines = wrap_text(draw, text, f, paper_w - 100)
    y = paper_y + paper_h - (len(lines) * 50) - 50
    
    for line in lines[:2]: # Max 2 lines inside the doc
        draw.text((paper_x + 50, y), line, font=f, fill=(20, 20, 20))
        y += 50
        
    # "REPORT" Stamp
    draw.rectangle([(paper_x + paper_w - 200, paper_y + 30), (paper_x + paper_w - 30, paper_y + 80)], outline=(200, 30, 30), width=4)
    draw.text((paper_x + paper_w - 180, paper_y + 40), "REPORT", font=font(24), fill=(200, 30, 30))

    return bg

def create_quote_card(text):
    """Generates a broadcast-style quote card if no photo exists."""
    bg = Image.new("RGB", (RW, 800), C_BG)
    draw = ImageDraw.Draw(bg)
    
    # Massive background quote mark
    quote_font = font(400)
    draw.text((100, -100), "“", font=quote_font, fill=(30, 45, 75)) # Subtle
 
    # Gold border accent
    draw.rectangle([(SAFE_LEFT, 150), (SAFE_LEFT + 10, 650)], fill=C_ACCENT)
    
    f = font(50)
    lines = wrap_text(draw, text, f, 750)
    y = 250
    
    for line in lines[:4]: # Max 4 lines
        draw.text((SAFE_LEFT + 50, y), line, font=f, fill=C_TEXT)
        y += 70
        
    return bg

def fetch_and_fit_image(url, fallback_text):
    bg = Image.new("RGB", (RW, RH), C_BG)
    
    # --- FALLBACK LOGIC ---
    if not url:
        # Randomly choose between Document Mockup and Quote Card for visual variety
        if random.choice([True, False]):
            visual = create_document_mockup(fallback_text)
        else:
            visual = create_quote_card(fallback_text)
            
        bg.paste(visual, (0, 300)) # Paste in the center area
        return bg
        
    # --- IMAGE LOGIC ---
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
        
        # 2. Foreground Contain (No Cropping)
        max_fg_w, max_fg_h = MAX_W, 700
        img.thumbnail((max_fg_w, max_fg_h), Image.Resampling.LANCZOS)
        x_offset, y_offset = (RW - img.width) // 2, 350
        
        # Shadow
        shadow = Image.new("RGBA", (img.width + 20, img.height + 20), (0,0,0,0))
        draw_shadow = ImageDraw.Draw(shadow)
        draw_shadow.rectangle([(0, 0), (img.width + 20, img.height + 20)], fill=(0,0,0,150))
        
        bg.paste(shadow, (x_offset - 10, y_offset - 10), shadow)
        bg.paste(img, (x_offset, y_offset))
        return bg
    except Exception:
        # If download fails, fallback
        return fetch_and_fit_image(None, fallback_text)

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

        # Pass the scene text to the image fetcher for the fallback mockups
        img = fetch_and_fit_image(scene["img"], scene["text"])
        
        draw = ImageDraw.Draw(img)
        draw_branding(draw)

        f = font(scene["font"])
        text_color = C_BG if scene["bg"] == C_ACCENT else C_TEXT
        
        draw_text_block(draw, scene["text"], f, 1150, text_color, bg_color=scene["bg"])

        p = f"{folder}/s{i:02d}.png"
        img.save(p, "PNG")
        scenes.append((p, duration))

    return scenes, folder

import os
import io
import requests
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
MARGIN = 90
MAX_W = W - (MARGIN * 2)
SPLIT_Y = 750 

# Elite Brand Palette
C_BG = (10, 22, 48)        # Midnight Navy
C_ACCENT = (201, 162, 39)  # Muted Gold
C_TEXT = (230, 235, 240)   # Restrained Silver
C_MUTED = (140, 160, 180)  # Slate Blue/Grey

FONT_PATHS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]

def font(size):
    for p in FONT_PATHS:
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def download_and_process_bg(url):
    if not url:
        return Image.new("RGB", (W, SPLIT_Y), C_BG)
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        
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
        print(f"Image download failed: {e}")
        return Image.new("RGB", (W, SPLIT_Y), C_BG)

def draw_centered_text(draw, text, f, y, color, bg_color=None, padding_x=30, padding_y=15):
    w = draw.textlength(text, font=f)
    x = (W - w) / 2
    if bg_color:
        draw.rectangle(
            [(x - padding_x, y - padding_y), (x + w + padding_x, y + f.size + padding_y)],
            fill=bg_color
        )
    draw.text((x, y), text, font=f, fill=color)

def draw_branding(draw):
    draw.text((MARGIN, 90), "THE DAILY PRECINCT", font=font(34), fill=C_TEXT)
    draw.rectangle([MARGIN, 145, MARGIN + 140, 151], fill=C_ACCENT)

def draw_footer(draw, n, total):
    draw.text((MARGIN, 1270), "@thedailyprecinct", font=font(28), fill=C_ACCENT)
    label = f"{n}/{total}"
    w = draw.textlength(label, font=font(28))
    draw.text((W - MARGIN - w, 1270), label, font=font(28), fill=C_MUTED)

def premium_slide(image_url, title, points, n, total, path):
    img = Image.new("RGB", (W, H), C_BG)
    top_img = download_and_process_bg(image_url)
    img.paste(top_img, (0, 0))
    
    draw = ImageDraw.Draw(img)
    draw_branding(draw)

    # Title (Gold Block, Navy Text)
    title_font = font(46)
    draw_centered_text(draw, title.upper(), title_font, 800, C_BG, bg_color=C_ACCENT)
    
    # Points (Silver Text, Gold bullet)
    y = 890
    body_font = font(36)
    for point in points:
        lines, cur = [], ""
        for word in point.split():
            trial = (cur + " " + word).strip()
            if draw.textlength(trial, font=body_font) <= MAX_W - 40:
                cur = trial
            else:
                if cur: lines.append(cur)
                cur = word
        if cur: lines.append(cur)
        
        draw.rectangle([MARGIN, y + 10, MARGIN + 16, y + 26], fill=C_ACCENT)
        
        for line in lines:
            draw.text((MARGIN + 40, y), line, font=body_font, fill=C_TEXT)
            y += int(body_font.size * 1.4) # Generous spacing
        y += 30 # Gap between bullets

    draw_footer(draw, n, total)
    img.save(path, "JPEG", quality=95)

def cover_slide(image_url, copy, n, total, path):
    img = Image.new("RGB", (W, H), C_BG)
    top_img = download_and_process_bg(image_url)
    img.paste(top_img, (0, 0))
    
    draw = ImageDraw.Draw(img)
    draw_branding(draw)

    # Hook (Gold Block)
    hook_font = font(48)
    draw_centered_text(draw, copy["hook"].upper(), hook_font, 800, C_BG, bg_color=C_ACCENT)

    # Headline (Silver Text)
    head_font = font(42)
    y = 900
    lines, cur = [], ""
    for word in copy["cover_headline"].split():
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=head_font) <= MAX_W:
            cur = trial
        else:
            if cur: lines.append(cur)
            cur = word
    if cur: lines.append(cur)

    for line in lines:
        draw_centered_text(draw, line, head_font, y, C_TEXT)
        y += int(head_font.size * 1.4)

    draw_footer(draw, n, total)
    img.save(path, "JPEG", quality=95)

def sources_slide(outlet_list, count, n, total, path):
    img = Image.new("RGB", (W, H), C_BG)
    draw = ImageDraw.Draw(img)
    draw_branding(draw)

    draw_centered_text(draw, "WHO'S REPORTING", font(48), 400, C_BG, bg_color=C_ACCENT)
    
    y = 520
    for o in outlet_list[:8]:
        draw_centered_text(draw, o, font(44), y, C_TEXT)
        y += 80
        
    draw_centered_text(draw, f"Verified by {count} independent outlets", font(32), y + 40, C_MUTED)
    
    draw_footer(draw, n, total)
    img.save(path, "JPEG", quality=95)

def cta_slide(image_url, cta, n, total, path):
    img = Image.new("RGB", (W, H), C_BG)
    # Heavy dark overlay on the cover image
    top_img = download_and_process_bg(image_url)
    img.paste(top_img, (0, 0))
    
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (W, H)], fill=(10, 22, 48, 230)) # Navy overlay
    
    draw_branding(draw)

    draw_centered_text(draw, "FOLLOW FOR MORE", font(56), 600, C_BG, bg_color=C_ACCENT)
    
    # CTA text (Silver)
    y = 750
    body_font = font(44)
    lines, cur = [], ""
    for word in cta.split():
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=body_font) <= MAX_W:
            cur = trial
        else:
            if cur: lines.append(cur)
            cur = word
    if cur: lines.append(cur)
    
    for line in lines:
        draw_centered_text(draw, line, body_font, y, C_TEXT)
        y += int(body_font.size * 1.4)

    draw_centered_text(draw, "Politics without the noise.", font(32), 950, C_MUTED)
    draw_centered_text(draw, "@thedailyprecinct", font(36), 1100, C_ACCENT)

    draw_footer(draw, n, total)
    img.save(path, "JPEG", quality=95)

def render_carousel(cid, copy, outlets, source_count, index, image_urls):
    folder = f"output/carousels/{cid}"
    os.makedirs(folder, exist_ok=True)
    
    paths = []
    
    p1 = f"{folder}/slide-1.jpg"
    cover_slide(image_urls[0], copy, 1, 5, p1)
    paths.append(p1)

    p2 = f"{folder}/slide-2.jpg"
    premium_slide(image_urls[1], copy["slides"][0]["title"], copy["slides"][0]["points"], 2, 5, p2)
    paths.append(p2)

    p3 = f"{folder}/slide-3.jpg"
    premium_slide(image_urls[2], copy["slides"][1]["title"], copy["slides"][1]["points"], 3, 5, p3)
    paths.append(p3)

    p4 = f"{folder}/slide-4.jpg"
    outlet_list = [o.strip() for o in outlets.split(",") if o.strip()]
    sources_slide(outlet_list, source_count, 4, 5, p4)
    paths.append(p4)

    p5 = f"{folder}/slide-5.jpg"
    cta_slide(image_urls[3], copy["cta"], 5, 5, p5)
    paths.append(p5)

    return paths, "elite_editorial"

import os
import io
import requests
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
MARGIN = 90
MAX_W = W - (MARGIN * 2)
SPLIT_Y = 750 # Image on top 750px, Black box bottom 600px

FONT_PATHS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]

def font(size):
    for p in FONT_PATHS:
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def download_and_process_bg(url):
    """Downloads image and crops perfectly to 1080x750."""
    if not url:
        return Image.new("RGB", (W, SPLIT_Y), (10, 10, 10))
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
        return Image.new("RGB", (W, SPLIT_Y), (10, 10, 10))

def draw_centered_text(draw, text, f, y, color, bg_color=None, padding_x=20, padding_y=10):
    w = draw.textlength(text, font=f)
    x = (W - w) / 2
    if bg_color:
        draw.rectangle(
            [(x - padding_x, y - padding_y), (x + w + padding_x, y + f.size + padding_y)],
            fill=bg_color
        )
    draw.text((x, y), text, font=f, fill=color)

def draw_branding(draw):
    draw.text((MARGIN, 90), "THE DAILY PRECINCT", font=font(34), fill=(255, 255, 255))
    draw.rectangle([MARGIN, 145, MARGIN + 140, 151], fill=(220, 40, 40))

def draw_footer(draw, n, total):
    draw.text((MARGIN, 1270), "@thedailyprecinct", font=font(28), fill=(220, 40, 40))
    label = f"{n}/{total}"
    w = draw.textlength(label, font=font(28))
    draw.text((W - MARGIN - w, 1270), label, font=font(28), fill=(150, 150, 150))

def premium_slide(image_url, title, points, n, total, path):
    img = Image.new("RGB", (W, H), (0, 0, 0))
    top_img = download_and_process_bg(image_url)
    img.paste(top_img, (0, 0))
    
    draw = ImageDraw.Draw(img)
    draw_branding(draw)

    # Title (Red Block)
    title_font = font(46)
    draw_centered_text(draw, title.upper(), title_font, 800, (255, 255, 255), bg_color=(220, 40, 40))
    
    # Points
    y = 890
    body_font = font(36)
    for point in points:
        # Wrap text
        lines, cur = [], ""
        for word in point.split():
            trial = (cur + " " + word).strip()
            if draw.textlength(trial, font=body_font) <= MAX_W - 40:
                cur = trial
            else:
                if cur: lines.append(cur)
                cur = word
        if cur: lines.append(cur)
        
        # Draw bullet
        draw.rectangle([MARGIN, y + 10, MARGIN + 16, y + 26], fill=(220, 40, 40))
        
        for line in lines:
            draw.text((MARGIN + 40, y), line, font=body_font, fill=(255, 255, 255))
            y += int(body_font.size * 1.3)
        y += 20 # Gap between bullets

    draw_footer(draw, n, total)
    img.save(path, "JPEG", quality=92)

def cover_slide(image_url, copy, n, total, path):
    img = Image.new("RGB", (W, H), (0, 0, 0))
    top_img = download_and_process_bg(image_url)
    img.paste(top_img, (0, 0))
    
    draw = ImageDraw.Draw(img)
    draw_branding(draw)

    # Hook
    hook_font = font(48)
    draw_centered_text(draw, copy["hook"].upper(), hook_font, 800, (255, 255, 255), bg_color=(220, 40, 40))

    # Headline
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
        draw_centered_text(draw, line, head_font, y, (255, 255, 255))
        y += int(head_font.size * 1.3)

    draw_footer(draw, n, total)
    img.save(path, "JPEG", quality=92)

def sources_slide(outlet_list, count, n, total, path):
    img = Image.new("RGB", (W, H), (10, 15, 30))
    draw = ImageDraw.Draw(img)
    draw_branding(draw)

    draw_centered_text(draw, "WHO'S REPORTING", font(48), 400, (255, 255, 255), bg_color=(220, 40, 40))
    
    y = 520
    for o in outlet_list[:8]:
        draw_centered_text(draw, o, font(44), y, (255, 255, 255))
        y += 80
        
    draw_centered_text(draw, f"Verified by {count} independent outlets", font(32), y + 40, (150, 150, 150))
    
    draw_footer(draw, n, total)
    img.save(path, "JPEG", quality=92)

def cta_slide(image_url, cta, n, total, path):
    # Premium CTA: Blurred background image
    img = download_and_process_bg(image_url)
    # Create full canvas
    full_img = Image.new("RGB", (W, H), (0, 0, 0))
    full_img.paste(img, (0, 0))
    
    # We won't actually blur because it's expensive, we'll just use a heavy dark overlay
    draw = ImageDraw.Draw(full_img)
    draw.rectangle([(0, 0), (W, H)], fill=(0, 0, 0, 200)) # Very dark overlay
    
    draw_branding(draw)

    draw_centered_text(draw, "FOLLOW FOR MORE", font(56), 500, (255, 255, 255), bg_color=(220, 40, 40))
    
    # The CTA text
    y = 650
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
        draw_centered_text(draw, line, body_font, y, (255, 255, 255))
        y += int(body_font.size * 1.3)

    draw_centered_text(draw, "Politics without the noise.", font(32), 900, (200, 200, 200))
    draw_centered_text(draw, "@thedailyprecinct", font(36), 1100, (220, 40, 40))

    draw_footer(draw, n, total)
    full_img.save(path, "JPEG", quality=92)

def render_carousel(cid, copy, outlets, source_count, index, image_urls):
    folder = f"output/carousels/{cid}"
    os.makedirs(folder, exist_ok=True)
    
    paths = []
    
    # Cover
    p1 = f"{folder}/slide-1.jpg"
    cover_slide(image_urls[0], copy, 1, 5, p1)
    paths.append(p1)

    # Slide 2
    p2 = f"{folder}/slide-2.jpg"
    premium_slide(image_urls[1], copy["slides"][0]["title"], copy["slides"][0]["points"], 2, 5, p2)
    paths.append(p2)

    # Slide 3
    p3 = f"{folder}/slide-3.jpg"
    premium_slide(image_urls[2], copy["slides"][1]["title"], copy["slides"][1]["points"], 3, 5, p3)
    paths.append(p3)

    # Slide 4 (Sources)
    p4 = f"{folder}/slide-4.jpg"
    outlet_list = [o.strip() for o in outlets.split(",") if o.strip()]
    sources_slide(outlet_list, source_count, 4, 5, p4)
    paths.append(p4)

    # Slide 5 (CTA)
    p5 = f"{folder}/slide-5.jpg"
    cta_slide(image_urls[3], copy["cta"], 5, 5, p5)
    paths.append(p5)

    return paths, "editorial"

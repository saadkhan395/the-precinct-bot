import os, requests, io
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

RW, RH = 1080, 1920
SAFE_L, SAFE_R, SAFE_T, SAFE_B = 80, 80, 180, 260
MAX_W = RW - (SAFE_L + SAFE_R)

C_BG = (10, 22, 48)
C_ACCENT = (201, 162, 39)
C_TEXT = (230, 235, 240)

def font(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]:
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def get_bg(url):
    bg = Image.new("RGB", (RW, RH), C_BG)
    if not url: return bg
    try:
        img = Image.open(io.BytesIO(requests.get(url, timeout=15).content)).convert("RGB")
        ratio = max(RW / img.width, RH / img.height)
        bg_img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.Resampling.LANCZOS)
        bg.paste(bg_img.crop(((bg_img.width-RW)//2, (bg_img.height-RH)//2, (bg_img.width-RW)//2+RW, (bg_img.height-RH)//2+RH)).filter(ImageFilter.GaussianBlur(30)), (0,0))
        
        # Contain Fit
        img.thumbnail((MAX_W, 700), Image.Resampling.LANCZOS)
        bg.paste(img, ((RW-img.width)//2, 350))
        return bg
    except: return bg

def wrap(draw, text, f, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=f) <= max_w: cur = trial
        else: lines.append(cur); cur = word
    if cur: lines.append(cur)
    return lines

def render_scenes(cid, script, urls, vo_dur):
    folder = f"output/reels/{cid}_frames"
    os.makedirs(folder, exist_ok=True)
    scenes = []
    
    defs = [
        (script["scene_1_hook"], 72, C_BG, urls[0]), (script["scene_2_context"], 46, C_BG, urls[1]),
        (script["scene_3_main"], 46, C_BG, urls[2]), (script["scene_4_details"], 40, C_BG, urls[3]),
        (script["scene_5_impact"], 46, C_BG, urls[4]), (script["scene_6_next"], 42, C_BG, urls[5]),
        (script["scene_7_cta"], 44, C_ACCENT, urls[6])
    ]
    total_words = sum(len(d[0].split()) for d in defs)
    
    for i, (text, sz, bg_c, url) in enumerate(defs):
        dur = max(2.0, (len(text.split()) / total_words) * vo_dur)
        img = get_bg(url)
        draw = ImageDraw.Draw(img)
        
        # Branding
        draw.text((SAFE_L, 100), "THE DAILY PRECINCT", font=font(38), fill=C_TEXT)
        draw.rectangle([SAFE_L, 155, SAFE_L+140, 161], fill=C_ACCENT)
        
        # Text Block
        f = font(sz)
        lines = wrap(draw, text, f, MAX_W)
        y = 1150
        
        draw.rectangle([(SAFE_L-30, y-20), (SAFE_L+MAX_W+30, y+(len(lines)*int(sz*1.3))+20)], fill=bg_c)
        for line in lines:
            draw.text((SAFE_L, y), line, font=f, fill=(C_BG if bg_c==C_ACCENT else C_TEXT))
            y += int(sz*1.3)
            
        p = f"{folder}/s{i:02d}.png"
        img.save(p)
        scenes.append((p, dur))
    return scenes, folder

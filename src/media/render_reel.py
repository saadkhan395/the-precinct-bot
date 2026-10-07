import os

from PIL import Image, ImageDraw

from media.render_image import MARGIN, STYLES, fit_text, font

RW, RH = 1080, 1920
TOP_SAFE = 220
BOTTOM_SAFE = 1600

PACING = [
    {"name": "quick", "hook": 2.5, "headline": 4.0, "fact": 3.5, "sources": 3.0, "cta": 3.0},
    {"name": "standard", "hook": 3.0, "headline": 5.0, "fact": 4.5, "sources": 3.5, "cta": 3.5},
]


def gradient_tall(top, bottom):
    img = Image.new("RGB", (RW, RH), top)
    d = ImageDraw.Draw(img)
    for y in range(RH):
        t = y / (RH - 1)
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        d.line([(0, y), (RW, y)], fill=c)
    return img


def new_frame(style):
    img = gradient_tall(style["top"], style["bottom"])
    draw = ImageDraw.Draw(img)
    draw.text((MARGIN, 110), "THE DAILY PRECINCT", font=font(38), fill=style["accent"])
    draw.rectangle([MARGIN, 165, MARGIN + 150, 172], fill=style["accent"])
    return img, draw


def put_lines(draw, lines, f, y, color, align, line_h):
    for line in lines:
        w = draw.textlength(line, font=f)
        x = MARGIN if align == "left" else (RW - w) / 2
        draw.text((x, y), line, font=f, fill=color)
        y += line_h
    return y


def center_block(draw, text, style, start, min_size, label=None):
    max_w = RW - 2 * MARGIN
    f, lines, lh = fit_text(draw, text, max_w, 900, start=start, min_size=min_size)
    label_h = 90 if label else 0
    block_h = len(lines) * lh + label_h
    y = max(TOP_SAFE + 80, (TOP_SAFE + BOTTOM_SAFE - block_h) // 2)
    if label:
        put_lines(draw, [label], font(46), y, style["accent"], style["align"], 60)
        y += label_h
    return put_lines(draw, lines, f, y, style["text"], style["align"], lh)


def render_scenes(cid, copy, outlets, source_count, index):
    style = STYLES[index % len(STYLES)]
    pace = PACING[index % len(PACING)]
    folder = f"output/reels/{cid}_frames"
    os.makedirs(folder, exist_ok=True)
    scenes = []

    def save(img, name, seconds):
        p = f"{folder}/{name}.png"
        img.save(p, "PNG")
        scenes.append((p, seconds))

    img, draw = new_frame(style)
    center_block(draw, copy["hook"].upper(), style, 120, 70)
    save(img, "s01_hook", pace["hook"])

    img, draw = new_frame(style)
    center_block(draw, copy["cover_headline"], style, 100, 56)
    save(img, "s02_headline", pace["headline"])

    n = 3
    for s in copy["slides"]:
        for point in s["points"]:
            if n > 6:
                break
            img, draw = new_frame(style)
            center_block(draw, point, style, 76, 46, label=s["title"].upper())
            save(img, f"s{n:02d}_fact", pace["fact"])
            n += 1

    img, draw = new_frame(style)
    names = [o.strip() for o in outlets.split(",") if o.strip()][:7]
    text = f"VERIFIED BY {source_count} OUTLETS"
    y = center_block(draw, text, style, 64, 48)
    y += 30
    put_lines(draw, names, font(44), y, style["muted"], style["align"], 60)
    save(img, f"s{n:02d}_sources", pace["sources"])
    n += 1

    img, draw = new_frame(style)
    center_block(draw, copy["cta"], style, 72, 46, label="FOLLOW @THEDAILYPRECINCT")
    save(img, f"s{n:02d}_cta", pace["cta"])
    return scenes, style["name"], pace["name"], folder

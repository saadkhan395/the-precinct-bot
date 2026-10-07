import os
import shutil

from PIL import ImageDraw

from media.render_image import (
    MARGIN,
    STYLES,
    W,
    fit_text,
    font,
    gradient,
    render_post,
    wrap,
)


def base(style):
    img = gradient(style["top"], style["bottom"])
    draw = ImageDraw.Draw(img)
    draw.text((MARGIN, 90), "THE DAILY PRECINCT", font=font(34), fill=style["accent"])
    draw.rectangle([MARGIN, 145, MARGIN + 140, 151], fill=style["accent"])
    return img, draw


def footer(draw, style, n, total):
    draw.text(
        (MARGIN, 1275), "@thedailyprecinct", font=font(30), fill=style["accent"]
    )
    label = f"{n}/{total}"
    f = font(30)
    w = draw.textlength(label, font=f)
    draw.text((W - MARGIN - w, 1275), label, font=f, fill=style["muted"])


def fit_points(draw, points, max_w, max_h, start=56, min_size=34):
    size = start
    while True:
        f = font(size)
        lh = int(size * 1.25)
        gap = int(size * 0.9)
        blocks = [wrap(draw, p, f, max_w) for p in points]
        total = sum(len(b) * lh for b in blocks) + gap * (len(blocks) - 1)
        if total <= max_h or size <= min_size:
            return f, blocks, lh, gap
        size -= 2


def bullet(draw, style, y, lh):
    top = y + int(lh * 0.3)
    draw.rectangle([MARGIN, top, MARGIN + 16, top + 16], fill=style["accent"])


def points_slide(style, title, points, n, total, path):
    img, draw = base(style)
    max_w = W - 2 * MARGIN - 50
    draw.text((MARGIN, 250), title.upper(), font=font(52), fill=style["accent"])
    f, blocks, lh, gap = fit_points(draw, points, max_w, 720)
    y = 360
    for block in blocks:
        bullet(draw, style, y, lh)
        for line in block:
            draw.text((MARGIN + 50, y), line, font=f, fill=style["text"])
            y += lh
        y += gap
    footer(draw, style, n, total)
    img.save(path, "JPEG", quality=92)


def sources_slide(style, outlet_list, count, n, total, path):
    img, draw = base(style)
    max_w = W - 2 * MARGIN
    draw.text((MARGIN, 250), "WHO'S REPORTING", font=font(52), fill=style["accent"])
    f = font(46)
    y = 360
    for o in outlet_list[:8]:
        bullet(draw, style, y, 56)
        draw.text((MARGIN + 50, y), o, font=f, fill=style["text"])
        y += 72
    y += 30
    small = font(34)
    for line in wrap(draw, f"Verified by {count} independent outlets", small, max_w):
        draw.text((MARGIN, y), line, font=small, fill=style["muted"])
        y += 46
    footer(draw, style, n, total)
    img.save(path, "JPEG", quality=92)


def cta_slide(style, cta, n, total, path):
    img, draw = base(style)
    max_w = W - 2 * MARGIN
    draw.text((MARGIN, 380), "FOLLOW FOR MORE", font=font(52), fill=style["accent"])
    f, lines, lh = fit_text(draw, cta, max_w, 420, start=72, min_size=44)
    y = 470
    for line in lines:
        draw.text((MARGIN, y), line, font=f, fill=style["text"])
        y += lh
    small = font(30)
    y = max(y + 60, 1000)
    note = "Summarized from public reporting. Read the full stories at the sources."
    for line in wrap(draw, note, small, max_w):
        draw.text((MARGIN, y), line, font=small, fill=style["muted"])
        y += 40
    footer(draw, style, n, total)
    img.save(path, "JPEG", quality=92)


def render_carousel(cid, copy, outlets, source_count, index):
    style = STYLES[index % len(STYLES)]
    folder = f"output/carousels/{cid}"
    os.makedirs(folder, exist_ok=True)

    cover_tmp, _ = render_post(
        cid, copy["hook"], copy["cover_headline"], outlets, source_count, index
    )
    paths = [f"{folder}/slide-1.jpg"]
    shutil.move(cover_tmp, paths[0])

    total = 1 + len(copy["slides"]) + 2
    n = 2
    for s in copy["slides"]:
        p = f"{folder}/slide-{n}.jpg"
        points_slide(style, s["title"], s["points"], n, total, p)
        paths.append(p)
        n += 1

    outlet_list = [o.strip() for o in outlets.split(",") if o.strip()]
    p = f"{folder}/slide-{n}.jpg"
    sources_slide(style, outlet_list, source_count, n, total, p)
    paths.append(p)
    n += 1

    p = f"{folder}/slide-{n}.jpg"
    cta_slide(style, copy["cta"], n, total, p)
    paths.append(p)
    return paths, style["name"]

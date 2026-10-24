#!/usr/bin/env python3
"""Portrait (1080x1350) image cards and carousel slides for @thecyberintellect news posts.

Used by render_all.py. Same dark navy / cyan palette and Inter fonts as the reels,
so feed posts and reels look like one brand.
"""
import os
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1350
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(os.path.dirname(HERE), "render", "fonts")

BG_TOP, BG_BOT = (6, 11, 24), (13, 25, 50)
GRID = (20, 35, 64)
TEXT = (241, 245, 249)
MUTED = (128, 146, 176)
ACCENT = (34, 211, 238)
AMBER = (245, 158, 11)
GREEN = (34, 197, 94)
RED = (239, 68, 68)
VIOLET = (167, 139, 250)
PANEL = (15, 27, 52)
INK = (6, 11, 24)
BRAND = "THE CYBER INTELLECT"
HANDLE = "@thecyberintellect"

CATEGORY_COLOUR = {
    "ZERO-DAY": RED, "BREACH": RED, "RANSOMWARE": RED, "ATTACK": RED,
    "PATCH NOW": AMBER, "VULNERABILITY": AMBER, "THREAT INTEL": AMBER, "SUPPLY CHAIN": AMBER,
    "AI SECURITY": VIOLET, "AGENTIC AI": VIOLET, "AI NEWS": VIOLET, "AI THREAT": VIOLET,
    "CLOUD": ACCENT, "IDENTITY": ACCENT, "POLICY": ACCENT, "DEFENCE": GREEN, "DEFENSE": GREEN,
}


def colour_for(category):
    c = (category or "").upper()
    if c in CATEGORY_COLOUR:
        return CATEGORY_COLOUR[c]
    words = c.replace("-", " ").split()
    if any(k in c for k in ("BREACH", "RANSOM", "ATTACK", "ZERO")):
        return RED
    if "AI" in words or "AGENTIC" in words or "LLM" in words:
        return VIOLET
    if any(k in c for k in ("PATCH", "VULN", "THREAT", "SUPPLY", "CVE")):
        return AMBER
    return ACCENT


def font(name, size):
    p = os.path.join(FONTS, name)
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default(size=size)


def heavy(size): return font("InterDisplay-Bold.otf", size)
def semi(size): return font("Inter-SemiBold.otf", size)
def medium(size): return font("Inter-Medium.otf", size)


def wrap(text, fnt, max_w):
    lines = []
    for para in str(text).split("\n"):
        words, cur = para.split(), ""
        for w in words:
            t = (cur + " " + w).strip()
            if fnt.getlength(t) <= max_w or not cur:
                cur = t
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return [l for l in lines if l is not None]


def fit(text, maker, max_w, max_lines, start, minimum, step=4):
    size = start
    while size >= minimum:
        f = maker(size)
        lines = wrap(text, f, max_w)
        if len(lines) <= max_lines and all(f.getlength(l) <= max_w for l in lines):
            return f, lines
        size -= step
    f = maker(minimum)
    return f, wrap(text, f, max_w)


def background(tint):
    col = Image.new("RGB", (1, H))
    for y in range(H):
        k = y / (H - 1)
        col.putpixel((0, y), tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * k) for i in range(3)))
    img = col.resize((W, H))
    d = ImageDraw.Draw(img)
    for x in range(0, W, 60):
        d.line([(x, 0), (x, H)], fill=GRID, width=1)
    for y in range(0, H, 60):
        d.line([(0, y), (W, y)], fill=GRID, width=1)
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    t = tuple(int(c * 0.32) for c in tint)
    gd.ellipse([-300, 180, 560, 980], fill=t)
    gd.ellipse([620, 760, 1420, 1560], fill=(34, 26, 80))
    glow = glow.filter(ImageFilter.GaussianBlur(170))
    return ImageChops.add(img, glow).convert("RGBA")


def header(img, category, index=None, total=None):
    d = ImageDraw.Draw(img)
    fb = semi(28)
    x = 70
    for ch in BRAND:
        d.text((x, 64), ch, font=fb, fill=ACCENT)
        x += fb.getlength(ch) + 3
    if index and total and total > 1:
        t = f"{index}/{total}"
        ft = semi(28)
        d.text((W - 70 - ft.getlength(t), 64), t, font=ft, fill=MUTED)
    if category:
        c = colour_for(category)
        fc = semi(28)
        label = category.upper()
        cw = fc.getlength(label) + 44
        d.rounded_rectangle([70, 118, 70 + cw, 168], radius=25, fill=c)
        d.text((92, 125), label, font=fc, fill=INK)
    return 210


def footer(img, swipe=False):
    d = ImageDraw.Draw(img)
    f = medium(28)
    d.text((70, H - 86), HANDLE, font=f, fill=MUTED)
    if swipe:
        t = "SWIPE  →"
        fs = semi(30)
        d.text((W - 70 - fs.getlength(t), H - 88), t, font=fs, fill=ACCENT)


def text_block(d, x, y, text, fnt, fill, max_w, lh=1.2):
    lines = wrap(text, fnt, max_w)
    step = int(fnt.size * lh)
    for ln in lines:
        d.text((x, y), ln, font=fnt, fill=fill)
        y += step
    return y


def cover(item, total, swipe):
    """Slide 1 / single card: category, huge hook, supporting line, optional bullets.
    Shrinks everything together until it fits above the footer."""
    cat = item.get("category", "")
    c = colour_for(cat)
    bullets = item.get("bullets") if not swipe else None
    for scale in (1.0, 0.92, 0.85, 0.78, 0.72, 0.66):
        img = background(c)
        y = header(img, cat, 1 if total > 1 else None, total) + int(90 * scale)
        d = ImageDraw.Draw(img)
        hf, hl = fit(item["cover"]["hook"], heavy, 940, 5, int(118 * scale), int(60 * scale))
        for ln in hl:
            d.text((70, y), ln, font=hf, fill=TEXT)
            y += int(hf.size * 1.1)
        y += 26
        d.rounded_rectangle([70, y, 210, y + 10], radius=5, fill=c)
        y += int(60 * scale)
        sub = item["cover"].get("sub")
        if sub:
            sf, sl = fit(sub, semi, 940, 4, int(48 * scale), int(32 * scale))
            for ln in sl:
                d.text((70, y), ln, font=sf, fill=(200, 212, 230))
                y += int(sf.size * 1.3)
        if bullets:
            y += int(40 * scale)
            y = bullet_list(d, y, bullets, c, size=int(40 * scale))
        if y <= H - 130:
            break
    footer(img, swipe=swipe)
    return img


def bullet_list(d, y, items, colour, size=40):
    f = semi(size)
    for it in items:
        d.ellipse([74, y + size * 0.32, 74 + 18, y + size * 0.32 + 18], fill=colour)
        y = text_block(d, 116, y, it, f, TEXT, 890, 1.28) + 22
    return y


def point(item, s, idx, total, n=None):
    c = colour_for(item.get("category"))
    img = background(c)
    y = header(img, None, idx, total) + 40
    d = ImageDraw.Draw(img)
    num = f"{n or idx - 1:02d}"
    d.text((70, y), num, font=heavy(120), fill=c)
    y += 170
    tf, tl = fit(s["title"], heavy, 940, 3, 84, 54)
    for ln in tl:
        d.text((70, y), ln, font=tf, fill=TEXT)
        y += int(tf.size * 1.12)
    y += 40
    bf, bl = fit(s.get("body", ""), semi, 940, 9, 52, 36)
    for ln in bl:
        d.text((70, y), ln, font=bf, fill=(204, 214, 232))
        y += int(bf.size * 1.36)
    footer(img, swipe=True)
    return img


def stat(item, s, idx, total):
    img = background(AMBER)
    header(img, None, idx, total)
    d = ImageDraw.Draw(img)
    bf, bl = fit(s["big"], heavy, 940, 2, 220, 96, 6)
    lf, ll = fit(s.get("label", ""), semi, 900, 3, 54, 38)
    bh = int(bf.size * 1.05) * len(bl)
    lh = int(lf.size * 1.3) * len(ll)
    y = (H - bh - 50 - lh) // 2
    for ln in bl:
        d.text(((W - bf.getlength(ln)) / 2, y), ln, font=bf, fill=AMBER)
        y += int(bf.size * 1.05)
    y += 50
    for ln in ll:
        d.text(((W - lf.getlength(ln)) / 2, y), ln, font=lf, fill=TEXT)
        y += int(lf.size * 1.3)
    if s.get("note"):
        nf = medium(32)
        nl = wrap(s["note"], nf, 900)
        ny = H - 190 - int(nf.size * 1.3) * len(nl)
        for ln in nl:
            d.text(((W - nf.getlength(ln)) / 2, ny), ln, font=nf, fill=MUTED)
            ny += int(nf.size * 1.3)
    footer(img, swipe=True)
    return img


def actions(item, s, idx, total):
    img = background(GREEN)
    y = header(img, None, idx, total) + 50
    d = ImageDraw.Draw(img)
    tf, tl = fit(s.get("title", "What to do now"), heavy, 940, 2, 92, 60)
    for ln in tl:
        d.text((70, y), ln, font=tf, fill=TEXT)
        y += int(tf.size * 1.12)
    y += 50
    f = semi(44)
    for it in s["items"][:5]:
        d.rounded_rectangle([70, y + 4, 122, y + 56], radius=14, fill=(12, 58, 38), outline=GREEN, width=3)
        d.line([(82, y + 31), (93, y + 43), (111, y + 18)], fill=GREEN, width=6, joint="curve")
        y = text_block(d, 150, y, it, f, TEXT, 860, 1.28) + 34
    footer(img, swipe=True)
    return img


def closing(item, idx, total):
    c = colour_for(item.get("category"))
    img = background(c)
    header(img, None, idx, total)
    d = ImageDraw.Draw(img)
    q = item.get("question")
    y = 300
    if q:
        qf, ql = fit(q, heavy, 940, 4, 76, 50)
        for ln in ql:
            d.text((70, y), ln, font=qf, fill=TEXT)
            y += int(qf.size * 1.14)
        y += 24
        d.text((70, y), "Tell us in the comments.", font=semi(40), fill=c)
        y += 90
    st = item.get("send_to")
    if st:
        sf, sl = fit(f"↗ Send this to {st}", heavy, 940, 2, 56, 40)
        for ln in sl:
            d.text((70, y), ln, font=sf, fill=ACCENT)
            y += int(sf.size * 1.18)
        y += 40
    box_top = max(y, 760)
    d.rounded_rectangle([70, box_top, W - 70, box_top + 250], radius=36, fill=PANEL, outline=c, width=4)
    d.text((110, box_top + 40), f"Follow {HANDLE}", font=heavy(54), fill=TEXT)
    d.text((110, box_top + 120), "Daily attacks, flaws and AI security,", font=semi(38), fill=(200, 212, 230))
    d.text((110, box_top + 170), "explained in 60 seconds.", font=semi(38), fill=(200, 212, 230))
    src = ", ".join(s["name"] for s in item.get("sources", [])[:3])
    if src:
        sf = medium(28)
        sy = H - 170
        for ln in wrap("Sources: " + src, sf, 940)[:2]:
            d.text((70, sy), ln, font=sf, fill=MUTED)
            sy += 38
    d.text((70, H - 86), "Save this  ·  Share it with your team", font=medium(28), fill=MUTED)
    return img


def render_item(item, outdir):
    """Write PNGs for one carousel/card/reel item. Returns list of file names in slide order."""
    os.makedirs(outdir, exist_ok=True)
    kind = item["kind"]
    files = []
    if kind == "carousel":
        body = item.get("slides", [])
        total = 1 + len(body) + 1
        imgs = [cover(item, total, swipe=True)]
        pn = 0
        for k, s in enumerate(body, start=2):
            t = s.get("type", "point")
            if t == "stat":
                imgs.append(stat(item, s, k, total))
            elif t == "actions":
                imgs.append(actions(item, s, k, total))
            else:
                pn += 1
                imgs.append(point(item, s, k, total, pn))
        imgs.append(closing(item, total, total))
        for i, im in enumerate(imgs, start=1):
            name = f"slide-{i:02d}.jpg"
            im.convert("RGB").save(os.path.join(outdir, name), quality=92)
            files.append(name)
    else:   # card, and the X/thumbnail image for a reel
        im = cover(item, 1, swipe=False)
        name = "card.jpg" if kind == "card" else "cover.jpg"
        im.convert("RGB").save(os.path.join(outdir, name), quality=92)
        files.append(name)
    return files

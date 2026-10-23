#!/usr/bin/env python3
"""Render source-backed Cyber Intellect editorial JSON to public portrait PNGs."""
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
BG = "#071422"
INK = "#F0F8FF"
MUTED = "#9DB8C8"
ACCENT = "#42E4DD"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)

def wrapped(draw, text, x, y, maxwidth, f, color, leading=1.28, max_lines=None):
    words = str(text).split()
    lines, line = [], ""
    for word in words:
        candidate = (line + " " + word).strip()
        if draw.textbbox((0, 0), candidate, font=f)[2] > maxwidth and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" .") + "..."
    step = round(f.size * leading)
    for item in lines:
        draw.text((x, y), item, font=f, fill=color)
        y += step
    return y

def render(post, date, index):
    W, H = 1080, 1350
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        d.line((0, y, W, y), fill=(int(7 + t*8), int(20 + t*11), int(34 + t*19)))
    d.rounded_rectangle((62, 60, 1018, 1290), radius=36, outline="#225066", width=3)
    d.rounded_rectangle((94, 98, 486, 160), radius=20, fill="#123C4A")
    d.text((119, 112), "THE CYBER INTELLECT", font=font(25, True), fill=ACCENT)
    d.text((95, 210), post.get("category", "CYBER INTELLIGENCE").upper()[:48], font=font(27, True), fill=ACCENT)
    y = wrapped(d, post["title"], 94, 274, 875, font(63, True), INK, 1.17, 4)
    y += 45
    d.line((95, y, 980, y), fill=ACCENT, width=5)
    y += 40
    for bullet in post.get("bullets", [])[:4]:
        d.ellipse((99, y + 16, 115, y + 32), fill=ACCENT)
        y = wrapped(d, bullet, 140, y, 790, font(32), INK, 1.38, 3) + 26
        if y > 1000:
            break
    takeaway = post.get("takeaway", "")
    if takeaway:
        d.rounded_rectangle((94, 1085, 986, 1197), radius=18, fill="#133B4A")
        wrapped(d, "ACTION: " + takeaway, 117, 1102, 835, font(27, True), INK, 1.3, 2)
    d.text((95, 1235), "@thecyberintellect", font=font(24, True), fill=ACCENT)
    d.text((770, 1235), date, font=font(23), fill=MUTED)
    return im

def main():
    for source in sys.argv[1:]:
        p = Path(source)
        data = json.loads(p.read_text(encoding="utf-8"))
        if not data.get("posts"):
            raise ValueError(f"No posts: {p}")
        date = p.stem
        target = ROOT / "media" / date
        target.mkdir(parents=True, exist_ok=True)
        for i, post in enumerate(data["posts"][:3], 1):
            if not post.get("title") or not post.get("sources"):
                raise ValueError("Every post must include title and source URLs")
            out = target / f"{i:02}.png"
            render(post, date, i).save(out, optimize=True)
            print(out)

if __name__ == "__main__":
    main()

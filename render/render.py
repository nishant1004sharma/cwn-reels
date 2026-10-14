#!/usr/bin/env python3
"""Render a 1080x1920 reel for "Cybersecurity with Nishant".

Usage:
  python3 render/render.py --id D1-R01 [--audio media/D1-R01.mp3] [--align media/D1-R01.align.json] --out media/D1-R01.mp4

Without --audio it renders a silent preview timed at a natural speaking pace.
With --align (ElevenLabs character timestamps) segment changes follow the voice exactly;
with audio but no alignment, segments are spread across the audio by text length.
"""
import argparse, json, os, re, subprocess, sys
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ---------- brand ----------
BG_TOP = (6, 11, 24)
BG_BOT = (13, 25, 50)
GRID = (22, 38, 70)
TEXT = (241, 245, 249)
MUTED = (110, 128, 158)
ACCENT = (34, 211, 238)      # cyan
AMBER = (245, 158, 11)
GREEN = (34, 197, 94)
RED = (239, 68, 68)
PANEL = (15, 27, 52)
BRAND = "CYBERSECURITY WITH NISHANT"

FONT_DIRS = [os.path.join(HERE, "fonts"), "/usr/share/fonts/opentype/inter", "/usr/share/fonts/truetype/google-fonts"]

def font(name, size):
    for d in FONT_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size=size)

F_BRAND = font("Inter-SemiBold.otf", 30)
F_CHIP = font("Inter-Medium.otf", 30)

def heavy(size): return font("InterDisplay-Bold.otf", size)
def semi(size): return font("Inter-SemiBold.otf", size)

VIOLET = (167, 139, 250)

STYLE = {
    "default": (ACCENT, TEXT),
    "formula": (ACCENT, ACCENT),
    "answer": (GREEN, TEXT),
    "fact": (GREEN, TEXT),
    "myth": (RED, TEXT),
    "alert": (RED, TEXT),
    "stat": (AMBER, AMBER),
}
TAGS = {"myth": "MYTH", "fact": "FACT", "answer": "KEY POINT", "alert": "MISTAKE"}

# series chip colours (creator-style series stand out from exam prep)
def chip_colour(series):
    s = series.upper()
    if "BREACH" in s: return RED
    if "AI" in s.split() or "AI SECURITY" in s: return VIOLET
    if "MYTH" in s or "PHISH" in s or "TIP" in s: return AMBER
    return (70, 96, 140)

# ---------- text helpers ----------
def wrap(text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if fnt.getlength(t) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def fit(text, maker, max_w, max_lines, start, minimum):
    size = start
    while size >= minimum:
        f = maker(size)
        lines = wrap(text, f, max_w)
        if len(lines) <= max_lines and all(f.getlength(l) <= max_w for l in lines):
            return f, lines
        size -= 4
    f = maker(minimum)
    return f, wrap(text, f, max_w)

def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3

# ---------- timing ----------
def weight(say):
    return len(say) + 14 * say.count("...") + 6 * len(re.findall(r"[.?!](\s|$)", say))

def est_seconds(say):
    words = len(say.replace("...", " ").split())
    return words / 2.55 + 0.38 * say.count("...") + 0.22 * len(re.findall(r"[.?!](\s|$)", say)) + 0.15

def seg_times(segs, audio_len=None, align=None):
    says = [s["say"] for s in segs]
    if align:
        chars = align["characters"]; st = align["character_start_times_seconds"]; en = align["character_end_times_seconds"]
        full = "".join(chars)
        starts, pos = [], 0
        for s in says:
            idx = full.find(s[:12], pos)
            if idx < 0: idx = pos
            starts.append(st[min(idx, len(st) - 1)])
            pos = idx + len(s)
        end = en[-1]
        return [(starts[i], starts[i + 1] if i + 1 < len(starts) else end) for i in range(len(starts))], end
    if audio_len:
        ws = [weight(s) for s in says]; tot = sum(ws); t = 0.0; out = []
        for w in ws:
            d = audio_len * w / tot; out.append((t, t + d)); t += d
        return out, audio_len
    t, out = 0.25, []
    for s in says:
        d = est_seconds(s); out.append((t, t + d)); t += d
    return out, t

# ---------- static layers ----------
def background():
    col = Image.new("RGB", (1, H))
    for y in range(H):
        k = y / (H - 1)
        col.putpixel((0, y), tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * k) for i in range(3)))
    img = col.resize((W, H))
    d = ImageDraw.Draw(img)
    for x in range(0, W, 72): d.line([(x, 0), (x, H)], fill=GRID, width=1)
    for y in range(0, H, 72): d.line([(0, y), (W, y)], fill=GRID, width=1)
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([-260, 380, 620, 1260], fill=(10, 60, 90))
    gd.ellipse([560, 1050, 1400, 1890], fill=(40, 30, 90))
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    return ImageChops.add(img, glow)

def scan_band():
    band = Image.new("RGBA", (W, 160), (0, 0, 0, 0))
    d = ImageDraw.Draw(band)
    for i in range(160):
        a = int(26 * (1 - abs(i - 80) / 80))
        d.line([(0, i), (W, i)], fill=ACCENT + (a,))
    return band

def rounded_panel(w, h, border, fill=PANEL, r=36, bw=4):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=fill + (235,), outline=border + (255,), width=bw)
    return im

def stat_card(text):
    """'BIG|label' -> huge amber figure with a smaller label underneath."""
    big, _, label = text.partition("|")
    bf, bl = fit(big.strip(), heavy, 860, 1, 210, 90)
    lf, ll = fit(label.strip(), semi, 820, 2, 50, 36) if label.strip() else (semi(50), [])
    bh = int(bf.size * 1.05)
    lh = int(lf.size * 1.25)
    h = 120 + bh + (24 + lh * len(ll) if ll else 0)
    im = rounded_panel(940, max(320, h), AMBER)
    d = ImageDraw.Draw(im)
    y = (im.height - (bh + (24 + lh * len(ll) if ll else 0))) // 2 - 10
    d.text(((940 - bf.getlength(bl[0])) / 2, y), bl[0], font=bf, fill=AMBER)
    y += bh + 24
    for ln in ll:
        d.text(((940 - lf.getlength(ln)) / 2, y), ln, font=lf, fill=TEXT)
        y += lh
    return im

def card_image(text, style):
    if style == "stat":
        return stat_card(text)
    border, colour = STYLE.get(style or "default", STYLE["default"])
    f, lines = fit(text, heavy, 820, 3, 104, 56)
    lh = int(f.size * 1.18)
    tagged = style in TAGS
    pad = 56 if tagged else 0
    h = max(300, lh * len(lines) + 140 + pad)
    im = rounded_panel(940, h, border)
    d = ImageDraw.Draw(im)
    y = (h - lh * len(lines) + pad) // 2 - 6
    for ln in lines:
        d.text(((940 - f.getlength(ln)) / 2, y), ln, font=f, fill=colour)
        y += lh
    if tagged:
        tag = TAGS[style]
        tf = semi(30)
        tw = tf.getlength(tag) + 36
        d.rounded_rectangle([28, 24, 28 + tw, 72], radius=24, fill=border)
        d.text((46, 30), tag, font=tf, fill=(6, 11, 24))
    return im

def quiz_rows(q, state, dim=False):
    """state: 'ask' | 'reveal'"""
    rows = []
    for i, opt in enumerate(q["options"]):
        correct = i == q["answer"]
        if state == "reveal":
            border = GREEN if correct else (60, 72, 96)
            fill = (12, 58, 38) if correct else PANEL
            tc = TEXT if correct else MUTED
        else:
            border, fill, tc = (52, 82, 128), PANEL, TEXT
        im = rounded_panel(940, 116, border, fill=fill, r=28, bw=4)
        d = ImageDraw.Draw(im)
        letter = "ABCD"[i]
        d.rounded_rectangle([22, 20, 98, 96], radius=20, fill=(border if state == "reveal" and correct else (30, 52, 88)))
        lf = heavy(46)
        d.text((60 - lf.getlength(letter) / 2, 28), letter, font=lf, fill=TEXT)
        of, ol = fit(opt, semi, 760, 1, 50, 34)
        d.text((126, (116 - of.size) / 2 - 4), ol[0], font=of, fill=tc)
        if state == "reveal" and correct:
            d.line([(862, 60), (884, 82), (918, 38)], fill=GREEN, width=10, joint="curve")
        rows.append(im)
    return rows

# ---------- main render ----------
def render(reel, out, audio=None, align=None):
    audio_len = None
    if audio:
        audio_len = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", audio]).strip())
    segs = reel["segments"]
    times, speech_end = seg_times(segs, audio_len, align)
    total = max(speech_end, audio_len or 0) + 1.1
    nframes = int(total * FPS)

    bg = background().convert("RGBA")
    d0 = ImageDraw.Draw(bg)
    # brand + chip (static)
    x = 70
    for ch in BRAND:
        d0.text((x, 112), ch, font=F_BRAND, fill=ACCENT); x += F_BRAND.getlength(ch) + 3
    chip = reel.get("series", "CISSP").upper()
    cw = F_CHIP.getlength(chip) + 48
    cc = chip_colour(chip)
    if cc == (70, 96, 140):
        d0.rounded_rectangle([70, 168, 70 + cw, 222], radius=27, outline=cc, width=2)
        d0.text((94, 177), chip, font=F_CHIP, fill=(190, 205, 228))
    else:   # creator-style series: filled, coloured chip
        d0.rounded_rectangle([70, 168, 70 + cw, 222], radius=27, fill=cc)
        d0.text((94, 177), chip, font=F_CHIP, fill=(6, 11, 24))
    # hook headline: its own layer so it can pop in during the first half-second
    hf, hl = fit(reel["hook"], heavy, 940, 3, 84, 56)
    hook_h = int(hf.size * 1.14) * len(hl) + 40
    hook_layer = Image.new("RGBA", (W, hook_h), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hook_layer)
    y = 0
    for ln in hl:
        hd.text((70, y), ln, font=hf, fill=TEXT); y += int(hf.size * 1.14)
    hd.line([(70, y + 22), (190, y + 22)], fill=AMBER, width=8)
    hook_bottom = 268 + y
    band = scan_band()

    zone_top = max(620, hook_bottom + 70)
    cap_top = 1250

    # pre-render per-segment assets
    q = reel.get("quiz")
    cards, current = [], None
    for i, s in enumerate(segs):
        if s.get("card"):
            current = (card_image(s["card"], s.get("card_style")), i)
        if q and i <= q["reveal"]:
            cards.append(None)
        else:
            cards.append(current)
    ask_rows = quiz_rows(q, "ask") if q else None
    rev_rows = quiz_rows(q, "reveal") if q else None

    cap_layouts = []
    for s in segs:
        f, lines = fit(s["show"], semi, 930, 4, 58, 42)
        words, lh, y = [], int(f.size * 1.3), cap_top
        for ln in lines:
            lw = f.getlength(ln); x = (W - lw) / 2
            for w in ln.split(" "):
                words.append((w, x, y)); x += f.getlength(w + " ")
            y += lh
        cap_layouts.append((f, words))

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    if audio:
        cmd += ["-i", audio, "-filter_complex", "[1:a]apad[a]", "-map", "0:v", "-map", "[a]"]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-map", "0:v", "-map", "1:a"]
    cmd += ["-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    for fi in range(nframes):
        t = fi / FPS
        frame = bg.copy()
        # moving scan band
        frame.alpha_composite(band, (0, int((t * 260) % (H + 160)) - 160))
        # hook pops in (slide up + fade) over the first 0.45 s, then holds
        hp = ease(t / 0.45)
        if hp >= 1:
            frame.alpha_composite(hook_layer, (0, 268))
        elif hp > 0:
            hl_img = hook_layer.copy()
            hl_img.putalpha(hl_img.getchannel("A").point(lambda v, a_=hp: int(v * a_)))
            frame.alpha_composite(hl_img, (0, int(268 + (1 - hp) * 50)))
        d = ImageDraw.Draw(frame)
        # progress bar
        d.rounded_rectangle([60, 52, 1020, 62], radius=5, fill=(30, 44, 72))
        d.rounded_rectangle([60, 52, 60 + int(960 * min(1, t / total)), 62], radius=5, fill=ACCENT)
        # active segment
        si = 0
        for i, (a, b) in enumerate(times):
            if t >= a: si = i
        a, b = times[si]
        seg_t = t - a
        # centre zone: quiz or card
        if q and si <= q["reveal"]:
            rows = rev_rows if si == q["reveal"] else ask_rows
            ry = zone_top
            for k, row in enumerate(rows):
                appear = ease((t - times[0][0] - 0.12 * k) / 0.3) if si == 0 else 1.0
                if appear > 0:
                    rr = row.copy()
                    if appear < 1:
                        rr.putalpha(rr.getchannel("A").point(lambda v, a_=appear: int(v * a_)))
                    frame.alpha_composite(rr, (70, int(ry + (1 - appear) * 40)))
                ry += 134
            if si == q["reveal"] - 1:   # countdown bar while viewer locks in
                k = max(0.0, 1 - seg_t / max(0.1, b - a))
                d.rounded_rectangle([70, ry + 6, 1010, ry + 18], radius=6, fill=(30, 44, 72))
                d.rounded_rectangle([70, ry + 6, 70 + int(940 * k), ry + 18], radius=6, fill=AMBER)
        elif cards[si]:
            img, start_idx = cards[si]
            p = ease((t - times[start_idx][0]) / 0.28)
            sc = 0.9 + 0.1 * p
            im = img if sc >= 0.999 else img.resize((int(img.width * sc), int(img.height * sc)))
            if p < 1:
                im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v, a_=p: int(v * a_)))
            cy = zone_top + (520 - img.height) // 2
            frame.alpha_composite(im, (int((W - im.width) / 2), int(cy + (img.height - im.height) / 2)))
        # captions with word highlight
        f, words = cap_layouts[si]
        dur = max(0.2, (b - a) * 0.92)
        total_chars = sum(len(w) + 1 for w, _, _ in words)
        spoken = seg_t / dur * total_chars
        acc = 0
        for w, x, y in words:
            acc += len(w) + 1
            col = TEXT if acc <= spoken else (ACCENT if acc - len(w) - 1 <= spoken else MUTED)
            d.text((x, y), w, font=f, fill=col)
        proc.stdin.write(frame.convert("RGB").tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg failed")
    return total

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--bank", default=os.path.join(ROOT, "bank", "reels.json"))
    ap.add_argument("--audio")
    ap.add_argument("--align")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    reels = {r["id"]: r for r in json.load(open(a.bank))["reels"]}
    if a.id not in reels: sys.exit(f"unknown reel id {a.id}")
    align = json.load(open(a.align)) if a.align and os.path.exists(a.align) else None
    total = render(reels[a.id], a.out, a.audio, align)
    print(f"rendered {a.out} ({total:.1f}s)")

if __name__ == "__main__":
    main()

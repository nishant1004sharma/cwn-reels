#!/usr/bin/env python3
"""Check a news run file before it is pushed. Exits non-zero with a list of problems.

Usage: python3 claude-news/validate.py claude-news/content/2026-10-24-pm.json
"""
import json, os, re, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "state", "posted.json")
SERIES = {"Breach of the Day", "Patch Now in 15s", "AI Attack Explained", "Zero-Day Alert", "Myth vs Reality"}


def x_len(text):
    """Approximate X's weighted length: URLs = 23, wide chars/emoji = 2."""
    t = re.sub(r"https?://\S+", "x" * 23, text)
    n = 0
    for ch in t:
        cp = ord(ch)
        if cp in (0xFE0F, 0x200D):
            continue
        wide = cp > 0x2FFF or unicodedata.east_asian_width(ch) in ("W", "F")
        n += 2 if wide else 1
    return n


def main(path):
    data = json.load(open(path))
    probs = []
    posted = json.load(open(STATE))["posted"] if os.path.exists(STATE) else []
    seen_keys = {p["story_key"] for p in posted}
    ids, keys = set(), set()
    items = data.get("items", [])
    if not 1 <= len(items) <= 6:
        probs.append(f"expected 1-6 items, got {len(items)}")
    for it in items:
        i = it.get("id", "?")
        if i in ids:
            probs.append(f"{i}: duplicate id")
        ids.add(i)
        k = it.get("story_key", "")
        if not k:
            probs.append(f"{i}: missing story_key")
        if k in keys:
            probs.append(f"{i}: story_key repeated in this run")
        if k in seen_keys:
            probs.append(f"{i}: story_key {k} already posted on an earlier run")
        keys.add(k)
        if it.get("kind") not in ("reel", "carousel", "card", "diagram"):
            probs.append(f"{i}: kind must be reel|carousel|card|diagram")
        if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:00$", it.get("slot", "")):
            probs.append(f"{i}: slot must be YYYY-MM-DDTHH:MM:00 (Asia/Kuala_Lumpur)")
        srcs = it.get("sources") or []
        if not srcs or not all(s.get("url", "").startswith("http") and s.get("name") for s in srcs):
            probs.append(f"{i}: needs sources with name + url")
        x = it.get("x_text", "")
        if not x or x_len(x) > 270:
            probs.append(f"{i}: x_text missing or too long ({x_len(x)} > 270)")
        if not 1 <= len(re.findall(r"#\w+", x)) <= 2:
            probs.append(f"{i}: x_text needs 1-2 specific hashtags at the end (e.g. #ZeroDay #CyberSecurity)")
        th = it.get("x_thread")
        if th is not None:
            if not 5 <= len(th) <= 8 or any(x_len(t) > 270 for t in th):
                probs.append(f"{i}: x_thread needs 5-8 posts of <= 270 characters each")
            if th and th[0] != x:
                probs.append(f"{i}: x_thread[0] must equal x_text (the hook post)")
        if not it.get("send_to") or len(it["send_to"]) > 40:
            probs.append(f"{i}: send_to (who to send it to, <= 40 chars) is required")
        cap = it.get("ig_caption", "")
        if "send this to" not in cap.lower():
            probs.append(f"{i}: ig_caption must include a 'Send this to ...' line")
        if not cap or len(cap) > 2000:
            probs.append(f"{i}: ig_caption missing or > 2000 chars")
        tags = re.findall(r"#\w+", cap)
        if not 3 <= len(tags) <= 8:
            probs.append(f"{i}: ig_caption needs 3-8 hashtags, has {len(tags)}")
        if "source" not in cap.lower():
            probs.append(f"{i}: ig_caption needs a 'Source:' line")
        cov = it.get("cover", {})
        if it.get("kind") in ("carousel", "card"):
            if not cov.get("hook") or len(cov["hook"]) > 90:
                probs.append(f"{i}: cover.hook missing or > 90 chars")
            if cov.get("sub") and len(cov["sub"]) > 170:
                probs.append(f"{i}: cover.sub > 170 chars")
        if it.get("kind") == "carousel":
            sl = it.get("slides", [])
            if not 3 <= len(sl) <= 6:
                probs.append(f"{i}: carousel needs 3-6 body slides")
            for n, s in enumerate(sl):
                t = s.get("type", "point")
                if t == "point" and (not s.get("title") or len(s.get("body", "")) > 260):
                    probs.append(f"{i}: slide {n} point needs title, body <= 260 chars")
                if t == "stat" and not s.get("big"):
                    probs.append(f"{i}: slide {n} stat needs big")
                if t == "actions" and not 2 <= len(s.get("items", [])) <= 5:
                    probs.append(f"{i}: slide {n} actions needs 2-5 items")
        if it.get("kind") == "card":
            b = it.get("bullets", [])
            if not 2 <= len(b) <= 4 or any(len(x) > 95 for x in b):
                probs.append(f"{i}: card needs 2-4 bullets of <= 95 chars")
        if it.get("kind") == "diagram":
            dg = it.get("diagram", {})
            hp = os.path.join(os.path.dirname(HERE), dg.get("html", ""))
            if not dg.get("title") or len(dg["title"]) > 60:
                probs.append(f"{i}: diagram.title missing or > 60 chars")
            if not dg.get("html", "").startswith("claude-news/diagrams/") or not os.path.isfile(hp):
                probs.append(f"{i}: diagram.html must be an existing file under claude-news/diagrams/")
            else:
                h = open(hp).read()
                if not re.search(r'class="flow[GR]?"', h):
                    probs.append(f"{i}: diagram has no animated arrows (class flow / flowG / flowR)")
                if 'width="1080" height="1350"' not in h:
                    probs.append(f"{i}: diagram svg must be 1080x1350")
                if "send this to" not in h.lower():
                    probs.append(f"{i}: diagram needs a '↗ Send this to ...' line")
            if not 6 <= int(dg.get("seconds", 8)) <= 12:
                probs.append(f"{i}: diagram.seconds should be 6-12")
        if it.get("kind") == "reel":
            r = it.get("reel", {})
            segs = r.get("segments", [])
            if not r.get("hook") or len(r["hook"]) > 45 or not 3 <= len(segs) <= 5:
                probs.append(f"{i}: reel needs a hook of <= 45 chars and 3-5 segments")
            words = sum(len(s.get("say", "").replace("...", " ").split()) for s in segs)
            if not 35 <= words <= 55:
                probs.append(f"{i}: reel spoken words {words}, want 35-55 (about 13-20 s)")
            if r.get("series") not in SERIES:
                probs.append(f"{i}: reel.series must be one of {sorted(SERIES)}")
            if segs and "send this" not in segs[-1].get("say", "").lower():
                probs.append(f"{i}: last reel segment must be the sendable ending ('Send this to ...')")
            if segs and not segs[0].get("card"):
                probs.append(f"{i}: first reel segment needs a card (the shock number/fact on screen at 0 s)")

            for n, s in enumerate(segs):
                if not s.get("say") or not s.get("show"):
                    probs.append(f"{i}: reel segment {n} needs say + show")
                if re.search(r"CVE-\d", s.get("say", "")):
                    probs.append(f"{i}: segment {n} 'say' reads a CVE id aloud; keep CVE ids in 'show'/'card' only")
    kinds = [it.get("kind") for it in items]
    if len(items) == 5 and (kinds.count("reel") != 3 or kinds.count("carousel") + kinds.count("diagram") != 2
                            or kinds.count("diagram") > 1):
        probs.append(f"a full run is 3 reels + 2 carousels (or 1 carousel + 1 diagram), got {kinds}")
    li = [it for it in items if it.get("linkedin")]
    if len(li) > 1:
        probs.append("at most 1 LinkedIn item per run")
    for it in li:
        if it.get("kind") != "carousel" or not it.get("li_text") or len(it["li_text"]) > 2800:
            probs.append(f"{it.get('id')}: LinkedIn item must be a carousel with li_text <= 2800 chars")
    if probs:
        print("PROBLEMS:\n- " + "\n- ".join(probs))
        sys.exit(1)
    print(f"ok: {len(items)} items")


if __name__ == "__main__":
    main(sys.argv[1])

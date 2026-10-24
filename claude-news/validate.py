#!/usr/bin/env python3
"""Check a news run file before it is pushed. Exits non-zero with a list of problems.

Usage: python3 claude-news/validate.py claude-news/content/2026-10-24-pm.json
"""
import json, os, re, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "state", "posted.json")


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
        if it.get("kind") not in ("reel", "carousel", "card"):
            probs.append(f"{i}: kind must be reel|carousel|card")
        if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:00$", it.get("slot", "")):
            probs.append(f"{i}: slot must be YYYY-MM-DDTHH:MM:00 (Asia/Kuala_Lumpur)")
        srcs = it.get("sources") or []
        if not srcs or not all(s.get("url", "").startswith("http") and s.get("name") for s in srcs):
            probs.append(f"{i}: needs sources with name + url")
        x = it.get("x_text", "")
        if not x or x_len(x) > 270:
            probs.append(f"{i}: x_text missing or too long ({x_len(x)} > 270)")
        if x.count("#") > 2:
            probs.append(f"{i}: x_text max 2 hashtags")
        cap = it.get("ig_caption", "")
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
        if it.get("kind") == "reel":
            r = it.get("reel", {})
            segs = r.get("segments", [])
            if not r.get("hook") or not 5 <= len(segs) <= 9:
                probs.append(f"{i}: reel needs hook and 5-9 segments")
            words = sum(len(s.get("say", "").replace("...", " ").split()) for s in segs)
            if not 60 <= words <= 125:
                probs.append(f"{i}: reel spoken words {words}, want 60-125")
            for n, s in enumerate(segs):
                if not s.get("say") or not s.get("show"):
                    probs.append(f"{i}: reel segment {n} needs say + show")
                if re.search(r"CVE-\d", s.get("say", "")):
                    probs.append(f"{i}: segment {n} 'say' reads a CVE id aloud; keep CVE ids in 'show'/'card' only")
    if probs:
        print("PROBLEMS:\n- " + "\n- ".join(probs))
        sys.exit(1)
    print(f"ok: {len(items)} items")


if __name__ == "__main__":
    main(sys.argv[1])

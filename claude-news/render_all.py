#!/usr/bin/env python3
"""Render every item of one news run file into images / voiced reels and write a manifest.

Usage: python3 claude-news/render_all.py claude-news/content/2026-10-24-pm.json --out out

Output: out/<run>/<item id>/slide-NN.jpg | card.jpg | reel.mp4, and out/<run>/manifest.json
with the public URLs the media will have on the claude-news-media branch.
"""
import argparse, json, os, subprocess, sys, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "render"))

import cards, news_tts as tts  # noqa: E402
import render as reelr       # noqa: E402  (render/render.py from the reels pipeline)

RAW = "https://raw.githubusercontent.com/nishant1004sharma/cwn-reels/claude-news-media"

reelr.BRAND = cards.BRAND
# News reels: everything pops in 3x faster than the CISSP reels, so the hook and first
# card are fully on screen within ~0.15 s (watch time on this account was ~2 s).
_ease = reelr.ease
reelr.ease = lambda x: _ease(x * 3)


reelr.chip_colour = lambda series: cards.colour_for(series)


def probe(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
                                   "-of", "json", path])
    j = json.loads(out)
    vid = [s for s in j["streams"] if s["codec_type"] == "video"]
    aud = [s for s in j["streams"] if s["codec_type"] == "audio"]
    return float(j["format"]["duration"]), (vid[0]["width"], vid[0]["height"]) if vid else None, bool(aud)


def render_reel(item, outdir):
    reel = dict(item["reel"])
    reel.setdefault("series", item.get("category", "News").title())
    text = " ".join(s["say"] for s in reel["segments"])
    mp3, al = os.path.join(outdir, "voice.mp3"), os.path.join(outdir, "voice.align.json")
    mp3, al, voice = tts.speak(text, mp3, al)
    align = json.load(open(al)) if al and os.path.exists(al) else None
    out = os.path.join(outdir, "reel.mp4")
    reelr.render(reel, out, mp3, align)
    dur, size, has_audio = probe(out)
    if size != (1080, 1920) or not has_audio or not (12 <= dur <= 70):
        raise RuntimeError(f"reel check failed: {size}, audio={has_audio}, {dur:.1f}s")
    for f in (mp3, al):
        if f and os.path.exists(f):
            os.remove(f)
    return ["reel.mp4"], voice, round(dur, 1)


def render_diagram(item, outdir):
    import diagram_render
    html = os.path.join(ROOT, item["diagram"]["html"])
    out = os.path.join(outdir, "diagram.mp4")
    diagram_render.render(html, out, int(item["diagram"].get("seconds", 8)))
    dur, size, has_audio = probe(out)
    if size != (1080, 1350) or not (5 <= dur <= 20):
        raise RuntimeError(f"diagram check failed: {size}, {dur:.1f}s")
    return ["diagram.mp4", "diagram-cover.jpg"], round(dur, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("content")
    ap.add_argument("--out", default="out")
    ap.add_argument("--only", help="comma-separated item ids")
    a = ap.parse_args()
    data = json.load(open(a.content))
    run = os.path.splitext(os.path.basename(a.content))[0]
    base = os.path.join(a.out, run)
    os.makedirs(base, exist_ok=True)
    only = set(a.only.split(",")) if a.only else None
    manifest = {"run": run, "items": {}, "errors": {}}
    for item in data["items"]:
        iid = item["id"]
        if only and iid not in only:
            continue
        d = os.path.join(base, iid)
        os.makedirs(d, exist_ok=True)
        try:
            entry = {"kind": item["kind"]}
            if item["kind"] == "reel":
                files, voice, dur = render_reel(item, d)
                entry.update(voice=voice, seconds=dur)
            elif item["kind"] == "diagram":
                files, dur = render_diagram(item, d)
                entry.update(seconds=dur)
            else:
                files = cards.render_item(item, d)
            entry["files"] = files
            entry["media"] = [f"{RAW}/{run}/{iid}/{f}" for f in files]
            manifest["items"][iid] = entry
            print(f"ok   {iid} {item['kind']} -> {files} {entry.get('voice', '')}")
        except Exception as e:
            traceback.print_exc()
            manifest["errors"][iid] = str(e)[:400]
            print(f"FAIL {iid}: {e}")
    json.dump(manifest, open(os.path.join(base, "manifest.json"), "w"), indent=2)
    print(json.dumps({"ok": len(manifest["items"]), "failed": len(manifest["errors"])}))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Print the Metricool createScheduledPost calls for one rendered run.

Usage: python3 claude-news/payloads.py claude-news/content/2026-10-24-pm.json manifest.json --networks instagram,twitter

Prints a JSON list: [{"item": id, "network": n, "date": "...+08:00", "info": "<json string for the info field>"}, ...]
Pass each entry's date and info straight to createScheduledPost (blogId from getBrandSettings).
Items that failed to render (missing from the manifest) are skipped and listed on stderr.
"""
import argparse, json, sys

TZ = "Asia/Kuala_Lumpur"


def base(text, media, slot):
    return {
        "autoPublish": True, "descendants": [], "draft": False, "firstCommentText": "",
        "hasNotReadNotes": False, "media": media, "mediaAltText": [], "shortener": False,
        "smartLinkData": {"ids": []}, "text": text,
        "publicationDate": {"dateTime": slot, "timezone": TZ},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("content")
    ap.add_argument("manifest")
    ap.add_argument("--networks", default="instagram")
    a = ap.parse_args()
    content = json.load(open(a.content))
    man = json.load(open(a.manifest))
    nets = [n.strip() for n in a.networks.split(",") if n.strip()]
    out = []
    for it in content["items"]:
        m = man["items"].get(it["id"])
        if not m:
            print(f"skip {it['id']}: not rendered ({man['errors'].get(it['id'], 'missing')})", file=sys.stderr)
            continue
        media = m["media"]
        slot = it["slot"]
        if "instagram" in nets:
            p = base(it["ig_caption"], media, slot)
            p["providers"] = [{"network": "instagram"}]
            if it["kind"] == "reel":
                p["instagramData"] = {"type": "REEL", "showReelOnFeed": True, "isAiGenerated": True}
            else:
                p["instagramData"] = {"type": "POST", "isAiGenerated": False}
            out.append({"item": it["id"], "network": "instagram", "date": slot + "+08:00", "info": json.dumps(p, ensure_ascii=False)})
        if "twitter" in nets:
            x_media = media if it["kind"] == "reel" else media[:1]
            p = base(it["x_text"], x_media, slot)
            p["providers"] = [{"network": "twitter"}]
            p["twitterData"] = {"tags": []}
            out.append({"item": it["id"], "network": "twitter", "date": slot + "+08:00", "info": json.dumps(p, ensure_ascii=False)})
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

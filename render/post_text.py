#!/usr/bin/env python3
"""Print the Metricool post fields for one reel as JSON.

Usage: python3 render/post_text.py --id C-R02
Output: {"title": ..., "text": ..., "tags": [...]}
Use "text" exactly as the post text (it already holds the caption, the course link and the hashtags).
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_config, post_text, BANK

ap = argparse.ArgumentParser()
ap.add_argument("--id", required=True)
a = ap.parse_args()
reels = {r["id"]: r for r in json.load(open(BANK))["reels"]}
if a.id not in reels:
    sys.exit(f"unknown reel id {a.id}")
r = reels[a.id]
print(json.dumps({
    "title": r["post"]["title"],
    "text": post_text(r, load_config()),
    "tags": [h.lstrip("#") for h in r["post"]["hashtags"]],
}, ensure_ascii=False, indent=2))

#!/usr/bin/env python3
"""Post today's CISSP Short on X (@CISMNishant) through Typefully, with the Udemy course link in a reply.

Usage: python3 render/x_post.py [--dry-run]
Runs in GitHub Actions (workflow "CISSP Short on X") after state/published.json is pushed.
Needs env TYPEFULLY_API_KEY (repo secret); optional TYPEFULLY_SOCIAL_SET_ID.
For every reel recorded as posted today (Asia/Kuala_Lumpur) it uploads media/<id>.mp4 and schedules a
2-post X thread at 11:05 KL (or 10 min from now if that has passed):
  1. the reel's hook + one-line caption + 2 hashtags, with the video
  2. the Udemy course link (config.json course_url)
Idempotent: the Typefully draft title is "cissp-<id>", never created twice. No Metricool, no "Made with AI" label.
Never fails the workflow.
"""
import argparse, datetime, importlib.util, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "render"))
from common import load_config, BANK  # noqa: E402

spec = importlib.util.spec_from_file_location("tf", os.path.join(ROOT, "claude-news", "typefully_post.py"))
tf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tf)
KL = tf.KL


def x_text(reel):
    hook = re.sub(r"\s*#Shorts\s*$", "", reel["post"]["title"]).strip()
    cap = (reel["post"].get("caption") or "").strip()
    first = re.split(r"(?<=[.!?])\s", cap, maxsplit=1)[0] if cap else ""
    tags = " ".join(h if h.startswith("#") else "#" + h for h in reel["post"]["hashtags"] if h.lstrip("#") != "Shorts")
    tags = " ".join(tags.split()[:2])
    text = f"{hook}\n\n{first}\n\n{tags}".replace("\n\n\n\n", "\n\n").strip()
    if len(text) > 275:
        text = f"{hook}\n\n{tags}"
    return text[:280]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    today = datetime.datetime.now(KL).date().isoformat()
    posted = [p for p in json.load(open(os.path.join(ROOT, "state", "published.json")))["posted"]
              if p.get("status") == "posted" and p.get("date") == today]
    if not posted:
        print(f"no CISSP reel posted on {today}")
        return
    reels = {r["id"]: r for r in json.load(open(BANK))["reels"]}
    cfg = load_config()
    link = f"🎓 Full CISSP course on Udemy: {cfg['course_url']}"
    slot = datetime.datetime.fromisoformat(f"{today}T11:05:00").replace(tzinfo=KL)
    for p in posted:
        r = reels.get(p["id"])
        if not r:
            print(f"skip {p['id']}: not in bank")
            continue
        posts = [{"text": x_text(r), "made_with_ai": False}, {"text": link, "made_with_ai": False}]
        if a.dry_run or not os.environ.get("TYPEFULLY_API_KEY"):
            print(("DRY " if a.dry_run else "TYPEFULLY_API_KEY not set: ") + json.dumps(posts, ensure_ascii=False))
            continue
        try:
            ss = os.environ.get("TYPEFULLY_SOCIAL_SET_ID") or tf.call("GET", "/social-sets")["results"][0]["id"]
            title = f"cissp-{p['id']}"
            existing = set()
            for status in ("scheduled", "published", "publishing", "draft"):
                for d in tf.call("GET", f"/social-sets/{ss}/drafts?limit=50&status={status}").get("results", []):
                    existing.add(d.get("draft_title"))
            if title in existing:
                print(f"skip {p['id']}: already on Typefully")
                continue
            video = os.path.join(ROOT, "media", f"{p['id']}.mp4")
            if not os.path.exists(video):
                print(f"skip {p['id']}: {video} missing")
                continue
            posts[0]["media_ids"] = [tf.upload(ss, video, re.sub(r"\s*#Shorts\s*$", "", r["post"]["title"]))]
            at = max(slot, datetime.datetime.now(KL) + datetime.timedelta(minutes=10)).replace(microsecond=0)
            d = tf.call("POST", f"/social-sets/{ss}/drafts",
                        {"draft_title": title, "platforms": {"x": {"enabled": True, "posts": posts}},
                         "publish_at": at.isoformat()})
            print(f"scheduled {p['id']} on X at {d.get('scheduled_date')} (draft {d.get('id')})")
        except Exception as e:
            body = e.read()[:300] if hasattr(e, "read") else b""
            print(f"FAIL {p['id']}: {e} {body!r}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"x_post error: {e}")
    sys.exit(0)

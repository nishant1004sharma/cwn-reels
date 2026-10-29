#!/usr/bin/env python3
"""Publish due news posts to Instagram through Instagram's own API (no Metricool). Runs every 10 min in Actions.

Usage: python3 claude-news/ig_publish.py --media media --content claude-news/content [--dry-run]

  --media    checkout of the claude-news-media branch (run folders with manifest.json and the media)
  --content  folder with the run files (ig_caption, kind, slot per item)

Env: IG_ACCESS_TOKEN (Instagram User token, Instagram API with Instagram Login,
     permissions instagram_business_basic + instagram_business_content_publish).
     TOKEN_DIR (optional): where a refreshed token is kept between runs (the workflow encrypts and caches it).

An item is due when its slot (Asia/Kuala_Lumpur) has passed and is less than 3 hours old. Before publishing,
the account's recent posts are checked: if one already starts with the same caption line, the item is skipped,
so re-runs and overlapping runs never double-post. At most 3 posts per run. Never fails the workflow.
"""
import argparse, datetime, glob, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

G = "https://graph.instagram.com/v26.0"
KL = datetime.timezone(datetime.timedelta(hours=8))
MAX_PER_RUN = 3
WINDOW = datetime.timedelta(hours=3)


def req(method, url, token, params=None):
    params = dict(params or {})
    data = None
    if method == "GET":
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    else:
        data = urllib.parse.urlencode(params).encode()
    r = urllib.request.Request(url, data=data, method=method, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {url.split('?')[0]} -> {e.code}: {e.read()[:300]!r}")


def key(caption):
    """Normalised first line of a caption, used to recognise a post we already published."""
    first = (caption or "").strip().split("\n")[0]
    return re.sub(r"\W+", " ", first).strip().lower()[:80]


def load_token():
    tdir = os.environ.get("TOKEN_DIR")
    if tdir and os.path.exists(os.path.join(tdir, "token.txt")):
        tok = open(os.path.join(tdir, "token.txt")).read().strip()
        at = open(os.path.join(tdir, "refreshed_at.txt")).read().strip() if os.path.exists(os.path.join(tdir, "refreshed_at.txt")) else ""
        if tok:
            return tok, at
    return os.environ.get("IG_ACCESS_TOKEN", "").strip(), ""


def maybe_refresh(token, refreshed_at):
    """Long-lived tokens last 60 days; refresh weekly and keep the new one for the next runs."""
    tdir = os.environ.get("TOKEN_DIR")
    if not tdir:
        return token
    now = datetime.datetime.now(datetime.timezone.utc)
    if refreshed_at:
        try:
            if now - datetime.datetime.fromisoformat(refreshed_at) < datetime.timedelta(days=7):
                return token
        except ValueError:
            pass
    try:
        r = req("GET", "https://graph.instagram.com/refresh_access_token", token, {"grant_type": "ig_refresh_token", "access_token": token})
        new = r.get("access_token")
        if new:
            os.makedirs(tdir, exist_ok=True)
            open(os.path.join(tdir, "token.txt"), "w").write(new)
            open(os.path.join(tdir, "refreshed_at.txt"), "w").write(now.isoformat())
            open(os.path.join(tdir, "REFRESHED"), "w").write("1")
            print(f"token refreshed, expires in {r.get('expires_in')} s")
            return new
    except Exception as e:
        print(f"token refresh skipped: {e}")   # e.g. token younger than 24 h
    return token


def wait_ready(cid, token, tries=20, pause=15):
    for _ in range(tries):
        st = req("GET", f"{G}/{cid}", token, {"fields": "status_code"}).get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {cid} {st}")
        time.sleep(pause)
    raise RuntimeError(f"container {cid} not ready after {tries * pause} s")


def publish(ig, token, item, urls):
    cap = item["ig_caption"]
    if item["kind"] in ("reel", "diagram"):
        params = {"media_type": "REELS", "video_url": urls[0], "caption": cap, "share_to_feed": "true"}
        if item["kind"] == "diagram" and len(urls) > 1:
            params["cover_url"] = urls[1]      # first frame as the grid cover
        c = req("POST", f"{G}/{ig}/media", token, params)["id"]
        wait_ready(c, token)
    elif len(urls) > 1:
        kids = [req("POST", f"{G}/{ig}/media", token, {"image_url": u, "is_carousel_item": "true"})["id"] for u in urls[:20]]
        for k in kids:
            wait_ready(k, token, tries=12, pause=5)
        c = req("POST", f"{G}/{ig}/media", token, {"media_type": "CAROUSEL", "children": ",".join(kids), "caption": cap})["id"]
        wait_ready(c, token, tries=12, pause=5)
    else:
        c = req("POST", f"{G}/{ig}/media", token, {"image_url": urls[0], "caption": cap})["id"]
        wait_ready(c, token, tries=12, pause=5)
    return req("POST", f"{G}/{ig}/media_publish", token, {"creation_id": c}).get("id")


def due_items(media_dir, content_dir, now):
    out = []
    for man_path in sorted(glob.glob(os.path.join(media_dir, "*", "manifest.json"))):
        run = os.path.basename(os.path.dirname(man_path))
        cpath = os.path.join(content_dir, run + ".json")
        if not os.path.exists(cpath):
            continue
        man = json.load(open(man_path))
        for it in json.load(open(cpath))["items"]:
            m = man["items"].get(it["id"])
            if not m or not it.get("ig_caption"):
                continue
            slot = datetime.datetime.fromisoformat(it["slot"]).replace(tzinfo=KL)
            if slot <= now <= slot + WINDOW:
                out.append((slot, it, m["media"]))
    return sorted(out, key=lambda x: x[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--media", default="media")
    ap.add_argument("--content", default="claude-news/content")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--now", help="override current time (ISO, for tests)")
    a = ap.parse_args()
    now = datetime.datetime.fromisoformat(a.now) if a.now else datetime.datetime.now(KL)
    due = due_items(a.media, a.content, now)
    print(f"{len(due)} item(s) due at {now.isoformat(timespec='minutes')}")
    if not due:
        return
    token, refreshed_at = load_token()
    if not token:
        print("IG_ACCESS_TOKEN not set: nothing published")
        return
    if a.dry_run:
        for slot, it, urls in due:
            print(f"DRY {it['id']} {it['kind']} {slot:%H:%M} {len(urls)} media | {key(it['ig_caption'])}")
        return
    token = maybe_refresh(token, refreshed_at)
    me = req("GET", f"{G}/me", token, {"fields": "user_id,username"})
    ig = me.get("user_id") or me.get("id")
    recent = req("GET", f"{G}/{ig}/media", token, {"fields": "caption,timestamp", "limit": 50}).get("data", [])
    seen = {key(m.get("caption")) for m in recent}
    done = 0
    for slot, it, urls in due:
        if key(it["ig_caption"]) in seen:
            print(f"skip {it['id']}: already on @{me.get('username')}")
            continue
        if done >= MAX_PER_RUN:
            print(f"later {it['id']}: {MAX_PER_RUN} per run")
            continue
        try:
            mid = publish(ig, token, it, urls)
            seen.add(key(it["ig_caption"]))
            done += 1
            print(f"published {it['id']} ({it['kind']}) as {mid}")
        except Exception as e:
            print(f"FAIL {it['id']}: {e}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ig_publish error: {e}")
    sys.exit(0)

#!/usr/bin/env python3
"""Schedule a run's X posts through Typefully (runs in GitHub Actions, which can reach Typefully's storage).

Usage: python3 claude-news/typefully_post.py claude-news/content/2026-10-24-pm.json --out out

Needs env TYPEFULLY_API_KEY (repo secret). Optional TYPEFULLY_SOCIAL_SET_ID (default: first social set).
For every rendered item (out/<run>/manifest.json): uploads the cover image (carousel/card) or the reel video,
then creates a draft scheduled at the item's slot (Asia/Kuala_Lumpur) on X, plus Threads and Bluesky when
they are connected to the same Typefully social set. Same text everywhere: the item's x_text.
Idempotent: a draft whose title is the item id is never created twice.
Writes out/<run>/typefully.json with what was scheduled. Never fails the workflow.
"""
import argparse, datetime, http.client, json, os, sys, time, urllib.error, urllib.parse, urllib.request

API = "https://api.typefully.com/v2"
KL = datetime.timezone(datetime.timedelta(hours=8))


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + os.environ["TYPEFULLY_API_KEY"],
                                          "Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        return json.loads(raw) if raw else {}


def upload(ss, path, alt):
    up = call("POST", f"/social-sets/{ss}/media/upload",
              {"file_name": os.path.basename(path), "alt_text": alt[:1000] if alt else None})
    data = open(path, "rb").read()
    # Presigned S3 PUT: raw bytes and NO Content-Type (urllib would add one and break the signature).
    u = urllib.parse.urlsplit(up["upload_url"])
    conn = http.client.HTTPSConnection(u.netloc, timeout=300)
    conn.request("PUT", u.path + ("?" + u.query if u.query else ""), body=data,
                 headers={"Content-Length": str(len(data))})
    r = conn.getresponse()
    body = r.read()
    if r.status not in (200, 204):
        raise RuntimeError(f"upload failed {r.status}: {body[:200]!r}")
    for _ in range(60):                       # wait for processing (videos can take a while)
        st = call("GET", f"/social-sets/{ss}/media/{up['media_id']}").get("status")
        if st == "ready":
            return up["media_id"]
        if st == "failed":
            raise RuntimeError("media processing failed")
        time.sleep(5)
    raise RuntimeError("media not ready after 5 minutes")


def when(slot, n):
    """The item's slot, or, if that has passed, 10 min from now plus 5 min per item so posts don't bunch up."""
    t = datetime.datetime.fromisoformat(slot).replace(tzinfo=KL)
    soon = datetime.datetime.now(KL) + datetime.timedelta(minutes=10 + 5 * n)
    return max(t, soon).replace(microsecond=0).isoformat()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("content")
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    run = os.path.splitext(os.path.basename(a.content))[0]
    base = os.path.join(a.out, run)
    result = {"run": run, "scheduled": {}, "skipped": {}, "errors": {}}
    try:
        if not os.environ.get("TYPEFULLY_API_KEY"):
            result["errors"]["_"] = "TYPEFULLY_API_KEY not set"
            return result
        content = json.load(open(a.content))
        man = json.load(open(os.path.join(base, "manifest.json")))
        ss = os.environ.get("TYPEFULLY_SOCIAL_SET_ID") or call("GET", "/social-sets")["results"][0]["id"]
        det = call("GET", f"/social-sets/{ss}")
        nets = [p for p in ("x", "threads", "bluesky") if det["platforms"].get(p)]
        quota = det.get("publishing_quota") or {}
        result.update(social_set=ss, networks=nets, quota_before=quota)
        if "x" not in nets:
            result["errors"]["_"] = "X is not connected to this Typefully social set"
            return result
        existing = set()
        for status in ("scheduled", "published", "publishing", "draft"):
            for d in call("GET", f"/social-sets/{ss}/drafts?limit=50&status={status}").get("results", []):
                existing.add(d.get("draft_title"))
        remaining = quota.get("remaining")
        for n, it in enumerate(content["items"]):
            iid = it["id"]
            m = man["items"].get(iid)
            if not m:
                result["skipped"][iid] = "not rendered"
                continue
            if it.get("x") is not True:          # Typefully free plan: ~10 posts/month, so only items marked "x": true go to X
                result["skipped"][iid] = "not marked for X"
                continue
            if iid in existing:
                result["skipped"][iid] = "already scheduled"
                continue
            if remaining is not None and remaining <= 0:
                result["skipped"][iid] = "Typefully publishing quota used up"
                continue
            try:
                f = {"reel": "reel.mp4", "diagram": "diagram.mp4"}.get(it["kind"], m["files"][0])
                alt = (it.get("cover") or {}).get("hook") or (it.get("reel") or {}).get("hook", "") or (it.get("diagram") or {}).get("title", "")
                media_id = upload(ss, os.path.join(base, iid, f), alt)
                # Weekly thread: x_thread holds 5-8 posts; the first carries the media. Otherwise a single post.
                texts = it.get("x_thread") or [it["x_text"]]
                posts = [{"text": t} for t in texts]
                posts[0]["media_ids"] = [media_id]
                platforms = {"x": {"enabled": True, "posts": [dict(q, made_with_ai=False) for q in posts]}}   # Nishant: no "Made with AI" label on X
                for p in nets:
                    if p != "x":
                        platforms[p] = {"enabled": True, "posts": posts}
                d = call("POST", f"/social-sets/{ss}/drafts",
                         {"draft_title": iid, "platforms": platforms, "publish_at": when(it["slot"], n)})
                result["scheduled"][iid] = {"draft_id": d.get("id"), "at": d.get("scheduled_date"), "networks": nets}
                if remaining is not None:
                    remaining -= 1
                print(f"scheduled {iid} on {nets} at {d.get('scheduled_date')}")
            except urllib.error.HTTPError as e:
                result["errors"][iid] = f"HTTP {e.code}: {e.read()[:300]!r}"
                print(f"FAIL {iid}: {result['errors'][iid]}")
            except Exception as e:
                result["errors"][iid] = str(e)[:300]
                print(f"FAIL {iid}: {e}")
    except Exception as e:
        result["errors"]["_"] = str(e)[:300]
    finally:
        os.makedirs(base, exist_ok=True)
        json.dump(result, open(os.path.join(base, "typefully.json"), "w"), indent=2)
        print(json.dumps({k: (len(v) if isinstance(v, dict) else v) for k, v in result.items()}))
    return result


if __name__ == "__main__":
    main()
    sys.exit(0)

#!/usr/bin/env python3
"""Publish due news posts as YouTube Shorts through the YouTube Data API. Runs every 10 min in Actions.

Usage: python3 claude-news/yt_publish.py --media media --content claude-news/content [--dry-run] [--build-only DIR]

Same content and slots as Instagram (claude-news/ig_publish.py), on the CISSP channel:
  reel     -> reel.mp4 (1080x1920, voiced) as is
  diagram  -> diagram.mp4 (silent 8 s loop) as is
  carousel -> slides turned into a vertical video here (ffmpeg): each slide ~3.5 s on a 1080x1920 dark canvas

Env: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN (OAuth "Desktop app" client on a Google Cloud project with
     YouTube Data API v3 enabled, consent screen published "In production", scope youtube.upload + youtube.readonly,
     refresh token from the channel's Google account). Missing secrets: nothing is published.

An item is due when its slot (Asia/Kuala_Lumpur) has passed and is less than 8 hours old. Before uploading, the
channel's latest uploads are read: a video with the same title is skipped, so re-runs never double-post.
At most 2 uploads per run. Never fails the workflow.
"""
import argparse, datetime, glob, json, os, re, subprocess, sys, tempfile, urllib.error, urllib.parse, urllib.request

KL = datetime.timezone(datetime.timedelta(hours=8))
WINDOW = datetime.timedelta(hours=8)
MAX_PER_RUN = 2
API = "https://www.googleapis.com/youtube/v3"
IG_LINE = "Daily AI and cyber news on Instagram: https://www.instagram.com/thecyberintellect/"
SLIDE_SECONDS = 3.5


def http(method, url, token=None, params=None, body=None, headers=None, raw=False):
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    h = dict(headers or {})
    if token:
        h["Authorization"] = "Bearer " + token
    data = body
    if isinstance(body, (dict, list)):
        data = json.dumps(body).encode()
        h.setdefault("Content-Type", "application/json; charset=UTF-8")
    r = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=300) as resp:
            return resp if raw else json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {url.split('?')[0]} -> {e.code}: {e.read()[:400]!r}")


def access_token():
    cid, sec, ref = (os.environ.get(k, "").strip() for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))
    if not (cid and sec and ref):
        return None
    body = urllib.parse.urlencode({"client_id": cid, "client_secret": sec, "refresh_token": ref,
                                   "grant_type": "refresh_token"}).encode()
    return http("POST", "https://oauth2.googleapis.com/token", body=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"})["access_token"]


def norm(t):
    return re.sub(r"\W+", " ", (t or "")).strip().lower()[:90]


def title_for(it):
    hook = ((it.get("reel") or {}).get("hook") or (it.get("cover") or {}).get("hook")
            or (it.get("diagram") or {}).get("title") or it["id"])
    t = hook.strip()
    if len(t) > 90:
        t = t[:87].rstrip() + "..."
    return t + " #Shorts"


def description_for(it):
    cap = it.get("ig_caption", "")
    return (cap + "\n\n" + IG_LINE)[:4900]


def tags_for(it):
    tags = re.findall(r"#(\w+)", it.get("ig_caption", ""))
    seen, out = set(), []
    for t in tags + ["CyberSecurity", "AI", "InfoSec", "Shorts"]:
        if t.lower() not in seen:
            seen.add(t.lower()); out.append(t)
    return out[:15]


def download(url, path):
    with urllib.request.urlopen(url, timeout=300) as r, open(path, "wb") as f:
        f.write(r.read())


def local_or_download(media_dir, run, iid, url, work):
    name = url.rsplit("/", 1)[-1]
    p = os.path.join(media_dir, run, iid, name)
    if os.path.exists(p):
        return p
    dst = os.path.join(work, f"{iid}-{name}")
    download(url, dst)
    return dst


def carousel_video(slides, out):
    """Slides (1080x1350) -> 1080x1920 H.264 video, SLIDE_SECONDS each, silent audio track for compatibility."""
    args = ["ffmpeg", "-loglevel", "error", "-y"]
    for s in slides:
        args += ["-loop", "1", "-t", str(SLIDE_SECONDS), "-i", s]
    n = len(slides)
    args += ["-f", "lavfi", "-t", str(SLIDE_SECONDS * n), "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    parts = [f"[{i}:v]scale=1080:1350,pad=1080:1920:0:285:color=0x0b1020,setsar=1,fps=30[v{i}]" for i in range(n)]
    filt = ";".join(parts) + ";" + "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]"
    args += ["-filter_complex", filt, "-map", "[v]", "-map", f"{n}:a", "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-shortest", "-movflags", "+faststart", out]
    subprocess.run(args, check=True)
    return out


def build_video(media_dir, run, it, m, work):
    urls = m["media"]
    if it["kind"] in ("reel", "diagram"):
        vid = next((u for u in urls if u.endswith(".mp4")), None)
        if not vid:
            raise RuntimeError("no mp4 in manifest")
        return local_or_download(media_dir, run, it["id"], vid, work)
    slides = [local_or_download(media_dir, run, it["id"], u, work) for u in urls if u.lower().endswith((".jpg", ".png"))]
    if not slides:
        raise RuntimeError("no slides in manifest")
    return carousel_video(slides[:12], os.path.join(work, f"{it['id']}-short.mp4"))


def upload(token, path, it):
    meta = {
        "snippet": {"title": title_for(it), "description": description_for(it), "tags": tags_for(it),
                    "categoryId": "28", "defaultLanguage": "en", "defaultAudioLanguage": "en"},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": it["kind"] == "reel"},   # reels use a synthetic (TTS) voice
    }
    size = os.path.getsize(path)
    init = http("POST", "https://www.googleapis.com/upload/youtube/v3/videos", token,
                params={"uploadType": "resumable", "part": "snippet,status"}, body=meta,
                headers={"X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)}, raw=True)
    loc = init.headers["Location"]
    with open(path, "rb") as f:
        res = http("PUT", loc, token, body=f.read(), headers={"Content-Type": "video/mp4"})
    return res.get("id")


def recent_titles(token):
    ch = http("GET", f"{API}/channels", token, {"part": "contentDetails,snippet", "mine": "true"})["items"][0]
    up = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    items = http("GET", f"{API}/playlistItems", token, {"part": "snippet", "playlistId": up, "maxResults": 50}).get("items", [])
    return ch["snippet"]["title"], {norm(i["snippet"]["title"]) for i in items}


def due_items(media_dir, content_dir, now):
    out = []
    for man_path in sorted(glob.glob(os.path.join(media_dir, "*", "manifest.json"))):
        run = os.path.basename(os.path.dirname(man_path))
        cpath = os.path.join(content_dir, run + ".json")
        if not os.path.exists(cpath):
            continue
        man = json.load(open(man_path))
        for it in json.load(open(cpath))["items"]:
            m = man.get("items", {}).get(it["id"])
            if not m or it.get("kind") not in ("reel", "diagram", "carousel") or it.get("youtube") is False:
                continue
            slot = datetime.datetime.fromisoformat(it["slot"]).replace(tzinfo=KL)
            if slot <= now <= slot + WINDOW:
                out.append((slot, run, it, m))
    return sorted(out, key=lambda x: x[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--media", default="media")
    ap.add_argument("--content", default="claude-news/content")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--build-only", help="build the videos into this folder and stop (local test)")
    ap.add_argument("--now", help="override current time (ISO, for tests)")
    a = ap.parse_args()
    now = datetime.datetime.fromisoformat(a.now) if a.now else datetime.datetime.now(KL)
    due = due_items(a.media, a.content, now)
    print(f"{len(due)} item(s) due at {now.isoformat(timespec='minutes')}")
    if not due:
        return
    if a.build_only:
        os.makedirs(a.build_only, exist_ok=True)
        for slot, run, it, m in due:
            print(f"built {it['id']} -> {build_video(a.media, run, it, m, a.build_only)} | {title_for(it)}")
        return
    if a.dry_run:
        for slot, run, it, m in due:
            print(f"DRY {it['id']} {it['kind']} {slot:%H:%M} | {title_for(it)}")
        return
    token = access_token()
    if not token:
        print("YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN not set: nothing published")
        return
    chan, seen = recent_titles(token)
    done = 0
    with tempfile.TemporaryDirectory() as work:
        for slot, run, it, m in due:
            t = title_for(it)
            if norm(t) in seen:
                print(f"skip {it['id']}: already on {chan}")
                continue
            if done >= MAX_PER_RUN:
                print(f"later {it['id']}: {MAX_PER_RUN} per run")
                continue
            try:
                vid = upload(token, build_video(a.media, run, it, m, work), it)
                seen.add(norm(t)); done += 1
                print(f"published {it['id']} ({it['kind']}) as https://youtube.com/shorts/{vid}")
            except Exception as e:
                print(f"FAIL {it['id']}: {e}")
                if "quotaExceeded" in str(e) or "uploadLimitExceeded" in str(e):
                    print("YouTube quota / upload limit reached: stopping this run")
                    break


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"yt_publish error: {e}")
    sys.exit(0)

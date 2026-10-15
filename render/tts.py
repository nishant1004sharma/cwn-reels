#!/usr/bin/env python3
"""Generate the narration for one reel with Nishant's ElevenLabs voice clone.

Usage: python3 render/tts.py --id D1-R01 --outdir media

Needs:
  ELEVENLABS_VOICE_ID   env var (the voice ID of "Nishant CISSP tutor")
  ELEVENLABS_API_KEY    env var, OR an environment network secret for api.elevenlabs.io
                        (header xi-api-key) that the agent proxy attaches for us
  ELEVENLABS_MODEL      optional, default eleven_v3

Writes <id>.mp3 and, when the API returns timestamps, <id>.align.json.
Uses the voice's saved settings (no voice_settings override).
"""
import argparse, base64, json, os, sys, urllib.error, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_reels

API = "https://api.elevenlabs.io/v1/text-to-speech/{voice}{suffix}?output_format=mp3_44100_128"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def call(url, body, accept):
    headers = {"Content-Type": "application/json", "Accept": accept}
    key = os.environ.get("ELEVENLABS_API_KEY")
    if key:
        headers["xi-api-key"] = key
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--bank", default=os.path.join(ROOT, "bank", "reels.json"))
    ap.add_argument("--outdir", default=os.path.join(ROOT, "media"))
    a = ap.parse_args()
    voice = os.environ.get("ELEVENLABS_VOICE_ID")
    if not voice:
        sys.exit("ELEVENLABS_VOICE_ID is not set")
    reels = load_reels(a.bank)
    reel = reels[a.id]
    text = " ".join(s["say"] for s in reel["segments"])
    body = {"text": text, "model_id": os.environ.get("ELEVENLABS_MODEL", "eleven_v3")}
    os.makedirs(a.outdir, exist_ok=True)
    mp3 = os.path.join(a.outdir, f"{a.id}.mp3")
    try:
        data = json.loads(call(API.format(voice=voice, suffix="/with-timestamps"), body, "application/json"))
        open(mp3, "wb").write(base64.b64decode(data["audio_base64"]))
        align = data.get("alignment") or data.get("normalized_alignment")
        if align:
            json.dump(align, open(os.path.join(a.outdir, f"{a.id}.align.json"), "w"))
        print(f"voice ok with timestamps: {mp3}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        if e.code in (401, 403):
            sys.exit(f"ElevenLabs auth failed ({e.code}): {detail}")
        print(f"timestamps endpoint failed ({e.code}: {detail}); retrying plain endpoint")
        open(mp3, "wb").write(call(API.format(voice=voice, suffix=""), body, "audio/mpeg"))
        print(f"voice ok (no timestamps): {mp3}")

if __name__ == "__main__":
    main()

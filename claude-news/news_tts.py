#!/usr/bin/env python3
"""Narration for a news reel.

Order:
  1. Nishant's ElevenLabs voice clone, when ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID are set
     (GitHub repo secrets in Actions). Model from ELEVENLABS_MODEL, default eleven_multilingual_v2.
  2. Otherwise a Microsoft neural voice via edge-tts (EDGE_VOICE, default en-US-AndrewMultilingualNeural).

Returns (mp3_path, align_path_or_None, voice_label). Raises RuntimeError if both fail.
"""
import base64, json, os, subprocess, urllib.error, urllib.request

EL_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice}{suffix}?output_format=mp3_44100_128"


def _el_call(url, body, accept, key):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Accept": accept, "xi-api-key": key})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def elevenlabs(text, mp3, align_path):
    key, voice = os.environ.get("ELEVENLABS_API_KEY"), os.environ.get("ELEVENLABS_VOICE_ID")
    if not key or not voice:
        raise RuntimeError("ElevenLabs secrets not set")
    body = {"text": text, "model_id": os.environ.get("ELEVENLABS_MODEL") or "eleven_multilingual_v2"}
    try:
        data = json.loads(_el_call(EL_URL.format(voice=voice, suffix="/with-timestamps"), body, "application/json", key))
        open(mp3, "wb").write(base64.b64decode(data["audio_base64"]))
        al = data.get("alignment") or data.get("normalized_alignment")
        if al:
            json.dump(al, open(align_path, "w"))
            return mp3, align_path
        return mp3, None
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise RuntimeError(f"ElevenLabs auth/quota {e.code}: {e.read()[:200]!r}")
        open(mp3, "wb").write(_el_call(EL_URL.format(voice=voice, suffix=""), body, "audio/mpeg", key))
        return mp3, None


def edge(text, mp3):
    voice = os.environ.get("EDGE_VOICE") or "en-US-AndrewMultilingualNeural"
    rate = os.environ.get("EDGE_RATE") or "+12%"
    subprocess.run(["edge-tts", "--voice", voice, f"--rate={rate}", "--text", text, "--write-media", mp3],
                   check=True, capture_output=True, timeout=180)
    return voice


def speak(text, mp3, align_path):
    errors = []
    try:
        m, a = elevenlabs(text, mp3, align_path)
        return m, a, "elevenlabs-clone"
    except Exception as e:
        errors.append(f"elevenlabs: {e}")
    try:
        v = edge(text, mp3)
        return mp3, None, f"edge-tts:{v}"
    except Exception as e:
        errors.append(f"edge-tts: {e}")
    raise RuntimeError("; ".join(errors))

#!/usr/bin/env python3
"""Render an animated explainer (kind "diagram") from an HTML/SVG file into a looping silent MP4.

Usage: python3 claude-news/diagram_render.py claude-news/diagrams/<id>.html out/diagram.mp4 [--seconds 8]

The page is 1080x1350. Its CSS animations (dashed arrows, pulses) are paused and stepped frame by frame,
so the output is deterministic and loops seamlessly when every animation period divides the length
(the template's periods are 0.5 s, 1 s and 2 s). A silent audio track is added because Instagram's
API is more reliable with video that has an audio stream.
"""
import argparse, os, shutil, subprocess, tempfile

W, H, FPS = 1080, 1350, 30


def render(html, out, seconds=8):
    from playwright.sync_api import sync_playwright
    tmp = tempfile.mkdtemp()
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": W, "height": H})
            pg.goto("file://" + os.path.abspath(html))
            pg.wait_for_timeout(600)
            n = pg.evaluate("document.getAnimations().length")
            if n == 0:
                raise RuntimeError("diagram has no CSS animations (use class flow / flowG / flowR)")
            pg.evaluate("document.getAnimations().forEach(a => a.pause())")
            for i in range(FPS * seconds):
                t = i * 1000 / FPS
                pg.evaluate(f"document.getAnimations().forEach(a => a.currentTime = {t})")
                pg.screenshot(path=os.path.join(tmp, f"{i:04d}.png"))
            b.close()
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(tmp, "%04d.png"),
                        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                        "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-r", str(FPS),
                        "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", out], check=True)
        cover = os.path.splitext(out)[0] + "-cover.jpg"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", os.path.join(tmp, "0000.png"), "-q:v", "2", cover], check=True)
        return cover
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("out")
    ap.add_argument("--seconds", type=int, default=8)
    a = ap.parse_args()
    print(render(a.html, a.out, a.seconds))

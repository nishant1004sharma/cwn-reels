# Cybersecurity with Nishant: reels

Automated short-form reels (YouTube Shorts + Instagram Reels) for CISSP, CEH and AI security prep.

- `bank/reels.json`: the reel scripts (spoken text, captions, cards, post copy)
- `render/tts.py`: narration with Nishant's ElevenLabs voice clone
- `render/render.py`: 1080x1920 video with synced captions, cards and quiz reveals
- `render/state.py`: picks the next reel and records what was posted
- `state/published.json`: posting history
- `media/`: rendered videos (public URLs used for posting)
- `RUNBOOK.md`: the steps the weekday scheduled task follows

Fonts: Inter (SIL Open Font License).

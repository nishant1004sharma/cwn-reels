# Claude news (The Cyber Intellect)

Twice-daily AI and cyber news posts for @thecyberintellect (Instagram and YouTube via Metricool, X via Typefully). Separate from the GPT pipeline in `the-cyber-intellect/` and the CISSP reels in `render/`.

- `RUNBOOK.md`: what each scheduled run does (research, write, render, schedule, record)
- `content/YYYY-MM-DD-am|pm.json`: the 5 stories of one run (copy, sources, slides, reel script, slot)
- `validate.py`: checks a run file before it is pushed
- `cards.py`: 1080x1350 carousel slides and single cards
- `news_tts.py`: reel narration: Nishant's ElevenLabs clone if the repo secrets are set, else edge-tts
- `render_all.py`: renders a run file (reels reuse `render/render.py`) and writes `manifest.json`
- `publish_media.sh`: pushes media to the `claude-news-media` branch (last 3 days only, force-pushed; Metricool keeps its own copy once a post is scheduled)
- `payloads.py`: builds the Metricool createScheduledPost payloads (Instagram, YouTube Shorts, LinkedIn)
- `typefully_post.py`: schedules each story on X (and Threads/Bluesky if connected) via Typefully, from the workflow; needs secret `TYPEFULLY_API_KEY`
- `state/posted.json`: stories already posted (dedupe)
- `.github/workflows/claude-news-media.yml`: renders on push of a run file

## Use his cloned voice on the reels
Add two repository secrets (Settings → Secrets and variables → Actions): `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID` (the "Nishant CISSP tutor" voice). Optional repository variable `ELEVENLABS_MODEL` (default `eleven_multilingual_v2`). Without them the reels use the `edge-tts` voice `en-US-AndrewMultilingualNeural` (variable `EDGE_VOICE` to change).

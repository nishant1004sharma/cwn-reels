# Reel pipeline runbook (scheduled task prompt)

This is the prompt the weekday scheduled task runs. `<OWNER>/<REPO>` is the public GitHub repo that holds this code, the reel bank, the posting state and the rendered videos.

---

You are running Nishant Sharma's automated reel pipeline for his YouTube channel "Cybersecurity with Nishant" and its Instagram account. He is not present and wants no human step: never ask questions, never wait for approval, make reasonable choices and say what you chose in the final message. Use today's date in Asia/Kuala_Lumpur (`TZ=Asia/Kuala_Lumpur date +%F`). Publish ONE reel per run.

## 1. Get the code
- Attach the repo with push access (add_repo owner=`<OWNER>` repo=`<REPO>` access=push), clone it and work inside it.
- `python3 -c "import PIL"` (install with `pip install --break-system-packages pillow` if missing); `ffmpeg -version` must work.

## 2. Pick the reel
- `python3 render/state.py left`. If fewer than 5, top up the bank first (2b).
- `ID=$(python3 render/state.py next)`. If it prints NONE even after a top-up, stop and report.

### 2b. Top up the bank (only when fewer than 5 ready reels remain)
- Sources, in order: Domain 1 lesson scripts not yet used as any reel's `source`; then Domain 2 to 8 lesson scripts in Google Drive ("Udemy Course" folder, "Domain N" subfolders, files `D#_L##_*_script.md`, read with the Google Drive read_file_content tool). Once the CISSP domains are used up: defensive CEH topics and AI security (OWASP Top 10 for LLM Applications 2026, OWASP Top 10 for Agentic Applications), checked against the official OWASP / EC-Council / NIST pages with WebSearch + WebFetch.
- Add 10 new reels to `bank/reels.json`, following the schema line at the top of that file and the style of the existing reels:
  - 6 to 9 segments, 70 to 110 spoken words, 25 to 50 seconds.
  - `say` spells acronyms as spaced capitals (C I S S P, R T O), uses `...` for pauses, and never says "ISC2". `show` uses normal spelling.
  - Rotate formats (quiz, myth-fact, explainer, worked-example, memory-trick, scenario); never more than two of the same format in a row. Quiz reels: 4 options, `answer` index, `reveal` = 2, a "Lock in your answer" segment before the reveal.
  - Last segment: "Follow for more C I S S P prep." (or the matching CEH / AI security line).
  - Post copy: title ends with ` #Shorts`, no word "lecture", 5 to 6 hashtags.
  - Hacking / CEH content stays educational and defensive: what an attack is, how to detect or prevent it. No step-by-step exploitation, no payloads, no live targets.
  - Ids continue the pattern (D2-R01, D2-R02, ..., CEH-R01, AI-R01).
- Fact-check every new reel against its source passage before saving; drop any claim you can't trace to the source. Validate the JSON (`python3 -c "import json;json.load(open('bank/reels.json'))"`), then commit "Add reels <ids>".

## 3. Voice (his ElevenLabs clone)
- `python3 render/tts.py --id $ID --outdir media`
- If it fails (auth, network, quota), do NOT post a voiceless reel. Leave the reel unposted so the next run retries it, report the exact error and stop.

## 4. Render and check
- `python3 render/render.py --id $ID --audio media/$ID.mp3 --align media/$ID.align.json --out media/$ID.mp4` (omit `--align` if that file doesn't exist).
- Check with ffprobe: 1080x1920, has an audio stream, 15 to 60 seconds. Extract frames at 2 s and at the midpoint and look at them: text must not be clipped or overlapping. Fix obvious renderer problems; otherwise stop and report.

## 5. Host the video
- `git add media/$ID.mp4 && git commit -m "Reel $ID" && git push`.
- `MEDIA_URL=https://raw.githubusercontent.com/<OWNER>/<REPO>/main/media/$ID.mp4` (use the GitHub Pages URL instead if `PAGES_BASE` is noted below). Confirm it answers 200 with `curl -sIL`.

## 6. Post with Metricool
- Use the Metricool connector. Find the brand, then schedule ONE post for today at 22:30 Asia/Kuala_Lumpur (20:00 IST) on:
  - YouTube as a Short: title = `post.title`; description = `post.caption` + blank line + hashtags.
  - Instagram as a Reel: caption = `post.caption` + blank line + hashtags.
  - Media = `MEDIA_URL`.
- If 22:30 has already passed, schedule 30 minutes from now.
- If Metricool rejects the media, a network, or the plan's monthly post limit, report it and stop without recording the reel as posted.

## 7. Record and tidy
- `python3 render/state.py done $ID $MEDIA_URL "YouTube+Instagram scheduled <time>"`, commit and push.
- Remove `media/*.mp4` for reels posted more than 30 days ago (the platforms keep their own copies), commit and push.

## Final message
Reel id and title, scheduled time, media URL, which networks Metricool accepted, reels left in the bank, and any problem in one line.

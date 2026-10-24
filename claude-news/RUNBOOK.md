# Claude news runbook (scheduled task prompt)

Two scheduled runs a day post AI and cyber news to **@thecyberintellect** on Instagram and, once it is connected in Metricool, to **X**. Each run publishes **5 stories**: each story becomes one Instagram post (reel, carousel or card) and one X post at the same time slot. This is separate from the GPT pipeline in `the-cyber-intellect/` and from the CISSP reel pipeline in `render/`: never edit, move or delete their files.

Nishant is not present and wants no human step: never ask questions or wait for approval. Make reasonable choices and say what you chose in the final message.

## 0. Setup
- Attach the repo with push access (add_repo owner=`nishant1004sharma` repo=`cwn-reels` access=push), clone it (`git clone --depth 1`) and work inside it.
- `RUN` = `am` if Kuala Lumpur time (`TZ=Asia/Kuala_Lumpur date +%H`) is before 14:00, else `pm`. `DATE` = `TZ=Asia/Kuala_Lumpur date +%F`. Run file: `claude-news/content/$DATE-$RUN.json`. If it already exists and its items are recorded in `claude-news/state/posted.json`, stop and report "already done".
- Slots (Asia/Kuala_Lumpur): am = 07:30, 08:15, 10:00, 12:00, 14:30; pm = 16:00, 17:30, 20:00, 21:15, 22:30.

## 1. Look at Metricool first
- `getBrandSettings`: blogId and connected networks. Instagram is `instagramData`; X is `twitterData`. Post to X only if it is connected.
- `getScheduledPosts` from 3 days ago to tomorrow (timezone Asia/Kuala_Lumpur). Use it to:
  - avoid clashes: other posts (GPT's run at about 09:00, 13:00, 19:00; the CISSP reel at 11:00) must be at least 20 minutes from any of our slots. Move a clashing slot later in 15-minute steps.
  - avoid repeats: skip any story already covered by any post in that window, whoever made it.
- Any slot less than 25 minutes from now moves to now + 30 minutes (rounded up to 5), keeping the 20-minute gaps.

## 2. Pick 5 stories
- Window: news from the last 36 hours (am run: overnight US/EU news first). Use WebSearch (`extended` mode) with several queries, e.g. "zero-day exploited", "CISA KEV added", "data breach confirmed", "ransomware attack", "AI agent vulnerability", "prompt injection", "AI security", "agentic AI", "AI model release", "LLM jailbreak", "supply chain attack", "Patch Tuesday" (plus today's date).
- Mix in every run: at least 1 AI / agentic-AI story (security of AI, AI used in attacks, or a major AI release with a security angle), at least 1 exploited vulnerability or zero-day, at least 1 attack or breach. Fill the rest with the strongest stories.
- Skip anything in `claude-news/state/posted.json` (by `story_key`: the CVE id if there is one, otherwise a short slug) or already covered per step 1.
- **Verify every story with WebFetch** on a primary source (vendor advisory, CISA, government regulator, company notice, Microsoft/Google/Mandiant research) or established security press (BleepingComputer, The Hacker News, SecurityWeek, The Record, Dark Reading, CSO, Infosecurity, The Register, Reuters, AP). Every number, CVE id, CVSS, version, date and attribution must come from a page you fetched this run. Drop anything you can't confirm.
- Never name a victim from a ransomware leak-site claim alone. Attribution is "X says / attributes to", never stated as fact. No exploit steps, payloads or live targets: what happened, why it matters, what to do.

## 3. Write the run file
Follow the shape of an existing file in `claude-news/content/` exactly. Items in this order: 1 = reel, 2 = carousel, 3 = card, 4 = reel, 5 = carousel. Ids `$DATE-$RUN-01` to `-05`. `slot` = `YYYY-MM-DDTHH:MM:00` (KL time). `category` is one of: ZERO-DAY, PATCH NOW, VULNERABILITY, BREACH, RANSOMWARE, ATTACK, THREAT INTEL, SUPPLY CHAIN, AI SECURITY, AGENTIC AI, AI THREAT, AI NEWS, CLOUD, IDENTITY, POLICY, DEFENCE.

The voice that makes these engaging (this is the point of the whole pipeline):
- **Hook first**: lead with the most surprising concrete fact (a number, a time, an absurd detail), not the headline. "The alerts fired. A tool closed them as false positives." beats "BeyondTrust patches zero-day".
- **Practitioner take**: one line on why it matters to defenders, then concrete actions a security team can do this week.
- **End with one real question** that people can answer from their own experience.
- Short lines, plain words, no hype words ("game-changer", "chilling", "alarming"), no emoji walls (max 3 per caption).
- `x_text`: 270 characters max, max 2 hashtags (0 is fine), no links, stands alone.
- `ig_caption`: hook line, 3 to 5 "→" fact lines, the action(s), the question with 👇, a `Source:` line naming the outlet and date, then 4 to 7 hashtags.
- Carousel: `cover.hook` (max 90 chars) + `cover.sub`, 4 or 5 body slides mixing `point` (title + body max 260 chars), one `stat` ("BIG" + label) and one `actions` slide (3 or 4 items), plus `question`. Card: hook, sub, 3 bullets (max 95 chars each).
- Reel: same schema as `bank/reels.json` segments (`say`, `show`, `card`, `card_style` default|stat|alert|fact|answer), 6 or 7 segments, 70 to 115 spoken words, hook in `reel.hook`, `reel.series` like "AI Threat", "Breach Alert", "Zero-Day Alert", "Patch Now". `say` spells acronyms as spaced capitals (A I, M F A, I P) and never reads CVE ids or version numbers aloud (keep those in `show`/`card`). Last segment: "Follow The Cyber Intellect for daily <attacks|breaches|AI security>, explained."
- Run `python3 claude-news/validate.py <run file>` and fix until it prints ok.

## 4. Render (GitHub Actions)
- Commit only the run file (`git add claude-news/content/$DATE-$RUN.json`), message "News run $DATE $RUN", `git pull --rebase origin main`, `git push`. The push triggers the workflow "Claude news media", which renders the cards and voiced reels (Nishant's ElevenLabs voice when the repo secrets exist, otherwise a neural voice) and publishes them to the `claude-news-media` branch.
- Wait for it: `gh run list -R nishant1004sharma/cwn-reels --workflow claude-news-media.yml -L 3` until the run for your commit completes (check every 30 s, up to 20 minutes). If it fails, read `gh run view <id> --log-failed`, fix the content if that's the cause, push again once, and wait again.
- Fetch the manifest: `curl -sSL https://raw.githubusercontent.com/nishant1004sharma/cwn-reels/claude-news-media/$DATE-$RUN/manifest.json -o /tmp/manifest.json`. Check every media URL answers 200 (`curl -sIL`).
- Look at the media: download each item's first image (or a frame at 3 s of each reel with ffmpeg) and view it. Text must not be clipped or overlapping. If one item is broken, drop just that item.

## 5. Schedule in Metricool
- `python3 claude-news/payloads.py claude-news/content/$DATE-$RUN.json /tmp/manifest.json --networks instagram[,twitter]` prints one entry per post. For each entry call `createScheduledPost` with `blogId`, `date` and `info` exactly as printed.
- If X rejects a text as too long, shorten that one `x_text` and retry once. If Metricool rejects media, a network or the plan limit, report it and carry on with the rest.
- Confirm with `getScheduledPosts` for today: each of our posts is there, pending, at its slot.

## 6. Record
- Append one entry per scheduled story to `claude-news/state/posted.json` `posted` list: `{"story_key", "id", "date", "slot", "kind", "networks": [...], "voice": manifest voice or null, "title": cover hook or reel hook}`. Keep only the last 30 days of entries. Commit "Record news run $DATE $RUN", pull --rebase, push.

## Final message
Short bullets: the 5 stories (time, format, hook), networks posted, voice used for reels, anything skipped or failed in one line each.

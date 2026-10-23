# The Cyber Intellect — public media assets

This directory hosts **public, non-confidential** Instagram content for @thecyberintellect. It is separate from the existing cwn-reels content.

- `content/YYYY-MM-DD.json`: fact-checked editorial copy and sources, generated only after verifying primary sources.
- `media/YYYY-MM-DD/*.png`: public images generated from the corresponding content file.
- `render.py`: renderer for portrait 1080 × 1350 PNG social graphics.
- `.github/workflows/the-cyber-intellect-media.yml`: on-push media renderer (stored at repository root).

Media URLs follow `https://raw.githubusercontent.com/nishant1004sharma/cwn-reels/main/the-cyber-intellect/media/YYYY-MM-DD/01.png`.

**Publishing status:** Media hosting is not Instagram publishing. Metricool must separately accept the generated public URLs and confirm each scheduled/published Instagram post. Never assume that a GitHub commit equals an Instagram post.

**Security:** No secrets, tokens, private data, employer information, or unverified vulnerability claims belong in this public directory.

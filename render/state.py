#!/usr/bin/env python3
"""Pick the next reel and record what was posted.

  python3 render/state.py next             -> prints the next ready reel id (or NONE)
  python3 render/state.py left             -> prints how many ready reels are unposted
  python3 render/state.py done ID URL NOTE -> records ID as posted today (KL time)
  python3 render/state.py skip ID REASON   -> marks ID as skipped so it isn't retried
"""
import json, os, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK = os.path.join(ROOT, "bank", "reels.json")
STATE = os.path.join(ROOT, "state", "published.json")

def load():
    bank = json.load(open(BANK))["reels"]
    state = json.load(open(STATE)) if os.path.exists(STATE) else {"posted": []}
    return bank, state

def today():
    return (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime("%Y-%m-%d")

def main():
    bank, state = load()
    used = {p["id"] for p in state["posted"]}
    ready = [r["id"] for r in bank if r.get("status") == "ready" and r["id"] not in used]
    cmd = sys.argv[1] if len(sys.argv) > 1 else "next"
    if cmd == "next":
        print(ready[0] if ready else "NONE")
    elif cmd == "left":
        print(len(ready))
    elif cmd in ("done", "skip"):
        rid = sys.argv[2]
        entry = {"id": rid, "date": today(), "status": "posted" if cmd == "done" else "skipped"}
        if cmd == "done":
            entry["media_url"] = sys.argv[3] if len(sys.argv) > 3 else ""
            entry["note"] = " ".join(sys.argv[4:])
        else:
            entry["reason"] = " ".join(sys.argv[3:])
        state["posted"].append(entry)
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        json.dump(state, open(STATE, "w"), indent=2)
        print(f"recorded {rid} as {entry['status']}")
    else:
        sys.exit(__doc__)

if __name__ == "__main__":
    main()

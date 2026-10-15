"""Shared loading for the reel scripts: bank + config, with the course CTA applied."""
import copy, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK = os.path.join(ROOT, "bank", "reels.json")
CONFIG = os.path.join(ROOT, "config.json")

def load_config():
    try:
        return json.load(open(CONFIG))
    except (OSError, ValueError):
        return {}

def apply_cta(reel, cfg):
    """Replace a closing 'Follow for more ...' segment with the course CTA (or append one)."""
    cta = cfg.get("cta")
    if not cta or not cfg.get("course_url"):
        return reel
    reel = copy.deepcopy(reel)
    segs = reel["segments"]
    seg = {k: cta[k] for k in ("say", "show", "card", "card_style") if k in cta}
    if segs and segs[-1]["say"].lower().startswith("follow for more"):
        segs[-1] = seg
    elif not segs or segs[-1].get("say") != seg["say"]:
        segs.append(seg)
    return reel

def load_reels(bank_path=BANK):
    cfg = load_config()
    return {r["id"]: apply_cta(r, cfg) for r in json.load(open(bank_path))["reels"]}

def post_text(reel, cfg=None):
    """Caption/description for Metricool: caption, course line, hashtags."""
    cfg = cfg if cfg is not None else load_config()
    parts = [reel["post"]["caption"]]
    if cfg.get("course_url") and cfg.get("description_line"):
        parts.append(cfg["description_line"].format(course_url=cfg["course_url"]))
    parts.append(" ".join(reel["post"]["hashtags"]))
    return "\n\n".join(parts)

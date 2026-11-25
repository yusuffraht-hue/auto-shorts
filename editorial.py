"""Editorial topic selection. No network calls or paid services.
A source pack is a human-reviewed paraphrase, not an automatically verified fact.
"""
import json
from pathlib import Path
from urllib.parse import urlparse

def select_topic(hist, avoid=(), requested="auto", path=None):
    path = Path(path or Path(__file__).with_name("editorial_topics.json"))
    entries = json.loads(path.read_text())
    used = {e.get("topic_id") for e in hist.get("episodes", [])[-30:]}
    recent = [e.get("work") for e in hist.get("episodes", [])[-10:]]
    eligible = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        if not all(isinstance(e.get(k), str) and e[k].strip()
                   for k in ("id", "work", "topic", "facts", "source")):
            continue
        if e.get("reviewed") is not True or e["id"] in used or e["work"] in avoid:
            continue
        if urlparse(e["source"]).scheme != "https" or not urlparse(e["source"]).hostname:
            continue
        if requested != "auto" and e["work"] != requested:
            continue
        if e.get("visual_complexity") not in ("low", "medium"):
            continue
        eligible.append(e)
    if not eligible:
        raise RuntimeError("No eligible reviewed editorial topic; skip rather than invent canon")
    return min(eligible, key=lambda e: (recent.count(e["work"]), e["id"]))

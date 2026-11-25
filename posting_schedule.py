"""Resolve local posting slots without triggering uploads."""
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

def due_slot(now, config=None):
    if now.tzinfo is None:
        raise ValueError("Timezone-aware datetime required")
    if config is None:
        config = json.loads(Path(__file__).with_name("posting_schedule.json").read_text())
    local = now.astimezone(ZoneInfo(config["timezone"]))
    for slot in config["slots"]:
        if local.strftime("%H:%M") == slot["time"]:
            return {"format": slot["format"], "key": local.date().isoformat() + ":" + slot["format"]}
    return None

"""Resolve local posting slots without triggering uploads."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

def due_slot(now, config=None):
    if now.tzinfo is None:
        raise ValueError("Timezone-aware datetime required")
    if config is None:
        config = json.loads(Path(__file__).with_name("posting_schedule.json").read_text())
    zone = ZoneInfo(config["timezone"])
    if zone.key == "America/Edmonton" and now >= datetime(2026, 11, 1, 8, tzinfo=timezone.utc):
        # Alberta stayed on UTC−6 when the final autumn clock change was cancelled.
        zone = timezone(timedelta(hours=-6), "ABT")
    local = now.astimezone(zone)
    for slot in config["slots"]:
        if local.strftime("%H:%M") == slot["time"]:
            return {"format": slot["format"], "key": local.date().isoformat() + ":" + slot["format"]}
    return None

"""Resolve local posting slots without triggering uploads."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BACKUP_MINUTE = 19

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


def scheduled_slot(cron, started_at):
    """Recover the intended Calgary date from the event cron and run creation time."""
    minute, hour, *rest = cron.split()
    if rest != ["*", "*", "*"] or int(minute) not in (0, BACKUP_MINUTE):
        raise ValueError("Expected a primary or backup daily cron expression")
    trigger = started_at.astimezone(timezone.utc).replace(
        hour=int(hour), minute=int(minute), second=0, microsecond=0)
    if trigger > started_at:
        trigger -= timedelta(days=1)
    slot_time = trigger.replace(minute=0)
    if started_at - slot_time >= timedelta(hours=2):
        raise ValueError("Scheduled run was too late for its posting slot")
    slot = due_slot(slot_time)
    if not slot:
        raise ValueError("Cron does not match a configured posting slot")
    return slot


def recovery_slot(key, started_at):
    """Allow recovery of today's original slot between 30 and 120 minutes late."""
    if started_at.tzinfo is None:
        raise ValueError("Timezone-aware datetime required")
    config = json.loads(Path(__file__).with_name("posting_schedule.json").read_text())
    local = started_at.astimezone(timezone(timedelta(hours=-6)))
    day, separator, kind = key.partition(":")
    if not separator or day != local.date().isoformat():
        raise ValueError("Recovery must use today's Calgary slot")
    for slot in config["slots"]:
        if slot["format"] == kind:
            hour, minute = map(int, slot["time"].split(":"))
            planned = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if timedelta(minutes=30) <= local - planned < timedelta(hours=2):
                return {"format": kind, "key": key}
            raise ValueError("Outside the recovery window for this posting slot")
    raise ValueError("Unknown recovery slot")

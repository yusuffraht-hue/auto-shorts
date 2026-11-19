"""Bounded, offline shot-plan validation for original town episodes."""
import json
from pathlib import Path

LOCATIONS = frozenset(("school", "square", "park"))
CHARACTERS = frozenset(("mira", "kai", "noor"))
ACTIONS = frozenset(("idle", "walk", "wave", "point", "surprised"))
CAMERAS = frozenset(("wide", "medium", "close"))
MAX_SHOTS = 12
MAX_TOTAL_FRAMES = 1800


def validate_plan(plan):
    """Return normalized shots or raise ValueError for invalid input."""
    if not isinstance(plan, dict) or set(plan) != {"series", "shots"}:
        raise ValueError("plan must contain exactly series and shots")
    if plan["series"] != "town":
        raise ValueError("only In This Town is supported")
    shots = plan["shots"]
    if not isinstance(shots, list) or not 1 <= len(shots) <= MAX_SHOTS:
        raise ValueError("shots must be a nonempty bounded list")
    normalized = []
    total = 0
    for index, shot in enumerate(shots):
        if not isinstance(shot, dict) or set(shot) != {"location", "character", "action", "camera", "frames"}:
            raise ValueError(f"shot {index}: invalid fields")
        for field, allowed in (("location", LOCATIONS), ("character", CHARACTERS),
                               ("action", ACTIONS), ("camera", CAMERAS)):
            if not isinstance(shot[field], str) or shot[field] not in allowed:
                raise ValueError(f"shot {index}: invalid {field}")
        frames = shot["frames"]
        if type(frames) is not int or not 1 <= frames <= 240:
            raise ValueError(f"shot {index}: invalid frame count")
        total += frames
        if total > MAX_TOTAL_FRAMES:
            raise ValueError("total frame budget exceeded")
        normalized.append(dict(shot))
    return normalized


def read_plan(path):
    path = Path(path)
    if path.stat().st_size > 32768:
        raise ValueError("shot plan too large")
    return validate_plan(json.loads(path.read_text(encoding="utf-8")))

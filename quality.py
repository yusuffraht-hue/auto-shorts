"""Deterministic pre-render quality checks for generated Shorts.

These checks cannot prove factual accuracy or guarantee monetization. They catch
common structural defects before expensive image/audio rendering begins.
"""
import re


def words(text):
    return re.findall(r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?", str(text or ""))


def _normal(text):
    return " ".join(words(text)).lower()


def check(data, history=None):
    """Return a stable report; never changes the story or episode history."""
    history = history or {}
    issues = []
    scenes = data.get("scenes") if isinstance(data, dict) else None

    title = str(data.get("title", "")).strip() if isinstance(data, dict) else ""
    if not title:
        issues.append("Missing title.")
    elif len(title) > 90:
        issues.append("Title exceeds 90 characters.")

    story = str(data.get("full_story", "")).strip() if isinstance(data, dict) else ""
    story_count = len(words(story))
    if story_count < 140:
        issues.append(f"Full story is too short ({story_count} words; minimum 140).")
    elif story_count > 180:
        issues.append(f"Full story is too long ({story_count} words; maximum 180).")

    if not isinstance(scenes, list) or len(scenes) != 10:
        issues.append("Exactly 10 scenes are required.")
        scenes = scenes if isinstance(scenes, list) else []
    seen_lines = set()
    for index, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict):
            issues.append(f"Scene {index} is not an object.")
            continue
        line = str(scene.get("line", "")).strip()
        image_prompt = str(scene.get("image_prompt", "")).strip()
        count = len(words(line))
        if not line:
            issues.append(f"Scene {index} has no narration.")
        elif count < 5 or count > 7:
            issues.append(f"Scene {index} narration has {count} words; expected 5-7.")
        normalized = _normal(line)
        if normalized and normalized in seen_lines:
            issues.append(f"Scene {index} repeats earlier narration.")
        seen_lines.add(normalized)
        image_count = len(words(image_prompt))
        if image_count < 8 or image_count > 16:
            issues.append(f"Scene {index} image prompt has {image_count} words; expected 8-16.")
        if not image_prompt:
            issues.append(f"Scene {index} has no image prompt.")

    recent_titles = {
        _normal(item.get("title", ""))
        for item in history.get("episodes", [])[-8:]
        if isinstance(item, dict)
    }
    if _normal(title) and _normal(title) in recent_titles:
        issues.append("Title duplicates one of the last eight episode titles.")

    return {
        "passed": not issues,
        "score": max(0, 100 - 15 * len(issues)),
        "story_word_count": story_count,
        "scene_count": len(scenes),
        "issues": issues,
        "checks": [
            "title present",
            "full-story length",
            "10-scene structure",
            "5-7 narration words per scene",
            "8-16 image-prompt words per scene",
            "duplicate narration",
            "recent-title repetition",
        ],
        "limitations": [
            "Automated checks do not verify canon facts, copyright clearance, visual quality, or audience retention.",
            "A human should review the rendered video before public release.",
        ],
    }

"""Deterministic pre-render quality checks for generated Shorts.

These checks cannot prove factual accuracy or guarantee monetization. They catch
common structural defects before expensive image/audio rendering begins.
"""
import re
from difflib import SequenceMatcher


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

    recent_stories = history.get("recent_stories", [])
    max_story_similarity = 0.0
    if isinstance(recent_stories, list) and story_count:
        current_tokens = _normal(story).split()
        for previous in recent_stories[-8:]:
            if isinstance(previous, dict):
                previous = previous.get("story") or previous.get("summary", "")
            previous_tokens = _normal(previous).split()
            if not previous_tokens:
                continue
            similarity = SequenceMatcher(
                None, current_tokens, previous_tokens, autojunk=False
            ).ratio()
            max_story_similarity = max(max_story_similarity, similarity)
            if similarity >= 0.72:
                issues.append(
                    f"Full story is too similar to a recent episode ({similarity:.0%} token-sequence similarity)."
                )
                break

    return {
        "passed": not issues,
        "score": max(0, 100 - 15 * len(issues)),
        "story_word_count": story_count,
        "scene_count": len(scenes),
        "max_recent_story_similarity": round(max_story_similarity, 3),
        "issues": issues,
        "checks": [
            "title present",
            "full-story length",
            "10-scene structure",
            "5-7 narration words per scene",
            "8-16 image-prompt words per scene",
            "duplicate narration",
            "recent-title repetition",
            "recent-story similarity heuristic",
        ],
        "limitations": [
            "Story similarity is a heuristic; it does not prove originality or platform monetization eligibility.",
            "Automated checks do not verify canon facts, copyright clearance, visual quality, or audience retention.",
            "A human should review the rendered video before public release.",
        ],
    }

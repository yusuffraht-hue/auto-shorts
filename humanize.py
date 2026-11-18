"""Remove common AI-writing tells from narration and captions.

Rules come from the humanizer skill (based on Wikipedia's "Signs of AI writing"). The prompt block
asks the story writer to avoid the patterns; scrub() cleans what slips through (it is deterministic and
never invents text); lint() reports what it cannot safely rewrite.
"""
import re

STYLE_RULES = """Write like a person telling a friend a story, not like a chatbot:
- State things directly. Never use "not X but Y" or "it's not just X, it's Y" contrasts.
- No one-line closers that repeat the point ("That's the real win", "Let that sink in", "Read that again").
- No deep-sounding sayings ("at its core", "the real question is", "what really matters").
- No forced groups of three, no em-dashes, no rows of short fragments ("No fear. No doubt. No mercy.").
- Each scene may only rely on people, places and rules that an earlier scene already introduced."""

STOCK_SENTENCE = re.compile(
    r"(let that sink in|read that again|that'?s the real (win|story|lesson|point)|"
    r"i hope this helps|great question)", re.I)
LITTLE_DID = re.compile(r"\blittle did \w+ know\b(,|\s+that\b)?\s*", re.I)
DEEP_OPENER = re.compile(r"\b(at its core|fundamentally|in reality|the heart of the matter)\b,?\s*", re.I)
DASH = re.compile(r"\s*[\u2014\u2013]\s*|\s+-\s+|(?<=\w)--(?=\w)")
NOT_X_BUT_Y = re.compile(
    r"(\bnot (just|only|merely)\b[^.!?]*\bbut\b|\bit'?s not\b[^.!?]*[,;]\s*it'?s\b|"
    r"\bthis (does not|doesn'?t) mean\b[^.!?]*\.\s*it means\b)", re.I)


def _sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


def scrub(text):
    """Return text with safe fixes applied; falls back to the original if nothing would be left."""
    if not text:
        return text
    t = DASH.sub(", ", text)
    t = DEEP_OPENER.sub("", t)
    t = LITTLE_DID.sub("", t)
    kept = [s for s in _sentences(t) if not STOCK_SENTENCE.search(s)]
    t = " ".join(kept)
    t = re.sub(r"\s+([,.!?])", r"\1", t)
    t = re.sub(r",\s*,", ",", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), t)
    return t or text


def lint(text):
    """Names of AI tells in the text that need a rewrite rather than a safe fix."""
    found = []
    if NOT_X_BUT_Y.search(text):
        found.append("not-x-but-y")
    run = 0
    for s in _sentences(text):
        run = run + 1 if len(s.split()) <= 3 else 0
        if run >= 3:
            found.append("fragment-row")
            break
    return found


def polish(data):
    """Scrub the narration lines, full story and description of a generated story in place."""
    for scene in data.get("scenes", []):
        scene["line"] = scrub(scene.get("line", ""))
    for key in ("full_story", "description"):
        if data.get(key):
            data[key] = scrub(data[key])
    tells = sorted({t for s in data.get("scenes", []) for t in lint(s["line"])}
                   | set(lint(data.get("full_story", ""))))
    if tells:
        print("humanizer: remaining tells:", tells)
    return data

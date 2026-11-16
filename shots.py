"""Turn story scenes into Blender shot specs using simple keyword rules (no extra LLM calls)."""
import random

COLORS = {"red": (0.85, 0.12, 0.12), "blue": (0.15, 0.35, 0.85), "green": (0.15, 0.6, 0.25),
          "yellow": (0.95, 0.8, 0.15), "orange": (0.95, 0.5, 0.1), "purple": (0.55, 0.25, 0.75),
          "pink": (0.95, 0.5, 0.7), "black": (0.07, 0.07, 0.08), "white": (0.92, 0.92, 0.92),
          "gray": (0.5, 0.5, 0.52), "grey": (0.5, 0.5, 0.52), "brown": (0.4, 0.25, 0.12),
          "teal": (0.1, 0.6, 0.6), "blonde": (0.9, 0.75, 0.3), "golden": (0.9, 0.75, 0.3)}
BRIGHT = [COLORS[k] for k in ("red", "blue", "green", "yellow", "orange", "purple", "pink", "teal")]
SKINS = [(0.95, 0.8, 0.6), (0.85, 0.65, 0.45), (0.65, 0.45, 0.3), (0.45, 0.3, 0.2), (0.98, 0.85, 0.7)]
HAIRS = [COLORS[k] for k in ("black", "brown", "orange", "blonde", "red")]
CAMS = ["wide", "medium", "closeup", "low", "medium", "over", "closeup", "wide", "low", "closeup"]


def _has(t, words):
    return any(w in t for w in words)


def look(hero_text, seed):
    rnd = random.Random(seed)
    words = (hero_text or "").lower().replace(",", " ").replace(".", " ").split()
    shirt = pants = hair = None
    for i, w in enumerate(words):
        if w in COLORS and i + 1 < len(words):
            nxt = words[i + 1]
            if nxt.startswith("hair") and hair is None:
                hair = COLORS[w]
            elif nxt in ("pants", "jeans", "shorts", "trousers", "overalls", "skirt") and pants is None:
                pants = COLORS[w]
            elif shirt is None and nxt not in ("hair", "haired", "eyes"):
                shirt = COLORS[w]
    shirt = shirt or rnd.choice(BRIGHT)
    pants = pants or rnd.choice([(0.15, 0.2, 0.5), (0.2, 0.2, 0.25), (0.35, 0.3, 0.25)])
    return {"role": "hero", "shirt": shirt, "pants": pants, "skin": rnd.choice(SKINS),
            "hair": hair or rnd.choice(HAIRS)}


def plan(data, seed=1):
    rnd = random.Random(seed)
    hero = look(data.get("hero", ""), seed)
    shots = []
    inside_underground = False
    for i, sc in enumerate(data["scenes"]):
        line = sc.get("line", "").lower()
        prompt = sc.get("image_prompt", "").strip().lower()
        t = line + " " + prompt
        first = prompt.replace(",", " ").split()[:1]
        if _has(t, ("outside", "emerges", "emerge", "escapes the tunnel", "back above ground",
                    "returns to street", "the next morning", "back at school")):
            inside_underground = False
        if _has(t, ("cavern", "cave", "tunnel", "basement", "hollow", "chamber", "sewer",
                    "crypt", "subterranean", "underground")):
            setting = "underground"
            inside_underground = True
        elif _has(t, ("library", "archive", "bookshelf", "book stacks")):
            setting = "library"
            inside_underground = False
        elif _has(t, ("market", "marketplace", "bazaar", "market stalls", "town square", "plaza")):
            setting = "market"
            inside_underground = False
        elif inside_underground:
            setting = "underground"
        elif first and first[0] in ("street", "park", "classroom", "house", "market", "underground", "library"):
            setting = first[0]
        elif _has(t, ("classroom", "school", "teacher", "blackboard", "lesson", "student", "homework")):
            setting = "classroom"
        elif _has(t, ("park", "garden", "forest", "pond", "bench", "meadow", "playground", "field")):
            setting = "park"
        elif _has(t, ("house", "home", "bedroom", "kitchen", "living room", "attic", "indoors", "inside")):
            setting = "house"
        else:
            setting = "street"
        if _has(t, ("night", "midnight", "moon", "dark", "shadow")):
            tm = "night"
        elif _has(t, ("sunset", "dusk", "evening", "sunrise", "dawn", "golden")):
            tm = "dusk"
        else:
            tm = "day"
        if _has(t, ("run", "chase", "flee", "rush", "sprint", "race")):
            pose = "run"
        elif _has(t, ("point", "gesture", "accuse", "show")):
            pose = "point"
        elif _has(t, ("gasp", "shock", "surpris", "stunned", "startled", "amaz", "astonish")):
            pose = "surprised"
        else:
            pose = "idle"
        if _has(t, ("gasp", "shock", "surpris", "stunned", "startled", "scream", "afraid", "fear")):
            emo = "shock"
        elif _has(t, ("angry", "furious", "glare", "scowl", "rage", "villain")):
            emo = "angry"
        elif _has(t, ("smile", "happy", "laugh", "grin", "cheer", "joy", "friend")):
            emo = "smile"
        else:
            emo = "neutral"
        if _has(t, ("key",)):
            prop = "key"
        elif _has(t, ("orb", "crystal", "glowing sphere", "magic ball")):
            prop = "orb"
        elif _has(t, ("book", "diary", "journal", "manual")):
            prop = "book"
        elif _has(t, ("letter", "note", "message", "envelope", "invitation")):
            prop = "letter"
        elif _has(t, ("door", "gate", "portal", "hatch")):
            prop = "door"
        else:
            prop = "none"
        chars = [dict(hero)]
        if _has(t, ("friend", "everyone", "crowd", "people", "neighbor", "villager", "townsfolk", "kids", "classmate")):
            chars.append({"role": "other", "shirt": rnd.choice(BRIGHT), "pants": (0.2, 0.2, 0.28),
                          "skin": rnd.choice(SKINS), "hair": rnd.choice(HAIRS), "emotion": "smile"})
        if _has(t, ("villain", "stranger", "mayor", "teacher", "figure", "enemy", "rival", "thief")):
            chars.append({"role": "villain", "shirt": (0.1, 0.1, 0.13), "pants": (0.08, 0.08, 0.1),
                          "skin": rnd.choice(SKINS), "hair": COLORS["black"], "emotion": "angry"})
        shots.append({"id": i, "setting": setting, "time": tm, "camera": CAMS[i % len(CAMS)],
                      "pose": pose, "emotion": emo, "prop": prop, "chars": chars})
    return {"width": 720, "height": 1280, "samples": 32, "shots": shots}

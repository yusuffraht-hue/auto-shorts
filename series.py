"""Two story series: prompts, visual styles, voices and episode history."""
import json, os, pathlib, random

HIST_DIR = pathlib.Path("history")


def load(name):
    try:
        h = json.loads((HIST_DIR / f"{name}.json").read_text())
    except Exception:
        h = {}
    h.setdefault("episodes", [])
    h.setdefault("works", {})
    h.setdefault("log", {})
    return h


def save(name, hist):
    HIST_DIR.mkdir(exist_ok=True)
    (HIST_DIR / f"{name}.json").write_text(json.dumps(hist, indent=1))


STYLE_TOWN = ("stylized 3D render, blocky toy-town world, glossy plastic look, bright saturated "
              "colors, soft cinematic lighting, shallow depth of field, vertical composition, "
              "highly detailed, clean, no text, no watermark")
STYLE_ANIME = ("cinematic dark-fantasy digital illustration, dramatic rim lighting, deep shadows, "
               "painterly, symbolic composition, anonymous silhouetted figures, atmospheric, "
               "vertical composition, highly detailed, no text, no logos, no watermark")

VIDEO_RULES = """Write TWO versions of the SAME story: (a) "full_story", a complete, well-written telling in
250-400 words, 3-5 short paragraphs, easy to read in a caption; (b) "scenes", a SUMMARIZED version for a
45-second video, exactly 10 scenes. Scene 10 must end by telling viewers the full story is in the caption.
Video structure:
1 HOOK: the first line must stop the scroll (an impossible rule, shocking claim or question).
2-4 SETUP: introduce the hero and what they want, concrete and visual.
5-8 ESCALATE: every scene adds a NEW problem, discovery or reversal; cause leads to effect.
9 TWIST: a reveal that recontextualizes what we saw.
10 END: a punchy last line that makes people comment or watch again.
Style: spoken narration only, short punchy sentences (max 13 words), vivid specific details, emotional
stakes, no filler, no stage directions, family-friendly."""

SPEC = """Return ONLY JSON:
{"title": "curiosity-driven title under 55 chars, no series prefix", "description": "2 sentences",
 "tags": ["..."], "hero": "HERO_RULE",
 "full_story": "the complete 250-400 word text, paragraphs separated by two newlines",
 "scenes": [{"line": "narration", "image_prompt": "IMAGE_RULE"}]}
Exactly 10 scenes."""

TOWN_THEMES = [
    "ordinary kids in a town secretly wake up with strange superpowers and must hide them",
    "a mystery: something different goes missing from the town every night",
    "school life with a hidden twist behind the friendliest teacher",
    "a villain who looks like the nicest person in town and a hero nobody believes",
    "a secret society that runs the town from underneath it",
    "a town where one bizarre rule must be obeyed and breaking it has strange consequences",
    "a time capsule that predicts what townspeople will do next",
    "a new kid discovers the town repeats the same day and tries to break the loop",
    "a rivalry between two schools that hides an ancient secret",
]

WORKS = {
    "Jujutsu Kaisen": ("a high-school student swallows a cursed finger, joins a school of sorcerers who fight "
                       "curses; arcs include the first cursed-womb mission, the Kyoto exchange event, the "
                       "Shibuya incident and the Culling Game", True),
    "Black Clover": ("two orphans, one with no magic but an anti-magic five-leaf grimoire, compete to become "
                     "Wizard King in the Clover Kingdom; arcs include the Black Bulls, the witches' forest, "
                     "the Eye of the Midnight Sun and the Spade Kingdom", True),
    "Lord of the Mysteries": ("a modern man wakes as Klein Moretti in a steampunk Victorian world of Beyonder "
                              "potion sequences, secret churches, a mysterious Tarot club and a foggy "
                              "gray space ruled by 'The Fool'", True),
    "Shadow Slave": ("Sunny, a poor youth, is dragged by the Nightmare Spell into a deadly dream world as a "
                     "Sleeper, awakens a shadow-related Aspect and fights to survive and rise", True),
    "A Regressor's Tale of Cultivation": ("a cultivation story about a regressor who returns in time to "
                                          "change his fate", False),
    "The Artist Who Paints Dungeons": ("a story about an artist whose paintings relate to dungeons", False),
}


def _fill(spec, hero, image):
    return spec.replace("HERO_RULE", hero).replace("IMAGE_RULE", image)


def build_town(hist):
    recent = [e["title"] for e in hist["episodes"][-6:]]
    theme = random.choice(TOWN_THEMES)
    prompt = f"""You are a top YouTube Shorts story writer. Write an ORIGINAL story about ONE invented
protagonist (give them a first name) in a blocky toy-town, in the popular "In this town, ..." format.
Theme: {theme}. End on a cliffhanger that makes viewers want part two. Never use real characters or
plots from existing media. Do not repeat these recent episodes: {recent}.
{VIDEO_RULES}
{_fill(SPEC, "protagonist in 15 words (blocky toy character, clothes, hair)",
       "what we SEE: setting, action, camera angle, lighting, mood")}"""
    return {"series": "town", "kind": "town", "prompt": prompt, "style": STYLE_TOWN,
            "voice": "en-US-AndrewMultilingualNeural",
            "hero_default": "a friendly blocky toy character with a bright jacket",
            "tags": ["shorts", "storytime", "inthistown", "blocky", "mystery", "superpowers"],
            "note": "An original story in a blocky toy-world style. Made with AI visuals and voice."}


def build_anime(hist, avoid=()):
    fmt, want = os.environ.get("FORMAT", "auto"), os.environ.get("WORK", "auto")
    if want in WORKS:
        work = want
    else:
        names = [w for w in WORKS if w not in avoid] or list(WORKS)
        random.shuffle(names)
        work = min(names, key=lambda w: sum(1 for e in hist["episodes"] if e.get("work") == w))
    hint, known = WORKS[work]
    kind = fmt if fmt in ("recap", "whatif") else ("recap" if len(hist["episodes"]) % 2 == 0 else "whatif")
    n = hist["works"].get(work, 0) + 1
    visuals = ("Image prompts must be symbolic and atmospheric: silhouettes, hands, objects, landscapes, "
               "crowds seen from behind. NEVER depict recognizable characters or faces, never use "
               "character names or logos in image prompts.")
    hero = "an anonymous silhouetted figure (cloak, posture, one glowing detail), never a known character"
    sure = ("Use ONLY plot details you are confident are real; stay high-level rather than inventing. "
            "If you do not know this work well enough to do this accurately, return only {\"skip\": true}.")
    if kind == "recap":
        prev = [x["summary"] for x in hist["log"].get(work, [])[-3:]]
        brief = (f"Recap Part {n} of \"{work}\". Background (high level): {hint}. Part 1 covers the premise "
                 f"and the first events; later parts continue the plot IN ORDER, one small chunk each. "
                 f"Previous parts covered: {prev}. {sure}")
    else:
        brief = (f"Write an ORIGINAL what-if scenario inspired by \"{work}\" (background: {hint}): a "
                 f"hypothetical alternate event, theory or fight. Make clear it is fan speculation, not "
                 f"canon. {sure}")
    prompt = f"""You are a top YouTube Shorts anime and novel story writer. {brief}
Narration is entirely in your own words; never quote the work. Do not repeat recent episodes:
{[e['title'] for e in hist['episodes'][-6:]]}.
{VIDEO_RULES}
{visuals}
{_fill(SPEC, hero, "what we SEE: symbolic, atmospheric scene, camera angle, lighting, mood")}"""
    return {"series": "anime", "kind": kind, "work": work, "n": n, "prompt": prompt,
            "style": STYLE_ANIME, "voice": "en-US-ChristopherNeural", "hero_default": hero,
            "tags": ["shorts", "anime", "manhwa", "webnovel", kind, work.lower().replace(" ", "").replace("'", "")],
            "note": (f"Unofficial fan {'recap' if kind == 'recap' else 'what-if speculation'} of {work}. "
                     "All rights belong to the original creators. No footage, panels or text from the "
                     "original are used; narration and visuals are original.")}


def build(name, hist, avoid=()):
    return build_anime(hist, avoid) if name == "anime" else build_town(hist)


def finish(meta, data, hist):
    """Final title/description/tags, and update the history in memory."""
    intro = data.get("description", "").strip()
    t = data.get("title", "Untitled").strip()
    if meta["series"] == "anime":
        w = meta["work"]
        data["title"] = (f"{w} Recap #{meta['n']}: {t}" if meta["kind"] == "recap"
                         else f"{w} What If: {t}")
    data["tags"] = list(dict.fromkeys(meta["tags"] + data.get("tags", [])))[:15]
    story = (data.get("full_story") or " ".join(s["line"] for s in data["scenes"])).strip()
    story = story.replace("<", "").replace(">", "")
    data["full_story"] = story
    data["description"] = (intro + "\n\nFULL STORY:\n" + story
                           + "\n\n" + meta["note"])[:4700]
    hist["episodes"].append({"title": data["title"], "kind": meta["kind"], "work": meta.get("work")})
    if meta["series"] == "anime" and meta["kind"] == "recap":
        hist["works"][meta["work"]] = meta["n"]
        hist["log"].setdefault(meta["work"], []).append(
            {"n": meta["n"], "summary": intro[:300]})
    return data

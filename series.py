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

VIDEO_RULES = """Write TWO versions of the SAME story:
(a) "full_story": 140-180 words, 3 short paragraphs, readable as a caption.
(b) "scenes": exactly 10 scenes for a 30-40 second Short.
Each scene line is 5-7 natural spoken words. Use contractions where natural, varied sentence openings, simple vivid language, and punctuation that creates realistic pauses. Each image_prompt is 8-16 visual words. Vary the subject, setting, and camera angle across scenes; do not reuse the same silhouette pose or background.
Scene 10 must end by telling viewers the full story is in the caption.
1 HOOK: start immediately with the strangest rule, danger, or unanswered question. No greeting or setup before the hook.
2-4 SETUP: introduce hero and goal with concrete visuals.
5-8 ESCALATE: every scene adds a new problem, discovery or reversal; avoid repeating information.
9 TWIST: reveal that changes what viewers thought.
10 END: finish on a specific cliffhanger or question, then say exactly: "Full story in caption."
Spoken narration only. No stage directions, generic filler, fake facts, or repetitive phrases. Proofread the story for grammar, spelling, continuity, and complete words before returning it. Keep the story easy to follow on first listen and family-friendly.
Never copy dialogue or prose from an existing work."""

SPEC = """Return ONLY this JSON structure:
{"title":"curiosity-driven title under 55 chars","description":"2 short sentences",
 "tags":["..."],"hero":"HERO_RULE","full_story":"140-180 words, paragraphs separated by blank lines",
 "scenes":[{"line":"short narration","image_prompt":"IMAGE_RULE"}]}
Exactly 10 scene objects. No markdown fences."""

TOWN_THEMES = [
    "ordinary kids secretly wake up with strange superpowers and must hide them",
    "something different goes missing from town every night",
    "school life hides a secret behind the friendliest teacher",
    "a villain looks like the nicest person in town",
    "a secret society secretly runs the town underground",
    "one bizarre town rule has strange consequences when broken",
    "a time capsule predicts what townspeople will do next",
    "a new kid discovers town repeats the same day",
    "two rival schools hide an ancient secret",
]

WORKS = {
    "Jujutsu Kaisen": ("A student joins sorcerers who fight curses; major story elements include cursed objects, school missions, rival schools, Shibuya and the Culling Game.", True),
    "Black Clover": ("Two orphans compete to become Wizard King; one has no magic but gains anti-magic, joins the Black Bulls and faces major kingdom threats.", True),
    "Lord of the Mysteries": ("Zhou Mingrui awakens in the body of Klein Moretti in an alternate Victorian-era world. He is trying to understand Klein’s death and his own arrival. The world includes steam-powered machinery, churches, divination, tarot, potions and sealed artifacts. Beyonder potions grant extraordinary abilities. Klein encounters a mysterious space above gray fog and summons two other people there, forming the Tarot Club.", True),
    "Shadow Slave": ("Sunny is drawn by the Nightmare Spell into a deadly dream world, awakens a shadow-related Aspect and struggles to survive.", True),
    "A Regressor's Tale of Cultivation": ("A cultivation story involving a protagonist who regresses and tries to change his fate.", False),
    "The Artist Who Paints Dungeons": ("A fantasy story centered on an artist and dungeon-related paintings.", False),
}


RECAP_RULES = """RECAP ACCURACY AND ORIGINALITY:
The background note is the complete approved canon fact sheet for this episode. Treat only facts explicitly stated in it as canon. Do not invent or infer specific events, locations, rules, objects, powers, characters, relationships, motives, outcomes, or chronology. Do not turn a setting detail into a rule. Do not invent a twist to fill the scene template. If these notes cannot support a coherent recap without padding or invented facts, return only {"skip":true}. Add one concise original analytical observation about the stated facts, clearly framed as commentary rather than canon; do not merely retell events. Never quote the source work.
"""

def _fill(spec, hero, image):
    return spec.replace("HERO_RULE", hero).replace("IMAGE_RULE", image)


def build_town(hist):
    recent = [e["title"] for e in hist["episodes"][-6:]]
    theme = random.choice(TOWN_THEMES)
    prompt = f"""Write an ORIGINAL "In this town..." story about ONE invented protagonist in a blocky toy-town.
Theme: {theme}. End with a strong cliffhanger. Never use real characters or plots from existing media.
Every image_prompt must show the exact action and location in its narration line. Do not move a scene to an unrelated setting or invent props that change the story.
Avoid repeating: {recent}.
{VIDEO_RULES}
{_fill(SPEC, "15-word description of the blocky protagonist's clothes and hair",
       "FIRST WORD must be the best matching location: street, park, classroom, house, market, underground or library; then show the exact narrated action, camera angle and lighting. Never choose an unrelated setting.")}"""
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
        names = [w for w, (_, known) in WORKS.items() if known and w not in avoid]
        if not names:
            names = [w for w, (_, known) in WORKS.items() if known]
        if not names:
            raise RuntimeError("No verified works are configured")
        work = min(names, key=lambda w: sum(1 for e in hist["episodes"] if e.get("work") == w))
    hint, known = WORKS[work]
    if not known:
        raise RuntimeError(f"No reliable plot notes configured for {work}; refusing to invent a recap")
    kind = fmt if fmt in ("recap", "whatif") else ("recap" if len(hist["episodes"]) % 2 == 0 else "whatif")
    n = hist["works"].get(work, 0) + 1
    visuals = ("Use symbolic atmospheric images only: silhouettes, hands, objects, landscapes, "
               "crowds from behind. No recognizable characters, faces, character names or logos in images.")
    hero = "anonymous silhouetted figure, cloak, posture, one glowing detail, never a known character"
    sure = ("Use only plot details you are confident are real. If unsure, return only {\"skip\":true}.")
    if kind == "recap":
        prev = [x["summary"] for x in hist["log"].get(work, [])[-3:]]
        brief = (f"Unofficial recap Part {n} of {work}. Verified background facts: {hint}. "
                 f"Part 1 covers the premise and opening events; later parts continue chronologically. "
                 f"Previously covered: {prev}. {sure}\n{RECAP_RULES}")
    else:
        brief = (f"Create an ORIGINAL fan what-if inspired by {work}. Background: {hint}. Clearly label it "
                 f"as speculation, not canon. {sure}")
    prompt = f"""You write accurate anime, manhwa and novel short stories. {brief}
Use original narration; never quote the work. Avoid these recent titles: {[e['title'] for e in hist['episodes'][-6:]]}.
{VIDEO_RULES}
{visuals}
{_fill(SPEC, hero, "symbolic atmospheric scene, camera angle and lighting")}"""
    return {"series": "anime", "kind": kind, "work": work, "n": n, "prompt": prompt,
            "style": STYLE_ANIME, "voice": "en-US-ChristopherNeural", "hero_default": hero,
            "tags": ["shorts", "anime", "manhwa", "webnovel", kind, work.lower().replace(" ", "").replace("'", "")],
            "note": (f"Unofficial fan {'recap' if kind == 'recap' else 'what-if speculation'} of {work}. "
                     "All rights belong to the original creators. No footage, panels or text from the "
                     "original are used; narration and visuals are original.")}


def build(name, hist, avoid=()):
    return build_anime(hist, avoid) if name == "anime" else build_town(hist)


def finish(meta, data, hist):
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
        hist["log"].setdefault(meta["work"], []).append({"n": meta["n"], "summary": intro[:300]})
    return data

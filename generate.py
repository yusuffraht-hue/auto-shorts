"""Daily pipeline: story -> narration -> vertical visuals -> readable captions -> YouTube."""
import asyncio
import json
import os
import pathlib
import random
import re
import subprocess
import time
import urllib.parse
import xml.etree.ElementTree as ET

import edge_tts
import requests
from llm import call_llm

OUT = pathlib.Path("out")
OUT.mkdir(exist_ok=True)
FONT = os.environ.get("FONT", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
PRIVACY = os.environ.get("PRIVACY", "private")
# Brian is a calmer conversational narrator than the old +10% default.
VOICE = os.environ.get("VOICE", "en-US-BrianNeural")
RATE = os.environ.get("RATE", "-5%")

STYLE = (
    "polished cinematic 3D animation still, premium stylized blocky toy-world, "
    "expressive readable character acting, detailed environment, dramatic but clear "
    "composition, cinematic lighting, rich controlled colors, depth of field, "
    "vertical 9:16 framing, no words, no letters, no captions, no watermark"
)
THEMES = [
    "a sorcery school where students hide dangerous techniques",
    "a secret society where every potion has a terrible cost",
    "a magic kingdom where a powerless kid discovers an anti-magic ability",
    "a dungeon hunter world where a weak hunter secretly levels up",
    "an isekai village where one ordinary villager has a forbidden skill",
    "a cultivation sect where a forgotten student finds a secret manual",
    "a tournament where the final rule changes everything",
    "a regression world where one person remembers the future",
    "a town where everyone must obey one impossible rule",
    "a town where tomorrow's events appear in a mysterious notebook",
]
BASE_TAGS = ["shorts", "storytime", "animation", "fantasy", "originalstory"]


def trend_ideas():
    """Optional inspiration only; never let a trend dictate the story."""
    try:
        r = requests.get("https://trends.google.com/trending/rss?geo=US", timeout=12)
        r.raise_for_status()
        return [i.findtext("title") for i in ET.fromstring(r.text).iter("item")][:5]
    except Exception as e:
        print("trend fetch skipped:", e)
        return []


def validate_story(data):
    if not isinstance(data, dict):
        raise ValueError("Story response is not a JSON object")
    required = ("title", "description", "hero", "scenes")
    if any(not data.get(k) for k in required):
        raise ValueError("Story is missing a required field")
    if not isinstance(data["scenes"], list) or len(data["scenes"]) != 7:
        raise ValueError("Story must contain exactly 7 scenes")
    total_words = 0
    for index, scene in enumerate(data["scenes"], 1):
        if not isinstance(scene, dict) or not scene.get("line") or not scene.get("image_prompt"):
            raise ValueError(f"Scene {index} is incomplete")
        count = len(scene["line"].split())
        if count > 19:
            raise ValueError(f"Scene {index} narration is too long ({count} words)")
        total_words += count
    if not 60 <= total_words <= 112:
        raise ValueError(f"Story length is {total_words} words; expected 60-112")
    data["title"] = str(data["title"]).strip()[:60]
    data["description"] = str(data["description"]).strip()
    data["hero"] = str(data["hero"]).strip()
    return data


def write_script():
    theme = random.choice(THEMES)
    trends = trend_ideas()
    prompt = f"""Act as a professional short-form storyteller and animation director.
Write ONE original, emotionally gripping 40-50 second story for a vertical video.
World/theme: {theme}.
Use the broad appeal of fantasy and mystery, but invent all characters, rules and events.

STORY DESIGN:
- The first sentence must create an immediate curiosity gap. Start with "In this world, ..."
- Establish ONE simple, strange rule the viewer understands instantly.
- Follow ONE named protagonist with a clear desire and something to lose.
- Every scene must change the situation. No repeated information or filler.
- Build cause and effect: each decision creates the next problem.
- Include a specific, logical twist in scene 6 that changes what the viewer thought.
- Scene 7 must deliver an emotional or surprising payoff AND leave one strong question.
- Make it feel like a complete mini-story, not a random list of fantasy facts.
- Use concrete objects, actions and consequences. Avoid generic phrases like "everything changed".
- Family-friendly. No gore, slurs, copyrighted characters, copied plots or franchise names.

PACING:
Exactly 7 scenes. Each narration line should be short and easy to say aloud.
Total narration: 70-100 words. Use natural spoken English and varied sentence lengths.
No stage directions, scene labels, emojis, hashtags or sound-effect words in narration.
Avoid starting every line with "Then". Read it aloud mentally; it must sound human.

VISUAL CONTINUITY:
Invent ONE distinctive protagonist. The "hero" field must describe their exact appearance
(clothing colors, hair, face/accessory and body shape) in 20-30 words.
Repeat that same identity in every image_prompt. Do not change clothes, hair or age.
Each image_prompt must describe one visible moment, a clear action, location, camera framing
and emotion. Do not put multiple moments or time jumps in one image.

TREND IDEAS (optional background inspiration; do not force them into the plot):
{trends}

Return ONLY valid JSON with this exact shape:
{{"title":"curiosity-driven title, max 60 characters",
"description":"one-sentence spoiler-free description",
"tags":["relevant tags"],
"hero":"fixed protagonist appearance",
"scenes":[{{"line":"spoken narration","image_prompt":"visual description"}}]}}
There must be exactly 7 scene objects."""
    try:
        data = validate_story(json.loads(call_llm(prompt)))
    except Exception as error:
        # Keep the daily pipeline alive if a free LLM returns truncated or invalid JSON.
        print("LLM story rejected; using validated fallback story:", repr(error))
        data = fallback_story()
    data["tags"] = list(dict.fromkeys(BASE_TAGS + data.get("tags", [])))[:15]
    data["description"] += (
        "\n\nOriginal fictional story with AI-assisted visuals and narration."
    )
    return data


def fallback_story():
    """A complete original story used only when free text APIs fail validation."""
    hero = "Milo, a small blocky boy with a teal jacket, orange scarf, dark curly hair and round glasses"
    scenes = [
        {
            "line": "In this world, every child receives one key that opens a single locked door.",
            "image_prompt": "Milo receives a glowing brass key in a crowded school courtyard, wide cinematic shot, curious expression"
        },
        {
            "line": "Most keys reveal treasure, secret rooms, or the future people dream about.",
            "image_prompt": "Milo watches other children open sparkling doors showing treasure and bright futures, over-the-shoulder view"
        },
        {
            "line": "But Milo's key opens a tiny door hidden beneath his classroom floor.",
            "image_prompt": "Milo kneels beside a tiny wooden door beneath classroom floorboards, close-up, nervous curiosity"
        },
        {
            "line": "Behind it, hundreds of keys hang beside rows of sleeping shadows.",
            "image_prompt": "Milo enters a mysterious underground chamber filled with hanging keys and still shadow silhouettes, dramatic wide shot"
        },
        {
            "line": "A dusty note explains that each key belongs to someone who disappears tomorrow.",
            "image_prompt": "Milo holds an old handwritten note beneath a single beam of light, worried close-up"
        },
        {
            "line": "Then he finds one key marked with his own name, and it is warm.",
            "image_prompt": "Milo stares at a glowing key engraved with his name, trembling hand, intense close-up"
        },
        {
            "line": "He turns around; his shadow is holding the tiny door open from the other side.",
            "image_prompt": "Milo faces his own living shadow holding the doorway open behind him, eerie final reveal, dramatic low angle"
        }
    ]
    return {
        "title": "The Key That Already Knew Milo",
        "description": "One strange key leads a schoolboy to a room that should not exist.",
        "tags": ["fantasy", "mystery", "originalstory"],
        "hero": hero,
        "scenes": scenes
    }


def get_image(prompt, path, seed):
    """Retry temporary image-provider rate limits without silently using broken files."""
    base = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt)
    for attempt in range(12):
        model = "&model=flux" if attempt < 8 else ""
        url = f"{base}?width=1080&height=1920&nologo=true&seed={seed}{model}"
        wait = 12
        try:
            r = requests.get(url, timeout=240)
            ok = r.status_code == 200 and (
                r.content[:3] == b"\xff\xd8\xff" or r.content[:4] == b"\x89PNG"
            )
            print("image:", r.status_code, len(r.content), "ok" if ok else r.text[:120])
            if ok:
                path.write_bytes(r.content)
                time.sleep(3)
                return
            m = re.search(r"Retry after (\d+)s", r.text)
            if m:
                wait = int(m.group(1)) + 3
            elif r.status_code == 402 or "FREE_LIMIT" in r.text or "every 45 seconds" in r.text:
                wait = 48
            else:
                wait = min(45, 15 + attempt * 3)
        except requests.RequestException as e:
            print("image retry:", e)
        time.sleep(wait)
    raise RuntimeError("Image generation failed after retries")


async def tts_words(text, path):
    """Save speech and return word-level timestamps when the voice provides them."""
    words = []
    com = edge_tts.Communicate(text, VOICE, rate=RATE, boundary="WordBoundary")
    with open(path, "wb") as f:
        async for chunk in com.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 1e7
                end = start + chunk["duration"] / 1e7
                words.append((start, end, chunk["text"]))
    return words


def duration(path):
    result = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", str(path)
    ])
    return float(result.strip())


def even_words(text, dur):
    words = text.split()
    step = dur / max(len(words), 1)
    return [(i * step, (i + 1) * step, word) for i, word in enumerate(words)]


def chunks(words):
    """Build readable 3-5 word caption phrases, keeping short pauses at punctuation."""
    groups, current = [], []
    for word in words:
        candidate = current + [word]
        phrase = " ".join(item[2] for item in candidate)
        punctuation = bool(re.search(r"[.!?]$", word[2]))
        if current and (
            len(current) >= 4 or len(phrase) > 27 or
            (len(current) >= 3 and re.search(r"[.!?]$", current[-1][2]))
        ):
            groups.append(current)
            current = [word]
        else:
            current = candidate
        if punctuation and len(current) >= 2:
            groups.append(current)
            current = []
    if current:
        groups.append(current)

    captions = []
    for index, group in enumerate(groups):
        start = group[0][0]
        end = groups[index + 1][0][0] if index + 1 < len(groups) else group[-1][1]
        phrase = " ".join(item[2] for item in group).strip()
        # Two balanced lines are easier to read than one very long line.
        if len(phrase) > 19 and " " in phrase:
            parts = phrase.split()
            midpoint = len(parts) // 2
            phrase = " ".join(parts[:midpoint]) + "\n" + " ".join(parts[midpoint:])
        captions.append((max(0, start), max(start + 0.12, end), phrase.upper()))
    return captions


def make_clip(i, scene, hero, seed):
    img = OUT / f"s{i}.jpg"
    aud = OUT / f"s{i}.mp3"
    clip = OUT / f"s{i}.mp4"

    # Repeat the exact identity description in every prompt to reduce character drift.
    prompt = (
        f"Same recurring main character in every scene, exact identity: {hero}. "
        f"Scene action and composition: {scene['image_prompt']}. {STYLE}"
    )
    get_image(prompt, img, seed)
    words = asyncio.run(tts_words(scene["line"], aud))
    dur = duration(aud) + 0.30
    if not words:
        words = even_words(scene["line"], dur - 0.30)
    captions = chunks(words)
    frames = max(1, int(dur * 25))

    if i % 2 == 0:
        zoom = "z='min(zoom+0.0009,1.16)'"
    else:
        zoom = "z='if(eq(on,1),1.16,max(zoom-0.0009,1.0))'"

    vf = (
        "scale=1620:2880:force_original_aspect_ratio=increase,"
        "crop=1620:2880,"
        f"zoompan={zoom}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s=1080x1920:fps=25"
    )
    for index, (start, end, caption) in enumerate(captions):
        caption_file = OUT / f"caption_{i}_{index}.txt"
        caption_file.write_text(caption, encoding="utf-8")
        color = "yellow" if index % 2 == 0 else "white"
        vf += (
            f",drawtext=fontfile={FONT}:textfile={caption_file}:"
            f"fontcolor={color}:fontsize=68:line_spacing=10:"
            "borderw=5:bordercolor=black:"
            "box=1:boxcolor=black@0.38:boxborderw=16:"
            "x=(w-text_w)/2:y=h*0.70-text_h/2:"
            f"enable='between(t,{start:.3f},{end:.3f})':fix_bounds=1"
        )

    command = [
        "ffmpeg", "-y", "-i", str(img), "-i", str(aud), "-vf", vf,
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11,apad",
        "-t", f"{dur:.2f}", "-c:v", "libx264", "-preset", "veryfast",
        "-pix_fmt", "yuv420p", "-r", "25", "-c:a", "aac", "-ar", "44100",
        str(clip)
    ]
    subprocess.run(command, check=True)
    return clip


def build_video(data):
    hero = data["hero"]
    seed = random.randint(1, 10**6)
    clips = [make_clip(i, scene, hero, seed) for i, scene in enumerate(data["scenes"])]
    listing = OUT / "list.txt"
    listing.write_text("".join(f"file '{clip.name}'\n" for clip in clips), encoding="utf-8")
    final = OUT / "final.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
        "-c", "copy", str(final)
    ], check=True)
    if not final.exists() or final.stat().st_size < 100_000:
        raise RuntimeError("Final video is missing or unexpectedly small")
    return final


def upload_youtube(path, data):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = Credentials(
        None, refresh_token=os.environ["YT_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube.upload"]
    )
    youtube = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {
            "title": data["title"][:90] + " #Shorts",
            "description": data["description"] + "\n\nAI-assisted visuals and voice. #Shorts",
            "tags": data.get("tags", [])[:15],
            "categoryId": "24"
        },
        "status": {
            "privacyStatus": PRIVACY,
            "selfDeclaredMadeForKids": False
        }
    }
    result = youtube.videos().insert(
        part="snippet,status", body=body,
        media_body=MediaFileUpload(str(path), mimetype="video/mp4", resumable=True)
    ).execute()
    print("uploaded:", f"https://www.youtube.com/watch?v={result['id']}", PRIVACY)


if __name__ == "__main__":
    data = write_script()
    print(json.dumps(data, indent=2))
    video = build_video(data)
    if all(os.environ.get(key) for key in (
        "YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"
    )):
        upload_youtube(video, data)
    else:
        print("YouTube secrets not set; video saved at", video)

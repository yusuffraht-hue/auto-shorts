"""Daily pipeline: story script (LLM) -> voice with word timings (edge-tts)
-> 3D blocky-style images (Pollinations flux) -> vertical video with big word-by-word
captions (ffmpeg) -> YouTube upload."""
import asyncio, json, os, pathlib, random, re, subprocess, textwrap, time, urllib.parse
import xml.etree.ElementTree as ET

import edge_tts
import requests
from llm import call_llm

OUT = pathlib.Path("out")
OUT.mkdir(exist_ok=True)
FONT = os.environ.get("FONT", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
PRIVACY = os.environ.get("PRIVACY", "private")
VOICE = os.environ.get("VOICE", "en-US-AndrewMultilingualNeural")
RATE = os.environ.get("RATE", "+8%")

STYLE = ("stylized 3D render, blocky toy-town world, glossy plastic look, bright saturated "
         "colors, soft cinematic lighting, shallow depth of field, vertical composition, "
         "highly detailed, clean, no text, no watermark")
THEMES = [
    "a sorcery school where students hide cursed-energy techniques and exorcise curses",
    "a secret mystery society where drinking potions advances you through ranked sequences and costs your sanity",
    "a magic kingdom where a powerless kid with an anti-magic grimoire tries to become the top mage",
    "a dungeon-and-hunter world with strict rank exams where one weak hunter secretly levels up alone",
    "an isekai village where a reincarnated villager has an overpowered skill nobody understands",
    "a cultivation sect with grumpy elders, breakthrough bottlenecks and secret manuals",
    "a tournament arc where the rules keep changing and everyone has a dramatic backstory",
    "a regression world where one person remembers the whole timeline and tries to dodge doom",
    "a town where money, time or luck works by one bizarre rule that everyone must obey",
    "a town with a time capsule that predicts what the townspeople will do next",
]
BASE_TAGS = ["anime", "manhwa", "manga", "lightnovel", "shorts", "storytime", "inthistown"]
CLASSICS = [
    "Journey to the West (the Monkey King's rebellion against heaven)",
    "Romance of the Three Kingdoms (a famous strategist outwitting a larger army)",
    "Water Margin (outlaws of the marsh banding together)",
    "Investiture of the Gods (gods and immortals fighting a dynasty war)",
    "The Tale of the Bamboo Cutter (the girl found inside glowing bamboo)",
    "Urashima Taro (the fisherman who visits the sea palace)",
    "Momotaro (the peach boy and his animal allies)",
    "The Odyssey (a hero tricking monsters on the way home)",
    "One Thousand and One Nights (a storyteller who survives by cliffhangers)",
    "Beowulf (the hall haunted by a monster)",
    "Dracula (a haunted castle journey)",
    "Frankenstein (a creation that turns on its maker)",
    "The Count of Monte Cristo (prison escape and elaborate revenge)",
    "Norse myths (the gods tricking a giant builder)",
    "Sherlock Holmes (a locked-room mystery solved by tiny clues)",
    "Greek myths (a mortal who challenges the gods)",
]


def trend_ideas():
    try:
        r = requests.get("https://trends.google.com/trending/rss?geo=US", timeout=20)
        return [i.findtext("title") for i in ET.fromstring(r.text).iter("item")][:6]
    except Exception as e:
        print("trend fetch skipped:", e)
        return []


def write_script():
    classic_day = int(time.time() // 86400) % 2 == 0
    if classic_day:
        brief = (f"Retell ONE gripping episode of this public-domain classic as a story-time short: "
                 f"{random.choice(CLASSICS)}. Use its traditional character names. Make it feel like a "
                 "binge-worthy anime episode recap: hook, rising stakes, a twist, a cliffhanger ending.")
        kind = "classic"
    else:
        brief = (f"Write an ORIGINAL story about ONE invented protagonist (give them a first name) in a "
                 f"blocky toy-town, in the popular 'In this town, ...' format. Genre flavor translated into "
                 f"plain story language: {random.choice(THEMES)}. NEVER use real character names or plot "
                 "points from any anime, manga, manhwa, light novel or game.")
        kind = "original"
    prompt = f"""You are a top YouTube Shorts story writer. {brief}
Write TWO versions of the SAME story: (a) "full_story", a complete, well-written telling of the whole story
in 250-400 words, 3-5 short paragraphs, easy to read in a caption; (b) "scenes", a SUMMARIZED version of it
for a 45-second video, 10 scenes. Scene 10 must end by telling viewers the full story is in the caption.
Video structure:
1 HOOK: the first line must stop the scroll (an impossible rule, shocking claim or question).
2-4 SETUP: introduce the hero and what they want, concrete and visual.
5-8 ESCALATE: every scene adds a NEW problem, discovery or reversal; cause leads to effect.
9 TWIST: a reveal that recontextualizes what we saw.
10 END: a punchy last line that makes people comment or watch again.
Style: spoken narration only, short punchy sentences (max 13 words), vivid specific details,
sensory words, emotional stakes, no filler, no stage directions, family-friendly.
Trend inspiration (optional, ignore if it does not fit): {trend_ideas()}
Return ONLY JSON:
{{"title": "curiosity-driven title under 60 chars", "description": "2 sentences", "tags": ["..."],
  "hero": "visual description of the main character in 15 words (blocky toy character, clothes, hair)",
  "full_story": "the complete 250-400 word story, paragraphs separated by two newlines",
  "scenes": [{{"line": "narration", "image_prompt": "what we SEE: setting, action, camera angle, lighting, mood"}}]}}
Exactly 10 scenes."""
    data = json.loads(call_llm(prompt))
    data["tags"] = list(dict.fromkeys(BASE_TAGS + data.get("tags", [])))[:15]
    story = (data.get("full_story") or " ".join(sc["line"] for sc in data["scenes"])).strip()
    story = story.replace("<", "").replace(">", "")
    if kind == "classic":
        note = "A retelling of a public-domain classic in a blocky toy-world style."
    else:
        note = ("Original story inspired by common anime, manga, manhwa and light-novel tropes. "
                "Not affiliated with any studio or publisher.")
    data["full_story"] = story
    data["description"] = (data.get("description", "").strip() + "\n\nFULL STORY:\n" + story
                           + "\n\n" + note)[:4700]
    return data


def get_image(prompt, path, seed):
    """Pollinations free tier allows 1 image per ~45s per IP, so wait out 402 limits."""
    base = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt)
    for attempt in range(12):
        model = "&model=flux" if attempt < 8 else ""
        url = f"{base}?width=1080&height=1920&nologo=true&seed={seed}{model}"
        wait = 10
        try:
            r = requests.get(url, timeout=240)
            ok = r.status_code == 200 and r.content[:3] in (b"\xff\xd8\xff", b"\x89PN")
            print("image:", r.status_code, len(r.content), "ok" if ok else r.text[:120])
            if ok:
                path.write_bytes(r.content)
                time.sleep(3)
                return
            m = re.search(r"Retry after (\d+)s", r.text)
            wait = int(m.group(1)) + 3 if m else 20
        except requests.RequestException as e:
            print("image retry:", e)
        time.sleep(wait)
    raise RuntimeError("image generation failed")


async def tts_words(text, path):
    """Save speech and return [(start, end, word)] using exact word timings when available."""
    words = []
    try:
        com = edge_tts.Communicate(text, VOICE, rate=RATE, boundary="WordBoundary")
        with open(path, "wb") as f:
            async for ch in com.stream():
                if ch["type"] == "audio":
                    f.write(ch["data"])
                elif ch["type"] == "WordBoundary":
                    s = ch["offset"] / 1e7
                    words.append((s, s + ch["duration"] / 1e7, ch["text"]))
    except TypeError:
        await edge_tts.Communicate(text, VOICE, rate=RATE).save(str(path))
    return words


def duration(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "csv=p=0", str(path)])
    return float(out.strip())


def even_words(text, dur):
    ws = text.split()
    step = dur / max(len(ws), 1)
    return [(i * step, (i + 1) * step, w) for i, w in enumerate(ws)]


def chunks(words, dur):
    """Group words into 1-2 word caption chunks with start/end times."""
    groups, cur = [], []
    for w in words:
        if cur and (len(cur) >= 2 or len(" ".join(x[2] for x in cur + [w])) > 14):
            groups.append(cur)
            cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    out = []
    for i, g in enumerate(groups):
        start = g[0][0]
        end = groups[i + 1][0][0] if i + 1 < len(groups) else dur
        out.append((start, end, " ".join(x[2] for x in g)))
    return out


def make_clip(i, scene, hero, seed):
    img, aud, clip = OUT / f"s{i}.jpg", OUT / f"s{i}.mp3", OUT / f"s{i}.mp4"
    prompt = f"{scene['image_prompt']}. Main character: {hero}. {STYLE}"
    get_image(prompt, img, seed)
    words = asyncio.run(tts_words(scene["line"], aud))
    dur = duration(aud) + 0.35
    if not words:
        words = even_words(scene["line"], dur - 0.35)
    caps = chunks(words, dur)
    frames = int(dur * 25)
    zoom = ("z='min(zoom+0.0011,1.22)'" if i % 2 == 0
            else "z='if(eq(on,1),1.22,max(zoom-0.0011,1.0))'")
    vf = ("scale=1620:2880:force_original_aspect_ratio=increase,crop=1620:2880,"
          f"zoompan={zoom}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps=25")
    for k, (s, e, txt) in enumerate(caps):
        cf = OUT / f"c{i}_{k}.txt"
        cf.write_text(txt.upper())
        color = "yellow" if k % 2 else "white"
        vf += (f",drawtext=fontfile={FONT}:textfile={cf}:fontcolor={color}:fontsize=92:"
               f"borderw=9:bordercolor=black:x=(w-text_w)/2:y=h*0.60:"
               f"enable='between(t,{s:.2f},{e:.2f})'")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(img), "-i", str(aud), "-vf", vf, "-af", "apad",
         "-t", f"{dur:.2f}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
         "-ar", "44100", str(clip)],
        check=True, capture_output=True)
    return clip


def build_video(data):
    hero = data.get("hero") or "a friendly blocky toy character with a bright jacket"
    seed = random.randint(1, 10**6)  # one seed for the whole video keeps the look consistent
    clips = [make_clip(i, s, hero, seed) for i, s in enumerate(data["scenes"])]
    lst = OUT / "list.txt"
    lst.write_text("".join(f"file '{c.name}'\n" for c in clips))
    final = OUT / "final.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", str(final)], check=True, capture_output=True)
    return final


def upload_youtube(path, data):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    creds = Credentials(
        None, refresh_token=os.environ["YT_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube.upload"])
    yt = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {
            "title": data["title"][:90] + " #Shorts",
            "description": data["description"] + "\n\nAI-generated visuals and voice. #Shorts",
            "tags": data.get("tags", [])[:15], "categoryId": "24"},
        "status": {"privacyStatus": PRIVACY, "selfDeclaredMadeForKids": False},
    }
    res = yt.videos().insert(
        part="snippet,status", body=body,
        media_body=MediaFileUpload(str(path), mimetype="video/mp4", resumable=True)).execute()
    print("uploaded:", f"https://www.youtube.com/watch?v={res['id']}", PRIVACY)


if __name__ == "__main__":
    data = write_script()
    print(json.dumps(data, indent=2))
    (OUT / "story.txt").write_text(data["title"] + "\n\n" + data["full_story"] + "\n\n"
                                   + " ".join("#" + t.replace(" ", "") for t in data["tags"]))
    video = build_video(data)
    if all(os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")):
        upload_youtube(video, data)
    else:
        print("YouTube secrets not set; video saved at", video)

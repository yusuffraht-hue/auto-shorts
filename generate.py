"""Pipeline for one series (set SERIES=town or anime): story (LLM) -> voice with word timings
(edge-tts) -> images (Pollinations flux) -> vertical video with big word-by-word captions
(ffmpeg) -> YouTube upload -> episode history."""
import asyncio, json, os, pathlib, random, re, subprocess, textwrap, time, urllib.parse

import edge_tts
import requests
from llm import call_llm
import series

OUT = pathlib.Path("out")
OUT.mkdir(exist_ok=True)
FONT = os.environ.get("FONT", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
PRIVACY = os.environ.get("PRIVACY", "private")
VOICE = os.environ.get("VOICE", "en-US-AndrewMultilingualNeural")
RATE = os.environ.get("RATE", "+0%")

SERIES = os.environ.get("SERIES", "town")


def write_script(hist):
    """Ask the LLM for the story; if it says it does not know the work, pick another."""
    avoid = set()
    for _ in range(5):
        meta = series.build(SERIES, hist, avoid)
        data = json.loads(call_llm(meta["prompt"]))
        if data.get("skip"):
            print("LLM skipped", meta.get("work"), "- trying another")
            avoid.add(meta.get("work"))
            continue
        data = series.finish(meta, data, hist)
        data["style"], data["voice"] = meta["style"], meta["voice"]
        data["hero"] = data.get("hero") or meta["hero_default"]
        return data
    raise RuntimeError("could not get a usable story")


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
            m = re.search(r"Retry after (\\d+)s", r.text)
            if m:
                wait = int(m.group(1)) + 3
            elif r.status_code == 402 or "FREE_LIMIT" in r.text:
                wait = 48
            else:
                wait = 20
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
    """Group words into readable 2-3 word caption chunks with start/end times."""
    groups, cur = [], []
    for w in words:
        if cur and (len(cur) >= 3 or len(" ".join(x[2] for x in cur + [w])) > 24):
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


def make_clip(i, scene, hero, seed, style):
    img, aud, clip = OUT / f"s{i}.jpg", OUT / f"s{i}.mp3", OUT / f"s{i}.mp4"
    prompt = f"{scene['image_prompt']}. Main character: {hero}. {style}"
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
        color = "white"
        vf += (f",drawtext=fontfile={FONT}:textfile={cf}:fontcolor={color}:fontsize=76:box=1:boxcolor=black@0.32:boxborderw=18:shadowcolor=black:shadowx=2:shadowy=2:"
               f"borderw=9:bordercolor=black:x=(w-text_w)/2:y=h*0.68:"
               f"enable='between(t,{s:.2f},{e:.2f})'")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(img), "-i", str(aud), "-vf", vf, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11,apad",
         "-t", f"{dur:.2f}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
         "-ar", "44100", str(clip)],
        check=True, capture_output=True)
    return clip


def build_video(data):
    hero = data.get("hero") or "a friendly blocky toy character with a bright jacket"
    seed = random.randint(1, 10**6)  # one seed for the whole video keeps the look consistent
    clips = [make_clip(i, s, hero, seed, data["style"]) for i, s in enumerate(data["scenes"])]
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
    hist = series.load(SERIES)
    data = write_script(hist)
    if not os.environ.get("VOICE"):
        VOICE = data["voice"]
    print(json.dumps({k: v for k, v in data.items() if k != "full_story"}, indent=2))
    (OUT / "story.txt").write_text(data["title"] + "\n\n" + data["full_story"] + "\n\n"
                                   + " ".join("#" + t.replace(" ", "") for t in data["tags"]))
    video = build_video(data)
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"
    if dry_run:
        print("DRY RUN: video generated but not uploaded; history was not changed.")
    elif all(os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")):
        upload_youtube(video, data)
        series.save(SERIES, hist)
    else:
        print("YouTube secrets not set; video saved at", video)
        series.save(SERIES, hist)

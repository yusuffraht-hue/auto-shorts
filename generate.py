"""Pipeline for one series (set SERIES=town or anime): story (LLM) -> voice with word timings
(edge-tts) -> images (Pollinations flux) -> vertical video with big word-by-word captions
(ffmpeg) -> YouTube upload -> episode history."""
import asyncio, json, os, pathlib, random, re, shutil, subprocess, textwrap, time, urllib.parse

import edge_tts
import requests
from llm import call_llm
import editorial
import series
import quality

OUT = pathlib.Path(os.environ.get("SHORTS_OUTPUT", "out"))
OUT.mkdir(parents=True, exist_ok=True)
FONT = os.environ.get("FONT", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
PRIVACY = os.environ.get("PRIVACY", "private")
VOICE = os.environ.get("VOICE", "en-US-AndrewMultilingualNeural")
RATE = os.environ.get("RATE", "+0%")

SERIES = os.environ.get("SERIES", "town")

SHOT_COMPOSITIONS = (
    "wide establishing shot showing the full environment",
    "extreme close-up of the important object or clue",
    "low-angle dramatic shot with strong foreground depth",
    "overhead view showing the layout and surrounding details",
    "side-profile medium shot with a different background",
    "macro detail shot focused on a small visual clue",
    "dynamic diagonal action composition with motion",
    "distant figure framed by a large environment",
    "over-the-shoulder view revealing what the subject sees",
    "wide final reveal with clear foreground and background",
)


def accepted_script(meta, data, hist, report):
    data = series.finish(meta, data, hist)
    data["quality_report"] = report
    data["style"], data["voice"] = meta["style"], meta["voice"]
    data["hero"] = data.get("hero") or meta["hero_default"]
    return data


class NoEditorialReserve(RuntimeError):
    """A production slot has no unused, eligible story."""


def reserve_script(hist, meta):
    """Select the first unused, eligible reviewed script."""
    entries = json.loads(pathlib.Path(__file__).with_name("editorial_reserve.json").read_text())
    scripts = entries.get(meta["kind"], [])
    if isinstance(scripts, dict):
        scripts = [scripts]
    if os.environ.get("EDITORIAL_TEST_LATEST") == "1" and os.environ.get("RENDER_CHECK") == "1":
        scripts = reversed(scripts)
    used = {episode.get("reserve_id") for episode in hist["episodes"]}
    for data in scripts:
        reserve_id = data["title"]
        if reserve_id in used:
            continue
        chosen_meta = meta
        if meta["series"] == "anime":
            topic_id = data.get("topic_id")
            avoid = {topic["id"] for topic in editorial.load_topics() if topic["id"] != topic_id}
            try:
                chosen_meta = series.build("anime", hist, avoid)
            except RuntimeError:
                continue
            if chosen_meta.get("topic_id") != topic_id:
                continue
        report = quality.check(data, hist)
        if not report["passed"]:
            print("Editorial reserve failed quality checks:", report["issues"])
            continue
        print("Using editorial reserve for", meta["kind"], reserve_id)
        result = accepted_script(chosen_meta, data, hist, report)
        hist["episodes"][-1]["reserve_id"] = reserve_id
        return result
    return None


def write_script(hist):
    """Generate, quality-check and repair a story before recording it in history."""
    if os.environ.get("EDITORIAL_RESERVE_ONLY") == "1":
        try:
            meta = series.build(SERIES, hist)
        except RuntimeError as error:
            raise NoEditorialReserve(str(error)) from error
        if data := reserve_script(hist, meta):
            return data
        raise NoEditorialReserve("No unused editorial reserve passed the quality gate")
    avoid = set()
    last_provider_error = None
    for _ in range(5):
        try:
            meta = series.build(SERIES, hist, avoid)
        except RuntimeError:
            break
        feedback = ""
        for _ in range(2):
            try:
                data = json.loads(call_llm(meta["prompt"] + feedback))
            except RuntimeError as error:
                last_provider_error = error
                print("Script provider failed for this draft:", error)
                break
            last_provider_error = None
            if data.get("skip"):
                print("LLM skipped", meta.get("work"), "- trying another")
                break
            report = quality.check(data, hist)
            if report["passed"]:
                return accepted_script(meta, data, hist, report)
            print("story quality gate rejected draft:", report["issues"])
            feedback = (
                "\n\nQUALITY REPAIR: Correct the specific issues below in the previous draft. "
                "Preserve the title, premise, source facts and scene order. "
                "Keep fields that already pass and return the full corrected JSON.\nIssues: "
                + "; ".join(report["issues"])
                + "\nPrevious draft JSON:\n"
                + json.dumps(data, ensure_ascii=True)
            )
        avoid.add(meta.get("topic_id") or meta.get("work"))
        if reserve := reserve_script(hist, meta):
            return reserve
    raise RuntimeError("could not generate a story that passed the quality gate") from last_provider_error


def get_image(prompt, path, seed):
    """Pollinations free tier allows 1 image per ~45s per IP, so wait out 402 limits."""
    import cloudflare_images
    if cloudflare_images.generate(prompt, path):
        print("image: Cloudflare FLUX")
        return
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
                time.sleep(48)
                return
            m = re.search(r"Retry after (\d+)s", r.text)
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


def local_voice(text, path):
    speech = path.with_suffix(".txt")
    speech.write_text(text)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"flite=textfile={speech}:voice=slt", str(path)],
                   check=True, capture_output=True)


async def tts_words(text, path):
    """Synthesize narration and return word timings when available."""
    if os.environ.get("LOCAL_MEDIA_ONLY") == "1":
        from offline_narration import synthesize

        try:
            if synthesize(text, path):
                return []
        except Exception as error:
            print(f"Kokoro synthesis failed ({type(error).__name__})")
        print("Narration: offline Flite fallback")
        local_voice(text, path)
        return []
    voices = [VOICE, "en-US-AndrewNeural", "en-US-GuyNeural", "en-US-AriaNeural"]
    for attempt, voice in enumerate(voices * 2):
        words = []
        try:
            try:
                com = edge_tts.Communicate(text, voice, rate=RATE, boundary="WordBoundary")
            except TypeError:
                com = edge_tts.Communicate(text, voice, rate=RATE)
            with open(path, "wb") as f:
                async for ch in com.stream():
                    if ch["type"] == "audio":
                        f.write(ch["data"])
                    elif ch["type"] == "WordBoundary":
                        s = ch["offset"] / 1e7
                        words.append((s, s + ch["duration"] / 1e7, ch["text"]))
            if pathlib.Path(path).stat().st_size > 1000:
                return words
        except Exception as e:
            print("tts retry:", voice, repr(e)[:120])
        await asyncio.sleep(2 + attempt)
    print("tts: falling back to local narration")
    local_voice(text, path)
    return []


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


def caption_font_size(text):
    """Shrink long uppercase captions so their text and box stay inside the 1080px frame."""
    length = max(len(str(text or "")), 1)
    estimated_width_per_character = 0.82
    available_width = 820  # leaves room for padding and the app's right-side controls
    return max(24, min(76, int(available_width / (estimated_width_per_character * length))))


def make_clip(i, scene, hero, seed, style, *, denoise=8):
    img, aud, clip = OUT / f"s{i}.jpg", OUT / f"s{i}.mp3", OUT / f"s{i}.mp4"
    prompt = f"{scene['image_prompt']}. Composition: {SHOT_COMPOSITIONS[i % len(SHOT_COMPOSITIONS)]}. Visual anchor: {hero}. {style}"
    shot = OUT / f"shot_{i}.png"
    if shot.exists():
        img, pre = shot, f"nlmeans=s={denoise}:p=7:r=15,"
    else:
        if os.environ.get("LOCAL_MEDIA_ONLY") == "1":
            raise RuntimeError(f"Missing local illustration for scene {i + 1}")
        get_image(prompt, img, seed)
        pre = ""  # preserve provider attribution
    words = asyncio.run(tts_words(scene["line"], aud))
    dur = duration(aud) + 0.35
    if not words:
        words = even_words(scene["line"], dur - 0.35)
    caps = chunks(words, dur)
    frames = max(2, int(dur * 25))
    # Ease the camera in and out over the length of each shot.
    motion = f"(1-cos(PI*on/{frames - 1}))/2"
    zoom = f"1.01+0.09*{motion}" if i % 2 == 0 else f"1.10-0.09*{motion}"
    vf = (pre + "scale=1620:2880:force_original_aspect_ratio=increase,crop=1620:2880,"
          f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps=25")
    for k, (s, e, txt) in enumerate(caps):
        cf = OUT / f"c{i}_{k}.txt"
        cf.write_text(txt.upper())
        vf += (f",drawtext=fontfile={FONT}:textfile={cf}:expansion=none:fontcolor=white:"
               f"fontsize={caption_font_size(txt)}:box=1:boxcolor=0x10141d@0.84:boxborderw=14:"
               f"x=(w-text_w)/2-36:y=h*0.71-text_h/2:"
               f"enable='gte(t,{s:.4f})*lt(t,{e:.4f})'")
    subprocess.run(
        ["ffmpeg", "-y", "-filter_threads", "2", "-i", str(img), "-i", str(aud), "-vf", vf, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11,apad",
         "-t", f"{dur:.2f}", "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-threads", "2", "-pix_fmt", "yuv420p", "-c:a", "aac",
         "-ar", "44100", str(clip)],
        check=True, capture_output=True)
    return clip


def blender_stills(data):
    """Town series: render consistent 3D blocky-town stills with Blender (free, CPU).
    Any failure just falls back to AI images for the scenes without a still."""
    if os.environ.get("USE_BLENDER") != "1" or not shutil.which("blender"):
        return
    try:
        import shots
        spec = shots.plan(data)
        if os.environ.get("RENDER_CHECK") == "1":
            spec.update(width=288, height=512, samples=4)
        (OUT / "shots.json").write_text(json.dumps(spec))
        t0 = time.time()
        r = subprocess.run(["blender", "-b", "-t", "4", "-noaudio", "-P", "blender/render_shots.py", "--",
                            str(OUT / "shots.json"), str(OUT)],
                           capture_output=True, text=True, timeout=1800)
        print("blender:", r.returncode, "%.0fs" % (time.time() - t0),
              [l for l in r.stdout.splitlines() if l.startswith("SHOT")][-12:], r.stderr[-300:])
    except Exception as e:
        print("blender stills failed, using AI images:", repr(e)[:200])


def build_video(data, *, denoise=8):
    hero = data.get("hero") or "a friendly blocky toy character with a bright jacket"
    seed = random.randint(1, 10**6)  # one seed for the whole video keeps the look consistent
    clips = [make_clip(i, s, hero, seed, data["style"], denoise=denoise)
             for i, s in enumerate(data["scenes"])]
    lst = OUT / "list.txt"
    lst.write_text("".join(f"file '{c.name}'\n" for c in clips))
    final = OUT / "final.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", "-movflags", "+faststart", str(final)], check=True, capture_output=True)
    return final


def _youtube_upload_body(data):
    return {
        "snippet": {
            "title": data["title"][:90] + " #Shorts",
            "description": data["description"] + "\n\nAI-generated visuals and voice. #Shorts",
            "tags": data.get("tags", [])[:15], "categoryId": "24"},
        "status": {"privacyStatus": PRIVACY, "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": True},
    }


def _execute_youtube_upload(yt, path, data, media_file_upload):
    """Execute exactly one upload request with the disclosure field intact."""
    body = _youtube_upload_body(data)
    request = yt.videos().insert(
        part="snippet,status", body=body,
        media_body=media_file_upload(str(path), mimetype="video/mp4", resumable=True))
    return request.execute()


def youtube_credentials():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google.auth.exceptions import RefreshError
    creds = Credentials(
        None, refresh_token=os.environ["YT_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube.upload"])
    try:
        creds.refresh(Request())
    except RefreshError as exc:
        raise RuntimeError("YouTube authorization failed; renew the refresh token before production runs") from exc
    return creds


def upload_youtube(path, data, creds=None):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    yt = build("youtube", "v3", credentials=creds or youtube_credentials())
    # Do not retry after dropping containsSyntheticMedia. Fail closed on API errors.
    res = _execute_youtube_upload(yt, path, data, MediaFileUpload)
    print("uploaded:", f"https://www.youtube.com/watch?v={res['id']}", PRIVACY)


if __name__ == "__main__":
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"
    queue_only = os.environ.get("YOUTUBE_QUEUE_ONLY", "false").lower() == "true"
    creds = publisher = None
    if not dry_run and not queue_only and os.environ.get("YOUTUBE_PROVIDER") == "composio":
        from post_youtube import publisher_from_env
        publisher = publisher_from_env()
    elif not dry_run and not queue_only:
        if not all(os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")):
            raise RuntimeError("YouTube credentials missing; use dry_run for render-only tests")
        creds = youtube_credentials()
    if os.environ.get("EDITORIAL_TEST_LATEST") == "1" and os.environ.get("RENDER_CHECK") == "1":
        if os.environ.get("GITHUB_EVENT_NAME") == "schedule":
            raise RuntimeError("Editorial preview settings are unavailable for scheduled runs")
        hist = {"episodes": [], "works": {}, "log": {}}
    else:
        hist = series.load(SERIES)
    try:
        data = write_script(hist)
    except NoEditorialReserve as error:
        if not queue_only:
            raise
        (OUT / "quality-report.json").write_text(json.dumps(
            {"passed": False, "state": "skipped", "reason": str(error)}))
        raise SystemExit(0)
    if not os.environ.get("VOICE"):
        VOICE = data["voice"]
    print(json.dumps({k: v for k, v in data.items() if k != "full_story"}, indent=2))
    (OUT / "quality-report.json").write_text(json.dumps(data["quality_report"], indent=2))
    (OUT / "story.txt").write_text(data["title"] + "\n\n" + data["full_story"] + "\n\n"
                                   + " ".join("#" + t.replace(" ", "") for t in data["tags"]))
    if os.environ.get("LOCAL_MEDIA_ONLY") == "1" and SERIES == "anime":
        from trend_video import illustrate
        for index, scene in enumerate(data["scenes"]):
            illustrate(OUT / f"shot_{index}.png", "ANIME & NOVEL STORIES",
                       data["title"], scene["line"], index)
        video = build_video(data)
    else:
        blender_stills(data)
        video = build_video(data, denoise=24)
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"
    if dry_run:
        print("DRY RUN: video generated but not uploaded; history was not changed.")
    elif queue_only:
        manifest = {"schema": 1, "series": SERIES, "run_id": os.environ.get("GITHUB_RUN_ID"),
                    "video": "final.mp4", "metadata": _youtube_upload_body(data),
                    "quality_passed": data["quality_report"]["passed"], "state": "pending_upload",
                    "history": hist}
        (OUT / "youtube-pending.json").write_text(json.dumps(manifest, indent=2))
        print("Render queued for authorized upload; history unchanged.")
    elif publisher is not None:
        # Keep the checked render as an artifact when YouTube rejects preflight.
        receipt = OUT / "youtube-receipt.json"
        try:
            publisher.preflight()
        except RuntimeError as error:
            receipt.write_text(json.dumps({"state": "preflight_blocked", "reason": str(error)}))
            raise
        publisher.publish(video, _youtube_upload_body(data), receipt)
        series.save(SERIES, hist)
    elif creds is not None:
        upload_youtube(video, data, creds)
        series.save(SERIES, hist)

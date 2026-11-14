"""Daily pipeline: trend ideas -> skit script (GitHub Models) -> voice (edge-tts)
-> images (Pollinations) -> vertical video (ffmpeg) -> YouTube upload."""
import asyncio, json, os, pathlib, random, re, subprocess, sys, textwrap, time, urllib.parse
import xml.etree.ElementTree as ET

import edge_tts
import requests

OUT = pathlib.Path("out")
OUT.mkdir(exist_ok=True)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MODEL = os.environ.get("MODEL", "openai/gpt-4o-mini")
PRIVACY = os.environ.get("PRIVACY", "private")
VOICE = os.environ.get("VOICE", "en-US-GuyNeural")


def trend_ideas():
    """Optional inspiration only. Failures are fine."""
    try:
        r = requests.get("https://trends.google.com/trending/rss?geo=US", timeout=20)
        root = ET.fromstring(r.text)
        return [i.findtext("title") for i in root.iter("item")][:8]
    except Exception as e:
        print("trend fetch skipped:", e)
        return []


def write_script():
    ideas = trend_ideas()
    prompt = f"""Write an ORIGINAL 25-35 second vertical-video skit in the popular
"In this town, ..." comedic format: a narrator describes absurd rules of a fictional
blocky toy-town. Do not copy any existing video, creator, or catchphrase.
Optional inspiration from today's trends (use loosely or ignore): {ideas}
Keep it family-friendly. Return ONLY JSON:
{{"title": "...", "description": "...", "tags": ["..."],
  "scenes": [{{"line": "narration, max 18 words",
              "image_prompt": "blocky low-poly toy town scene, bright colors, ..."}}]}}
Exactly 5 scenes. Image prompts must NOT mention Roblox or any brand."""
    r = requests.post(
        "https://models.github.ai/inference/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                 "Content-Type": "application/json"},
        json={"model": MODEL, "temperature": 1.0,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=120,
    )
    r.raise_for_status()
    txt = r.json()["choices"][0]["message"]["content"]
    txt = re.sub(r"^```(?:json)?|```$", "", txt.strip(), flags=re.M).strip()
    data = json.loads(txt)
    assert len(data["scenes"]) >= 3
    return data


def get_image(prompt, path, seed):
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt)
           + f"?width=1080&height=1920&nologo=true&seed={seed}")
    for attempt in range(4):
        try:
            r = requests.get(url, timeout=180)
            if r.status_code == 200 and r.content[:4] != b"<!DO":
                path.write_bytes(r.content)
                return
        except requests.RequestException as e:
            print("image retry:", e)
        time.sleep(10 * (attempt + 1))
    raise RuntimeError("image generation failed")


async def tts(text, path):
    await edge_tts.Communicate(text, VOICE).save(str(path))


def duration(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)])
    return float(out.strip())


def make_clip(i, scene):
    img, aud = OUT / f"s{i}.jpg", OUT / f"s{i}.mp3"
    cap, clip = OUT / f"s{i}.txt", OUT / f"s{i}.mp4"
    get_image(scene["image_prompt"], img, random.randint(1, 10**6))
    asyncio.run(tts(scene["line"], aud))
    dur = duration(aud) + 0.4
    cap.write_text(textwrap.fill(scene["line"], 24))
    frames = int(dur * 25)
    vf = (f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
          f"zoompan=z='min(zoom+0.0008,1.15)':d={frames}:s=1080x1920:fps=25,"
          f"drawtext=fontfile={FONT}:textfile={cap}:fontcolor=white:fontsize=62:"
          f"borderw=6:bordercolor=black:line_spacing=10:x=(w-text_w)/2:y=h*0.68")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(img), "-i", str(aud), "-vf", vf,
         "-t", f"{dur:.2f}", "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-ar", "44100", "-shortest", str(clip)],
        check=True, capture_output=True)
    return clip


def build_video(scenes):
    clips = [make_clip(i, s) for i, s in enumerate(scenes)]
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
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube.upload"])
    yt = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {
            "title": (data["title"][:90] + " #Shorts"),
            "description": data["description"] + "\n\nAI-generated visuals and voice. #Shorts",
            "tags": data.get("tags", [])[:15],
            "categoryId": "24",
        },
        "status": {"privacyStatus": PRIVACY, "selfDeclaredMadeForKids": False},
    }
    res = yt.videos().insert(
        part="snippet,status", body=body,
        media_body=MediaFileUpload(str(path), mimetype="video/mp4", resumable=True),
    ).execute()
    print("uploaded:", f"https://www.youtube.com/watch?v={res['id']}", PRIVACY)


if __name__ == "__main__":
    data = write_script()
    print(json.dumps(data, indent=2))
    video = build_video(data["scenes"])
    if all(os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")):
        upload_youtube(video, data)
    else:
        print("YouTube secrets not set; video saved at", video)

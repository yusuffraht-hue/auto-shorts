"""Use the current Hacker News ranking to choose a sourced tech explainer."""
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests

API = "https://hacker-news.firebaseio.com/v0/"
CARDS = (
    ("browser", r"\b(browser|firefox|chromium|chrome|safari|web platform)\b",
     "What happens when a browser opens a page?",
     "https://developer.mozilla.org/en-US/docs/Learn_web_development/Getting_started/Web_standards/How_the_web_works",
     ("A web browser topic made Hacker News's top stories.",
      "Type a website address, and your browser first needs to find the server.",
      "It requests the page, then reads its HTML to understand the document.",
      "Styles control the layout. Scripts can add behavior. Together they turn a response into a page.")),
    ("database", r"\b(sql|sqlite|postgres|postgresql|database|databases)\b",
     "Why do databases use indexes?",
     "https://www.postgresql.org/docs/current/indexes-intro.html",
     ("A database topic made Hacker News's top stories.",
      "Imagine looking for one name on a list with a million lines.",
      "A database index can help find matching rows without scanning the whole table.",
      "The tradeoff? An index uses space and needs updating when the underlying data changes.")),
    ("software", r"\b(open source|open-source|linux|git|github|compiler|compilers)\b",
     "What does version control track?",
     "https://git-scm.com/book/en/v2/Getting-Started-About-Version-Control",
     ("A software development topic made Hacker News's top stories.",
      "Think about changing the same project from two different laptops.",
      "Version control stores a history of changes, so you can compare versions and recover earlier work.",
      "With Git, a clone usually includes the repository history. That means you can inspect earlier changes locally.")),
    ("space", r"\b(nasa|telescope|telescopes|exoplanet|exoplanets|astronomy)\b",
     "How can a telescope spot an unseen planet?",
     "https://science.nasa.gov/exoplanets/how-we-find-and-characterize/",
     ("An astronomy topic made Hacker News's top stories.",
      "A planet outside our solar system is often too faint to see directly.",
      "If it passes between us and its star, the star can look slightly dimmer.",
      "Repeated dips can help astronomers identify a possible planet. This is called the transit method.")),
)
SENSITIVE = re.compile(r"\b(kill\w*|shoot\w*|war|abuse|exploit\w*|malware|attack\w*|death|crime\w*|fraud|porn\w*)\b", re.I)


def fetch(path):
    response = requests.get(API + path, timeout=8)
    response.raise_for_status()
    return response.json()


def select_topic(now, used, get=fetch):
    ranked = get("topstories.json")[:25]
    with ThreadPoolExecutor(max_workers=5) as workers:
        articles = list(workers.map(lambda item: get(f"item/{item}.json"), ranked))
    for rank, (item_id, item) in enumerate(zip(ranked, articles), 1):
        if not item or item.get("id") != item_id or item.get("type") != "story":
            continue
        if item.get("dead") or item.get("deleted") or f"hn:{item_id}" in used:
            continue
        title = item.get("title", "")
        age = now.timestamp() - item.get("time", 0)
        if not 0 <= age <= 48 * 3600 or item.get("score", 0) < 25 or SENSITIVE.search(title):
            continue
        for key, pattern, headline, source, lines in CARDS:
            if f"topic:{key}" not in used and re.search(pattern, title, re.I):
                return {"id": item_id, "key": key, "rank": rank, "headline": headline,
                        "source": source, "discussion": f"https://news.ycombinator.com/item?id={item_id}",
                        "lines": lines}
    return None


def illustrate(path, label, headline, detail, index):
    from PIL import Image, ImageDraw, ImageFont
    import textwrap

    image = Image.new("RGB", (540, 960), "#141e2d")
    draw = ImageDraw.Draw(image)
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    accent = ("#91edca", "#f9cb82", "#bccaff", "#f0b2d2")[index % 4]
    draw.rounded_rectangle((54, 140, 486, 610), radius=34, fill="#202e42")
    draw.text((82, 185), label, font=ImageFont.truetype(font, 20), fill=accent)
    draw.multiline_text((82, 245), textwrap.fill(headline, 17), spacing=7,
                        font=ImageFont.truetype(font, 32), fill="white")
    words = textwrap.fill(detail, 31)
    draw.multiline_text((82, 425), words, spacing=7,
                        font=ImageFont.truetype(font, 20), fill="#dbe5f7")
    draw.line((82, 582, 458, 582), fill="#344862", width=4)
    draw.line((82, 582, 114 + (index % 10) * 37, 582), fill=accent, width=4)
    image.save(path)


def main():
    from generate import OUT, _youtube_upload_body, build_video

    used = set()
    for path in (OUT.parent / "history" / "production").glob("*.json"):
        record = json.loads(path.read_text())
        if record.get("format") == "trending":
            used.add(record.get("content_key"))
            if record.get("topic") and (datetime.now(timezone.utc).date()
                                        - datetime.fromisoformat(record["day"]).date()).days < 30:
                used.add("topic:" + record["topic"])
    report_path = OUT / "quality-report.json"
    preview = os.environ.get("RENDER_CHECK") == "1" and os.environ.get("EDITORIAL_TEST_LATEST") == "1"
    if preview:
        key, _, headline, source, lines = CARDS[0]
        lines = ("Your browser begins with a question.", *lines[1:])
        topic = {"id": 0, "key": key, "rank": None, "headline": headline,
                 "source": source, "discussion": None, "lines": lines}
    else:
        topic = select_topic(datetime.now(timezone.utc), used)
    if not topic:
        report_path.write_text(json.dumps({"passed": False, "state": "skipped",
                                           "reason": "No fresh reviewed trend matched"}))
        return
    labels = ("TREND SIGNAL", "THE QUESTION", "HOW IT WORKS", "WHAT TO REMEMBER")
    signal = "Render preview" if preview else f"Hacker News ranking #{topic['rank']} at selection"
    scenes = []
    for index, line in enumerate(topic["lines"]):
        illustrate(OUT / f"shot_{index}.png", labels[index], topic["headline"],
                   signal if index == 0 else line, index)
        scenes.append({"line": line, "image_prompt": ""})
    data = {"title": topic["headline"], "description":
            f"Tech explainer. Trend signal: Hacker News #{topic['rank']} at selection.\n"
            f"Discussion: {topic['discussion']}\nReference: {topic['source']}",
            "scenes": scenes, "style": "", "tags": ["technology", "explainer"]}
    build_video(data)
    report_path.write_text(json.dumps({"passed": True, **topic}, indent=2))
    if preview:
        return
    (OUT / "youtube-pending.json").write_text(json.dumps({
        "metadata": _youtube_upload_body(data), "quality_passed": True,
        "content_key": f"hn:{topic['id']}", "topic": topic["key"]}))


if __name__ == "__main__":
    main()

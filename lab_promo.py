"""Select an explicit public release and record a verified mobile demo."""
import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from zipfile import ZipFile
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from web_lab_showcase import verify_release

SOURCE_API = "https://api.github.com/repos/yusuffraht-hue/useful-web-lab-public/"
SITE = "https://yusuffraht-hue.github.io/useful-web-lab-public/"
OUT = Path("out/lab-promo")
HISTORY = Path("history/lab-promos")
LOCAL = timezone(timedelta(hours=-6))
DEMOS = {
    "screenshot-cleaner": ("", "Screenshot Cleaner", "Cover private details before sharing"),
    "signal-garden": ("signal-garden/", "Signal Garden", "Play a quick light-up puzzle"),
}


def fetch(url):
    headers = {"Cache-Control": "no-cache"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith(SOURCE_API):
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(url, headers=headers), timeout=20) as response:
        if response.url != url:
            raise ValueError("Unexpected redirect")
        data = response.read(1_000_001)
        if len(data) > 1_000_000:
            raise ValueError("Response exceeds the release-check limit")
        return data



def source_json(path):
    return json.loads(fetch(SOURCE_API + path))


def deployed_apps(commit):
    tree = source_json(f"git/trees/{commit}?recursive=1")
    if tree.get("truncated"):
        raise ValueError("Public source tree is incomplete")
    apps, demos = {}, {}
    for entry in tree["tree"]:
        match = re.fullmatch(r"apps/([a-z0-9][a-z0-9-]{0,47})/(index\.html|promo\.json)", entry["path"])
        if match and entry["type"] == "blob":
            project, name = match.groups()
            (apps if name == "index.html" else demos)[project] = entry["sha"]
    return apps, demos


def source_blob(sha):
    blob = source_json(f"git/blobs/{sha}")
    if blob.get("encoding") != "base64":
        raise ValueError("Unexpected public source encoding")
    return base64.b64decode(blob["content"])


def deployment_launches(now):
    deployments = source_json("deployments?environment=github-pages&per_page=12")
    successful = {}
    for deployment in deployments:
        statuses = source_json(f"deployments/{int(deployment['id'])}/statuses")
        success = next((status for status in statuses if status.get("state") == "success"), None)
        if success:
            deployed = datetime.fromisoformat(success["created_at"])
            successful.setdefault(deployment["sha"], deployed)
            if deployed < now - timedelta(days=7):
                break
    history = sorted(successful.items(), key=lambda item: item[1])
    previous, live, releases = {}, {}, []
    if history:
        live, _ = deployed_apps(history[-1][0])
    for index, (commit, deployed) in enumerate(history):
        apps, demos = deployed_apps(commit)
        has_baseline = index > 0 or len(deployments) < 12
        if has_baseline and now - timedelta(days=7) <= deployed <= now:
            for project in sorted(apps.keys() - previous.keys()):
                if apps[project] != live.get(project):
                    continue
                item = {"project": project, "kind": "launch",
                        "path": DEMOS.get(project, (f"{project}/",))[0],
                        "sha256": hashlib.sha256(source_blob(apps[project])).hexdigest(),
                        "deployed_at": deployed.isoformat()}
                if project not in DEMOS and project in demos:
                    item["demo"] = json.loads(source_blob(demos[project]))
                releases.append(item)
        previous = apps
    return {"version": 1, "releases": releases}


def release_feed(now):
    try:
        return json.loads(fetch(SITE + "shorts-releases.json"))
    except HTTPError as error:
        if error.code != 404:
            raise
        return deployment_launches(now)


def select(feed, records, day, now):
    if feed.get("version") != 1 or not isinstance(feed.get("releases"), list):
        raise ValueError("Unsupported release feed")
    if any(item.get("attempt_day") == day for item in records.values()):
        return None, ["Daily promo upload already reserved"]
    candidates, reasons = [], []
    for item in feed["releases"]:
        if not isinstance(item, dict):
            reasons.append("Invalid release entry")
            continue
        app, sha = item.get("project"), item.get("sha256")
        if item.get("kind") not in {"launch", "feature"}:
            continue
        try:
            release_demo(item)
        except ValueError as error:
            reasons.append(str(error))
            continue
        if not isinstance(sha, str) or not re.fullmatch("[0-9a-f]{64}", sha):
            reasons.append("Invalid path or checksum")
            continue
        try:
            published = datetime.fromisoformat(item["deployed_at"])
            if published.utcoffset() is None:
                raise ValueError("Missing timezone")
        except (KeyError, ValueError, TypeError):
            reasons.append("Invalid deployment timestamp")
            continue
        if not now - timedelta(days=7) <= published <= now:
            continue
        key = f"{app}-{sha}"
        if key not in records and not (
            item["kind"] == "launch" and any(
                record.get("project") == app for record in records.values()
            )
        ):
            candidates.append((published, key, item))
    return (max(candidates, key=lambda entry: (entry[0], entry[1]))[2] if candidates else None), reasons


def release_demo(item):
    app, path = item.get("project"), item.get("path")
    if not isinstance(app, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,47}", app):
        raise ValueError("Invalid public project ID")
    if app in DEMOS:
        if path != DEMOS[app][0]:
            raise ValueError("Unexpected app path")
        return (*DEMOS[app], None)
    if path != f"{app}/":
        raise ValueError("Unexpected app path")
    demo = item.get("demo")
    if not isinstance(demo, dict):
        raise ValueError("New project has no public sample demo")
    title, value, action = (demo.get(key) for key in ("title", "value", "action"))
    expected, buttons = demo.get("expected"), demo.get("buttons")

    def valid_text(text, limit):
        return isinstance(text, str) and 0 < len(text) <= limit and text.isprintable()
    if not all(valid_text(text, 32) for text in (title, value, action)):
        raise ValueError("Invalid promo caption")
    if (not valid_text(expected, 120) or not isinstance(buttons, list)
            or not 1 <= len(buttons) <= 4 or not all(valid_text(label, 100) for label in buttons)):
        raise ValueError("Invalid sample demo controls or result")
    return path, title, value, demo


def live_release(app, expected=None, path=None):
    url = SITE + (DEMOS[app][0] if path is None else path)
    return verify_release(app, url, fetch, expected), url


def check_profile_destination(url):
    if url == SITE:
        return

    class SiteLinks(HTMLParser):
        def __init__(self):
            super().__init__()
            self.targets = set()

        def handle_starttag(self, tag, attrs):
            href = dict(attrs).get("href")
            if tag == "a" and href:
                self.targets.add(urljoin(SITE, href))

    links = SiteLinks()
    links.feed(fetch(SITE).decode("utf-8"))
    if url not in links.targets:
        raise ValueError("The promoted app is missing from the Useful Web Lab profile destination")


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def demo(app, url, sha, chromium=None, sample=None):
    from playwright.sync_api import expect, sync_playwright

    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=chromium)
        context = browser.new_context(
            viewport={"width": 432, "height": 720}, is_mobile=True, has_touch=True,
            record_video_dir=OUT, record_video_size={"width": 432, "height": 720},
            accept_downloads=True,
        )
        # Demos run without file uploads, credentials, third-party requests or live user data.
        live_html = fetch(url)

        def route_request(route):
            request = route.request
            if request.method != "GET" or not request.url.startswith(SITE):
                route.abort()
            elif request.url == url and request.is_navigation_request():
                route.fulfill(content_type="text/html; charset=utf-8", body=live_html)
            else:
                route.continue_()

        context.route("**/*", route_request)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        response = page.goto(url, wait_until="domcontentloaded")
        if (not response or not response.ok or page.url != url
                or hashlib.sha256(response.body()).hexdigest() != sha):
            raise ValueError("Browser did not receive the verified live release")
        if page.evaluate("document.documentElement.scrollWidth") > 432:
            raise ValueError("Demo page overflows the phone viewport")
        video = page.video
        page.wait_for_timeout(2800)
        if app == "screenshot-cleaner":
            page.get_by_role("button", name="Try sample batch").click()
            page.locator("#batch").check()
            canvas = page.locator("#canvas")
            canvas.scroll_into_view_if_needed()
            box = canvas.bounding_box()
            page.wait_for_timeout(2400)
            page.mouse.move(box["x"] + box["width"] * .10, box["y"] + box["height"] * .30)
            page.mouse.down()
            page.mouse.move(box["x"] + box["width"] * .47, box["y"] + box["height"] * .57, steps=20)
            page.mouse.up()
            expect(page.get_by_role("status")).to_have_text("Cover applied to 3 of 3 screenshots.")
            page.wait_for_timeout(3500)
            with page.expect_download() as saved:
                page.get_by_role("button", name="Download batch ZIP").click()
            if saved.value.suggested_filename != "cleaned-screenshots.zip":
                raise ValueError("Sample export did not produce the expected archive")
            with ZipFile(saved.value.path()) as batch:
                exports = batch.namelist()
                if len(exports) != 3 or len(set(exports)) != 3 or any(
                    not name.endswith(".png") or not batch.read(name).startswith(b"\x89PNG\r\n\x1a\n")
                    for name in exports
                ):
                    raise ValueError("The sample archive did not contain three PNG exports")
        elif app == "signal-garden":
            for tile in (1, 7, 14):
                page.get_by_role("button", name=f"Tile {tile}", exact=True).click()
                page.wait_for_timeout(1100)
            expect(page.get_by_role("status")).to_have_text("Garden lit in 3 moves!")
        else:
            result = page.get_by_text(sample["expected"], exact=True)
            if result.is_visible():
                raise ValueError("Demo result was visible before the featured action")
            for label in sample["buttons"]:
                page.get_by_role("button", name=label, exact=True).click(timeout=4000)
                page.wait_for_timeout(900)
            expect(result).to_be_visible(timeout=4000)
        page.wait_for_timeout(6500)
        context.close()
        raw = video.path()
        browser.close()
    if errors:
        raise ValueError("Live app raised a browser error")
    return raw


def render(app, raw, details=None):
    from PIL import ImageFont
    from generate import local_voice

    _, title, value, sample = details or (*DEMOS[app], None)
    actions = {"screenshot-cleaner": "Try the sample batch\nCover details, then export",
               "signal-garden": "Tap the numbered tiles\nLight the whole garden"}
    action = f"Try the sample\n{sample['action']}" if sample else actions[app]
    captions = ((0, 5, f"{title}\n{value}"), (5, 17, action),
                (17, 25, "Try it free\nUseful Web Lab • channel profile"))
    overlays = ["fps=30", "scale=444:740", "pad=540:960:48:144:0x151924",
                "tpad=stop_mode=clone:stop_duration=25"]
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font = ImageFont.truetype(font_path, 24)
    for i, (start, end, caption) in enumerate(captions):
        if max(font.getlength(line) for line in caption.splitlines()) > 500:
            raise ValueError("Promo caption does not fit the phone frame")
        label = OUT / f"caption-{i}.txt"
        label.write_text(caption)
        overlays.append(
            f"drawtext=fontfile={font_path}:expansion=none:"
            f"textfile={label}:fontsize=24:fontcolor=white:x=(w-tw)/2:y=66:line_spacing=9:"
            f"enable='between(t,{start},{end})'"
        )
    final = OUT / "final.mp4"
    audio = OUT / "showcase.mp3"
    local_voice(f"{title}. {value}. {action.replace(chr(10), '. ')}. Try it at Useful Web Lab.", audio)
    run("ffmpeg", "-loglevel", "error", "-y", "-filter_threads", "2", "-i", str(raw), "-i", str(audio),
        "-vf", ",".join(overlays), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11,apad",
        "-t", "24", "-c:a", "aac", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(final))
    probe = json.loads(run("ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(final)))
    stream = probe["streams"][0]
    if (stream["width"], stream["height"]) != (540, 960) or not 23 <= float(probe["format"]["duration"]) <= 25:
        raise ValueError("Rendered Short failed the mobile size or duration check")
    run("ffmpeg", "-v", "error", "-xerror", "-i", str(final), "-f", "null", "-")
    return final


def main():
    from playwright.sync_api import Error as BrowserError

    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", choices=DEMOS)
    parser.add_argument("--chromium", default=os.environ.get("SHORTS_CHROMIUM"))
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for output_name in ("report.json", "final.mp4"):
        (OUT / output_name).unlink(missing_ok=True)
    now = datetime.now(timezone.utc)
    day = now.astimezone(LOCAL).date().isoformat()
    records = {p.stem: json.loads(p.read_text()) for p in HISTORY.glob("*.json")}
    for path in Path("history/production").glob("*.json"):
        record = json.loads(path.read_text())
        if record.get("format") == "showcase":
            records[record["content_key"]] = {**record, "attempt_day": record["day"]}
    if args.sample:
        app, item = args.sample, None
    else:
        feed = release_feed(now)
        skipped = []
        while True:
            item, reasons = select(feed, records, day, now)
            if not item:
                report = {"state": "skipped", "reasons": skipped + reasons or ["No new eligible release"]}
                (OUT / "report.json").write_text(json.dumps(report))
                return
            app = item["project"]
            path = release_demo(item)[0]
            try:
                _, url = live_release(app, item["sha256"], path)
                check_profile_destination(url)
                details = release_demo(item)
                raw = demo(app, url, item["sha256"], args.chromium, details[3])
                render(app, raw, details)
                live_release(app, item["sha256"], path)
            except (OSError, ValueError, BrowserError, subprocess.CalledProcessError) as error:
                (OUT / "final.mp4").unlink(missing_ok=True)
                skipped.append(f"{app}: {error}")
                feed = {**feed, "releases": [entry for entry in feed["releases"] if entry is not item]}
                continue
            break
    details = release_demo(item) if item else (*DEMOS[app], None)
    path, title, value, sample = details
    sha, url = live_release(app, item["sha256"] if item else None, path)
    check_profile_destination(url)
    if args.sample:
        render(app, demo(app, url, sha, args.chromium, sample), details)
        live_release(app, sha, path)
    details = {"state": "verified", "sample": bool(args.sample), "project": app,
               "sha256": sha, "url": url, "attempt_day": day,
               "title": f"{title}: {value} #Shorts", "value": value, "path": path}
    (OUT / "report.json").write_text(json.dumps(details, indent=2))


if __name__ == "__main__":
    main()

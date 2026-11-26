"""Select an explicit public release and record a verified mobile demo."""
import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

SITE = "https://yusuffraht-hue.github.io/useful-web-lab-public/"
OUT = Path("out/lab-promo")
HISTORY = Path("history/lab-promos")
LOCAL = timezone(timedelta(hours=-6))
DEMOS = {
    "screenshot-cleaner": ("", "Screenshot Cleaner", "Cover private details before sharing"),
    "signal-garden": ("signal-garden/", "Signal Garden", "Play a quick light-up puzzle"),
}


def fetch(url):
    with urlopen(Request(url, headers={"Cache-Control": "no-cache"}), timeout=20) as response:
        if response.url != url:
            raise ValueError("Unexpected redirect")
        data = response.read(1_000_001)
        if len(data) > 1_000_000:
            raise ValueError("Response exceeds the release-check limit")
        return data


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
        if not isinstance(app, str) or app not in DEMOS:
            reasons.append("Release has no reviewed demo")
            continue
        path = DEMOS[app][0]
        if item.get("path") != path or not isinstance(sha, str) or not re.fullmatch("[0-9a-f]{64}", sha):
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
        if key not in records:
            candidates.append((published, key, item))
    return (max(candidates, key=lambda entry: (entry[0], entry[1]))[2] if candidates else None), reasons


def live_release(app, expected=None):
    url = SITE + DEMOS[app][0]
    manifest = json.loads(fetch(url + "release.json"))
    sha = hashlib.sha256(fetch(url)).hexdigest()
    if manifest.get("app") != app or manifest.get("sha256") != sha or (expected and expected != sha):
        raise ValueError("Live app does not match the selected release")
    return sha, url


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


def demo(app, url, sha, chromium=None):
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
        else:
            for tile in (1, 7, 14):
                page.get_by_role("button", name=f"Tile {tile}", exact=True).click()
                page.wait_for_timeout(1100)
            expect(page.get_by_role("status")).to_have_text("Garden lit in 3 moves!")
        page.wait_for_timeout(6500)
        context.close()
        raw = video.path()
        browser.close()
    if errors:
        raise ValueError("Live app raised a browser error")
    return raw


def render(app, raw):
    _, title, value = DEMOS[app]
    action = ("Try the sample batch\nCover details, then export" if app == "screenshot-cleaner"
              else "Tap the numbered tiles\nLight the whole garden")
    captions = ((0, 5, f"{title}\n{value}"), (5, 17, action),
                (17, 25, "Try it free\nUseful Web Lab • channel profile"))
    overlays = ["fps=30", "scale=444:740", "pad=540:960:48:144:0x151924",
                "tpad=stop_mode=clone:stop_duration=25"]
    for i, (start, end, caption) in enumerate(captions):
        label = OUT / f"caption-{i}.txt"
        label.write_text(caption)
        overlays.append(
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"textfile={label}:fontsize=24:fontcolor=white:x=(w-tw)/2:y=66:line_spacing=9:"
            f"enable='between(t,{start},{end})'"
        )
    final = OUT / "final.mp4"
    run("ffmpeg", "-loglevel", "error", "-y", "-i", str(raw), "-vf", ",".join(overlays),
        "-t", "24", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(final))
    probe = json.loads(run("ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(final)))
    stream = probe["streams"][0]
    if (stream["width"], stream["height"]) != (540, 960) or not 23 <= float(probe["format"]["duration"]) <= 25:
        raise ValueError("Rendered Short failed the mobile size or duration check")
    run("ffmpeg", "-v", "error", "-xerror", "-i", str(final), "-f", "null", "-")
    return final


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", choices=DEMOS)
    parser.add_argument("--chromium")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    day = now.astimezone(LOCAL).date().isoformat()
    records = {p.stem: json.loads(p.read_text()) for p in HISTORY.glob("*.json")}
    if args.sample:
        app, item = args.sample, None
    else:
        try:
            feed = json.loads(fetch(SITE + "shorts-releases.json"))
        except HTTPError as error:
            if error.code != 404:
                raise
            (OUT / "report.json").write_text(json.dumps({"state": "skipped", "reasons": ["No public promo release feed"]}))
            return
        item, reasons = select(feed, records, day, now)
        if not item:
            (OUT / "report.json").write_text(json.dumps({"state": "skipped", "reasons": reasons or ["No new eligible release"]}))
            return
        app = item["project"]
    sha, url = live_release(app, item["sha256"] if item else None)
    check_profile_destination(url)
    render(app, demo(app, url, sha, args.chromium))
    # Reject a release that changed while the demo was recorded.
    live_release(app, sha)
    details = {"state": "verified", "sample": bool(args.sample), "project": app,
               "sha256": sha, "url": url, "attempt_day": day,
               "title": f"{DEMOS[app][1]}: {DEMOS[app][2]} #Shorts"}
    (OUT / "report.json").write_text(json.dumps(details, indent=2))


if __name__ == "__main__":
    main()

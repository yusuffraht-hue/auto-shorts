#!/usr/bin/env python3
"""Post the day's video to Instagram as a Reel through Composio (free).

Flow (Instagram's two-step publishing): create a Reel container from a public video URL, wait until
Instagram has processed it, then publish. Needs the repo secret COMPOSIO_API_KEY and an Instagram
Business/Creator account connected in Composio. Skips cleanly when the key is missing, and the repo
variable INSTAGRAM_POST=0 pauses posting. Usage: post_instagram.py VIDEO_URL STORY_TXT
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://backend.composio.dev/api/v3"
CAPTION_LIMIT = 2200


class ReelFailed(RuntimeError):
    pass


def build_caption(text, limit=CAPTION_LIMIT):
    """Keep the title (first line) and the hashtag line (last line); trim the story in between."""
    text = text.strip()
    if len(text) <= limit:
        return text
    lines = text.splitlines()
    head, tail = lines[0], lines[-1]
    body = "\n".join(lines[1:-1]).strip()
    room = limit - len(head) - len(tail) - 8
    cut = body[:max(room, 0)].rsplit(" ", 1)[0].rstrip(",;:") + "..."
    return f"{head}\n\n{cut}\n\n{tail}"


def _unwrap(response):
    data = response.get("data") or {}
    inner = data.get("data")
    return inner if isinstance(inner, dict) else data


def rest_executor(api_key, account_id, opener=urllib.request.urlopen):
    """Return execute(slug, args) that calls the Composio REST API and returns the tool's data."""
    def execute(slug, args):
        body = json.dumps({"connected_account_id": account_id, "arguments": args}).encode()
        request = urllib.request.Request(
            f"{API}/tools/execute/{slug}", data=body, method="POST",
            headers={"x-api-key": api_key, "Content-Type": "application/json"})
        try:
            with opener(request, timeout=120) as response:
                payload = json.loads(response.read().decode() or "{}")
        except urllib.error.HTTPError as exc:
            raise ReelFailed(f"{slug} failed: HTTP {exc.code} {exc.read().decode()[:200]}") from exc
        if payload.get("successful") is False or payload.get("error"):
            raise ReelFailed(f"{slug} failed: {payload.get('error')}")
        return _unwrap(payload)
    return execute


def find_account(api_key, opener=urllib.request.urlopen):
    request = urllib.request.Request(
        f"{API}/connected_accounts?toolkit_slugs=instagram&statuses=ACTIVE&limit=5",
        headers={"x-api-key": api_key})
    with opener(request, timeout=60) as response:
        items = json.loads(response.read().decode()).get("items", [])
    if not items:
        raise ReelFailed("no active Instagram connection in Composio")
    return items[0]["id"]


def post_reel(video_url, caption, execute, sleep=time.sleep, publish=True, max_polls=40):
    """Create, wait for, and (optionally) publish a Reel. Returns the media id, or None if not published."""
    info = execute("INSTAGRAM_GET_USER_INFO", {"ig_user_id": "me"})
    ig_user_id = str(info.get("id") or "me")
    container = execute("INSTAGRAM_POST_IG_USER_MEDIA", {
        "ig_user_id": ig_user_id, "media_type": "REELS", "video_url": video_url,
        "caption": caption, "share_to_feed": True})
    creation_id = container.get("id")
    if not creation_id:
        raise ReelFailed("Instagram returned no container id")
    delay = 4
    for _ in range(max_polls):
        status = execute("INSTAGRAM_GET_POST_STATUS", {"creation_id": creation_id}).get("status_code")
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            raise ReelFailed(f"Instagram could not process the video (status {status})")
        sleep(delay)
        delay = min(delay + 2, 15)
    else:
        raise ReelFailed("Instagram is still processing the video; gave up waiting")
    if not publish:
        return None
    published = execute("INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH", {"ig_user_id": ig_user_id, "creation_id": creation_id})
    return published.get("id")


def main(argv=None, env=None):
    argv = sys.argv[1:] if argv is None else argv
    env = os.environ if env is None else env
    if len(argv) < 2:
        print("usage: post_instagram.py VIDEO_URL STORY_TXT")
        return 2
    if not env.get("COMPOSIO_API_KEY"):
        print("Instagram post skipped: COMPOSIO_API_KEY is not set")
        return 0
    if env.get("INSTAGRAM_POST") == "0":
        print("Instagram post skipped: paused (INSTAGRAM_POST=0)")
        return 0
    caption = build_caption(Path(argv[1]).read_text())
    try:
        execute = rest_executor(env["COMPOSIO_API_KEY"], find_account(env["COMPOSIO_API_KEY"]))
        media_id = post_reel(argv[0], caption, execute)
    except (ReelFailed, urllib.error.URLError) as exc:
        print("Instagram post failed:", exc)
        return 1
    print("Instagram Reel published, media id:", media_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())

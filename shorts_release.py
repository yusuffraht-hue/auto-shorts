"""Route, verify and publish one scheduled Short using Git as a durable ledger."""
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from posting_schedule import ExpiredPostingSlot, recovery_slot, scheduled_slot

OUT = Path("out")
LEDGER = Path("history/production")
QUOTA = Path("history/youtube-quota.json")
FORMATS = ("world", "kingdom", "town", "power", "mystery", "analysis", "showcase", "trending")


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def git(*args):
    subprocess.run(["git", *args], check=True, timeout=60)


def persist(path, record, history=None):
    dump(path, record)
    files = [path]
    if history:
        series = "anime" if record["format"] == "analysis" else "town"
        history_path = Path(f"history/{series}.json")
        dump(history_path, history)
        files.append(history_path)
    git("add", "--", *map(str, files))
    git("commit", "-m", f"Shorts ledger: {record['state']} {path.stem}")
    # A concurrent update causes a safe failure before upload. A receipt is also kept as an artifact.
    git("push", "origin", "HEAD:main")


def quota_reset(now):
    pacific = ZoneInfo("America/Los_Angeles")
    tomorrow = now.astimezone(pacific).date() + timedelta(days=1)
    return datetime.combine(tomorrow, time.min, pacific).astimezone(timezone.utc)


def quota_active(record, now):
    return now < datetime.fromisoformat(record["resume_at"])


def save_quota_block():
    now = datetime.now(timezone.utc)
    persist(QUOTA, {"state": "quota_exhausted", "detected_at": now.isoformat(),
                    "resume_at": quota_reset(now).isoformat()})


def scheduled_block(slot):
    destination = LEDGER / f"{slot.replace(':', '-')}.json"
    paths = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", "FETCH_HEAD", "--", str(destination)],
        text=True, timeout=30).splitlines()
    if str(destination) in paths:
        return "The slot already has an upload reservation"
    return None


def verify_media(path):
    probe = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path),
    ], timeout=30))
    streams = probe["streams"]
    videos = [stream for stream in streams if stream["codec_type"] == "video"]
    if (len(videos) != 1 or videos[0]["codec_name"] != "h264"
            or videos[0]["height"] * 9 != videos[0]["width"] * 16
            or not any(stream["codec_type"] == "audio" for stream in streams)
            or not 5 <= float(probe["format"]["duration"]) <= 180):
        raise ValueError("Expected a decodable vertical Short with narration")
    subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(path), "-f", "null", "-"],
                   check=True, timeout=180)
    dump(path.with_name("media-report.json"), probe)


def authorized_recovery(slot):
    actor = os.environ.get("GITHUB_ACTOR", "")
    return (os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
            and os.environ.get("GITHUB_REF") == "refs/heads/main"
            and bool(actor) and actor == os.environ.get("GITHUB_REPOSITORY_OWNER")
            and bool(slot) and slot == os.environ.get("RECOVERY_SLOT"))


def route():
    kind = os.environ.get("REQUESTED_FORMAT")
    blocked = None
    recover = os.environ.get("RECOVERY_SLOT")
    if kind and not recover:
        slot = {"format": kind, "key": "manual"}
    else:
        stamp = os.environ["RUN_CREATED_AT"] or datetime.now(timezone.utc).isoformat()
        started = datetime.fromisoformat(stamp)
        if recover:
            if not authorized_recovery(recover):
                raise ValueError("Recovery requires the repository owner and main branch")
            slot = recovery_slot(recover, started)
            if kind != slot["format"]:
                raise ValueError("Requested format does not match the recovery slot")
        else:
            try:
                slot = scheduled_slot(os.environ["CRON"], started)
            except ExpiredPostingSlot as error:
                print(f"Skipping expired slot: {error}")
                with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
                    print("proceed=false", file=output)
                return
        blocked = scheduled_block(slot["key"])
    if blocked:
        print(blocked)
    if slot["format"] not in FORMATS:
        raise ValueError("Unknown format")
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        proceed = "false" if blocked else "true"
        print(f"format={slot['format']}\nslot={slot['key']}\nproceed={proceed}", file=output)


def render(kind):
    env = {**os.environ, "LOCAL_MEDIA_ONLY": "1", "DRY_RUN": "false", "PRIVACY": "private",
           "YOUTUBE_QUEUE_ONLY": "true"}
    module = {"trending": "trend_video.py", "showcase": "lab_promo.py"}.get(kind, "generate.py")
    if module == "generate.py":
        env.update(SERIES="anime" if kind == "analysis" else "town", ORIGINAL_FORMAT=kind,
                   USE_BLENDER="1", EDITORIAL_RESERVE_ONLY="1")
    subprocess.run([sys.executable, "-u", module], check=True, env=env, timeout=3000)
    if kind == "showcase":
        from lab_promo import OUT as lab_out
        from shutil import copyfile

        lab = json.loads((lab_out / "report.json").read_text())
        if lab["state"] != "verified" or lab.get("sample"):
            dump(OUT / "quality-report.json", {"passed": False, **lab})
            return
        copyfile(lab_out / "final.mp4", OUT / "final.mp4")
        dump(OUT / "quality-report.json", {"passed": True, **lab})
        dump(OUT / "youtube-pending.json", {
            "quality_passed": True, "content_key": f"{lab['project']}-{lab['sha256']}",
            "project": lab["project"], "metadata": {
                "snippet": {"title": lab["title"], "categoryId": "24",
                            "description": f"{lab['value']}. Try the free app at {lab['url']}"},
                "status": {"privacyStatus": "private", "containsSyntheticMedia": True,
                           "selfDeclaredMadeForKids": False},
            },
        })
    report = json.loads((OUT / "quality-report.json").read_text())
    if report.get("passed") is True:
        verify_media(OUT / "final.mp4")


def identity(manifest):
    if manifest.get("content_key"):
        return manifest["content_key"]
    snippet = manifest["metadata"]["snippet"]
    normalized = re.sub(r"[^a-z0-9]+", " ", snippet["title"].lower()).strip()
    return "title:" + hashlib.sha256(normalized.encode()).hexdigest()


def already_reserved(kind, slot, key, manifest, records):
    return any(
        record["slot"] == slot or record.get("content_key") == key
        or (kind == "showcase" and record.get("project") == manifest["project"])
        for record in records
    )


def publish(kind, slot):
    from post_youtube import YouTubeQuotaExceeded, publisher_from_env

    mode = os.environ["PUBLISH_MODE"]
    if mode not in ("canary", "public") or os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
        raise RuntimeError("Publishing requires an authorized first attempt")
    if mode == "public" and (
        kind not in FORMATS or not re.fullmatch(r"\d{4}-\d{2}-\d{2}:" + kind, slot)
        or (os.environ.get("GITHUB_EVENT_NAME") != "schedule" and not authorized_recovery(slot))
        or os.environ.get("GITHUB_REF") != "refs/heads/main"
        or os.environ.get("SHORTS_PUBLIC_VERIFIED") != "true"
        or os.environ.get("COMPOSIO_ZERO_COST_CONFIRMED") != "true"
    ):
        raise RuntimeError("Public mode requires a verified scheduled or recovery run on main")
    manifest_path = OUT / "youtube-pending.json"
    report = json.loads((OUT / "quality-report.json").read_text())
    if report.get("passed") is not True or not manifest_path.exists():
        print("Skipped by quality or eligibility checks")
        return
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("quality_passed") is not True:
        raise ValueError("Missing editorial approval")
    if kind == "showcase" and mode == "public":
        from lab_promo import check_profile_destination, live_release
        _, current = live_release(report["project"], report["sha256"], report["path"])
        if current != report["url"] or os.environ.get("LAB_PROMO_PROFILE_LINK_VERIFIED") != "true":
            raise ValueError("The current release or channel profile link is unverified")
        check_profile_destination(current)
    video = OUT / "final.mp4"
    verify_media(video)
    key = identity(manifest)
    destination = LEDGER / f"{slot.replace(':', '-')}.json"
    record = {"slot": slot, "day": slot.split(":")[0], "format": kind, "content_key": key,
              "run_id": os.environ["GITHUB_RUN_ID"], "state": "reserved"}
    for field in ("project", "topic"):
        if field in manifest:
            record[field] = manifest[field]

    if mode == "public":
        git("fetch", "origin", "main")
        git("merge", "--ff-only", "origin/main")
        if QUOTA.exists() and quota_active(json.loads(QUOTA.read_text()), datetime.now(timezone.utc)):
            print("YouTube quota is paused until its daily reset")
            return
        records = [json.loads(path.read_text()) for path in LEDGER.glob("*.json")]
        if already_reserved(kind, slot, key, manifest, records):
            print("Slot or content already reserved")
            return
        # A missing or unsafe attempt is isolated to its slot and content key.
        local_now = datetime.now(timezone(timedelta(hours=-6)))
        if local_now.date().isoformat() != record["day"]:
            raise RuntimeError("The original Calgary posting day has ended")

    receipt = OUT / "youtube-receipt.json"
    publisher = publisher_from_env()
    try:
        publisher.preflight()
    except YouTubeQuotaExceeded as error:
        dump(receipt, {"state": "quota_exhausted", "reason": str(error)})
        if mode == "public":
            save_quota_block()
        raise
    except RuntimeError as error:
        dump(receipt, {"state": "preflight_blocked", "reason": str(error)})
        raise

    if mode == "public":
        persist(destination, record)
    metadata = manifest["metadata"]
    metadata["status"]["privacyStatus"] = "public" if mode == "public" else "private"
    metadata["snippet"]["description"] += f"\n\nAuto Shorts release: {slot}/{key}"
    try:
        publisher.publish(video, metadata, receipt)
    except YouTubeQuotaExceeded:
        if mode == "public":
            save_quota_block()
        raise
    finally:
        if mode == "public":
            actual = json.loads(receipt.read_text()) if receipt.exists() else {}
            published = actual.get("state") == "verified" and actual.get("privacyStatus") == "public"
            state = {**record, "state": "published" if published else "needs_reconciliation"}
            if actual.get("video_id"):
                state["video_id"] = actual["video_id"]
            persist(destination, state, manifest.get("history") if published else None)


if __name__ == "__main__":
    command, *args = sys.argv[1:]
    {"route": route, "render": render, "publish": publish}[command](*args)

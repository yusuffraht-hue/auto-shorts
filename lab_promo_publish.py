"""Reserve a promo durably before uploading and reconcile ambiguous submissions."""
import json
import os
import subprocess
from datetime import datetime

from lab_promo import HISTORY, LOCAL, OUT, check_profile_destination, live_release


def save(path, state):
    HISTORY.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n")
    subprocess.run(["git", "add", "--", str(path)], check=True)
    subprocess.run(["git", "commit", "-m", f"Record Lab promo {state['state']}"], check=True)
    subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=True)
    subprocess.run(["git", "push", "origin", "HEAD:main"], check=True)


def recent_uploads(publisher):
    response = publisher._proxy("channels", "GET", {"part": "contentDetails", "mine": "true"})
    playlist = response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    page = publisher._proxy("playlistItems", "GET", {"part": "contentDetails", "playlistId": playlist, "maxResults": "50"})
    ids = [item["contentDetails"]["videoId"] for item in page.get("items", [])]
    if not ids:
        return []
    return publisher._proxy("videos", "GET", {"part": "snippet,status", "id": ",".join(ids)}).get("items", [])


def reconcile(publisher, pending):
    videos = recent_uploads(publisher)
    for path, record in pending:
        marker = "Lab release: " + path.stem
        matches = [video for video in videos if marker in video["snippet"].get("description", "").splitlines()]
        if len(matches) == 1 and matches[0]["status"].get("privacyStatus") == "public":
            save(path, {**record, "state": "public", "public_video_id": matches[0]["id"]})
        else:
            # No blind retry, including a submission found private or missing from the recent list.
            print(f"Pending promo {path.stem} requires reconciliation before another attempt.")


def main():
    if os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
        raise SystemExit("Reruns cannot upload promos")
    report_path = OUT / "report.json"
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    can_post = report.get("state") == "verified" and report.get("sample") is False
    records = {path: json.loads(path.read_text()) for path in HISTORY.glob("*.json")}
    pending = [(path, record) for path, record in records.items() if record["state"] == "reserved"]
    if not pending and not can_post:
        return
    from post_youtube import publisher_from_env

    publisher = publisher_from_env()
    publisher.preflight()
    if pending:
        reconcile(publisher, pending)
    if not can_post:
        return
    app, sha = report["project"], report["sha256"]
    _, url = live_release(app, sha, report["path"])
    if url != report["url"]:
        raise ValueError("Promotion URL differs from the verified site")
    check_profile_destination(url)
    day = datetime.now(LOCAL).date().isoformat()
    records = [json.loads(path.read_text()) for path in HISTORY.glob("*.json")]
    key = f"{app}-{sha}"
    reservation = HISTORY / f"{key}.json"
    if reservation.exists() or any(item["attempt_day"] == day for item in records):
        print("Already reserved this release or today’s promo")
        return
    state = {"state": "reserved", "project": app, "sha256": sha, "attempt_day": day}
    save(reservation, state)
    metadata = {
        "snippet": {
            "title": report["title"][:100],
            "description": f"{report['value']}. Visit Useful Web Lab from the channel profile.\n{url}\n\nLab release: {key}",
            "categoryId": "24",
        },
        "status": {"privacyStatus": "public", "containsSyntheticMedia": True,
                   "selfDeclaredMadeForKids": False},
    }
    receipt = OUT / "youtube-receipt.json"
    publisher.publish(OUT / "final.mp4", metadata, receipt)
    result = json.loads(receipt.read_text())
    if result.get("state") != "verified" or result.get("privacyStatus") != "public":
        raise ValueError("Public publication was not confirmed")
    save(reservation, {**state, "state": "public", "public_video_id": result["video_id"]})


if __name__ == "__main__":
    main()

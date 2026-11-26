"""Report missed and failed production runs without triggering a retry."""
import json
import os
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from posting_schedule import scheduled_slot

CALGARY = timezone(timedelta(hours=-6))


def daily_report(day, expected, total, runs):
    lines = [
        f"## Auto Shorts health — {day.isoformat()}",
        f"{total} of {expected} scheduled runs started.",
    ]
    if total != expected:
        lines.append("The number of runs differs from the scheduled slots.")
    unsuccessful = [run for run in runs if run["conclusion"] != "success"]
    for run in unsuccessful:
        result = run["conclusion"] or run["status"]
        lines.append(f"- [Run {run['id']}]({run['html_url']}) — {result}")
    if unsuccessful or total != expected:
        lines.append("Check the publishing receipt and YouTube Studio before any retry.")
    else:
        lines.append("All scheduled runs reported success.")
    return "\n".join(lines), total == expected and not unsuccessful


def one_run_per_slot(day, runs):
    per_slot = {}
    for run in runs:
        if not run["display_title"].startswith("Short "):
            continue
        cron = run["display_title"].removeprefix("Short ")
        try:
            slot = scheduled_slot(cron, datetime.fromisoformat(run["created_at"]))
        except ValueError:
            continue
        if not slot["key"].startswith(day.isoformat() + ":"):
            continue
        old = per_slot.get(slot["key"])
        if old is None or (old["conclusion"] != "success" and run["conclusion"] == "success"):
            per_slot[slot["key"]] = run
    return per_slot


def main():
    day = datetime.now(CALGARY).date() - timedelta(days=1)
    start = datetime.combine(day, time.min, CALGARY).astimezone(timezone.utc)
    end = start + timedelta(days=1, hours=2) - timedelta(seconds=1)
    filters = urlencode({
        "event": "schedule",
        "branch": "main",
        "created": f"{start:%Y-%m-%dT%H:%M:%SZ}..{end:%Y-%m-%dT%H:%M:%SZ}",
        "per_page": 100,
    })
    repo = os.environ["GITHUB_REPOSITORY"]
    path = f"/repos/{repo}/actions/workflows/six-format-production.yml/runs"
    request = Request(f"{os.environ.get('GITHUB_API_URL', 'https://api.github.com')}{path}?{filters}",
                      headers={"Authorization": f"Bearer {os.environ['GH_TOKEN']}",
                               "Accept": "application/vnd.github+json"})
    with urlopen(request, timeout=20) as response:
        data = json.load(response)
    expected = len(json.loads(Path("posting_schedule.json").read_text())["slots"])
    runs = one_run_per_slot(day, data["workflow_runs"])
    report, healthy = daily_report(day, expected, len(runs), list(runs.values()))
    receipts = [json.loads(path.read_text()) for path in Path("history/production").glob(f"{day}-*.json")]
    published = sum(receipt.get("state") == "published" for receipt in receipts)
    report += f"\n\n{published} public uploads verified in the ledger."
    if any(receipt.get("state") != "published" for receipt in receipts):
        report += "\nAn upload reservation still needs reconciliation."
        healthy = False
    quota_path = Path("history/youtube-quota.json")
    if quota_path.exists():
        quota = json.loads(quota_path.read_text())
        detected = datetime.fromisoformat(quota["detected_at"]).astimezone(CALGARY)
        if detected.date() == day:
            resume = datetime.fromisoformat(quota["resume_at"]).astimezone(CALGARY)
            report += f"\nYouTube reported a quota error. Uploads paused until {resume:%Y-%m-%d %H:%M} Calgary time."
            healthy = False
    print(report)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        Path(summary).write_text(report + "\n")
    return 0 if healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())

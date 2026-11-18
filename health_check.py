#!/usr/bin/env python3
"""Daily self-check for the shorts pipeline (runs in GitHub Actions, free).

- Checks both series ran on schedule in the last 30 hours.
- Retries a failed scheduled run once, and opens a GitHub issue so you get an email.
- Tests the YouTube login (refresh token) and opens an issue when it has expired.
Issues are not duplicated while an open one with the same title exists.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

SERIES_WORKFLOWS = {"in-this-town": "in-this-town.yml",
                    "anime-and-novel-stories": "anime-and-novel-stories.yml"}
WINDOW_HOURS = 30

LOGIN_FIX = """The YouTube login saved in the repo secret YT_REFRESH_TOKEN no longer works, so daily uploads will fail.

Common cause: the Google Cloud OAuth consent screen is still in "Testing", where tokens expire after 7 days.

Fix:
1. Google Cloud console > OAuth consent screen (or Audience) > click **Publish app**.
2. Open developers.google.com/oauthplayground, use your own OAuth credentials, authorize
   https://www.googleapis.com/auth/youtube.upload with your channel account, exchange the code.
3. Copy the new refresh token into the repo secret YT_REFRESH_TOKEN."""


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def evaluate_runs(runs, now=None):
    """runs: GitHub workflow-run dicts. Returns a list of actions (retry / issue)."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=WINDOW_HOURS)
    runs = sorted(runs, key=lambda r: r["created_at"], reverse=True)
    actions = []
    for name, workflow in SERIES_WORKFLOWS.items():
        mine = [r for r in runs if r["name"] == name]
        scheduled = [r for r in mine if r["event"] == "schedule" and parse_time(r["created_at"]) >= cutoff]
        if not scheduled:
            actions.append({"type": "issue", "title": f"{name}: no scheduled run in the last {WINDOW_HOURS}h",
                            "body": "GitHub did not start the daily run. Check that Actions are enabled and the schedule exists."})
            continue
        latest = scheduled[0]
        if latest["status"] != "completed" or latest["conclusion"] == "success":
            continue
        started = parse_time(latest["created_at"])
        retried = any(r["event"] == "workflow_dispatch" and parse_time(r["created_at"]) > started for r in mine)
        if not retried:
            actions.append({"type": "retry", "workflow": workflow, "name": name})
        actions.append({"type": "issue", "title": f"{name}: scheduled run failed ({latest['conclusion']})",
                        "body": f"Run: {latest['html_url']}\nAutomatic retry: {'already tried' if retried else 'started now'}."})
    return actions


def check_youtube_login(env, opener=urllib.request.urlopen):
    keys = ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")
    if not all(env.get(k) for k in keys):
        return None
    data = urllib.parse.urlencode({"client_id": env["YT_CLIENT_ID"], "client_secret": env["YT_CLIENT_SECRET"],
                                   "refresh_token": env["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"}).encode()
    try:
        with opener(urllib.request.Request("https://oauth2.googleapis.com/token", data=data), timeout=30) as response:
            json.loads(response.read().decode() or "{}")
        return None
    except urllib.error.HTTPError as exc:
        if "invalid_grant" in exc.read().decode()[:300]:
            return {"type": "issue", "title": "YouTube login expired: uploads will fail", "body": LOGIN_FIX}
        return None
    except (urllib.error.URLError, TimeoutError):
        return None


def github(method, path, token, body=None):
    request = urllib.request.Request(
        "https://api.github.com" + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        text = response.read().decode()
    return json.loads(text) if text else {}


def main(env=None):
    env = os.environ if env is None else env
    token, repo = env.get("GITHUB_TOKEN"), env.get("GITHUB_REPOSITORY")
    if not token or not repo:
        print("GITHUB_TOKEN / GITHUB_REPOSITORY missing: nothing to check")
        return 0
    runs = github("GET", f"/repos/{repo}/actions/runs?per_page=60", token).get("workflow_runs", [])
    actions = evaluate_runs(runs)
    login = check_youtube_login(env)
    if login:
        actions.append(login)
    if not actions:
        print("health ok: both series ran on schedule, YouTube login works")
        return 0
    open_titles = {i["title"] for i in github("GET", f"/repos/{repo}/issues?state=open&per_page=100", token)
                   if "pull_request" not in i}
    for action in actions:
        if action["type"] == "retry":
            github("POST", f"/repos/{repo}/actions/workflows/{action['workflow']}/dispatches", token, {"ref": "main"})
            print("retry started:", action["name"])
        elif action["title"] in open_titles:
            print("issue already open:", action["title"])
        else:
            github("POST", f"/repos/{repo}/issues", token, {"title": action["title"], "body": action["body"]})
            print("issue opened:", action["title"])
    return 0


if __name__ == "__main__":
    sys.exit(main())

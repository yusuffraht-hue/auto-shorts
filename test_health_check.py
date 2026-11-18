import json
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone

import health_check as hc

NOW = datetime(2026, 11, 18, 20, 0, tzinfo=timezone.utc)


def run(name, event, hours_ago, conclusion="success", status="completed", url="https://x/run/1"):
    created = (NOW - timedelta(hours=hours_ago)).isoformat().replace("+00:00", "Z")
    return {"name": name, "event": event, "created_at": created, "status": status,
            "conclusion": conclusion, "html_url": url}


GOOD = [run("in-this-town", "schedule", 4), run("anime-and-novel-stories", "schedule", 4)]


class EvaluateRunsTests(unittest.TestCase):
    def test_healthy_runs_need_no_action(self):
        self.assertEqual(hc.evaluate_runs(GOOD, NOW), [])

    def test_missing_scheduled_run_opens_issue(self):
        runs = [run("anime-and-novel-stories", "schedule", 4)]
        actions = hc.evaluate_runs(runs, NOW)
        self.assertEqual([a["type"] for a in actions], ["issue"])
        self.assertIn("in-this-town", actions[0]["title"])

    def test_old_scheduled_run_counts_as_missing(self):
        runs = [run("in-this-town", "schedule", 40), run("anime-and-novel-stories", "schedule", 4)]
        self.assertEqual(len(hc.evaluate_runs(runs, NOW)), 1)

    def test_failed_run_is_retried_once_and_reported(self):
        runs = [run("in-this-town", "schedule", 4, conclusion="failure"), GOOD[1]]
        actions = hc.evaluate_runs(runs, NOW)
        self.assertEqual([a["type"] for a in actions], ["retry", "issue"])
        self.assertEqual(actions[0]["workflow"], "in-this-town.yml")

    def test_failed_run_is_not_retried_twice(self):
        runs = [run("in-this-town", "workflow_dispatch", 2),
                run("in-this-town", "schedule", 4, conclusion="failure"), GOOD[1]]
        actions = hc.evaluate_runs(runs, NOW)
        self.assertEqual([a["type"] for a in actions], ["issue"])

    def test_run_still_going_is_left_alone(self):
        runs = [run("in-this-town", "schedule", 1, conclusion=None, status="in_progress"), GOOD[1]]
        self.assertEqual(hc.evaluate_runs(runs, NOW), [])


class FakeResponse:
    def __init__(self, body=b"{}"):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


ENV = {"YT_CLIENT_ID": "a", "YT_CLIENT_SECRET": "b", "YT_REFRESH_TOKEN": "c"}


class LoginTests(unittest.TestCase):
    def test_not_configured_is_skipped(self):
        self.assertIsNone(hc.check_youtube_login({}))

    def test_working_token_is_fine(self):
        self.assertIsNone(hc.check_youtube_login(ENV, opener=lambda r, timeout=0: FakeResponse(b'{"access_token":"x"}')))

    def test_expired_token_opens_issue_with_fix_steps(self):
        def opener(request, timeout=0):
            raise urllib.error.HTTPError("u", 400, "bad", {}, __import__("io").BytesIO(b'{"error":"invalid_grant"}'))
        issue = hc.check_youtube_login(ENV, opener=opener)
        self.assertEqual(issue["type"], "issue")
        self.assertIn("YouTube login expired", issue["title"])
        self.assertIn("Publish app", issue["body"])

    def test_network_error_is_not_an_alarm(self):
        def opener(request, timeout=0):
            raise urllib.error.URLError("offline")
        self.assertIsNone(hc.check_youtube_login(ENV, opener=opener))


if __name__ == "__main__":
    unittest.main()

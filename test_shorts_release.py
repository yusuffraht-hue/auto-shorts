import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime, timezone
from unittest.mock import patch

from posting_schedule import recovery_slot, scheduled_slot
from shorts_release import already_reserved, authorized_recovery, quota_active, quota_reset, route, scheduled_block
from trend_video import select_topic


class ShortsReleaseTests(unittest.TestCase):
    def test_eight_slots_and_delayed_run_use_calgary_date(self):
        expected = {14: "world", 16: "kingdom", 18: "town", 20: "power", 22: "mystery",
                    0: "analysis", 2: "showcase", 3: "trending"}
        for hour, kind in expected.items():
            with self.subTest(kind=kind):
                creation = datetime(2026, 11, 27 if hour < 6 else 26, hour, 31, tzinfo=timezone.utc)
                self.assertEqual(scheduled_slot(f"0 {hour} * * *", creation),
                                 {"format": kind, "key": f"2026-11-26:{kind}"})
        with self.assertRaisesRegex(ValueError, "too late"):
            scheduled_slot("0 3 * * *", datetime(2026, 11, 27, 8, tzinfo=timezone.utc))

    def test_dispatch_recovers_original_slot_only_in_the_due_window(self):
        key = "2026-11-26:showcase"
        now = datetime(2026, 11, 27, 2, 45, tzinfo=timezone.utc)
        self.assertEqual(recovery_slot(key, now), {"format": "showcase", "key": key})
        for invalid, stamp in [
            ("2026-11-25:showcase", now),
            ("2026-11-26:trending", now),
            (key, datetime(2026, 11, 27, 4, tzinfo=timezone.utc)),
            ("2026-11-26:unknown", now),
        ]:
            with self.subTest(slot=invalid, time=stamp), self.assertRaises(ValueError):
                recovery_slot(invalid, stamp)

    def test_dispatch_requires_owner_main_and_exact_slot(self):
        key = "2026-11-26:power"
        context = {"GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF": "refs/heads/main",
                   "GITHUB_ACTOR": "owner", "GITHUB_REPOSITORY_OWNER": "owner", "RECOVERY_SLOT": key}
        with patch.dict("os.environ", context, clear=True):
            self.assertTrue(authorized_recovery(key))
            self.assertFalse(authorized_recovery("2026-11-26:town"))
        for changes in [{"GITHUB_ACTOR": "other"}, {"GITHUB_REF": "refs/heads/topic"},
                        {"RECOVERY_SLOT": ""}]:
            with self.subTest(changes=changes), patch.dict("os.environ", {**context, **changes}, clear=True):
                self.assertFalse(authorized_recovery(key))

    def test_backup_retains_the_primary_slot_and_cutoff(self):
        creation = datetime(2026, 11, 27, 2, 25, tzinfo=timezone.utc)
        self.assertEqual(scheduled_slot("19 2 * * *", creation), scheduled_slot("0 2 * * *", creation))
        with self.assertRaisesRegex(ValueError, "too late"):
            scheduled_slot("19 2 * * *", datetime(2026, 11, 27, 4, tzinfo=timezone.utc))

    def test_backup_stops_before_render_when_slot_has_reservation(self):
        with patch("shorts_release.subprocess.check_output",
                   return_value="history/production/2026-11-26-world.json\n") as git_read:
            result = scheduled_block("2026-11-26:world")
        self.assertIn("reservation", result)
        git_read.assert_called_once()

    def test_scheduled_run_renders_during_a_quota_pause(self):
        with TemporaryDirectory() as folder:
            output = Path(folder) / "output"
            env = {"CRON": "0 22 * * *", "RUN_CREATED_AT": "2026-11-26T22:05:00+00:00",
                   "GITHUB_OUTPUT": str(output)}
            with patch.dict("os.environ", env, clear=True), patch(
                "shorts_release.subprocess.check_output", return_value=""
            ) as git_read:
                route()
            self.assertIn("proceed=true", output.read_text())
            self.assertNotIn("history/youtube-quota.json", git_read.call_args.args[0])

    def test_expired_scheduled_run_skips_without_reading_the_ledger(self):
        with TemporaryDirectory() as folder:
            output = Path(folder) / "output"
            env = {"CRON": "0 14 * * *", "RUN_CREATED_AT": "2026-11-26T22:39:10+00:00",
                   "GITHUB_OUTPUT": str(output)}
            with patch.dict("os.environ", env, clear=True), patch(
                "shorts_release.scheduled_block"
            ) as check_slot:
                route()
            self.assertEqual(output.read_text(), "proceed=false\n")
            check_slot.assert_not_called()

    def test_quota_pause_ends_at_pacific_midnight_in_both_seasons(self):
        for month, reset_hour in [(7, 7), (11, 8)]:
            now = datetime(2026, month, 26, 20, tzinfo=timezone.utc)
            reset = quota_reset(now)
            record = {"resume_at": reset.isoformat()}
            self.assertEqual(reset, datetime(2026, month, 27, reset_hour, tzinfo=timezone.utc))
            self.assertTrue(quota_active(record, now))
            self.assertFalse(quota_active(record, reset))

    def test_ambiguous_attempt_blocks_same_slot_and_same_project(self):
        record = {"slot": "2026-11-25:showcase", "content_key": "app-a",
                  "project": "sample-app", "state": "needs_reconciliation"}
        self.assertTrue(already_reserved("showcase", "2026-11-26:showcase", "app-b",
                                         {"project": "sample-app"}, [record]))
        self.assertTrue(already_reserved("showcase", record["slot"], "other",
                                         {"project": "different-app"}, [record]))
        self.assertFalse(already_reserved("showcase", "2026-11-26:showcase", "other",
                                          {"project": "different-app"}, [record]))

    def test_trend_selection_uses_rank_and_excludes_sensitive_stale_and_reused(self):
        now = datetime(2026, 11, 26, tzinfo=timezone.utc)
        entries = {"topstories.json": [1, 2, 3, 4, 5]}
        for number, title in enumerate(("Browser attack", "Old browser",
                                         "A database engine", "Linux compilation",
                                         "Modern browser"), 1):
            entries[f"item/{number}.json"] = {
                "id": number, "title": title, "type": "story", "score": 50,
                "time": now.timestamp() - (259200 if number == 2 else 100)}
        result = select_topic(now, {"hn:3", "topic:software"}, get=entries.__getitem__)
        self.assertEqual((result["id"], result["rank"], result["key"]), (5, 5, "browser"))
        self.assertIsNone(select_topic(now, {"hn:3", "topic:software", "topic:browser"},
                                       get=entries.__getitem__))

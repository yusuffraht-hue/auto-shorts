import unittest
from datetime import datetime, timezone

from posting_schedule import scheduled_slot
from shorts_release import already_reserved
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

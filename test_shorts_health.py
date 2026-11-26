from datetime import date
import unittest

from shorts_health import daily_report, one_run_per_slot


class ShortsHealthTests(unittest.TestCase):
    def test_missing_run_fails_daily_check(self):
        report, ok = daily_report(date(2026, 11, 26), 6, 5, [])
        self.assertFalse(ok)
        self.assertIn("5 of 6", report)

    def test_failed_run_is_linked(self):
        report, ok = daily_report(date(2026, 11, 26), 1, 1, [{
            "id": 42, "html_url": "https://github.com/example/repo/actions/runs/42",
            "conclusion": "failure", "status": "completed",
        }])
        self.assertFalse(ok)
        self.assertIn("runs/42", report)

    def test_successful_run_passes(self):
        _, ok = daily_report(date(2026, 11, 26), 1, 1, [{"conclusion": "success"}])
        self.assertTrue(ok)

    def test_primary_and_backup_count_as_one_slot(self):
        runs = [
            {"display_title": "Short 0 14 * * *", "created_at": "2026-11-26T14:06:00Z", "conclusion": "failure"},
            {"display_title": "Short 19 14 * * *", "created_at": "2026-11-26T14:21:00Z", "conclusion": "success"},
            {"display_title": "Short 19 0 * * *", "created_at": "2026-11-27T00:26:00Z", "conclusion": "success"},
        ]
        self.assertEqual(one_run_per_slot(date(2026, 11, 26), runs),
                         {"2026-11-26:world": runs[1], "2026-11-26:analysis": runs[2]})

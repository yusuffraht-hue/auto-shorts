from datetime import date
import unittest

from shorts_health import daily_report


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

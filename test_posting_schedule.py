import unittest
from datetime import datetime, timezone
from posting_schedule import due_slot

class ScheduleTests(unittest.TestCase):
    def test_winter(self):
        self.assertEqual(due_slot(datetime(2026,11,25,15,tzinfo=timezone.utc))["format"], "world")
    def test_summer(self):
        self.assertEqual(due_slot(datetime(2026,7,25,14,tzinfo=timezone.utc))["format"], "world")
    def test_no_slot(self):
        self.assertIsNone(due_slot(datetime(2026,11,25,15,30,tzinfo=timezone.utc)))
    def test_naive_rejected(self):
        with self.assertRaises(ValueError):
            due_slot(datetime(2026,11,25,8))

"""Offline tests for the town shot-plan contract."""
import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "town_shots.py"
spec = importlib.util.spec_from_file_location("town_shots", SCRIPT)
town_shots = importlib.util.module_from_spec(spec)
spec.loader.exec_module(town_shots)
validate_plan = town_shots.validate_plan
SHOT = {"location": "square", "character": "mira", "action": "wave", "camera": "wide", "frames": 48}


class ShotPlanTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_plan({"series": "town", "shots": [SHOT]})[0], SHOT)

    def test_reject_other_series(self):
        with self.assertRaises(ValueError):
            validate_plan({"series": "anime", "shots": [SHOT]})

    def test_reject_unknown_action(self):
        with self.assertRaises(ValueError):
            validate_plan({"series": "town", "shots": [{**SHOT, "action": "execute_python"}]})

    def test_reject_extra_fields(self):
        with self.assertRaises(ValueError):
            validate_plan({"series": "town", "shots": [{**SHOT, "command": "echo hi"}]})

    def test_reject_boolean_frames(self):
        with self.assertRaises(ValueError):
            validate_plan({"series": "town", "shots": [{**SHOT, "frames": True}]})

    def test_reject_unbounded_duration(self):
        with self.assertRaises(ValueError):
            validate_plan({"series": "town", "shots": [{**SHOT, "frames": 240}] * 8})

    def test_reject_too_many_shots(self):
        with self.assertRaises(ValueError):
            validate_plan({"series": "town", "shots": [SHOT] * 13})

    def test_reject_empty(self):
        with self.assertRaises(ValueError):
            validate_plan({"series": "town", "shots": []})


if __name__ == "__main__":
    unittest.main()

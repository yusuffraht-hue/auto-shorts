import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "trend_engine.py"
spec = importlib.util.spec_from_file_location("trend_engine", MODULE_PATH)
engine = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = engine
spec.loader.exec_module(engine)

class TrendEngineTests(unittest.TestCase):
    def test_extracts_nested_game_records(self):
        payload = {"searchResults": [{"contents": [{"universeId": 123, "name": "Example"}]}]}
        games = engine.extract_search_games(payload)
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["universe_id"], 123)

    def test_growth_scoring_prefers_rising_game(self):
        games = [
            {"universe_id": 1, "name": "Rising", "playing": 1500, "appearances": 1},
            {"universe_id": 2, "name": "Flat", "playing": 1000, "appearances": 1},
        ]
        ranked = engine.score_games(games, {1: {"playing": 1000}, 2: {"playing": 1000}}, 10)
        self.assertEqual(ranked[0]["universe_id"], 1)
        self.assertEqual(ranked[0]["growth_pct_since_previous_scan"], 50.0)

    def test_first_scan_has_no_growth_baseline(self):
        ranked = engine.score_games([{"universe_id": 1, "name": "New", "playing": 50}], {}, 10)
        self.assertIsNone(ranked[0]["growth_pct_since_previous_scan"])

    def test_concepts_are_hypotheses(self):
        ideas = engine.concept_ideas([], 3)
        self.assertEqual(len(ideas), 3)
        self.assertTrue(all("core_hook" in idea for idea in ideas))

if __name__ == "__main__":
    unittest.main()

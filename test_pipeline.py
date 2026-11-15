import json
import os
import unittest
from unittest.mock import patch

import llm
import series


class LLMValidationTests(unittest.TestCase):
    def make_payload(self, count=10):
        return {
            "title": "A Test Story",
            "description": "A short test description.",
            "tags": ["test"],
            "hero": "A blocky hero in a red jacket",
            "full_story": "A complete test story. " * 12,
            "scenes": [
                {"line": f"Scene {i} reveals something strange.", "image_prompt": f"cinematic test scene number {i}"}
                for i in range(count)
            ],
        }

    def test_accepts_exactly_ten_valid_scenes(self):
        cleaned = json.loads(llm._clean_json(json.dumps(self.make_payload())))
        self.assertEqual(len(cleaned["scenes"]), 10)

    def test_rejects_nine_scenes(self):
        with self.assertRaises(ValueError):
            llm._clean_json(json.dumps(self.make_payload(9)))

    def test_rejects_missing_image_prompt(self):
        payload = self.make_payload()
        payload["scenes"][3]["image_prompt"] = ""
        with self.assertRaises(ValueError):
            llm._clean_json(json.dumps(payload))

    def test_accepts_skip_response(self):
        self.assertEqual(json.loads(llm._clean_json('{"skip": true}')), {"skip": True})


class SeriesTests(unittest.TestCase):
    def test_town_prompt_requests_ten_scenes(self):
        meta = series.build("town", {"episodes": [], "works": {}, "log": {}})
        self.assertIn("exactly 10 scenes", meta["prompt"])

    def test_auto_anime_selection_uses_only_verified_works(self):
        hist = {"episodes": [], "works": {}, "log": {}}
        with patch.dict(os.environ, {"WORK": "auto", "FORMAT": "recap"}):
            meta = series.build("anime", hist)
        self.assertTrue(series.WORKS[meta["work"]][1])

    def test_unverified_manual_work_is_blocked(self):
        hist = {"episodes": [], "works": {}, "log": {}}
        with patch.dict(os.environ, {"WORK": "The Artist Who Paints Dungeons", "FORMAT": "recap"}):
            with self.assertRaises(RuntimeError):
                series.build("anime", hist)


if __name__ == "__main__":
    unittest.main()

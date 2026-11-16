import json
import os
import unittest
from unittest.mock import patch

import generate
import llm
import series
import shots


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
    def test_video_prompt_uses_shorter_caption_story(self):
        self.assertIn("140-180 words", series.VIDEO_RULES)
        self.assertIn('"full_story":"140-180 words', series.SPEC)
        self.assertIn("5-7 spoken words", llm.SUFFIX)
        self.assertIn("5-7 natural spoken words", series.VIDEO_RULES)
        self.assertIn("Proofread the story", series.VIDEO_RULES)

    def test_town_prompt_requests_ten_scenes(self):
        meta = series.build("town", {"episodes": [], "works": {}, "log": {}})
        self.assertIn("exactly 10 scenes", meta["prompt"])

    def test_visual_shot_list_has_ten_distinct_compositions(self):
        self.assertEqual(len(generate.SHOT_COMPOSITIONS), 10)
        self.assertEqual(len(set(generate.SHOT_COMPOSITIONS)), 10)

    def test_town_shot_planner_keeps_story_specific_locations(self):
        data = {"hero": "a red jacket", "scenes": [
            {"line": "He slips down the hidden tunnel.",
             "image_prompt": "house basement, brick stairs descending, worm's-eye view, dim lantern"},
            {"line": "Gears spin, cloaked figures whisper.",
             "image_prompt": "street cavern, glowing gears rotating, high angle, eerie teal"},
            {"line": "A lever cracks, earth shivers loudly.",
             "image_prompt": "classroom floor, lever pulled, close-up, dramatic shadows"},
            {"line": "The book names Brickby as keeper.",
             "image_prompt": "park library, massive book opened, low angle, golden dust"},
            {"line": "The hero returns outside.",
             "image_prompt": "street night, hero looking upward, dramatic tilt, neon rain"},
        ]}
        planned = shots.plan(data)
        self.assertEqual(
            [shot["setting"] for shot in planned["shots"]],
            ["underground", "underground", "underground", "library", "street"],
        )

    def test_town_prompt_requires_scene_matched_visuals(self):
        meta = series.build("town", {"episodes": [], "works": {}, "log": {}})
        self.assertIn("exact action and location", meta["prompt"])
        self.assertIn("market, underground or library", meta["prompt"])

    def test_caption_chunks_are_readable_and_timed(self):
        words = [(i * 0.4, (i + 1) * 0.4, w)
                 for i, w in enumerate(["The", "door", "opened", "by", "itself", "again"])]
        caps = generate.chunks(words, 2.5)
        self.assertEqual([c[2] for c in caps], ["The door opened", "by itself again"])
        self.assertAlmostEqual(caps[0][1], caps[1][0])

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

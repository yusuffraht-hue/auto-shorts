import json
import os
import unittest
from unittest.mock import patch

import generate
import llm
import series
import shots
import quality



class QualityGateTests(unittest.TestCase):
    def valid_story(self):
        return {
            "title": "The Door Beneath the City",
            "full_story": " ".join(["A mysterious door appeared beneath the city overnight."] * 20),
            "scenes": [
                {"line": f"The strange door opened for scene {i}.",
                 "image_prompt": f"underground stone doorway glowing softly scene number {i} wide cinematic view"}
                for i in range(1, 11)
            ],
        }

    def test_quality_gate_accepts_complete_distinct_story(self):
        report = quality.check(self.valid_story(), {"episodes": []})
        self.assertTrue(report["passed"], report["issues"])
        self.assertEqual(report["scene_count"], 10)

    def test_quality_gate_rejects_short_story(self):
        data = self.valid_story()
        data["full_story"] = "A door appeared."
        report = quality.check(data, {"episodes": []})
        self.assertFalse(report["passed"])
        self.assertTrue(any("too short" in issue for issue in report["issues"]))

    def test_quality_gate_enforces_prompt_word_count_range(self):
        for count, expected in ((139, "too short"), (181, "too long")):
            with self.subTest(count=count):
                data = self.valid_story()
                data["full_story"] = "word " * count
                report = quality.check(data, {"episodes": []})
                self.assertFalse(report["passed"])
                self.assertTrue(any(expected in issue for issue in report["issues"]))

    def test_quality_gate_rejects_repeated_scene_lines(self):
        data = self.valid_story()
        data["scenes"][1]["line"] = data["scenes"][0]["line"]
        report = quality.check(data, {"episodes": []})
        self.assertTrue(any("repeats earlier narration" in issue for issue in report["issues"]))

    def test_quality_gate_rejects_recent_duplicate_title(self):
        data = self.valid_story()
        report = quality.check(data, {"episodes": [{"title": data["title"]}]})
        self.assertTrue(any("duplicates" in issue for issue in report["issues"]))

    def test_quality_gate_rejects_near_duplicate_story(self):
        data = self.valid_story()
        previous = data["full_story"].replace("door", "gate")
        report = quality.check(data, {"recent_stories": [previous]})
        self.assertTrue(any("too similar" in issue for issue in report["issues"]))
        self.assertGreaterEqual(report["max_recent_story_similarity"], 0.72)

    def test_quality_gate_allows_distinct_story(self):
        data = self.valid_story()
        previous = " ".join(["A young pilot crossed the ocean to deliver medicine to an isolated island."] * 20)
        report = quality.check(data, {"recent_stories": [previous]})
        self.assertFalse(any("too similar" in issue for issue in report["issues"]))


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
        self.assertIn("30-40 second Short", series.VIDEO_RULES)
        self.assertNotIn("45-second video", series.VIDEO_RULES)
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

    def test_caption_font_size_shrinks_long_chunks(self):
        self.assertEqual(generate.caption_font_size("LUMEN"), 76)
        self.assertLess(generate.caption_font_size("DREAMGATE'S BROKEN KEY"), 60)
        self.assertGreaterEqual(generate.caption_font_size("DREAMGATE'S BROKEN KEY"), 24)

    def test_caption_font_size_has_a_lower_bound_for_extreme_tokens(self):
        self.assertEqual(generate.caption_font_size("W" * 100), 24)


    def test_auto_anime_selection_uses_only_verified_works(self):
        hist = {"episodes": [], "works": {}, "log": {}}
        with patch.dict(os.environ, {"WORK": "auto", "FORMAT": "auto"}):
            meta = series.build("anime", hist)
        self.assertTrue(series.WORKS[meta["work"]][1])

    def test_finish_keeps_only_eight_recent_story_texts(self):
        hist = {
            "episodes": [], "works": {}, "log": {},
            "recent_stories": [f"old story {i}" for i in range(10)],
        }
        meta = series.build("town", hist)
        data = {
            "title": "A New Door",
            "description": "A new mystery begins.",
            "full_story": "A newly written story with a unique ending.",
            "scenes": [],
            "tags": [],
        }
        with patch("humanize.polish", lambda value: None):
            series.finish(meta, data, hist)
        self.assertEqual(len(hist["recent_stories"]), 8)
        self.assertEqual(hist["recent_stories"][-1], data["full_story"])

    def test_anime_title_cleanup_removes_duplicate_work_and_format_labels(self):
        self.assertEqual(
            series._clean_title("Jujutsu Kaisen What If the Cursed Mirror Fell?", "Jujutsu Kaisen"),
            "the Cursed Mirror Fell?",
        )
        self.assertEqual(
            series._clean_title("Jujutsu Kaisen Recap: Dreamgate's Shadow", "Jujutsu Kaisen"),
            "Dreamgate's Shadow",
        )

    def test_unverified_manual_work_is_blocked(self):
        hist = {"episodes": [], "works": {}, "log": {}}
        with patch.dict(os.environ, {"WORK": "The Artist Who Paints Dungeons", "FORMAT": "recap"}):
            with self.assertRaises(RuntimeError):
                series.build("anime", hist)

    def test_auto_mode_falls_back_to_labeled_what_if_without_episode_facts(self):
        hist = {"episodes": [], "works": {}, "log": {}}
        with patch.dict(os.environ, {"WORK": "Jujutsu Kaisen", "FORMAT": "auto"}):
            meta = series.build("anime", hist)
        self.assertEqual(meta["kind"], "whatif")
        self.assertIn("Clearly label it as speculation, not canon", meta["prompt"])
        self.assertIn("what-if speculation", meta["note"])

    def test_explicit_recap_fails_closed_without_episode_specific_facts(self):
        hist = {"episodes": [], "works": {}, "log": {}}
        with patch.dict(os.environ, {"WORK": "Jujutsu Kaisen", "FORMAT": "recap"}):
            with self.assertRaisesRegex(RuntimeError, "episode-specific verified fact sheet"):
                series.build("anime", hist)

    def test_episode_fact_sheet_enables_recap_with_strict_prompt(self):
        hist = {"episodes": [], "works": {}, "log": {}}
        with patch.dict(series.RECAP_FACT_SHEETS, {
            "Jujutsu Kaisen": "Yuji swallows Sukuna's finger; Gojo explains the execution choice."
        }):
            with patch.dict(os.environ, {"WORK": "Jujutsu Kaisen", "FORMAT": "recap"}):
                meta = series.build("anime", hist)
        self.assertEqual(meta["kind"], "recap")
        self.assertIn("Verified episode-specific canon facts:", meta["prompt"])
        self.assertIn(series.RECAP_RULES, meta["prompt"])
        self.assertNotIn("Part 1 covers the premise and opening events", meta["prompt"])
        self.assertIn('{"skip":true}', meta["prompt"])

class UploadSafetyTests(unittest.TestCase):
    def test_upload_failure_does_not_retry_or_remove_synthetic_disclosure(self):
        class FakeRequest:
            def __init__(self):
                self.execute_calls = 0

            def execute(self):
                self.execute_calls += 1
                raise RuntimeError("synthetic disclosure rejected")

        class FakeVideos:
            def __init__(self):
                self.insert_calls = 0
                self.body = None
                self.request = FakeRequest()

            def insert(self, **kwargs):
                self.insert_calls += 1
                self.body = kwargs["body"]
                return self.request

        class FakeYouTube:
            def __init__(self):
                self.resource = FakeVideos()

            def videos(self):
                return self.resource

        fake = FakeYouTube()
        data = {"title": "Test story", "description": "Original story.", "tags": ["test"]}
        with self.assertRaisesRegex(RuntimeError, "synthetic disclosure rejected"):
            generate._execute_youtube_upload(
                fake, "video.mp4", data,
                lambda path, **kwargs: {"path": path, **kwargs},
            )
        self.assertEqual(fake.resource.insert_calls, 1)
        self.assertEqual(fake.resource.request.execute_calls, 1)
        self.assertTrue(fake.resource.body["status"]["containsSyntheticMedia"])
        self.assertEqual(fake.resource.body["status"]["privacyStatus"], "private")

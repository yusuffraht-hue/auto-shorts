import unittest

import humanize
import series


class ScrubTests(unittest.TestCase):
    def test_dashes_become_commas_for_the_voice(self):
        self.assertEqual(humanize.scrub("He ran \u2014 fast \u2014 home."), "He ran, fast, home.")

    def test_stock_sentences_are_removed(self):
        self.assertEqual(humanize.scrub("The door opened. Let that sink in. He stepped inside."),
                         "The door opened. He stepped inside.")

    def test_cliche_phrase_goes_but_the_fact_stays(self):
        self.assertEqual(humanize.scrub("Little did she know, the bell was a warning."), "The bell was a warning.")

    def test_sentence_starts_stay_capitalised(self):
        self.assertEqual(humanize.scrub("Mara froze. Little did she know, the bell was a warning."),
                         "Mara froze. The bell was a warning.")

    def test_never_returns_empty_text(self):
        self.assertEqual(humanize.scrub("Let that sink in."), "Let that sink in.")

    def test_deep_sounding_openers_are_dropped(self):
        self.assertEqual(humanize.scrub("At its core, the bell was a warning."), "The bell was a warning.")


class LintTests(unittest.TestCase):
    def test_flags_not_x_but_y(self):
        self.assertIn("not-x-but-y", humanize.lint("It's not just a door, it's a portal."))

    def test_flags_fragment_rows(self):
        self.assertIn("fragment-row", humanize.lint("No fear. No doubt. No mercy."))

    def test_plain_sentence_is_clean(self):
        self.assertEqual(humanize.lint("The door creaked open."), [])


class IntegrationTests(unittest.TestCase):
    def test_polish_cleans_lines_and_story_without_losing_scenes(self):
        data = {"full_story": "A bell rang \u2014 twice. Read that again.",
                "scenes": [{"line": "Mara froze \u2014 listening.", "image_prompt": "street"},
                           {"line": "The street went quiet.", "image_prompt": "street"}]}
        out = humanize.polish(data)
        self.assertEqual(len(out["scenes"]), 2)
        self.assertNotIn("\u2014", out["scenes"][0]["line"])
        self.assertNotIn("\u2014", out["full_story"])
        self.assertNotIn("Read that again", out["full_story"])

    def test_series_finish_applies_the_polish(self):
        hist = {"episodes": [], "works": {}, "log": {}}
        meta = series.build_town(hist)
        data = {"title": "Quiet Street", "description": "A bell rings.", "tags": [],
                "full_story": "The bell rang. Let that sink in. Mara ran.",
                "scenes": [{"line": "She waited \u2014 alone.", "image_prompt": "street"}] * 6}
        out = series.finish(meta, data, hist)
        self.assertNotIn("\u2014", out["scenes"][0]["line"])
        self.assertNotIn("Let that sink in", out["full_story"])

    def test_prompts_carry_the_style_rules(self):
        meta = series.build_town({"episodes": [], "works": {}, "log": {}})
        self.assertIn("not X but Y", meta["prompt"])
        self.assertIn("already introduced", meta["prompt"])


if __name__ == "__main__":
    unittest.main()

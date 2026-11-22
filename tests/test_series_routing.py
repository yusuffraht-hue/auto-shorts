"""Regression tests for strict separation of the two production series."""
import unittest
from unittest.mock import patch

import series


class SeriesRoutingTests(unittest.TestCase):
    def setUp(self):
        self.history = {"episodes": [], "works": {}, "log": {}}

    def test_town_routes_only_to_town_builder(self):
        with patch.object(series, "build_town", return_value={"series": "town"}) as town, \
             patch.object(series, "build_anime") as anime:
            self.assertEqual(series.build("town", self.history), {"series": "town"})
            town.assert_called_once_with(self.history)
            anime.assert_not_called()

    def test_anime_routes_only_to_anime_builder(self):
        with patch.object(series, "build_town") as town, \
             patch.object(series, "build_anime", return_value={"series": "anime"}) as anime:
            self.assertEqual(series.build("anime", self.history, {"Jujutsu Kaisen"}), {"series": "anime"})
            anime.assert_called_once_with(self.history, {"Jujutsu Kaisen"})
            town.assert_not_called()

    def test_invalid_series_fails_before_story_generation(self):
        for value in ("", "Town", "animes", "auto", None):
            with self.subTest(value=value), \
                 patch.object(series, "build_town") as town, \
                 patch.object(series, "build_anime") as anime:
                with self.assertRaises(ValueError):
                    series.build(value, self.history)
                town.assert_not_called()
                anime.assert_not_called()


if __name__ == "__main__":
    unittest.main()

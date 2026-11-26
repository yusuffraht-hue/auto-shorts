from datetime import datetime, timezone
import hashlib
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from lab_promo import SITE, live_release, select

NOW = datetime(2026, 11, 26, 20, tzinfo=timezone.utc)
DAY = "2026-11-26"
SHA = "a" * 64
RELEASE = {"project": "screenshot-cleaner", "sha256": SHA, "kind": "launch",
           "path": "", "deployed_at": "2026-11-26T12:00:00Z"}


class LabPromoTests(unittest.TestCase):
    def candidate(self, releases, records=None):
        return select({"version": 1, "releases": releases}, records or {}, DAY, NOW)[0]

    def test_finds_new_launch(self):
        self.assertEqual(self.candidate([RELEASE]), RELEASE)

    def test_rejects_maintenance_private_links_and_stale_releases(self):
        for invalid in [
            {**RELEASE, "kind": "maintenance"},
            {**RELEASE, "path": "https://preview.example/"},
            {**RELEASE, "deployed_at": "2026-11-05T12:00:00Z"},
        ]:
            self.assertIsNone(self.candidate([invalid]))

    def test_never_selects_an_already_reserved_release_or_second_daily_upload(self):
        self.assertIsNone(self.candidate([RELEASE], {"screenshot-cleaner-" + SHA: {"attempt_day": "2026-11-25"}}))
        self.assertIsNone(self.candidate([RELEASE], {"other": {"attempt_day": DAY}}))

    def test_checks_actual_live_bytes_and_link(self):
        html = b"<html>live</html>"
        digest = hashlib.sha256(html).hexdigest()
        manifest = json.dumps({"app": "screenshot-cleaner", "sha256": digest}).encode()
        with patch("lab_promo.fetch", side_effect=[manifest, html]) as fetch:
            self.assertEqual(live_release("screenshot-cleaner", digest), (digest, SITE))
        self.assertEqual([arg.args[0] for arg in fetch.call_args_list], [SITE + "release.json", SITE])
        with patch("lab_promo.fetch", side_effect=[manifest, b"stale HTML"]):
            with self.assertRaises(ValueError):
                live_release("screenshot-cleaner", digest)
        with patch("lab_promo.fetch", side_effect=HTTPError(SITE, 404, "Not found", {}, None)):
            with self.assertRaises(HTTPError):
                live_release("screenshot-cleaner", digest)

from datetime import datetime, timezone
import hashlib
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from lab_promo import SITE, check_profile_destination, live_release, select
from lab_promo_publish import reconcile

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

    def test_featured_app_reachable_from_public_profile_destination(self):
        url = SITE + "signal-garden/"
        with patch("lab_promo.fetch", return_value=b'<a href="signal-garden/">Play</a>'):
            check_profile_destination(url)
        with patch("lab_promo.fetch", return_value=b"<p>No app link</p>"):
            with self.assertRaises(ValueError):
                check_profile_destination(url)

    def test_timeout_reconciliation_uses_public_marker_without_uploading(self):
        path = Path("screenshot-cleaner-" + SHA + ".json")
        pending = [(path, {"state": "reserved"})]
        matching = {"id": "confirmed-id", "snippet": {"description": "Lab release: " + path.stem},
                    "status": {"privacyStatus": "public"}}
        with patch("lab_promo_publish.recent_uploads", return_value=[matching]), patch("lab_promo_publish.save") as save:
            reconcile(object(), pending)
            save.assert_called_once_with(path, {"state": "public", "public_video_id": "confirmed-id"})
        for uploads in ([], [{**matching, "status": {"privacyStatus": "private"}}]):
            with patch("lab_promo_publish.recent_uploads", return_value=uploads), patch("lab_promo_publish.save") as save:
                reconcile(object(), pending)
                save.assert_not_called()

    def test_accepts_another_public_app_with_a_sample_demo(self):
        release = {**RELEASE, "project": "timer", "path": "timer/",
                   "demo": {"title": "Timer", "value": "Start a focus session",
                            "action": "Start the timer", "buttons": ["Try sample", "Start"],
                            "expected": "Timer running"}}
        self.assertEqual(self.candidate([release]), release)
        self.assertIsNone(self.candidate([{**release, "path": "../timer/"}]))
        self.assertIsNone(self.candidate([{**release, "demo": None}]))

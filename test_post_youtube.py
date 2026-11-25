import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from post_youtube import YouTubePublisher


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.publisher = YouTubePublisher("key", "account", "expected")
        self.status = {"privacyStatus": "public", "containsSyntheticMedia": True,
                       "selfDeclaredMadeForKids": False}
        self.metadata = {"snippet": {"title": "Episode"}, "status": self.status}
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.receipt = Path(directory.name) / "receipt.json"

    @staticmethod
    def status_response(resource, method, query, body):
        return body

    def test_private_before_public_and_verifies_both(self):
        with (patch.object(self.publisher, "_stage", return_value={"s3key": "staged"}),
              patch.object(self.publisher, "_post", return_value={
                  "successful": True, "data": {"video": {"id": "video"}}}) as post,
              patch.object(self.publisher, "_proxy", side_effect=self.status_response) as proxy,
              patch.object(self.publisher, "_verify") as verify):
            self.publisher.publish(Path("episode.mp4"), self.metadata, self.receipt)
        self.assertEqual(post.call_args.args[1]["arguments"]["privacyStatus"], "private")
        private = {**self.status, "privacyStatus": "private"}
        self.assertEqual(proxy.call_args_list[0].args[-1]["status"], private)
        self.assertEqual(proxy.call_args_list[1].args[-1]["status"], self.status)
        self.assertEqual([call.args for call in verify.call_args_list],
                         [("video", private), ("video", self.status)])
        self.assertEqual(json.loads(self.receipt.read_text())["state"], "verified")

    def test_failed_disclosure_keeps_video_private(self):
        with (patch.object(self.publisher, "_stage", return_value={"s3key": "staged"}),
              patch.object(self.publisher, "_post", return_value={
                  "successful": True, "data": {"video": {"id": "video"}}}),
              patch.object(self.publisher, "_proxy", side_effect=self.status_response) as proxy,
              patch.object(self.publisher, "_verify", side_effect=RuntimeError("missing disclosure"))):
            with self.assertRaisesRegex(RuntimeError, "missing disclosure"):
                self.publisher.publish(Path("episode.mp4"), self.metadata, self.receipt)
        proxy.assert_called_once()
        self.assertEqual(json.loads(self.receipt.read_text())["state"], "uploaded_private")

    def test_waits_for_private_video_to_finish_processing(self):
        video = {"snippet": {"channelId": "expected"},
                 "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False}}
        expected = {**self.status, "privacyStatus": "private"}
        with (patch.object(self.publisher, "_proxy", side_effect=[
                {"items": []},
                {"items": [{**video, "processingDetails": {"processingStatus": "processing"}}]},
                {"items": [{**video, "processingDetails": {"processingStatus": "succeeded"}}]},
              ]) as proxy,
              patch("post_youtube.time.sleep") as sleep):
            self.publisher._verify("video", expected)
        self.assertEqual(proxy.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_wrong_channel_fails_preflight(self):
        with patch.object(self.publisher, "_proxy", return_value={"items": [{"id": "other"}]}):
            with self.assertRaisesRegex(RuntimeError, "different YouTube channel"):
                self.publisher.preflight()

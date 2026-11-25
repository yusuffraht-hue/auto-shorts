import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
import cloudflare_images as cf

class CloudflareTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict("os.environ", {"CLOUDFLARE_FREE_CONFIRMED":"true", "CLOUDFLARE_ACCOUNT_ID":"a"*32, "CLOUDFLARE_API_TOKEN":"x"*30})
        self.env.start()
        self.addCleanup(self.env.stop)
        cf._remaining = 10
        self.addCleanup(setattr, cf, "_remaining", 10)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/"image.png"

    @patch("cloudflare_images.requests.post")
    def test_disabled_never_calls_api(self, post):
        with patch.dict("os.environ", {"CLOUDFLARE_FREE_CONFIRMED":"false"}):
            self.assertFalse(cf.generate("test", self.path))
        post.assert_not_called()

    @patch("cloudflare_images.requests.post")
    def test_quota_failure_stops_requests(self, post):
        post.return_value.status_code = 429
        self.assertFalse(cf.generate("test", self.path))
        self.assertFalse(cf.generate("test", self.path))
        post.assert_called_once()

    @patch("cloudflare_images.requests.post")
    def test_success_and_budget(self, post):
        raw = b"\x89PNG\r\n\x1a\n"
        post.return_value = Mock(status_code=200)
        post.return_value.json.return_value = {"result":{"image":base64.b64encode(raw).decode()}}
        cf._remaining = 1
        self.assertTrue(cf.generate("test", self.path))
        self.assertEqual(self.path.read_bytes(), raw)
        self.assertFalse(cf.generate("test", self.path))
        post.assert_called_once()

import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "publish_place.py"
spec = importlib.util.spec_from_file_location("publish_place", MODULE)
pp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pp)


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class PublishTests(unittest.TestCase):
    def run_publish(self, live):
        calls = []

        def opener(request, timeout=0):
            calls.append(request)
            return FakeResponse(b'{"versionNumber": 7}')

        with tempfile.TemporaryDirectory() as tmp:
            place = Path(tmp) / "game.rbxl"
            place.write_bytes(b"data")
            result = pp.publish(place, 11, 22, "KEY", live=live, opener=opener)
        return calls[0], result

    def test_default_is_saved_not_live(self):
        request, result = self.run_publish(False)
        self.assertIn("/universes/v1/11/places/22/versions?versionType=Saved", request.full_url)
        self.assertEqual(result["versionNumber"], 7)
        self.assertEqual(request.get_header("X-api-key"), "KEY")

    def test_live_publish_only_when_requested(self):
        request, _ = self.run_publish(True)
        self.assertIn("versionType=Published", request.full_url)

    def test_skips_cleanly_without_credentials(self):
        self.assertEqual(pp.main(["x.rbxl"], env={}), 0)


if __name__ == "__main__":
    unittest.main()

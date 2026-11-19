"""No-network tests for Instagram preflight."""
import importlib.util
import json
import pathlib
import tempfile
import unittest

PATH = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "instagram_reels_preflight.py"
spec = importlib.util.spec_from_file_location("ig_preflight", PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class InstagramPreflightTests(unittest.TestCase):
    def test_quality_must_explicitly_pass(self):
        for report in ({}, {"passed": False}, {"passed": True, "issues": ["bad"]}):
            with self.subTest(report=report), self.assertRaises(ValueError):
                mod.check_quality(report)
        mod.check_quality({"passed": True, "issues": []})

    def test_bad_video_file(self):
        with self.assertRaises(ValueError):
            mod.inspect_video("missing.mp4")

    def test_reject_invalid_series_before_file_reads(self):
        with self.assertRaises(ValueError):
            mod.build_manifest("unknown", "none.mp4", "none.json", "caption", "abc")

    def test_reject_invalid_episode_id_before_file_reads(self):
        with self.assertRaises(ValueError):
            mod.build_manifest("town", "none.mp4", "none.json", "caption", "../other")

    def test_valid_video_probe(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "clip.mp4"
            path.write_bytes(b"0" * 2048)
            response = {"format": {"duration": "35.5"}, "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920},
                {"codec_type": "audio", "codec_name": "aac"},
            ]}
            meta = mod.inspect_video(path, probe=lambda cmd: json.dumps(response).encode())
            self.assertEqual(meta["duration_seconds"], 35.5)

    def test_reject_landscape_video(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "clip.mp4"
            path.write_bytes(b"0" * 2048)
            response = {"format": {"duration": "35"}, "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080},
                {"codec_type": "audio", "codec_name": "aac"},
            ]}
            with self.assertRaises(ValueError):
                mod.inspect_video(path, probe=lambda cmd: json.dumps(response).encode())


if __name__ == "__main__":
    unittest.main()

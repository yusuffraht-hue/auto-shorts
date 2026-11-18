import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import voice_studio


class VoiceStudioTests(unittest.TestCase):
    def test_configured_requires_url(self):
        self.assertTrue(voice_studio.configured({"VOICESTUDIO_URL": "https://voice.example"}))
        self.assertFalse(voice_studio.configured({"VOICESTUDIO_URL": "  "}))

    def test_synthesize_posts_openai_compatible_request_and_writes_audio(self):
        response = Mock()
        response.content = b"ID3" + b"x" * 1197
        response.headers = {"Content-Type": "audio/mpeg"}
        response.raise_for_status.return_value = None
        session = Mock()
        session.post.return_value = response
        env = {
            "VOICESTUDIO_URL": "https://voice.example/",
            "VOICESTUDIO_API_KEY": "secret-test",
            "VOICESTUDIO_MODEL": "omnivoice",
            "VOICESTUDIO_VOICE": "narrator",
        }
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "speech.mp3"
            self.assertTrue(voice_studio.synthesize("Hello there.", output, env, session))
            self.assertEqual(output.read_bytes(), response.content)
        args, kwargs = session.post.call_args
        self.assertEqual(args[0], "https://voice.example/v1/audio/speech")
        self.assertEqual(kwargs["json"], {
            "model": "omnivoice", "voice": "narrator",
            "input": "Hello there.", "response_format": "mp3",
        })
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer secret-test")

    def test_rejects_remote_http_before_sending_any_api_key(self):
        session = Mock()
        with self.assertRaisesRegex(ValueError, "must use HTTPS"):
            voice_studio.synthesize(
                "Hello",
                "/tmp/not-written.mp3",
                {"VOICESTUDIO_URL": "http://voice.example", "VOICESTUDIO_API_KEY": "secret-test"},
                session,
            )
        session.post.assert_not_called()

    def test_rejects_non_audio_content_type_even_when_response_is_large(self):
        response = Mock()
        response.content = b"ID3" + b"x" * 1197
        response.headers = {"Content-Type": "text/html"}
        response.raise_for_status.return_value = None
        session = Mock()
        session.post.return_value = response
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "audio/mpeg"):
                voice_studio.synthesize(
                    "Hello", Path(tmp) / "bad.mp3",
                    {"VOICESTUDIO_URL": "http://localhost:3900"}, session
                )

    def test_rejects_non_mp3_body_even_when_content_type_claims_audio(self):
        response = Mock()
        response.content = b"<html>" * 300
        response.headers = {"Content-Type": "audio/mpeg"}
        response.raise_for_status.return_value = None
        session = Mock()
        session.post.return_value = response
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "recognizable MP3"):
                voice_studio.synthesize(
                    "Hello", Path(tmp) / "bad.mp3",
                    {"VOICESTUDIO_URL": "http://localhost:3900"}, session
                )

    def test_rejects_input_over_voice_studio_limit(self):
        session = Mock()
        with self.assertRaises(ValueError):
            voice_studio.synthesize("a" * 2001, "/tmp/not-written.mp3",
                                    {"VOICESTUDIO_URL": "http://localhost:3900"}, session)
        session.post.assert_not_called()

    def test_rejects_small_response(self):
        response = Mock()
        response.content = b"tiny"
        response.headers = {"Content-Type": "audio/mpeg"}
        response.raise_for_status.return_value = None
        session = Mock()
        session.post.return_value = response
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                voice_studio.synthesize("Hello", Path(tmp) / "bad.mp3",
                                        {"VOICESTUDIO_URL": "http://localhost:3900"}, session)


if __name__ == "__main__":
    unittest.main()

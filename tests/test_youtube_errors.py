"""Offline regression checks for credential-safe YouTube error reporting."""
import unittest
from google.auth.exceptions import RefreshError
from youtube_errors import youtube_upload_error


class YoutubeErrorsTests(unittest.TestCase):
    def test_invalid_grant_with_dict(self):
        err = RefreshError("redacted", {"error": "invalid_grant", "refresh_token": "SECRET_MARKER"})
        message = youtube_upload_error(err)
        self.assertIn("invalid_grant", message)
        self.assertNotIn("SECRET_MARKER", message)
        self.assertNotIn("redacted", message)

    def test_invalid_grant_text(self):
        message = youtube_upload_error(RefreshError("invalid_grant: Token has expired"))
        self.assertIn("reauthorization", message.lower())

    def test_other_refresh_error_redacted(self):
        message = youtube_upload_error(RefreshError("SECRET_MARKER", {"error": "server_error"}))
        self.assertIn("upload stopped", message)
        self.assertNotIn("SECRET_MARKER", message)

    def test_unrelated_error_not_masked(self):
        self.assertIsNone(youtube_upload_error(ValueError("video failed")))


if __name__ == "__main__":
    unittest.main()

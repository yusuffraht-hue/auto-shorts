import json
import unittest
import urllib.error

import post_instagram as pi


class FakeExec:
    """Scripted stand-in for Composio tool calls; records every call."""

    def __init__(self, statuses):
        self.calls = []
        self.statuses = list(statuses)

    def __call__(self, slug, args):
        self.calls.append((slug, args))
        if slug == "INSTAGRAM_GET_USER_INFO":
            return {"id": "111"}
        if slug == "INSTAGRAM_POST_IG_USER_MEDIA":
            return {"id": "c1"}
        if slug == "INSTAGRAM_GET_POST_STATUS":
            return {"status_code": self.statuses.pop(0) if self.statuses else "IN_PROGRESS"}
        if slug == "INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH":
            return {"id": "m1"}
        raise AssertionError(slug)

    def slugs(self):
        return [c[0] for c in self.calls]


class PostReelTests(unittest.TestCase):
    def test_publishes_only_after_processing_finishes(self):
        ex = FakeExec(["IN_PROGRESS", "FINISHED"])
        media_id = pi.post_reel("https://x/v.mp4", "hello #a", ex, sleep=lambda s: None)
        self.assertEqual(media_id, "m1")
        self.assertEqual(ex.slugs(), ["INSTAGRAM_GET_USER_INFO", "INSTAGRAM_POST_IG_USER_MEDIA",
                                      "INSTAGRAM_GET_POST_STATUS", "INSTAGRAM_GET_POST_STATUS",
                                      "INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH"])
        create = ex.calls[1][1]
        self.assertEqual((create["media_type"], create["video_url"], create["caption"], create["ig_user_id"]),
                         ("REELS", "https://x/v.mp4", "hello #a", "111"))
        self.assertEqual(ex.calls[-1][1], {"ig_user_id": "111", "creation_id": "c1"})

    def test_error_status_never_publishes(self):
        ex = FakeExec(["ERROR"])
        with self.assertRaises(pi.ReelFailed):
            pi.post_reel("https://x/v.mp4", "c", ex, sleep=lambda s: None)
        self.assertNotIn("INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH", ex.slugs())

    def test_gives_up_when_processing_never_finishes(self):
        ex = FakeExec([])
        with self.assertRaises(pi.ReelFailed):
            pi.post_reel("https://x/v.mp4", "c", ex, sleep=lambda s: None, max_polls=3)
        self.assertEqual(ex.slugs().count("INSTAGRAM_GET_POST_STATUS"), 3)
        self.assertNotIn("INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH", ex.slugs())

    def test_check_only_mode_never_publishes(self):
        ex = FakeExec(["FINISHED"])
        self.assertIsNone(pi.post_reel("https://x/v.mp4", "c", ex, sleep=lambda s: None, publish=False))
        self.assertNotIn("INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH", ex.slugs())


class CaptionTests(unittest.TestCase):
    def test_caption_fits_the_limit_and_keeps_title_and_hashtags(self):
        story = "Word " * 800
        text = "My Title\n\n" + story + "\n\n#shorts #story"
        caption = pi.build_caption(text, limit=2200)
        self.assertLessEqual(len(caption), 2200)
        self.assertTrue(caption.startswith("My Title"))
        self.assertTrue(caption.endswith("#shorts #story"))

    def test_short_story_is_kept_whole(self):
        text = "Title\n\nA short story.\n\n#a"
        self.assertEqual(pi.build_caption(text), text)


class RestTests(unittest.TestCase):
    class Resp:
        def __init__(self, body):
            self.body = body

        def read(self):
            return json.dumps(self.body).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def test_rest_executor_unwraps_data_and_sends_account(self):
        seen = {}

        def opener(request, timeout=0):
            seen["url"] = request.full_url
            seen["key"] = request.get_header("X-api-key")
            seen["body"] = json.loads(request.data)
            return self.Resp({"data": {"id": "x"}, "successful": True, "error": None})

        run = pi.rest_executor("KEY", "ca_1", opener=opener)
        self.assertEqual(run("INSTAGRAM_GET_USER_INFO", {"ig_user_id": "me"}), {"id": "x"})
        self.assertTrue(seen["url"].endswith("/api/v3/tools/execute/INSTAGRAM_GET_USER_INFO"))
        self.assertEqual(seen["key"], "KEY")
        self.assertEqual(seen["body"], {"connected_account_id": "ca_1", "arguments": {"ig_user_id": "me"}})

    def test_rest_executor_raises_on_failure(self):
        opener = lambda r, timeout=0: self.Resp({"data": {}, "successful": False, "error": "boom"})
        with self.assertRaises(pi.ReelFailed):
            pi.rest_executor("KEY", "ca_1", opener=opener)("X", {})

    def test_nested_data_shape_is_handled(self):
        opener = lambda r, timeout=0: self.Resp({"data": {"data": {"id": "y"}}, "successful": True})
        self.assertEqual(pi.rest_executor("K", "a", opener=opener)("X", {}), {"id": "y"})


class MainTests(unittest.TestCase):
    def test_skips_without_api_key(self):
        self.assertEqual(pi.main(["https://x/v.mp4", "story.txt"], env={}), 0)

    def test_pause_variable_skips(self):
        env = {"COMPOSIO_API_KEY": "k", "INSTAGRAM_POST": "0"}
        self.assertEqual(pi.main(["https://x/v.mp4", "story.txt"], env=env), 0)


if __name__ == "__main__":
    unittest.main()

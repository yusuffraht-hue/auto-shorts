"""Upload through Composio, then verify YouTube's disclosure and visibility."""
import hashlib
import json
import os
import time
from urllib.parse import urlsplit

import requests

API = "https://backend.composio.dev/api/v3.1"
YOUTUBE = "https://www.googleapis.com/youtube/v3"
UPLOAD_TOOL = "YOUTUBE_MULTIPART_UPLOAD_VIDEO"


class YouTubePublisher:
    def __init__(self, api_key, account_id, channel_id):
        if not api_key or not channel_id:
            raise RuntimeError("Composio API key and expected YouTube channel are required")
        self.api_key = api_key
        self.account_id = account_id
        self.user_id = None
        self.channel_id = channel_id

    def _post(self, route, payload):
        try:
            response = requests.post(API + route, json=payload,
                                     headers={"x-api-key": self.api_key}, timeout=180)
            if not response.ok:
                raise RuntimeError(f"Composio {route} returned HTTP {response.status_code}")
            return response.json()
        except (requests.RequestException, ValueError):
            raise RuntimeError(f"Composio {route} request failed") from None

    def _proxy(self, resource, method, query, body=None):
        payload = {
            "connected_account_id": self.account_id,
            "user_id": self.user_id,
            "endpoint": f"{YOUTUBE}/{resource}",
            "method": method,
            "parameters": [{"type": "query", "name": key, "value": value}
                           for key, value in query.items()],
        }
        if body is not None:
            payload["body"] = body
        result = self._post("/tools/execute/proxy", payload)
        if result.get("status") != 200:
            data = result.get("data")
            error = data.get("error") if isinstance(data, dict) else None
            reasons = error.get("errors", []) if isinstance(error, dict) else []
            if any(isinstance(item, dict) and item.get("reason") in {"quotaExceeded", "dailyLimitExceeded"}
                   for item in reasons):
                raise RuntimeError(f"YouTube API quota exhausted during {method} {resource}")
            raise RuntimeError(f"YouTube {method} {resource} returned status {result.get('status')}")
        return result["data"]

    def _execute(self, tool, arguments):
        result = self._post(f"/tools/execute/{tool}", {
            "connected_account_id": self.account_id, "user_id": self.user_id,
            "arguments": arguments,
        })
        if result.get("successful") is not True:
            raise RuntimeError(f"Composio did not confirm {tool}")
        data = result.get("data") or {}
        return data.get("data") or data

    def preflight(self):
        params = {"toolkit_slugs": "youtube", "statuses": "ACTIVE", "limit": 2}
        if self.account_id:
            params["connected_account_ids"] = self.account_id
        try:
            response = requests.get(
                API + "/connected_accounts",
                headers={"x-api-key": self.api_key},
                params=params,
                timeout=60,
            )
            if not response.ok:
                raise RuntimeError(f"Composio account lookup returned HTTP {response.status_code}")
            accounts = response.json()["items"]
        except (requests.RequestException, ValueError, KeyError):
            raise RuntimeError("Composio account lookup failed") from None
        if len(accounts) != 1:
            raise RuntimeError("Set COMPOSIO_YOUTUBE_ACCOUNT_ID to select the active YouTube account")
        account = accounts[0]
        if self.account_id and account["id"] != self.account_id:
            raise RuntimeError("Composio returned a different connected account")
        self.account_id = account["id"]
        self.user_id = account.get("user_id")
        if not self.user_id:
            raise RuntimeError("Composio did not return the connected account owner")
        result = self._execute("YOUTUBE_LIST_CHANNELS", {"part": "id", "mine": True})
        if [item["id"] for item in result.get("items", [])] != [self.channel_id]:
            raise RuntimeError("Composio is connected to a different YouTube channel")

    def _stage(self, path):
        mime_type = "video/mp4"
        with path.open("rb") as video:
            digest = hashlib.file_digest(video, lambda: hashlib.md5(usedforsecurity=False))
            staging = self._post("/files/upload/request", {
                "toolkit_slug": "youtube", "tool_slug": UPLOAD_TOOL,
                "filename": path.name, "mimetype": mime_type, "md5": digest.hexdigest(),
            })
            url = staging.get("new_presigned_url") or staging["newPresignedUrl"]
            if urlsplit(url).scheme != "https":
                raise RuntimeError("Composio returned an invalid staging URL")
            video.seek(0)
            try:
                response = requests.put(url, data=video, headers={"Content-Type": mime_type},
                                        timeout=180, allow_redirects=False)
            except requests.RequestException:
                raise RuntimeError("Composio video staging failed") from None
            if not 200 <= response.status_code < 300:
                raise RuntimeError(f"Composio video staging returned HTTP {response.status_code}")
        return {"name": path.name, "mimetype": mime_type, "s3key": staging["key"]}

    def _set_status(self, video_id, expected, defaults):
        payload = {"id": video_id, "status": {**defaults, **expected}}
        result = self._proxy("videos", "PUT", {"part": "status"}, payload)
        status = result.get("status", {})
        if result.get("id") != video_id or any(status.get(key) != value for key, value in expected.items()):
            raise RuntimeError(f"YouTube did not confirm the requested status for {video_id}")
        self._verify(video_id, expected)

    def _verify(self, video_id, expected):
        query = {"part": "snippet,status,processingDetails", "id": video_id}
        for attempt in range(12):
            result = self._proxy("videos", "GET", query)
            items = result.get("items", [])
            if items:
                if len(items) != 1 or items[0]["snippet"]["channelId"] != self.channel_id:
                    raise RuntimeError(f"YouTube returned {video_id} on an unexpected channel")
                video = items[0]
                status = video["status"]
                # videos.list can omit synthetic disclosure, which the write must confirm.
                if any(status.get(key) != value for key, value in expected.items()
                       if key != "containsSyntheticMedia" or key in status):
                    raise RuntimeError(f"YouTube returned unexpected visibility or disclosure for {video_id}")
                processing = video.get("processingDetails", {}).get("processingStatus")
                if (status.get("uploadStatus") in {"failed", "rejected", "deleted"}
                        or processing in {"failed", "terminated"}):
                    raise RuntimeError(f"YouTube rejected video {video_id}")
                if status.get("uploadStatus") == "processed" or processing == "succeeded":
                    return
            if attempt < 11:
                time.sleep(10)
        raise RuntimeError(f"YouTube did not confirm successful processing for {video_id}")

    def publish(self, path, metadata, receipt):
        requested = metadata["status"]
        if (requested["privacyStatus"] not in {"private", "unlisted", "public"}
                or requested.get("containsSyntheticMedia") is not True
                or not isinstance(requested.get("selfDeclaredMadeForKids"), bool)):
            raise ValueError("YouTube visibility and audience/disclosure settings are required")
        if receipt.exists():
            raise RuntimeError("An upload was already attempted for this render. Check the receipt.")
        staged = self._stage(path)
        # Preserve an ambiguous upload outcome. A retry could create a duplicate.
        receipt.write_text(json.dumps({"state": "upload_attempted"}))
        data = self._execute(UPLOAD_TOOL, {**metadata["snippet"], "privacyStatus": "private", "videoFile": staged})
        video = data.get("video") or data
        video_id = video.get("id")
        if not isinstance(video_id, str) or not video_id:
            raise RuntimeError("Composio did not return a YouTube video ID")
        receipt.write_text(json.dumps({"state": "uploaded_private", "video_id": video_id}))
        private = {**requested, "privacyStatus": "private"}
        defaults = {key: value for key, value in video.get("status", {}).items()
                    if key in {"license", "embeddable", "publicStatsViewable"}}
        self._set_status(video_id, private, defaults)
        if requested != private:
            self._set_status(video_id, requested, defaults)
        receipt.write_text(json.dumps({"state": "verified", "video_id": video_id, **requested}))
        print(f"YouTube verified ({requested['privacyStatus']}): https://www.youtube.com/watch?v={video_id}")


def publisher_from_env():
    return YouTubePublisher(os.environ.get("COMPOSIO_API_KEY"),
                            os.environ.get("COMPOSIO_YOUTUBE_ACCOUNT_ID"),
                            os.environ.get("YOUTUBE_CHANNEL_ID"))

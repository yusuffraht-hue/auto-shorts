#!/usr/bin/env python3
"""Upload a built .rbxl to Roblox through the free Open Cloud Place Publishing API.

Safe by default: versions are *Saved* (visible in Studio's version history, not live).
Set ROBLOX_PUBLISH=1 to publish live. Needs ROBLOX_API_KEY (permission: universe-places:write),
ROBLOX_UNIVERSE_ID and ROBLOX_PLACE_ID. When any is missing the upload is skipped cleanly."""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def publish(rbxl, universe_id, place_id, api_key, live=False, opener=urllib.request.urlopen):
    version_type = "Published" if live else "Saved"
    url = f"https://apis.roblox.com/universes/v1/{universe_id}/places/{place_id}/versions?versionType={version_type}"
    request = urllib.request.Request(
        url, data=Path(rbxl).read_bytes(), method="POST",
        headers={"x-api-key": api_key, "Content-Type": "application/octet-stream"})
    with opener(request, timeout=120) as response:
        body = response.read().decode() or "{}"
    return {"versionType": version_type, **json.loads(body)}


def main(argv=None, env=None):
    argv = sys.argv[1:] if argv is None else argv
    env = os.environ if env is None else env
    if not argv:
        print("usage: publish_place.py game.rbxl")
        return 2
    missing = [k for k in ("ROBLOX_API_KEY", "ROBLOX_UNIVERSE_ID", "ROBLOX_PLACE_ID") if not env.get(k)]
    if missing:
        print("Roblox upload skipped (not configured):", ", ".join(missing))
        return 0
    try:
        result = publish(argv[0], env["ROBLOX_UNIVERSE_ID"], env["ROBLOX_PLACE_ID"],
                         env["ROBLOX_API_KEY"], live=env.get("ROBLOX_PUBLISH") == "1")
    except urllib.error.HTTPError as exc:
        print("Roblox upload failed:", exc.code, exc.read().decode()[:300])
        return 1
    print("Roblox upload ok:", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

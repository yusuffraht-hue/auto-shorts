"""Discover live releases; never publish or fabricate demonstrations."""
import hashlib
import json
import re
from urllib.request import urlopen

SOURCE = "https://api.github.com/repos/yusuffraht-hue/useful-web-lab-public/contents/apps"
SITE = "https://yusuffraht-hue.github.io/useful-web-lab-public/"

def read(url):
    with urlopen(url, timeout=20) as response:
        return response.read(4_000_000)

def verify_release(app, url, fetch, expected=None, *, document=""):
    manifest = json.loads(fetch(url + "release.json"))
    digest = hashlib.sha256(fetch(url + document)).hexdigest()
    if manifest.get("app") != app or manifest.get("sha256") != digest or (expected and digest != expected):
        raise ValueError("Live app does not match the selected release")
    return digest


def discover(fetch=read, promoted=()):
    candidates = []
    for entry in json.loads(fetch(SOURCE)):
        app = entry.get("name", "")
        if entry.get("type") != "dir" or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", app):
            continue
        url = SITE + app + "/"
        try:
            digest = verify_release(app, url, fetch, document="index.html")
        except (OSError, ValueError):
            continue
        if app in promoted:
            continue
        candidates.append({"app": app, "url": url, "sha256": digest,
                           "state": "pending_functional_demo"})
    return candidates

if __name__ == "__main__":
    print(json.dumps(discover(), indent=2))

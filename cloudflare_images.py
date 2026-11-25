import base64
import os
import re
import requests

MODEL = "@cf/black-forest-labs/flux-1-schnell"
_remaining = 10

def generate(prompt, path):
    global _remaining
    account = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
    token = os.getenv("CLOUDFLARE_API_TOKEN", "")
    if os.getenv("CLOUDFLARE_FREE_CONFIRMED") != "true" or not re.fullmatch(r"[0-9a-fA-F]{32}", account) or len(token) < 20 or _remaining <= 0:
        return False
    _remaining -= 1
    try:
        r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{MODEL}",
                          headers={"Authorization": f"Bearer {token}"},
                          json={"prompt": prompt[:2048], "steps": 4}, timeout=90)
        if r.status_code != 200:
            _remaining = 0
            print("Cloudflare disabled for this run:", r.status_code)
            return False
        raw = base64.b64decode(r.json()["result"]["image"], validate=True)
        if not raw.startswith((b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n")):
            return False
        path.write_bytes(raw)
        return True
    except (requests.RequestException, ValueError, KeyError, TypeError):
        _remaining = 0
        return False

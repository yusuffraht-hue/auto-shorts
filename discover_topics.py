"""Discover candidate manga/anime topics using public Jikan metadata.
Candidates are NOT approved facts. Never write into the reviewed topic database.
Check provider terms before enabling scheduled commercial use.
"""
import json
from pathlib import Path
import requests

def discover():
    response = requests.get("https://api.jikan.moe/v4/top/manga",
                            params={"filter": "bypopularity", "limit": 25}, timeout=30)
    response.raise_for_status()
    candidates = []
    for item in response.json().get("data", []):
        if item.get("rating") in ("Rx", "R+"):
            continue
        title = item.get("title_english") or item.get("title")
        if title and item.get("url"):
            candidates.append({"work": title, "discovery_url": item["url"],
                               "reviewed": False, "status": "needs official source and suitability review"})
    return candidates

if __name__ == "__main__":
    path = Path("out/editorial_candidates.json")
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(discover(), indent=2))
    print("Saved unreviewed candidates:", path)

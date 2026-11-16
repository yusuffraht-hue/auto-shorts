#!/usr/bin/env python3
"""Free-first Roblox trend discovery and original concept brief generator."""
from __future__ import annotations
import argparse
import json
import os
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
HISTORY_PATH = ROOT / "history"
USER_AGENT = "RobloxTrendEngine/0.1 (public metadata research)"

def utc_now():
    return datetime.now(timezone.utc)

def load_config():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    override = os.getenv("ROBLOX_SEARCH_TERMS")
    if override:
        config["search_terms"] = [x.strip() for x in override.split(",") if x.strip()]
    config["max_results_per_term"] = int(os.getenv("ROBLOX_MAX_RESULTS", config["max_results_per_term"]))
    return config

def fetch_json(url: str, timeout: int = 15) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))

def walk_dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_dicts(child)

def extract_search_games(payload):
    """Tolerantly extract game-like records from Roblox's evolving search response."""
    found = {}
    for item in walk_dicts(payload):
        universe_id = item.get("universeId") or item.get("universe_id")
        name = item.get("name") or item.get("title")
        if not universe_id or not name:
            continue
        try:
            uid = int(universe_id)
        except (TypeError, ValueError):
            continue
        if uid <= 0:
            continue
        place_id = item.get("rootPlaceId") or item.get("placeId") or item.get("place_id")
        found.setdefault(uid, {
            "universe_id": uid,
            "place_id": int(place_id) if str(place_id or "").isdigit() else None,
            "name": str(name)[:160],
            "search_players": int(item.get("playing") or item.get("playerCount") or 0),
            "search_visits": int(item.get("visits") or 0),
            "search_rank": None,
        })
    return list(found.values())

def search_term(term, limit):
    params = urllib.parse.urlencode({"searchQuery": term, "pageType": "games", "sessionId": "", "pageToken": ""})
    payload = fetch_json("https://apis.roblox.com/search-api/omni-search?" + params)
    games = extract_search_games(payload)[:limit]
    for rank, game in enumerate(games, start=1):
        game["search_rank"] = rank
    return games

def enrich_games(games):
    ids = [str(g["universe_id"]) for g in games]
    if not ids:
        return games
    enriched = {}
    for start in range(0, len(ids), 50):
        url = "https://games.roblox.com/v1/games?universeIds=" + ",".join(ids[start:start + 50])
        payload = fetch_json(url)
        for item in payload.get("data", []):
            uid = int(item.get("id", 0))
            if uid:
                enriched[uid] = item
        time.sleep(0.35)
    result = []
    for game in games:
        details = enriched.get(game["universe_id"], {})
        result.append({
            **game,
            "name": details.get("name") or game["name"],
            "playing": int(details.get("playing") or game.get("search_players") or 0),
            "visits": int(details.get("visits") or game.get("search_visits") or 0),
            "created": details.get("created"),
            "updated": details.get("updated"),
            "genre": details.get("genre"),
            "max_players": details.get("maxPlayers"),
            "source": "Roblox public search + game details",
        })
    return result

def load_previous_snapshot():
    files = sorted(HISTORY_PATH.glob("*.json"))
    if not files:
        return {}
    try:
        data = json.loads(files[-1].read_text(encoding="utf-8"))
        return {int(g["universe_id"]): g for g in data.get("games", [])}
    except (OSError, ValueError, KeyError, TypeError):
        return {}

def score_games(games, previous, min_players):
    scored = []
    for game in games:
        uid = int(game["universe_id"])
        old = previous.get(uid, {})
        players = int(game.get("playing", 0))
        old_players = int(old.get("playing", 0))
        growth_pct = round(((players - old_players) / old_players) * 100, 1) if old and old_players > 0 else None
        appearances = int(game.get("appearances", 1))
        growth_score = min(35, max(0, (growth_pct or 0) / 3))
        player_score = min(25, (players / 1000) ** 0.5 * 5)
        discovery_score = min(20, appearances * 5)
        saturation_penalty = min(25, max(0, appearances - 2) * 4)
        score = round(max(0, min(100, 20 + growth_score + player_score + discovery_score - saturation_penalty)), 1)
        if players < min_players:
            score = round(score * 0.65, 1)
        scored.append({
            **game,
            "growth_pct_since_previous_scan": growth_pct,
            "trend_score": score,
            "signal": "rising" if growth_pct is not None and growth_pct >= 15 else ("established" if players >= 1000 else "early_or_unverified"),
        })
    return sorted(scored, key=lambda x: (x["trend_score"], x.get("playing", 0)), reverse=True)

def concept_ideas(ranked, count):
    """Generate original combinations as hypotheses, not trend predictions."""
    patterns = [
        ("Hatch + expedition", "Players hatch companions, then take them on co-op expeditions where the world changes their evolution.", ["egg hatching", "exploration", "creature evolution"]),
        ("Garden + defense", "Players grow living defenses, cross-breed plants, and protect a shared island from night events.", ["gardening", "tower defense", "co-op survival"]),
        ("RNG + skill", "Random drops create build variety, but skill challenges and crafting let players influence outcomes.", ["RNG", "skill trials", "crafting"]),
        ("Creature rescue + builder", "Players rescue varied creatures, build habitats, and unlock community expeditions.", ["collection", "base building", "social play"]),
        ("Short-session roguelite", "Players enter replayable 5-minute dungeons, combine temporary powers, and bring home cosmetic trophies.", ["roguelite", "progression", "co-op"]),
        ("Mystery + survival", "A group investigates a shifting map, gathers clues, and survives an adaptive creature.", ["horror", "mystery", "survival"]),
        ("Tycoon + competition", "Players build unusual production lines, then enter fair timed challenges using what they created.", ["tycoon", "building", "competition"]),
    ]
    top_names = [g["name"] for g in ranked[:5]]
    ideas = []
    for title, hook, tags in patterns[:min(count, len(patterns))]:
        ideas.append({
            "title": title, "core_hook": hook, "inspiration_signals": tags,
            "why_test_it": "Combines familiar loops with a distinct player-driven mechanic; validate demand before committing.",
            "monetization": ["optional cosmetics", "fair convenience features", "private servers if appropriate"],
            "avoid": ["pay-to-win advantages", "paid random rewards aimed at children", "misleading purchase prompts"],
            "validation": ["prototype the first 3 minutes", "test with a small group", "measure day-1 return rate and session length"],
            "observed_games_for_context": top_names,
        })
    return ideas

def build_ai_handoff(ideas):
    import json
    return (
        "Act as a Roblox game design team. Treat these as hypotheses, not proof of demand. "
        "Create an original concept; do not copy existing games, names, maps, UI, or assets. "
        "Prioritize a fun first 3 minutes, meaningful progression, accessibility, and fair optional cosmetics. "
        "No paid APIs, assets, Robux purchases, gambling-like monetization, or pay-to-win. "
        "Return a design brief, MVP scope, Luau module plan, test plan, and risks.\n\n"
        + json.dumps(ideas, ensure_ascii=False, indent=2)
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=os.getenv("TREND_REPORT_DIR", str(ROOT / "reports")))
    args = parser.parse_args()
    config = load_config()
    warnings = []
    by_id = {}
    term_results = {}
    for term in config["search_terms"]:
        try:
            results = search_term(term, int(config["max_results_per_term"]))
            term_results[term] = len(results)
            for game in results:
                uid = int(game["universe_id"])
                if uid not in by_id:
                    by_id[uid] = {**game, "matched_terms": [term], "appearances": 1}
                else:
                    by_id[uid]["matched_terms"].append(term)
                    by_id[uid]["appearances"] += 1
            time.sleep(0.5)
        except Exception as exc:
            warnings.append(f"{term}: {type(exc).__name__}: {str(exc)[:240]}")
    games = list(by_id.values())[:int(config["max_universes_to_enrich"])]
    try:
        games = enrich_games(games)
    except Exception as exc:
        warnings.append(f"Metadata enrichment: {type(exc).__name__}: {str(exc)[:240]}")
        for game in games:
            game.setdefault("playing", game.get("search_players", 0))
            game.setdefault("visits", game.get("search_visits", 0))
    ranked = score_games(games, load_previous_snapshot(), int(config["minimum_players_for_signal"]))
    ideas = concept_ideas(ranked, int(config["concepts_to_generate"]))
    now = utc_now()
    snapshot = {"generated_at": now.isoformat(), "source": "Roblox public search and game details endpoints",
                "terms_checked": term_results, "warnings": warnings, "games": ranked}
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.mkdir(parents=True, exist_ok=True)
    (HISTORY_PATH / (now.strftime("%Y-%m-%d") + ".json")).write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    report = {"generated_at": now.isoformat(), "terms_checked": term_results, "games_scanned": len(ranked),
              "warnings": warnings, "top_signals": ranked[:20], "concept_ideas": ideas,
              "ai_handoff_prompt": build_ai_handoff(ideas),
              "interpretation": "Heuristic opportunity signals, not predictions of popularity or income."}
    (output / "latest-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = ["# Roblox Trend Engine — Daily Opportunity Report", "", f"Generated: {now.isoformat()}",
             f"Games found: {len(ranked)}", "",
             "> Scores are heuristics, not a promise of popularity or revenue. Search ranking is incomplete.",
             "", "## Top game signals", "", "| Score | Game | Players now | Change vs previous scan | Search themes |",
             "|---:|---|---:|---:|---|"]
    for game in ranked[:20]:
        change = "baseline pending" if game["growth_pct_since_previous_scan"] is None else f'{game["growth_pct_since_previous_scan"]:+.1f}%'
        name = game["name"].replace("|", "/")
        lines.append(f'| {game["trend_score"]} | {name} | {game.get("playing", 0)} | {change} | {", ".join(game.get("matched_terms", []))} |')
    lines += ["", "## Original concepts to test", ""]
    for idea in ideas:
        lines += [f'### {idea["title"]}', "", idea["core_hook"], "", "**Core loops:** " + ", ".join(idea["inspiration_signals"]), ""]
    lines += ["## Collection warnings", ""]
    lines += [f"- {w}" for w in warnings] or ["- None"]
    lines += ["", "## AI handoff", "", "Copy ai_handoff_prompt from latest-report.json into Gemini, then ask Claude to review the Luau architecture."]
    (output / "latest-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report written to {output}. Games scanned: {len(ranked)}. Warnings: {len(warnings)}.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

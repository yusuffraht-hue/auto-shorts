# Roblox Trend Engine (free-first MVP)

A separate project inside this repository. It scans Roblox game-search results for configurable gameplay themes, records public game metadata, compares snapshots, ranks opportunity signals, and generates original game concept briefs.

## What it does
- Queries Roblox's public game search endpoint for configured discovery phrases.
- Enriches returned universe IDs with public game metadata (playing, visits, update time).
- Stores dated snapshots and compares player-count changes where a prior snapshot exists.
- Scores signals using player growth, current player count, search appearances, and saturation.
- Generates original concept briefs and a structured JSON report.
- Runs daily in GitHub Actions and saves a report artifact.

## Important limits
- This is an opportunity detector, not a reliable prediction of virality or earnings.
- Roblox search results are personalized/ranked and are not a complete view of discovery or revenue charts.
- The first scan has no historical baseline, so growth scores are unavailable until later scans.
- The public search endpoint is undocumented and may change or rate-limit. Failures are reported, not fabricated.
- It does not create or publish a Roblox experience, access Roblox accounts, spend Robux, or make purchases.
- The generated concepts are original design briefs, not complete playable games yet.
- Daily analysis only; no automatic game publishing.

## Run locally
Requires Python 3.11+ and no third-party packages.

    python roblox_trend_engine/trend_engine.py --output roblox_trend_engine/reports
    python -m unittest discover -s roblox_trend_engine/tests -v

Optional environment variables:
- ROBLOX_SEARCH_TERMS: comma-separated override for query phrases.
- ROBLOX_MAX_RESULTS: max search results per phrase (default 20).
- TREND_REPORT_DIR: output directory (default roblox_trend_engine/reports).

## AI handoff
Each report includes a prompt to pass to Gemini for concept expansion and Claude for Luau architecture/code review. The MVP does not automatically connect consumer AI chats.

# AI Roblox Trend Engine

The Trend Engine is a separate, free-first project alongside Auto-Shorts.

## Current MVP
- Daily scheduled Roblox public-search scan.
- Public game metadata enrichment.
- Snapshot history and growth comparisons.
- Heuristic opportunity scoring and original concept generation.
- Markdown + JSON reports uploaded as GitHub Actions artifacts.
- Unit tests.
- No paid services, paid APIs, game publishing, account access, Robux spending, or automatic monetization changes.

Start here: roblox_trend_engine/README.md.

## Roadmap
1. Validate discovery data collection over several daily scans.
2. Add genre-level trend clustering and saturation detection.
3. Add Gemini concept expansion using only an explicitly configured free-tier key, with manual handoff fallback.
4. Add Claude code review through manual shared GitHub handoff unless a genuinely free API route is available.
5. Generate Roblox Luau project modules and test plans.
6. Add a safe Studio import/export workflow. Roblox Studio still needs a supported computer; this repo does not bypass that limitation.
7. Only after human review, test a small prototype with players and use aggregate analytics to decide whether to expand.

## Guardrails
A high trend score is not a promise of success. Prefer original mechanics over copying, protect player data, avoid manipulative monetization and paid random rewards aimed at children, and require human approval before publishing or spending.

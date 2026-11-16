# Daily Roblox Game Factory

A no-cost, offline-first generator that packages one Roblox MVP source project per day.

## Daily process
1. GitHub Actions checks out the repository.
2. Offline tests verify archetype rotation and project structure.
3. The generator chooses a gameplay archetype and avoids the most recently used archetypes until the catalog has rotated.
4. It creates a Rojo project with server/client Luau, metadata, README and a test plan.
5. GitHub Actions stores the source as a downloadable artifact for 30 days.

## Gameplay archetypes
Crystal mining; floating-island parcel delivery; relic maze exploration; garden planting; dungeon treasure hunting; tidal rescue time trials. These have different interactions, not just different names.

## Honest limitations
- This is deterministic template-based generation, not an AI that invents unlimited new mechanics.
- Generated source is not verified inside Roblox Studio. A human must import and play-test on supported Windows/Mac.
- It never publishes, accesses Roblox credentials, spends Robux, or requires API keys.
- Daily generation begins only after the PR is merged and Actions is enabled.
- Artifacts expire after 30 days; download and archive projects you want to keep.

## Run locally
python -m unittest discover -s roblox_game_factory/tests -v
python roblox_game_factory/daily_factory.py --output dist/daily-games

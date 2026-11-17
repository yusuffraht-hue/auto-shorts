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

## No Roblox Studio needed (built and saved from GitHub)
The daily workflow now builds `game.rbxl` with Rojo on GitHub's servers, runs a Luau check and a simulated
play-through of every game, and can save the place to your Roblox experience through the free Open Cloud API.

Optional setup (all free):
1. Create an experience in Roblox Creator Hub and note its **Universe ID** and **Place ID**.
2. Create an Open Cloud API key with the **Place Publishing** permission for that experience.
3. Add repository secrets `ROBLOX_API_KEY`, `ROBLOX_UNIVERSE_ID`, `ROBLOX_PLACE_ID`.

Uploads are **Saved** versions by default (they appear in Studio's version history and are not live). Set the
repository variable `ROBLOX_PUBLISH` to `1` only when you have reviewed a build and want it live.

# Trend-to-game generation contract

The Trend Engine should turn its highest-ranked original concepts into small, playable Roblox MVPs.

## Required outputs
1. Original design brief tied to observed signals, without copying a named game.
2. Small playable MVP, not a giant untestable code dump.
3. Server-authoritative Luau for currency, inventory, rewards, combat and saving.
4. Client UI that calls validated RemoteEvents/RemoteFunctions.
5. World generation using Roblox-native Parts when no approved free assets are available.
6. Test checklist, economy data and known limitations.
7. Importable Rojo project and manual Studio fallback guide.

## Quality gates
- Never trust client-supplied currency, rarity, damage, ownership or purchase success.
- Validate every remote request and add rate limits.
- Use DataStore calls inside pcall and handle unavailable storage without crashing.
- Do not add paid assets, paid APIs, paid hosting, Robux products or automatic public publishing.
- No paid random-item mechanics, gambling-like loops, manipulative purchase prompts or pay-to-win.
- Do not copy another creator's maps, code, names, UI, characters or assets.
- A human must test the project in Roblox Studio before publishing.

# Playable Roblox prototype: Critter Hatchers — Sky Isles

This is the first playable game template produced by the Trend Engine. It uses Roblox-built Parts and UI only: no Higgsfield, paid asset packs, paid APIs, or external art are required.

## Gameplay included
- Floating-island hub generated automatically.
- Click to earn coins.
- Hatch a companion egg for 100 coins, with server-controlled weighted rarity.
- View your collection and equip a companion.
- Equipped companions increase click earnings.
- Rebirth for a permanent multiplier after reaching the coin requirement.
- DataStore saving for coins, collection, equipped companion, and rebirths (when Studio/API settings permit).
- Server-side validation and click cooldowns.

## Open and run
1. Download or clone this repository on a computer that can run Roblox Studio.
2. Install the free open-source Rojo tool and Rojo Studio plugin, or manually copy the scripts into the matching Roblox Studio services.
3. Open default.project.json with Rojo and sync the project into a blank place.
4. In Roblox Studio, press Play.
5. For saving in a published test experience, enable Game Settings → Security → Enable Studio Access to API Services.

## Chromebook limitation
Roblox Studio does not officially support ChromeOS/ARM Linux. These source files are ready for Studio import, but this repository cannot run Roblox Studio or publish the game from your Chromebook. You will need a supported Windows/Mac computer (or a trusted helper with Studio) for final import, testing, and publishing. Never give anyone your Roblox password.

## Source structure
- src/server/GameServer.server.lua: world generation, server economy, hatching, inventory, saving.
- src/client/HatchUI.client.lua: responsive game UI and client requests.
- default.project.json: Rojo project mapping.

## Monetization
This is a prototype, not a revenue guarantee. It has no paid products, paid random rewards, trading, or pay-to-win purchases. Validate that the game is fun first. Future monetization should be optional cosmetics and transparent, age-appropriate purchases, with human approval.

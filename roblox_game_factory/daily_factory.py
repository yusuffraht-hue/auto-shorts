#!/usr/bin/env python3
"""Offline daily Roblox MVP source generator. No credentials or network access."""
import argparse, hashlib, json, re
from datetime import date
from pathlib import Path

CATALOG = [
 {"id":"crystal_miner","title":"Crystal Frontier","genre":"Mining","hook":"Mine crystal clusters and upgrade tools to reach deeper deposits.","objective":"Mine five crystals.","world":"A terraced crystal canyon."},
 {"id":"sky_courier","title":"Cloudline Couriers","genre":"Delivery","hook":"Carry parcels between floating islands and build a delivery streak.","objective":"Deliver three parcels.","world":"Floating islands connected by bridges."},
 {"id":"relic_maze","title":"Relic Run","genre":"Maze exploration","hook":"Explore branching corridors, collect relics and unlock the exit.","objective":"Collect three relics and open the exit.","world":"A stone maze with a sealed exit."},
 {"id":"garden_guard","title":"Moonroot Garden","genre":"Garden defense","hook":"Plant defensive sprouts in marked plots and protect a moonroot.","objective":"Plant six sprouts.","world":"A moonlit garden arena."},
 {"id":"dungeon_echo","title":"Echoes Below","genre":"Dungeon treasure hunt","hook":"Search chambers for ancient echoes and open a sealed vault.","objective":"Collect five echoes and unlock the vault.","world":"An underground multi-room ruin."},
 {"id":"tidal_rescue","title":"Tidal Rescue Crew","genre":"Rescue time trial","hook":"Rescue stranded islanders and return them to a safe dock.","objective":"Rescue four crew members and return to the dock.","world":"A low-poly archipelago."}
]

def choose_game(day, history=None):
    digest = hashlib.sha256(day.isoformat().encode()).digest()
    if not history:
        # The scheduled workflow has no external state: calendar rotation guarantees
        # different archetypes on consecutive days without a database or API.
        selected = CATALOG[day.toordinal() % len(CATALOG)]
    else:
        pool = [g for g in CATALOG if g["id"] not in history[-len(CATALOG):]] or CATALOG
        selected = pool[int.from_bytes(digest[:4], "big") % len(pool)]
    return {**selected, "seed": int.from_bytes(digest[4:8], "big"), "date": day.isoformat()}

GOALS = {"crystal_miner": 5, "sky_courier": 3, "relic_maze": 3, "garden_guard": 6,
         "dungeon_echo": 5, "tidal_rescue": 4}

SERVER_LUA = r"""-- Generated MVP. All progress and rewards are server-authoritative.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Workspace = game:GetService("Workspace")
local MODE = %%MODE%%
local SEED = %%SEED%%
local GOAL = %%GOAL%%
local OBJECTIVE = %%OBJECTIVE%%
local AUTO = (MODE == "crystal_miner" or MODE == "garden_guard" or MODE == "sky_courier")
local event = Instance.new("RemoteEvent")
event.Name = "DailyGameStatus"; event.Parent = ReplicatedStorage
local world = Instance.new("Folder"); world.Name = "GeneratedWorld"; world.Parent = Workspace
local progress, runStart, carrying, resets = {}, {}, {}, {}

local function part(name, size, pos, color)
 local p = Instance.new("Part"); p.Name = name; p.Size = size; p.Position = pos
 p.Anchored = true; p.Color = color; p.Parent = world; return p
end
local function notify(player, msg) event:FireClient(player, msg, progress[player] or 0, GOAL) end
local function prompt(obj, action, callback)
 local p = Instance.new("ProximityPrompt"); p.ActionText = action; p.ObjectText = obj.Name
 p.HoldDuration = 0.4; p.MaxActivationDistance = 12; p.Parent = obj
 p.Triggered:Connect(callback)
end
local function setProgress(player, value)
 progress[player] = value
 local stats = player:FindFirstChild("leaderstats")
 if stats and stats:FindFirstChild("Progress") then stats.Progress.Value = value end
end
local function complete(player, msg)
 local stats = player:FindFirstChild("leaderstats")
 if stats and stats:FindFirstChild("Wins") then stats.Wins.Value = stats.Wins.Value + 1 end
 notify(player, msg .. " Round complete! New round starting soon...")
 task.delay(6, function()
  if not player.Parent then return end
  for _, reset in ipairs(resets) do reset() end
  carrying[player] = nil; runStart[player] = nil
  setProgress(player, 0)
  notify(player, "New round! " .. OBJECTIVE)
 end)
end
local function award(player, msg)
 if (progress[player] or 0) >= GOAL then return end
 runStart[player] = runStart[player] or os.clock()
 setProgress(player, (progress[player] or 0) + 1)
 if AUTO and progress[player] >= GOAL then complete(player, msg) else notify(player, msg) end
end
local function setup(player)
 progress[player] = 0
 local stats = Instance.new("Folder"); stats.Name = "leaderstats"; stats.Parent = player
 local value = Instance.new("IntValue"); value.Name = "Progress"; value.Parent = stats
 local wins = Instance.new("IntValue"); wins.Name = "Wins"; wins.Parent = stats
 player.CharacterAdded:Connect(function() task.wait(1); notify(player, OBJECTIVE) end)
end
Players.PlayerAdded:Connect(setup)
for _, existing in ipairs(Players:GetPlayers()) do setup(existing) end
Players.PlayerRemoving:Connect(function(p) progress[p] = nil; carrying[p] = nil; runStart[p] = nil end)

local ground = Color3.fromRGB(70, 120, 90)
if MODE == "tidal_rescue" then ground = Color3.fromRGB(60, 130, 190) end
if MODE ~= "sky_courier" then part("IslandGround", Vector3.new(160, 4, 160), Vector3.new(0, -3, 0), ground) end
local spawn = Instance.new("SpawnLocation"); spawn.Size = Vector3.new(12, 1, 12)
spawn.Position = Vector3.new(0, 1, 0); spawn.Anchored = true; spawn.Neutral = true; spawn.Parent = world

if MODE == "crystal_miner" then
 local nodes = {}
 for i = 1, 10 do
  local node = part("Crystal" .. i, Vector3.new(5, 7, 5), Vector3.new((i - 5) * 13, 2, (i % 3) * 15 + 10), Color3.fromRGB(90, 210, 235))
  node.Shape = Enum.PartType.Ball
  nodes[#nodes + 1] = node
  prompt(node, "Mine crystal", function(p)
   if node:GetAttribute("Mined") then return end
   node:SetAttribute("Mined", true); node.Transparency = 1; node.CanCollide = false
   award(p, "Crystal mined!")
   task.delay(10, function() if node.Parent then node:SetAttribute("Mined", false); node.Transparency = 0; node.CanCollide = true end end)
  end)
 end
 resets[#resets + 1] = function() for _, n in ipairs(nodes) do n:SetAttribute("Mined", false); n.Transparency = 0; n.CanCollide = true end end
elseif MODE == "sky_courier" then
 local green = Color3.fromRGB(70, 120, 90)
 part("HubIsland", Vector3.new(36, 4, 36), Vector3.new(0, -3, 0), green)
 part("PickupIsland", Vector3.new(36, 4, 36), Vector3.new(-52, -3, 0), green)
 part("DeliveryIsland", Vector3.new(36, 4, 36), Vector3.new(52, -3, 0), green)
 part("BridgeWest", Vector3.new(16, 2, 8), Vector3.new(-26, -2, 0), Color3.fromRGB(150, 110, 70))
 part("BridgeEast", Vector3.new(16, 2, 8), Vector3.new(26, -2, 0), Color3.fromRGB(150, 110, 70))
 local parcel = part("Parcel", Vector3.new(4, 4, 4), Vector3.new(-52, 1, 0), Color3.fromRGB(230, 175, 70))
 local beacon = part("DeliveryBeacon", Vector3.new(12, 2, 12), Vector3.new(52, 0, 0), Color3.fromRGB(75, 190, 230))
 prompt(parcel, "Collect parcel", function(p)
  if carrying[p] then notify(p, "Already carrying a parcel. Deliver it!"); return end
  carrying[p] = true; notify(p, "Parcel collected. Deliver it to the far island!")
 end)
 prompt(beacon, "Deliver parcel", function(p)
  if not carrying[p] then notify(p, "Collect a parcel first."); return end
  carrying[p] = nil; award(p, "Delivery complete!")
 end)
elseif MODE == "relic_maze" or MODE == "dungeon_echo" then
 local dark = MODE == "dungeon_echo"
 local wallColor = dark and Color3.fromRGB(70, 60, 85) or Color3.fromRGB(150, 140, 120)
 local rows = dark and 4 or 3
 for r = 1, rows do
  local z = r * 12
  local gx = (r % 2 == 1) and 28 or -28
  part("WallL" .. r, Vector3.new((gx - 8) + 80, 12, 2), Vector3.new(((gx - 8) - 80) / 2, 6, z), wallColor)
  part("WallR" .. r, Vector3.new(80 - (gx + 8), 12, 2), Vector3.new(((gx + 8) + 80) / 2, 6, z), wallColor)
 end
 local finalZ = (rows + 1) * 12
 part("FinalWallL", Vector3.new(70, 12, 2), Vector3.new(-45, 6, finalZ), wallColor)
 part("FinalWallR", Vector3.new(70, 12, 2), Vector3.new(45, 6, finalZ), wallColor)
 part("BoundaryW", Vector3.new(2, 12, finalZ + 30), Vector3.new(-80, 6, (finalZ + 10) / 2), wallColor)
 part("BoundaryE", Vector3.new(2, 12, finalZ + 30), Vector3.new(80, 6, (finalZ + 10) / 2), wallColor)
 part("BackWall", Vector3.new(160, 12, 2), Vector3.new(0, 6, finalZ + 20), wallColor)
 part("TreasureRoom", Vector3.new(30, 1, 14), Vector3.new(0, 0.5, finalZ + 10), Color3.fromRGB(235, 200, 90))
 local relics = {}
 for i = 1, GOAL do
  local corridor = dark and (i - 1) or i
  local x = (i % 2 == 1) and -24 or 24
  local relic = part((dark and "Echo" or "Relic") .. i, Vector3.new(3, 3, 3), Vector3.new(x, 2, corridor * 12 + 6), Color3.fromRGB(190, 125, 245))
  relics[#relics + 1] = relic
  prompt(relic, dark and "Collect echo" or "Collect relic", function(p)
   if relic:GetAttribute("Taken") then return end
   relic:SetAttribute("Taken", true); relic.Transparency = 1; relic.CanCollide = false
   award(p, dark and "Echo collected!" or "Relic collected!")
  end)
 end
 local gate = part("ExitGate", Vector3.new(20, 14, 2), Vector3.new(0, 7, finalZ), Color3.fromRGB(180, 75, 65))
 prompt(gate, dark and "Unlock vault" or "Open exit", function(p)
  if (progress[p] or 0) < GOAL then notify(p, "Find all " .. GOAL .. " first."); return end
  gate.Color = Color3.fromRGB(70, 210, 120); gate.CanCollide = false; gate.Transparency = 0.6
  complete(p, "Unlocked!")
 end)
 resets[#resets + 1] = function()
  for _, r in ipairs(relics) do r:SetAttribute("Taken", false); r.Transparency = 0; r.CanCollide = true end
  gate.Color = Color3.fromRGB(180, 75, 65); gate.CanCollide = true; gate.Transparency = 0
 end
elseif MODE == "garden_guard" then
 local plots, sprouts = {}, {}
 for i = 1, 6 do
  local plot = part("GardenPlot" .. i, Vector3.new(10, 1, 10), Vector3.new((i - 3.5) * 15, 0, 20), Color3.fromRGB(110, 75, 50))
  plots[#plots + 1] = plot
  part("Fence" .. i, Vector3.new(11, 2, 1), Vector3.new((i - 3.5) * 15, 1, 27), Color3.fromRGB(150, 110, 70))
  prompt(plot, "Plant sprout", function(p)
   if plot:GetAttribute("Planted") then return end
   plot:SetAttribute("Planted", true)
   local sprout = part("Sprout", Vector3.new(3, 7, 3), plot.Position + Vector3.new(0, 4, 0), Color3.fromRGB(80, 190, 95))
   sprout.Shape = Enum.PartType.Ball; sprouts[#sprouts + 1] = sprout
   award(p, "Sprout planted!")
  end)
 end
 resets[#resets + 1] = function()
  for _, s in ipairs(sprouts) do s:Destroy() end
  sprouts = {}
  for _, pl in ipairs(plots) do pl:SetAttribute("Planted", false) end
 end
elseif MODE == "tidal_rescue" then
 local dock = part("SafeDock", Vector3.new(18, 2, 18), Vector3.new(0, 0, -40), Color3.fromRGB(150, 110, 70))
 local crew = {}
 for i = 1, 4 do
  local member = part("CrewMember" .. i, Vector3.new(4, 6, 4), Vector3.new((i - 2.5) * 24, 2, 35), Color3.fromRGB(235, 190, 120))
  crew[#crew + 1] = member
  prompt(member, "Rescue crew", function(p)
   if member:GetAttribute("Rescued") then return end
   member:SetAttribute("Rescued", true); member.Transparency = 1; member.CanCollide = false
   award(p, "Crew member rescued!")
  end)
 end
 prompt(dock, "Return to dock", function(p)
  if (progress[p] or 0) < GOAL then notify(p, "Rescue all " .. GOAL .. " crew members first."); return end
  complete(p, string.format("All crew rescued in %.0f seconds!", os.clock() - (runStart[p] or os.clock())))
 end)
 resets[#resets + 1] = function() for _, m in ipairs(crew) do m:SetAttribute("Rescued", false); m.Transparency = 0; m.CanCollide = true end end
end
print("Generated game loaded. Seed: " .. tostring(SEED))
"""

CLIENT_LUA = r"""local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local event = ReplicatedStorage:WaitForChild("DailyGameStatus")
local gui = Instance.new("ScreenGui"); gui.Name = "DailyGameHUD"; gui.ResetOnSpawn = false
gui.Parent = Players.LocalPlayer:WaitForChild("PlayerGui")
local panel = Instance.new("Frame"); panel.Size = UDim2.new(0, 350, 0, 125)
panel.Position = UDim2.new(0, 18, 0, 18); panel.BackgroundColor3 = Color3.fromRGB(28, 38, 58); panel.Parent = gui
local title = Instance.new("TextLabel"); title.Size = UDim2.new(1, -20, 0, 36)
title.Position = UDim2.new(0, 10, 0, 6); title.BackgroundTransparency = 1
title.Text = %%TITLE%%; title.TextColor3 = Color3.new(1, 1, 1)
title.TextSize = 22; title.Font = Enum.Font.GothamBold; title.Parent = panel
local objective = Instance.new("TextLabel"); objective.Size = UDim2.new(1, -20, 0, 65)
objective.Position = UDim2.new(0, 10, 0, 48); objective.BackgroundTransparency = 1
objective.Text = %%OBJECTIVE%%; objective.TextWrapped = true
objective.TextColor3 = Color3.fromRGB(225, 235, 245); objective.TextSize = 16; objective.Parent = panel
event.OnClientEvent:Connect(function(msg, count, goal)
 objective.Text = tostring(msg) .. " | Progress: " .. tostring(count or 0) .. "/" .. tostring(goal or 0)
end)
"""

def server_source(game):
    goal = GOALS.get(game["id"], 3)
    return (SERVER_LUA.replace("%%MODE%%", json.dumps(game["id"]))
            .replace("%%SEED%%", str(int(game.get("seed", 0))))
            .replace("%%GOAL%%", str(goal))
            .replace("%%OBJECTIVE%%", json.dumps(game["objective"])))

def client_source(game):
    return (CLIENT_LUA.replace("%%TITLE%%", json.dumps(game["title"]))
            .replace("%%OBJECTIVE%%", json.dumps(game["objective"])))

def generate(output, day, history=None):
    game=choose_game(day,history)
    folder=output/(day.isoformat()+"-"+re.sub(r"[^a-z0-9]+","-",game["title"].lower()).strip("-"))
    (folder/"src/server").mkdir(parents=True,exist_ok=True)
    (folder/"src/client").mkdir(parents=True,exist_ok=True)
    (folder/"src/server/GameServer.server.lua").write_text(server_source(game),encoding="utf-8")
    (folder/"src/client/GameHUD.client.lua").write_text(client_source(game),encoding="utf-8")
    project={"name":re.sub(r"[^A-Za-z0-9]","",game["title"]),"tree":{"$className":"DataModel",
      "ReplicatedStorage":{"$className":"ReplicatedStorage"},
      "ServerScriptService":{"$className":"ServerScriptService","GameServer":{"$path":"src/server/GameServer.server.lua"}},
      "StarterPlayer":{"$className":"StarterPlayer","StarterPlayerScripts":{"$className":"StarterPlayerScripts","GameHUD":{"$path":"src/client/GameHUD.client.lua"}}}}}
    (folder/"default.project.json").write_text(json.dumps(project,indent=2)+"\n",encoding="utf-8")
    (folder/"game.json").write_text(json.dumps(game,indent=2)+"\n",encoding="utf-8")
    (folder/"README.md").write_text("# "+game["title"]+"\n\nGenerated "+day.isoformat()+" by the offline Daily Roblox Game Factory.\n\nGenre: "+game["genre"]+"\n\n"+game["hook"]+"\n\nObjective: "+game["objective"]+"\n\nWorld: "+game["world"]+"\n\nImport with Rojo on a supported Windows/Mac computer and press Play in Studio. This is an MVP scaffold, not a Studio-verified finished game. No publishing or account access occurs.\n",encoding="utf-8")
    (folder/"TEST_PLAN.md").write_text("# Test plan\n\n- [ ] Rojo project resolves both scripts.\n- [ ] Spawn and HUD appear.\n- [ ] "+game["objective"]+"\n- [ ] Duplicate interactions do not grant duplicate rewards.\n- [ ] Two-player test and disconnect test.\n- [ ] Review Output window and mobile UI in Studio.\n",encoding="utf-8")
    return {"date":day.isoformat(),"game_id":game["id"],"title":game["title"],"path":str(folder)}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=Path("dist/daily-games"))
    parser.add_argument("--date",default=date.today().isoformat())
    parser.add_argument("--history",type=Path)
    args=parser.parse_args()
    history=json.loads(args.history.read_text()) if args.history and args.history.exists() else []
    print(json.dumps(generate(args.output,date.fromisoformat(args.date),history),indent=2))

if __name__=="__main__": main()

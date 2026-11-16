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
    history = history or []
    pool = [g for g in CATALOG if g["id"] not in history[-len(CATALOG):]] or CATALOG
    digest = hashlib.sha256(day.isoformat().encode()).digest()
    selected = pool[int.from_bytes(digest[:4], "big") % len(pool)]
    return {**selected, "seed": int.from_bytes(digest[4:8], "big"), "date": day.isoformat()}

def server_source(game):
    mode = game["id"]
    return """-- Generated MVP. All progress and rewards are server-authoritative.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Workspace = game:GetService("Workspace")
local MODE = """ + json.dumps(mode) + """
local SEED = """ + str(game["seed"]) + """
local event = Instance.new("RemoteEvent")
event.Name = "DailyGameStatus"; event.Parent = ReplicatedStorage
local world = Instance.new("Folder"); world.Name = "GeneratedWorld"; world.Parent = Workspace
local progress = {}
local function part(name, size, pos, color)
 local p=Instance.new("Part"); p.Name=name; p.Size=size; p.Position=pos
 p.Anchored=true; p.Color=color; p.Parent=world; return p
end
part("IslandGround",Vector3.new(160,4,160),Vector3.new(0,-3,0),Color3.fromRGB(70,120,90))
local spawn=Instance.new("SpawnLocation"); spawn.Size=Vector3.new(12,1,12)
spawn.Position=Vector3.new(0,1,0); spawn.Anchored=true; spawn.Neutral=true; spawn.Parent=world
local function notify(player,msg) event:FireClient(player,msg,progress[player] or 0) end
local function award(player,msg)
 progress[player]=(progress[player] or 0)+1
 local stats=player:FindFirstChild("leaderstats")
 if stats then stats.Progress.Value=progress[player] end
 notify(player,msg)
end
local function prompt(obj,action,callback)
 local p=Instance.new("ProximityPrompt"); p.ActionText=action; p.ObjectText=obj.Name
 p.HoldDuration=.4; p.MaxActivationDistance=12; p.Parent=obj
 p.Triggered:Connect(callback)
end
local function setup(player)
 progress[player]=0
 local stats=Instance.new("Folder"); stats.Name="leaderstats"; stats.Parent=player
 local value=Instance.new("IntValue"); value.Name="Progress"; value.Parent=stats
 player.CharacterAdded:Connect(function() task.wait(1); notify(player,"""" + game["objective"] + """") end)
end
Players.PlayerAdded:Connect(setup)
Players.PlayerRemoving:Connect(function(p) progress[p]=nil end)
if MODE == "crystal_miner" then
 for i=1,10 do
  local node=part("Crystal"..i,Vector3.new(5,7,5),Vector3.new((i-5)*13,2,(i%3)*15),Color3.fromRGB(90,210,235))
  node.Shape=Enum.PartType.Ball
  prompt(node,"Mine crystal",function(p)
   if node:GetAttribute("Mined") then return end
   node:SetAttribute("Mined",true); node.Transparency=1; node.CanCollide=false
   award(p,"Crystal mined!"); task.delay(10,function() if node.Parent then node:SetAttribute("Mined",false); node.Transparency=0; node.CanCollide=true end end)
  end)
 end
elseif MODE == "sky_courier" then
 local parcel=part("Parcel",Vector3.new(4,4,4),Vector3.new(-30,3,0),Color3.fromRGB(230,175,70))
 local beacon=part("DeliveryBeacon",Vector3.new(12,2,12),Vector3.new(30,0,0),Color3.fromRGB(75,190,230))
 local carrying={}
 prompt(parcel,"Collect parcel",function(p) if carrying[p] then return end; carrying[p]=true; parcel.Transparency=1; notify(p,"Parcel collected. Deliver it!") end)
 prompt(beacon,"Deliver parcel",function(p) if not carrying[p] then notify(p,"Collect the parcel first."); return end; carrying[p]=nil; award(p,"Delivery complete!"); parcel.Transparency=0 end)
elseif MODE == "relic_maze" or MODE == "dungeon_echo" then
 local needed=MODE=="relic_maze" and 3 or 5
 for i=1,needed do
  local relic=part("Relic"..i,Vector3.new(3,3,3),Vector3.new((i-3)*18,2,(i%2)*20),Color3.fromRGB(190,125,245))
  prompt(relic,"Collect relic",function(p) if relic:GetAttribute("Taken") then return end; relic:SetAttribute("Taken",true); relic.Transparency=1; relic.CanCollide=false; award(p,"Relic collected!") end)
 end
 local gate=part("ExitGate",Vector3.new(12,14,2),Vector3.new(0,5,50),Color3.fromRGB(180,75,65))
 prompt(gate,"Open exit",function(p) if (progress[p] or 0)<needed then notify(p,"Find more relics."); return end; gate.Color=Color3.fromRGB(70,210,120); notify(p,"Exit unlocked! Mission complete.") end)
elseif MODE == "garden_guard" then
 for i=1,6 do
  local plot=part("GardenPlot"..i,Vector3.new(10,1,10),Vector3.new((i-3.5)*15,0,20),Color3.fromRGB(110,75,50))
  prompt(plot,"Plant sprout",function(p) if plot:GetAttribute("Planted") then return end; plot:SetAttribute("Planted",true); local sprout=part("Sprout",Vector3.new(3,7,3),plot.Position+Vector3.new(0,4,0),Color3.fromRGB(80,190,95)); sprout.Shape=Enum.PartType.Ball; award(p,"Sprout planted!") end)
 end
elseif MODE == "tidal_rescue" then
 local dock=part("SafeDock",Vector3.new(18,2,18),Vector3.new(0,0,-40),Color3.fromRGB(80,160,220))
 for i=1,4 do
  local crew=part("CrewMember"..i,Vector3.new(4,6,4),Vector3.new((i-2.5)*24,2,35),Color3.fromRGB(235,190,120))
  prompt(crew,"Rescue crew",function(p) if crew:GetAttribute("Rescued") then return end; crew:SetAttribute("Rescued",true); crew.Transparency=1; crew.CanCollide=false; award(p,"Crew member rescued!") end)
 end
 prompt(dock,"Return to dock",function(p) if (progress[p] or 0)<4 then notify(p,"Rescue all four crew members first."); return end; notify(p,"All crew rescued. Mission complete!") end)
end
print("Generated game loaded. Seed: "..tostring(SEED))
"""

def client_source(game):
    return '''local Players=game:GetService("Players")
local ReplicatedStorage=game:GetService("ReplicatedStorage")
local event=ReplicatedStorage:WaitForChild("DailyGameStatus")
local gui=Instance.new("ScreenGui"); gui.Name="DailyGameHUD"; gui.ResetOnSpawn=false
gui.Parent=Players.LocalPlayer:WaitForChild("PlayerGui")
local panel=Instance.new("Frame"); panel.Size=UDim2.new(0,350,0,125)
panel.Position=UDim2.new(0,18,0,18); panel.BackgroundColor3=Color3.fromRGB(28,38,58); panel.Parent=gui
local title=Instance.new("TextLabel"); title.Size=UDim2.new(1,-20,0,36)
title.Position=UDim2.new(0,10,0,6); title.BackgroundTransparency=1
title.Text=''' + json.dumps(game["title"]) + '''; title.TextColor3=Color3.new(1,1,1)
title.TextSize=22; title.Font=Enum.Font.GothamBold; title.Parent=panel
local objective=Instance.new("TextLabel"); objective.Size=UDim2.new(1,-20,0,65)
objective.Position=UDim2.new(0,10,0,48); objective.BackgroundTransparency=1
objective.Text=''' + json.dumps(game["objective"]) + '''; objective.TextWrapped=true
objective.TextColor3=Color3.fromRGB(225,235,245); objective.TextSize=16; objective.Parent=panel
event.OnClientEvent:Connect(function(msg,count) objective.Text=tostring(msg).." | Progress: "..tostring(count or 0) end)
'''

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

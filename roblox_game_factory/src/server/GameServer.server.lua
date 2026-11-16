-- Critter Hatchers: Sky Isles. Server-authoritative prototype.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local DataStoreService = game:GetService("DataStoreService")
local Workspace = game:GetService("Workspace")

local Store = DataStoreService:GetDataStore("CritterHatchersSkyIsles_v1")
local EGG_COST, REBIRTH_COST, CLICK_COOLDOWN = 100, 5000, 0.35
local profiles, lastClick = {}, {}

local PETS = {
 {name="Cloud Bunny", rarity="Common", weight=55, multiplier=1.25},
 {name="Moss Turtle", rarity="Uncommon", weight=27, multiplier=1.6},
 {name="Ember Fox", rarity="Rare", weight=13, multiplier=2.2},
 {name="Star Whale", rarity="Epic", weight=4, multiplier=3.5},
 {name="Aurora Dragon", rarity="Legendary", weight=1, multiplier=6},
}

local function part(parent, name, size, pos, color, material)
 local p=Instance.new("Part"); p.Name=name; p.Size=size; p.Position=pos
 p.Anchored=true; p.Color=color; p.Material=material or Enum.Material.SmoothPlastic
 p.TopSurface=Enum.SurfaceType.Smooth; p.BottomSurface=Enum.SurfaceType.Smooth; p.Parent=parent
 return p
end

local function createWorld()
 if Workspace:FindFirstChild("CritterHatchersWorld") then return end
 local world=Instance.new("Folder"); world.Name="CritterHatchersWorld"; world.Parent=Workspace
 part(world,"FloatingIsland",Vector3.new(150,8,150),Vector3.new(0,-5,0),Color3.fromRGB(75,160,105),Enum.Material.Grass)
 part(world,"CentralPath",Vector3.new(18,.5,85),Vector3.new(0,-.7,-12),Color3.fromRGB(210,190,145),Enum.Material.Sand)
 part(world,"HatchPlatform",Vector3.new(28,2,24),Vector3.new(0,0,-35),Color3.fromRGB(120,105,190),Enum.Material.Slate)
 part(world,"EggPedestal",Vector3.new(9,5,9),Vector3.new(0,3.5,-35),Color3.fromRGB(255,205,95),Enum.Material.Neon)
 local egg=part(world,"StarterEgg",Vector3.new(5,7,5),Vector3.new(0,9,-35),Color3.fromRGB(245,245,255),Enum.Material.Glass)
 egg.Shape=Enum.PartType.Ball; egg.Transparency=.12
 local sign=part(world,"WelcomeSign",Vector3.new(24,10,1),Vector3.new(0,8,12),Color3.fromRGB(35,45,75))
 local gui=Instance.new("SurfaceGui"); gui.Face=Enum.NormalId.Front; gui.Parent=sign
 local label=Instance.new("TextLabel"); label.Size=UDim2.fromScale(1,1); label.BackgroundTransparency=1
 label.Text="CRITTER HATCHERS\nSKY ISLES\nClick to earn • Hatch companions"
 label.TextColor3=Color3.new(1,1,1); label.TextScaled=true; label.Font=Enum.Font.GothamBold; label.Parent=gui
 local spawn=Instance.new("SpawnLocation"); spawn.Name="SkyIslesSpawn"; spawn.Size=Vector3.new(12,1,12)
 spawn.Position=Vector3.new(0,1,25); spawn.Anchored=true; spawn.Neutral=true; spawn.Duration=0; spawn.Parent=world
 for i=1,8 do
  local a=math.pi*2/8*i
  local cloud=part(world,"CloudRock"..i,Vector3.new(16,5,16),Vector3.new(math.cos(a)*64,-9,math.sin(a)*64),Color3.fromRGB(225,235,250))
  cloud.Shape=Enum.PartType.Ball
 end
end

local remotes=ReplicatedStorage:FindFirstChild("CritterRemotes") or Instance.new("Folder")
remotes.Name="CritterRemotes"; remotes.Parent=ReplicatedStorage
local request=remotes:FindFirstChild("Request") or Instance.new("RemoteFunction")
request.Name="Request"; request.Parent=remotes

local function defaultProfile() return {coins=500,rebirths=0,inventory={},equipped=nil} end
local function petInfo(name)
 for _,pet in ipairs(PETS) do if pet.name==name then return pet end end
end
local function clean(raw)
 local d=defaultProfile()
 if type(raw)~="table" then return d end
 d.coins=math.max(0,math.floor(tonumber(raw.coins) or 500))
 d.rebirths=math.max(0,math.floor(tonumber(raw.rebirths) or 0))
 if type(raw.inventory)=="table" then
  for _,name in ipairs(raw.inventory) do
   if type(name)=="string" and petInfo(name) and #d.inventory<100 then table.insert(d.inventory,name) end
  end
 end
 if type(raw.equipped)=="string" and table.find(d.inventory,raw.equipped) then d.equipped=raw.equipped end
 return d
end
local function multiplier(d)
 local pet=d.equipped and petInfo(d.equipped)
 return (1+d.rebirths*.5)*(pet and pet.multiplier or 1)
end
local function state(d)
 return {coins=d.coins,rebirths=d.rebirths,inventory=table.clone(d.inventory),equipped=d.equipped,
  multiplier=multiplier(d),eggCost=EGG_COST,rebirthCost=REBIRTH_COST,pets=PETS}
end
local function sync(player,d)
 local stats=player:FindFirstChild("leaderstats")
 if stats then stats.Coins.Value=d.coins; stats.Rebirths.Value=d.rebirths end
end
local function save(player)
 local d=profiles[player]; if not d then return end
 local payload={coins=d.coins,rebirths=d.rebirths,inventory=d.inventory,equipped=d.equipped}
 local ok,err=pcall(function() Store:SetAsync("player_"..player.UserId,payload) end)
 if not ok then warn("Critter Hatchers save failed: "..tostring(err)) end
end
local function load(player)
 local ok,raw=pcall(function() return Store:GetAsync("player_"..player.UserId) end)
 local d=ok and clean(raw) or defaultProfile()
 profiles[player]=d
 if not ok then warn("DataStore unavailable; this session may not save.") end
 local stats=Instance.new("Folder"); stats.Name="leaderstats"; stats.Parent=player
 local coins=Instance.new("IntValue"); coins.Name="Coins"; coins.Value=d.coins; coins.Parent=stats
 local rebirths=Instance.new("IntValue"); rebirths.Name="Rebirths"; rebirths.Value=d.rebirths; rebirths.Parent=stats
end
local function rollPet()
 local total=0; for _,p in ipairs(PETS) do total+=p.weight end
 local roll=math.random(1,total); local cursor=0
 for _,p in ipairs(PETS) do cursor+=p.weight; if roll<=cursor then return p end end
 return PETS[1]
end

request.OnServerInvoke=function(player,action,arg)
 local d=profiles[player]
 if not d then return {ok=false,message="Your profile is loading."} end
 if action=="GetData" then return {ok=true,state=state(d)}
 elseif action=="Click" then
  local now=os.clock()
  if lastClick[player] and now-lastClick[player]<CLICK_COOLDOWN then return {ok=false,message="Slow down a little!"} end
  lastClick[player]=now
  local reward=math.max(1,math.floor(5*multiplier(d))); d.coins+=reward; sync(player,d)
  return {ok=true,state=state(d),message="+"..reward.." coins"}
 elseif action=="Hatch" then
  if d.coins<EGG_COST then return {ok=false,state=state(d),message="Not enough coins!"} end
  if #d.inventory>=100 then return {ok=false,state=state(d),message="Collection full."} end
  d.coins-=EGG_COST; local pet=rollPet(); table.insert(d.inventory,pet.name); d.equipped=pet.name; sync(player,d)
  return {ok=true,state=state(d),message="You hatched "..pet.rarity.." "..pet.name.."!"}
 elseif action=="Equip" then
  if type(arg)~="string" or not table.find(d.inventory,arg) or not petInfo(arg) then
   return {ok=false,state=state(d),message="That companion is not in your collection."}
  end
  d.equipped=arg; return {ok=true,state=state(d),message="Equipped "..arg.."!"}
 elseif action=="Rebirth" then
  if d.coins<REBIRTH_COST then return {ok=false,state=state(d),message="You need 5,000 coins to rebirth."} end
  d.coins=0; d.rebirths+=1; sync(player,d)
  return {ok=true,state=state(d),message="Rebirth complete! Permanent +0.5x base bonus."}
 end
 return {ok=false,message="Unknown request."}
end

createWorld()
Players.PlayerAdded:Connect(load)
Players.PlayerRemoving:Connect(function(player) save(player); profiles[player]=nil; lastClick[player]=nil end)
for _,player in ipairs(Players:GetPlayers()) do task.spawn(load,player) end
task.spawn(function()
 while true do task.wait(60); for player in pairs(profiles) do save(player) end end
end)
game:BindToClose(function() for player in pairs(profiles) do save(player) end; task.wait(2) end)

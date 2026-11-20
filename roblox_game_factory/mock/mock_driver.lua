local plr = makeInstance("Player"); plr.Name = "P1"; plr.Parent = Players
Players.PlayerAdded:Fire(plr)
local function find(name) for _, e in ipairs(prompts) do if e.obj.Name == name then return e.p end end end
local function fire(name) local p = find(name); assert(p, "no prompt named " .. name); p.Triggered:Fire(plr) end
local function wins() return plr:FindFirstChild("leaderstats").Wins.Value end
local function prog() return plr:FindFirstChild("leaderstats").Progress.Value end
local function play()
 if MODE == "crystal_miner" then for i = 1, 5 do fire("Crystal" .. i) end
 elseif MODE == "sky_courier" then for i = 1, 3 do fire("Parcel"); fire("DeliveryBeacon") end
 elseif MODE == "relic_maze" then for i = 1, 3 do fire("Relic" .. i) end; fire("ExitGate")
 elseif MODE == "dungeon_echo" then for i = 1, 5 do fire("Echo" .. i) end; fire("ExitGate")
 elseif MODE == "garden_guard" then for i = 1, 6 do fire("GardenPlot" .. i) end
 elseif MODE == "tidal_rescue" then for i = 1, 4 do fire("CrewMember" .. i) end; fire("SafeDock") end
end
if find("ExitGate") then fire("ExitGate"); assert(wins() == 0, MODE .. ": gate completed the round too early") end
if find("SafeDock") then fire("SafeDock"); assert(wins() == 0, MODE .. ": dock completed the round too early") end
play()
assert(wins() == 1, MODE .. ": expected 1 win, got " .. wins())
flushTasks()
assert(prog() == 0 and wins() == 1, MODE .. ": round did not reset")
play()
assert(wins() == 2, MODE .. ": second round was not winnable, wins=" .. wins())
print("PASS " .. MODE .. " (2 full rounds, early-exit blocked, reset works)")

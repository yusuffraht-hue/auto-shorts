-- Critter Hatchers: Sky Isles client interface. Server validates all game actions.
local Players=game:GetService("Players")
local ReplicatedStorage=game:GetService("ReplicatedStorage")
local player=Players.LocalPlayer
local request=ReplicatedStorage:WaitForChild("CritterRemotes"):WaitForChild("Request")

local gui=Instance.new("ScreenGui"); gui.Name="CritterHatchersUI"; gui.ResetOnSpawn=false
gui.Parent=player:WaitForChild("PlayerGui")
local function round(obj,r)
 local c=Instance.new("UICorner"); c.CornerRadius=UDim.new(0,r or 12); c.Parent=obj
end
local function label(parent,text,size,pos,fontSize)
 local l=Instance.new("TextLabel"); l.Size=size; l.Position=pos; l.BackgroundTransparency=1
 l.Text=text; l.TextColor3=Color3.new(1,1,1); l.TextSize=fontSize or 18
 l.Font=Enum.Font.GothamBold; l.TextWrapped=true; l.Parent=parent; return l
end
local panel=Instance.new("Frame"); panel.Name="MainPanel"; panel.Size=UDim2.new(0,310,0,390)
panel.Position=UDim2.new(0,18,.5,-195); panel.BackgroundColor3=Color3.fromRGB(35,43,73)
panel.BackgroundTransparency=.06; panel.Parent=gui; round(panel,18)
label(panel,"☁ CRITTER HATCHERS",UDim2.new(1,-20,0,42),UDim2.new(0,10,0,8),21)
local stats=label(panel,"Loading your island...",UDim2.new(1,-24,0,52),UDim2.new(0,12,0,50),17)

local function button(text,y,color)
 local b=Instance.new("TextButton"); b.Size=UDim2.new(1,-28,0,48); b.Position=UDim2.new(0,14,0,y)
 b.BackgroundColor3=color; b.TextColor3=Color3.new(1,1,1); b.Text=text; b.TextSize=17
 b.Font=Enum.Font.GothamBold; b.Parent=panel; round(b,12); return b
end
local clickButton=button("CLICK TO EARN COINS",112,Color3.fromRGB(55,155,115))
local hatchButton=button("HATCH EGG — 100 COINS",168,Color3.fromRGB(205,135,55))
local collectionButton=button("SHOW COLLECTION",224,Color3.fromRGB(105,105,190))
local rebirthButton=button("REBIRTH — 5,000 COINS",280,Color3.fromRGB(145,85,180))
local message=label(panel,"Welcome to Sky Isles!",UDim2.new(1,-24,0,38),UDim2.new(0,12,0,338),14)

local collection=Instance.new("Frame"); collection.Name="CollectionPanel"; collection.Size=UDim2.new(0,285,0,300)
collection.Position=UDim2.new(0,340,.5,-150); collection.BackgroundColor3=Color3.fromRGB(35,43,73)
collection.Visible=false; collection.Parent=gui; round(collection,16)
label(collection,"YOUR COMPANIONS",UDim2.new(1,-20,0,40),UDim2.new(0,10,0,8),18)
local list=Instance.new("ScrollingFrame"); list.Size=UDim2.new(1,-20,1,-60)
list.Position=UDim2.new(0,10,0,50); list.BackgroundTransparency=1; list.BorderSizePixel=0
list.ScrollBarThickness=6; list.CanvasSize=UDim2.new(0,0,0,0); list.Parent=collection
local layout=Instance.new("UIListLayout"); layout.Padding=UDim.new(0,6); layout.Parent=list

local state=nil
local busy=false
local function refreshCollection()
 for _,child in ipairs(list:GetChildren()) do
  if child:IsA("TextButton") or child:IsA("TextLabel") then child:Destroy() end
 end
 if not state or #state.inventory==0 then
  label(list,"No companions yet. Hatch your first egg!",UDim2.new(1,-8,0,48),UDim2.new(),14)
 else
  for _,petName in ipairs(state.inventory) do
   local b=Instance.new("TextButton"); b.Size=UDim2.new(1,-8,0,38)
   b.BackgroundColor3=petName==state.equipped and Color3.fromRGB(65,145,110) or Color3.fromRGB(65,75,115)
   b.TextColor3=Color3.new(1,1,1); b.TextSize=14; b.Font=Enum.Font.Gotham
   b.Text=(petName==state.equipped and "✓ " or "")..petName.."  •  Equip"; b.Parent=list; round(b,8)
   b.MouseButton1Click:Connect(function()
    if busy then return end; busy=true
    local ok,result=pcall(function() return request:InvokeServer("Equip",petName) end)
    if ok and result then
     state=result.state or state; message.Text=result.message or "Updated."
     stats.Text=string.format("Coins: %d   Rebirths: %d\nMultiplier: %.2fx",state.coins,state.rebirths,state.multiplier)
     refreshCollection()
    else message.Text="Could not equip. Try again." end
    busy=false
   end)
  end
 end
 task.defer(function() list.CanvasSize=UDim2.new(0,0,0,layout.AbsoluteContentSize.Y+8) end)
end
local function apply(result)
 if not result then return end
 if result.state then
  state=result.state
  stats.Text=string.format("Coins: %d   Rebirths: %d\nMultiplier: %.2fx",state.coins,state.rebirths,state.multiplier)
  refreshCollection()
 end
 if result.message then message.Text=result.message end
end
local function send(action)
 if busy then return end; busy=true
 local ok,result=pcall(function() return request:InvokeServer(action) end)
 if ok then apply(result) else message.Text="Connection issue. Please retry." end
 busy=false
end
clickButton.MouseButton1Click:Connect(function() send("Click") end)
hatchButton.MouseButton1Click:Connect(function() send("Hatch") end)
rebirthButton.MouseButton1Click:Connect(function() send("Rebirth") end)
collectionButton.MouseButton1Click:Connect(function()
 collection.Visible=not collection.Visible; if collection.Visible then refreshCollection() end
end)
task.spawn(function()
 for _=1,10 do
  local ok,result=pcall(function() return request:InvokeServer("GetData") end)
  if ok and result and result.ok then apply(result); message.Text="Welcome to Sky Isles! Hatch a companion."; return end
  task.wait(1)
 end
 message.Text="Could not load profile. Rejoin to retry."
end)

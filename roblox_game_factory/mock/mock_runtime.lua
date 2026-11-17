local function newSignal()
 local s = {h = {}}
 function s:Connect(f) table.insert(self.h, f); return {Disconnect = function() end} end
 function s:Fire(...) for _, f in ipairs(self.h) do f(...) end end
 return s
end
local queue = {}
task = {delay = function(t, f) table.insert(queue, f) end, wait = function() end}
function flushTasks() local q = queue; queue = {}; for _, f in ipairs(q) do f() end end
Vector3 = {new = function(x, y, z) return setmetatable({X = x or 0, Y = y or 0, Z = z or 0}, {__add = function(a, b) return Vector3.new(a.X + b.X, a.Y + b.Y, a.Z + b.Z) end}) end}
Color3 = {fromRGB = function(r, g, b) return {r, g, b} end, new = function(r, g, b) return {r, g, b} end}
UDim2 = {new = function(...) return {...} end}
Enum = setmetatable({}, {__index = function(t, k) return setmetatable({}, {__index = function(_, j) return k .. "." .. j end}) end})
local prompts = {}
local function makeInstance(cls)
 local o = {ClassName = cls, Name = cls, _children = {}, _attrs = {}, Triggered = newSignal(), CharacterAdded = newSignal(), Value = 0}
 return setmetatable(o, {
  __index = function(t, k)
   local c = rawget(t, "_children")[k]; if c then return c end
   if k == "SetAttribute" then return function(self, a, v) self._attrs[a] = v end end
   if k == "GetAttribute" then return function(self, a) return self._attrs[a] end end
   if k == "FindFirstChild" then return function(self, n) return self._children[n] end end
   if k == "Destroy" then return function(self) self.Parent = nil end end
   if k == "FireClient" then return function() end end
   return nil
  end,
  __newindex = function(t, k, v)
   if k == "Parent" then
    local old = rawget(t, "Parent")
    if old and old._children then old._children[t.Name] = nil end
    rawset(t, "Parent", v)
    if v and v._children then v._children[t.Name] = t end
    if cls == "ProximityPrompt" and v then table.insert(prompts, {obj = v, p = t}) end
   else rawset(t, k, v) end
  end})
end
Instance = {new = makeInstance}
local Players = {PlayerAdded = newSignal(), PlayerRemoving = newSignal(), _list = {}}
function Players:GetPlayers() return self._list end
local services = {Players = Players, ReplicatedStorage = makeInstance("ReplicatedStorage"), Workspace = makeInstance("Workspace")}
game = {GetService = function(self, n) return services[n] end}

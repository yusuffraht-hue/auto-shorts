"""Render blocky-town stills for the story video.
Usage: blender -b -noaudio -P blender/render_shots.py -- spec.json outdir"""
import bpy, math, random, sys, json, os, time

args = sys.argv[sys.argv.index("--") + 1:]
SPEC = json.load(open(args[0]))
OUT = args[1]
os.makedirs(OUT, exist_ok=True)
W, H = SPEC.get("width", 720), SPEC.get("height", 1280)

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.engine = "CYCLES"
scn.cycles.device = "CPU"
scn.cycles.samples = SPEC.get("samples", 32)
try:
    scn.cycles.use_denoising = True
except Exception:
    pass
scn.render.resolution_x, scn.render.resolution_y = W, H
scn.render.resolution_percentage = 100
scn.render.image_settings.file_format = "PNG"
scn.view_settings.view_transform = "Standard"
scn.view_settings.look = "None"

world = bpy.data.worlds.new("w")
scn.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
scn.collection.objects.link(sun)

_mats = {}


def M(rgb, rough=0.8, emit=0.0):
    key = (tuple(rgb), rough, emit)
    if key not in _mats:
        m = bpy.data.materials.new("m%d" % len(_mats))
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*rgb, 1)
        b.inputs["Roughness"].default_value = rough
        if emit > 0:
            b.inputs["Emission Color"].default_value = (*rgb, 1)
            b.inputs["Emission Strength"].default_value = emit
        _mats[key] = m
    return _mats[key]


def box(loc, dim, rgb, parent=None, rough=0.8, emit=0.0, rot=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    o = bpy.context.active_object
    o.scale = dim
    o.data.materials.append(M(rgb, rough, emit))
    if parent is not None:
        o.parent = parent
    o.location = loc
    if rot:
        o.rotation_euler = rot
    return o


def sphere(loc, r, rgb, emit=0.0, rough=0.8):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=r, location=loc)
    o = bpy.context.active_object
    o.data.materials.append(M(rgb, rough, emit))
    return o


def light(kind, loc, energy, color=(1, 1, 1), size=None):
    d = bpy.data.lights.new("l", kind)
    d.energy = energy
    d.color = color
    if size is not None:
        d.size = size
    o = bpy.data.objects.new("l", d)
    o.location = loc
    scn.collection.objects.link(o)
    return o


def tree(x, y, s=1.0):
    box((x, y, 1.0 * s), (0.4 * s, 0.4 * s, 2.0 * s), (0.4, 0.26, 0.15))
    sphere((x, y, 3.0 * s), 1.3 * s, (0.2, 0.55, 0.2))
    sphere((x, y, 4.0 * s), 0.9 * s, (0.25, 0.62, 0.25))


PALETTE = [(0.95, 0.8, 0.5), (0.6, 0.75, 0.95), (0.85, 0.6, 0.6),
           (0.7, 0.9, 0.7), (0.92, 0.92, 0.96), (0.8, 0.7, 0.9)]
LAMPS = []


def build_street(ox):
    rnd = random.Random(3)
    box((ox, 20, -0.25), (80, 170, 0.5), (0.35, 0.7, 0.35))
    box((ox, 20, 0.02), (8, 170, 0.1), (0.12, 0.12, 0.16))
    for s in (-1, 1):
        box((ox + s * 5.25, 20, 0.06), (2.5, 170, 0.2), (0.78, 0.78, 0.8))
    for y in range(-40, 100, 6):
        box((ox, y, 0.09), (0.25, 2.6, 0.03), (0.95, 0.85, 0.2))
    for side in (-1, 1):
        y = -34.0
        while y < 75:
            w, h, d = rnd.uniform(7, 11), rnd.uniform(9, 24), 9.0
            box((ox + side * (6.5 + d / 2), y + w / 2, h / 2), (d, w, h), rnd.choice(PALETTE))
            fx = ox + side * 6.5 - side * 0.05
            for fl in range(int(h // 3)):
                for k in range(int(w // 2.4)):
                    box((fx, y + 1.4 + k * 2.4, 2.2 + fl * 3), (0.12, 1.3, 1.6), (0.15, 0.27, 0.42))
            y += w + 0.6
        for yy in range(-30, 80, 11):
            tree(ox + side * 4.5, yy, 0.8)
        for yy in (-4, 10, 24, 38):
            x = ox + side * 4.2
            box((x, yy, 2.0), (0.15, 0.15, 4.0), (0.2, 0.2, 0.22))
            sphere((x, yy, 4.1), 0.3, (1.0, 0.85, 0.5), emit=6)
            LAMPS.append(light("POINT", (x, yy, 3.9), 1200, (1, 0.8, 0.5)))
    for (cx, cy), c in [((-2, 14), (0.9, 0.15, 0.15)), ((2, 26), (0.15, 0.4, 0.9)),
                        ((-2, 40), (0.95, 0.85, 0.2)), ((2, 54), (0.9, 0.9, 0.92))]:
        box((ox + cx, cy, 0.55), (1.8, 3.8, 0.9), c)
        box((ox + cx, cy - 0.2, 1.25), (1.6, 2.0, 0.7), (0.7, 0.85, 0.95))


def build_park(ox):
    rnd = random.Random(5)
    box((ox, 20, -0.25), (140, 140, 0.5), (0.35, 0.7, 0.3))
    box((ox, 14, 0.02), (3.2, 90, 0.06), (0.82, 0.72, 0.5))
    box((ox - 14, 20, 0.04), (12, 9, 0.06), (0.2, 0.5, 0.8), rough=0.1)
    for _ in range(70):
        x, y = ox + rnd.uniform(-45, 45), rnd.uniform(-4, 65)
        if abs(x - ox) > 4.5 and not (abs(x - (ox - 14)) < 8 and 14 < y < 26):
            tree(x, y, rnd.uniform(0.8, 1.3))
    for y in (2, 12, 22):
        for s in (-1, 1):
            bx = ox + s * 3.4
            box((bx, y, 0.5), (0.8, 2.2, 0.15), (0.45, 0.28, 0.14))
            box((bx + s * 0.35, y, 0.95), (0.15, 2.2, 0.8), (0.45, 0.28, 0.14))
            box((bx, y - 0.9, 0.25), (0.7, 0.12, 0.5), (0.2, 0.2, 0.2))
            box((bx, y + 0.9, 0.25), (0.7, 0.12, 0.5), (0.2, 0.2, 0.2))
    for k in range(9):
        box((ox + (k - 4) * 18, 80, 3), (17, 10, 6 + (k % 3) * 2.5), (0.3, 0.55, 0.38))
    for yy in (0, 16, 32):
        x = ox + 5.5
        box((x, yy, 2.0), (0.15, 0.15, 4.0), (0.2, 0.2, 0.22))
        sphere((x, yy, 4.1), 0.3, (1.0, 0.85, 0.5), emit=6)
        LAMPS.append(light("POINT", (x, yy, 3.9), 1200, (1, 0.8, 0.5)))


def room(ox, length=28, width=20, wall=(0.92, 0.9, 0.8), floor=(0.75, 0.6, 0.4)):
    cy = 3
    box((ox, cy, -0.05), (width, length, 0.1), floor)
    box((ox, cy + length / 2, 2.5), (width, 0.3, 5), wall)
    box((ox, cy - length / 2, 2.5), (width, 0.3, 5), wall)
    box((ox - width / 2, cy, 2.5), (0.3, length, 5), wall)
    box((ox + width / 2, cy, 2.5), (0.3, length, 5), wall)
    box((ox, cy, 5.05), (width, length, 0.1), (0.95, 0.95, 0.95))


def build_classroom(ox):
    room(ox)
    by = 16.7
    box((ox, by, 2.4), (8, 0.1, 2.2), (0.1, 0.25, 0.18))
    box((ox, by - 0.1, 1.2), (8.2, 0.3, 0.1), (0.5, 0.35, 0.2))
    box((ox + 2.5, by - 0.08, 2.4), (2.5, 0.02, 0.05), (0.95, 0.95, 0.95))
    for y in (0, 7, 14):
        box((ox - 9.8, y, 2.6), (0.1, 3, 2.2), (0.9, 0.95, 1.0), emit=3.0)
    for r in range(3):
        for x in (-7, -4.5, 4.5, 7):
            y = 9.5 + r * 2.4
            box((ox + x, y, 0.8), (1.6, 1.0, 0.1), (0.7, 0.5, 0.3))
            box((ox + x - 0.6, y, 0.4), (0.1, 0.8, 0.8), (0.3, 0.3, 0.33))
            box((ox + x + 0.6, y, 0.4), (0.1, 0.8, 0.8), (0.3, 0.3, 0.33))
            box((ox + x, y - 0.9, 0.5), (0.8, 0.7, 0.08), (0.2, 0.4, 0.8))
    light("AREA", (ox, 6, 4.8), 900, (1, 0.97, 0.9), size=9)
    light("AREA", (ox, 14, 4.8), 500, (1, 0.97, 0.9), size=7)


def build_house(ox):
    room(ox, length=26, width=16, wall=(0.95, 0.9, 0.78), floor=(0.55, 0.38, 0.22))
    box((ox + 3, 15.8, 2.6), (4, 0.1, 2.4), (0.9, 0.95, 1.0), emit=4.0)
    box((ox - 6.4, 10, 0.5), (2.4, 5, 1.0), (0.7, 0.2, 0.2))
    box((ox - 7.4, 10, 1.3), (0.4, 5, 1.6), (0.65, 0.18, 0.18))
    box((ox - 1, 12, 0.4), (3, 1.6, 0.8), (0.4, 0.26, 0.15))
    box((ox, 15.7, 1.7), (4, 0.2, 2.2), (0.05, 0.05, 0.07))
    box((ox, 8, 0.03), (6, 8, 0.04), (0.2, 0.3, 0.7))
    box((ox + 6, 13, 1.0), (0.12, 0.12, 2.0), (0.2, 0.2, 0.22))
    sphere((ox + 6, 13, 2.2), 0.35, (1.0, 0.9, 0.6), emit=8)
    light("POINT", (ox + 6, 13, 2.2), 400, (1, 0.85, 0.6))
    light("AREA", (ox, 6, 4.8), 700, (1, 0.95, 0.85), size=8)


ZONES = {"street": (0, build_street, False), "park": (300, build_park, False),
         "classroom": (600, build_classroom, True), "house": (900, build_house, True)}
FOCUS_Y = 5.0
for name in {s["setting"] for s in SPEC["shots"]}:
    ZONES[name][1](ZONES[name][0])

SKIN_DARK = (0.05, 0.05, 0.05)


def character(c, x, y, yaw, pose, emotion):
    u = 0.5
    made = []
    root = bpy.data.objects.new("char", None)
    scn.collection.objects.link(root)
    made.append(root)

    def part(loc, dim, rgb, parent=root, **kw):
        o = box(loc, dim, rgb, parent, **kw)
        made.append(o)
        return o

    shirt, pants, skin, hair = c["shirt"], c["pants"], c["skin"], c["hair"]
    part((0, 0, 3 * u), (2 * u, 1 * u, 2 * u), shirt)
    part((0, 0, 4.6 * u), (1.2 * u, 1.2 * u, 1.2 * u), skin)
    part((0, 0.05 * u, 5.3 * u), (1.3 * u, 1.3 * u, 0.4 * u), hair)
    part((0, 0.5 * u, 4.7 * u), (1.3 * u, 0.3 * u, 1.0 * u), hair)
    fy = -0.6 * u - 0.01
    for ex in (-0.28, 0.28):
        part((ex * u * 1.2, fy, 4.72 * u), (0.16 * u, 0.06 * u, 0.24 * u), SKIN_DARK)
    if emotion == "smile":
        part((0, fy, 4.32 * u), (0.5 * u, 0.06 * u, 0.09 * u), (0.3, 0.08, 0.08))
        for sx in (-1, 1):
            part((sx * 0.3 * u, fy, 4.4 * u), (0.1 * u, 0.06 * u, 0.1 * u), (0.3, 0.08, 0.08))
    elif emotion == "shock":
        part((0, fy, 4.3 * u), (0.22 * u, 0.06 * u, 0.3 * u), (0.2, 0.03, 0.03))
    elif emotion == "angry":
        part((0, fy, 4.3 * u), (0.5 * u, 0.06 * u, 0.08 * u), (0.2, 0.05, 0.05))
        for sx in (-1, 1):
            part((sx * 0.3 * u, fy, 4.98 * u), (0.38 * u, 0.06 * u, 0.09 * u), SKIN_DARK,
                 rot=(0, sx * 0.45, 0))
    else:
        part((0, fy, 4.3 * u), (0.4 * u, 0.06 * u, 0.07 * u), (0.3, 0.1, 0.1))
    joints = []
    for jx, jz, rgb in ((-1.5, 4, skin), (1.5, 4, skin), (-0.5, 2, pants), (0.5, 2, pants)):
        j = bpy.data.objects.new("j", None)
        j.parent = root
        j.location = (jx * u, 0, jz * u)
        scn.collection.objects.link(j)
        made.append(j)
        part((0, 0, -u), (1 * u, 1 * u, 2 * u), rgb, parent=j)
        joints.append(j)
    if pose == "point":
        joints[1].rotation_euler[0] = -1.5
    elif pose == "surprised":
        joints[0].rotation_euler[1] = 2.3
        joints[1].rotation_euler[1] = -2.3
    elif pose == "run":
        joints[0].rotation_euler[0], joints[1].rotation_euler[0] = 0.9, -0.9
        joints[2].rotation_euler[0], joints[3].rotation_euler[0] = -0.8, 0.8
    root.location = (x, y, 0)
    root.rotation_euler[2] = yaw
    return made


def add_prop(kind, fx, fy):
    made = []
    if kind == "orb":
        made.append(sphere((fx + 1.1, fy - 0.7, 1.9), 0.28, (0.4, 0.8, 1.0), emit=14))
        made.append(light("POINT", (fx + 1.1, fy - 0.8, 1.9), 120, (0.4, 0.8, 1.0)))
    elif kind == "key":
        made.append(box((fx + 1.0, fy - 0.7, 1.7), (0.1, 0.55, 0.1), (0.95, 0.75, 0.15), emit=1.5))
        made.append(box((fx + 1.0, fy - 1.0, 1.7), (0.1, 0.25, 0.25), (0.95, 0.75, 0.15), emit=1.5))
    elif kind == "book":
        made.append(box((fx + 1.0, fy - 0.7, 1.6), (0.8, 0.6, 0.15), (0.6, 0.15, 0.15), rot=(0.4, 0, 0.3)))
    elif kind == "letter":
        made.append(box((fx + 1.0, fy - 0.7, 1.7), (0.6, 0.05, 0.8), (0.95, 0.95, 0.9), rot=(0.2, 0, 0.2)))
    elif kind == "door":
        made.append(box((fx, fy + 3.5, 2.1), (3.2, 0.3, 4.2), (0.25, 0.15, 0.08)))
        made.append(box((fx, fy + 3.3, 2.0), (2.4, 0.1, 3.7), (0.6, 0.85, 1.0), emit=6))
        made.append(light("POINT", (fx, fy + 2.5, 2.0), 300, (0.6, 0.85, 1.0)))
    return made


PRESETS = {"wide": (14, 3.2, 1.6, 26), "medium": (6.5, 2.2, 1.7, 32), "closeup": (3.4, 2.1, 2.1, 38),
           "low": (7, 0.6, 2.2, 24), "over": (5.2, 2.7, 1.8, 30)}
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scn.collection.objects.link(cam)
scn.camera = cam
target = bpy.data.objects.new("target", None)
scn.collection.objects.link(target)
con = cam.constraints.new("TRACK_TO")
con.target = target
con.track_axis = "TRACK_NEGATIVE_Z"
con.up_axis = "UP_Y"


def set_time(kind, interior):
    if interior:
        bg.inputs[0].default_value = (0.6, 0.65, 0.78, 1)
        bg.inputs[1].default_value = 0.15
        sun.data.energy = 0
    elif kind == "night":
        bg.inputs[0].default_value = (0.04, 0.05, 0.12, 1)
        bg.inputs[1].default_value = 0.7
        sun.data.energy, sun.data.color = 0.5, (0.5, 0.6, 1.0)
        sun.rotation_euler = (math.radians(55), 0, math.radians(30))
    elif kind == "dusk":
        bg.inputs[0].default_value = (1.0, 0.55, 0.35, 1)
        bg.inputs[1].default_value = 0.9
        sun.data.energy, sun.data.color = 3.0, (1.0, 0.6, 0.35)
        sun.rotation_euler = (math.radians(80), math.radians(5), math.radians(25))
    else:
        bg.inputs[0].default_value = (0.55, 0.78, 1.0, 1)
        bg.inputs[1].default_value = 1.1
        sun.data.energy, sun.data.color = 4.0, (1, 1, 1)
        sun.rotation_euler = (math.radians(48), math.radians(8), math.radians(25))
    for l in LAMPS:
        l.hide_render = (kind == "day")


for shot in SPEC["shots"]:
    t0 = time.time()
    ox, _, interior = ZONES[shot["setting"]]
    fx, fy = ox, FOCUS_Y
    set_time(shot.get("time", "day"), interior)
    made = []
    for i, c in enumerate(shot["chars"]):
        if c["role"] == "hero":
            made += character(c, fx, fy, 0.0, shot.get("pose", "idle"), shot.get("emotion", "neutral"))
        else:
            side = 1 if i % 2 else -1
            x = fx + side * (2.6 + 0.9 * ((i - 1) // 2))
            made += character(c, x, fy + 0.6 * i, -side * 0.35, "idle", c.get("emotion", "neutral"))
    made += add_prop(shot.get("prop", "none"), fx, fy)
    dist, h, tz, lens = PRESETS[shot.get("camera", "medium")]
    rnd = random.Random(shot["id"] * 7 + 1)
    xo = 1.8 if shot.get("camera") == "over" else rnd.uniform(-1.2, 1.2)
    cam.location = (fx + xo, fy - dist, h)
    cam.data.lens = lens
    target.location = (fx, fy, tz)
    scn.render.filepath = os.path.join(OUT, "shot_%d.png" % shot["id"])
    bpy.ops.render.render(write_still=True)
    for o in made:
        bpy.data.objects.remove(o, do_unlink=True)
    print("SHOT", shot["id"], shot["setting"], shot.get("time"), shot.get("camera"),
          "%.1fs" % (time.time() - t0), flush=True)

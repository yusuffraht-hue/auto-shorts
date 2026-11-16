"""Proof of concept: procedural blocky 3D town street with walking characters, rendered headless.
Run: blender -b -noaudio -P blender/town.py -- OUTDIR"""
import bpy, math, random, sys

random.seed(11)
OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp/frames"
FPS, SECS = 12, 8
N = FPS * SECS

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.engine = "CYCLES"
scn.cycles.device = "CPU"
scn.cycles.samples = 24
try:
    scn.cycles.use_denoising = True
except Exception:
    pass
scn.render.resolution_x, scn.render.resolution_y = 540, 960
scn.render.fps = FPS
scn.view_settings.view_transform = "Standard"
scn.view_settings.look = "None"
scn.frame_start, scn.frame_end = 1, N
scn.render.image_settings.file_format = "PNG"
scn.render.filepath = OUT + "/f_"

world = bpy.data.worlds.new("w")
scn.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.55, 0.78, 1.0, 1)
bg.inputs[1].default_value = 1.1

sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 4.0
sun.rotation_euler = (math.radians(48), math.radians(8), math.radians(25))
scn.collection.objects.link(sun)

_mats = {}


def M(rgb, rough=0.8):
    if rgb not in _mats:
        m = bpy.data.materials.new("m%d" % len(_mats))
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*rgb, 1)
        b.inputs["Roughness"].default_value = rough
        _mats[rgb] = m
    return _mats[rgb]


def box(loc, dim, rgb, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    o = bpy.context.active_object
    o.scale = dim
    o.data.materials.append(M(rgb))
    if parent is not None:
        o.parent = parent
    o.location = loc
    return o


def lerp(a, b, t):
    return a + (b - a) * t


# ---- ground, road, sidewalks, lane dashes
box((0, 20, -0.25), (80, 170, 0.5), (0.35, 0.7, 0.35))
box((0, 20, 0.02), (8, 170, 0.1), (0.12, 0.12, 0.16))
for s in (-1, 1):
    box((s * 5.25, 20, 0.06), (2.5, 170, 0.2), (0.78, 0.78, 0.8))
for y in range(-40, 100, 6):
    box((0, y, 0.09), (0.25, 2.6, 0.03), (0.95, 0.85, 0.2))

# ---- buildings with windows
palette = [(0.95, 0.8, 0.5), (0.6, 0.75, 0.95), (0.85, 0.6, 0.6),
           (0.7, 0.9, 0.7), (0.92, 0.92, 0.96), (0.8, 0.7, 0.9)]
for side in (-1, 1):
    y = -34.0
    while y < 75:
        w, h, d = random.uniform(7, 11), random.uniform(9, 24), 9.0
        box((side * (6.5 + d / 2), y + w / 2, h / 2), (d, w, h), random.choice(palette))
        fx = side * 6.5 - side * 0.05
        for fl in range(int(h // 3)):
            for k in range(int(w // 2.4)):
                box((fx, y + 1.4 + k * 2.4, 2.2 + fl * 3), (0.12, 1.3, 1.6), (0.15, 0.27, 0.42))
        y += w + 0.6

# ---- trees and cars
for side in (-1, 1):
    for y in range(-30, 80, 11):
        x = side * 4.5
        box((x, y, 1.0), (0.4, 0.4, 2.0), (0.4, 0.26, 0.15))
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.3, location=(x, y, 3.0))
        t = bpy.context.active_object
        t.data.materials.append(M((0.2, 0.55, 0.2)))
cars = [((-2, 8), (0.9, 0.15, 0.15)), ((2, 20), (0.15, 0.4, 0.9)),
        ((-2, 36), (0.95, 0.85, 0.2)), ((2, 50), (0.9, 0.9, 0.92))]
for (x, y), c in cars:
    box((x, y, 0.55), (1.8, 3.8, 0.9), c)
    box((x, y - 0.2, 1.25), (1.6, 2.0, 0.7), (0.7, 0.85, 0.95))


# ---- blocky characters with a walk cycle
def character(shirt, pants, skin, x, y0, y1, face_cam=True):
    u = 0.5
    root = bpy.data.objects.new("char", None)
    scn.collection.objects.link(root)
    if not face_cam:
        root.rotation_euler[2] = math.pi
    box((0, 0, 3 * u), (2 * u, 1 * u, 2 * u), shirt, root)
    head = box((0, 0, 4.6 * u), (1.2 * u, 1.2 * u, 1.2 * u), skin, root)
    for ex in (-0.25, 0.25):
        box((ex * u * 1.2, -0.6 * u - 0.01, 4.7 * u), (0.16 * u, 0.06 * u, 0.24 * u), (0.05, 0.05, 0.05), root)
    box((0, -0.6 * u - 0.01, 4.35 * u), (0.5 * u, 0.06 * u, 0.1 * u), (0.3, 0.1, 0.1), root)
    joints = []
    for jx, jz, rgb, name in ((-1.5, 4, skin, "arm"), (1.5, 4, skin, "arm"),
                              (-0.5, 2, pants, "leg"), (0.5, 2, pants, "leg")):
        j = bpy.data.objects.new("joint", None)
        j.parent = root
        j.location = (jx * u, 0, jz * u)
        scn.collection.objects.link(j)
        box((0, 0, -u), (1 * u, 1 * u, 2 * u), rgb, j)
        joints.append(j)
    for f in range(1, N + 1):
        k = (f - 1) / (N - 1)
        ph = (f - 1) / FPS * 2 * math.pi * 1.6
        sw = math.sin(ph) * 0.75
        for j, sgn in zip(joints, (1, -1, -1, 1)):
            j.rotation_euler[0] = sw * sgn
            j.keyframe_insert("rotation_euler", index=0, frame=f)
        root.location = (x, lerp(y0, y1, k), 0)
        root.keyframe_insert("location", frame=f)


character((0.9, 0.2, 0.2), (0.2, 0.25, 0.6), (0.95, 0.8, 0.6), -5.2, 16, -6)
character((0.2, 0.6, 0.9), (0.15, 0.15, 0.2), (0.7, 0.5, 0.35), 5.2, 12, -8)
character((0.95, 0.8, 0.2), (0.3, 0.3, 0.3), (0.9, 0.7, 0.55), 0.0, -4, 26, face_cam=False)

# ---- camera dolly
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.lens = 26
scn.collection.objects.link(cam)
scn.camera = cam
for f in range(1, N + 1):
    k = (f - 1) / (N - 1)
    cam.location = (lerp(-1.0, 1.0, k), lerp(-24, -5, k), lerp(2.6, 2.1, k))
    cam.rotation_euler = (math.radians(88), 0, 0)
    cam.keyframe_insert("location", frame=f)
    cam.keyframe_insert("rotation_euler", frame=f)

bpy.ops.render.render(animation=True)

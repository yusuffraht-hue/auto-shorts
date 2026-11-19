"""Opt-in reusable In This Town set. No upload, network, or production hooks.

Run: blender -b -t 2 --python scripts/reusable_town.py -- --output /tmp/town.png
The script creates an original low-poly set in memory and renders one test still.
"""
import argparse
import pathlib
import sys

LOCATIONS = ("school", "square", "park")
CHARACTERS = ("mira", "kai", "noor")
PALETTE = {
    "ground": (0.24, 0.52, 0.38, 1),
    "road": (0.12, 0.17, 0.23, 1),
    "school": (0.94, 0.64, 0.30, 1),
    "shop": (0.30, 0.66, 0.84, 1),
    "roof": (0.36, 0.22, 0.38, 1),
    "tree": (0.17, 0.45, 0.26, 1),
    "skin": (0.75, 0.51, 0.36, 1),
}


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Render a reusable original town test still")
    parser.add_argument("--output", required=True)
    parser.add_argument("--location", choices=LOCATIONS, default="square")
    parser.add_argument("--frame", type=int, default=1)
    args = parser.parse_args(argv)
    if not 1 <= args.frame <= 250:
        parser.error("--frame must be between 1 and 250")
    output = pathlib.Path(args.output).expanduser().resolve()
    if output.suffix.lower() != ".png":
        parser.error("--output must be a PNG path")
    return args, output


def build_and_render(args, output):
    import bpy
    from mathutils import Vector

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    def material(name, color):
        mat = bpy.data.materials.new(name)
        mat.diffuse_color = color
        return mat

    mats = {key: material(key, value) for key, value in PALETTE.items()}

    def cube(name, xyz, scale, mat):
        bpy.ops.mesh.primitive_cube_add(size=1, location=xyz)
        obj = bpy.context.object
        obj.name = name
        obj.dimensions = scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.data.materials.append(mats[mat])
        return obj

    cube("town_ground", (0, 0, -0.15), (34, 34, 0.3), "ground")
    cube("main_road", (0, 0, 0.015), (4, 33, 0.06), "road")
    cube("cross_street", (0, 0, 0.02), (33, 4, 0.06), "road")
    for name, x, y, color in (
        ("school", -9, 8, "school"),
        ("library", 9, 8, "shop"),
        ("bakery", -9, -8, "shop"),
        ("home", 9, -8, "school"),
    ):
        cube(name, (x, y, 2), (6, 5, 4), color)
        cube(name + "_roof", (x, y, 4.4), (6.5, 5.5, 0.8), "roof")
        cube(name + "_door", (x, y - 2.54, 0.9), (1.2, 0.12, 1.8), "road")
    for i, (x, y) in enumerate(((-14, 12), (14, 12), (-14, -12), (14, -12))):
        cube("tree_trunk_" + str(i), (x, y, 1.1), (0.7, 0.7, 2.2), "roof")
        cube("tree_canopy_" + str(i), (x, y, 3.2), (2.8, 2.8, 2.8), "tree")
    for i, (name, x, y) in enumerate((("mira", -2.5, -3.5), ("kai", 0, -3.5), ("noor", 2.5, -3.5))):
        cube(name + "_body", (x, y, 1.0), (0.8, 0.55, 1.3), "shop" if i == 1 else "roof")
        cube(name + "_head", (x, y, 1.95), (0.75, 0.7, 0.7), "skin")

    targets = {"square": (0, 0, 0), "school": (-9, 8, 1), "park": (-13, 12, 0)}
    target = Vector(targets[args.location])
    bpy.ops.object.camera_add(location=target + Vector((17, -23, 20)))
    camera = bpy.context.object
    direction = target - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 27
    bpy.context.scene.camera = camera
    bpy.ops.object.light_add(type="AREA", location=(0, -3, 19))
    bpy.context.object.data.energy = 3200
    bpy.context.object.data.shape = "DISK"
    bpy.context.object.data.size = 16

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT" if bpy.app.version >= (4, 2, 0) else "BLENDER_EEVEE"
    scene.render.resolution_x = 540
    scene.render.resolution_y = 960
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(output)
    scene.frame_set(args.frame)
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    arguments = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    options, destination = parse_args(arguments)
    build_and_render(options, destination)

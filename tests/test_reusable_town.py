"""Offline checks for the opt-in town scene (Blender not required)."""
import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "reusable_town.py"


class ReusableTownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        # Importing the file is safe because bpy is only imported during rendering.
        import importlib.util
        spec = importlib.util.spec_from_file_location("reusable_town", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.world = module
        cls.tree = tree

    def test_all_three_locations(self):
        self.assertEqual(set(self.world.LOCATIONS), {"school", "square", "park"})

    def test_cast_is_stable(self):
        self.assertEqual(self.world.CHARACTERS, ("mira", "kai", "noor"))

    def test_png_required(self):
        with self.assertRaises(SystemExit):
            self.world.parse_args(["--output", "video.mp4"])

    def test_frame_bounded(self):
        for frame in ("0", "251"):
            with self.subTest(frame=frame), self.assertRaises(SystemExit):
                self.world.parse_args(["--output", "test.png", "--frame", frame])

    def test_valid_arguments(self):
        args, output = self.world.parse_args(
            ["--output", "test.png", "--location", "school", "--frame", "20"]
        )
        self.assertEqual(args.location, "school")
        self.assertEqual(args.frame, 20)
        self.assertEqual(output.suffix, ".png")

    def test_blender_is_not_imported_at_module_level(self):
        imports = [n for n in self.tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertFalse(any(
            alias.name == "bpy"
            for node in imports
            for alias in (node.names if isinstance(node, ast.Import) else [])
        ))


if __name__ == "__main__":
    unittest.main()

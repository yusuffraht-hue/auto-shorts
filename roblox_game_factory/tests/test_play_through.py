import importlib.util
import os
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


factory = load("daily_factory", "daily_factory.py")
gate = load("check_game", "check_game.py")
HAVE_LUAU = all(shutil.which(t, path=os.environ.get("LUAU_DIR") or None) for t in ("luau", "luau-analyze"))


@unittest.skipUnless(HAVE_LUAU, "luau tools not installed (set LUAU_DIR)")
class PlayThroughTests(unittest.TestCase):
    def test_every_archetype_is_playable_for_two_rounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            for offset in range(len(factory.CATALOG)):
                day = date.fromordinal(date(2026, 11, 16).toordinal() + offset)
                result = factory.generate(Path(tmp), day)
                problems = gate.check(result["path"])
                self.assertEqual(problems, [], result["title"])


if __name__ == "__main__":
    unittest.main()

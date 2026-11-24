import json
import tempfile
import unittest
from pathlib import Path
from editorial import select_topic

class EditorialTests(unittest.TestCase):
    def test_selection(self):
        base = dict(id="a", work="Any title", topic="World rules", facts="Reviewed notes",
                    source="https://example.org/source", reviewed=True, visual_complexity="low")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "topics.json"
            p.write_text(json.dumps([base, dict(base, id="b", reviewed=False),
                                     dict(base, id="c", visual_complexity="high")]))
            self.assertEqual(select_topic({}, path=p)["id"], "a")
            with self.assertRaises(RuntimeError):
                select_topic({"episodes": [{"topic_id": "a"}]}, path=p)
            with self.assertRaises(RuntimeError):
                select_topic({}, requested="Other", path=p)
            with self.assertRaises(RuntimeError):
                select_topic({}, avoid=["Any title"], path=p)

if __name__ == "__main__":
    unittest.main()

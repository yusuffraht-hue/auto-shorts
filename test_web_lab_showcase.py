import hashlib
import json
import unittest
from web_lab_showcase import discover, SOURCE, SITE

class ShowcaseTests(unittest.TestCase):
    def test_discovery(self):
        html = b"<html>demo</html>"
        url = SITE + "demo/"
        data = {SOURCE: json.dumps([{"name":"demo","type":"dir"},{"name":"../bad","type":"dir"}]).encode(),
                url+"index.html":html,
                url+"release.json":json.dumps({"app":"demo","sha256":hashlib.sha256(html).hexdigest()}).encode()}
        self.assertEqual(discover(data.__getitem__)[0]["app"], "demo")
        self.assertEqual(discover(data.__getitem__, promoted=["demo"]), [])
        data[url+"index.html"] = b"changed"
        self.assertEqual(discover(data.__getitem__), [])

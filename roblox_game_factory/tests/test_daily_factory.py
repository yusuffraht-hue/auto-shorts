import importlib.util, json, tempfile, unittest
from datetime import date
from pathlib import Path
MODULE=Path(__file__).resolve().parents[1]/"daily_factory.py"
spec=importlib.util.spec_from_file_location("daily_factory",MODULE)
factory=importlib.util.module_from_spec(spec); spec.loader.exec_module(factory)

class FactoryTests(unittest.TestCase):
 def test_rotates_without_repeating_until_catalog_exhausted(self):
  day=date(2026,11,16); seen=[]
  for offset in range(len(factory.CATALOG)):
   game=factory.choose_game(date.fromordinal(day.toordinal()+offset),seen)
   self.assertNotIn(game["id"],seen); seen.append(game["id"])
  self.assertEqual(len(seen),len(factory.CATALOG))
 def test_builds_rojo_project_and_test_plan(self):
  with tempfile.TemporaryDirectory() as tmp:
   result=factory.generate(Path(tmp),date(2026,11,16)); root=Path(result["path"])
   project=json.loads((root/"default.project.json").read_text())
   self.assertIn("ServerScriptService",project["tree"])
   self.assertTrue((root/"src/server/GameServer.server.lua").is_file())
   self.assertTrue((root/"src/client/GameHUD.client.lua").is_file())
   self.assertTrue((root/"TEST_PLAN.md").is_file())
 def test_client_never_awards_rewards(self):
  for game in factory.CATALOG:
   self.assertNotIn("FireServer",factory.client_source(game))
   self.assertIn("Triggered:Connect",factory.server_source(game))
 def test_deterministic_per_date(self):
  d=date(2026,11,16); self.assertEqual(factory.choose_game(d),factory.choose_game(d))

if __name__=="__main__": unittest.main()

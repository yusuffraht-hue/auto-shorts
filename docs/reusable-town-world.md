# In This Town: reusable 3D world experiment

This is an **opt-in prototype**, not a production renderer or a complete animated episode. It builds an original, stylized blocky town in Blender from reusable geometry: school, library, bakery, home, streets, trees, and three simple characters (Mira, Kai, Noor). Three fixed camera targets are available: square, school, park.

## Local render (no upload or network calls)

Requires a locally installed Blender 4.x and CPU/GPU resources. This is **not** invoked by any GitHub Actions schedule.

```bash
blender -b -t 2 --python scripts/reusable_town.py -- --output /tmp/town.png --location square
```

Offline unit checks (no Blender needed):

```bash
python -m unittest discover -s tests -p 'test_reusable_town.py' -v
python -m py_compile scripts/reusable_town.py tests/test_reusable_town.py
```

The renderer produces **one still PNG**, not motion, narration, a Short, or a publishable episode. Scene geometry is deterministic and can be reused. It does not modify `generate.py`, YouTube upload behavior, the two series' histories, or scheduled workflows. All existing videos remain on their current pipeline.

## Experimental expansion gates

Before using this for daily Shorts, inspect a real render for legibility, lighting, visual quality and character continuity. Benchmark CPU render time and free runner resource use. Later add shot descriptions and controlled character motion with a schema validator and offline tests. Avoid external Roblox models, copied assets, or recognizable copyrighted characters. Keep Anime & Novel Stories separate.

No production cutover or automated video/upload workflow is authorized by this experiment.

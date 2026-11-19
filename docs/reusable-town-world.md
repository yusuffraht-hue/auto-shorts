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

## Episode shot-plan contract (offline)

`scripts/town_shots.py` validates JSON instructions like `examples/town-episode.json`.
It accepts only the original town series, known characters, locations, camera framings,
and a fixed action vocabulary. It rejects unknown fields (including commands), invalid
frame counts, more than 12 shots, and more than 1,800 total frames. This prevents a
story model from turning arbitrary text into execution instructions.

To validate an episode locally without Blender:

```bash
python -c "import sys; sys.path.insert(0, 'scripts'); from town_shots import read_plan; print(read_plan('examples/town-episode.json'))"
python -m unittest discover -s tests -p 'test_town_shots.py' -v
```

**Limit:** shot plans are validated data only; they are not yet wired to
Blender animation, rendering, narration or publishing. The `walk`, `wave`,
`point`, and `surprised` labels are a future animation contract, not
implemented motions. Do not advertise an animated episode until a real render
has been generated and reviewed.

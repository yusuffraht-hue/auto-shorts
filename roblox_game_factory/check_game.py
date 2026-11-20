#!/usr/bin/env python3
"""Quality gate for generated games: Luau analysis plus a simulated play-through.

Needs the free `luau` and `luau-analyze` binaries (CI downloads them). Roblox's own globals
(Vector3, Enum, task...) are unknown to the stock analyzer, so only other problems are reported."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def tool(name):
    base = os.environ.get("LUAU_DIR", ".")
    return str(Path(base) / name)


def check(game_dir):
    game_dir = Path(game_dir)
    server = game_dir / "src/server/GameServer.server.lua"
    client = game_dir / "src/client/GameHUD.client.lua"
    problems = []
    out = subprocess.run([tool("luau-analyze"), str(server), str(client)], capture_output=True, text=True)
    for line in (out.stdout + out.stderr).splitlines():
        if line.strip() and "Unknown global" not in line:
            problems.append(line.strip())
    sim = ((HERE / "mock/mock_runtime.lua").read_text() + "\n" + server.read_text()
           + "\n" + (HERE / "mock/mock_driver.lua").read_text())
    with tempfile.NamedTemporaryFile("w", suffix=".lua", delete=False) as handle:
        handle.write(sim)
        path = handle.name
    run = subprocess.run([tool("luau"), path], capture_output=True, text=True)
    os.unlink(path)
    if run.returncode != 0:
        problems.append("play-through failed: " + (run.stdout + run.stderr).strip()[-400:])
    return problems


def main():
    root = Path(sys.argv[1])
    folders = sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else []
    if not folders:
        print("no generated games found in", root)
        return 1
    failed = False
    for folder in folders:
        problems = check(folder)
        print(("FAIL " if problems else "PASS ") + folder.name)
        for problem in problems:
            print("   ", problem)
        failed = failed or bool(problems)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

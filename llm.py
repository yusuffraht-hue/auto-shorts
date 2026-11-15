"""LLM helper. Returns a clean JSON string. Tries GitHub Models, then free Pollinations text."""
import json, os, time, requests

GH = os.environ.get("GITHUB_TOKEN", "")
TRIES = [
    ("https://models.github.ai/inference/chat/completions",
     {"Authorization": f"Bearer {GH}", "Accept-Encoding": "identity",
      "Content-Type": "application/json"},
     ["openai/gpt-4o-mini"], 1),
    ("https://text.pollinations.ai/openai",
     {"Content-Type": "application/json"},
     ["openai"], 4),
]


def _clean_json(out):
    a, b = out.find("{"), out.rfind("}")
    obj = json.loads(out[a:b + 1], strict=False)
    assert isinstance(obj.get("scenes"), list) and len(obj["scenes"]) >= 3
    for s in obj["scenes"]:
        assert s.get("line") and s.get("image_prompt")
    obj.setdefault("title", "In this world...")
    obj.setdefault("description", "")
    obj.setdefault("tags", [])
    return json.dumps(obj)


def call_llm(prompt):
    for url, headers, models, attempts in TRIES:
        for model in models:
            for _ in range(attempts):
                try:
                    r = requests.post(url, headers=headers, timeout=120, json={
                        "model": model, "temperature": 1.0, "max_tokens": 1500,
                        "messages": [{"role": "user", "content": prompt}]})
                    print("llm:", url.split("/")[2], model, r.status_code, repr(r.content[:80]))
                    if r.status_code != 200 or not r.content.strip():
                        break
                    out = r.json()["choices"][0]["message"]["content"] or ""
                    try:
                        return _clean_json(out)
                    except Exception as e:
                        print("llm bad json:", repr(e), repr(out[:600]))
                except Exception as e:
                    print("llm error:", url.split("/")[2], model, repr(e))
                    break
                time.sleep(3)
    raise RuntimeError("No LLM endpoint returned a usable script (see 'llm' lines above)")

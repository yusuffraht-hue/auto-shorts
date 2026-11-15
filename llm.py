"""LLM helper. Returns a clean JSON string. Tries GitHub Models, then free Pollinations text."""
import json, os, random, re, time, requests

GH = os.environ.get("GITHUB_TOKEN", "")
TRIES = [
    ("https://models.github.ai/inference/chat/completions",
     {"Authorization": f"Bearer {GH}", "Accept-Encoding": "identity",
      "Content-Type": "application/json"},
     ["openai/gpt-4o-mini"], 1),
    ("https://text.pollinations.ai/openai",
     {"Content-Type": "application/json"},
     ["openai-fast"], 8),
]
SUFFIX = ("\nUse plain ASCII only: straight quotes, no curly quotes, no em-dashes, "
          "no double quotes inside text values. Output raw JSON only.")


def _ascii(s):
    try:  # undo UTF-8 text that was decoded as latin-1/cp1252
        s = s.encode("cp1252").decode("utf-8")
    except Exception:
        pass
    for a, b in (("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"'),
                 ("\u2013", "-"), ("\u2014", "-"), ("\u2026", "...")):
        s = s.replace(a, b)
    return s.encode("ascii", "ignore").decode()


def _lenient(out):
    """Regex fallback for almost-JSON with stray quotes."""
    scenes = re.findall(
        r'"line"\s*:\s*"(.*?)"\s*,\s*"image_prompt"\s*:\s*"(.*?)"\s*\}', out, re.S)
    if len(scenes) < 3:
        raise ValueError("could not recover scenes")
    t = re.search(r'"title"\s*:\s*"(.*?)"\s*,\s*"description"', out, re.S)
    d = re.search(r'"description"\s*:\s*"(.*?)"\s*,\s*"tags"', out, re.S)
    h = re.search(r'"hero"\s*:\s*"(.*?)"\s*,\s*"scenes"', out, re.S)
    tags = re.findall(r'"([A-Za-z0-9 #_-]{2,30})"', (re.search(r'"tags"\s*:\s*\[(.*?)\]', out, re.S) or [None, ""])[1])
    return {"title": t.group(1) if t else "In this town...",
            "description": d.group(1) if d else "", "tags": tags,
            "hero": h.group(1) if h else "",
            "scenes": [{"line": a.replace('\\"', '"'), "image_prompt": b} for a, b in scenes]}


def _clean_json(out):
    out = _ascii(out)
    a, b = out.find("{"), out.rfind("}")
    body = out[a:b + 1]
    try:
        obj = json.loads(body, strict=False)
    except Exception:
        obj = _lenient(body)
    assert isinstance(obj.get("scenes"), list) and len(obj["scenes"]) >= 3
    for s in obj["scenes"]:
        assert s.get("line") and s.get("image_prompt")
    obj.setdefault("title", "In this town...")
    obj.setdefault("description", "")
    obj.setdefault("tags", [])
    return json.dumps(obj)


def call_llm(prompt):
    for url, headers, models, attempts in TRIES:
        for model in models:
            for _ in range(attempts):
                nonce = f"\n(variation id: {random.randint(10**6, 10**9)})"
                try:
                    r = requests.post(url, headers=headers, timeout=180, json={
                        "model": model, "temperature": 1.0, "max_tokens": 6000,
                        "seed": random.randint(1, 10**8),
                        "messages": [{"role": "user", "content": prompt + SUFFIX + nonce}]})
                    print("llm:", url.split("/")[2], model, r.status_code, repr(r.content[:200]))
                    if r.status_code != 200 or not r.content.strip():
                        if "github" in url:
                            break
                        m = re.search(r"Retry after (\d+)s", r.text)
                        time.sleep(int(m.group(1)) + 3 if m else 20)
                        continue
                    out = r.json()["choices"][0]["message"]["content"] or ""
                    try:
                        return _clean_json(out)
                    except Exception as e:
                        print("llm bad json:", repr(e), repr(out[:300]))
                except Exception as e:
                    print("llm error:", url.split("/")[2], model, repr(e))
                    if "github" in url:
                        break
                    continue
                time.sleep(3)
    raise RuntimeError("No LLM endpoint returned a usable script (see 'llm' lines above)")

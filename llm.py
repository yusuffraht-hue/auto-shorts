"""LLM helper. Returns a clean JSON string.
Order: Gemini (free key) -> Groq (free key) -> GitHub Models -> Pollinations (free, weak)."""
import json, os, random, re, time, requests

GH = os.environ.get("GITHUB_TOKEN", "")
GEMINI = os.environ.get("GEMINI_API_KEY", "").strip()
GROQ = os.environ.get("GROQ_API_KEY", "").strip()
MIN_SCENES = 6
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
    if len(scenes) < MIN_SCENES:
        raise ValueError("could not recover scenes")
    t = re.search(r'"title"\s*:\s*"(.*?)"\s*,\s*"description"', out, re.S)
    d = re.search(r'"description"\s*:\s*"(.*?)"\s*,\s*"tags"', out, re.S)
    h = re.search(r'"hero"\s*:\s*"(.*?)"\s*,\s*"scenes"', out, re.S)
    tags = re.findall(r'"([A-Za-z0-9 #_-]{2,30})"',
                      (re.search(r'"tags"\s*:\s*\[(.*?)\]', out, re.S) or [None, ""])[1])
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
    assert isinstance(obj.get("scenes"), list) and len(obj["scenes"]) >= MIN_SCENES, "too few scenes"
    for s in obj["scenes"]:
        assert s.get("line") and s.get("image_prompt")
    obj.setdefault("title", "In this town...")
    obj.setdefault("description", "")
    obj.setdefault("tags", [])
    return json.dumps(obj)


def _gemini(prompt):
    for model in ("gemini-2.5-flash", "gemini-2.0-flash"):
        cfg = {"temperature": 1.0, "maxOutputTokens": 8000,
               "responseMimeType": "application/json"}
        if "2.5" in model:
            cfg["thinkingConfig"] = {"thinkingBudget": 0}
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": GEMINI, "Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": cfg},
            timeout=120)
        print("llm: gemini", model, r.status_code, repr(r.text[:120]))
        if r.status_code == 200:
            yield r.json()["candidates"][0]["content"]["parts"][0]["text"]
        elif r.status_code == 429:
            time.sleep(20)


def _groq(prompt):
    for model in ("llama-3.3-70b-versatile",):
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ}", "Content-Type": "application/json"},
            json={"model": model, "temperature": 1.0, "max_tokens": 4000,
                  "response_format": {"type": "json_object"},
                  "messages": [{"role": "user", "content": prompt}]}, timeout=120)
        print("llm: groq", model, r.status_code, repr(r.text[:120]))
        if r.status_code == 200:
            yield r.json()["choices"][0]["message"]["content"]
        elif r.status_code == 429:
            time.sleep(20)


def _github(prompt):
    r = requests.post(
        "https://models.github.ai/inference/chat/completions",
        headers={"Authorization": f"Bearer {GH}", "Accept-Encoding": "identity",
                 "Content-Type": "application/json"},
        json={"model": "openai/gpt-4o-mini", "max_tokens": 4000,
              "messages": [{"role": "user", "content": prompt}]}, timeout=120)
    print("llm: github", r.status_code, repr(r.content[:60]))
    if r.status_code == 200 and r.content.strip():
        yield r.json()["choices"][0]["message"]["content"]


def _pollinations(prompt):
    for _ in range(8):
        r = requests.post(
            "https://text.pollinations.ai/openai",
            json={"model": "openai-fast", "max_tokens": 8000, "seed": random.randint(1, 10**8),
                  "messages": [{"role": "user", "content": prompt}]}, timeout=180)
        print("llm: pollinations", r.status_code, repr(r.text[:120]))
        if r.status_code == 200:
            yield r.json()["choices"][0]["message"]["content"]
        else:
            m = re.search(r"Retry after (\d+)s", r.text)
            time.sleep(int(m.group(1)) + 3 if m else 20)


def call_llm(prompt):
    sources = []
    if GEMINI:
        sources.append(("gemini", _gemini, 3))
    if GROQ:
        sources.append(("groq", _groq, 3))
    sources += [("github", _github, 1), ("pollinations", _pollinations, 1)]
    for name, fn, tries in sources:
        for _ in range(tries):
            try:
                for out in fn(prompt + SUFFIX + f"\n(variation id: {random.randint(10**6, 10**9)})"):
                    try:
                        return _clean_json(out or "")
                    except Exception as e:
                        print(f"llm {name} bad output:", repr(e), repr((out or "")[:200]))
            except Exception as e:
                print(f"llm {name} error:", repr(e)[:200])
            time.sleep(3)
    raise RuntimeError("No LLM source gave a usable script (see 'llm' lines above)")

"""LLM helper. Returns validated JSON.
Provider order: Gemini -> Groq -> GitHub Models -> Pollinations.
"""
import json, os, random, re, time, requests

GH = os.environ.get("GITHUB_TOKEN", "")
GEMINI = os.environ.get("GEMINI_API_KEY", "").strip()
GROQ = os.environ.get("GROQ_API_KEY", "").strip()
SCENE_COUNT = 10
SUFFIX = (
    "\nOutput raw JSON only. Exactly 10 scenes. Keep every image_prompt to 8-16 words. "
    "Keep scene lines to 5-10 spoken words. No markdown fences."
)


def _ascii(s):
    try:
        s = s.encode("cp1252").decode("utf-8")
    except Exception:
        pass
    for a, b in (("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"'),
                 ("\u2013", "-"), ("\u2014", "-"), ("\u2026", "...")):
        s = s.replace(a, b)
    return s.encode("ascii", "ignore").decode()


def _lenient(out):
    scenes = re.findall(
        r'"line"\s*:\s*"(.*?)"\s*,\s*"image_prompt"\s*:\s*"(.*?)"\s*\}', out, re.S)
    if len(scenes) != SCENE_COUNT:
        raise ValueError(f"expected {SCENE_COUNT} scenes, recovered {len(scenes)}")
    t = re.search(r'"title"\s*:\s*"(.*?)"\s*,\s*"description"', out, re.S)
    d = re.search(r'"description"\s*:\s*"(.*?)"\s*,\s*"tags"', out, re.S)
    h = re.search(r'"hero"\s*:\s*"(.*?)"\s*,\s*"(?:full_story|scenes)"', out, re.S)
    fs = re.search(r'"full_story"\s*:\s*"(.*?)"\s*,\s*"scenes"', out, re.S)
    tags = re.findall(r'"([A-Za-z0-9 #_-]{2,30})"',
                      (re.search(r'"tags"\s*:\s*\[(.*?)\]', out, re.S) or [None, ""])[1])
    return {"title": t.group(1) if t else "Untitled",
            "description": d.group(1) if d else "", "tags": tags,
            "hero": h.group(1) if h else "",
            "full_story": fs.group(1).replace("\\n", "\n") if fs else "",
            "scenes": [{"line": a.replace('\\\"', '"'), "image_prompt": b} for a, b in scenes]}


def _clean_json(out):
    out = _ascii(out or "")
    a, b = out.find("{"), out.rfind("}")
    if a < 0 or b <= a:
        raise ValueError("provider returned no JSON object")
    body = out[a:b + 1]
    try:
        obj = json.loads(body, strict=False)
    except Exception:
        if '"skip"' in body and '"scenes"' not in body:
            return json.dumps({"skip": True})
        obj = _lenient(body)
    if not isinstance(obj, dict):
        raise ValueError("response must be a JSON object")
    if obj.get("skip"):
        return json.dumps({"skip": True})
    scenes = obj.get("scenes")
    if not isinstance(scenes, list) or len(scenes) != SCENE_COUNT:
        raise ValueError(f"expected exactly {SCENE_COUNT} scenes")
    for i, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict) or not str(scene.get("line", "")).strip() or not str(scene.get("image_prompt", "")).strip():
            raise ValueError(f"scene {i} is missing narration or image prompt")
    obj.setdefault("title", "Untitled")
    obj.setdefault("description", "")
    obj.setdefault("tags", [])
    obj.setdefault("hero", "")
    obj.setdefault("full_story", "")
    if not isinstance(obj["tags"], list):
        obj["tags"] = []
    return json.dumps(obj)


def _gemini(prompt):
    for model in ("gemini-2.5-flash", "gemini-2.0-flash"):
        cfg = {"temperature": 0.9, "maxOutputTokens": 10000,
               "responseMimeType": "application/json"}
        if "2.5" in model:
            cfg["thinkingConfig"] = {"thinkingBudget": 0}
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": GEMINI, "Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": cfg},
            timeout=120)
        print("llm: gemini", model, r.status_code, repr(r.text[:160]))
        if r.status_code == 200:
            try:
                yield r.json()["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError, ValueError):
                print("llm: gemini returned no candidate text")
        elif r.status_code == 429:
            time.sleep(20)


def _groq(prompt):
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ}", "Content-Type": "application/json"},
        json={"model": "llama-3.3-70b-versatile", "temperature": 0.9, "max_tokens": 10000,
              "response_format": {"type": "json_object"},
              "messages": [{"role": "user", "content": prompt}]}, timeout=120)
    print("llm: groq", r.status_code, repr(r.text[:160]))
    if r.status_code == 200:
        try:
            yield r.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError):
            print("llm: groq returned no message content")
    elif r.status_code == 429:
        time.sleep(20)


def _github(prompt):
    r = requests.post(
        "https://models.github.ai/inference/chat/completions",
        headers={"Authorization": f"Bearer {GH}", "Accept": "application/json",
                 "Content-Type": "application/json"},
        json={"model": "openai/gpt-4o-mini", "max_tokens": 10000,
              "messages": [{"role": "user", "content": prompt}]}, timeout=120)
    print("llm: github", r.status_code, repr(r.text[:160]))
    if r.status_code == 200:
        try:
            yield r.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError):
            print("llm: github returned non-chat response; falling back")


def _pollinations(prompt):
    for attempt in range(5):
        r = requests.post(
            "https://text.pollinations.ai/openai",
            json={"model": "openai", "max_tokens": 12000, "seed": random.randint(1, 10**8),
                  "messages": [{"role": "user", "content": prompt}]}, timeout=180)
        print("llm: pollinations", r.status_code, repr(r.text[:160]))
        if r.status_code == 200:
            try:
                yield r.json()["choices"][0]["message"]["content"]
            except (KeyError, IndexError, ValueError):
                print("llm: pollinations returned no message content")
        elif r.status_code == 429:
            m = re.search(r"Retry after (\d+)s", r.text)
            time.sleep(int(m.group(1)) + 3 if m else 30)
        elif r.status_code == 400 and "output token limit" in r.text.lower():
            # Prompt is already deliberately compact; don't hammer the same rejected request.
            break
        else:
            time.sleep(8)


def call_llm(prompt):
    sources = []
    if GEMINI:
        sources.append(("gemini", _gemini, 2))
    if GROQ:
        sources.append(("groq", _groq, 2))
    sources += [("github", _github, 2), ("pollinations", _pollinations, 1)]
    for name, fn, tries in sources:
        for _ in range(tries):
            try:
                for out in fn(prompt + SUFFIX + f"\n(variation id: {random.randint(10**6, 10**9)})"):
                    try:
                        clean = _clean_json(out)
                        print("llm: accepted", name)
                        return clean
                    except Exception as e:
                        print(f"llm {name} invalid output:", repr(e), repr((out or "")[:180]))
            except Exception as e:
                print(f"llm {name} error:", repr(e)[:200])
            time.sleep(2)
    raise RuntimeError("No LLM provider returned valid JSON with exactly 10 scenes")

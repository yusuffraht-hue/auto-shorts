"""LLM helper. Returns validated JSON.
Provider order: Gemini -> Groq -> GitHub Models -> Pollinations.
"""
import json, os, random, re, time, requests

GH = os.environ.get("GITHUB_TOKEN", "")
GEMINI = GROQ = ""


def _classify(k):
    """Identify a key by its public prefix so a misnamed secret still works. Never prints the key."""
    k = (k or "").strip()
    if k.startswith("AIza"):
        return "gemini"
    if k.startswith("gsk_"):
        return "groq"
    if k.startswith("sk-"):
        return "openai (paid - not used)"
    return "unknown" if k else "empty"


for _name in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY"):
    _v = os.environ.get(_name, "").strip()
    _kind = _classify(_v)
    print("key check:", _name, "->", _kind)
    if _kind == "gemini" and not GEMINI:
        GEMINI = _v
    elif _kind == "groq" and not GROQ:
        GROQ = _v
SCENE_COUNT = 10
SUFFIX = (
    "\nOutput raw JSON only with exactly 10 scenes. Aim for 11 words per image prompt, "
    "6 spoken words per scene line (5-7 spoken words allowed), and 155 words in full_story. Count each before submitting. No markdown fences."
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


_GROQ_MODEL = None
_GROQ_PREF = ("llama-3.3-70b-versatile", "openai/gpt-oss-120b", "qwen/qwen3-32b",
              "openai/gpt-oss-20b", "llama-3.1-8b-instant")


def _groq_model():
    """Pick a chat model this Groq key can actually use (model names change over time)."""
    global _GROQ_MODEL
    if _GROQ_MODEL:
        return _GROQ_MODEL
    try:
        r = requests.get("https://api.groq.com/openai/v1/models",
                         headers={"Authorization": f"Bearer {GROQ}"}, timeout=30)
        ids = [m["id"] for m in r.json().get("data", [])]
        print("llm: groq models:", ids)
        for p in _GROQ_PREF:
            if p in ids:
                _GROQ_MODEL = p
                return p
        chat = [i for i in ids if not any(x in i.lower() for x in
                ("whisper", "guard", "tts", "prompt", "orpheus", "distil"))]
        if chat:
            _GROQ_MODEL = chat[0]
            return _GROQ_MODEL
    except Exception as e:
        print("llm: groq model list failed:", repr(e)[:150])
    return "llama-3.3-70b-versatile"


def _groq(prompt):
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ}", "Content-Type": "application/json"},
        json={"model": _groq_model(), "temperature": 0.9, "max_tokens": 10000,
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


_pollinations_available_at = 0.0


def _pollinations(prompt):
    global _pollinations_available_at
    for _ in range(3):
        delay = _pollinations_available_at - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        r = requests.post(
            "https://text.pollinations.ai/openai",
            json={"model": "openai-fast", "max_tokens": 12000, "reasoning_effort": "none",
                  "seed": random.randint(1, 10**8),
                  "messages": [{"role": "user", "content": prompt}]}, timeout=180)
        print("llm: pollinations", r.status_code, repr(r.text[:160]))
        if r.status_code == 200:
            _pollinations_available_at = time.monotonic() + 48
            try:
                yield r.json()["choices"][0]["message"]["content"]
            except (KeyError, IndexError, ValueError):
                print("llm: pollinations returned no message content")
        elif r.status_code in (402, 429):
            retry = re.search(r"Retry after (\d+)s", r.text, re.I)
            if r.status_code == 402 and not retry:
                return
            wait = min(int(retry.group(1)) + 3, 90) if retry else 48
            _pollinations_available_at = time.monotonic() + wait
        elif r.status_code == 400 and "output token limit" in r.text.lower():
            # This can be transient even with reasoning disabled. Keep retries paced and bounded.
            _pollinations_available_at = time.monotonic() + 48
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

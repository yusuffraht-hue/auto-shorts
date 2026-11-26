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


_github_compatible = True


def _github(prompt):
    global _github_compatible
    if not GH or not _github_compatible:
        return
    r = requests.post(
        "https://models.github.ai/inference/chat/completions",
        headers={"Authorization": f"Bearer {GH}", "Accept": "application/json",
                 "Content-Type": "application/json"},
        json={"model": "openai/gpt-4.1-mini", "max_tokens": 3000,
              "response_format": {"type": "json_object"},
              "messages": [{"role": "user", "content": prompt}]}, timeout=120)
    print("llm: github", r.status_code, repr(r.text[:160]))
    if r.status_code == 200:
        try:
            yield r.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError):
            _github_compatible = False
            print("llm: github returned non-chat response; skipping it for this run")


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
            # Return to the caller so a checked reserve can run before another identical request.
            _pollinations_available_at = time.monotonic() + 48
            return
        else:
            time.sleep(8)



def _word_range(minimum, maximum, sentence=False):
    word = "[A-Za-z0-9'-]+[,.:;!?]?"
    if sentence:
        ending = "[A-Za-z0-9'-]+[.!?]"
        pattern = f"^{word}( {word}){{{minimum - 2},{maximum - 2}}} {ending}$"
    else:
        pattern = f"^{word}( {word}){{{minimum - 1},{maximum - 1}}}$"
    return {"type": "string", "pattern": pattern}


def _local(prompt):
    if os.environ.get("SHORTS_LOCAL_WRITER") != "1":
        return
    string = {"type": "string"}
    scene_fields = {"beat": _word_range(14, 17, sentence=True), "line": _word_range(4, 8, sentence=True),
                    "image_prompt": _word_range(8, 16)}
    scene = {"type": "object", "properties": scene_fields,
             "required": list(scene_fields), "additionalProperties": False}
    fields = {"title": _word_range(3, 10), "description": _word_range(8, 20),
              "hero": _word_range(6, 15),
              "scenes": {"type": "array", "items": scene, "minItems": 10, "maxItems": 10}}
    schema = {"type": "object", "properties": fields, "required": list(fields),
              "additionalProperties": False}
    brief = prompt.split("Write TWO versions", 1)[0]
    instructions = (
        "Write an original, clear Short made of ten scenes. For each scene, write a complete "
        "14-to-17-word story beat, a 4-to-8-word narration line that tells that beat, and an "
        "8-to-16-word illustration brief that starts with the setting. Order the scenes as "
        "hook, goal, discovery, complication, insight, action, response, result, payoff, ending. "
        "Give the episode a specific title. Start narration with the actual unusual event instead "
        "of a character's name. Every line must be a complete, short sentence. "
        "End with an action that solves the opening problem. Use concrete actions, family-friendly "
        "language, varied sentences, and no quotes from another work. Stick to the supplied facts "
        "for commentary and clearly label interpretations. Return only the structured response."
    )
    response = requests.post(
        "http://127.0.0.1:18171/v1/chat/completions",
        json={"messages": [{"role": "user", "content": brief.strip() + "\n\n" + instructions}],
              "temperature": 0.67, "max_tokens": 1900,
              "response_format": {"type": "json_schema", "json_schema": {"schema": schema}}},
        timeout=160,
    )
    response.raise_for_status()
    result = json.loads(response.json()["choices"][0]["message"]["content"])
    beats = [scene.pop("beat") for scene in result["scenes"]]
    lines = [scene["line"] for scene in result["scenes"]]
    unfinished = re.compile(r"\b(a|an|and|as|becomes|for|from|in|into|is|of|or|that|the|to|with)[.!?]$", re.I)
    if any(unfinished.search(text) for text in beats + lines):
        raise ValueError("Draft contains an unfinished sentence")
    if len(set(lines)) != len(lines) or "blocky town" in result["title"].lower():
        raise ValueError("Draft has repeated narration or a generic title")
    result["full_story"] = "\n\n".join(" ".join(beats[start:end])
                                      for start, end in ((0, 3), (3, 7), (7, 10)))
    yield json.dumps(result)


def call_llm(prompt):
    sources = []
    if GEMINI:
        sources.append(("gemini", _gemini, 2))
    if GROQ:
        sources.append(("groq", _groq, 2))
    if os.environ.get("LOCAL_MEDIA_ONLY") == "1":
        sources = [("cpu", _local, 1)]
    else:
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

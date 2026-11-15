"""LLM helper: tries GitHub Models (two endpoints), then Pollinations text as a free fallback."""
import os, time, requests

GH = os.environ.get("GITHUB_TOKEN", "")
TRIES = [
    ("https://models.github.ai/inference/chat/completions",
     {"Authorization": f"Bearer {GH}", "Accept-Encoding": "identity",
      "Content-Type": "application/json"},
     ["openai/gpt-4o-mini", "openai/gpt-4.1-mini", "meta/Llama-3.3-70B-Instruct"]),
    ("https://models.inference.ai.azure.com/chat/completions",
     {"Authorization": f"Bearer {GH}", "Accept-Encoding": "identity",
      "Content-Type": "application/json"},
     ["gpt-4o-mini", "Llama-3.3-70B-Instruct"]),
    ("https://text.pollinations.ai/openai",
     {"Content-Type": "application/json"},
     ["openai"]),
]


def call_llm(prompt):
    for url, headers, models in TRIES:
        for model in models:
            try:
                r = requests.post(url, headers=headers, timeout=120, json={
                    "model": model, "temperature": 1.0, "max_tokens": 1500,
                    "messages": [{"role": "user", "content": prompt}]})
                hdr = {k: v for k, v in r.headers.items()
                       if k.lower() in ("content-type", "content-length", "content-encoding",
                                        "x-ratelimit-remaining", "retry-after")}
                print("llm:", url.split("/")[2], model, r.status_code, hdr, repr(r.content[:150]))
                if r.status_code == 200 and r.content.strip():
                    out = r.json()["choices"][0]["message"]["content"]
                    if out and out.strip():
                        return out
            except Exception as e:
                print("llm error:", url.split("/")[2], model, repr(e))
            time.sleep(3)
    raise RuntimeError("No LLM endpoint returned a usable reply (see 'llm:' lines above)")

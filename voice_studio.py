"""Optional VoiceStudio TTS client for the auto-shorts pipeline.

VoiceStudio exposes an OpenAI-compatible POST /v1/audio/speech endpoint.
This module does not install or host VoiceStudio; it connects to an already
running, reachable VoiceStudio backend when configured.
"""
import os
from pathlib import Path

import requests


def configured(env=None):
    env = os.environ if env is None else env
    return bool(env.get("VOICESTUDIO_URL", "").strip())


def synthesize(text, path, env=None, session=requests):
    """Write an MP3 using VoiceStudio; raise on any error so callers can fall back."""
    env = os.environ if env is None else env
    base_url = env.get("VOICESTUDIO_URL", "").strip().rstrip("/")
    if not base_url:
        raise RuntimeError("VOICESTUDIO_URL is not configured")
    if len(text.encode("utf-16-le")) // 2 > 2000:
        raise ValueError("VoiceStudio speech input exceeds 2,000 UTF-16 units")

    payload = {
        "model": env.get("VOICESTUDIO_MODEL", "tts-1"),
        "voice": env.get("VOICESTUDIO_VOICE", "default"),
        "input": text,
        "response_format": "mp3",
    }
    headers = {"Content-Type": "application/json"}
    api_key = env.get("VOICESTUDIO_API_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = session.post(
        f"{base_url}/v1/audio/speech",
        json=payload,
        headers=headers,
        timeout=(15, 240),
    )
    response.raise_for_status()
    if len(response.content) < 1000:
        raise RuntimeError("VoiceStudio returned an empty or suspiciously small audio file")
    Path(path).write_bytes(response.content)
    return True

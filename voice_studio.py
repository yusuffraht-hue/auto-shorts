"""Optional VoiceStudio TTS client for the auto-shorts pipeline.

VoiceStudio exposes an OpenAI-compatible POST /v1/audio/speech endpoint.
This module does not install or host VoiceStudio; it connects to an already
running, reachable VoiceStudio backend when configured.
"""
import ipaddress
import os
from pathlib import Path
from urllib.parse import urlsplit

import requests


def configured(env=None):
    env = os.environ if env is None else env
    return bool(env.get("VOICESTUDIO_URL", "").strip())


def _is_loopback_host(host):
    host = str(host or "").strip().lower().rstrip(".")
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


def _validate_base_url(value):
    """Require HTTPS for remote hosts so a configured Bearer key is not sent in cleartext."""
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
    except ValueError as exc:
        raise ValueError("VOICESTUDIO_URL must be a valid HTTP(S) service-root URL") from exc
    if parsed.scheme not in ("http", "https") or not host:
        raise ValueError("VOICESTUDIO_URL must be an HTTP(S) service-root URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("VOICESTUDIO_URL must not contain credentials, a query, or a fragment")
    if parsed.path not in ("", "/"):
        raise ValueError("VOICESTUDIO_URL must be the VoiceStudio service root, without an API path")
    if parsed.scheme == "http" and not _is_loopback_host(host):
        raise ValueError("Remote VoiceStudio URLs must use HTTPS to protect Bearer API keys")
    return value.rstrip("/")


def _looks_like_mp3(content):
    if content.startswith(b"ID3"):
        return True
    # MP3 frames start with an 11-bit sync word; allow a short leading tag/header.
    limit = min(max(len(content) - 1, 0), 4096)
    return any(
        content[index] == 0xFF and (content[index + 1] & 0xE0) == 0xE0
        for index in range(limit)
    )


def synthesize(text, path, env=None, session=requests):
    """Write an MP3 using VoiceStudio; raise on any error so callers can fall back."""
    env = os.environ if env is None else env
    raw_url = env.get("VOICESTUDIO_URL", "").strip()
    if not raw_url:
        raise RuntimeError("VOICESTUDIO_URL is not configured")
    base_url = _validate_base_url(raw_url)
    if not isinstance(text, str) or not text.strip():
        raise ValueError("VoiceStudio speech input must be nonempty text")
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
    host = urlsplit(base_url).hostname
    if not _is_loopback_host(host) and not api_key:
        raise ValueError("Remote VoiceStudio endpoints require VOICESTUDIO_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = session.post(
        f"{base_url}/v1/audio/speech",
        json=payload,
        headers=headers,
        timeout=(15, 240),
    )
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    if content_type != "audio/mpeg":
        raise RuntimeError("VoiceStudio did not return the requested audio/mpeg content type")
    content = response.content
    if len(content) < 1000:
        raise RuntimeError("VoiceStudio returned an empty or suspiciously small audio file")
    if not _looks_like_mp3(content):
        raise RuntimeError("VoiceStudio response is not a recognizable MP3 file")
    Path(path).write_bytes(content)
    return True

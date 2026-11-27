"""Synthesize Shorts narration on the runner using public Kokoro model weights."""
import hashlib
import os
from functools import lru_cache
from pathlib import Path
from tempfile import NamedTemporaryFile

import requests

RELEASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1"
MODEL = ("kokoro-v1.0.onnx", "beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a")
VOICES = ("voices-v1.0.bin", "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d")


def model_asset(cache, name, digest):
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / name
    if path.is_file():
        with path.open("rb") as source:
            if hashlib.file_digest(source, "sha256").hexdigest() == digest:
                return path

    with NamedTemporaryFile(dir=cache, delete=False) as target:
        temporary = Path(target.name)
        try:
            checksum = hashlib.sha256()
            with requests.get(f"{RELEASE}/{name}", timeout=(10, 35), stream=True) as response:
                response.raise_for_status()
                for chunk in response.iter_content(1024 * 1024):
                    checksum.update(chunk)
                    target.write(chunk)
            if checksum.hexdigest() != digest:
                raise ValueError(f"Kokoro model checksum mismatch for {name}")
            target.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    return path


@lru_cache(maxsize=1)
def narrator():
    try:
        from kokoro_onnx import Kokoro
        from onnxruntime import InferenceSession, SessionOptions

        cache = Path(os.environ.get("SHORTS_VOICE_CACHE", Path.home() / ".cache" / "shorts-kokoro"))
        model = model_asset(cache, *MODEL)
        voices = model_asset(cache, *VOICES)
        options = SessionOptions()
        options.intra_op_num_threads = 2
        session = InferenceSession(str(model), sess_options=options, providers=["CPUExecutionProvider"])
        return Kokoro.from_session(session, str(voices))
    except Exception as error:
        print(f"Kokoro unavailable ({type(error).__name__})")
        return None


def synthesize(text, path):
    engine = narrator()
    if engine is None:
        return False
    import soundfile

    voice = "am_michael"
    samples, rate = engine.create(text, voice=voice, lang="en-us")
    if len(samples) == 0:
        return False
    soundfile.write(path, samples, rate, format="WAV")
    print("Narration: Kokoro", voice)
    return True

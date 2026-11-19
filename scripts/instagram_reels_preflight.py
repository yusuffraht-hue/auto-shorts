"""Fail-closed Instagram Reel readiness checks; no API calls or publishing."""
import argparse
import json
import pathlib
import subprocess

MAX_BYTES = 300 * 1024 * 1024
MIN_DURATION = 3
MAX_DURATION = 180


def check_quality(report):
    if not isinstance(report, dict) or report.get("passed") is not True:
        raise ValueError("quality report must explicitly pass")
    if report.get("issues"):
        raise ValueError("quality report contains unresolved issues")


def inspect_video(path, probe=subprocess.check_output):
    path = pathlib.Path(path)
    if path.suffix.lower() != ".mp4" or not path.is_file():
        raise ValueError("missing MP4")
    if not 1024 <= path.stat().st_size <= MAX_BYTES:
        raise ValueError("invalid MP4 size")
    raw = probe(["ffprobe", "-v", "error", "-show_entries",
                 "format=duration:stream=codec_type,codec_name,width,height",
                 "-of", "json", str(path)])
    meta = json.loads(raw)
    seconds = float(meta["format"]["duration"])
    videos = [s for s in meta["streams"] if s.get("codec_type") == "video"]
    audio = [s for s in meta["streams"] if s.get("codec_type") == "audio"]
    if not MIN_DURATION <= seconds <= MAX_DURATION:
        raise ValueError("Reel duration outside allowed range")
    if len(videos) != 1 or videos[0].get("codec_name") != "h264":
        raise ValueError("requires one H.264 video stream")
    if (videos[0].get("width"), videos[0].get("height")) != (1080, 1920):
        raise ValueError("requires 1080x1920 vertical video")
    if not audio or not any(s.get("codec_name") == "aac" for s in audio):
        raise ValueError("requires AAC audio")
    return {"duration_seconds": seconds, "size_bytes": path.stat().st_size}


def build_manifest(series, video, quality, caption, episode_id):
    if series not in ("town", "anime"):
        raise ValueError("unknown series")
    if not isinstance(episode_id, str) or not 1 <= len(episode_id) <= 120 or not all(
        c.isalnum() or c in "-_" for c in episode_id
    ):
        raise ValueError("invalid episode id")
    check_quality(json.loads(pathlib.Path(quality).read_text(encoding="utf-8")))
    video_meta = inspect_video(video)
    if not isinstance(caption, str) or not 1 <= len(caption) <= 2200:
        raise ValueError("caption must be 1-2200 characters")
    return {
        "destination": "instagram",
        "username": "zebra.7392820",
        "series": series,
        "episode_id": episode_id,
        "video": str(pathlib.Path(video)),
        "caption": caption,
        "video_checks": video_meta,
        "publish_status": "READY_NOT_PUBLISHED",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--series", required=True, choices=("town", "anime"))
    parser.add_argument("--video", required=True)
    parser.add_argument("--quality", required=True)
    parser.add_argument("--caption", required=True)
    parser.add_argument("--episode-id", required=True)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()
    manifest = build_manifest(args.series, args.video, args.quality, args.caption, args.episode_id)
    output = pathlib.Path(args.manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Instagram Reel passed preflight. NOT published.")


if __name__ == "__main__":
    main()

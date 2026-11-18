# auto-shorts

A free-first pipeline for two separate vertical-video series. Each series has its own prompts, style, voice, tags and episode history.

## Series

- **In This Town** — original blocky-toy-town mysteries, strange rules, powers and recurring characters. Town scenes use CPU-rendered Blender stills when Blender is enabled; the pipeline falls back to generated images if rendering fails.
- **Anime & Novel Stories** — unofficial recaps and clearly labelled fan what-if stories. Recaps use configured canon fact sheets and should be skipped when those notes cannot support an accurate episode. Visuals are symbolic rather than recognizable copies of characters or source artwork.

The pipeline creates a script, narration, scene images, captions and a vertical MP4 using FFmpeg. It does not guarantee that every free provider will be available on every run.

## GitHub Actions workflows

- `.github/workflows/in-this-town.yml` — scheduled daily at 15:00 UTC.
- `.github/workflows/anime-and-novel-stories.yml` — scheduled daily at 15:30 UTC.
- `.github/workflows/pipeline-checks.yml` — Python syntax checks and offline unit tests on pushes and pull requests.
- `.github/workflows/blender-shots-test.yml` — manual still-image rendering test for the Blender scene renderer.

For manual runs of either series workflow, the `dry_run` input defaults to **true**. Scheduled runs are not dry runs. When YouTube credentials are configured, scheduled runs can upload videos; the default upload privacy is **private**. Generated MP4s and story text are also saved as short-lived GitHub Actions artifacts.

Keep videos private while reviewing them. Do not change the `PRIVACY` repository variable to `public` unless the channel owner has reviewed the actual video and explicitly chosen to publish it.

## Story and originality safeguards

- Town stories must be original and must not borrow characters or plots from existing media.
- Anime/novel recaps may use only facts supported by the selected work's configured canon notes. If those notes are insufficient, the model is instructed to return a skip response rather than invent events.
- What-if episodes must be clearly described as speculation, not canon.
- Do not copy protected dialogue, prose, panels, logos or footage.
- Each episode should have a distinct story and meaningful viewer value; high output volume or a repeated template alone is not a monetization strategy.

## Free-first providers

Story generation tries available providers in this order: Gemini, Groq, GitHub Models, then Pollinations text. Provider access, rate limits and free-tier terms can change. Image generation uses Pollinations when a scene does not have a Blender still. Narration uses Edge TTS with a series-specific voice and fallback voices. If `VOICESTUDIO_URL` is configured, the pipeline tries VoiceStudio first and visibly falls back to Edge TTS if it is unavailable.

No paid API or subscription is required by the repository's default design, but free services can be rate-limited, unavailable or changed without notice.

## Setup

For YouTube uploads, configure these repository Actions secrets:

- `YT_CLIENT_ID`
- `YT_CLIENT_SECRET`
- `YT_REFRESH_TOKEN`

Optional story-provider secrets:

- `GEMINI_API_KEY`
- `GROQ_API_KEY`

Optional VoiceStudio connection (leave unset to keep the existing free Edge TTS path):

- `VOICESTUDIO_URL` — reachable VoiceStudio service root, for example `https://your-private-host`
- `VOICESTUDIO_API_KEY` — optional bearer key if the backend requires authentication
- Repository variables `VOICESTUDIO_MODEL` (default `tts-1`) and `VOICESTUDIO_VOICE` (default `default`)

VoiceStudio must already be running somewhere reachable by GitHub Actions. This repository does not host it or provide a free GPU server. Its speech endpoint returns audio but not word timings, so captions use estimated word timing for VoiceStudio clips. Do not expose a private backend to the public internet; use a secure HTTPS tunnel or private network arrangement.

The GitHub Actions token is supplied to the workflow for GitHub Models access. Never commit API keys, OAuth tokens or passwords to the repository.

To run offline checks locally:

```bash
python -m compileall -q .
python -m unittest discover -v
```

## Important limitations

- GitHub Actions and free text/image/TTS providers have usage limits and can change their free access at any time.
- A successful workflow run does not prove that a video is good; watch the actual MP4 and check the story, narration, captions and visuals before any public release.
- Private and unlisted Shorts do not count toward YouTube's qualified public Shorts-view thresholds.
- YouTube monetization is reviewed at the channel level. Repetitive, mass-produced or minimally varied AI content may be ineligible even when every upload is technically original.
- If the creator is under 18, AdSense for YouTube requires an approved account belonging to a parent or guardian over 18; do not create an AdSense account in a minor's name.

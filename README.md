# auto-shorts

A free-first pipeline for two separate vertical-video series. Each series has its own prompts, style, voice, tags and episode history.

## Series

- **Original stories** — rotating In This Town, World Simulator, Kingdom Simulator, Power Archive and Mystery Files formats.
- **Anime & Novel Stories** — evidence-based analysis using reviewed topic records; no unsupported recaps or fan what-if episodes.

The pipeline creates a script, narration, scene images, captions and a vertical MP4 using FFmpeg.

## GitHub Actions workflows

- **Six-format render check** makes and decodes one MP4 per format and saves each video, story and probe report as a short-lived artifact.
- **Six-format production** has daily start slots at 08:00, 10:00, 12:00, 14:00, 16:00 and 18:00 Alberta Time. Enable the schedule after upload verification by setting the repository variable `YOUTUBE_SIX_FORMATS=true`. This also turns off the two legacy schedules and their legacy OAuth retry job. GitHub may start a slot late.
- Manual production runs default to render-only. Select **Upload and verify one private YouTube video** to test Composio. Manual uploads stay private and leave episode history alone.
- **Pipeline checks** runs Python syntax checks and offline unit tests.

Scheduled runs automatically make qualifying Shorts public after the quality checks pass and YouTube confirms processing and disclosure. Manual test uploads stay private. Check the YouTube receipt before retrying a failed run to see whether it already created a video.

## Story and originality safeguards

- Town stories must be original and must not borrow characters or plots from existing media.
- Analysis requires a reviewed topic record in `editorial_topics.json`; selection fails closed when no eligible topic remains. A review flag is not independent proof of accuracy. Verify source facts and rights before release.
- Do not copy protected dialogue, prose, panels, logos or footage.
- Each episode should have a distinct story and meaningful viewer value. Pre-render checks compare story text against the last eight episodes for near-duplicates; this heuristic cannot prove originality or monetization eligibility.

## Free-first providers

Story generation tries available providers in this order: Gemini, Groq, GitHub Models, then Pollinations text. Provider access, rate limits and free-tier terms can change. Image generation uses Pollinations when a scene does not have a Blender still. Narration uses Edge TTS with a series-specific voice and fallback voices.

No paid API or subscription is required by the repository's default design, but free services can be rate-limited, unavailable or changed without notice.

## Setup

For the six-format workflow, set the GitHub Actions secret `COMPOSIO_API_KEY` from the free Composio project that owns the YouTube connection. Set the repository variable `YOUTUBE_CHANNEL_ID` to the intended channel ID. If the project has multiple active YouTube connections, set `COMPOSIO_YOUTUBE_ACCOUNT_ID` to choose the right account. The key must allow account lookup if needed, file staging, tool execution and proxy execution. Composio uploads the file privately first, then the workflow applies and verifies the audience and synthetic-media fields through YouTube.

The legacy manual workflows still use `YT_CLIENT_ID`, `YT_CLIENT_SECRET` and `YT_REFRESH_TOKEN`. The six-format workflow uses the GitHub Actions token for GitHub Models. Never commit keys or credentials.

Cloudflare Workers AI uses `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` only when the `CLOUDFLARE_FREE_CONFIRMED` repository variable is `true`. Enable that variable only after confirming the Cloudflare account uses Workers Free with paid overages disabled.

To run offline checks locally:

```bash
python -m compileall -q .
python -m unittest discover -v
```

## Operating the schedule

- [Recovery and rollback](RECOVERY.md) explains how to reconcile failed uploads and restore service.
- **Shorts daily health** reports missing and failed scheduled runs in its GitHub Actions summary. Scheduled production retains publishing outcomes in `history/publishing/`.
- [Editorial experiments](EDITORIAL_EXPERIMENT.md) documents how to measure changes before rollout.

## Important limitations

- GitHub Actions and free text/image/TTS providers have usage limits and can change their free access at any time.
- A successful workflow run does not prove that a video is good; watch the actual MP4 and check the story, narration, captions and visuals before any public release.
- Private and unlisted Shorts do not count toward YouTube's qualified public Shorts-view thresholds.
- YouTube monetization is reviewed at the channel level. Repetitive, mass-produced or minimally varied AI content may be ineligible even when every upload is technically original.
- If the creator is under 18, AdSense for YouTube requires an approved account belonging to a parent or guardian over 18; do not create an AdSense account in a minor's name.

## Eight daily Shorts

The production workflow uses Alberta Time (UTC−6) with no end date. The Roblox game trend engine is separate from the Trending Topics Shorts.

| Calgary time | Format |
| --- | --- |
| 8 AM | World Simulator |
| 10 AM | Kingdom Simulator |
| 12 PM | In This Town |
| 2 PM | Power Archive |
| 4 PM | Mystery Files |
| 6 PM | Anime & Novel Stories |
| 8 PM | Useful Web Lab Showcase |
| 9 PM | Trending Topics |

Render tests exercise local speech, FFmpeg, Blender or illustrated explainers, and the real Web Lab demo in an isolated browser. The showcase verifies a production deployment against the public release manifest and skips projects without a verified demo. Trending Topics uses a current Hacker News ranking to choose a sourced, reviewed tech explainer. It skips when none of the stories qualify.

Production jobs run when `SHORTS_DAILY_ENABLED=true`. Public publishing additionally requires `SHORTS_PUBLIC_VERIFIED=true` after a successful private canary from this workflow, and the Composio project must have a hard $0 limit. Use the manual production dispatch with `upload=true` for the canary. Check the processed private video ID and disclosure in the workflow receipt. Showcase public publishing also requires the verified channel profile link flag. Keep Cloudflare inference disabled while free usage is unverified. The production renderer uses local media and the workflow's GitHub Models token or an unused, reviewed fallback script.

Each public attempt reserves its slot and content in `history/production` before upload. A failed preflight changes no reservation. After submission, check the receipt and match the release marker in YouTube Studio before making any recovery decision. An ambiguous attempt holds its slot and content key to prevent duplicates. Other eligible slots can still run.

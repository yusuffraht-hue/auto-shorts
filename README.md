# auto-shorts

A zero-cost starting point for a daily vertical story Short.

Pipeline: story script (GitHub Models, with Pollinations text fallback) -> Edge TTS narration -> Pollinations images -> FFmpeg captions/render -> YouTube upload.

## What the current version improves

- Story prompts require a clear rule, one protagonist, cause-and-effect escalation, a meaningful twist and a payoff.
- Script validation rejects missing fields, incorrect scene counts and narration that is far too short or long.
- The same detailed protagonist description is repeated in each image prompt to help visual continuity.
- Default narration is slower and uses a conversational Edge TTS voice.
- Captions use short phrases rather than flashing one or two words at a time, with a dark backing and safer screen placement.
- Audio is loudness-normalized and the final render is checked before upload.

These changes improve the production process, but free image generation can still produce inconsistent characters and AI narration will not sound exactly like a human voice. Always watch the rendered Short before making it public.

## Setup

1. Google Cloud console: create a project, enable **YouTube Data API v3**, create an OAuth client (Web application) with redirect URI \`https://developers.google.com/oauthplayground\`.
2. In OAuth Playground (gear icon -> use your own credentials), authorize scope \`https://www.googleapis.com/auth/youtube.upload\` with your channel's Google account and exchange the code for a refresh token.
3. Repo -> Settings -> Secrets and variables -> Actions -> add secrets:
   \`YT_CLIENT_ID\`, \`YT_CLIENT_SECRET\`, \`YT_REFRESH_TOKEN\`.
4. Actions tab -> \`daily-short\` -> Run workflow. The default privacy is PRIVATE.
5. Keep videos private while testing. Only change the \`PRIVACY\` repository variable to \`public\` after you have reviewed the results and confirmed your upload/API setup allows public publishing.

## Free customization

The workflow uses these defaults if no variables are set:

- \`VOICE\`: \`en-US-BrianNeural\`
- \`RATE\`: \`-5%\`
- \`PRIVACY\`: \`private\`
- \`MODEL\`: \`openai/gpt-4o-mini\` (the script currently uses the GitHub Models endpoint first)

You can set \`VOICE\` and \`RATE\` as repository variables under Settings -> Secrets and variables -> Actions -> Variables. Edge TTS voice availability can change; if a voice fails, use a supported English voice from the Edge TTS voice list.

## Important limits

- GitHub Actions and free image/text services have rate limits and can change their free access at any time.
- New, unaudited YouTube API projects can be limited to private uploads. Public publishing may require Google's YouTube API compliance audit.
- YouTube API quota limits apply.
- Repetitive, mass-produced AI videos may not qualify for monetization under YouTube's inauthentic-content rules. Add original creative direction, meaningful editing and your own contribution; don't rely on volume alone.
- The code in this repository uploads to YouTube. Any separate Composio workflow for other platforms is managed separately.
- Never put API keys, OAuth tokens or passwords in source code or commit them to GitHub. Store secrets in GitHub Actions Secrets.

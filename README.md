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


## Optional: FreeLLMAPI text provider

The two video workflows can use a FreeLLMAPI gateway as their first story-generation provider. If it is not configured or its response is unusable, the existing Gemini, Groq, GitHub Models and Pollinations fallback chain remains available.

1. Run FreeLLMAPI and add your upstream provider keys in its dashboard. Its OpenAI-compatible API uses `/v1/chat/completions` and a unified bearer key.
2. Make the FreeLLMAPI server reachable from GitHub Actions over HTTPS. A local address such as `http://localhost:3001` or a Chromebook LAN address will **not** work from GitHub-hosted runners.
3. In this repository, open **Settings → Secrets and variables → Actions**.
4. Add the repository secret `FREELLMAPI_API_KEY` with your unified key.
5. Add the repository variable `FREELLMAPI_BASE_URL` with the server origin, for example `https://your-private-gateway.example` (do not append `/v1`; the client accepts either form).
6. Optionally add `FREELLMAPI_MODEL` as a variable. It defaults to `auto`, allowing FreeLLMAPI to select a model from its configured routing pool.

Keep the gateway private where possible, use HTTPS, restrict who can reach it, and rotate the unified key if it is exposed. Do not put the key in workflow YAML, repository variables, source files, or chat. This integration does not deploy or host FreeLLMAPI for you; the gateway must be running and reachable before a workflow can use it.

## Optional free research and skill security tools

These tools are optional helpers for preparing stories and reviewing agent extensions. They do not add a paid API dependency to the video pipeline.

### Agent Reach (local research helper)

[Agent Reach](https://github.com/Panniantong/agent-reach) is an open-source capability installer for an AI coding assistant. It can help research public web pages, YouTube transcripts, RSS feeds and public GitHub repositories. It is designed to run on your own computer alongside an agent that can execute shell commands; it is **not** a hosted API that GitHub Actions automatically calls during video generation.

On a Linux machine with Python and pip available, use its safe setup path:

```bash
python3 -m venv ~/.venvs/agent-reach
source ~/.venvs/agent-reach/bin/activate
python -m pip install --upgrade pip
python -m pip install https://github.com/Panniantong/agent-reach/archive/main.zip
agent-reach install --env=auto --safe
agent-reach doctor
```

Use the assistant to read sources before writing a recap, for example: ask it to read official episode/chapter pages or public reference pages and summarize only facts supported by those sources. Some channels need a logged-in browser session or cookies; do not export or share account cookies unless you understand the risk. Web semantic search may require a free Exa key. Reddit is not zero-config. Agent Reach's own documentation lists the platform-specific setup requirements: [Agent Reach guide](https://github.com/Panniantong/agent-reach/blob/main/docs/README_en.md).

### NVIDIA SkillSpector (static security checks)

[NVIDIA SkillSpector](https://github.com/NVIDIA/skillspector) scans agent skill bundles for suspicious instructions, dangerous code patterns and supply-chain risks. Static mode does not need an LLM API key:

```bash
python3 -m pip install --user 'git+https://github.com/NVIDIA/skillspector.git'
skillspector scan ./path/to/skill --no-llm
```

This repository also includes a GitHub Actions check that scans any committed `SKILL.md` skill folders on pull requests. If the repository contains no skill bundles, the check reports that it skipped rather than pretending a scan happened. SkillSpector is defense-in-depth, not a sandbox; inspect findings and do not install a skill just because it receives a low score. See [NVIDIA's scanning guide](https://docs.nvidia.com/skills/scanning-agent-skills).

### What remains free, and what does not

- Agent Reach and SkillSpector are open-source tools; their upstream services, platform access and optional integrations can still have limits or require account setup.
- Neither tool generates video. Video images still use the existing Pollinations endpoint, which may throttle or change its free access.
- FreeLLMAPI remains optional and requires a reachable gateway plus a working upstream model. This project does not assume that a gateway or unlimited free model capacity exists.
- Edge TTS and GitHub Actions are external services with their own availability and usage limits. No zero-cost setup can guarantee unlimited generation.

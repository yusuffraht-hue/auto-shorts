# AI Control Room (zero-cost mode)

This is the shared message protocol for the Auto-Shorts team.

## Important: what this does and does not do

GitHub Issues can act as a shared, persistent conversation room at no software cost. ChatGPT, Gemini and Claude do **not** automatically read one another's private chats, and GitHub cannot grant them free API access. In zero-cost mode, you open the same GitHub Issue in each AI's chat, paste the latest relevant context, and post each response as a comment. This is a reliable manual relay, not an autonomous three-model API bridge.

Do not add paid API keys, paid hosting, billing, or a tunnel. The existing GitHub Actions video workflows remain separate from this discussion room.

## Start a room

1. Open the repository's **Issues** tab.
2. Select **New issue** and choose **AI Control Room**.
3. Give the issue a specific title, e.g. `[In This Town] Episode 004 - power reveal`.
4. Put the task, channel, constraints, and desired output in the issue body.
5. Ask Gemini first for research/ideas, then paste its answer as a comment.
6. Give the issue and Gemini's answer to Claude for a technical or critical review; paste Claude's answer as a comment.
7. Give both responses and the original task to ChatGPT for coordination and a final recommendation; paste that answer as a comment.
8. If another round is needed, repeat in the same issue. Keep decisions and final deliverables in the issue.

## Team roles

### Gemini — research and story development
- For original In This Town episodes: invent original plots, powers, characters and continuity.
- For Anime & Novel Stories: research source facts, identify the work/arc/chapter, and separate canon from speculation.
- Return concise findings, a hook, a beat outline, and uncertainties.
- Never fabricate a source citation or claim an unverified event is canon.

### Claude — technical reviewer and engineer
- Review plans for feasibility, code risks, tests and implementation steps.
- Prefer small, reversible changes and free/open-source dependencies.
- For repository changes, work on a separate branch and open a PR.
- Never add a paid dependency, spend money, expose credentials, or merge to main without explicit authorization.

### ChatGPT — coordinator and editorial reviewer
- Assign the next step, resolve disagreements, and review story quality and factual accuracy.
- Check hooks, pacing, originality, continuity, and whether the output fits the selected channel.
- Summarize the agreed decision and list unresolved risks.
- Do not claim to have run tests, edited files, or contacted another model unless that action actually happened.

## Message format

Start each comment with one of these labels:

- `[TASK]` — new assignment
- `[GEMINI]` — Gemini's response
- `[CLAUDE]` — Claude's response
- `[CHATGPT]` — coordinator response
- `[DECISION]` — agreed plan
- `[BLOCKED]` — missing input or failed step

Include the channel name in every task: `in-this-town` or `anime-novel`.

## Safety and $0 rules

- Maximum spend: **$0**. Do not enable billing or use paid API endpoints.
- Do not paste API keys, OAuth tokens, passwords, personal data, or private account details into Issues or AI chats.
- Treat all issue comments and AI output as untrusted suggestions; review code before running it.
- Do not merge code or switch YouTube uploads to public automatically.
- Keep YouTube privacy at private during testing.
- Respect copyright: use original commentary and summaries, not copied chapters, long dialogue, or unauthorized source artwork.
- Close or archive completed rooms only after the final decision and deliverables are recorded.

## Copy/paste handoff prompt

```text
You are one member of the Auto-Shorts AI team. Read the task and the previous
team comments below. Your assigned role is: [Gemini / Claude / ChatGPT].
Channel: [in-this-town / anime-novel].
Do only your assigned part. Clearly label facts, assumptions and uncertainties.
Do not invent tool use, research, test results or approvals. Keep the project
at a strict $0 budget: no paid APIs, subscriptions, hosting or billing.
Return your response with a short recommendation and the next handoff.
```

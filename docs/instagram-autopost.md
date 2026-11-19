# Instagram Reels autoposting: connection and activation checklist

Target account: **@zebra.7392820** (Creator account verified via connected Composio Instagram profile). Two series: `town` and `anime`.

**Current state: NOT ACTIVE.** Composio is connected in the ChatGPT session, not necessarily in the unattended GitHub Actions runner. A working authorized authentication path, video delivery to Meta, status polling, and a verified publish must exist before scheduling. This PR does **not** change schedules, secrets, or upload behavior.

## What is implemented

`scripts/instagram_reels_preflight.py` validates an existing MP4 (H.264, AAC, 1080x1920, duration 3-180s, bounded size), requires a passed quality report, and produces a **not-published** manifest for the selected series. It never contacts Instagram. Run only after a successful generation:

```bash
python scripts/instagram_reels_preflight.py \
  --series town --video out/final.mp4 --quality out/quality-report.json \
  --caption "Original story. AI-generated visuals and narration. #InThisTown" \
  --episode-id town-2026-11-19 --manifest out/instagram-ready.json
```

The quality report currently covers story checks; it does not verify the rendered MP4's narrative quality, rights, or audio intelligibility. Those limitations must be addressed before unattended public posting.

## What is still required to activate

1. Securely authorize a **runner-accessible** Composio connection (or approved Meta publishing credentials) for the intended account. Do not paste keys in chat, commits, logs, or workflow YAML. ChatGPT's connected app does not automatically authorize GitHub Actions.
2. Provide a Meta-fetchable MP4 URL or supported temporary media upload from the runner. Do not expose private artifacts publicly without reviewing the security implications.
3. Implement the exact supported Composio Instagram API call sequence: create REELS media container; poll status with bounded backoff until FINISHED; publish once; verify returned media ID.
4. Store durable idempotency state keyed by series+episode ID; handle retries/timeouts without double posting, and record publish outcome.
5. Add a dry-run integration test with fake responses, and verify permissions and publishing limits with one explicitly approved test before switching to unattended public posting.
6. Wire only successful non-dry-run episodes to the publisher; keep both series' current YouTube behavior, schedules, and history unchanged unless explicitly authorized. Fail closed on missing authentication, quality failures, or provider errors.

**Important:** Public Instagram Reels cannot be made private using the existing YouTube `PRIVACY` variable. Creator account eligibility and Composio connection alone do not guarantee permission to publish. Publishing can be limited by account age, Meta permissions, policy, or API quotas.

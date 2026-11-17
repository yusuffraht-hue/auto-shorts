# AI Development Rules

## Purpose
Maintain a reliable, original, free-first automated video pipeline. Preserve existing behaviour unless a change is explicitly requested.

## Before changing code
1. Inspect the relevant files, workflows, configuration and recent history.
2. Trace how the affected feature is used by the pipeline.
3. State a concise plan, risks and files expected to change.
4. Prefer the smallest change that solves the problem.

## Implementation
- Follow the existing Python style and project structure.
- Keep functions focused and avoid unnecessary dependencies.
- Validate external responses, generated model output, file paths and user-controlled inputs.
- Handle network, provider, subprocess and file errors explicitly.
- Never silently turn a failed generation step into a successful episode.
- Keep credentials in GitHub Actions secrets or environment variables; never commit or print secrets.
- Preserve the free-first design. Do not add paid services, paid APIs or subscriptions without explicit approval.
- Keep story series, prompts, histories and styles separate where the project requires it.

## Video and story quality
- Prefer distinct, coherent stories over high upload volume.
- Check generated story structure, scene count, narration, captions and metadata before rendering.
- For recaps, only state facts supported by the configured source notes; skip when evidence is insufficient.
- Clearly label speculative what-if content.
- Avoid copied dialogue, prose, artwork, footage, logos and misleading claims.
- Review the actual rendered MP4 when possible; a successful workflow is not proof of a good video.
- Preserve accurate AI/synthetic-media disclosures. Never remove a disclosure merely to make an upload succeed.

## Testing and verification
- Add or update automated tests for meaningful behaviour changes.
- Run the narrowest relevant tests, then the full offline test suite when practical.
- Run Python compilation checks when Python files change.
- Report the exact commands executed and their real results.
- Do not claim a test, render, upload or integration was verified unless it was actually executed.
- Do not weaken or delete a test just to get a green result.

## Git and release safety
- Work on a separate branch and open a pull request for review.
- Do not merge pull requests without the repository owner's explicit approval.
- Do not publish videos, change schedules, change upload privacy, or modify production secrets without explicit approval.
- Do not delete user data, episode history or artifacts without explicit approval.
- Keep scheduled uploads private by default unless the owner explicitly authorizes a different setting.

## Final report
Summarize the goal, files changed, tests actually run, results, known limitations and any action needing owner approval. Clearly distinguish completed work from recommendations.

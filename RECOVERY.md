# Auto Shorts recovery

## Diagnose an outage

Open the production run and check its last failed step, then inspect the publishing record under `history/publishing/` and the available run artifacts. The daily health workflow reports missed starts and unsuccessful runs for the previous Calgary day. It uses GitHub's run data and never retries uploads.

- **No receipt:** Check the failed step. If the runner was cancelled or disappeared, still verify YouTube Studio before retrying.
- **Upload attempted:** The outcome may be unknown. Check YouTube Studio for the intended channel and title.
- **Uploaded private:** Reconcile the existing video in YouTube Studio before doing anything that could upload another copy.
- **Verified public:** Use the recorded video ID. If the overall run failed after publishing, repair the bookkeeping without regenerating the video.
- **Quota or credentials:** Wait for the service's quota to recover or restore the connection in its own dashboard. Verify the configured channel before resuming.

## Restore service

1. Pause the Six-format production workflow in GitHub Actions if it is publishing incorrectly. The `YOUTUBE_SIX_FORMATS` variable also controls legacy schedules, so check their settings before changing it.
2. Revert the offending commit through a PR. Preserve newer history and publishing records.
3. For a provider change, verify free usage, credentials and supported models, then run the offline checks and render-only workflow. Check the actual video before enabling the affected path.
4. Resume the workflow and verify the first scheduled run's public receipt.

Keep the Git repository, including `history/`, backed up. Record only credential names and renewal instructions. Keep the actual secrets in the account owner's password manager and GitHub Actions secrets. Logs and render artifacts have limited retention, so the ledger stores publishing outcomes and includes IDs only for verified public videos.

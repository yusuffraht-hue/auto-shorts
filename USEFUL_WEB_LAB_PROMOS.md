# Useful Web Lab promos

The separate scheduled workflow checks once a day at 7:17 p.m. Calgary time. Pull requests and manual workflow runs render the Screenshot Cleaner sample without uploading. The six-format schedule continues independently.

## Public release feed

Useful Web Lab should deploy a version 1 JSON feed at `https://yusuffraht-hue.github.io/useful-web-lab-public/shorts-releases.json` with the static site. Add entries only for confirmed public launches and meaningful user-facing updates. Publish the feed with the same deployed HTML and release manifest. Keep recent releases for at least seven days. Do not add maintenance changes, typo fixes, or private previews. Use this schema:

```json
{
  "version": 1,
  "releases": [{
    "project": "screenshot-cleaner",
    "kind": "launch",
    "path": "",
    "sha256": "<same SHA-256 as the deployed release.json>",
    "deployed_at": "<ISO 8601 UTC deployment timestamp>"
  }]
}
```

Use `kind: "feature"` for a meaningful update. Signal Garden uses the project ID `signal-garden` and path `signal-garden/`. The promo workflow skips projects without a reviewed live demo. To promote a new app, add a demo that uses public sample data and verifies the main action against the live release.

## Supported link and activation

Shorts direct viewers to a clickable channel profile link titled **Useful Web Lab**. Set its destination to the site root and verify the link from the public channel, plus access to both featured apps from the site. After verifying the link and the first unpublished render, set the Auto Shorts repository variable `LAB_PROMO_PROFILE_LINK_VERIFIED=true`. Publication also requires a current eligible release and successful live browser, recording, and video checks.

The publisher first commits a reservation to `history/lab-promos/`. A shared daily reservation limit and the release checksum prevent repeated uploads. If submission becomes ambiguous, a later eligible run checks recent channel uploads for the release marker. It never sends another upload for the same reservation. A confirmed public video gets a public ID in the record. Review any unresolved reservation before resetting it. Never reset it just because a video did not show up in a list.

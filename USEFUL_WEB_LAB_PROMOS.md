# Useful Web Lab promos

The separate scheduled workflow checks once a day at 7:17 p.m. Calgary time. Pull requests and manual runs check the same live releases and render without uploading. The six-format schedule continues independently.

## Public deployment detection

Auto-Shorts reads successful GitHub Pages deployments from Useful Web Lab. It automatically discovers projects added under `apps/<project-id>/index.html`, compares the deployed source with the live HTML checksum, and confirms the app can be reached from the YouTube profile destination. The first public deployment can include multiple launches. Auto-Shorts promotes at most one per day.

For a new app using custom controls, put its demo object in `apps/<project-id>/promo.json`. The object uses the schema below. The fallback promotes launches discovered from deployments. Publish a feed entry to mark a meaningful update.

## Public release feed

Useful Web Lab can deploy an explicit version 1 JSON feed at `https://yusuffraht-hue.github.io/useful-web-lab-public/shorts-releases.json` with the static site. Add entries only for confirmed public launches and meaningful user-facing updates. Publish the feed with the same deployed HTML and release manifest. Keep recent releases for at least seven days. Do not add maintenance changes, typo fixes, or private previews. Use this schema:

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

Use `kind: "feature"` for a meaningful update. Signal Garden uses the project ID `signal-garden` and path `signal-garden/`. For any new app, serve it at `<project-id>/` with its own `release.json` containing the matching `app` ID and HTML `sha256`. Link it from the site root. Add a `demo` object to its feed entry with `title`, `value`, and `action` for the captions (up to 32 characters each), `buttons` with one to four exact accessible button labels, and `expected` with exact text that becomes visible after those clicks. Use only built-in public sample data. Demos that require a sign-in, file selection, or third-party requests are skipped.

## Supported link and activation

Shorts direct viewers to a clickable channel profile link titled **Useful Web Lab**. Set its destination to the site root and verify the link from the public channel. Apps served below the site root must have a visible link from the root page before they qualify for a promo. After verifying the link and the first unpublished render, set the Auto Shorts repository variable `LAB_PROMO_PROFILE_LINK_VERIFIED=true`. Publication also requires a current eligible release and successful live browser, recording, and video checks.

The publisher first commits a reservation to `history/lab-promos/`. A shared daily reservation limit and the release checksum prevent repeated uploads. If submission becomes ambiguous, the next scheduled run checks recent channel uploads even when there is no new eligible release for the release marker. It never sends another upload for the same reservation. A confirmed public video gets a public ID in the record. Review any unresolved reservation before resetting it. Never reset it just because a video did not show up in a list.

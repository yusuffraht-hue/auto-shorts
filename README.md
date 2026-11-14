# auto-shorts

Daily pipeline on GitHub Actions: script (GitHub Models) -> voice (edge-tts) ->
images (Pollinations) -> 9:16 video (ffmpeg) -> YouTube upload.

## Setup
1. Google Cloud console: create a project, enable **YouTube Data API v3**, create an
   **OAuth client (Web application)** with redirect URI `https://developers.google.com/oauthplayground`.
2. In the OAuth Playground (gear icon -> use your own credentials), authorize scope
   `https://www.googleapis.com/auth/youtube.upload` with your channel's Google account and
   exchange the code to get a **refresh token**.
3. Repo -> Settings -> Secrets and variables -> Actions -> add secrets:
   `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.
4. Actions tab -> daily-short -> Run workflow. Check the result (it uploads as PRIVATE).
5. When you are happy: add a repo *variable* `PRIVACY` = `public`.

## Important limits
- New, unaudited YouTube API projects can only upload PRIVATE videos. To post public you
  must pass YouTube's API compliance audit (a Google form).
- YouTube's default API quota allows roughly 6 uploads per day.
- Fully automatic, repetitive AI uploads can trigger YouTube's "inauthentic/mass-produced
  content" policy. Keep PRIVACY=private and review, or vary topics and add your own footage.
- TikTok and Instagram are not included: their posting APIs need app approval/audit.

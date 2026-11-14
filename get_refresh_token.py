"""Optional: get a YouTube refresh token on a machine with a browser.
Usage: python get_refresh_token.py client_secret.json"""
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
flow = InstalledAppFlow.from_client_secrets_file(
    sys.argv[1], scopes=["https://www.googleapis.com/auth/youtube.upload"])
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
print("\nYT_REFRESH_TOKEN =", creds.refresh_token)

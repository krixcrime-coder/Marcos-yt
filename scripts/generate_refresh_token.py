"""Generate a long-lived YouTube OAuth refresh token locally.

Usage:
  python scripts/generate_refresh_token.py path/to/client_secret.json

The script opens Google's consent page in a browser. Copy only the printed
refresh token into the YOUTUBE_REFRESH_TOKEN GitHub Actions secret.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("client_secret", type=Path)
    args = parser.parse_args()
    if not args.client_secret.exists():
        parser.error(f"Client secret file does not exist: {args.client_secret}")

    flow = InstalledAppFlow.from_client_secrets_file(str(args.client_secret), SCOPES)
    credentials = flow.run_local_server(
        port=0,
        access_type="offline",
        prompt="consent",
    )
    if not credentials.refresh_token:
        raise RuntimeError(
            "Google did not return a refresh token. Revoke the app grant and run again."
        )
    print("\nYOUTUBE_REFRESH_TOKEN=")
    print(credentials.refresh_token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
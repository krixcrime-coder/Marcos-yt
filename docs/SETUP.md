# YouTube Auto Uploader setup

This repository schedules videos from a public Google Drive folder as private
YouTube uploads. YouTube publishes each upload automatically at the next free
time in `PUBLISH_TIMES`.

## Credential safety

Do not put API keys, OAuth client secrets, service-account private keys, or
refresh tokens in tracked files, zip files, `.env` files that will be shared,
or source code. A `.env` file is only acceptable as an untracked local file on
your own computer. GitHub Actions must receive runtime credentials through
GitHub Actions Secrets; otherwise anyone who can read the repository can use
the credentials.

The uploaded `marcos-yt-*.json` file is a Google service-account credential.
It is not a replacement for the YouTube desktop OAuth client. Do not upload it
to GitHub. The uploaded `client_secret_*.json` file is the correct input to the
refresh-token helper, but it must remain outside the repository.

## 1. Prepare the repository

Push this project to `krixcrime-coder/yt-auto-uploader`, or copy these files into
that repository:

```text
config/
  descriptions.txt
  tags.json
  titles.txt
data/
  reports.json
  state.json
uploader/
  config.py
  drive.py
  metadata.py
  models.py
  runner.py
  scheduler.py
  state.py
  youtube.py
.github/workflows/youtube-auto-uploader.yml
requirements.txt
```

Edit the files in `config/` directly. Titles are one per line, descriptions are
separated by a line containing exactly `---`, and tags are JSON arrays.

## 2. Create the Google API project

1. Open Google Cloud Console and create or select a project.
2. Enable **YouTube Data API v3** and **Google Drive API**.
3. Configure the OAuth consent screen. Add your YouTube account as a test user
   while the app is in testing mode.
4. Create an OAuth 2.0 **Desktop app** client. Download the client secret JSON.
5. Install dependencies locally and generate the refresh token:

   ```bash
   python -m venv .venv
   . .venv/bin/activate
   python -m pip install -r requirements.txt
   python scripts/generate_refresh_token.py /path/to/client_secret.json
   ```

   Complete Google's consent flow and keep the printed refresh token private.
   It is not a password that belongs in Git.

## 3. Make the Drive folder public

The folder must be shared as **Anyone with the link: Viewer**. Every video
file that should be uploaded must inherit that access. Copy the folder ID from
the URL:

```text
https://drive.google.com/drive/folders/<DRIVE_FOLDER_ID>
```

The Drive API key is used only for listing public files. Do not put the OAuth
client secret or refresh token in the Drive folder.

## 4. Add GitHub Actions secrets

In the target repository, open **Settings → Secrets and variables → Actions**.
Add these repository secrets:

| Secret | Value |
| --- | --- |
| `DRIVE_FOLDER_ID` | `1vm7O3p9JiEqRV9p_xzmP9RIItVkDM66Z` |
| `DRIVE_API_KEY` | Google Cloud API key restricted to Drive API |
| `YOUTUBE_CLIENT_ID` | OAuth desktop client ID |
| `YOUTUBE_CLIENT_SECRET` | OAuth desktop client secret |
| `YOUTUBE_REFRESH_TOKEN` | Token printed by `generate_refresh_token.py` |

Recommended repository variables (not secrets):

| Variable | Example | Meaning |
| --- | --- | --- |
| `PUBLISH_TIMES` | `08:00,20:00` | Local publish times, comma-separated |
| `PUBLISH_TIMEZONE` | `America/New_York` | IANA timezone for those times |
| `DAILY_UPLOAD_LIMIT` | `10` | Safety cap for successful uploads per day |
| `MAX_UPLOADS_PER_RUN` | `2` | Optional cap per workflow run |
| `DRIVE_SORT_FIELD` | `name` | `name`, `createdTime`, or `modifiedTime` |
| `SCHEDULE_LOOKAHEAD_DAYS` | `90` | How far ahead the slot allocator may search |

The workflow has write permission because it commits `data/state.json` and
`data/reports.json` back to the repository. If your organization blocks
workflow write access, enable it in repository Actions settings.

## 5. Run it safely

Use **Actions → YouTube auto uploader → Run workflow** for the first run.
Before a real upload, run locally with a copy of the repository and
`--dry-run`. The dry run lists the next videos and slots without changing state,
downloading files, or calling YouTube.

The scheduled workflow runs daily at 00:15 UTC. It uploads up to the number of
configured slots (or `MAX_UPLOADS_PER_RUN`, if set), then assigns each upload
to the next unfilled future slot.

## 6. How persistence works

- `data/state.json` stores the next sequence index, uploaded Drive IDs, and
  filled publish slots.
- `data/reports.json` stores one success or failure record per attempted video.
- A successful upload advances the sequence and fills its slot.
- A failed upload is logged and remains the next item for the following run.
- The workflow uses a concurrency lock so two runs cannot fill the same slot.

If you deliberately reorder or remove Drive files, keep in mind that sequence
selection is based on the configured sort field. Do not manually delete IDs
from `data/state.json` unless you intend to reprocess those files.

## YouTube scheduling notes

The uploader sends `privacyStatus: private` with `publishAt` in UTC. YouTube
will automatically publish the video at that time. The channel must be allowed
to schedule videos, and the scheduled time must be in the future.

The daily cap here is an application safety limit. YouTube API quota units and
YouTube's account/channel limits are separate; keep this number conservative.
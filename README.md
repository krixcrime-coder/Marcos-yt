# YouTube Auto Uploader

This repository contains the GitHub Actions automation that selects public
Google Drive videos in sequence and schedules them as private YouTube uploads.

## Quick start

1. Copy `.env.example` to `.env` for a local test.
2. Put your real values only in the untracked local `.env`.
3. Install Python dependencies:

   ```bash
   python -m venv .venv
   . .venv/bin/activate
   python -m pip install -r requirements.txt
   ```

4. Generate the YouTube refresh token:

   ```bash
   python scripts/generate_refresh_token.py /path/to/client_secret.json
   ```

5. Run a safe local preview:

   ```bash
   set -a
   . .env
   set +a
   python -m uploader --dry-run
   ```

6. Read `docs/SETUP.md` before enabling the GitHub Actions workflow.

## Security

Never commit `.env`, Google client-secret JSON files, service-account JSON
files, refresh tokens, or API keys. The workflow receives these values through
GitHub Actions secret variables at runtime. This is required because a
committed `.env` is readable by anyone with repository access and cannot be
made safe by renaming the file.
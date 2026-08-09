# YouTube Auto Uploader

An automation bundle that selects public Google Drive videos in sequence and uploads them to YouTube as scheduled private videos through GitHub Actions.

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

- `uploader/` — Python runner, Drive source, OAuth-backed YouTube uploader, metadata selection, slot scheduling, and durable JSON state.
- `config/` — user-editable title, description, and tag options.
- `data/` — committed upload pointer, filled publish slots, and per-video reports.
- `.github/workflows/youtube-auto-uploader.yml` — daily/manual automation workflow.
- `docs/SETUP.md` — Google Cloud, OAuth, GitHub secret, and first-run instructions.
- `scripts/generate_refresh_token.py` — local one-time OAuth consent helper.

## Architecture decisions

- Drive videos are ordered using `DRIVE_SORT_FIELD` and the pointer advances only after a successful YouTube upload.
- Publish slots are keyed by local wall-clock time and sent to YouTube as UTC timestamps.
- Failed uploads are logged but intentionally remain the next sequence item for retry.
- GitHub Actions serializes runs and commits only `data/state.json` and `data/reports.json`.

## Product

The first milestone provides a scheduled uploader that rotates metadata, downloads the next public Drive video in HD, schedules it privately on YouTube, and records the result for later reporting or companion-app use.

## User preferences

The target repository is `https://github.com/krixcrime-coder/yt-auto-uploader`.

## Gotchas

- Keep OAuth client secrets and refresh tokens only in GitHub Actions secrets; never commit them.
- The public Drive folder must allow viewer access to each video.
- Configure `PUBLISH_TIMEZONE` explicitly when publish times are not UTC.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ConfigurationError(ValueError):
    """Raised when required uploader configuration is missing or invalid."""


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigurationError(f"Missing required environment variable: {name}")
    return value


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer, got {raw!r}") from exc
    if value < 1:
        raise ConfigurationError(f"{name} must be at least 1")
    return value


def _time_slots(raw: str) -> tuple[time, ...]:
    slots: list[time] = []
    for item in raw.split(","):
        value = item.strip()
        if not value:
            continue
        try:
            hour, minute = (int(part) for part in value.split(":", 1))
            parsed = time(hour=hour, minute=minute)
        except (ValueError, TypeError) as exc:
            raise ConfigurationError(
                f"PUBLISH_TIMES must be comma-separated HH:MM values, got {value!r}"
            ) from exc
        slots.append(parsed)
    if not slots:
        raise ConfigurationError("PUBLISH_TIMES must contain at least one time")
    return tuple(sorted(set(slots)))


@dataclass(frozen=True)
class Settings:
    drive_folder_id: str
    drive_api_key: str
    youtube_client_id: str
    youtube_client_secret: str
    youtube_refresh_token: str
    publish_times: tuple[time, ...]
    publish_timezone: ZoneInfo
    daily_upload_limit: int
    max_uploads_per_run: int | None
    lookahead_days: int
    drive_sort_field: str
    metadata_dir: str
    state_path: str
    reports_path: str

    @classmethod
    def from_environment(cls) -> "Settings":
        timezone_name = os.getenv("PUBLISH_TIMEZONE", "UTC").strip() or "UTC"
        try:
            publish_timezone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise ConfigurationError(
                f"PUBLISH_TIMEZONE is not a valid IANA timezone: {timezone_name!r}"
            ) from exc

        raw_max = os.getenv("MAX_UPLOADS_PER_RUN", "").strip()
        max_uploads_per_run: int | None = None
        if raw_max:
            try:
                max_uploads_per_run = int(raw_max)
            except ValueError as exc:
                raise ConfigurationError("MAX_UPLOADS_PER_RUN must be an integer") from exc
            if max_uploads_per_run < 1:
                raise ConfigurationError("MAX_UPLOADS_PER_RUN must be at least 1")

        sort_field = os.getenv("DRIVE_SORT_FIELD", "name").strip()
        if sort_field not in {"name", "createdTime", "modifiedTime"}:
            raise ConfigurationError(
                "DRIVE_SORT_FIELD must be one of name, createdTime, modifiedTime"
            )

        return cls(
            drive_folder_id=_required("DRIVE_FOLDER_ID"),
            drive_api_key=_required("DRIVE_API_KEY"),
            youtube_client_id=_required("YOUTUBE_CLIENT_ID"),
            youtube_client_secret=_required("YOUTUBE_CLIENT_SECRET"),
            youtube_refresh_token=_required("YOUTUBE_REFRESH_TOKEN"),
            publish_times=_time_slots(os.getenv("PUBLISH_TIMES", "08:00,20:00")),
            publish_timezone=publish_timezone,
            daily_upload_limit=_positive_int("DAILY_UPLOAD_LIMIT", 10),
            max_uploads_per_run=max_uploads_per_run,
            lookahead_days=_positive_int("SCHEDULE_LOOKAHEAD_DAYS", 90),
            drive_sort_field=sort_field,
            metadata_dir=os.getenv("METADATA_DIR", "config"),
            state_path=os.getenv("STATE_PATH", "data/state.json"),
            reports_path=os.getenv("REPORTS_PATH", "data/reports.json"),
        )

    @property
    def uploads_per_run(self) -> int:
        return self.max_uploads_per_run or len(self.publish_times)
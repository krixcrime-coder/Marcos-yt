from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .models import UploadSlot
from .state import UploaderState


def _slot_key(local_dt: datetime) -> str:
    return local_dt.isoformat(timespec="minutes")


def _to_utc_iso(local_dt: datetime) -> str:
    return (
        local_dt.astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def next_available_slot(
    state: UploaderState,
    *,
    now: datetime,
    publish_times: tuple[time, ...],
    publish_timezone: ZoneInfo,
    lookahead_days: int,
) -> UploadSlot:
    local_now = now.astimezone(publish_timezone)
    for day_offset in range(lookahead_days + 1):
        date = local_now.date() + timedelta(days=day_offset)
        for slot_time in publish_times:
            candidate = datetime.combine(date, slot_time, tzinfo=publish_timezone)
            if candidate <= local_now + timedelta(minutes=5):
                continue
            key = _slot_key(candidate)
            if key not in state.scheduled_slots:
                return UploadSlot(key=key, publish_at_utc=_to_utc_iso(candidate))
    raise RuntimeError(
        f"No available publish slot in the next {lookahead_days} days; "
        "increase SCHEDULE_LOOKAHEAD_DAYS or add more PUBLISH_TIMES"
    )
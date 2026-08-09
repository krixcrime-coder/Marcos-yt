from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DriveVideo:
    file_id: str
    name: str
    mime_type: str
    size: int | None = None
    created_time: str | None = None
    modified_time: str | None = None

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> "DriveVideo":
        raw_size = payload.get("size")
        return cls(
            file_id=str(payload["id"]),
            name=str(payload.get("name") or payload["id"]),
            mime_type=str(payload.get("mimeType") or "application/octet-stream"),
            size=int(raw_size) if raw_size else None,
            created_time=payload.get("createdTime"),
            modified_time=payload.get("modifiedTime"),
        )


@dataclass(frozen=True)
class Metadata:
    title: str
    description: str
    tags: list[str]


@dataclass(frozen=True)
class UploadSlot:
    key: str
    publish_at_utc: str


@dataclass(frozen=True)
class UploadResult:
    youtube_video_id: str
    slot: UploadSlot


def utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
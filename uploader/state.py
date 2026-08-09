from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import utc_now_iso


@dataclass
class UploaderState:
    version: int = 1
    next_index: int = 0
    uploaded_file_ids: list[str] = field(default_factory=list)
    scheduled_slots: dict[str, str] = field(default_factory=dict)
    last_run_at: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "UploaderState":
        scheduled = payload.get("scheduled_slots", {})
        if not isinstance(scheduled, dict):
            raise ValueError("scheduled_slots must be an object")
        raw_index = payload.get("next_index", 0)
        if not isinstance(raw_index, int) or raw_index < 0:
            raise ValueError("next_index must be a non-negative integer")
        return cls(
            version=int(payload.get("version", 1)),
            next_index=raw_index,
            uploaded_file_ids=[str(item) for item in payload.get("uploaded_file_ids", [])],
            scheduled_slots={str(key): str(value) for key, value in scheduled.items()},
            last_run_at=payload.get("last_run_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "next_index": self.next_index,
            "uploaded_file_ids": self.uploaded_file_ids,
            "scheduled_slots": self.scheduled_slots,
            "last_run_at": self.last_run_at,
        }

    def mark_uploaded(self, file_id: str, slot_key: str) -> None:
        if file_id not in self.uploaded_file_ids:
            self.uploaded_file_ids.append(file_id)
        self.scheduled_slots[slot_key] = file_id


def _write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_path = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


def load_state(path: str) -> UploaderState:
    state_path = Path(path)
    if not state_path.exists():
        return UploaderState()
    with state_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"State file must contain a JSON object: {path}")
    return UploaderState.from_dict(payload)


def save_state(path: str, state: UploaderState) -> None:
    state.last_run_at = utc_now_iso()
    _write_json_atomic(Path(path), state.to_dict())


def load_reports(path: str) -> list[dict[str, Any]]:
    report_path = Path(path)
    if not report_path.exists():
        return []
    with report_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"Reports file must contain a JSON array: {path}")
    return [item for item in payload if isinstance(item, dict)]


def append_report(path: str, report: dict[str, Any]) -> None:
    reports = load_reports(path)
    reports.append(report)
    _write_json_atomic(Path(path), reports)
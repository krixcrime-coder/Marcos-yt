from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import ConfigurationError, Settings
from .drive import DriveSource
from .metadata import MetadataError, MetadataPool
from .models import DriveVideo, Metadata, UploadSlot, utc_now_iso
from .scheduler import next_available_slot
from .state import append_report, load_reports, load_state, save_state
from .youtube import YouTubeUploader

LOGGER = logging.getLogger("youtube-uploader")


def _configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _daily_success_count(reports: list[dict[str, Any]], local_date: str) -> int:
    return sum(
        1
        for report in reports
        if report.get("status") == "success"
        and str(report.get("uploaded_at", "")).startswith(local_date)
    )


def _next_video(
    videos: list[DriveVideo],
    state_uploaded: set[str],
    start_index: int,
) -> tuple[int, DriveVideo] | None:
    for index in range(start_index, len(videos)):
        video = videos[index]
        if video.file_id not in state_uploaded:
            return index, video
    return None


def _success_report(
    video: DriveVideo,
    metadata: Metadata,
    slot: UploadSlot,
    youtube_video_id: str,
) -> dict[str, Any]:
    return {
        "uploaded_at": utc_now_iso(),
        "status": "success",
        "drive_file_id": video.file_id,
        "filename": video.name,
        "youtube_video_id": youtube_video_id,
        "scheduled_publish_at": slot.publish_at_utc,
        "slot_key": slot.key,
        "metadata": {
            "title": metadata.title,
            "description": metadata.description,
            "tags": metadata.tags,
        },
    }


def _failure_report(
    video: DriveVideo,
    metadata: Metadata | None,
    slot: UploadSlot | None,
    error: Exception,
) -> dict[str, Any]:
    return {
        "uploaded_at": utc_now_iso(),
        "status": "failed",
        "drive_file_id": video.file_id,
        "filename": video.name,
        "error": f"{type(error).__name__}: {error}",
        "scheduled_publish_at": slot.publish_at_utc if slot else None,
        "slot_key": slot.key if slot else None,
        "metadata": (
            {
                "title": metadata.title,
                "description": metadata.description,
                "tags": metadata.tags,
            }
            if metadata
            else None
        ),
    }


def run(*, dry_run: bool = False) -> int:
    settings = Settings.from_environment()
    state = load_state(settings.state_path)
    reports = load_reports(settings.reports_path)
    metadata_pool = MetadataPool(settings.metadata_dir)
    drive = DriveSource(
        settings.drive_folder_id,
        settings.drive_api_key,
        settings.drive_sort_field,
    )
    videos = drive.list_videos()
    LOGGER.info(
        "Found %d video files; next sequence index is %d",
        len(videos),
        state.next_index,
    )

    local_today = datetime.now(settings.publish_timezone).date().isoformat()
    remaining_quota = settings.daily_upload_limit - _daily_success_count(
        reports, local_today
    )
    upload_count = min(settings.uploads_per_run, max(remaining_quota, 0))
    if upload_count == 0:
        LOGGER.info("Daily upload limit reached; nothing to upload")
        return 0

    uploaded_ids = set(state.uploaded_file_ids)
    completed = 0
    youtube_uploader: YouTubeUploader | None = None
    if not dry_run:
        youtube_uploader = YouTubeUploader(
            settings.youtube_client_id,
            settings.youtube_client_secret,
            settings.youtube_refresh_token,
        )

    for _ in range(upload_count):
        next_video = _next_video(videos, uploaded_ids, state.next_index)
        if not next_video:
            LOGGER.info("No unprocessed videos remain in the Drive folder")
            break
        index, video = next_video
        metadata: Metadata | None = None
        slot: UploadSlot | None = None
        temporary_path: Path | None = None
        try:
            metadata = metadata_pool.choose()
            slot = next_available_slot(
                state,
                now=datetime.now(timezone.utc),
                publish_times=settings.publish_times,
                publish_timezone=settings.publish_timezone,
                lookahead_days=settings.lookahead_days,
            )
            if dry_run:
                LOGGER.info(
                    "[dry-run] %s -> %s using title %r",
                    video.name,
                    slot.publish_at_utc,
                    metadata.title,
                )
                continue

            temporary_path = drive.download_to_temp(video)
            if youtube_uploader is None:
                raise RuntimeError("YouTube uploader was not initialized")
            result = youtube_uploader.upload(temporary_path, metadata, slot)
            state.next_index = index + 1
            state.mark_uploaded(video.file_id, slot.key)
            uploaded_ids.add(video.file_id)
            append_report(
                settings.reports_path,
                _success_report(video, metadata, slot, result.youtube_video_id),
            )
            completed += 1
        except Exception as error:  # noqa: BLE001 - report the failure and preserve order
            LOGGER.exception("Upload failed for %s", video.name)
            append_report(
                settings.reports_path,
                _failure_report(video, metadata, slot, error),
            )
            LOGGER.error(
                "The failed file remains at sequence index %d and will be retried next run",
                index,
            )
            break
        finally:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()
        save_state(settings.state_path, state)

    # A dry run must not mutate the committed state file, including its
    # last_run_at timestamp.
    LOGGER.info("Run finished: %d upload(s) completed", completed)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list the next uploads without downloading or uploading videos",
    )
    args = parser.parse_args(argv)
    _configure_logging()
    try:
        return run(dry_run=args.dry_run)
    except (ConfigurationError, MetadataError, ValueError, RuntimeError) as error:
        LOGGER.error("%s", error)
        return 2
    except Exception as error:  # noqa: BLE001 - fail clearly for the workflow
        LOGGER.exception("Unexpected uploader error: %s", error)
        return 1
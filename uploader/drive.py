from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from .models import DriveVideo

LOGGER = logging.getLogger(__name__)


class DriveSource:
    def __init__(self, folder_id: str, api_key: str, sort_field: str = "name") -> None:
        self.folder_id = folder_id
        self.sort_field = sort_field
        self.service = build("drive", "v3", developerKey=api_key, cache_discovery=False)

    def list_videos(self) -> list[DriveVideo]:
        files: list[DriveVideo] = []
        page_token: str | None = None
        query = (
            f"'{self.folder_id}' in parents and trashed = false "
            "and mimeType contains 'video/'"
        )
        fields = (
            "nextPageToken,files(id,name,mimeType,size,createdTime,modifiedTime)"
        )
        while True:
            response: dict[str, Any] = (
                self.service.files()
                .list(
                    q=query,
                    spaces="drive",
                    fields=fields,
                    pageSize=1000,
                    pageToken=page_token,
                )
                .execute()
            )
            files.extend(
                DriveVideo.from_api(payload)
                for payload in response.get("files", [])
            )
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        def sort_key(video: DriveVideo) -> str:
            value = getattr(video, self.sort_field)
            return str(value or "").casefold()

        return sorted(files, key=lambda video: (sort_key(video), video.file_id))

    def download(self, video: DriveVideo, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        request = self.service.files().get_media(fileId=video.file_id)
        with destination.open("wb") as handle:
            downloader = MediaIoBaseDownload(handle, request, chunksize=10 * 1024 * 1024)
            completed = False
            while not completed:
                _, completed = downloader.next_chunk()
        LOGGER.info("Downloaded %s to %s", video.name, destination)

    def download_to_temp(self, video: DriveVideo) -> Path:
        suffix = Path(video.name).suffix or ".mp4"
        handle = tempfile.NamedTemporaryFile(
            prefix="youtube-upload-",
            suffix=suffix,
            delete=False,
        )
        destination = Path(handle.name)
        handle.close()
        self.download(video, destination)
        return destination
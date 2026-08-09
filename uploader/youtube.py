from __future__ import annotations

import logging
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from .models import Metadata, UploadResult, UploadSlot

LOGGER = logging.getLogger(__name__)

YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"


class YouTubeUploader:
    def __init__(self, client_id: str, client_secret: str, refresh_token: str) -> None:
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=[YOUTUBE_UPLOAD_SCOPE],
        )
        self.service = build("youtube", "v3", credentials=credentials, cache_discovery=False)

    def upload(
        self,
        video_path: Path,
        metadata: Metadata,
        slot: UploadSlot,
        *,
        category_id: str = "22",
    ) -> UploadResult:
        body = {
            "snippet": {
                "title": metadata.title,
                "description": metadata.description,
                "tags": metadata.tags,
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": "private",
                "publishAt": slot.publish_at_utc,
                "selfDeclaredMadeForKids": False,
            },
        }
        media = MediaFileUpload(
            str(video_path),
            mimetype="video/*",
            chunksize=8 * 1024 * 1024,
            resumable=True,
        )
        request = self.service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )
        response = None
        while response is None:
            _, response = request.next_chunk()
        video_id = response.get("id")
        if not video_id:
            raise RuntimeError("YouTube upload completed without returning a video ID")
        LOGGER.info(
            "Uploaded %s as %s, scheduled for %s",
            video_path.name,
            video_id,
            slot.publish_at_utc,
        )
        return UploadResult(youtube_video_id=video_id, slot=slot)
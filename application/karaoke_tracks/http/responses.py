import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel

from application.karaoke_tracks.models import (
    TrackCreatingTask,
    KaraokeTrack,
    TrackCreatingTaskStatus,
    TranscriptItem,
)


class TrackCreatingTaskResponse(BaseModel):
    id: uuid.UUID
    base_track_file: str
    result_track_id: Optional[uuid.UUID] = None
    vocal_file: Optional[str] = None
    instrumental_file: Optional[str] = None
    lang_code: str
    transcript: Optional[List[TranscriptItem]] = None
    status: TrackCreatingTaskStatus
    split_at: Optional[datetime] = None
    split_retries: Optional[int] = None
    transcribed_at: Optional[datetime] = None
    transcript_retries: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm(cls, task: TrackCreatingTask) -> "TrackCreatingTaskResponse":
        return cls(
            id=task.id,
            base_track_file=task.base_track_file,
            result_track_id=task.result_track_id,
            vocal_file=task.vocal_file,
            instrumental_file=task.instrumental_file,
            lang_code=task.lang_code,
            transcript=task.transcript,
            status=task.status,
            split_at=task.split_at,
            split_retries=task.split_retries,
            transcribed_at=task.transcribed_at,
            transcript_retries=task.transcript_retries,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )


class KaraokeTrackResponse(BaseModel):
    id: uuid.UUID
    base_track_file: str
    vocal_file: str
    instrumental_file: str
    lang_code: str
    transcript: Optional[List[TranscriptItem]] = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm(cls, track: KaraokeTrack) -> "KaraokeTrackResponse":
        return cls(
            id=track.id,
            base_track_file=track.base_track_file,
            vocal_file=track.vocal_file,
            instrumental_file=track.instrumental_file,
            lang_code=track.lang_code,
            transcript=track.transcript,
            created_at=track.created_at,
            updated_at=track.updated_at,
        )

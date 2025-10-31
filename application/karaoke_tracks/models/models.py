import enum
import uuid
from typing import Optional, List, Any

from sqlalchemy import UUID, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum

from pydantic import BaseModel, Field

from core.models.base import Base
from core.models.fields import uuid_pk, optional_date_time_tz, PydanticListType


class TrackCreatingTaskStatus(str, enum.Enum):
    CREATED = "created"
    SPLIT_STARTED = "split_started"
    SPLIT_ITERATION_FAILED = "split_iteration_failed"
    SPLIT_FINAL_FAILED = "split_final_failed"
    SPLIT_COMPLETED = "split_completed"
    TRANSCRIPT_STARTED = "transcript_started"
    TRANSCRIPT_ITERATION_FAILED = "transcript_iteration_failed"
    TRANSCRIPT_FINAL_FAILED = "transcript_final_failed"
    COMPLETED = "completed"


class TrackCreatingTaskLogStep(str, enum.Enum):
    SPLIT_START = "split_start"
    SPLIT_SUCCESS = "split_success"
    SPLIT_ERROR = "split_error"
    TRANSCRIPT_START = "transcript_start"
    TRANSCRIPT_SUCCESS = "transcript_success"
    TRANSCRIPT_ERROR = "transcript_error"


class TranscriptItem(BaseModel):
    text: str = Field(description="Текст произнесенной фразы")
    start: int = Field(description="Время начала в миллисекундах")
    end: int = Field(description="Время окончания в миллисекундах")
    confidence: float = Field(description="Уверенность в распознавании", ge=0, le=1)
    speaker: Optional[str] = Field(description="Идентификатор говорящего", default=None)


class KaraokeTrack(Base):
    __tablename__ = "karaoke_tracks"

    id: Mapped[uuid_pk]
    base_track_file: Mapped[str] = mapped_column(String, nullable=False)
    vocal_file: Mapped[str] = mapped_column(String, nullable=False)
    instrumental_file: Mapped[str] = mapped_column(String, nullable=False)
    lang_code: Mapped[str] = mapped_column(String(10), nullable=False)
    transcript: Mapped[Optional[List[TranscriptItem]]] = mapped_column(
        PydanticListType(TranscriptItem), nullable=True
    )

    # Связь с задачей создания
    creating_task: Mapped["TrackCreatingTask"] = relationship(
        "TrackCreatingTask", back_populates="result_track", uselist=False
    )


class TrackCreatingTask(Base):
    __tablename__ = "karaoke_track_creating_tasks"

    id: Mapped[uuid_pk]
    base_track_file: Mapped[str] = mapped_column(String, nullable=False)
    result_track_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("karaoke_tracks.id"), nullable=True
    )
    vocal_file: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    instrumental_file: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    lang_code: Mapped[str] = mapped_column(String(10), nullable=False)
    transcript: Mapped[Optional[List[TranscriptItem]]] = mapped_column(
        PydanticListType(TranscriptItem), nullable=True
    )

    status: Mapped[TrackCreatingTaskStatus] = mapped_column(
        Enum(TrackCreatingTaskStatus, native_enum=False),
        default=TrackCreatingTaskStatus.CREATED,
        nullable=False,
    )

    split_at: Mapped[optional_date_time_tz]
    split_retries: Mapped[Optional[int]] = mapped_column(Integer, default=0)

    transcribed_at: Mapped[optional_date_time_tz]
    transcript_retries: Mapped[Optional[int]] = mapped_column(Integer, default=0)

    # Связи
    result_track: Mapped[Optional["KaraokeTrack"]] = relationship(
        "KaraokeTrack", back_populates="creating_task", foreign_keys=[result_track_id]
    )
    logs: Mapped[List["TrackCreatingTaskLog"]] = relationship(
        "TrackCreatingTaskLog", back_populates="task", cascade="all, delete-orphan"
    )


class TrackCreatingTaskLog(Base):
    __tablename__ = "karaoke_track_creating_task_logs"

    id: Mapped[uuid_pk]
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("karaoke_track_creating_tasks.id"),
        nullable=False,
    )
    step: Mapped[TrackCreatingTaskLogStep] = mapped_column(
        Enum(TrackCreatingTaskLogStep, native_enum=False),
        default=TrackCreatingTaskLogStep.SPLIT_START,
        nullable=False,
    )
    data: Mapped[Any] = mapped_column(JSONB, nullable=False)

    # Связи
    task: Mapped["TrackCreatingTask"] = relationship(
        "TrackCreatingTask", back_populates="logs"
    )

import enum
import uuid
from typing import Optional, List, Any, Dict

from sqlalchemy import UUID, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum

from pydantic import BaseModel, Field

from core.models.base import Base
from core.models.fields import uuid_pk, optional_date_time_tz, PydanticListType


class TrackCreatingTaskStatus(str, enum.Enum):
    CREATED = "created"
    IN_SPLIT_PROCESS = "in_split_process"
    SPLIT_COMPLETED = "split_completed"
    IN_TRANSCRIPT_PROCESS = "in_transcript_process"
    TRANSCRIPT_COMPLETED = "transcript_completed"
    IN_SUBTITLES_PROCESS = "in_subtitles_process"
    SUBTITLES_COMPLETED = "subtitles_completed"
    COMPLETED = "completed"
    FAILED = "failed"


class TrackCreatingTaskStepType(str, enum.Enum):
    SPLIT = "split"
    TRANSCRIPT = "transcript"
    SUBTITLES = "subtitles"


class TrackCreatingTaskStepStatus(str, enum.Enum):
    INIT = "init"
    IN_PROCESS = "in_process"
    COMPLETED = "completed"
    FAILED = "failed"
    FINAL_FAILED = "final_failed"


class TranscriptItem(BaseModel):
    text: str = Field(description="Текст произнесенной фразы")
    start: int = Field(description="Время начала в миллисекундах")
    end: int = Field(description="Время окончания в миллисекундах")
    words: List["WordItem"] = Field(description="Слова из фразы")


class WordItem(BaseModel):
    text: str = Field(description="Слово")
    start: int = Field(description="Время начала в миллисекундах")
    end: int = Field(description="Время окончания в миллисекундах")
    confidence: float = Field(description="Уверенность в распознавании", ge=0, le=1)
    speaker: Optional[str] = Field(description="Идентификатор говорящего", default=None)


class SubtitleItem(BaseModel):
    text: str = Field(description="Текст субтитра")
    start: int = Field(description="Время начала в миллисекундах")
    end: int = Field(description="Время окончания в миллисекундах")


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
    words: Mapped[Optional[List[WordItem]]] = mapped_column(
        PydanticListType(WordItem), nullable=True
    )
    subtitles: Mapped[Optional[List[SubtitleItem]]] = mapped_column(
        PydanticListType(SubtitleItem), nullable=True
    )
    lang_code: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[TrackCreatingTaskStatus] = mapped_column(
        Enum(TrackCreatingTaskStatus, native_enum=False),
        default=TrackCreatingTaskStatus.CREATED,
        nullable=False,
    )

    # Связи
    result_track: Mapped[Optional["KaraokeTrack"]] = relationship(
        "KaraokeTrack", back_populates="creating_task", foreign_keys=[result_track_id]
    )
    steps: Mapped[List["TrackCreatingTaskStep"]] = relationship(
        "TrackCreatingTaskStep", back_populates="task", cascade="all, delete-orphan"
    )
    logs: Mapped[List["TrackCreatingTaskLog"]] = relationship(
        "TrackCreatingTaskLog", back_populates="task", cascade="all, delete-orphan"
    )


class TrackCreatingTaskStep(Base):
    __tablename__ = "karaoke_track_creating_task_steps"

    id: Mapped[uuid_pk]
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("karaoke_track_creating_tasks.id"),
        nullable=False,
    )
    data: Mapped[Optional[Any | Dict]] = mapped_column(JSONB, nullable=True)
    step: Mapped[TrackCreatingTaskStepType] = mapped_column(
        Enum(TrackCreatingTaskStepType, native_enum=False),
        nullable=False,
    )
    status: Mapped[TrackCreatingTaskStepStatus] = mapped_column(
        Enum(TrackCreatingTaskStepStatus, native_enum=False),
        nullable=False,
    )
    retries: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processed_at: Mapped[optional_date_time_tz]

    # Связи
    task: Mapped["TrackCreatingTask"] = relationship(
        "TrackCreatingTask", back_populates="steps"
    )
    logs: Mapped[List["TrackCreatingTaskLog"]] = relationship(
        "TrackCreatingTaskLog", back_populates="step", cascade="all, delete-orphan"
    )


class TrackCreatingTaskLog(Base):
    __tablename__ = "karaoke_track_creating_task_logs"

    id: Mapped[uuid_pk]
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("karaoke_track_creating_tasks.id"),
        nullable=False,
    )
    step_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("karaoke_track_creating_task_steps.id"),
        nullable=True,
    )
    data: Mapped[Any] = mapped_column(JSONB, nullable=False)

    # Связи
    task: Mapped["TrackCreatingTask"] = relationship(
        "TrackCreatingTask", back_populates="logs"
    )
    step: Mapped[Optional["TrackCreatingTaskStep"]] = relationship(
        "TrackCreatingTaskStep", back_populates="logs"
    )

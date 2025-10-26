"""Database models describing jobs, assets and metrics."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Column, Enum
from sqlmodel import Field, Relationship, SQLModel


class JobStatus(str, enum.Enum):
    """Lifecycle states for processing jobs."""

    CREATED = "created"
    UPLOADING = "uploading"
    SPLITTING = "splitting"
    WAITING_ASR = "waiting_asr"
    ALIGNING = "aligning"
    COMPLETED = "completed"
    FAILED = "failed"


class AssetType(str, enum.Enum):
    """Type of asset stored for a job."""

    ORIGINAL = "original"
    MINUS = "minus"
    VOCALS = "vocals"
    LYRICS = "lyrics"
    METADATA = "metadata"


class MetricType(str, enum.Enum):
    """Distinct metrics collected for processing."""

    SPLIT = "split"
    ASR = "asr"
    ALIGN = "align"


class Job(SQLModel, table=True):
    """Job representing karaoke track processing workflow."""

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    input_filename: str
    status: JobStatus = Field(
        sa_column=Column(Enum(JobStatus, native_enum=False, length=32), nullable=False)
    )
    split_progress: float = 0.0
    asr_progress: float = 0.0
    align_progress: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    completed_at: datetime | None = None
    error_message: str | None = None

    assets: list[Asset] = Relationship(back_populates="job")
    metrics: list[Metric] = Relationship(back_populates="job")


class Asset(SQLModel, table=True):
    """Asset stored for a job (S3 object)."""

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    job_id: str = Field(foreign_key="job.id")
    type: AssetType = Field(
        sa_column=Column(Enum(AssetType, native_enum=False, length=32), nullable=False)
    )
    s3_key: str
    url: str
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    job: Job | None = Relationship(back_populates="assets")


class Metric(SQLModel, table=True):
    """Metric describing processing statistics."""

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    job_id: str = Field(foreign_key="job.id")
    type: MetricType = Field(
        sa_column=Column(Enum(MetricType, native_enum=False, length=32), nullable=False)
    )
    name: str
    payload: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    job: Job | None = Relationship(back_populates="metrics")


__all__ = [
    "Asset",
    "AssetType",
    "Job",
    "JobStatus",
    "Metric",
    "MetricType",
]

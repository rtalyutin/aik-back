"""Pydantic schemas for API requests and responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .models import AssetType, JobStatus, MetricType


class PresignedUploadOut(BaseModel):
    """Presigned upload payload returned to clients."""

    url: str
    fields: dict[str, str]
    expires_in: int


class AssetOut(BaseModel):
    """Asset response representation."""

    type: AssetType
    url: str
    key: str


class MetricOut(BaseModel):
    """Metric response representation."""

    type: MetricType
    name: str
    payload: dict[str, Any]
    created_at: datetime


class ProgressOut(BaseModel):
    """Detailed progress across workflow stages."""

    split: float = Field(ge=0.0, le=1.0)
    asr: float = Field(ge=0.0, le=1.0)
    align: float = Field(ge=0.0, le=1.0)


class EnhancedLRCLine(BaseModel):
    """Single line of enhanced LRC."""

    start: float
    end: float
    text: str

    @property
    def lrc(self) -> str:
        minutes, seconds = divmod(self.start, 60)
        return f"[{int(minutes):02d}:{seconds:05.2f}]{self.text}"


class EnhancedLRC(BaseModel):
    """Enhanced LRC representation."""

    lines: list[EnhancedLRCLine]

    def to_string(self) -> str:
        return "\n".join(line.lrc for line in self.lines)


class JobCreateRequest(BaseModel):
    """Request payload for creating a job."""

    filename: str = Field(..., min_length=1)
    content_type: str | None = None


class JobResponse(BaseModel):
    """Representation of a job including progress."""

    id: str
    status: JobStatus
    progress: ProgressOut
    assets: list[AssetOut]
    metrics: list[MetricOut]
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    error_message: str | None
    upload: PresignedUploadOut | None = None
    lyrics: EnhancedLRC | None = None


class JobCreatedResponse(JobResponse):
    """Response returned after job creation."""


class JobListResponse(BaseModel):
    """Response with list of jobs."""

    jobs: list[JobResponse]


class ErrorResponse(BaseModel):
    """Standard API error response."""

    detail: str


class ASRWebhookPayload(BaseModel):
    """Payload sent by ASR provider to webhook."""

    job_id: str
    transcript: str
    signature: str | None = None


class ASRWebhookResponse(BaseModel):
    """Response confirming webhook processing."""

    status: str

"""Job API endpoints."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from ...db import async_session_factory, get_session
from ...dependencies import get_asr_service, get_lalal_service, get_s3_service
from ...models import Asset, AssetType, Job, JobStatus, Metric, MetricType
from ...schemas import (
    AssetOut,
    EnhancedLRC,
    EnhancedLRCLine,
    ErrorResponse,
    JobCreatedResponse,
    JobCreateRequest,
    JobResponse,
    MetricOut,
    PresignedUploadOut,
    ProgressOut,
)
from ...services.asr import ASRService
from ...services.lalal import LalalService
from ...services.s3 import PresignedUpload, TimewebS3Service
from ...workflows import fetch_job, list_jobs, process_split

SessionDep = Annotated[AsyncSession, Depends(get_session)]
S3ServiceDep = Annotated[TimewebS3Service, Depends(get_s3_service)]
LalalServiceDep = Annotated[LalalService, Depends(get_lalal_service)]
ASRServiceDep = Annotated[ASRService, Depends(get_asr_service)]

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _serialize_assets(assets: Iterable[Asset]) -> list[AssetOut]:
    return [
        AssetOut(type=asset.type, url=asset.url, key=asset.s3_key)
        for asset in assets
    ]


def _extract_lyrics(metrics: Iterable[Metric]) -> EnhancedLRC | None:
    for metric in metrics:
        if metric.type == MetricType.ALIGN:
            payload = metric.payload or {}
            lines_data = payload.get("lines") if isinstance(payload, dict) else None
            if isinstance(lines_data, list):
                try:
                    lines = [EnhancedLRCLine(**line) for line in lines_data]
                except TypeError:
                    return None
                return EnhancedLRC(lines=lines)
    return None


def _serialize_metrics(metrics: Iterable[Metric]) -> list[MetricOut]:
    return [
        MetricOut(
            type=metric.type,
            name=metric.name,
            payload=metric.payload,
            created_at=metric.created_at,
        )
        for metric in metrics
    ]


def _job_to_response(
    job: Job,
    *,
    upload: PresignedUpload | None = None,
) -> JobResponse:
    progress = ProgressOut(
        split=job.split_progress,
        asr=job.asr_progress,
        align=job.align_progress,
    )
    upload_out: PresignedUploadOut | None = None
    if upload:
        upload_out = PresignedUploadOut(
            url=upload.url, fields=upload.fields, expires_in=upload.expires_in
        )
    lyrics = _extract_lyrics(job.metrics)
    assets = _serialize_assets(job.assets)
    metrics = _serialize_metrics(job.metrics)
    return JobResponse(
        id=job.id,
        status=job.status,
        progress=progress,
        assets=assets,
        metrics=metrics,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
        upload=upload_out,
        lyrics=lyrics,
    )


@router.post(
    "",
    response_model=JobCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_job(
    payload: JobCreateRequest,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    s3_service: S3ServiceDep,
    lalal_service: LalalServiceDep,
    asr_service: ASRServiceDep,
) -> JobCreatedResponse:
    """Create a new job and return presigned URL for upload."""

    job = Job(
        input_filename=payload.filename,
        status=JobStatus.CREATED,
        split_progress=0.0,
        asr_progress=0.0,
        align_progress=0.0,
    )
    session.add(job)
    await session.flush()

    upload, original_descriptor = s3_service.generate_presigned_upload(payload.filename)

    session.add(
        Asset(
            job_id=job.id,
            type=AssetType.ORIGINAL,
            s3_key=original_descriptor.key,
            url=original_descriptor.url,
        )
    )
    job.status = JobStatus.UPLOADING
    job.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(job, attribute_names=["assets", "metrics"])

    background_tasks.add_task(
        process_split,
        job.id,
        payload.filename,
        async_session_factory,
        s3_service,
        lalal_service,
        asr_service,
    )

    return _job_to_response(job, upload=upload)


@router.get("/{job_id}", response_model=JobResponse, responses={404: {"model": ErrorResponse}})
async def get_job(job_id: str, session: SessionDep) -> JobResponse:
    job = await fetch_job(session, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _job_to_response(job)


@router.get("", response_model=list[JobResponse])
async def list_job_endpoint(session: SessionDep) -> list[JobResponse]:
    jobs = await list_jobs(session)
    return [_job_to_response(job) for job in jobs]

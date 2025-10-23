"""Workflow orchestration for karaoke job processing."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from .models import Asset, AssetType, Job, JobStatus, Metric, MetricType
from .schemas import EnhancedLRC, EnhancedLRCLine
from .services.align import AlignService
from .services.asr import ASRService
from .services.lalal import LalalService
from .services.s3 import TimewebS3Service

logger = logging.getLogger(__name__)


async def mark_job_failed(
    job_id: str,
    reason: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Update job status to failed with error message."""

    async with session_factory() as session:
        job = await session.get(Job, job_id)
        if job is None:
            return
        job.status = JobStatus.FAILED
        job.error_message = reason
        job.updated_at = datetime.utcnow()
        await session.commit()
        logger.error("Marked job %s as failed: %s", job_id, reason)


async def process_split(
    job_id: str,
    filename: str,
    session_factory: async_sessionmaker[AsyncSession],
    s3_service: TimewebS3Service,
    lalal_service: LalalService,
    asr_service: ASRService,
) -> None:
    """Launch the splitting workflow and schedule ASR."""

    async with session_factory() as session:
        job = await session.get(Job, job_id)
        if job is None:
            logger.warning("Job %s not found for split", job_id)
            return
        job.status = JobStatus.SPLITTING
        job.updated_at = datetime.utcnow()
        await session.commit()

    try:
        split_result = await lalal_service.split(job_id, filename)
    except Exception as exc:  # pragma: no cover - network failure simulation
        await mark_job_failed(job_id, f"split_failed: {exc}", session_factory)
        return

    minus_url = s3_service.generate_presigned_get(split_result.minus_key)
    vocals_url = s3_service.generate_presigned_get(split_result.vocals_key)

    async with session_factory() as session:
        job = await session.get(Job, job_id)
        if job is None:
            logger.warning("Job %s disappeared after split", job_id)
            return
        job.split_progress = 1.0
        job.status = JobStatus.WAITING_ASR
        job.updated_at = datetime.utcnow()

        assets = [
            Asset(
                job_id=job_id,
                type=AssetType.MINUS,
                s3_key=split_result.minus_key,
                url=minus_url,
            ),
            Asset(
                job_id=job_id,
                type=AssetType.VOCALS,
                s3_key=split_result.vocals_key,
                url=vocals_url,
            ),
        ]
        session.add_all(assets)
        metric = Metric(
            job_id=job_id,
            type=MetricType.SPLIT,
            name="lalal.split",
            payload=split_result.metrics,
        )
        session.add(metric)
        await session.commit()

    try:
        await asr_service.start_transcription(job_id, minus_url)
    except Exception as exc:  # pragma: no cover - network failure simulation
        await mark_job_failed(job_id, f"asr_failed: {exc}", session_factory)
        return

    async with session_factory() as session:
        job = await session.get(Job, job_id)
        if job is None:
            return
        job.asr_progress = 0.1
        job.updated_at = datetime.utcnow()
        await session.commit()
        logger.info("Job %s awaiting ASR callback", job_id)


async def process_alignment(
    job_id: str,
    transcript: str,
    session_factory: async_sessionmaker[AsyncSession],
    s3_service: TimewebS3Service,
    align_service: AlignService,
    asr_service: ASRService,
) -> EnhancedLRC | None:
    """Handle ASR webhook by running alignment and finalising job."""

    try:
        asr_result = await asr_service.build_result(transcript)
        alignment = await align_service.align(asr_result.words)
    except Exception as exc:  # pragma: no cover - network failure simulation
        await mark_job_failed(job_id, f"align_failed: {exc}", session_factory)
        return None

    lyrics_lines = [
        EnhancedLRCLine(start=line.start, end=line.end, text=line.text)
        for line in alignment.lines
    ]
    lrc_model = EnhancedLRC(lines=lyrics_lines)
    lyrics_key = f"jobs/{job_id}/lyrics.lrc"
    lyrics_url = s3_service.generate_presigned_get(lyrics_key)

    async with session_factory() as session:
        job = await session.get(Job, job_id)
        if job is None:
            logger.warning("Job %s missing during alignment", job_id)
            return lrc_model
        job.status = JobStatus.COMPLETED
        job.asr_progress = 1.0
        job.align_progress = 1.0
        job.completed_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        job.error_message = None

        session.add(
            Asset(
                job_id=job_id,
                type=AssetType.LYRICS,
                s3_key=lyrics_key,
                url=lyrics_url,
            )
        )
        session.add(
            Metric(
                job_id=job_id,
                type=MetricType.ASR,
                name="asr.result",
                payload={"transcript": asr_result.transcript},
            )
        )
        session.add(
            Metric(
                job_id=job_id,
                type=MetricType.ALIGN,
                name="align.result",
                payload={
                    "lines": [line.model_dump() for line in lyrics_lines],
                    "raw": lrc_model.to_string(),
                },
            )
        )
        await session.commit()
        logger.info("Job %s completed", job_id)

    return lrc_model


async def fetch_job(session: AsyncSession, job_id: str) -> Job | None:
    """Retrieve job including eager loaded relations."""

    query = select(Job).where(Job.id == job_id)
    result = await session.exec(query)
    job = result.one_or_none()
    if job:
        await session.refresh(job, attribute_names=["assets", "metrics"])
    return job


async def list_jobs(session: AsyncSession) -> Sequence[Job]:
    """Return list of jobs ordered by creation time."""

    query = select(Job).order_by(Job.created_at.desc())
    result = await session.exec(query)
    jobs = list(result.all())
    for job in jobs:
        await session.refresh(job, attribute_names=["assets", "metrics"])
    return jobs

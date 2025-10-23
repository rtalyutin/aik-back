"""Webhook endpoints for external providers."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from ...db import async_session_factory, get_session
from ...dependencies import get_align_service, get_asr_service, get_s3_service
from ...schemas import ASRWebhookPayload, ASRWebhookResponse, ErrorResponse
from ...services.align import AlignService
from ...services.asr import ASRService
from ...services.s3 import TimewebS3Service
from ...workflows import fetch_job, process_alignment

SessionDep = Annotated[AsyncSession, Depends(get_session)]
S3ServiceDep = Annotated[TimewebS3Service, Depends(get_s3_service)]
AlignServiceDep = Annotated[AlignService, Depends(get_align_service)]
ASRServiceDep = Annotated[ASRService, Depends(get_asr_service)]

router = APIRouter(prefix="/webhook", tags=["webhooks"])


@router.post(
    "/asr",
    response_model=ASRWebhookResponse,
    responses={404: {"model": ErrorResponse}},
)
async def handle_asr_webhook(
    payload: ASRWebhookPayload,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    s3_service: S3ServiceDep,
    align_service: AlignServiceDep,
    asr_service: ASRServiceDep,
) -> ASRWebhookResponse:
    job = await fetch_job(session, payload.job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    background_tasks.add_task(
        process_alignment,
        payload.job_id,
        payload.transcript,
        async_session_factory,
        s3_service,
        align_service,
        asr_service,
    )

    return ASRWebhookResponse(status="accepted")

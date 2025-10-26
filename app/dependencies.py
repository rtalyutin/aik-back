"""Dependency wiring for FastAPI application."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from .core.config import Settings, get_settings
from .services.align import AlignService
from .services.asr import ASRService
from .services.lalal import LalalService
from .services.s3 import TimewebS3Service

SettingsDep = Annotated[Settings, Depends(get_settings)]


def _build_s3(settings: Settings) -> TimewebS3Service:
    return TimewebS3Service(
        bucket=settings.s3_bucket,
        endpoint_url=settings.s3_endpoint_url,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        region_name=settings.s3_region_name,
        upload_expires=settings.s3_upload_expire_seconds,
        use_dummy=settings.feature_flags.use_dummy_s3,
    )


def _build_lalal(settings: Settings) -> LalalService:
    return LalalService(
        base_url=(
            settings.provider_options()["lalal"]["alternative_base_url"]
            if settings.feature_flags.enable_lalal_alternative
            else settings.provider_options()["lalal"]["base_url"]
        ),
        api_key=settings.provider_options()["lalal"]["api_key"],
        use_alternative=settings.feature_flags.enable_lalal_alternative,
    )


def _build_asr(settings: Settings) -> ASRService:
    return ASRService(
        provider=settings.provider_options()["asr"]["provider"],
        callback_secret=settings.provider_options()["asr"]["callback_secret"],
    )


def _build_align(settings: Settings) -> AlignService:
    provider = (
        "alternative"
        if settings.feature_flags.enable_align_alternative
        else settings.provider_options()["align"]["provider"]
    )
    return AlignService(provider=provider)


async def get_s3_service(settings: SettingsDep) -> TimewebS3Service:
    return _build_s3(settings)


async def get_lalal_service(settings: SettingsDep) -> LalalService:
    return _build_lalal(settings)


async def get_asr_service(settings: SettingsDep) -> ASRService:
    return _build_asr(settings)


async def get_align_service(settings: SettingsDep) -> AlignService:
    return _build_align(settings)


__all__ = [
    "SettingsDep",
    "get_align_service",
    "get_asr_service",
    "get_lalal_service",
    "get_s3_service",
]

from application.job_matcher.models import (
    JobMatcherResume,
)
from application.job_matcher.services import (
    ResumeCollector,
    DataForResumeCollection,
)
from application.job_matcher.services.llm_service import GetResumeError
from application.job_matcher.services.resume_collector import CollectResumeError
from core.database.uow import UoW
from typing import Dict, Any
from logger import setup_logging
import logging
from config import get_config

config = get_config()
setup_logging(config)
logger = logging.getLogger(__name__)


async def add_manual_resume(
    resume_text: str, resume_collector: ResumeCollector, uow: UoW
) -> JobMatcherResume:
    try:
        result = await resume_collector.collect_resume(
            DataForResumeCollection(resume_text=resume_text)
        )
    except (GetResumeError, CollectResumeError, Exception) as exception:
        log_data: Dict[str, Any] = {
            "exception": str(exception),
        }
        if isinstance(exception, GetResumeError):
            log_data["metainfo"] = exception.metainfo
        elif isinstance(exception, CollectResumeError):
            log_data["get_resume_result"] = exception.get_resume_result.model_dump()

        logger.warning("Failed to collect resume result", extra=log_data)

        raise exception

    async with uow:
        result.resume.is_active = False
        uow.session.add(result.resume)

        logger.info(
            "Successfully added manual resume",
            extra={
                "get_resume_result": result.get_resume_result.model_dump(),
            },
        )
        await uow.session.flush()
        await uow.session.refresh(result.resume)

        return result.resume

from application.job_matcher.models import (
    JobMatcherVacancy,
    SourceType,
    JobMatcherSourceProcessLog,
    JobMatcherVacancyWithResumeMatch,
)
from application.job_matcher.services import VacancyCollector, DataForVacancyCollection
from application.job_matcher.services.llm_service import GetVacancyError
from application.job_matcher.services.vacancy_collector import CollectVacancyError
from core.database.uow import UoW
from typing import Dict, Any
from sqlalchemy import select
from sqlalchemy.orm import selectinload


async def add_manual_vacancy(
    vacancy_text: str, vacancy_collector: VacancyCollector, uow: UoW
) -> JobMatcherVacancy:
    try:
        result = await vacancy_collector.collect_vacancy(
            DataForVacancyCollection(
                vacancy_text=vacancy_text, source_type=SourceType.manual, source_id=None
            )
        )
    except (GetVacancyError, CollectVacancyError, Exception) as exception:
        is_vacancy = None
        log_data: Dict[str, Any] = {
            "exception": str(exception),
        }
        if isinstance(exception, GetVacancyError):
            log_data["metainfo"] = exception.metainfo
        elif isinstance(exception, CollectVacancyError):
            is_vacancy = False
            log_data["get_vacancy_result"] = exception.get_vacancy_result.model_dump()

        async with uow:
            source_process_log = JobMatcherSourceProcessLog(
                source_type=SourceType.manual,
                source_id=None,
                source_text=vacancy_text,
                is_vacancy=is_vacancy,
                data=log_data,
            )
            uow.session.add(source_process_log)

        raise exception

    async with uow:
        uow.session.add(result.vacancy)
        source_process_log = JobMatcherSourceProcessLog(
            source_type=SourceType.manual,
            source_id=None,
            source_text=vacancy_text,
            is_vacancy=True,
            data={
                "get_vacancy_result": result.get_vacancy_result.model_dump(),
            },
        )
        uow.session.add(source_process_log)
        await uow.session.flush()
        result.vacancy = (
            await uow.session.execute(
                select(JobMatcherVacancy)
                .where(JobMatcherVacancy.id == result.vacancy.id)
                .options(
                    selectinload(JobMatcherVacancy.matches).selectinload(
                        JobMatcherVacancyWithResumeMatch.resume
                    )
                )
            )
        ).scalar_one()

        return result.vacancy

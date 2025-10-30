import asyncio
import datetime
from typing import List, Dict, Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from application.job_matcher.services import LLMService
from application.job_matcher.services.llm_service import (
    MatchVacancyAndResumeError,
    MatchVacancyAndResumeResult,
    MatchVacancyAndResumeComment,
)

from application.job_matcher.models import (
    JobMatcherResume,
    JobMatcherVacancy,
    JobMatcherVacancyWithResumeMatch,
    VacancyWithResumeMatchComment,
    JobMatcherVacancyWithResumeMatchProcessLog,
)
from core.notifier.notifier import Notifier
from config import get_config


class MatchVacancyWithResumesDto(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    vacancy: JobMatcherVacancy
    resumes: List[JobMatcherResume]


async def match_vacancies_with_resumes(
    session_maker: async_sessionmaker[AsyncSession],
    llm_service: LLMService,
    notifier: Notifier,
) -> None:
    async with session_maker() as session:
        resumes = list(
            (
                await session.execute(
                    select(JobMatcherResume)
                    .filter(JobMatcherResume.is_active.is_(True))
                    .order_by(JobMatcherResume.created_at, JobMatcherResume.id)
                )
            )
            .scalars()
            .all()
        )

        vacancies = (
            (
                await session.execute(
                    select(JobMatcherVacancy)
                    .where(JobMatcherVacancy.duplicate_check_success.is_(True))
                    .where(JobMatcherVacancy.processed_at.is_(None))
                    .order_by(JobMatcherVacancy.created_at, JobMatcherVacancy.id)
                    .options(selectinload(JobMatcherVacancy.matches))
                    .limit(20)
                )
            )
            .scalars()
            .all()
        )

    for vacancy in vacancies:
        await __match_vacancy_with_resumes(
            MatchVacancyWithResumesDto(vacancy=vacancy, resumes=resumes),
            session_maker,
            llm_service,
            notifier,
        )


async def __match_vacancy_with_resumes(
    dto: MatchVacancyWithResumesDto,
    session_maker: async_sessionmaker[AsyncSession],
    llm_service: LLMService,
    notifier: Notifier,
) -> None:
    if dto.vacancy.original_vacancy_id is None:
        await asyncio.gather(
            *[
                __match_vacancy_with_resume(
                    dto.vacancy, resume, session_maker, llm_service, notifier
                )
                for resume in dto.resumes
            ]
        )

    async with session_maker() as session:
        dto.vacancy.processed_at = datetime.datetime.now(datetime.UTC)
        session.add(dto.vacancy)
        await session.commit()


async def __match_vacancy_with_resume(
    vacancy: JobMatcherVacancy,
    resume: JobMatcherResume,
    session_maker: async_sessionmaker[AsyncSession],
    llm_service: LLMService,
    notifier: Notifier,
) -> None:
    for match in vacancy.matches:
        if match.resume_id == resume.id:
            return

    try:
        result = await __get_match_result(vacancy, resume, llm_service)
    except MatchVacancyAndResumeError | Exception as exception:
        log_data: Dict[str, Any] = {
            "exception": str(exception),
        }
        if isinstance(exception, MatchVacancyAndResumeError):
            log_data["metainfo"] = exception.metainfo

        async with session_maker() as session:
            log = JobMatcherVacancyWithResumeMatchProcessLog(
                vacancy_id=vacancy.id,
                resume_id=resume.id,
                score=None,
                is_recommended=None,
                data=log_data,
            )
            session.add(log)
            await session.commit()
        return

    async with session_maker() as session:
        match = JobMatcherVacancyWithResumeMatch(
            vacancy_id=vacancy.id,
            resume_id=resume.id,
            score=result.score,
            is_recommended=__calculate_is_recommended_match(result),
            comments=[
                VacancyWithResumeMatchComment(
                    text=comment.text,
                    score=comment.score,
                )
                for comment in result.comments
            ],
        )
        log = JobMatcherVacancyWithResumeMatchProcessLog(
            vacancy_id=vacancy.id,
            resume_id=resume.id,
            score=match.score,
            is_recommended=match.is_recommended,
            data={
                "match_result": result.model_dump(),
            },
        )
        session.add(match)
        session.add(log)
        await session.commit()
    await notify_about_match_if_need(match, vacancy, resume, notifier)


async def __get_match_result(
    vacancy: JobMatcherVacancy, resume: JobMatcherResume, llm_service: LLMService
) -> MatchVacancyAndResumeResult:
    if vacancy.specialist_type != resume.specialist_type:
        return MatchVacancyAndResumeResult(
            score=1,
            comments=[
                MatchVacancyAndResumeComment(
                    score=10, text="Тип специалиста не совпадает с типом вакансии"
                )
            ],
            metainfo={},
        )

    return await llm_service.try_match_vacancy_and_resume(vacancy.text, resume.text)


def __calculate_is_recommended_match(match_data: MatchVacancyAndResumeResult) -> bool:
    return match_data.score >= get_config().JOB_MATCHER_MIN_SCORE_FOR_RECOMMENDED_MATCH


async def notify_about_match_if_need(
    match: JobMatcherVacancyWithResumeMatch,
    vacancy: JobMatcherVacancy,
    resume: JobMatcherResume,
    notifier: Notifier,
) -> None:
    if not match.is_recommended:
        return

    await notifier.send_notification(
        (
            f"<b>Найдено новое совпадение для {resume.employee} ({resume.grade.value} {resume.specialist_type.value})!</b>\n"
            f"Вакансия {vacancy.job_title} от компании {vacancy.company}\n"
            f"Рейтинг совпадения - {match.score} из 10"
        )
    )

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from application.job_matcher.exceptions import VacancyNotFoundException
from application.job_matcher.models import (
    JobMatcherVacancy,
    JobMatcherVacancyWithResumeMatch,
)
from core.database.uow import UoW


async def get_vacancy_by_id(vacancy_id: UUID, uow: UoW) -> JobMatcherVacancy:
    async with uow:
        vacancy: JobMatcherVacancy = (
            await uow.session.execute(
                select(JobMatcherVacancy)
                .where(JobMatcherVacancy.id == vacancy_id)
                .options(
                    selectinload(JobMatcherVacancy.matches).selectinload(
                        JobMatcherVacancyWithResumeMatch.resume
                    ),
                    selectinload(JobMatcherVacancy.original_vacancy),
                    selectinload(JobMatcherVacancy.duplicates),
                )
            )
        ).scalar_one_or_none()

        if vacancy is None:
            raise VacancyNotFoundException(vacancy_id)

        return vacancy

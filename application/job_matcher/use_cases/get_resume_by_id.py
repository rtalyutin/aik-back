from uuid import UUID

from sqlalchemy import select

from application.job_matcher.exceptions import ResumeNotFoundException
from application.job_matcher.models import (
    JobMatcherResume,
)
from core.database.uow import UoW


async def get_resume_by_id(resume_id: UUID, uow: UoW) -> JobMatcherResume:
    async with uow:
        resume: JobMatcherResume = (
            await uow.session.execute(
                select(JobMatcherResume).where(JobMatcherResume.id == resume_id)
            )
        ).scalar_one_or_none()

        if resume is None:
            raise ResumeNotFoundException(resume_id)

        return resume

from application.job_matcher.exceptions import (
    ResumeNotFoundException,
    ResumeAlreadyActivatedException,
)
from application.job_matcher.models import JobMatcherResume
from core.database.uow import UoW
from sqlalchemy import select
from uuid import UUID


async def activate_resume(resume_id: UUID, uow: UoW) -> JobMatcherResume:
    async with uow:
        resume: JobMatcherResume = (
            await uow.session.execute(
                select(JobMatcherResume)
                .where(JobMatcherResume.id == resume_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if resume is None:
            raise ResumeNotFoundException(resume_id)

        if resume.is_active:
            raise ResumeAlreadyActivatedException(resume_id)

        resume.is_active = True
        uow.session.add(resume)
        await uow.session.flush()
        await uow.session.refresh(resume)

        return resume

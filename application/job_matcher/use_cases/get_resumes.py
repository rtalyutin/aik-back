import uuid
from typing import Optional, List

from pydantic import BaseModel

from application.job_matcher.models import JobMatcherResume, SpecialistType, Grade
from core.database.uow import UoW
from sqlalchemy import select, desc, or_, and_


class GetResumesFilter(BaseModel):
    specialist_type: Optional[SpecialistType]
    grade: Optional[Grade]
    query_text: Optional[str]


async def get_resumes(
    query_filters: GetResumesFilter,
    limit: int,
    last_resume_id: Optional[uuid.UUID],
    uow: UoW,
) -> List[JobMatcherResume]:
    async with uow:
        filters = []
        if query_filters.specialist_type:
            filters.append(
                JobMatcherResume.specialist_type == query_filters.specialist_type
            )
        if query_filters.grade:
            filters.append(JobMatcherResume.grade == query_filters.grade)
        if query_filters.query_text:
            filters.append(JobMatcherResume.text.ilike(f"%{query_filters.query_text}%"))

        query = (
            select(JobMatcherResume)
            .order_by(desc(JobMatcherResume.created_at), desc(JobMatcherResume.id))
            .filter(*filters)
        )

        if last_resume_id:
            last_resume = (
                await uow.session.execute(
                    select(JobMatcherResume).where(
                        JobMatcherResume.id == last_resume_id
                    )
                )
            ).scalar_one_or_none()
            if last_resume:
                query = query.filter(
                    or_(
                        JobMatcherResume.created_at < last_resume.created_at,
                        and_(
                            JobMatcherResume.created_at == last_resume.created_at,
                            JobMatcherResume.id < last_resume.id,
                        ),
                    ),
                )

        return list((await uow.session.execute(query.limit(limit))).scalars().all())

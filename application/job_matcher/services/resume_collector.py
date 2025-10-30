import dataclasses

from pydantic import BaseModel

from application.job_matcher.models import (
    SpecialistType,
    Grade,
    Salary,
    JobMatcherResume,
)
from application.job_matcher.services import LLMService
from application.job_matcher.services import (
    GetResumeResult,
    TechnologyForResume,
    SkillForResume,
)


class DataForResumeCollection(BaseModel):
    resume_text: str


@dataclasses.dataclass
class ResumeCollectionResult:
    resume: JobMatcherResume
    get_resume_result: GetResumeResult


class CollectResumeError(Exception):
    message: str = "Invalid resume text"
    get_resume_result: GetResumeResult

    def __init__(
        self,
        get_resume_result: GetResumeResult,
    ):
        self.get_resume_result = get_resume_result
        super().__init__(self.message)


class ResumeCollector:
    llm_service: LLMService

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def collect_resume(
        self, data: DataForResumeCollection
    ) -> ResumeCollectionResult:
        result = await self.llm_service.try_get_resume_from_text(data.resume_text)
        if not result.is_resume:
            raise CollectResumeError(
                get_resume_result=result,
            )

        return ResumeCollectionResult(
            resume=JobMatcherResume(
                text=data.resume_text,
                employee=result.resume.employee,
                specialist_type=SpecialistType(result.resume.specialist_type.value),
                grade=Grade(result.resume.grade.value),
                experience=result.resume.experience,
                salary=Salary(
                    salary_from=result.resume.salary.salary_from,
                    salary_to=result.resume.salary.salary_to,
                    currency=result.resume.salary.currency,
                    tax_included=result.resume.salary.tax_included,
                )
                if result.resume.salary.is_defined
                else None,
                technologies=[
                    TechnologyForResume(
                        name=el.name,
                        level=el.level,
                    )
                    for el in result.resume.technologies
                ],
                skills=[
                    SkillForResume(
                        name=el.name,
                        level=el.level,
                    )
                    for el in result.resume.skills
                ],
            ),
            get_resume_result=result,
        )

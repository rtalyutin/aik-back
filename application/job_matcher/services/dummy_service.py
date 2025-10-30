from application.job_matcher.services import (
    LLMService,
    GetVacancyResult,
    VacancyData,
    SpecialistType,
    WorkFormat,
    Grade,
    Salary,
    Technology,
    Skill,
)
from application.job_matcher.services.llm_service import (
    GetResumeResult,
    ResumeData,
    TechnologyForResume,
    SkillForResume,
    MatchVacancyAndResumeResult,
    MatchVacancyAndResumeComment,
    CheckVacancyDuplicateResult,
)


class DummyService(LLMService):
    async def try_get_vacancy_from_text(self, text: str) -> GetVacancyResult:
        return GetVacancyResult(
            is_vacancy=True,
            vacancy=VacancyData(
                company="Рога и копыта",
                job_title="Backend разработчик",
                specialist_type=SpecialistType.backend,
                work_format=WorkFormat.office,
                grade=Grade.junior,
                experience_required=1,
                salary=Salary(
                    is_defined=True,
                    salary_from=100000,
                    salary_to=120000,
                    currency="RUB",
                    tax_included=True,
                ),
                technologies=[
                    Technology(name="php", level=5, required=True),
                    Technology(name="js", level=5, required=False),
                ],
                skills=[
                    Skill(name="ООП", level=4, required=True),
                    Skill(name="SOLID", level=3, required=False),
                ],
            ),
            metainfo={},
        )

    async def try_get_resume_from_text(self, text: str) -> GetResumeResult:
        return GetResumeResult(
            is_resume=True,
            resume=ResumeData(
                employee="Иванов И.И.",
                specialist_type=SpecialistType.backend,
                grade=Grade.junior,
                experience=1,
                salary=Salary(
                    is_defined=True,
                    salary_from=100000,
                    salary_to=120000,
                    currency="RUB",
                    tax_included=True,
                ),
                technologies=[
                    TechnologyForResume(name="php", level=5),
                    TechnologyForResume(name="js", level=5),
                ],
                skills=[
                    SkillForResume(name="ООП", level=4),
                    SkillForResume(name="SOLID", level=3),
                ],
            ),
            metainfo={},
        )

    async def try_match_vacancy_and_resume(
        self, vacancy_text: str, resume_text: str
    ) -> MatchVacancyAndResumeResult:
        return MatchVacancyAndResumeResult(
            score=9,
            comments=[
                MatchVacancyAndResumeComment(
                    text="Коммент текст",
                    score=7,
                ),
                MatchVacancyAndResumeComment(
                    text="Коммент2 текст",
                    score=1,
                ),
            ],
            metainfo={},
        )

    async def check_vacancy_duplicate(
        self, vacancy_text_1: str, vacancy_text_2: str
    ) -> CheckVacancyDuplicateResult:
        return CheckVacancyDuplicateResult(
            probability_score=5,
            metainfo={},
        )

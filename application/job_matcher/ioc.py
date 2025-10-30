from typing import Self

from dishka import Provider, Scope, provide

from application.job_matcher.services import (
    LLMService,
    VacancyCollector,
    ResumeCollector,
)
from application.job_matcher.services.dummy_service import DummyService


class JobMatcherDepsProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def get_vacancy_collector(
        self: Self, llm_service: LLMService
    ) -> VacancyCollector:
        return VacancyCollector(llm_service=llm_service)

    @provide(scope=Scope.APP)
    async def get_vacancy_collector_app(
        self: Self, llm_service: LLMService
    ) -> VacancyCollector:
        return VacancyCollector(llm_service=llm_service)

    @provide(scope=Scope.REQUEST)
    async def get_resume_collector(
        self: Self, llm_service: LLMService
    ) -> ResumeCollector:
        return ResumeCollector(llm_service=llm_service)

    @provide(scope=Scope.APP)
    async def get_resume_collector_app(
        self: Self, llm_service: LLMService
    ) -> ResumeCollector:
        return ResumeCollector(llm_service=llm_service)

    @provide(scope=Scope.REQUEST)
    async def get_llm_service(self: Self) -> LLMService:
        return DummyService()

    @provide(scope=Scope.APP)
    async def get_llm_service_app(self: Self) -> LLMService:
        return DummyService()

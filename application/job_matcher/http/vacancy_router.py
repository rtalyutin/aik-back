import uuid
from typing import Optional, Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Query, Depends

from application.job_matcher.exceptions import VacancyNotFoundException
from application.job_matcher.http.responses.responses import (
    VacancyResponse,
    VacancyListItemResponse,
)
from application.job_matcher.models import SpecialistType, Grade, WorkFormat
from application.job_matcher.use_cases import GetVacanciesFilter
from core.auth import authentication_middleware
from core.handlers.handlers import get_responses_for_exceptions
from core.responses.responses import (
    BaseDataResponse,
    BaseListDataResponse,
)
from core.database.uow import UoW

from pydantic import BaseModel

from application.job_matcher.services import (
    VacancyCollector,
)
from application.job_matcher import use_cases

router = APIRouter(
    prefix="/job-matcher/vacancies",
    tags=["job-matcher-vacancies"],
    dependencies=[Depends(authentication_middleware)],
)


class AddManualFromTextRequest(BaseModel):
    text: str


class MatchRequest(BaseModel):
    vacancy_text: str
    resume_text: str


@router.get(
    "",
    response_model=BaseListDataResponse[VacancyListItemResponse],
    responses=get_responses_for_exceptions(
        with_validation_error=True,
        with_auth_error=True,
        with_internal_error=True,
    ),
)
@inject
async def get_vacancies(
    uow: FromDishka[UoW],
    specialist_type: Optional[SpecialistType] = Query(
        None, description="Тип специалиста для фильтрации"
    ),
    grade: Optional[Grade] = Query(
        None, description="Грейд специалиста для фильтрации"
    ),
    work_format: Optional[WorkFormat] = Query(None, description="Формат работы"),
    with_duplicates: Optional[bool] = Query(
        None, description="Нужно ли возвращать дубликаты"
    ),
    query_text: Optional[str] = Query(None, description="Часть текста вакансии"),
    limit: Annotated[
        int, Query(description="Лимит записей в результате", le=100, ge=10)
    ] = 20,
    last_vacancy_id: Annotated[
        Optional[uuid.UUID], Query(description="Id последнего полученного вакансии")
    ] = None,
) -> BaseListDataResponse[VacancyListItemResponse]:
    return BaseListDataResponse[VacancyListItemResponse](
        data=[
            VacancyListItemResponse.make_from_model(vacancy)
            for vacancy in await use_cases.get_vacancies(
                query_filters=GetVacanciesFilter(
                    specialist_type=specialist_type,
                    grade=grade,
                    work_format=work_format,
                    with_duplicates=with_duplicates,
                    query_text=query_text,
                ),
                limit=limit,
                last_vacancy_id=last_vacancy_id,
                uow=uow,
            )
        ]
    )


@router.get(
    "/{vacancy_id}",
    response_model=BaseDataResponse[VacancyResponse],
    responses=get_responses_for_exceptions(
        VacancyNotFoundException,
        with_validation_error=False,
        with_auth_error=True,
        with_internal_error=True,
    ),
)
@inject
async def get_vacancy_by_id(
    vacancy_id: uuid.UUID,
    uow: FromDishka[UoW],
) -> BaseDataResponse[VacancyResponse]:
    return BaseDataResponse[VacancyResponse](
        data=VacancyResponse.make_from_model(
            await use_cases.get_vacancy_by_id(vacancy_id, uow)
        )
    )


@router.post(
    "/add-manual",
    response_model=BaseDataResponse[VacancyResponse],
    responses=get_responses_for_exceptions(
        with_validation_error=True,
        with_auth_error=True,
        with_internal_error=True,
    ),
)
@inject
async def add_manual(
    request: AddManualFromTextRequest,
    vacancy_collector: FromDishka[VacancyCollector],
    uow: FromDishka[UoW],
) -> BaseDataResponse[VacancyResponse]:
    return BaseDataResponse[VacancyResponse](
        data=VacancyResponse.make_from_model(
            await use_cases.add_manual_vacancy(request.text, vacancy_collector, uow)
        )
    )

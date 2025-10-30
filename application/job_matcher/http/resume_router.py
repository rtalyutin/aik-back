import uuid
from typing import Optional, Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Query
from fastapi.params import Depends

from application.job_matcher.exceptions import (
    ResumeNotFoundException,
    ResumeAlreadyActivatedException,
    ResumeAlreadyNotActivatedException,
)
from application.job_matcher.http.responses.responses import (
    ResumeBaseResponse,
    ResumeListItemResponse,
)
from application.job_matcher.models import SpecialistType, Grade
from application.job_matcher.use_cases import GetResumesFilter
from core.database.uow import UoW

from pydantic import BaseModel

from application.job_matcher.services import (
    ResumeCollector,
)
from application.job_matcher import use_cases
from core.handlers.handlers import get_responses_for_exceptions
from core.responses.responses import (
    BaseDataResponse,
    BaseListDataResponse,
)
from core.auth import (
    authentication_middleware,
)

router = APIRouter(
    prefix="/job-matcher/resumes",
    tags=["job-matcher-resumes"],
    dependencies=[Depends(authentication_middleware)],
)


class AddManualFromTextRequest(BaseModel):
    text: str


@router.get(
    "",
    response_model=BaseListDataResponse[ResumeListItemResponse],
    responses=get_responses_for_exceptions(
        with_validation_error=True,
        with_auth_error=True,
        with_internal_error=True,
    ),
)
@inject
async def get_resumes(
    uow: FromDishka[UoW],
    specialist_type: Optional[SpecialistType] = Query(
        None, description="Тип специалиста для фильтрации"
    ),
    grade: Optional[Grade] = Query(
        None, description="Грейд специалиста для фильтрации"
    ),
    query_text: Optional[str] = Query(None, description="Часть текста резюме"),
    limit: Annotated[
        int, Query(description="Лимит записей в результате", le=100, ge=10)
    ] = 20,
    last_resume_id: Annotated[
        Optional[uuid.UUID], Query(description="Id последнего полученного резюме")
    ] = None,
) -> BaseListDataResponse[ResumeListItemResponse]:
    return BaseListDataResponse[ResumeListItemResponse](
        data=[
            ResumeListItemResponse.make_from_model(resume)
            for resume in await use_cases.get_resumes(
                query_filters=GetResumesFilter(
                    specialist_type=specialist_type, grade=grade, query_text=query_text
                ),
                limit=limit,
                last_resume_id=last_resume_id,
                uow=uow,
            )
        ]
    )


@router.get(
    "/{resume_id}",
    response_model=BaseDataResponse[ResumeBaseResponse],
    responses=get_responses_for_exceptions(
        ResumeNotFoundException,
        with_validation_error=False,
        with_auth_error=True,
        with_internal_error=True,
    ),
)
@inject
async def get_resume_by_id(
    resume_id: uuid.UUID,
    uow: FromDishka[UoW],
) -> BaseDataResponse[ResumeBaseResponse]:
    return BaseDataResponse[ResumeBaseResponse](
        data=ResumeBaseResponse.make_from_model(
            await use_cases.get_resume_by_id(resume_id, uow)
        )
    )


@router.post(
    "/add-manual",
    response_model=BaseDataResponse[ResumeBaseResponse],
    responses=get_responses_for_exceptions(
        with_validation_error=True,
        with_auth_error=True,
        with_internal_error=True,
    ),
)
@inject
async def add_manual(
    request: AddManualFromTextRequest,
    resume_collector: FromDishka[ResumeCollector],
    uow: FromDishka[UoW],
) -> BaseDataResponse[ResumeBaseResponse]:
    return BaseDataResponse[ResumeBaseResponse](
        data=ResumeBaseResponse.make_from_model(
            await use_cases.add_manual_resume(request.text, resume_collector, uow)
        )
    )


@router.post(
    "/{resume_id}/activate",
    response_model=BaseDataResponse[ResumeBaseResponse],
    responses=get_responses_for_exceptions(
        ResumeNotFoundException,
        ResumeAlreadyActivatedException,
        with_validation_error=True,
        with_auth_error=True,
        with_internal_error=True,
    ),
)
@inject
async def activate_resume(
    resume_id: uuid.UUID,
    uow: FromDishka[UoW],
) -> BaseDataResponse[ResumeBaseResponse]:
    return BaseDataResponse[ResumeBaseResponse](
        data=ResumeBaseResponse.make_from_model(
            await use_cases.activate_resume(resume_id, uow)
        )
    )


@router.post(
    "/{resume_id}/deactivate",
    response_model=BaseDataResponse[ResumeBaseResponse],
    responses=get_responses_for_exceptions(
        ResumeNotFoundException,
        ResumeAlreadyNotActivatedException,
        with_validation_error=True,
        with_auth_error=True,
        with_internal_error=True,
    ),
)
@inject
async def deactivate_resume(
    resume_id: uuid.UUID,
    uow: FromDishka[UoW],
) -> BaseDataResponse[ResumeBaseResponse]:
    return BaseDataResponse[ResumeBaseResponse](
        data=ResumeBaseResponse.make_from_model(
            await use_cases.deactivate_resume(resume_id, uow)
        )
    )

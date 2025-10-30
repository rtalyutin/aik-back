from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter
from fastapi.params import Depends

from application.job_matcher.use_cases import StatisticsResult
from core.database.uow import UoW


from application.job_matcher import use_cases
from core.handlers.handlers import get_responses_for_exceptions
from core.responses.responses import (
    BaseDataResponse,
)
from core.auth import (
    authentication_middleware,
)

router = APIRouter(
    prefix="/job-matcher/statistics",
    tags=["job-matcher-statics"],
    dependencies=[Depends(authentication_middleware)],
)


@router.get(
    "",
    response_model=BaseDataResponse[StatisticsResult],
    responses=get_responses_for_exceptions(
        with_auth_error=True,
        with_internal_error=True,
    ),
)
@inject
async def get_statistics(
    uow: FromDishka[UoW],
) -> BaseDataResponse[StatisticsResult]:
    return BaseDataResponse[StatisticsResult](data=await use_cases.get_statistics(uow))

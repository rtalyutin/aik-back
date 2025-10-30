from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter
from pydantic import BaseModel

from core.auth import AuthService
from core.errors import BaseError
from core.handlers.handlers import get_responses_for_exceptions
from core.responses.responses import BaseDataResponse

router = APIRouter()


class SignInRequest(BaseModel):
    login: str
    password: str


class SignInResponse(BaseModel):
    token: str


class CredentialsNotVerified(BaseError):
    code: str = "credentials_not_verified"
    message: str = "Credentials not verified"


@router.post(
    "/sign-in",
    response_model=BaseDataResponse[SignInResponse],
    responses=get_responses_for_exceptions(
        CredentialsNotVerified,
        with_validation_error=True,
        with_internal_error=True,
    ),
)
@inject
async def sign_in(
    request: SignInRequest,
    auth_service: FromDishka[AuthService],
) -> BaseDataResponse[SignInResponse]:
    if not auth_service.verify_credentials(request.login, request.password):
        raise CredentialsNotVerified()

    return BaseDataResponse[SignInResponse](
        data=SignInResponse(token=auth_service.create_access_token())
    )

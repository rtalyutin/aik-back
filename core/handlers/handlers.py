from typing import Union, Awaitable, Optional, Any, Dict, Type, List

from fastapi import Request, FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse
from starlette.status import (
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from core.auth import AuthenticationError
from core.errors import BaseError, ExceptionData
from config import get_config
from core.responses.responses import ErrorResponse

config = get_config()


def get_responses_for_exceptions(
    *exceptions: Type[BaseError],
    with_internal_error: bool = True,
    with_auth_error: bool = False,
    with_validation_error: bool = False,
) -> Dict[Union[int, str], Dict[str, Any]]:
    responses = {}

    # Группируем исключения по status_code
    status_groups: Dict[int, List[Dict[str, Any]]] = {}

    for exc_class in exceptions:
        status_code = exc_class.status_code

        if status_code not in status_groups:
            status_groups[status_code] = []

        status_groups[status_code].append(
            {
                "status_code": exc_class.status_code,
                "code": exc_class.code,
            }
        )

    if with_internal_error:
        status_groups[HTTP_500_INTERNAL_SERVER_ERROR] = [
            {
                "status_code": HTTP_500_INTERNAL_SERVER_ERROR,
                "code": "internal_server_error",
            }
        ]

    if with_auth_error:
        status_groups[AuthenticationError.status_code] = [
            {
                "status_code": AuthenticationError.status_code,
                "code": AuthenticationError.code,
            }
        ]

    if with_validation_error:
        status_groups[HTTP_422_UNPROCESSABLE_ENTITY] = [
            {
                "status_code": HTTP_422_UNPROCESSABLE_ENTITY,
                "code": "validation_error",
            }
        ]

    # Создаем responses для каждой группы status_code
    for status_code, exc_list in status_groups.items():
        if len(exc_list) == 1:
            # Если только одно исключение для этого status_code
            exc_info = exc_list[0]
            description = f"Code: {exc_info['code']}"
        else:
            # Если несколько исключений для одного status_code
            codes = [exc["code"] for exc in exc_list]
            description = f"Possible errors: {', '.join(codes)}"

        responses[status_code] = {"model": ErrorResponse, "description": description}

    return responses


def core_register_api_handlers(app: FastAPI):
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> Union[JSONResponse, Awaitable[JSONResponse]]:
        exception_data = ExceptionData.make_exception_data(exc)

        return JSONResponse(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            content=make_error_content(
                "validation_error",
                "Validation error",
                details=[err for err in exc.errors()],
                exception_data=exception_data,
            ),
        )

    @app.exception_handler(BaseError)
    def base_error_handler(request: Request, exc: BaseError) -> JSONResponse:
        exception_data = ExceptionData.make_exception_data(exc)
        return JSONResponse(
            status_code=exc.status_code,
            content=make_error_content(
                exc.code,
                exc.message,
                details=exc.details,
                exception_data=exception_data,
            ),
        )

    @app.exception_handler(Exception)
    def internal_server_error_handler(request: Request, exc: Exception) -> JSONResponse:
        exception_data = ExceptionData.make_exception_data(exc)
        return JSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=make_error_content(
                "internal_server_error",
                "Internal server error",
                details=None,
                exception_data=exception_data,
            ),
        )


def make_error_content(
    code: str, message: str, details: Optional[Any], exception_data: ExceptionData
) -> Dict:
    content = {
        "code": code,
        "message": message,
        "details": details,
    }

    if config.DEBUG:
        content["exception_data"] = {
            "type": exception_data.exc_type,
            "text": str(exception_data.exc),
            "traceback": exception_data.traceback,
        }

    return content

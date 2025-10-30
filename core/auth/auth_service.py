from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import Depends, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
)
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, UTC
from fastapi import Request

from pydantic import BaseModel
from core.errors import BaseError

ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security_scheme = HTTPBearer(
    scheme_name="BaseAuth",
    description="Аутентификация по access токену",
    auto_error=False,
)


class AuthenticationError(BaseError):
    status_code: int = status.HTTP_401_UNAUTHORIZED
    code: str = "authentication_error"
    message: str = "Authentication error"


class AuthUser(BaseModel):
    username: str
    is_admin: bool


class AuthService:
    current_user: AuthUser | None

    def __init__(
        self,
        base_login: str,
        base_password_hash: str,
        jwt_secret: str,
        access_token_expire_minutes: int = 30,
    ):
        self.base_login = base_login
        self.base_password_hash = base_password_hash
        self.jwt_secret = jwt_secret
        self.access_token_expire_minutes = access_token_expire_minutes

    def verify_credentials(self, login: str, password: str) -> bool:
        return login == self.base_login and pwd_context.verify(
            password, self.base_password_hash
        )

    def create_access_token(self, expires_delta: timedelta = None) -> str:
        if expires_delta is None:
            expires_delta = timedelta(minutes=self.access_token_expire_minutes)
        expire = datetime.now(UTC) + expires_delta
        encoded_jwt = jwt.encode(
            {
                "sub": self.base_login,
                "exp": expire,
            },
            self.jwt_secret,
            algorithm=ALGORITHM,
        )

        return encoded_jwt

    def get_current_user(self) -> AuthUser | None:
        return self.current_user

    async def try_auth_user(
        self, data: HTTPAuthorizationCredentials | None
    ) -> AuthUser:
        if not data:
            raise AuthenticationError()

        try:
            payload = jwt.decode(
                data.credentials, self.jwt_secret, algorithms=[ALGORITHM]
            )
            username: str = payload.get("sub")
            if username != self.base_login:
                raise AuthenticationError()

            self.current_user = AuthUser(
                username=username,
                is_admin=True,
            )
        except JWTError:
            raise AuthenticationError()

        return self.current_user


@inject
async def authentication_middleware(
    request: Request,
    security_data: HTTPAuthorizationCredentials = Depends(security_scheme),
    auth_service: FromDishka[AuthService] = FromDishka(),
):
    user = await auth_service.try_auth_user(security_data)
    request.state.user = user

from dishka import Provider, Scope, provide

from config import get_config
from core.auth.auth_service import AuthService


class AuthDepsProvider(Provider):
    @provide(scope=Scope.REQUEST)  # Or a different scope based on your needs
    def get_auth_service(self) -> AuthService:
        config = get_config()

        return AuthService(
            base_login=config.AUTH_BASE_LOGIN,
            base_password_hash=config.AUTH_BASE_PASSWORD_HASH,
            jwt_secret=config.AUTH_JWT_SECRET,
            access_token_expire_minutes=config.AUTH_ACCESS_TOKEN_EXPIRE_MINUTES,
        )

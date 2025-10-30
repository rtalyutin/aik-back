import html
from abc import ABC, abstractmethod
from datetime import datetime


class Notifier(ABC):
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    ERROR_MESSAGE_TEMPLATE = """
<b>Ошибка в обработке вакансий</b>

{timestamp}
{context}
{error_type}
{error_message}
    """.strip()

    def _format_error_message(self, error: Exception, context: str) -> str:
        return self.ERROR_MESSAGE_TEMPLATE.format(
            timestamp=datetime.now().strftime(self.DATETIME_FORMAT),
            context=html.escape(context),
            error_type=html.escape(type(error).__name__),
            error_message=html.escape(str(error)),
        )

    @abstractmethod
    async def send_error_notification(
        self,
        error: Exception,
        context: str = "",
    ) -> None:
        pass

    @abstractmethod
    async def send_notification(
        self,
        message: str,
    ) -> None:
        pass

from abc import abstractmethod


class TelegramNotifiable:
    @abstractmethod
    def get_notification_message(self) -> str:
        pass

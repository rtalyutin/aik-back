import logging
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from application.karaoke_tracks.services.assemblyai_client import IAssemblyAIClient
from core.file_storage.file_storage_service import FileStorageService
from core.notifier.notifier import Notifier

logger = logging.getLogger(__name__)


async def process_transcription(
    session_maker: async_sessionmaker[AsyncSession],
    assemblyai_client: IAssemblyAIClient,
    file_storage_service: FileStorageService,
    notifier: Notifier,
) -> None:
    pass

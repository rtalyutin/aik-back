import asyncio
import logging
import signal
from typing import List

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from application.job_matcher.services import (
    LLMService,
)
from application.job_matcher.use_cases import (
    match_vacancies_with_resumes,
    check_vacancies_for_duplicates,
)
from config import get_config

from core import ioc
from core.notifier.notifier import Notifier
from logger import setup_logging

container = ioc.make_ioc(with_fast_api=False)

config = get_config()
setup_logging(config, service_name="background")
logger = logging.getLogger(__name__)


async def _graceful_shutdown(tasks: List[asyncio.Task]):
    logger.info("Initiating graceful shutdown", extra={"tasks_count": len(tasks)})
    for task in tasks:
        if not task.done():
            task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("Graceful shutdown completed")


async def main():
    shutdown_initiated = False

    notifier: Notifier = await container.get(Notifier)

    def signal_handler():
        nonlocal shutdown_initiated
        if not shutdown_initiated:
            logger.info("Received shutdown signal")
            shutdown_initiated = True
            asyncio.create_task(_graceful_shutdown(tasks))

    session_maker: async_sessionmaker[AsyncSession] = await container.get(
        async_sessionmaker[AsyncSession]
    )
    llm_service: LLMService = await container.get(LLMService)

    tasks = [
        asyncio.create_task(
            job_matcher_check_vacancies_for_duplicates(
                session_maker, llm_service, notifier
            )
        ),
        asyncio.create_task(
            job_matcher_match_vacancies_with_resumes(
                session_maker, llm_service, notifier
            )
        ),
    ]

    loop = asyncio.get_running_loop()
    for sig in [signal.SIGTERM, signal.SIGINT]:
        loop.add_signal_handler(sig, signal_handler)

    logger.info("Background tasks started", extra={"tasks_count": len(tasks)})

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        if not shutdown_initiated:
            await _graceful_shutdown(tasks)


async def job_matcher_check_vacancies_for_duplicates(
    session_maker: async_sessionmaker[AsyncSession],
    llm_service: LLMService,
    notifier: Notifier,
):
    iteration = 0
    task_name = "job_matcher_check_vacancies_for_duplicates"

    while True:
        iteration += 1
        logger.info(
            "Checking vacancies for duplicates",
            extra={"task": task_name, "iteration": iteration},
        )

        task = asyncio.create_task(
            check_vacancies_for_duplicates(session_maker, llm_service)
        )

        try:
            await asyncio.shield(task)
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            logger.info(
                "Task cancelled", extra={"task": task_name, "iteration": iteration}
            )
            if not task.done():
                await task
            break
        except Exception as e:
            logger.exception(
                "Task failed",
                extra={"task": task_name, "iteration": iteration},
                exc_info=e,
            )
            if notifier:
                await notifier.send_error_notification(
                    error=e,
                    context=f"{task_name} (iteration #{iteration})",
                )


async def job_matcher_match_vacancies_with_resumes(
    session_maker: async_sessionmaker[AsyncSession],
    llm_service: LLMService,
    notifier: Notifier,
):
    iteration = 0
    task_name = "job_matcher_match_vacancies_with_resumes"

    while True:
        iteration += 1
        logger.info(
            "Matching vacancies with resumes",
            extra={"task": task_name, "iteration": iteration},
        )

        task = asyncio.create_task(
            match_vacancies_with_resumes(session_maker, llm_service, notifier)
        )

        try:
            await asyncio.shield(task)
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            logger.info(
                "Task cancelled", extra={"task": task_name, "iteration": iteration}
            )
            if not task.done():
                await task
            break
        except Exception as e:
            logger.exception(
                "Task failed",
                extra={"task": task_name, "iteration": iteration},
                exc_info=e,
            )
            if notifier:
                await notifier.send_error_notification(
                    error=e,
                    context=f"{task_name} (iteration #{iteration})",
                )


if __name__ == "__main__":
    asyncio.run(main())
